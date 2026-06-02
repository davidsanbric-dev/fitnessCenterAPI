from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.firebase_auth import verify_firebase_token
from app.core.db import SessionLocal
from app.core.tenancy import set_session_company
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


def get_current_user(
	credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
	db: Session = Depends(get_db),
) -> User:
	if credentials is None:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

	payload = verify_firebase_token(credentials.credentials)
	email = str(payload.get("email") or "").strip().lower()
	if not email:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing email")

	statement = (
		select(User)
		.options(selectinload(User.role))
		.where(func.lower(User.email) == email)
	)
	user = db.scalar(statement)
	if user is None or not user.is_active:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
	# Establish the tenant scope for the rest of the request: every subsequent
	# query on this session is now auto-filtered to the user's company. The
	# lookup above ran unscoped on purpose -- the company is only known now.
	set_session_company(db, user.company_id)
	return user
