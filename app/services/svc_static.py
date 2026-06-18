from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.scm_static import StaticConfigResponse


class StaticService:
    def __init__(self, db: Session):
        self.db = db

    def get_statics(self) -> StaticConfigResponse:
        return StaticConfigResponse(
            booking_statuses=settings.booking_statuses,
        )
