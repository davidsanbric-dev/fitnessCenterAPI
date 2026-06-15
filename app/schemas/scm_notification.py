from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from app.schemas import APIModel

if TYPE_CHECKING:
    from app.models import DeviceToken, Notification


# Gym-specific extension tied to adapted booking lifecycle events.
class NotificationResponse(APIModel):
    id: int
    title: str
    body: str
    type: str
    is_read: bool
    data: dict
    created_at: datetime

    @classmethod
    def from_model(cls, notification: Notification) -> NotificationResponse:
        return cls(
            id=notification.id,
            title=notification.title,
            body=notification.body,
            type=notification.type,
            is_read=notification.is_read,
            data=notification.data,
            created_at=notification.created_at,
        )


class NotificationsListResponse(APIModel):
    # Paginated envelope for adapted domain notifications.
    items: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int


class NotificationReadResponse(APIModel):
    # Read-state mutation response.
    id: int
    is_read: bool

    @classmethod
    def from_model(cls, notification: Notification) -> NotificationReadResponse:
        return cls(id=notification.id, is_read=notification.is_read)


class ReadAllResponse(APIModel):
    # Bulk read-state mutation response.
    updated_count: int


class DeviceTokenCreate(APIModel):
    # Gym mobile push registration payload.
    token: str
    platform: Literal["android", "ios"]


class DeviceTokenResponse(APIModel):
    # Stored push token projection.
    id: int
    token: str
    platform: str

    @classmethod
    def from_model(cls, device: DeviceToken) -> DeviceTokenResponse:
        return cls(id=device.id, token=device.token, platform=device.platform)
