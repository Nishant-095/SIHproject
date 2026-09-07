from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin_token
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.enums import RunTrigger
from app.models import CollectionJob, CollectionRun
from app.schemas.collection import (
    AdminCollectionRunRequest,
    CollectionJobResponse,
    CollectionRunDetailResponse,
    CollectionRunResponse,
)
from app.services.collection import CollectionService

router = APIRouter(tags=["collection runs"])


def _run_detail(
    session: Session,
    run: CollectionRun,
    *,
    created: bool | None = None,
) -> CollectionRunDetailResponse:
    jobs = list(
        session.scalars(
            select(CollectionJob)
            .where(CollectionJob.collection_run_id == run.id)
            .order_by(CollectionJob.advance_days, CollectionJob.id)
        )
    )
    base = CollectionRunResponse.model_validate(run)
    return CollectionRunDetailResponse(
        **base.model_dump(),
        jobs=[CollectionJobResponse.model_validate(job) for job in jobs],
        created=created,
    )


@router.get("/collection-runs", response_model=list[CollectionRunResponse])
def list_collection_runs(
    session: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[CollectionRun]:
    return list(
        session.scalars(
            select(CollectionRun)
            .order_by(CollectionRun.methodological_date.desc(), CollectionRun.created_at.desc())
            .limit(limit)
        )
    )


@router.get(
    "/collection-runs/{run_id}",
    response_model=CollectionRunDetailResponse,
)
def get_collection_run(
    run_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
) -> CollectionRunDetailResponse:
    run = session.get(CollectionRun, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection run not found",
        )
    return _run_detail(session, run)


@router.post(
    "/admin/collection-runs",
    response_model=CollectionRunDetailResponse,
    dependencies=[Depends(require_admin_token)],
)
async def run_collection(
    request: AdminCollectionRunRequest,
    session: Annotated[Session, Depends(get_db)],
) -> CollectionRunDetailResponse:
    settings = get_settings()
    effective_date = request.methodological_date or datetime.now(
        ZoneInfo(settings.collection_timezone)
    ).date()
    service = CollectionService(settings)
    try:
        if request.source == "fixture":
            result = await service.run_fixture(
                session, methodological_date=effective_date, trigger=RunTrigger.MANUAL
            )
        elif request.source == "duffel":
            result = await service.run_duffel(
                session, methodological_date=effective_date, trigger=RunTrigger.MANUAL
            )
        else:
            result = await service.run_permissioned_web(
                session, methodological_date=effective_date, trigger=RunTrigger.MANUAL
            )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _run_detail(session, result.run, created=result.created)


@router.post(
    "/admin/collection-runs/fixture",
    response_model=CollectionRunDetailResponse,
    dependencies=[Depends(require_admin_token)],
)
async def run_fixture_collection(
    session: Annotated[Session, Depends(get_db)],
    methodological_date: Annotated[date | None, Query()] = None,
) -> CollectionRunDetailResponse:
    settings = get_settings()
    effective_date = (
        methodological_date or datetime.now(ZoneInfo(settings.collection_timezone)).date()
    )
    result = await CollectionService(settings).run_fixture(
        session,
        methodological_date=effective_date,
        trigger=RunTrigger.MANUAL,
    )
    return _run_detail(session, result.run, created=result.created)


@router.post(
    "/admin/collection-runs/duffel",
    response_model=CollectionRunDetailResponse,
    dependencies=[Depends(require_admin_token)],
)
async def run_duffel_collection(
    session: Annotated[Session, Depends(get_db)],
    methodological_date: Annotated[date | None, Query()] = None,
) -> CollectionRunDetailResponse:
    settings = get_settings()
    effective_date = (
        methodological_date or datetime.now(ZoneInfo(settings.collection_timezone)).date()
    )
    try:
        result = await CollectionService(settings).run_duffel(
            session,
            methodological_date=effective_date,
            trigger=RunTrigger.MANUAL,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _run_detail(session, result.run, created=result.created)


@router.post(
    "/admin/collection-runs/permissioned-web",
    response_model=CollectionRunDetailResponse,
    dependencies=[Depends(require_admin_token)],
)
async def run_permissioned_web_collection(
    session: Annotated[Session, Depends(get_db)],
    methodological_date: Annotated[date | None, Query()] = None,
) -> CollectionRunDetailResponse:
    settings = get_settings()
    effective_date = (
        methodological_date or datetime.now(ZoneInfo(settings.collection_timezone)).date()
    )
    try:
        result = await CollectionService(settings).run_permissioned_web(
            session,
            methodological_date=effective_date,
            trigger=RunTrigger.MANUAL,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _run_detail(session, result.run, created=result.created)
