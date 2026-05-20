from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    MemberMembership,
    MemberProfile,
    RefreshToken,
    User,
)


# Adapted data-access layer for clinic Patient/Register/GetPatient semantics -> gym User/MemberProfile persistence.
class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        statement = (
            select(User)
            .options(
                selectinload(User.profile),
                selectinload(User.membership).selectinload(MemberMembership.plan),
            )
            .where(User.email == email)
        )
        return self.db.scalar(statement)

    def get_by_id(self, user_id: int) -> User | None:
        statement = (
            select(User)
            .options(
                selectinload(User.profile),
                selectinload(User.membership).selectinload(MemberMembership.plan),
            )
            .where(User.id == user_id)
        )
        return self.db.scalar(statement)

    def create_user(self, user: User, profile: MemberProfile) -> User:
        # Adapted from clinic RegisterPatient write contract.
        self.db.add(user)
        self.db.flush()
        profile.user_id = user.id
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(user)
        return self.get_by_id(user.id) or user

    def update_profile(self, user: User, payload: dict) -> User:
        # Adapted from clinic patient profile mutation behavior.
        for field, value in payload.items():
            setattr(user.profile, field, value)
        self.db.commit()
        self.db.refresh(user)
        return self.get_by_id(user.id) or user

    def update_password(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        self.db.commit()

    def store_refresh_token(self, user_id: int, token: str, expires_at: datetime) -> RefreshToken:
        record = RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_refresh_token(self, token: str) -> RefreshToken | None:
        return self.db.scalar(select(RefreshToken).where(RefreshToken.token == token))

    def revoke_refresh_token(self, token: str) -> None:
        record = self.get_refresh_token(token)
        if record is not None:
            record.is_revoked = True
            self.db.commit()

    def revoke_user_refresh_tokens(self, user_id: int) -> None:
        records = self.db.scalars(select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.is_revoked.is_(False))).all()
        for record in records:
            record.is_revoked = True
        self.db.commit()

    def count_user_bookings_for_month(self, user_id: int, year: int, month: int) -> int:
        statement = select(func.count()).select_from(User).join(User.bookings).where(
            User.id == user_id,
            func.extract("year", User.bookings.property.entity.class_.booking_datetime) == year,
            func.extract("month", User.bookings.property.entity.class_.booking_datetime) == month,
        )
        return int(self.db.scalar(statement) or 0)
