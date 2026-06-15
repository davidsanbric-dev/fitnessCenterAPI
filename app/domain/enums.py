from __future__ import annotations

from enum import StrEnum


# Domain status vocabularies. These are ``StrEnum`` so they compare equal to the
# bare strings already stored in the database and accepted at the API boundary
# (``BookingStatus.CONFIRMED == "CONFIRMED"``), making adoption incremental and
# behaviour-preserving while giving the codebase one typed source of truth.
class BookingStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class MembershipStatus(StrEnum):
    # ACTIVE is the seeded/registration default; the others describe the natural
    # lifecycle of a membership bounded by its end_date.
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ScheduleType(StrEnum):
    # How a slot/class is delivered: one-to-one trainer time vs. a group class.
    PERSONAL = "PERSONAL"
    GROUP = "GROUP"
