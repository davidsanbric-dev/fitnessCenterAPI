from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import RequireStaff, get_current_user, get_db
from app.core.media import serve_image
from app.schemas import MessageResponse, PaginatedResponse
from app.schemas.scm_blog import BlogCreateRequest, BlogResponse, BlogUpdateRequest
from app.services.svc_blog import BlogService

router = APIRouter(prefix="/blog", tags=["blog"])


# Hero image bytes. Unauthenticated so clients can render the image directly
# (e.g. Flutter Image.network / <img>); filenames are opaque uuids only handed
# out inside company-scoped responses. Declared before /{blog_id}.
@router.get("/media/{filename}")
def get_blog_media(filename: str):
    return serve_image(filename)


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
@router.post("", response_model=BlogResponse, dependencies=[RequireStaff])
def create_blog(payload: BlogCreateRequest, db: Session = Depends(get_db)):
    return BlogService(db).create_blog(payload)


@router.put("/{blog_id}", response_model=BlogResponse, dependencies=[RequireStaff])
def update_blog(blog_id: int, payload: BlogUpdateRequest, db: Session = Depends(get_db)):
    return BlogService(db).update_blog(blog_id, payload)


@router.delete("/{blog_id}", response_model=MessageResponse, dependencies=[RequireStaff])
def delete_blog(blog_id: int, db: Session = Depends(get_db)):
    return BlogService(db).delete_blog(blog_id)
