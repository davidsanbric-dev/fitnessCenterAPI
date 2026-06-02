from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(
		env_file=os.getenv("ENV_FILE", ".env"),
		env_file_encoding="utf-8",
		case_sensitive=False,
		extra="ignore",
	)

	app_name: str = "Gym Scheduling API"
	api_v1_prefix: str = "/api/v1"
	debug: bool = False
	database_url: str = Field(...)
	access_token_expire_minutes: int = 30
	seed_data: bool = False
	demo_users: str = Field(default="")
	firebase_project_id: str | None = None
	firebase_service_account_path: str | None = None
	cors_origins: list[str] = Field(default_factory=list)
	locations: dict[str, str] = Field(
		default_factory=lambda: {
			"LOC001": "Downtown Gym",
			"LOC002": "North Branch",
		}
	)
	booking_statuses: dict[str, str] = Field(
		default_factory=lambda: {
			"PENDING": "Pending",
			"CONFIRMED": "Confirmed",
			"CANCELLED": "Cancelled",
			"COMPLETED": "Completed",
		}
	)

	@property
	def demo_user_credentials(self) -> list[tuple[str, str, str | None]]:
		"""Returns (role, email, password) tuples from demo_users JSON file.

		The single source of truth for demo users: drives both Firebase account
		setup and the backend user seed.
		"""
		if not self.demo_users:
			return []
		import json
		from pathlib import Path

		path = Path(self.demo_users)
		if not path.is_absolute():
			path = Path(__file__).resolve().parents[2] / path
		if not path.exists():
			return []
		data = json.loads(path.read_text())
		result: list[tuple[str, str, str | None]] = []
		for _group, entries in data.items():
			for role_name, credential in entries.items():
				email, _, password = credential.partition(":")
				email = email.strip().lower()
				if email:
					result.append((role_name, email, password.strip() or None))
		return result


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()


settings = get_settings()
