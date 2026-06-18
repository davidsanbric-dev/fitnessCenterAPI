from __future__ import annotations

from app.schemas import APIModel


# Adapted from clinic GetStatic: StateAppointment -> booking_statuses.
class StaticConfigResponse(APIModel):
    booking_statuses: dict[str, str]
