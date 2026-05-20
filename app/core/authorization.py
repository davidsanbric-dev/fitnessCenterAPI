from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User
from app.services.svc_auth import AuthService


def ensure_admin_or_manager(db: Session, current_user: User) -> None:
    if not AuthService(db).is_admin_or_manager(current_user.email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions for this resource")
