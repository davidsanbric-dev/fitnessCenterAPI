from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas import APIModel

if TYPE_CHECKING:
    from app.models import Booking, ClassCategory, User


# Static home navigation block; identical for every member.
_QUICK_ACTIONS = (
    ("Book a Class", "/class-categories"),
    ("Find a Trainer", "/trainers"),
)


# Adapted home aggregate built from clinic-like composition of agenda + static data.
class HomeMemberResponse(APIModel):
    first_name: str
    membership_plan: str | None = None

    @classmethod
    def from_user(cls, user: User) -> HomeMemberResponse:
        plan = user.membership.plan if user.membership and user.membership.plan else None
        return cls(first_name=user.profile.first_name, membership_plan=plan.name if plan else None)


class HomeUpcomingBooking(APIModel):
    # Home-friendly projection adapted from booking agenda rows.
    id: int
    date: str
    start_time: str
    class_type: str | None = None
    trainer: str | None = None

    @classmethod
    def from_booking(cls, booking: Booking) -> HomeUpcomingBooking:
        return cls(
            id=booking.id,
            date=booking.booking_datetime.date().isoformat(),
            start_time=booking.booking_datetime.time().strftime("%H:%M"),
            class_type=booking.class_type.name if booking.class_type else None,
            trainer=booking.trainer.full_name if booking.trainer else None,
        )


class HomeFeaturedClass(APIModel):
    # Gym-specific featured catalog block built from adapted class hierarchy.
    id: int
    name: str
    description: str | None = None
    icon_url: str | None = None

    @classmethod
    def from_category(cls, category: ClassCategory) -> HomeFeaturedClass:
        return cls(
            id=category.id,
            name=category.name,
            description=f"Featured classes in {category.name}",
            icon_url=category.icon_url,
        )


class HomeQuickAction(APIModel):
    # Home navigation actions for adapted gym flows.
    label: str
    route: str


class HomeResponse(APIModel):
    # Aggregated home response joining adapted entities and gym extensions.
    member: HomeMemberResponse
    upcoming_bookings: list[HomeUpcomingBooking]
    featured_classes: list[HomeFeaturedClass]
    unread_notifications_count: int
    quick_actions: list[HomeQuickAction]

    @classmethod
    def build(
        cls,
        user: User,
        upcoming: list[Booking],
        categories: list[ClassCategory],
        unread_count: int,
    ) -> HomeResponse:
        # The service supplies the already-fetched aggregate inputs; the DTO owns
        # the projection/formatting and the static quick-action block.
        return cls(
            member=HomeMemberResponse.from_user(user),
            upcoming_bookings=[HomeUpcomingBooking.from_booking(booking) for booking in upcoming],
            featured_classes=[HomeFeaturedClass.from_category(category) for category in categories],
            unread_notifications_count=unread_count,
            quick_actions=[HomeQuickAction(label=label, route=route) for label, route in _QUICK_ACTIONS],
        )
