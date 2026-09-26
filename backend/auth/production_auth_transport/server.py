"""P006.UI.10.4 private same-origin Production-auth transport adapter.

The P006.UI.10.3 service remains the domain authority. This successor HTTP
boundary adds exact deployed-Origin admission and canonical ``/auth/admin/*``
routes while preserving the locked local routes for bounded localhost
compatibility. First-Admin bootstrap remains terminal-only.
"""
from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer
import os

from backend.auth.first_admin_bootstrap.server import (
    ProductionAuthHandler,
    build_service,
)

from .contracts import (
    canonical_route_for_locked_authority,
    origin_allowed,
    parse_allowed_origins,
)

_LOOPBACK_HOSTS = {"127.0.0.1", "::1"}


class ProductionAuthTransportHandler(ProductionAuthHandler):
    """Exact-Origin, canonical-route wrapper around the locked handler."""

    allowed_origins: tuple[str, ...] = parse_allowed_origins(None)

    def _origin_allowed(self) -> bool:
        return origin_allowed(self.headers.get("Origin"), self.allowed_origins)

    def _dispatch_with_canonical_route(self, method_name: str) -> None:
        original_path = self.path
        try:
            self.path = canonical_route_for_locked_authority(original_path)
            getattr(super(), method_name)()
        finally:
            self.path = original_path

    def do_GET(self):
        self._dispatch_with_canonical_route("do_GET")

    def do_POST(self):
        self._dispatch_with_canonical_route("do_POST")


def configured_allowed_origins() -> tuple[str, ...]:
    return parse_allowed_origins(os.environ.get("NEXILABS_PRODUCTION_AUTH_ALLOWED_ORIGINS"))


def _validated_loopback_host(host: str) -> str:
    value = str(host or "").strip()
    if value not in _LOOPBACK_HOSTS:
        raise ValueError("Production authentication must bind to an explicit loopback address")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the private P006.UI.10.4 NexiLabs Production-auth transport.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    host = _validated_loopback_host(args.host)
    if not 1 <= int(args.port) <= 65535:
        raise ValueError("port is invalid")

    ProductionAuthTransportHandler.allowed_origins = configured_allowed_origins()
    ProductionAuthTransportHandler.service = build_service()
    server = ThreadingHTTPServer((host, args.port), ProductionAuthTransportHandler)
    print(f"NexiLabs production auth listening privately on http://{host}:{args.port}")
    print("Public browser namespace: /auth/*")
    print("First-Admin bootstrap HTTP endpoint: disabled")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        ProductionAuthTransportHandler.service.authority.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
