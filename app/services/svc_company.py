from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, NotFoundException
from app.models import TargetCompany
from app.repositories.rps_company import CompanyRepository


class CompanyService:
    def __init__(self, db: Session):
        self.repository = CompanyRepository(db)

    def resolve_registration_company(self, slug: str | None) -> TargetCompany:
        if slug:
            company = self.repository.get_by_slug(slug)
            if company is None:
                raise NotFoundException("Unknown company")
            return company
        companies = self.repository.list_companies()
        if len(companies) == 1:
            return companies[0]
        raise BadRequestException("company is required")
