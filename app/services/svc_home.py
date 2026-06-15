from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ClassCategory, User
from app.repositories.rps_booking import BookingRepository
from app.repositories.rps_notification import NotificationRepository
from app.schemas.scm_home import HomeResponse


class HomeService:
    def __init__(self, db: Session):
        self.db = db
        self.booking_repository = BookingRepository(db)
        self.notification_repository = NotificationRepository(db)

    def get_home(self, user: User) -> HomeResponse:
        upcoming = self.booking_repository.list_upcoming(user.id, limit=5)
        categories = self.db.scalars(select(ClassCategory).order_by(ClassCategory.name).limit(3)).all()
        unread_count = self.notification_repository.unread_count(user.id)
        return HomeResponse.build(user, upcoming, categories, unread_count)
