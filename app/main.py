from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.models import (
    ClassCategory,
    ClassSubcategory,
    ClassType,
    Discipline,
    Location,
    MembershipPlan,
    Slot,
    Trainer,
)
from app.routers import api_router


def seed_reference_data() -> None:
    with SessionLocal() as db:
        existing_location = db.scalar(select(Location.id).limit(1))
        if existing_location is not None:
            return

        locations = [
            Location(location_code=code, name=name)
            for code, name in settings.locations.items()
        ]
        db.add_all(locations)
        db.flush()

        disciplines = [
            Discipline(discipline_code="YOGA", name="Yoga", description="Mobility and mindful movement", icon_url="/icons/yoga.svg"),
            Discipline(discipline_code="CROSSFIT", name="CrossFit", description="High intensity functional training", icon_url="/icons/crossfit.svg"),
            Discipline(discipline_code="PILATES", name="Pilates", description="Core strength and posture", icon_url="/icons/pilates.svg"),
        ]
        db.add_all(disciplines)

        memberships = [
            MembershipPlan(
                name="Basic",
                description="Access to essential classes",
                price=29.99,
                duration_days=30,
                features=["Gym floor access", "2 group classes per week"],
                max_bookings_per_month=8,
                includes_personal_training=False,
            ),
            MembershipPlan(
                name="Premium",
                description="Unlimited classes and amenities",
                price=59.99,
                duration_days=30,
                features=["Unlimited classes", "Sauna access", "Nutrition webinar"],
                max_bookings_per_month=30,
                includes_personal_training=True,
            ),
            MembershipPlan(
                name="VIP",
                description="All access with premium coaching",
                price=89.99,
                duration_days=30,
                features=["Unlimited classes", "2 PT sessions", "Priority booking"],
                max_bookings_per_month=50,
                includes_personal_training=True,
            ),
        ]
        db.add_all(memberships)
        db.flush()

        yoga, crossfit, pilates = disciplines
        downtown, north = locations

        categories = [
            ClassCategory(name="Mind & Body", icon_url="/icons/mind-body.svg", location=downtown),
            ClassCategory(name="Performance", icon_url="/icons/performance.svg", location=north),
        ]
        db.add_all(categories)
        db.flush()

        categories[0].membership_plans.extend(memberships)
        categories[1].membership_plans.extend(memberships[1:])

        subcategories = [
            ClassSubcategory(name="Yoga Flow", category=categories[0]),
            ClassSubcategory(name="Strength", category=categories[1]),
        ]
        db.add_all(subcategories)
        db.flush()

        class_types = [
            ClassType(
                name="Sunrise Yoga",
                subcategory=subcategories[0],
                location=downtown,
                schedule_type="GROUP",
                preparation_info="Bring a yoga mat and water bottle.",
                pdf_code="YOGA-001",
            ),
            ClassType(
                name="CrossFit Starter",
                subcategory=subcategories[1],
                location=north,
                schedule_type="GROUP",
                preparation_info="Arrive 10 minutes early for warm-up.",
                pdf_code="CF-010",
            ),
        ]
        db.add_all(class_types)

        trainers = [
            Trainer(
                trainer_code=1001,
                full_name="Sofia Ramirez",
                bio="Yoga instructor focused on flexibility and balance.",
                photo_url="/images/trainers/sofia.jpg",
                certifications=["RYT-500", "Mobility Coach"],
                location=downtown,
                disciplines=[yoga, pilates],
                membership_plans=memberships,
            ),
            Trainer(
                trainer_code=1002,
                full_name="Diego Herrera",
                bio="Cross-training coach with performance background.",
                photo_url="/images/trainers/diego.jpg",
                certifications=["CrossFit Level 2", "TRX Coach"],
                location=north,
                disciplines=[crossfit],
                membership_plans=memberships[1:],
            ),
        ]
        db.add_all(trainers)
        db.flush()

        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        slots = [
            Slot(
                slot_datetime=now + timedelta(days=1, hours=7),
                location=downtown,
                trainer=trainers[0],
                discipline=yoga,
                class_type=class_types[0],
                is_online=False,
                is_available=True,
                slot_assignment_code="ASG-100",
                schedule_type="GROUP",
            ),
            Slot(
                slot_datetime=now + timedelta(days=2, hours=18),
                location=north,
                trainer=trainers[1],
                discipline=crossfit,
                class_type=class_types[1],
                is_online=True,
                is_available=True,
                slot_assignment_code="ASG-200",
                schedule_type="GROUP",
            ),
        ]
        db.add_all(slots)
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.seed_data:
        seed_reference_data()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
