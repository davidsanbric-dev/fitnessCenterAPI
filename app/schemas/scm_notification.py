from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.schemas import APIModel


# Gym-specific extension tied to adapted booking lifecycle events.
class NotificationResponse(APIModel):
    id: int
    title: str
    body: str
    type: str
    is_read: bool
    data: dict
    created_at: datetime


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
