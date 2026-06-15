from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.core.push import send_push_to_tokens
from app.models import Notification
from app.repositories.rps_notification import NotificationRepository
from app.schemas.scm_notification import (
    DeviceTokenResponse,
    NotificationReadResponse,
    NotificationResponse,
    NotificationsListResponse,
    ReadAllResponse,
)
from app.services.svc_common import get_or_404

logger = logging.getLogger("uvicorn.error")


class NotificationService:
    def __init__(self, db: Session):
        self.repository = NotificationRepository(db)

    def list_notifications(self, user_id: int, is_read: bool | None, page: int, page_size: int) -> NotificationsListResponse:
        items, total, unread_count = self.repository.list_notifications(user_id, is_read, page, page_size)
        return NotificationsListResponse(
            items=[NotificationResponse.from_model(item) for item in items],
            total=total,
            unread_count=unread_count,
            page=page,
            page_size=page_size,
        )

    def mark_read(self, user_id: int, notification_id: int) -> NotificationReadResponse:
        notification = get_or_404(self.repository.get_notification(user_id, notification_id), "Notification not found")
        notification = self.repository.mark_read(notification)
        return NotificationReadResponse.from_model(notification)

    def mark_all_read(self, user_id: int) -> ReadAllResponse:
        return ReadAllResponse(updated_count=self.repository.mark_all_read(user_id))

    def create_device(self, user_id: int, token: str, platform: str) -> DeviceTokenResponse:
        device = self.repository.upsert_device(user_id, token, platform)
        if device is None:
            return DeviceTokenResponse(id=0, token=token, platform=platform)
        return DeviceTokenResponse.from_model(device)

    def delete_device(self, user_id: int, device_id: int) -> bool:
        if not self.repository.delete_device(user_id, device_id):
            raise NotFoundException("Device not found")
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

    def notify_many(self, user_ids: list[int], title: str, body: str, notification_type: str, data: dict | None = None) -> None:
        for user_id in dict.fromkeys(user_ids):
            self.notify(user_id, title, body, notification_type, data)

    def broadcast_push(self, title: str, body: str, data: dict | None = None) -> None:
        try:
            tokens = [device.token for device in self.repository.list_device_tokens()]
            if not tokens:
                return
            invalid = send_push_to_tokens(tokens, title=title, body=body, data=data)
            if invalid:
                self.repository.prune_tokens(invalid)
        except Exception:
            logger.warning("Failed to dispatch push notification", exc_info=True)
