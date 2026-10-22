"""Reset one demo tenant to a clean, freshly-dated state.

Deletes a single company's transactional state (bookings and slots) and then
re-runs the idempotent reference seed, which regenerates the rolling timetable
anchored to today. Catalog, users, profiles and memberships survive: only what
a reviewer's clicking produced is cleared.

This exists because the seeded timetable is anchored to `CURRENT_DATE` at seed
time, so a demo left alone for a month shows an empty availability screen.

Scoped to one company by slug and refuses to run without one, so it can never
fan out across tenants.

Usage:
    uv run python scripts/reset_demo_tenant.py --slug demo
    uv run python scripts/reset_demo_tenant.py --slug demo --yes   # no prompt
    uv run python scripts/reset_demo_tenant.py --slug demo --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlalchemy as sa  # noqa: E402


def _resolve_company(connection, slug: str) -> int | None:
    return connection.execute(
        sa.text("SELECT id FROM target_companies WHERE slug = :slug"),
        {"slug": slug},
    ).scalar()


def _summarize(connection, company_id: int) -> dict[str, int]:
    return {
        table: connection.execute(
            sa.text(f"SELECT count(*) FROM {table} WHERE company_id = :cid"),
            {"cid": company_id},
        ).scalar_one()
        for table in (
            "bookings",
            "slots",
            "member_memberships",
            "member_profiles",
            "disciplines",
            "class_types",
            "membership_plans",
            "trainers",
            "blogs",
        )
    }


# Catalog teardown in foreign-key order, children first. The association tables
# carry no company_id of their own, so they are scoped through whichever parent
# is company-scoped.
#
# Needed because the catalog seed is written to be additive: its guards are
# ON CONFLICT DO NOTHING and NOT EXISTS keyed on *names*. Re-seeding over a
# tenant that was provisioned with the older English catalog therefore does not
# rename anything -- it leaves 'Basic' in place and inserts 'Basico' alongside
# it. Clearing the catalog first is what makes the re-seed authoritative.
_CATALOG_PURGE_SQL: tuple[str, ...] = (
    "DELETE FROM bookings WHERE company_id = :cid",
    "DELETE FROM slots WHERE company_id = :cid",
    "DELETE FROM member_memberships WHERE company_id = :cid",
    "DELETE FROM membership_plan_categories WHERE membership_plan_id IN "
    "  (SELECT id FROM membership_plans WHERE company_id = :cid)",
    "DELETE FROM trainer_disciplines WHERE trainer_id IN "
    "  (SELECT id FROM trainers WHERE company_id = :cid)",
    "DELETE FROM trainer_membership_plans WHERE trainer_id IN "
    "  (SELECT id FROM trainers WHERE company_id = :cid)",
    "DELETE FROM class_types WHERE company_id = :cid",
    "DELETE FROM class_subcategories WHERE company_id = :cid",
    "DELETE FROM class_categories WHERE company_id = :cid",
    "DELETE FROM membership_plans WHERE company_id = :cid",
    "DELETE FROM disciplines WHERE company_id = :cid",
    "DELETE FROM trainers WHERE company_id = :cid",
    "DELETE FROM blogs WHERE company_id = :cid",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True, help="target company slug")
    parser.add_argument("--yes", action="store_true", help="skip confirmation")
    parser.add_argument(
        "--purge-catalog",
        action="store_true",
        help=(
            "also delete the tenant's catalog (disciplines, plans, trainers, "
            "class types, blogs) so the re-seed rebuilds it from scratch"
        ),
    )
    parser.add_argument(
        "--refresh-profiles",
        action="store_true",
        help=(
            "also delete the tenant's member profiles so the re-seed rebuilds "
            "them from _DEMO_MEMBER_PROFILES, discarding any edits made in the "
            "app (user accounts and logins are kept)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without writing",
    )
    args = parser.parse_args()

    from app.core.config import settings
    from app.core.seed import seed_reference_data

    url = os.environ.get("DATABASE_URL") or settings.database_url
    engine = sa.create_engine(url)

    # Mask credentials when echoing the target back.
    shown = url
    if "@" in shown:
        shown = shown.split("@", 1)[0].rsplit(":", 1)[0] + ":***@" + shown.split("@", 1)[1]
    print(f"database: {shown}")
    print(f"tenant:   {args.slug}")

    with engine.connect() as connection:
        company_id = _resolve_company(connection, args.slug)
        if company_id is None:
            known = connection.execute(
                sa.text("SELECT slug FROM target_companies ORDER BY slug")
            ).scalars().all()
            print(
                f"\nNo company with slug {args.slug!r}. Known slugs: {known or '(none)'}",
                file=sys.stderr,
            )
            return 1
        before = _summarize(connection, company_id)

    print(f"\ncurrent state (company_id={company_id}):")
    for table, count in before.items():
        print(f"  {table:<20} {count}")

    if args.purge_catalog:
        print(
            "\nthis will DELETE that tenant's bookings, slots, memberships AND "
            "its whole catalog (disciplines, plans, trainers, class types, "
            "blogs), then re-seed all of it from the current code."
        )
        print(
            "member profiles are rebuilt too."
            if args.refresh_profiles
            else "users and member profiles are left in place."
        )
    elif args.refresh_profiles:
        print(
            "\nthis will DELETE that tenant's bookings, slots and member "
            "profiles, then re-seed them. Profiles come back from the seeded "
            "persona, so edits made in the app are discarded."
        )
        print("user accounts and logins are kept.")
    else:
        print(
            "\nthis will DELETE that tenant's bookings and slots, reset its "
            "booking counters, and re-seed the timetable anchored to today."
        )
        print("catalog, users, profiles and memberships are left in place.")

    if args.dry_run:
        print("\ndry run: nothing written.")
        return 0

    if not args.yes:
        answer = input(f"\nproceed for tenant {args.slug!r}? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("aborted.")
            return 1

    with engine.begin() as connection:
        if args.purge_catalog:
            total = 0
            for statement in _CATALOG_PURGE_SQL:
                total += connection.execute(
                    sa.text(statement), {"cid": company_id}
                ).rowcount
            print(f"\npurged {total} catalog and transactional rows")
        else:
            # Bookings reference slots, so they go first.
            deleted_bookings = connection.execute(
                sa.text("DELETE FROM bookings WHERE company_id = :cid"),
                {"cid": company_id},
            ).rowcount
            deleted_slots = connection.execute(
                sa.text("DELETE FROM slots WHERE company_id = :cid"),
                {"cid": company_id},
            ).rowcount
            connection.execute(
                sa.text(
                    "UPDATE member_memberships SET bookings_used = 0 "
                    "WHERE company_id = :cid"
                ),
                {"cid": company_id},
            )
            print(f"\ndeleted {deleted_bookings} bookings, {deleted_slots} slots")

        # Nothing references member_profiles, so dropping the rows is safe; the
        # seed recreates them from the persona. This is the forced counterpart
        # to the seed's own backfill, which only heals a profile still carrying
        # the generated placeholder and deliberately leaves edits alone.
        if args.refresh_profiles:
            dropped = connection.execute(
                sa.text("DELETE FROM member_profiles WHERE company_id = :cid"),
                {"cid": company_id},
            ).rowcount
            print(f"dropped {dropped} member profiles for rebuild")

    # Re-seed in its own transaction: the seed takes an advisory lock for the
    # life of the transaction, and holding it across the deletes above would
    # serialise longer than necessary.
    print("re-seeding reference data...")
    with engine.begin() as connection:
        seed_reference_data(connection)

    with engine.connect() as connection:
        after = _summarize(connection, company_id)

    print("\nnew state:")
    for table, count in after.items():
        print(f"  {table:<20} {count}")

    if not after["slots"]:
        print(
            "\nWARNING: no slots were regenerated. Check that the catalog seed "
            "still matches this tenant.",
            file=sys.stderr,
        )
        return 1

    print(f"\nOK: tenant {args.slug!r} reset.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
