from __future__ import annotations

from alembic import op

revision = "20260604_0002"
down_revision = "20260525_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
	# Link a trainer record to its authenticated User (the "trainer" role demo
	# user). Guarded with IF NOT EXISTS so it is a no-op when ``create_all`` (run
	# at startup before migrations) has already provisioned the column on a fresh
	# database, while still adding it to pre-existing databases.
	op.execute(
		"ALTER TABLE trainers "
		"ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)"
	)
	op.execute(
		"CREATE INDEX IF NOT EXISTS ix_trainers_user_id ON trainers (user_id)"
	)


def downgrade() -> None:
	op.execute("DROP INDEX IF EXISTS ix_trainers_user_id")
	op.execute("ALTER TABLE trainers DROP COLUMN IF EXISTS user_id")
