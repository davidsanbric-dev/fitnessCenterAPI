from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Booking, MemberMembership, Notification


# Adapted repository backing the gym admin dashboard KPIs/aggregations
# (clinic management-overview contracts repurposed for booking metrics).
class AdminRepository:
    def __init__(self, db: Session):
        self.db = db

    def count_bookings(self) -> int:
        return int(self.db.scalar(select(func.count()).select_from(Booking)) or 0)

    def count_bookings_by_status(self, booking_status: str) -> int:
        return int(
            self.db.scalar(
                select(func.count()).select_from(Booking).where(Booking.booking_status == booking_status)
            )
            or 0
        )

    def count_upcoming_bookings(self) -> int:
        return int(
            self.db.scalar(
                select(func.count()).select_from(Booking).where(Booking.booking_datetime >= datetime.utcnow())
            )
            or 0
        )

    def count_memberships(self) -> int:
        return int(self.db.scalar(select(func.count()).select_from(MemberMembership)) or 0)

    def count_unread_notifications(self) -> int:
        return int(
            self.db.scalar(
                select(func.count()).select_from(Notification).where(Notification.is_read.is_(False))
            )
            or 0
        )

    def booking_status_breakdown(self) -> dict[str, int]:
        rows = self.db.execute(
            select(Booking.booking_status, func.count()).group_by(Booking.booking_status)
        ).all()
        return {str(status): int(total) for status, total in rows}
