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
	admin_emails: list[str] = Field(default_factory=list)
	manager_emails: list[str] = Field(default_factory=list)
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
	def admin_credentials(self) -> list[tuple[str, str | None]]:
		"""Demo admin accounts from ADMIN_EMAILS, each entry as 'email[:password]'.

		The single source of truth for demo users: drives both Firebase account
		setup and the backend user seed. Password is optional (None when absent).
		"""
		return _parse_credentials(self.admin_emails)

	@property
	def admin_email_addresses(self) -> list[str]:
		"""Bare admin emails (password stripped) for role/permission resolution."""
		return [email for email, _ in self.admin_credentials]

	@property
	def manager_email_addresses(self) -> list[str]:
		"""Bare manager emails (password stripped) for role/permission resolution."""
		return [email for email, _ in _parse_credentials(self.manager_emails)]


def _parse_credentials(items: list[str]) -> list[tuple[str, str | None]]:
	credentials: list[tuple[str, str | None]] = []
	for item in items:
		email, _, password = item.partition(":")
		email = email.strip().lower()
		if not email:
			continue
		credentials.append((email, password.strip() or None))
	return credentials


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()


settings = get_settings()
