from __future__ import annotations

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.models import User
from app.repositories.rps_user import UserRepository


class AuthGuards:
    """Preconditions for auth/profile use cases.

    Repository-backed checks that gate registration, profile access, and login.
    Each returns the validated user or raises. Constructed with the same user
    repository the service uses, so guards and service share one persistence
    context.
    """

    def __init__(self, repository: UserRepository):
        self._repo = repository

    def require_email_available(self, email: str) -> None:
        # Email uniqueness is global, so this must run before the tenant is set
        # (otherwise it would only see the resolved company's users).
        if self._repo.get_by_email(email):
            raise ConflictException("Email already registered")

    def require_user_with_profile(self, user_id: int) -> User:
        # Profile reads/writes require both the user and its member profile to
        # exist; a user without a profile is treated as not found.
        user = self._repo.get_by_id(user_id)
        if user is None or user.profile is None:
            raise NotFoundException("User not found")
        return user

    def require_provisioned_user(self, email: str) -> User:
        # A Firebase-authenticated identity must already exist in the backend; we
        # never auto-provision on login.
        user = self._repo.get_by_email(email)
        if user is None:
            raise ForbiddenException("User authenticated with Firebase but not provisioned in backend")
        return user
