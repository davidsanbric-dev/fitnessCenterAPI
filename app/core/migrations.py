from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import settings


def apply_migrations() -> None:
	project_root = Path(__file__).resolve().parents[2]
	alembic_ini = project_root / "alembic.ini"
	if not alembic_ini.exists():
		return

	config = Config(str(alembic_ini))
	config.set_main_option("script_location", str(project_root / "alembic"))
	config.set_main_option("sqlalchemy.url", settings.database_url)
	command.upgrade(config, "head")
