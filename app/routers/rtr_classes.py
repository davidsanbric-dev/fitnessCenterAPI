from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.schemas.scm_class_type import ClassPreparationResponse, ClassTypeAvailabilityResponse, ClassTypeDetailResponse
from app.services.svc_class import ClassService

# Auth required so the class catalogue is scoped to the caller's company.
router = APIRouter(tags=["classes"], dependencies=[Depends(get_current_user)])


# Adapted from clinic GetCapabilities with TipoConsulta="1".
@router.get("/class-categories")
def list_categories(location_code: str | None = None, db: Session = Depends(get_db)):
    return ClassService(db).list_categories(location_code)


# Adapted from clinic GetCapabilities with TipoConsulta="2".
@router.get("/class-categories/{category_id}/subcategories")
def list_subcategories(category_id: int, location_code: str | None = None, db: Session = Depends(get_db)):
    return ClassService(db).list_subcategories(category_id, location_code)


# Adapted from clinic GetCapabilities with TipoConsulta="3".
@router.get("/class-categories/{category_id}/subcategories/{subcategory_id}/class-types")
def list_class_types(category_id: int, subcategory_id: int, location_code: str | None = None, db: Session = Depends(get_db)):
    return ClassService(db).list_class_types(subcategory_id, location_code)


# Adapted class/service detail endpoint from clinic capability/service read model.
@router.get("/class-types/{class_type_id}", response_model=ClassTypeDetailResponse)
def get_class_type(class_type_id: int, db: Session = Depends(get_db)):
    return ClassService(db).get_class_type(class_type_id)


# Adapted from clinic Preparacion/CodigoPDF read fields.
@router.get("/class-types/{class_type_id}/preparation", response_model=ClassPreparationResponse)
def get_preparation(class_type_id: int, db: Session = Depends(get_db)):
    return ClassService(db).get_preparation(class_type_id)


# Adapted from clinic GetAvailableServiceAppointments query semantics.
@router.get("/class-types/{class_type_id}/availability", response_model=ClassTypeAvailabilityResponse)
def get_availability(
    class_type_id: int,
    location_code: str,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    trainer_id: int | None = None,
    query_type: str | None = None,
    db: Session = Depends(get_db),
):
    return ClassService(db).get_availability(class_type_id, location_code, date_from, date_to, trainer_id, query_type)
