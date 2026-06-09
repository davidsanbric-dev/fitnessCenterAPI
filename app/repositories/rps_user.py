from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    MemberMembership,
    MemberProfile,
    Role,
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
                selectinload(User.role),
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
                selectinload(User.role),
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

    def list_staff_user_ids(self, role_names: tuple[str, ...] = ("admin", "manager")) -> list[int]:
        # Web-app staff recipients for member-driven booking events. Auto-scoped to
        # the active company by the tenant session filter (User is tenant-scoped);
        # Role is the global catalogue, so it is matched by name only.
        statement = (
            select(User.id)
            .join(User.role)
            .where(Role.name.in_(role_names), User.is_active.is_(True))
        )
        return [int(uid) for uid in self.db.scalars(statement).all()]

    def count_user_bookings_for_month(self, user_id: int, year: int, month: int) -> int:
        statement = select(func.count()).select_from(User).join(User.bookings).where(
            User.id == user_id,
            func.extract("year", User.bookings.property.entity.class_.booking_datetime) == year,
            func.extract("month", User.bookings.property.entity.class_.booking_datetime) == month,
        )
        return int(self.db.scalar(statement) or 0)
