from __future__ import annotations

from app.core.config import settings


# Adapted service from clinic GetStatic contract (branches + appointment states).
class StaticService:
    def get_statics(self) -> dict:
        return {
            "locations": settings.locations,
            "booking_statuses": settings.booking_statuses,
        }
