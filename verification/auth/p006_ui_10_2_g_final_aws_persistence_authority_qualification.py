"""P006.UI.10.2.G final AWS persistence authority qualification CLI.

This command is strictly read-only. It creates no schema/data, no synthetic
principal, no OTP, no bundle/delivery, no mail, no object-storage artifact and
no public endpoint. Commit/tag creation remains an operator action after this
proof and the full repository regression are green.
"""
from __future__ import annotations

import argparse
from getpass import getpass
import json
import os
from pathlib import Path
import sys

_HERE = Path(__file__).resolve()
for _candidate in [_HERE.parent, *_HERE.parents]:
    if (_candidate / "backend").is_dir() and (_candidate / "database").is_dir():
        if str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
        break
else:
    raise RuntimeError("repository root not found for imports")

from backend.auth.final_persistence_authority_qualification import (
    G_TAG,
    PARENT_CLOSURE_TAG,
    FinalPersistenceAuthorityQualification,
)


def repository_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in [here.parent, *here.parents]:
        if (candidate / "database" / "migrations" / "migration_manifest.json").is_file():
            return candidate
    raise RuntimeError("repository root not found")


def _settings():
    from infrastructure.database.runtime.settings import DatabaseRuntimeSettings

    values = dict(os.environ)
    if not values.get("PGPASSWORD"):
        values["PGPASSWORD"] = getpass("PostgreSQL password: ")
    return DatabaseRuntimeSettings.from_mapping(values)


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _base_payload() -> dict[str, object]:
    return {
        "milestone": "P006.UI.10.2.G",
        "operation": "verify",
        "migrationWritePerformed": False,
        "databaseWritePerformed": False,
        "syntheticAuthorityCreated": False,
        "privateSourceRowsPrinted": False,
        "credentialMaterialPrinted": False,
        "mailRendered": False,
        "mailSent": False,
        "auditArtifactGenerated": False,
        "auditArtifactUploaded": False,
        "publicUrlActivated": False,
        "productionAuthenticationCutoverPerformed": False,
        "plannedGTag": G_TAG,
        "plannedParentClosureTag": PARENT_CLOSURE_TAG,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="P006.UI.10.2.G final AWS persistence authority qualification"
    )
    parser.add_argument("command", choices=("verify",))
    parser.add_argument("--repository-root", type=Path, default=None)
    parser.add_argument("--expected-database", default="npp_dev")
    args = parser.parse_args(argv)

    root = (args.repository_root or repository_root()).resolve()

    from infrastructure.database.runtime.pool import PostgreSQLPool

    pool = PostgreSQLPool(_settings())
    pool.open()
    try:
        report = FinalPersistenceAuthorityQualification(pool).verify(
            repository_root=root,
            expected_database=args.expected_database,
            require_source_lock=True,
        )
        payload = _base_payload()
        payload["closure"] = report.safe_summary()
        _emit(payload)
        return 0
    finally:
        pool.close()


if __name__ == "__main__":
    raise SystemExit(main())
