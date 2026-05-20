from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DeviceToken, Notification


# Gym-specific repository for notification/device token persistence tied to adapted booking events.
class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_notifications(self, user_id: int, is_read: bool | None = None, page: int = 1, page_size: int = 20) -> tuple[list[Notification], int, int]:
        statement = select(Notification).where(Notification.user_id == user_id)
        count_statement = select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
        unread_statement = select(func.count()).select_from(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False))
        if is_read is not None:
            statement = statement.where(Notification.is_read == is_read)
            count_statement = count_statement.where(Notification.is_read == is_read)
        total = int(self.db.scalar(count_statement) or 0)
        unread_count = int(self.db.scalar(unread_statement) or 0)
        items = self.db.scalars(statement.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        return list(items), total, unread_count

    def get_notification(self, user_id: int, notification_id: int) -> Notification | None:
        return self.db.scalar(select(Notification).where(Notification.user_id == user_id, Notification.id == notification_id))

    def mark_read(self, notification: Notification) -> Notification:
        notification.is_read = True
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def mark_all_read(self, user_id: int) -> int:
        items = self.db.scalars(select(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False))).all()
        for item in items:
            item.is_read = True
        self.db.commit()
        return len(items)

    def create_notification(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def create_device(self, device: DeviceToken) -> DeviceToken:
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return device

    def delete_device(self, user_id: int, device_id: int) -> bool:
        device = self.db.scalar(select(DeviceToken).where(DeviceToken.user_id == user_id, DeviceToken.id == device_id))
        if device is None:
            return False
        self.db.delete(device)
        self.db.commit()
        return True

    def unread_count(self, user_id: int) -> int:
        return int(self.db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False))) or 0)
