from pathlib import Path


def test_production_server_has_no_bootstrap_http_route():
    path = Path(__file__).resolve().parents[3] / "backend" / "auth" / "first_admin_bootstrap" / "server.py"
    source = path.read_text(encoding="utf-8")
    assert "Deliberately no /bootstrap-admin" in source
    assert 'self.path == "/bootstrap-admin"' not in source


def test_cli_accepts_no_password_or_otp_arguments():
    path = Path(__file__).resolve().parents[3] / "backend" / "auth" / "first_admin_bootstrap" / "cli.py"
    source = path.read_text(encoding="utf-8")
    assert "--password" not in source
    assert "--otp" not in source
    assert "getpass(" in source


def test_production_server_uses_warmed_bounded_postgresql_pool_and_closes_it():
    path = Path(__file__).resolve().parents[3] / "backend" / "auth" / "first_admin_bootstrap" / "server.py"
    source = path.read_text(encoding="utf-8")
    assert "PostgreSQLConnectionPool(" in source
    assert "min_size=1" in source
    assert "max_size=4" in source
    assert "pool.open()" in source
    assert "close=pool.close" in source
    assert "service.authority.close()" in source


def test_production_server_treats_disconnected_client_as_transport_event():
    path = Path(__file__).resolve().parents[3] / "backend" / "auth" / "first_admin_bootstrap" / "server.py"
    source = path.read_text(encoding="utf-8")
    assert "except (BrokenPipeError, ConnectionResetError):" in source
