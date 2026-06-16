from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Location


class LocationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_default_location(self) -> Location | None:
        # Anchor for newly provisioned trainers: the company's first location.
        return self.db.scalar(select(Location).order_by(Location.id))

    def get_by_code(self, location_code: str) -> Location | None:
        return self.db.scalar(select(Location).where(Location.location_code == location_code))
