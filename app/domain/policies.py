from __future__ import annotations

from collections.abc import Collection
from datetime import datetime, timedelta

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
)
from app.domain.enums import BookingStatus, MembershipStatus

# A booking may only be cancelled up to this long before it starts.
CANCELLATION_WINDOW = timedelta(hours=2)


def enforce_booking_allowance(
    *,
    membership_status: str | None,
    plan_name: str | None,
    monthly_limit: int | None,
    bookings_used: int,
) -> None:
    # Gate booking creation on the member's subscribed plan: an active membership
    # is required, and every booking -- regardless of class or session type --
    # counts against the plan's monthly quota. Plans differ only by that quota
    # (e.g. Basic 8, Premium 30, VIP 50). Pure rule over primitives so it is
    # testable without constructing membership/plan rows.
    if membership_status != MembershipStatus.ACTIVE or plan_name is None:
        raise ForbiddenException("An active membership is required to book sessions")
    if monthly_limit and bookings_used >= monthly_limit:
        raise ConflictException(f"You have reached your monthly booking limit for the {plan_name} plan")


def require_notes_for_completion(booking_status: str, notes: str | None) -> None:
    # Completing a session must carry a feedback note (surfaced to the member in
    # their Training History). Enforced for every caller -- trainer panel, admin
    # panel, or member app.
    if booking_status == BookingStatus.COMPLETED and not (notes or "").strip():
        raise BadRequestException("A feedback note is required when marking a session as completed")


def enforce_cancellation_window(
    booking_status: str, booking_datetime: datetime, *, now: datetime | None = None
) -> None:
    # Cancellations are only allowed outside the window before the booking start.
    now = now or datetime.utcnow()
    if booking_status == BookingStatus.CANCELLED and booking_datetime - now < CANCELLATION_WINDOW:
        raise BadRequestException("Cancellation window has passed")


def enforce_origin_login_allowed(role: str, allowed_roles: Collection[str]) -> None:
    # Product/UX gate: each deployed app may only be used by certain role buckets
    # (members -> mobile, staff -> web). Role is resolved from the verified
    # identity, so this can only reject a login, never elevate one. The
    # origin -> allowed-roles mapping is deployment configuration passed in by the
    # caller; this rule just enforces membership.
    if role not in allowed_roles:
        raise ForbiddenException("This account is not allowed to sign in from this application")
