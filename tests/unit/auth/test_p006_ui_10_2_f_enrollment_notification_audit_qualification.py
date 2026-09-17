from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path

import pytest

from backend.auth.credential_bundle_persistence.contracts import CredentialBundleQualificationReport
from backend.auth.enrollment_notification_audit_persistence import qualification as subject
from backend.auth.enrollment_notification_audit_persistence.contracts import (
    EnrollmentNotificationAuditQualificationError,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _rows(root: Path | None = None) -> list[dict[str, object]]:
    root=root or _root()
    return json.loads((root/'database/migrations/migration_manifest.json').read_text())['migrations']


def _ledger(rows: list[dict[str, object]], count: int) -> list[tuple[object,...]]:
    return [(r['migration_id'],r['sequence_number'],r['forward_sha256'],'APPLIED') for r in rows[:count]]


def _predecessor_report(*, count: int=34, operational: int=0) -> CredentialBundleQualificationReport:
    return CredentialBundleQualificationReport(
        phase='post-E', database_name='npp_dev', tls_active=True,
        repository_migration_count=35, database_migration_count=count,
        migration_tail_sequence=count,
        migration_tail_id='m006_10_02_credential_bundle_storage_delivery' if count==34 else 'later',
        nexilabs_auth_tables=subject.POST_E_AUTH_TABLES,
        public_schema_privilege_count=0, public_table_privilege_count=0,
        public_routine_privilege_count=0, principal_count=operational,
        credential_count=operational, developer_request_count=operational,
        admin_operator_count=operational, developer_decision_count=operational,
        email_challenge_count=operational, enigma_catalogue_count=3,
        enigma_catalogue_entry_count=279, enigma_profile_count=operational,
        principal_enigma_profile_count=operational, bundle_count=operational,
        bundle_secret_count=operational, delivery_count=operational,
    )


class FakePredecessor:
    report=_predecessor_report()
    calls=[]
    def __init__(self,pool): self.pool=pool
    def verify(self,*,repository_root,expected_database):
        type(self).calls.append((repository_root,expected_database))
        return type(self).report


class Cursor:
    def __init__(self, *, ledger_rows, tables, missing=None, f_count=0,
                 database='npp_dev', tls=True):
        self.ledger_rows=list(ledger_rows); self.tables=tuple(tables); self.missing=missing
        self.f_count=f_count; self.database=database; self.tls=tls; self._result=[]
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def execute(self,sql,params=None):
        s=' '.join(str(sql).split())
        if s=='SELECT current_database()': self._result=[(self.database,)]
        elif 'FROM pg_stat_ssl' in s: self._result=[(self.tls,)]
        elif 'FROM platform.schema_migration' in s: self._result=list(self.ledger_rows)
        elif 'FROM information_schema.tables' in s: self._result=[(x,) for x in self.tables]
        elif 'FROM information_schema.columns' in s:
            table=str(params[0]); values=set(dict(subject.REQUIRED_F_COLUMNS)[table])
            if self.missing in values: values.remove(self.missing)
            self._result=[(x,) for x in values]
        elif 'FROM pg_indexes' in s:
            values=set(subject.REQUIRED_F_INDEXES)
            if self.missing in values: values.remove(self.missing)
            self._result=[(x,) for x in values]
        elif 'FROM information_schema.table_constraints' in s:
            values=set(subject.REQUIRED_F_CONSTRAINTS)
            if self.missing in values: values.remove(self.missing)
            self._result=[(x,) for x in values]
        elif 'FROM information_schema.routines' in s:
            values=set(subject.REQUIRED_F_FUNCTIONS)
            if self.missing in values: values.remove(self.missing)
            self._result=[(x,) for x in values]
        elif 'FROM information_schema.triggers' in s:
            values=set(subject.REQUIRED_F_TRIGGERS)
            if self.missing in values: values.remove(self.missing)
            self._result=[(x,) for x in values]
        elif s.startswith('SELECT COUNT(*) FROM nexilabs_auth.'):
            self._result=[(self.f_count,)]
        else: raise AssertionError(f'unexpected SQL: {s}')
    def fetchone(self): return self._result[0]
    def fetchall(self): return list(self._result)


class Connection:
    def __init__(self,cursor): self._cursor=cursor
    def cursor(self): return self._cursor


class Pool:
    def __init__(self,cursor): self.cursor_obj=cursor; self.read_only=[]
    @contextmanager
    def connection(self,read_only=False): self.read_only.append(read_only); yield Connection(self.cursor_obj)


def _successor_root(tmp_path: Path) -> tuple[Path,list[dict[str,object]]]:
    src=_root(); root=tmp_path/'repo'; d=root/'database/migrations'; d.mkdir(parents=True)
    for name in (subject.F_FORWARD_FILE,subject.F_ROLLBACK_FILE,'m006_10_02_enrollment_notification_audit_filter_regex_correction.sql','m006_10_02_enrollment_notification_audit_filter_regex_correction_rollback.sql','migration_manifest.json'):
        (d/name).write_bytes((src/'database/migrations'/name).read_bytes())
    p=d/'migration_manifest.json'; payload=json.loads(p.read_text())
    payload['migrations']=payload['migrations'][:36]
    payload['catalogue_version']=21
    payload['migrations'].append({
        'migration_id':'m006_10_02_later_successor','milestone_id':'M006.10.2','sequence_number':37,
        'description':'later_successor','forward_file':'m006_10_02_later_successor.sql',
        'rollback_file':'m006_10_02_later_successor_rollback.sql','forward_sha256':'a'*64,
        'rollback_sha256':'b'*64,'forward_byte_size':1,'rollback_byte_size':1,
        'depends_on':['m006_10_02_enrollment_notification_audit_filter_regex_correction'],'transaction_policy':'embedded',
        'expected_objects':{'schemas':[],'tables':[],'indexes':[],'constraints':[],'views':[],'functions':[]},
        'destructive':False,'catalogue_entry_version':1})
    p.write_text(json.dumps(payload,indent=2)+'\n')
    return root,payload['migrations']


def test_repository_artifact_gate_locks_exact_f_row_35_hashes_and_e_predecessor() -> None:
    rows=subject.PostgreSQLEnrollmentNotificationAuditQualification.verify_repository_artifacts(_root())
    assert len(rows)>=35
    assert rows[33]['migration_id']==subject.E_MIGRATION_ID
    assert rows[34]['migration_id']==subject.F_MIGRATION_ID
    assert rows[34]['sequence_number']==35
    assert rows[34]['depends_on']==[subject.E_MIGRATION_ID]


def test_repository_artifact_gate_is_successor_safe(tmp_path: Path) -> None:
    root,_=_successor_root(tmp_path)
    rows=subject.PostgreSQLEnrollmentNotificationAuditQualification.verify_repository_artifacts(root)
    assert len(rows)==37 and rows[34]['migration_id']==subject.F_MIGRATION_ID
    assert rows[35]['migration_id']=='m006_10_02_enrollment_notification_audit_filter_regex_correction'
    assert rows[35]['sequence_number']==36
    assert rows[36]['migration_id']=='m006_10_02_later_successor'
    assert rows[36]['sequence_number']==37


def test_preflight_requires_exact_e_tail_and_zero_operational_authority(monkeypatch) -> None:
    monkeypatch.setattr(subject,'PostgreSQLCredentialBundleQualification',FakePredecessor)
    FakePredecessor.report=_predecessor_report(count=34,operational=0)
    rows=_rows(); pool=Pool(Cursor(ledger_rows=_ledger(rows,34),tables=subject.POST_E_AUTH_TABLES))
    report=subject.PostgreSQLEnrollmentNotificationAuditQualification(pool).preflight(repository_root=_root())
    assert report.phase=='pre-F'
    assert report.database_migration_count==34 and report.migration_tail_id==subject.E_MIGRATION_ID
    assert report.enrollment_event_count==report.notification_delivery_count==report.audit_export_count==0
    assert pool.read_only==[True]


def test_preflight_rejects_non_e_predecessor_tail(monkeypatch) -> None:
    monkeypatch.setattr(subject,'PostgreSQLCredentialBundleQualification',FakePredecessor)
    FakePredecessor.report=_predecessor_report(count=35)
    rows=_rows(); pool=Pool(Cursor(ledger_rows=_ledger(rows,34),tables=subject.POST_E_AUTH_TABLES))
    with pytest.raises(EnrollmentNotificationAuditQualificationError,match='exact E database tail'):
        subject.PostgreSQLEnrollmentNotificationAuditQualification(pool).preflight(repository_root=_root())


def test_post_f_verify_proves_structure_zero_seed_and_predecessor_compatibility(monkeypatch) -> None:
    monkeypatch.setattr(subject,'PostgreSQLCredentialBundleQualification',FakePredecessor)
    FakePredecessor.report=_predecessor_report(count=35,operational=0)
    rows=_rows(); pool=Pool(Cursor(ledger_rows=_ledger(rows,35),tables=subject.POST_F_AUTH_TABLES))
    report=subject.PostgreSQLEnrollmentNotificationAuditQualification(pool).verify(repository_root=_root())
    assert report.phase=='post-F' and report.database_migration_count==35
    assert set(subject.POST_F_AUTH_TABLES)<=set(report.nexilabs_auth_tables)
    assert report.enigma_catalogue_count==3 and report.enigma_catalogue_entry_count==279
    assert report.public_schema_privilege_count==report.public_table_privilege_count==report.public_routine_privilege_count==0
    assert report.enrollment_event_count==report.notification_delivery_count==report.audit_export_count==0


def test_post_f_tail_rejects_seeded_f_or_predecessor_operational_rows(monkeypatch) -> None:
    monkeypatch.setattr(subject,'PostgreSQLCredentialBundleQualification',FakePredecessor)
    rows=_rows()
    FakePredecessor.report=_predecessor_report(count=35,operational=0)
    with pytest.raises(EnrollmentNotificationAuditQualificationError,match='zero operational authority rows'):
        subject.PostgreSQLEnrollmentNotificationAuditQualification(
            Pool(Cursor(ledger_rows=_ledger(rows,35),tables=subject.POST_F_AUTH_TABLES,f_count=1))
        ).verify(repository_root=_root())
    FakePredecessor.report=_predecessor_report(count=35,operational=1)
    with pytest.raises(EnrollmentNotificationAuditQualificationError,match='zero operational authority rows'):
        subject.PostgreSQLEnrollmentNotificationAuditQualification(
            Pool(Cursor(ledger_rows=_ledger(rows,35),tables=subject.POST_F_AUTH_TABLES,f_count=0))
        ).verify(repository_root=_root())


def test_successor_era_allows_later_operational_data_without_weakening_f_structure(monkeypatch,tmp_path: Path) -> None:
    monkeypatch.setattr(subject,'PostgreSQLCredentialBundleQualification',FakePredecessor)
    root,rows=_successor_root(tmp_path)
    FakePredecessor.report=_predecessor_report(count=36,operational=2)
    tables=tuple(sorted((*subject.POST_F_AUTH_TABLES,'later_successor_table')))
    result=subject.PostgreSQLEnrollmentNotificationAuditQualification(
        Pool(Cursor(ledger_rows=_ledger(rows,36),tables=tables,f_count=3))
    ).verify(repository_root=root)
    assert result.database_migration_count==36 and result.enrollment_event_count==3
    assert result.principal_count==2


def test_missing_f_structure_wrong_database_and_tls_fail_closed(monkeypatch) -> None:
    monkeypatch.setattr(subject,'PostgreSQLCredentialBundleQualification',FakePredecessor)
    FakePredecessor.report=_predecessor_report(count=35,operational=0)
    rows=_rows()
    missing=next(iter(subject.REQUIRED_F_TRIGGERS))
    with pytest.raises(EnrollmentNotificationAuditQualificationError,match='missing F triggers'):
        subject.PostgreSQLEnrollmentNotificationAuditQualification(
            Pool(Cursor(ledger_rows=_ledger(rows,35),tables=subject.POST_F_AUTH_TABLES,missing=missing))
        ).verify(repository_root=_root())
    with pytest.raises(EnrollmentNotificationAuditQualificationError,match='wrong database target'):
        subject.PostgreSQLEnrollmentNotificationAuditQualification(
            Pool(Cursor(ledger_rows=_ledger(rows,35),tables=subject.POST_F_AUTH_TABLES,database='wrong'))
        ).verify(repository_root=_root())
    with pytest.raises(EnrollmentNotificationAuditQualificationError,match='TLS is not active'):
        subject.PostgreSQLEnrollmentNotificationAuditQualification(
            Pool(Cursor(ledger_rows=_ledger(rows,35),tables=subject.POST_F_AUTH_TABLES,tls=False))
        ).verify(repository_root=_root())
