from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.schemas import APIModel

if TYPE_CHECKING:
    from app.models import ClassType, Slot


def _class_type_fields(class_type: ClassType) -> dict:
    # Shared summary mapping, reused by the summary and detail responses.
    return {
        "class_type_id": class_type.id,
        "name": class_type.name,
        "schedule_type": class_type.schedule_type,
        "preparation_info": class_type.preparation_info,
        "pdf_code": class_type.pdf_code,
        "location_id": class_type.location_id,
    }


# Adapted from clinic Service/Capability query type "3" -> gym ClassType summary.
class ClassTypeSummary(APIModel):
    class_type_id: int
    name: str
    schedule_type: str | None = None
    preparation_info: str | None = None
    pdf_code: str | None = None
    location_id: int | None = None

    @classmethod
    def from_model(cls, class_type: ClassType) -> ClassTypeSummary:
        return cls(**_class_type_fields(class_type))


class ClassTypeDetailResponse(ClassTypeSummary):
    # Adapted class type detail with hierarchy context.
    category: dict | None = None
    subcategory: dict | None = None

    @classmethod
    def from_model(cls, class_type: ClassType) -> ClassTypeDetailResponse:
        subcategory = class_type.subcategory
        return cls(
            **_class_type_fields(class_type),
            category={"category_id": subcategory.category.id, "name": subcategory.category.name},
            subcategory={"subcategory_id": subcategory.id, "name": subcategory.name},
        )


class ClassPreparationResponse(APIModel):
    # Adapted from clinic Preparacion/CodigoPDF fields.
    class_type_id: int
    name: str
    preparation_info: str | None = None
    pdf_code: str | None = None

    @classmethod
    def from_model(cls, class_type: ClassType) -> ClassPreparationResponse:
        return cls(
            class_type_id=class_type.id,
            name=class_type.name,
            preparation_info=class_type.preparation_info,
            pdf_code=class_type.pdf_code,
        )


class ClassTypeAvailabilityTrainer(APIModel):
    # Adapted professional node for class type availability.
    trainer_id: int
    full_name: str
    discipline_id: int | None = None
    discipline_name: str | None = None

    @classmethod
    def from_slot(cls, slot: Slot) -> ClassTypeAvailabilityTrainer:
        # Built only for slots that have a trainer; discipline comes from the slot.
        return cls(
            trainer_id=slot.trainer.id,
            full_name=slot.trainer.full_name,
            discipline_id=slot.discipline.id if slot.discipline else None,
            discipline_name=slot.discipline.name if slot.discipline else None,
        )


class ClassTypeAvailabilityItem(APIModel):
    # Adapted from clinic GetAvailableServiceAppointments slot row.
    slot_datetime: datetime
    slot_assignment_code: str | None = None
    schedule_type: str | None = None
    trainer: ClassTypeAvailabilityTrainer

    @classmethod
    def from_slot(cls, slot: Slot) -> ClassTypeAvailabilityItem:
        return cls(
            slot_datetime=slot.slot_datetime,
            slot_assignment_code=slot.slot_assignment_code,
            schedule_type=slot.schedule_type,
            trainer=ClassTypeAvailabilityTrainer.from_slot(slot),
        )


class ClassTypeAvailabilityResponse(APIModel):
    # Adapted class type availability envelope.
    class_type_id: int
    slots: list[ClassTypeAvailabilityItem]

    @classmethod
    def from_slots(cls, class_type_id: int, slots: list[Slot]) -> ClassTypeAvailabilityResponse:
        return cls(
            class_type_id=class_type_id,
            slots=[ClassTypeAvailabilityItem.from_slot(slot) for slot in slots if slot.trainer is not None],
        )
