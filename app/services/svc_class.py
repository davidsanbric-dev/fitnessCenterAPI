from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.repositories.rps_class import ClassRepository
from app.schemas.scm_class_category import ClassCategorySummary, ClassSubcategorySummary
from app.schemas.scm_class_type import (
    ClassPreparationResponse,
    ClassTypeAvailabilityResponse,
    ClassTypeDetailResponse,
    ClassTypeSummary,
)
from app.services.svc_common import get_or_404


class ClassService:
    def __init__(self, db: Session):
        self.repository = ClassRepository(db)

    def _require_class_type(self, class_type_id: int):
        return get_or_404(self.repository.get_class_type(class_type_id), "Class type not found")

    def list_categories(self, location_code: str | None) -> dict:
        categories = self.repository.list_categories(location_code)
        return {"items": [ClassCategorySummary.from_model(category) for category in categories]}

    def list_subcategories(self, category_id: int, location_code: str | None) -> dict:
        items = self.repository.list_subcategories(category_id, location_code)
        return {"items": [ClassSubcategorySummary.from_model(item) for item in items]}

    def list_class_types(self, subcategory_id: int, location_code: str | None) -> dict:
        items = self.repository.list_class_types(subcategory_id, location_code)
        return {"items": [ClassTypeSummary.from_model(item) for item in items]}

    def get_class_type(self, class_type_id: int) -> ClassTypeDetailResponse:
        return ClassTypeDetailResponse.from_model(self._require_class_type(class_type_id))

    def get_preparation(self, class_type_id: int) -> ClassPreparationResponse:
        return ClassPreparationResponse.from_model(self._require_class_type(class_type_id))

    def get_availability(
        self,
        class_type_id: int,
        location_code: str,
        date_from: datetime | None,
        date_to: datetime | None,
        trainer_id: int | None,
        query_type: str | None,
    ) -> ClassTypeAvailabilityResponse:
        self._require_class_type(class_type_id)
        slots = self.repository.get_class_type_availability(class_type_id, location_code, date_from, date_to, trainer_id, query_type)
        return ClassTypeAvailabilityResponse.from_slots(class_type_id, slots)
