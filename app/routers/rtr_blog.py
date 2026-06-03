from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.authorization import ensure_admin_or_manager
from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import MessageResponse, PaginatedResponse
from app.schemas.scm_blog import BlogResponse, BlogUpsertRequest
from app.services.svc_blog import BlogService

router = APIRouter(prefix="/blog", tags=["blog"])


# Hero image bytes. Unauthenticated so clients can render the image directly
# (e.g. Flutter Image.network / <img>); filenames are opaque uuids only handed
# out inside company-scoped responses. Declared before /{blog_id}.
@router.get("/media/{filename}")
def get_blog_media(filename: str):
    return BlogService.serve_media(filename)


# Read endpoints require auth so results are scoped to the caller's company.
# Consumed read-only by the mobile app and for listing in the web admin.
@router.get("", response_model=PaginatedResponse[BlogResponse], dependencies=[Depends(get_current_user)])
def list_blogs(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return BlogService(db).list_blogs(search, page, page_size)


@router.get("/{blog_id}", response_model=BlogResponse, dependencies=[Depends(get_current_user)])
def get_blog(blog_id: int, db: Session = Depends(get_db)):
    return BlogService(db).get_blog(blog_id)


# Write endpoints are restricted to admin/manager staff (web app CRUD).
@router.post("", response_model=BlogResponse)
def create_blog(
    payload: BlogUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_or_manager(db, current_user)
    return BlogService(db).create_blog(payload)


@router.put("/{blog_id}", response_model=BlogResponse)
def update_blog(
    blog_id: int,
    payload: BlogUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_or_manager(db, current_user)
    return BlogService(db).update_blog(blog_id, payload)


@router.delete("/{blog_id}", response_model=MessageResponse)
def delete_blog(
    blog_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_or_manager(db, current_user)
    return BlogService(db).delete_blog(blog_id)
