from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Booking, MemberMembership, Notification


class AdminService:
    def __init__(self, db: Session):
        self.db = db

    def get_home(self) -> dict:
        total_bookings = int(self.db.scalar(select(func.count()).select_from(Booking)) or 0)
        confirmed_bookings = int(
            self.db.scalar(select(func.count()).select_from(Booking).where(Booking.booking_status == "CONFIRMED")) or 0
        )
        cancelled_bookings = int(
            self.db.scalar(select(func.count()).select_from(Booking).where(Booking.booking_status == "CANCELLED")) or 0
        )
        upcoming_bookings = int(
            self.db.scalar(select(func.count()).select_from(Booking).where(Booking.booking_datetime >= datetime.utcnow())) or 0
        )
        total_memberships = int(self.db.scalar(select(func.count()).select_from(MemberMembership)) or 0)
        unread_notifications = int(
            self.db.scalar(select(func.count()).select_from(Notification).where(Notification.is_read.is_(False))) or 0
        )

        rows = self.db.execute(
            select(Booking.booking_status, func.count()).group_by(Booking.booking_status)
        ).all()
        status_breakdown = {str(status): int(total) for status, total in rows}

        return {
            "kpis": {
                "total_bookings": total_bookings,
                "confirmed_bookings": confirmed_bookings,
                "cancelled_bookings": cancelled_bookings,
                "upcoming_bookings": upcoming_bookings,
                "total_memberships": total_memberships,
                "unread_notifications": unread_notifications,
            },
            "status_breakdown": status_breakdown,
        }
