from __future__ import annotations

from pathlib import Path
import logging

from alembic import command
from alembic.config import Config

from app.core.config import settings

logger = logging.getLogger(__name__)


def apply_migrations() -> None:
	project_root = Path(__file__).resolve().parents[2]
	alembic_ini = project_root / "alembic.ini"
	if not alembic_ini.exists():
		logger.warning("Alembic config not found at %s; skipping migrations.", alembic_ini)
		return

	logger.info("Applying Alembic migrations from %s", alembic_ini)
	config = Config(str(alembic_ini))
	config.set_main_option("script_location", str(project_root / "alembic"))
	config.set_main_option("sqlalchemy.url", settings.database_url)
	try:
		command.upgrade(config, "head")
		logger.info("Alembic migrations applied successfully.")
	except Exception:
		logger.exception("Alembic migration failed.")
		raise
