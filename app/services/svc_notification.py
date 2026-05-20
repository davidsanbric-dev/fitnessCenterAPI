from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import DeviceToken, Notification
from app.repositories.rps_notification import NotificationRepository


# Gym-specific service for notification lifecycle based on adapted booking events.
class NotificationService:
    def __init__(self, db: Session):
        self.repository = NotificationRepository(db)

    def list_notifications(self, user_id: int, is_read: bool | None, page: int, page_size: int) -> dict:
        items, total, unread_count = self.repository.list_notifications(user_id, is_read, page, page_size)
        return {
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "body": item.body,
                    "type": item.type,
                    "is_read": item.is_read,
                    "data": item.data,
                    "created_at": item.created_at,
                }
                for item in items
            ],
            "total": total,
            "unread_count": unread_count,
            "page": page,
            "page_size": page_size,
        }

    def mark_read(self, user_id: int, notification_id: int) -> dict:
        notification = self.repository.get_notification(user_id, notification_id)
        if notification is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        notification = self.repository.mark_read(notification)
        return {"id": notification.id, "is_read": notification.is_read}

    def mark_all_read(self, user_id: int) -> dict:
        updated_count = self.repository.mark_all_read(user_id)
        return {"updated_count": updated_count}

    def create_device(self, user_id: int, token: str, platform: str) -> dict:
        device = self.repository.create_device(DeviceToken(user_id=user_id, token=token, platform=platform))
        return {"id": device.id, "token": device.token, "platform": device.platform}

    def delete_device(self, user_id: int, device_id: int) -> bool:
        if not self.repository.delete_device(user_id, device_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        return True

    def notify(self, user_id: int, title: str, body: str, notification_type: str, data: dict | None = None) -> None:
        self.repository.create_notification(
            Notification(
                user_id=user_id,
                title=title,
                body=body,
                type=notification_type,
                data=data or {},
            )
        )
