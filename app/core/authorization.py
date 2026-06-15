from __future__ import annotations

from app.core.config import PERMISSIONS_BY_ROLE, STAFF_ROLES
from app.core.exceptions import ForbiddenException
from app.models import User


def resolve_role_permissions(user: User) -> tuple[str, list[str]]:
    # Role is sourced from the database (``users.role_id`` -> ``roles.name``), not
    # from config. Users without an assigned role (e.g. self-registered members)
    # default to "member".
    role_name = (user.role.name if user.role else "") or "member"
    permissions = PERMISSIONS_BY_ROLE.get(role_name, PERMISSIONS_BY_ROLE["member"])
    return role_name, permissions


def is_admin_or_manager(user: User) -> bool:
    role, _ = resolve_role_permissions(user)
    return role in STAFF_ROLES


def ensure_admin_or_manager(current_user: User) -> None:
    if not is_admin_or_manager(current_user):
        raise ForbiddenException("Insufficient permissions for this resource")
