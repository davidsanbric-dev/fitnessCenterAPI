from fastapi import APIRouter

from .rtr_admin import router as admin_router
from .rtr_auth import router as auth_router
from .rtr_bookings import router as bookings_router
from .rtr_classes import router as classes_router
from .rtr_disciplines import router as disciplines_router
from .rtr_home import router as home_router
from .rtr_memberships import router as memberships_router
from .rtr_notifications import router as notifications_router
from .rtr_slots import router as slots_router
from .rtr_statics import router as statics_router
from .rtr_trainers import router as trainers_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(trainers_router)
api_router.include_router(disciplines_router)
api_router.include_router(classes_router)
api_router.include_router(bookings_router)
api_router.include_router(memberships_router)
api_router.include_router(statics_router)
api_router.include_router(notifications_router)
api_router.include_router(home_router)
api_router.include_router(slots_router)

__all__ = [
	"api_router",
	"auth_router",
	"admin_router",
	"bookings_router",
	"classes_router",
	"disciplines_router",
	"home_router",
	"memberships_router",
	"notifications_router",
	"slots_router",
	"statics_router",
	"trainers_router",
]
