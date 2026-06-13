from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.repositories.rps_class import ClassRepository
from app.services.svc_common import get_or_404


# Adapted service from clinic GetCapabilities hierarchy and service-availability contracts.
class ClassService:
    def __init__(self, db: Session):
        self.repository = ClassRepository(db)

    def list_categories(self, location_code: str | None) -> dict:
        categories = self.repository.list_categories(location_code)
        return {
            "items": [
                {
                    "category_id": category.id,
                    "name": category.name,
                    "location_id": category.location_id,
                    "icon_url": category.icon_url,
                    "subcategories_count": len(category.subcategories),
                }
                for category in categories
            ]
        }

    def list_subcategories(self, category_id: int, location_code: str | None) -> dict:
        items = self.repository.list_subcategories(category_id, location_code)
        return {
            "items": [
                {
                    "subcategory_id": item.id,
                    "name": item.name,
                    "class_types_count": len(item.class_types),
                }
                for item in items
            ]
        }

    def list_class_types(self, subcategory_id: int, location_code: str | None) -> dict:
        items = self.repository.list_class_types(subcategory_id, location_code)
        return {
            "items": [
                {
                    "class_type_id": item.id,
                    "name": item.name,
                    "schedule_type": item.schedule_type,
                    "preparation_info": item.preparation_info,
                    "pdf_code": item.pdf_code,
                    "location_id": item.location_id,
                }
                for item in items
            ]
        }

    def get_class_type(self, class_type_id: int) -> dict:
        item = get_or_404(self.repository.get_class_type(class_type_id), "Class type not found")
        return {
            "class_type_id": item.id,
            "name": item.name,
            "schedule_type": item.schedule_type,
            "preparation_info": item.preparation_info,
            "pdf_code": item.pdf_code,
            "location_id": item.location_id,
            "category": {
                "category_id": item.subcategory.category.id,
                "name": item.subcategory.category.name,
            },
            "subcategory": {
                "subcategory_id": item.subcategory.id,
                "name": item.subcategory.name,
            },
        }

    def get_preparation(self, class_type_id: int) -> dict:
        item = get_or_404(self.repository.get_class_type(class_type_id), "Class type not found")
        return {
            "class_type_id": item.id,
            "name": item.name,
            "preparation_info": item.preparation_info,
            "pdf_code": item.pdf_code,
        }

    def get_availability(
        self,
        class_type_id: int,
        location_code: str,
        date_from: datetime | None,
        date_to: datetime | None,
        trainer_id: int | None,
        query_type: str | None,
    ) -> dict:
        item = get_or_404(self.repository.get_class_type(class_type_id), "Class type not found")
        slots = self.repository.get_class_type_availability(class_type_id, location_code, date_from, date_to, trainer_id, query_type)
        return {
            "class_type_id": class_type_id,
            "slots": [
                {
                    "slot_datetime": slot.slot_datetime,
                    "slot_assignment_code": slot.slot_assignment_code,
                    "schedule_type": slot.schedule_type,
                    "trainer": {
                        "trainer_id": slot.trainer.id,
                        "full_name": slot.trainer.full_name,
                        "discipline_id": slot.discipline.id if slot.discipline else None,
                        "discipline_name": slot.discipline.name if slot.discipline else None,
                    },
                }
                for slot in slots
                if slot.trainer is not None
            ],
        }
