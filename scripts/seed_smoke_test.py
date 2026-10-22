"""Seed smoke test: provision a throwaway database and assert the result.

Runs the real `seed_reference_data` against a scratch database so catalog
changes can be verified without touching the dev database or anything
deployed. Also re-runs the seed a second time to prove idempotency, which
matters because the whole seed is a single transaction: a statement that is
not idempotent silently discards every insert before it on the second run.

Usage:
    DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:55432/gym_schedule_seedtest \\
        uv run python scripts/seed_smoke_test.py
"""

from __future__ import annotations

import os
import sys

# Import the app package from the repo root regardless of cwd.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlalchemy as sa  # noqa: E402

from app.core.config import settings  # noqa: E402


def _counts(connection, company_slug: str) -> dict[str, int]:
    cid = connection.execute(
        sa.text("SELECT id FROM target_companies WHERE slug = :slug"),
        {"slug": company_slug},
    ).scalar()
    if cid is None:
        return {}

    tables = (
        "disciplines",
        "class_categories",
        "class_subcategories",
        "class_types",
        "membership_plans",
        "trainers",
        "slots",
        "blogs",
        "users",
        "member_profiles",
        "member_memberships",
        "bookings",
    )
    out: dict[str, int] = {}
    for table in tables:
        out[table] = connection.execute(
            sa.text(f"SELECT count(*) FROM {table} WHERE company_id = :cid"),
            {"cid": cid},
        ).scalar_one()
    return out


def main() -> int:
    url = os.environ.get("DATABASE_URL") or settings.database_url
    if "seedtest" not in url:
        print(
            f"Refusing to run against {url!r}: the target database name must "
            "contain 'seedtest' so this can never hit a real environment.",
            file=sys.stderr,
        )
        return 2

    from app.core.db import Base
    from app.core.seed import seed_reference_data

    engine = sa.create_engine(url)

    print(f"target: {url}")
    print("dropping and recreating schema...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    print("seeding (pass 1)...")
    with engine.begin() as connection:
        seed_reference_data(connection)

    slugs = list(settings.demo_companies.keys())
    if not slugs:
        print("no demo companies configured; check DEMO_USERS", file=sys.stderr)
        return 1

    with engine.connect() as connection:
        first = {slug: _counts(connection, slug) for slug in slugs}

    print("seeding (pass 2, idempotency check)...")
    with engine.begin() as connection:
        seed_reference_data(connection)

    with engine.connect() as connection:
        second = {slug: _counts(connection, slug) for slug in slugs}

    failed = False
    for slug in slugs:
        print(f"\n=== {slug} ===")
        for table, count in sorted(first[slug].items()):
            again = second[slug].get(table, -1)
            drifted = again != count
            flag = "  <-- DRIFT" if drifted else ""
            failed = failed or drifted
            print(f"  {table:<22} {count:>4}{(' -> ' + str(again)) if drifted else ''}{flag}")
        if not first[slug].get("users"):
            print("  WARNING: no users seeded for this company")

    if failed:
        print("\nFAIL: row counts changed on the second seed; something is not idempotent.")
        return 1

    print("\nOK: seed is idempotent across two runs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
