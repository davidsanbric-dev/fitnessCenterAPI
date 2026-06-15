from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Location
from app.schemas.scm_static import StaticConfigResponse


class StaticService:
    def __init__(self, db: Session):
        self.db = db

    def get_statics(self) -> StaticConfigResponse:
        locations = self.db.scalars(select(Location).order_by(Location.location_code)).all()
        return StaticConfigResponse(
            locations={location.location_code: location.name for location in locations},
            booking_statuses=settings.booking_statuses,
        )
