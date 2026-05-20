from __future__ import annotations

from datetime import datetime

from app.schemas import APIModel


# Adapted from clinic Service/Capability query type "3" -> gym ClassType summary.
class ClassTypeSummary(APIModel):
    class_type_id: int
    name: str
    schedule_type: str | None = None
    preparation_info: str | None = None
    pdf_code: str | None = None
    location_id: int | None = None


class ClassTypeDetailResponse(ClassTypeSummary):
    # Adapted class type detail with hierarchy context.
    category: dict | None = None
    subcategory: dict | None = None


class ClassPreparationResponse(APIModel):
    # Adapted from clinic Preparacion/CodigoPDF fields.
    class_type_id: int
    name: str
    preparation_info: str | None = None
    pdf_code: str | None = None


class ClassTypeAvailabilityTrainer(APIModel):
    # Adapted professional node for class type availability.
    trainer_id: int
    full_name: str
    discipline_id: int | None = None
    discipline_name: str | None = None


class ClassTypeAvailabilityItem(APIModel):
    # Adapted from clinic GetAvailableServiceAppointments slot row.
    slot_datetime: datetime
    slot_assignment_code: str | None = None
    schedule_type: str | None = None
    trainer: ClassTypeAvailabilityTrainer


class ClassTypeAvailabilityResponse(APIModel):
    # Adapted class type availability envelope.
    class_type_id: int
    slots: list[ClassTypeAvailabilityItem]
