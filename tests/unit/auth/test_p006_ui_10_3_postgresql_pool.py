from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

from backend.auth.first_admin_bootstrap.postgresql import (
    PostgreSQLConnectionPool,
    psycopg_connection_check,
)


class FakeConnection:
    def __init__(self, serial: int):
        self.serial = serial
        self.closed = False
        self.broken = False
        self.commits = 0
        self.rollbacks = 0
        self.close_calls = 0

    def commit(self):
        if self.closed or self.broken:
            raise RuntimeError("connection unavailable")
        self.commits += 1

    def rollback(self):
        if self.closed or self.broken:
            raise RuntimeError("connection unavailable")
        self.rollbacks += 1

    def close(self):
        self.close_calls += 1
        self.closed = True


class CountingFactory:
    def __init__(self):
        self.calls = 0
        self.connections: list[FakeConnection] = []

    def __call__(self):
        self.calls += 1
        connection = FakeConnection(self.calls)
        self.connections.append(connection)
        return connection


def test_pool_reuses_warmed_physical_connection_across_sequential_repository_boundaries():
    factory = CountingFactory()
    pool = PostgreSQLConnectionPool(factory, min_size=1, max_size=4)
    pool.open()

    with pool.connection() as first:
        first_serial = first.serial
    with pool.connection() as second:
        second_serial = second.serial
    with pool.connection() as third:
        third_serial = third.serial

    assert factory.calls == 1
    assert first_serial == second_serial == third_serial == 1
    assert factory.connections[0].commits == 3

    pool.close()
    assert factory.connections[0].closed is True


def test_pool_rolls_back_failed_repository_boundary_and_reuses_healthy_connection():
    factory = CountingFactory()
    pool = PostgreSQLConnectionPool(factory, min_size=1, max_size=2)
    pool.open()

    try:
        with pool.connection() as connection:
            raise ValueError("application rejection")
    except ValueError:
        pass

    with pool.connection() as reused:
        assert reused.serial == 1

    assert factory.calls == 1
    assert factory.connections[0].rollbacks == 1
    pool.close()


def test_pool_discards_broken_connection_and_replaces_it_on_next_lease():
    factory = CountingFactory()
    pool = PostgreSQLConnectionPool(factory, min_size=1, max_size=2)
    pool.open()

    try:
        with pool.connection() as connection:
            connection.broken = True
            raise ConnectionError("network lost")
    except ConnectionError:
        pass

    assert factory.connections[0].closed is True

    with pool.connection() as replacement:
        assert replacement.serial == 2

    assert factory.calls == 2
    pool.close()


def test_pool_never_shares_one_raw_connection_between_concurrent_leases():
    factory = CountingFactory()
    pool = PostgreSQLConnectionPool(factory, min_size=1, max_size=2)
    pool.open()
    barrier = Barrier(2)
    release = Event()

    def lease_serial():
        with pool.connection() as connection:
            barrier.wait(timeout=2)
            release.wait(timeout=2)
            return connection.serial

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(lease_serial) for _ in range(2)]
        barrier.wait if False else None
        release.set()
        serials = {future.result(timeout=3) for future in futures}

    assert serials == {1, 2}
    assert factory.calls == 2
    pool.close()


def test_pool_close_is_idempotent_and_rejects_future_leases():
    factory = CountingFactory()
    pool = PostgreSQLConnectionPool(factory, min_size=1, max_size=1)
    pool.open()
    pool.close()
    pool.close()

    assert factory.connections[0].close_calls == 1

    try:
        with pool.connection():
            pass
    except RuntimeError as exc:
        assert "closed" in str(exc)
    else:
        raise AssertionError("closed pool unexpectedly granted a connection")

class RuntimeCursor:
    def __init__(self):
        self._one = None
        self._all = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        compact = " ".join(str(sql).split())
        self._one = None
        self._all = []
        if "SELECT pa.principal_id, pa.username" in compact:
            self._one = (
                "principal:first",
                "alex",
                "nexadevs_developer",
                "ACTIVE",
                "developer-verifier",
                "enigma-profile:1",
            )
        elif "SELECT permission_code" in compact:
            self._all = [("NEXILABS.ADMIN.ELEVATE",)]
        elif "SELECT ece.catalogue_id" in compact:
            self._one = ("catalogue:3", "CAT", "DOG", "OWL", "a" * 64)
        elif "INSERT INTO nexilabs_auth.authority_audit_event" in compact:
            pass
        else:
            raise AssertionError(f"unexpected SQL in runtime-pool regression: {compact}")

    def fetchone(self):
        return self._one

    def fetchall(self):
        return list(self._all)


class RuntimeConnection(FakeConnection):
    def cursor(self):
        return RuntimeCursor()


class RuntimeFactory:
    def __init__(self):
        self.calls = 0
        self.connections: list[RuntimeConnection] = []

    def __call__(self):
        self.calls += 1
        connection = RuntimeConnection(self.calls)
        self.connections.append(connection)
        return connection


def test_layer1_start_repository_boundaries_reuse_one_physical_connection():
    from backend.auth.first_admin_bootstrap.postgresql import PostgreSQLFirstAdminAuthority

    factory = RuntimeFactory()
    pool = PostgreSQLConnectionPool(factory, min_size=1, max_size=4)
    pool.open()
    authority = PostgreSQLFirstAdminAuthority(
        pool.connection,
        database_name="npp_dev",
        close=pool.close,
    )

    principal = authority.principal_for_password_auth("alex")
    catalogue = authority.enigma_catalogue_row(
        profile_id="enigma-profile:1",
        word_length=3,
        day=15,
        period="DAY",
    )
    authority.append_runtime_audit(
        event_type="ENIGMA_CHALLENGE_ISSUED",
        outcome="ISSUED",
        actor_type="PRINCIPAL",
        actor_principal_id="principal:first",
        subject_type="AUTHENTICATION_ATTEMPT",
        subject_id="prod-auth:1",
        correlation_id="auth-correlation:1",
    )

    assert principal["principalId"] == "principal:first"
    assert catalogue["words"] == ("CAT", "DOG", "OWL")
    assert factory.calls == 1
    assert factory.connections[0].commits == 3

    authority.close()
    assert factory.connections[0].closed is True


class StaleConnection(FakeConnection):
    def __init__(self, serial: int):
        super().__init__(serial)
        self.stale = False
        self.checks = 0


class StaleFactory:
    def __init__(self):
        self.calls = 0
        self.connections: list[StaleConnection] = []

    def __call__(self):
        self.calls += 1
        connection = StaleConnection(self.calls)
        self.connections.append(connection)
        return connection


def _stale_connection_check(connection: StaleConnection) -> None:
    connection.checks += 1
    if connection.stale:
        raise ConnectionError("server closed idle connection")


def test_pool_replaces_idle_connection_that_looks_open_but_fails_live_check():
    factory = StaleFactory()
    pool = PostgreSQLConnectionPool(
        factory,
        min_size=1,
        max_size=2,
        check=_stale_connection_check,
    )
    pool.open()

    warmed = factory.connections[0]
    assert warmed.serial == 1
    assert warmed.closed is False
    assert warmed.broken is False

    # Model the exact live failure: psycopg's local flags still look healthy,
    # but the remote RDS/TLS peer has already closed the idle connection.
    warmed.stale = True

    with pool.connection() as replacement:
        assert replacement.serial == 2

    assert factory.calls == 2
    assert warmed.closed is True
    assert factory.connections[1].checks >= 1
    pool.close()


def test_pool_live_check_is_optional_for_existing_fake_and_offline_callers():
    factory = CountingFactory()
    pool = PostgreSQLConnectionPool(factory, min_size=1, max_size=1)
    pool.open()

    with pool.connection() as connection:
        assert connection.serial == 1

    assert factory.calls == 1
    pool.close()


class CheckCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        assert sql == "SELECT 1"
        self.connection.execute_calls += 1
        if self.connection.fail_probe:
            raise ConnectionError("server closed idle connection")

    def fetchone(self):
        return (1,)


class CheckConnection:
    def __init__(self, *, fail_probe=False):
        self.closed = False
        self.broken = False
        self.autocommit = False
        self.fail_probe = fail_probe
        self.execute_calls = 0

    def cursor(self):
        return CheckCursor(self)


def test_psycopg_connection_check_uses_one_autocommit_probe_and_restores_mode():
    connection = CheckConnection()

    psycopg_connection_check(connection)

    assert connection.execute_calls == 1
    assert connection.autocommit is False


def test_psycopg_connection_check_propagates_stale_socket_failure():
    connection = CheckConnection(fail_probe=True)

    try:
        psycopg_connection_check(connection)
    except ConnectionError as exc:
        assert "closed idle connection" in str(exc)
    else:
        raise AssertionError("stale connection check unexpectedly succeeded")

    assert connection.execute_calls == 1
    assert connection.autocommit is False
