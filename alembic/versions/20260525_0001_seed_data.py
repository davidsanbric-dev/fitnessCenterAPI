from __future__ import annotations

import logging

from alembic import op

from app.core.seed import seed_reference_data

logger = logging.getLogger("alembic.runtime.migration")

revision = "20260525_0001"
down_revision = None
branch_labels = None
depends_on = None


def _provision_demo_firebase_accounts() -> None:
	"""Create/align the Firebase credentials for DEMO_USERS (best-effort).

	Mirrors the DB-side seed below so running the migration on its own
	(``alembic upgrade head`` / ``make seed``) also provisions the Firebase
	accounts -- no manual creation in the Firebase console needed. Idempotent:
	``seed_demo_users_from_settings`` creates each account if missing or aligns
	an existing one (resets password, marks verified). Never fails the migration:
	if Firebase is unconfigured (e.g. local dev) the step is simply skipped, and
	the app-startup path (see app.main.lifespan) provisions them when it runs.
	"""
	try:
		from scripts.set_and_verify_demo_users import seed_demo_users_from_settings

		seed_demo_users_from_settings()
	except Exception:
		logger.warning("Demo Firebase account provisioning skipped (see traceback).", exc_info=True)


def upgrade() -> None:
	# Idempotent per-company reference seed. The same routine also runs on every
	# application startup (see app.main.lifespan), so companies added to
	# DEMO_USERS after this migration has been applied are still seeded without
	# recreating the database.
	seed_reference_data(op.get_bind())
	# Provision the matching Firebase credentials so the standalone migration path
	# is self-sufficient. Idempotent and best-effort (see helper docstring).
	_provision_demo_firebase_accounts()


def downgrade() -> None:
	pass
