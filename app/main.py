from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import Base, engine
from app.core.migrations import apply_migrations
from app.routers import api_router

logger = logging.getLogger("uvicorn.error")


def _setup_demo_firebase_accounts() -> None:
    """Create/verify demo Firebase accounts from ADMIN_EMAILS (best-effort).

    Runs before migrations so demo credentials exist on the Firebase side. Never
    blocks startup: if Firebase is unconfigured (e.g. local dev), it is skipped.
    """
    try:
        from scripts.set_and_verify_demo_users import seed_demo_users_from_settings

        seed_demo_users_from_settings()
    except Exception:
        logger.warning("Demo Firebase account setup skipped (see traceback).", exc_info=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _setup_demo_firebase_accounts()
    apply_migrations()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}