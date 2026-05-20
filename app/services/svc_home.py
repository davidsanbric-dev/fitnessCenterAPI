from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ClassCategory, User
from app.repositories.rps_booking import BookingRepository
from app.repositories.rps_notification import NotificationRepository


# Adapted home aggregation service composing clinic-like agenda/static concepts for gym dashboard.
class HomeService:
    def __init__(self, db: Session):
        self.db = db
        self.booking_repository = BookingRepository(db)
        self.notification_repository = NotificationRepository(db)

    def get_home(self, user: User) -> dict:
        upcoming = self.booking_repository.list_upcoming(user.id, limit=5)
        categories = self.db.scalars(select(ClassCategory).order_by(ClassCategory.name).limit(3)).all()
        membership_plan = user.membership.plan.name if user.membership and user.membership.plan else None
        return {
            "member": {
                "first_name": user.profile.first_name,
                "membership_plan": membership_plan,
            },
            "upcoming_bookings": [
                {
                    "id": item.id,
                    "date": item.booking_datetime.date().isoformat(),
                    "start_time": item.booking_datetime.time().strftime("%H:%M"),
                    "class_type": item.class_type.name if item.class_type else None,
                    "trainer": item.trainer.full_name if item.trainer else None,
                }
                for item in upcoming
            ],
            "featured_classes": [
                {
                    "id": category.id,
                    "name": category.name,
                    "description": f"Featured classes in {category.name}",
                    "icon_url": category.icon_url,
                }
                for category in categories
            ],
            "unread_notifications_count": self.notification_repository.unread_count(user.id),
            "quick_actions": [
                {"label": "Book a Class", "route": "/class-categories"},
                {"label": "Find a Trainer", "route": "/trainers"},
            ],
        }
