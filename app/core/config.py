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
	jwt_secret_key: str = Field(...)
	jwt_algorithm: str = "HS256"
	access_token_expire_minutes: int = 30
	refresh_token_expire_days: int = 7
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()


settings = get_settings()
