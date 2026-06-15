from __future__ import annotations

from datetime import datetime

from app.core.exceptions import ConflictException, NotFoundException
from app.domain import enforce_booking_allowance
from app.models import Booking, Slot, User
from app.repositories.rps_booking import BookingRepository


class BookingGuards:
    """Preconditions for booking use cases.

    Each method asserts something that must hold before an operation proceeds --
    existence, ownership, uniqueness, availability, or eligibility -- raising the
    appropriate exception otherwise. Most consult persistence via the repository;
    eligibility reads the member's loaded entity graph and delegates the rule to
    the pure domain policy. Constructed with the same repository the service
    uses, so guards and service share one persistence context.
    """

    def __init__(self, repository: BookingRepository):
        self._repo = repository

    def require_booking_allowance(self, user: User) -> None:
        # Eligibility precondition for creating a booking: extract the member's
        # membership/plan facts from the ORM graph and delegate the rule (active
        # membership + monthly quota) to the domain policy.
        membership = user.membership
        plan = membership.plan if membership else None
        enforce_booking_allowance(
            membership_status=membership.status if membership else None,
            plan_name=plan.name if plan else None,
            monthly_limit=plan.max_bookings_per_month if plan else None,
            bookings_used=membership.bookings_used if membership else 0,
        )

    def require_existing(
        self, booking_id: int, *, user_id: int | None = None, trainer_id: int | None = None
    ) -> Booking:
        # Fetch a booking and assert it exists and (optionally) belongs to the
        # given member or trainer. Ownership mismatches return the same "not
        # found" as a missing id so callers can't probe for others' bookings.
        booking = self._repo.get_booking(booking_id)
        if booking is None:
            raise NotFoundException("Booking not found")
        if user_id is not None and booking.user_id != user_id:
            raise NotFoundException("Booking not found")
        if trainer_id is not None and booking.trainer_id != trainer_id:
            raise NotFoundException("Booking not found")
        return booking

    def require_existing_for_location(
        self, booking_id: int, location_code: str, *, user_id: int | None = None, trainer_id: int | None = None
    ) -> Booking:
        # As above, additionally scoping the booking to the active location so a
        # booking from another branch is treated as not found here.
        booking = self.require_existing(booking_id, user_id=user_id, trainer_id=trainer_id)
        if booking.location and booking.location.location_code != location_code:
            raise NotFoundException("Booking not found for location")
        return booking

    def require_no_existing_booking_at(self, user_id: int, booking_datetime: datetime) -> None:
        # A member may hold at most one booking per time slot, regardless of which
        # path (trainer or class) created it.
        if self._repo.user_has_booking_at(user_id, booking_datetime):
            raise ConflictException("You already have a booking at that time")

    def require_available_slot(self, slot: Slot | None) -> Slot:
        # The slot lookups return None when the requested slot doesn't exist or is
        # already taken; both surface to the member as the same conflict.
        if slot is None:
            raise ConflictException("Selected slot is not available")
        return slot
