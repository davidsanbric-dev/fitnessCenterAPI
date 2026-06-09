from __future__ import annotations

from datetime import date, datetime, time

from app.models import (
    Booking,
    MemberMembership,
    Slot,
    Trainer,
    User,
)


def parse_datetime_parts(date_value: str, time_value: str) -> datetime:
    return datetime.combine(date.fromisoformat(date_value), time.fromisoformat(time_value))


def serialize_trainer_summary(trainer: Trainer) -> dict:
    discipline = trainer.disciplines[0] if trainer.disciplines else None
    return {
        "trainer_id": trainer.id,
        "full_name": trainer.full_name,
        "discipline_id": discipline.id if discipline else None,
        "discipline_name": discipline.name if discipline else None,
        "bio": trainer.bio,
        "photo_url": trainer.photo_url,
        "certifications": trainer.certifications or [],
    }


def serialize_booking(booking: Booking) -> dict:
    trainer_discipline = booking.trainer.disciplines[0] if booking.trainer and booking.trainer.disciplines else None
    member = None
    if booking.user is not None:
        profile = booking.user.profile
        full_name = (
            " ".join(filter(None, [profile.first_name, profile.paternal_surname, profile.maternal_surname])).strip()
            if profile is not None
            else ""
        ) or booking.user.email
        member = {
            "user_id": booking.user.id,
            "full_name": full_name,
            "email": booking.user.email,
        }
    return {
        "booking_id": booking.id,
        "booking_status": booking.booking_status,
        "booking_datetime": booking.booking_datetime,
        "scheduled_at": booking.scheduled_at,
        "session_duration_minutes": booking.session_duration_minutes,
        "preparation_info": booking.preparation_info,
        "has_pdf": booking.has_pdf,
        "pdf_code": booking.pdf_code,
        "notes": booking.notes,
        "is_overbooking": booking.is_overbooking,
        "member": member,
        "trainer": {
            "trainer_id": booking.trainer.id,
            "full_name": booking.trainer.full_name,
            "discipline_id": trainer_discipline.id if trainer_discipline else booking.discipline_id,
            "discipline_name": trainer_discipline.name if trainer_discipline else booking.discipline.name if booking.discipline else None,
        } if booking.trainer else None,
        "class_type": {
            "class_type_id": booking.class_type.id,
            "name": booking.class_type.name,
            "type_name": booking.class_type.schedule_type,
        } if booking.class_type else None,
        "category": {
            "category_id": booking.category.id,
            "name": booking.category.name,
        } if booking.category else None,
        "location": {
            "location_id": booking.location.id,
            "name": booking.location.name,
            "location_code": booking.location.location_code,
        } if booking.location else None,
    }


def serialize_user(user: User) -> dict:
    membership_plan = None
    if user.membership and user.membership.plan:
        membership_plan = {
            "membership_plan_id": user.membership.plan.id,
            "name": user.membership.plan.name,
            "description": user.membership.plan.description,
        }
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.profile.first_name,
        "paternal_surname": user.profile.paternal_surname,
        "maternal_surname": user.profile.maternal_surname,
        "rut": user.profile.rut,
        "mobile_phone": user.profile.mobile_phone,
        "landline_phone": user.profile.landline_phone,
        "birth_date": user.profile.birth_date,
        "address": user.profile.address,
        "avatar_url": user.profile.avatar_url,
        "membership_plan": membership_plan,
        "fitness_goals": user.profile.fitness_goals,
        "created_at": user.created_at,
    }


def serialize_slot(slot: Slot) -> dict:
    discipline = slot.trainer.disciplines[0] if slot.trainer and slot.trainer.disciplines else slot.discipline
    return {
        "slot_datetime": slot.slot_datetime,
        "location_id": slot.location_id,
        "slot_assignment_code": slot.slot_assignment_code,
        "schedule_type": slot.schedule_type,
        "is_available": slot.is_available,
        "trainer": {
            "trainer_id": slot.trainer.id,
            "trainer_code": slot.trainer.trainer_code,
            "full_name": slot.trainer.full_name,
            "discipline_id": discipline.id if discipline else None,
            "discipline_code": discipline.discipline_code if discipline else None,
            "discipline_name": discipline.name if discipline else None,
        } if slot.trainer else None,
    }


def serialize_membership(membership: MemberMembership) -> dict:
    remaining = max(membership.plan.max_bookings_per_month - membership.bookings_used, 0)
    return {
        "plan": {
            "membership_plan_id": membership.plan.id,
            "name": membership.plan.name,
            "description": membership.plan.description,
            "price": membership.plan.price,
            "duration_days": membership.plan.duration_days,
            "features": membership.plan.features,
            "max_bookings_per_month": membership.plan.max_bookings_per_month,
            "includes_personal_training": membership.plan.includes_personal_training,
        },
        "start_date": membership.start_date,
        "end_date": membership.end_date,
        "status": membership.status,
        "bookings_used": membership.bookings_used,
        "bookings_remaining": remaining,
    }
