from __future__ import annotations

from app.schemas import APIModel


class AdminKpiSummary(APIModel):
    total_bookings: int
    confirmed_bookings: int
    cancelled_bookings: int
    upcoming_bookings: int
    total_memberships: int
    unread_notifications: int


class AdminHomeResponse(APIModel):
    kpis: AdminKpiSummary
    status_breakdown: dict[str, int]
