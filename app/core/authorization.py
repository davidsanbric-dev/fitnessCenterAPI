from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException
from app.models import User
from app.services.svc_auth import AuthService


def ensure_admin_or_manager(db: Session, current_user: User) -> None:
    if not AuthService(db).is_admin_or_manager(current_user):
        raise ForbiddenException("Insufficient permissions for this resource")
