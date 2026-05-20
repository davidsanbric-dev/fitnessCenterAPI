from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.repositories.rps_slot import SlotRepository
from app.services.svc_common import serialize_slot


# Adapted service unifying clinic slot-search contracts into one gym endpoint.
class SlotService:
    def __init__(self, db: Session):
        self.repository = SlotRepository(db)

    def search_slots(self, **filters) -> dict:
        items, total = self.repository.search_slots(**filters)
        return {
            "items": [serialize_slot(item) for item in items],
            "total": total,
            "page": filters["page"],
            "page_size": filters["page_size"],
        }
