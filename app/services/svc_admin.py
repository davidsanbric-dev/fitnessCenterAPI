from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain import BookingStatus
from app.repositories.rps_admin import AdminRepository
from app.schemas.scm_admin import AdminHomeResponse, AdminKpiSummary


class AdminService:
    def __init__(self, db: Session):
        self.db = db
        self.admin_repository = AdminRepository(db)

    def get_home(self) -> AdminHomeResponse:
        repo = self.admin_repository
        return AdminHomeResponse(
            kpis=AdminKpiSummary(
                total_bookings=repo.count_bookings(),
                confirmed_bookings=repo.count_bookings_by_status(BookingStatus.CONFIRMED),
                cancelled_bookings=repo.count_bookings_by_status(BookingStatus.CANCELLED),
                upcoming_bookings=repo.count_upcoming_bookings(),
                total_memberships=repo.count_memberships(),
                unread_notifications=repo.count_unread_notifications(),
            ),
            status_breakdown=repo.booking_status_breakdown(),
        )
