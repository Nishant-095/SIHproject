from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin_token
from app.db.session import get_db
from app.domain.enums import SourceReviewStatus
from app.models import Source
from app.schemas.analytics import SourceToggleResponse
from app.schemas.health import SourceHealthHistoryPointResponse, SourceHealthResponse
from app.services.source_health import source_health_history, source_health_summary

router = APIRouter(prefix="/sources", tags=["source health"])
admin_router = APIRouter(prefix="/admin/sources", tags=["source administration"])


@router.get("/health", response_model=list[SourceHealthResponse])
def get_source_health(
    session: Annotated[Session, Depends(get_db)],
) -> list[SourceHealthResponse]:
    return source_health_summary(session)


@router.get("/health/history", response_model=list[SourceHealthHistoryPointResponse])
def get_source_health_history(
    session: Annotated[Session, Depends(get_db)],
    limit_days: Annotated[int, Query(ge=1, le=90)] = 30,
) -> list[SourceHealthHistoryPointResponse]:
    return source_health_history(session, limit_days=limit_days)


def _set_source_enabled(
    session: Session,
    source_id: uuid.UUID,
    *,
    enabled: bool,
) -> SourceToggleResponse:
    source = session.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    if enabled and source.review_status is not SourceReviewStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an approved source can be enabled",
        )
    source.enabled = enabled
    session.commit()
    session.refresh(source)
    return SourceToggleResponse(
        id=source.id,
        code=source.code,
        enabled=source.enabled,
        review_status=source.review_status.value,
    )


@router.post(
    "/{source_id}/enable",
    response_model=SourceToggleResponse,
    dependencies=[Depends(require_admin_token)],
)
def enable_source(
    source_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
) -> SourceToggleResponse:
    return _set_source_enabled(session, source_id, enabled=True)


@router.post(
    "/{source_id}/disable",
    response_model=SourceToggleResponse,
    dependencies=[Depends(require_admin_token)],
)
def disable_source(
    source_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
) -> SourceToggleResponse:
    return _set_source_enabled(session, source_id, enabled=False)


@admin_router.post(
    "/{source_id}/enable",
    response_model=SourceToggleResponse,
    dependencies=[Depends(require_admin_token)],
)
def admin_enable_source(
    source_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
) -> SourceToggleResponse:
    return _set_source_enabled(session, source_id, enabled=True)


@admin_router.post(
    "/{source_id}/disable",
    response_model=SourceToggleResponse,
    dependencies=[Depends(require_admin_token)],
)
def admin_disable_source(
    source_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
) -> SourceToggleResponse:
    return _set_source_enabled(session, source_id, enabled=False)
