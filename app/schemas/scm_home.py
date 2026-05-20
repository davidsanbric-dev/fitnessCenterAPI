from __future__ import annotations

from app.schemas import APIModel


# Adapted home aggregate built from clinic-like composition of agenda + static data.
class HomeMemberResponse(APIModel):
    first_name: str
    membership_plan: str | None = None


class HomeUpcomingBooking(APIModel):
    # Home-friendly projection adapted from booking agenda rows.
    id: int
    date: str
    start_time: str
    class_type: str | None = None
    trainer: str | None = None


class HomeFeaturedClass(APIModel):
    # Gym-specific featured catalog block built from adapted class hierarchy.
    id: int
    name: str
    description: str | None = None
    icon_url: str | None = None


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
