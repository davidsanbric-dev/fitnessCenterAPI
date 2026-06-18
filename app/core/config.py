from __future__ import annotations

import os
import re
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.client_origin import ClientOrigin
from app.domain.enums import BookingStatus


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
	demo_users: str = Field(default="")
	# Filesystem directory where blog hero images are written. In production this
	# is a Dokploy bind volume mounted on the API service (env BLOG_IMAGES_PATH);
	# locally it defaults to a repo-relative folder.
	blog_images_path: str = Field(default="blog_images")
	# Filesystem directory where trainer/member profile images are written. Same
	# bind-volume model as ``blog_images_path`` (env PROFILE_IMAGES_PATH); locally
	# it defaults to a repo-relative folder.
	profile_images_path: str = Field(default="profile_images")
	firebase_project_id: str | None = None
	firebase_service_account_path: str | None = None
	cors_origins: list[str] = Field(default_factory=list)
	# Display labels for booking statuses, keyed off the domain vocabulary so the
	# set can never drift from BookingStatus (label is the title-cased value).
	booking_statuses: dict[str, str] = Field(
		default_factory=lambda: {status.value: status.value.title() for status in BookingStatus}
	)

	def _load_demo_users(self) -> dict[str, dict[str, str]]:
		if not self.demo_users:
			return {}
		import json
		from pathlib import Path

		path = Path(self.demo_users)
		if not path.is_absolute():
			path = Path(__file__).resolve().parents[2] / path
		if not path.exists():
			return {}
		return json.loads(path.read_text())

	@property
	def demo_companies(self) -> dict[str, list[tuple[str, str, str | None]]]:
		"""Returns {company_slug: [(role, email, password), ...]} from demo_users.

		Preserves the JSON top-level key (the targeted company) so the seed can
		provision an isolated, identically-shaped data environment per company.
		"""
		result: dict[str, list[tuple[str, str, str | None]]] = {}
		for group, entries in self._load_demo_users().items():
			members: list[tuple[str, str, str | None]] = []
			for role_name, credential in entries.items():
				email, _, password = credential.partition(":")
				email = email.strip().lower()
				if email:
					members.append((role_name, email, password.strip() or None))
			result[group] = members
		return result

	@property
	def demo_user_credentials(self) -> list[tuple[str, str, str | None]]:
		"""Returns (role, email, password) tuples from demo_users JSON file.

		The single source of truth for demo users: drives both Firebase account
		setup and the backend user seed. Flattens across companies (callers here
		only need the credential, not the company key).
		"""
		return [member for members in self.demo_companies.values() for member in members]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()


settings = get_settings()


# Permission sets keyed by the role name stored in the ``roles`` table. The
# role catalogue and the per-user assignment both live in the database (see
# the seed migration); this only maps a resolved role name to its grants.
PERMISSIONS_BY_ROLE: dict[str, list[str]] = {
	"admin": [
		"admin.dashboard.read",
		"bookings.read",
		"bookings.write",
		"schedule.read",
		"trainers.read",
		"disciplines.read",
		"memberships.read",
		"notifications.read",
	],
	"manager": [
		"admin.dashboard.read",
		"bookings.read",
		"schedule.read",
		"trainers.read",
		"disciplines.read",
		"memberships.read",
	],
	"member": ["member.home.read", "bookings.read", "bookings.write"],
	# The trainer signs into the web app but, unlike admin/manager, is scoped
	# to its own slots, bookings, profile and a home dashboard. The grants
	# below back those four web modules.
	"trainer": [
		"trainer.home.read",
		"schedule.read",
		"schedule.write",
		"bookings.read",
		"trainer.profile.read",
		"trainer.profile.write",
	],
}

STAFF_ROLES: frozenset[str] = frozenset({"admin", "manager"})

# Role buckets each deployed application is allowed to sign in as. The mobile
# app serves members; the web app serves staff (admin/manager).
ALLOWED_ROLES_BY_ORIGIN: dict[ClientOrigin, frozenset[str]] = {
	ClientOrigin.MOBILE: frozenset({"member"}),
	ClientOrigin.WEB: frozenset({"admin", "manager", "trainer"}),
}

# Blog hero-image upload contract. Allowed image content types -> file extension
# written to the bind volume (see ``blog_images_path``); the regex matches the
# ``data:<mime>;base64,<payload>`` data-URL the clients send.
ALLOWED_IMAGE_TYPES: dict[str, str] = {
	"image/png": ".png",
	"image/jpeg": ".jpg",
	"image/jpg": ".jpg",
	"image/webp": ".webp",
	"image/gif": ".gif",
}
DATA_URL_RE = re.compile(r"^data:(?P<mime>[\w/+.-]+);base64,(?P<payload>.+)$", re.DOTALL)
