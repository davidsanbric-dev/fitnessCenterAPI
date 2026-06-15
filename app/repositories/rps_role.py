from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Role


# Data-access for the Role catalogue. Role is the global authorization vocabulary
# and is not tenant-scoped, so these reads are never filtered by the active company.
class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_name(self, name: str) -> Role | None:
        return self.db.scalar(select(Role).where(Role.name == name))
