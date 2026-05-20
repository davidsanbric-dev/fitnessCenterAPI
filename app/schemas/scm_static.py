from __future__ import annotations

from app.schemas import APIModel


# Adapted from clinic GetStatic: Branches -> locations, StateAppointment -> booking_statuses.
class StaticConfigResponse(APIModel):
    locations: dict[str, str]
    booking_statuses: dict[str, str]
