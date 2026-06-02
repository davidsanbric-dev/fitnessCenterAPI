from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Location


# Adapted service from clinic GetStatic contract (branches + appointment states).
class StaticService:
    def __init__(self, db: Session):
        self.db = db

    def get_statics(self) -> dict:
        # Locations are read from the DB so they are scoped to the caller's
        # company (the session tenant filter is established by auth). Booking
        # statuses stay global config.
        locations = self.db.scalars(select(Location).order_by(Location.location_code)).all()
        return {
            "locations": {location.location_code: location.name for location in locations},
            "booking_statuses": settings.booking_statuses,
        }
