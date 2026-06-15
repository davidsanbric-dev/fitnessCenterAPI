from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.models import User
from app.repositories.rps_user import UserRepository


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = UserRepository(db)

    def create_user(self, email: str, role_id: int, is_active: bool = True) -> User:
        user = User(email=email, role_id=role_id, is_active=is_active)
        self.db.add(user)
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictException("Email already registered") from exc
        return user
