from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import TargetCompany


# Data-access for the TargetCompany catalogue. TargetCompany is not tenant-scoped,
# so these reads are never filtered by the active company.
class CompanyRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_companies(self) -> list[TargetCompany]:
        return list(self.db.scalars(select(TargetCompany)).all())

    def get_by_slug(self, slug: str) -> TargetCompany | None:
        wanted = slug.strip().lower()
        statement = select(TargetCompany).where(func.lower(TargetCompany.slug) == wanted)
        return self.db.scalar(statement)
