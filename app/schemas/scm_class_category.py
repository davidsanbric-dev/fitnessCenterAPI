from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas import APIModel

if TYPE_CHECKING:
    from app.models import ClassCategory, ClassSubcategory


# Adapted from clinic Capabilities query type "1" group -> gym ClassCategory.
class ClassCategorySummary(APIModel):
    category_id: int
    name: str
    icon_url: str | None = None
    subcategories_count: int = 0

    @classmethod
    def from_model(cls, category: ClassCategory) -> ClassCategorySummary:
        return cls(
            category_id=category.id,
            name=category.name,
            icon_url=category.icon_url,
            subcategories_count=len(category.subcategories),
        )


class ClassSubcategorySummary(APIModel):
    # Adapted from clinic Capabilities query type "2" subgroup -> gym ClassSubcategory.
    subcategory_id: int
    name: str
    class_types_count: int = 0

    @classmethod
    def from_model(cls, subcategory: ClassSubcategory) -> ClassSubcategorySummary:
        return cls(
            subcategory_id=subcategory.id,
            name=subcategory.name,
            class_types_count=len(subcategory.class_types),
        )
