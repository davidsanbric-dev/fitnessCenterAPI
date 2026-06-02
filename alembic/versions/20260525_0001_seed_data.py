from __future__ import annotations

from alembic import op

from app.core.seed import seed_reference_data

revision = "20260525_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
	# Idempotent per-company reference seed. The same routine also runs on every
	# application startup (see app.main.lifespan), so companies added to
	# DEMO_USERS after this migration has been applied are still seeded without
	# recreating the database.
	seed_reference_data(op.get_bind())


def downgrade() -> None:
	pass
