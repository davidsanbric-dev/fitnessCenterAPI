from __future__ import annotations

from app.schemas import APIModel


# Adapted from clinic Capabilities query type "1" group -> gym ClassCategory.
class ClassCategorySummary(APIModel):
    category_id: int
    name: str
    location_id: int | None = None
    icon_url: str | None = None
    subcategories_count: int = 0


class ClassSubcategorySummary(APIModel):
    # Adapted from clinic Capabilities query type "2" subgroup -> gym ClassSubcategory.
    subcategory_id: int
    name: str
    class_types_count: int = 0
