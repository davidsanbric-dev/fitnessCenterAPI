"""Set up and verify Firebase demo accounts from the env file.

For each entry in ``DEMO_USERS`` (path to a JSON file with role→credential pairs,
the single source of truth for demo users) this **idempotently**:
  - creates the Firebase account with ``email_verified=True`` if it does not exist, or
  - aligns an existing account to the env state (sets the password, marks verified).

This lets showcase credentials handed out for evaluation sign in without the
email-verification step — while the backend's verification gate
(``verify_firebase_token``) stays fully enforced for everyone else.

Usage:
    # Seed every demo account declared in DEMO_USERS (default):
    python scripts/set_and_verify_demo_users.py

    # Or target specific emails ad hoc:
    python scripts/set_and_verify_demo_users.py demo@example.com --password 'Demo1234'

Requires the same Firebase service-account config the backend uses
(``FIREBASE_PROJECT_ID`` / ``FIREBASE_SERVICE_ACCOUNT_PATH`` in ``.env``).

Note: this only sets the Firebase credential side. The backend user records are
seeded from the same ``DEMO_USERS`` by the Alembic seed migration.
"""
from pathlib import Path
import argparse
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from firebase_admin import auth

from app.core.config import settings
from app.core.firebase_auth import _get_firebase_app


def ensure_account(email: str, password: str | None) -> None:
    """Create-or-align a single Firebase account to the desired demo state."""
    try:
        user = auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        if not password:
            print(f"  x {email}: missing and no password provided; skipping")
            return
        user = auth.create_user(email=email, password=password, email_verified=True)
        print(f"  + {email}: created and verified (uid={user.uid})")
        return

    updates: dict[str, object] = {}
    if not user.email_verified:
        updates["email_verified"] = True
    if password:
        # Keep the env file authoritative for demo credentials.
        updates["password"] = password
    if updates:
        auth.update_user(user.uid, **updates)
        print(f"  ~ {email}: updated {sorted(updates)} (uid={user.uid})")
    else:
        print(f"  . {email}: already aligned (uid={user.uid})")


def seed_demo_users_from_settings() -> None:
    """Set up every demo account declared in DEMO_USERS. Safe to call repeatedly."""
    credentials = settings.demo_user_credentials
    if not credentials:
        print("No demo credentials in DEMO_USERS; nothing to set up.")
        return
    _get_firebase_app()  # initialise using the backend's Firebase config
    print(f"Setting up {len(credentials)} demo account(s) from DEMO_USERS:")
    for _role, email, password in credentials:
        ensure_account(email, password)


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up and verify Firebase demo accounts.")
    parser.add_argument(
        "emails",
        nargs="*",
        help="Specific emails to set up (default: every account in ADMIN_EMAILS)",
    )
    parser.add_argument(
        "--password",
        metavar="PASSWORD",
        help="Password to set for the given emails (Firebase requires >= 6 chars)",
    )
    args = parser.parse_args()

    if not args.emails:
        seed_demo_users_from_settings()
        return

    _get_firebase_app()
    print(f"Setting up {len(args.emails)} account(s):")
    for email in args.emails:
        ensure_account(email.strip().lower(), args.password)


if __name__ == "__main__":
    main()
