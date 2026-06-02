from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from app.models import TenantMixin

# Key under which the active TargetCompany id is stored on ``Session.info``.
_COMPANY_KEY = "company_id"


def set_session_company(session: Session, company_id: int | None) -> None:
    """Bind the active TargetCompany to a session.

    Once set, every subsequent ORM SELECT on this session is auto-scoped to the
    company and every new tenant-scoped row flushed through it is auto-stamped
    with the same company. Resolving the authenticated user must happen *before*
    this is set (we don't yet know the company), which is why it is unfiltered.
    """
    session.info[_COMPANY_KEY] = company_id


def get_session_company(session: Session) -> int | None:
    return session.info.get(_COMPANY_KEY)


@event.listens_for(Session, "do_orm_execute")
def _scope_reads_to_company(execute_state) -> None:
    # Apply the tenant filter only to ordinary ORM SELECTs. Column loads and
    # relationship (lazy/selectin) loads are left alone: they originate from an
    # already-scoped parent row, and re-applying the criteria there can break
    # eager loaders.
    if (
        not execute_state.is_select
        or execute_state.is_column_load
        or execute_state.is_relationship_load
    ):
        return

    company_id = execute_state.session.info.get(_COMPANY_KEY)
    if company_id is None:
        return

    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            TenantMixin,
            lambda cls: cls.company_id == company_id,
            include_aliases=True,
        )
    )


@event.listens_for(Session, "before_flush")
def _stamp_writes_with_company(session: Session, flush_context, instances) -> None:
    company_id = session.info.get(_COMPANY_KEY)
    if company_id is None:
        return
    for instance in session.new:
        if isinstance(instance, TenantMixin) and getattr(instance, "company_id", None) is None:
            instance.company_id = company_id
