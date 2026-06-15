"""Domain layer: status vocabularies, value objects, and pure business rules.

This package holds logic that is intrinsic to the business -- independent of how
data is stored (repositories/ORM) or exposed (routers/schemas). Services remain
the orchestration layer: they load and persist rows and call into these rules.
Everything here is free of database/session access so it stays unit-testable.
"""

from __future__ import annotations

from app.domain.enums import BookingStatus, MembershipStatus, ScheduleType
from app.domain.policies import (
    CANCELLATION_WINDOW,
    enforce_booking_allowance,
    enforce_cancellation_window,
    enforce_origin_login_allowed,
    require_notes_for_completion,
)
from app.domain.value_objects import Rut

__all__ = [
    "BookingStatus",
    "MembershipStatus",
    "ScheduleType",
    "CANCELLATION_WINDOW",
    "enforce_booking_allowance",
    "enforce_cancellation_window",
    "enforce_origin_login_allowed",
    "require_notes_for_completion",
    "Rut",
]
