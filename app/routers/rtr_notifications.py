from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.scm_notification import (
    DeviceTokenCreate,
    DeviceTokenResponse,
    NotificationReadResponse,
    NotificationsListResponse,
    ReadAllResponse,
)
from app.services.svc_notification import NotificationService

router = APIRouter(tags=["notifications"])


# Gym-specific extension driven by adapted booking lifecycle events.
@router.get("/notifications", response_model=NotificationsListResponse)
def list_notifications(
    is_read: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return NotificationService(db).list_notifications(current_user.id, is_read, page, page_size)


# Gym extension for notification read-state update.
@router.put("/notifications/{notification_id}/read", response_model=NotificationReadResponse)
def mark_notification_read(notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return NotificationService(db).mark_read(current_user.id, notification_id)


# Gym extension for bulk notification read-state update.
@router.put("/notifications/read-all", response_model=ReadAllResponse)
def mark_all_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return NotificationService(db).mark_all_read(current_user.id)


# Gym extension for mobile push token registration.
@router.post("/devices", response_model=DeviceTokenResponse, status_code=status.HTTP_201_CREATED)
def register_device(payload: DeviceTokenCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return NotificationService(db).create_device(current_user.id, payload.token, payload.platform)


# Gym extension for push token deregistration.
@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    NotificationService(db).delete_device(current_user.id, device_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
