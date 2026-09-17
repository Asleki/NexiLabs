"""Read-only CLI qualification for P006.UI.10.3."""
from __future__ import annotations

import argparse
from getpass import getpass
import json
import os

from backend.auth.first_admin_bootstrap.postgresql import (
    DatabaseSettings,
    psycopg_connect_factory,
)
from backend.auth.first_admin_bootstrap.qualification import qualify


def main() -> int:
    parser = argparse.ArgumentParser(description="Qualify P006.UI.10.3 PostgreSQL authority without writes.")
    parser.add_argument("--expect-admin-count", type=int, choices=(0, 1), default=None)
    args = parser.parse_args()
    password = os.environ.get("PGPASSWORD") or getpass("PostgreSQL password: ")
    settings = DatabaseSettings(
        host=os.environ.get("PGHOST", ""),
        port=int(os.environ.get("PGPORT", "5432")),
        database_name=os.environ.get("PGDATABASE", ""),
        username=os.environ.get("PGUSER", ""),
        password=password,
        ssl_mode=os.environ.get("PGSSLMODE", "require"),
    )
    receipt = qualify(
        psycopg_connect_factory(settings),
        expected_admin_count=args.expect_admin_count,
    )
    print(json.dumps(receipt.as_dict(), indent=2, sort_keys=True))
    return 0 if receipt.qualified else 2


if __name__ == "__main__":
    raise SystemExit(main())
