"""Local Production authentication authority for P006.UI.10.3.

This server intentionally exposes no first-Admin bootstrap endpoint. Bootstrap is
terminal-only through ``python -m backend.auth.first_admin_bootstrap``.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from .contracts import AuthenticationRejected
from .postgresql import (
    DatabaseSettings,
    PostgreSQLConnectionPool,
    PostgreSQLFirstAdminAuthority,
    psycopg_connect_factory,
    psycopg_connection_check,
)
from .enigma import ProductionDeveloperEnigmaAuthority
from .service import ProductionAdminAuthenticationService


def settings_from_environment() -> DatabaseSettings:
    return DatabaseSettings(
        host=os.environ.get("PGHOST", ""),
        port=int(os.environ.get("PGPORT", "5432")),
        database_name=os.environ.get("PGDATABASE", ""),
        username=os.environ.get("PGUSER", ""),
        password=os.environ.get("PGPASSWORD", ""),
        ssl_mode=os.environ.get("PGSSLMODE", "require"),
    )


def build_service() -> ProductionAdminAuthenticationService:
    settings = settings_from_environment()
    pool = PostgreSQLConnectionPool(
        psycopg_connect_factory(settings),
        min_size=1,
        max_size=4,
        acquire_timeout_seconds=15.0,
        check=psycopg_connection_check,
    )
    # Fail startup rather than advertising a healthy local authority that cannot
    # reach PostgreSQL. Subsequent sequential auth operations reuse this warmed
    # TLS/RDS connection instead of reopening one for every repository method.
    pool.open()
    authority = PostgreSQLFirstAdminAuthority(
        pool.connection,
        database_name=settings.database_name,
        close=pool.close,
    )
    repository_root = Path(__file__).resolve().parents[3]
    catalogue_dir = Path(
        os.environ.get(
            "NEXILABS_PRIVATE_ENIGMA_DIR",
            str(repository_root / "development" / "auth" / "private" / "enigma"),
        )
    )
    developer_enigma = ProductionDeveloperEnigmaAuthority(catalogue_dir)
    return ProductionAdminAuthenticationService(
        authority=authority,
        developer_enigma=developer_enigma,
    )


class ProductionAuthHandler(BaseHTTPRequestHandler):
    service: ProductionAdminAuthenticationService

    def _origin_allowed(self) -> bool:
        origin = self.headers.get("Origin", "")
        if not origin:
            return True
        try:
            parsed = urlparse(origin)
        except ValueError:
            return False
        return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}

    def _cors(self) -> None:
        origin = self.headers.get("Origin")
        if origin and self._origin_allowed():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _send(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        try:
            self.send_response(status)
            self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            # The authority transaction may already have completed when a local
            # browser/client disappears. Do not turn that transport disconnect
            # into a noisy server-side traceback.
            self.close_connection = True

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > 16_384:
            raise AuthenticationRejected("invalid request body")
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise AuthenticationRejected("invalid request body")
        return value

    def _bearer(self) -> str:
        value = self.headers.get("Authorization", "")
        if not value.startswith("Bearer "):
            raise AuthenticationRejected("missing session token")
        token = value[7:].strip()
        if not token:
            raise AuthenticationRejected("missing session token")
        return token

    def do_OPTIONS(self):
        if not self._origin_allowed():
            self._send(403, {"ok": False, "error": "origin_rejected"})
            return
        self.send_response(204)
        self._cors()
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_GET(self):
        if not self._origin_allowed():
            self._send(403, {"ok": False, "error": "origin_rejected"})
            return
        try:
            if self.path == "/health":
                self._send(200, {"ok": True, "service": "nexilabs-production-auth", "bootstrapHttpExposed": False})
                return
            if self.path == "/auth/session":
                self._send(200, {"ok": True, "session": self.service.session(self._bearer())})
                return
            if self.path == "/admin/eligibility":
                self._send(200, {"ok": True, **self.service.eligibility(self._bearer()).as_dict()})
                return
            self._send(404, {"ok": False, "error": "not_found"})
        except AuthenticationRejected as exc:
            self._send(401, {"ok": False, "error": str(exc)})

    def do_POST(self):
        if not self._origin_allowed():
            self._send(403, {"ok": False, "error": "origin_rejected"})
            return
        try:
            if self.path == "/auth/developer/start":
                payload = self._read_json()
                result = self.service.start_developer(
                    username=str(payload.get("username", "")),
                    password=str(payload.get("password", "")),
                    runtime=str(payload.get("runtime", "")),
                )
                self._send(200, {"ok": True, **result})
                return
            if self.path == "/auth/developer/enigma":
                payload = self._read_json()
                session = self.service.verify_developer(
                    attempt_id=str(payload.get("attemptId", "")),
                    response=str(payload.get("response", "")),
                )
                self._send(200, {"ok": True, "session": session})
                return
            if self.path == "/auth/logout":
                self._send(200, {"ok": True, "revoked": self.service.logout(self._bearer())})
                return
            if self.path == "/admin/elevate":
                payload = self._read_json()
                result = self.service.start_admin_elevation(
                    self._bearer(),
                    admin_email=str(payload.get("adminEmail", "")),
                    admin_password=str(payload.get("adminPassword", "")),
                )
                self._send(200, {"ok": True, **result})
                return
            if self.path == "/admin/elevate/enigma":
                payload = self._read_json()
                elevation = self.service.verify_admin_elevation(
                    self._bearer(),
                    attempt_id=str(payload.get("attemptId", "")),
                    response=str(payload.get("response", "")),
                )
                self._send(200, {"ok": True, "elevation": elevation.as_dict()})
                return
            if self.path == "/admin/elevation/logout":
                payload = self._read_json()
                revoked = self.service.revoke_elevation(
                    self._bearer(),
                    str(payload.get("elevationId", "")),
                )
                self._send(200, {"ok": True, "revoked": revoked})
                return
            # Deliberately no /bootstrap-admin or equivalent route.
            self._send(404, {"ok": False, "error": "not_found"})
        except (AuthenticationRejected, json.JSONDecodeError) as exc:
            self._send(401, {"ok": False, "error": str(exc)})

    def log_message(self, format, *args):
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local NexiLabs Production authentication authority.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    ProductionAuthHandler.service = build_service()
    server = ThreadingHTTPServer((args.host, args.port), ProductionAuthHandler)
    print(f"NexiLabs production auth listening on http://{args.host}:{args.port}")
    print("First-Admin bootstrap HTTP endpoint: disabled")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        ProductionAuthHandler.service.authority.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
