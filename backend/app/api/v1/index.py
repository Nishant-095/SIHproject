from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.api.dependencies import require_admin_token
from app.db.session import get_db
from app.domain.enums import AggregationPeriod, DataClass
from app.indexing.periods import refresh_periods_for_index
from app.indexing.service import calculate_index_for_run
from app.models import DailyIndex, PeriodIndex
from app.schemas.analytics import (
    DailyIndexResponse,
    IndexCoverageResponse,
    IndexHistoryPointResponse,
    PeriodIndexResponse,
)
from app.services.aggregation import index_coverage_response
from app.services.analytics import daily_index_response

router = APIRouter(tags=["index"])


def _base_query(data_class: DataClass) -> Select[tuple[DailyIndex]]:
    return select(DailyIndex).where(DailyIndex.data_class == data_class)


@router.get("/index/current", response_model=DailyIndexResponse)
def current_index(
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
) -> DailyIndexResponse:
    index = session.scalar(
        _base_query(data_class).order_by(
            DailyIndex.methodological_date.desc(), DailyIndex.calculated_at.desc()
        )
    )
    if index is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Index not found")
    return daily_index_response(session, index)


@router.get("/index/current/coverage", response_model=IndexCoverageResponse)
def current_index_coverage(
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
) -> IndexCoverageResponse:
    index = session.scalar(
        _base_query(data_class).order_by(
            DailyIndex.methodological_date.desc(), DailyIndex.calculated_at.desc()
        )
    )
    if index is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Index not found")
    return index_coverage_response(session, index)


@router.get("/index/history", response_model=list[IndexHistoryPointResponse])
def index_history(
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
    limit: Annotated[int, Query(ge=1, le=366)] = 90,
) -> list[IndexHistoryPointResponse]:
    indices = list(
        session.scalars(
            _base_query(data_class).order_by(DailyIndex.methodological_date.desc()).limit(limit)
        )
    )
    return [
        IndexHistoryPointResponse(
            id=index.id,
            methodological_date=index.methodological_date,
            data_class=index.data_class,
            index_value=index.index_value,
            coverage_percent=index.coverage_percent,
            publication_status=index.publication_status,
        )
        for index in reversed(indices)
    ]


@router.get("/index/daily/{methodological_date}", response_model=DailyIndexResponse)
def daily_index(
    methodological_date: date,
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
) -> DailyIndexResponse:
    index = session.scalar(
        _base_query(data_class).where(DailyIndex.methodological_date == methodological_date)
    )
    if index is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Index not found")
    return daily_index_response(session, index)


def _period_history(
    session: Session,
    *,
    period_type: AggregationPeriod,
    data_class: DataClass,
    limit: int,
) -> list[PeriodIndex]:
    rows = list(
        session.scalars(
            select(PeriodIndex)
            .where(
                PeriodIndex.period_type == period_type,
                PeriodIndex.data_class == data_class,
            )
            .order_by(PeriodIndex.period_start.desc())
            .limit(limit)
        )
    )
    return list(reversed(rows))


@router.get("/index/weekly", response_model=list[PeriodIndexResponse])
def weekly_index(
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
    limit: Annotated[int, Query(ge=1, le=104)] = 52,
) -> list[PeriodIndex]:
    return _period_history(
        session,
        period_type=AggregationPeriod.WEEKLY,
        data_class=data_class,
        limit=limit,
    )


@router.get("/index/monthly", response_model=list[PeriodIndexResponse])
def monthly_index(
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
    limit: Annotated[int, Query(ge=1, le=60)] = 24,
) -> list[PeriodIndex]:
    return _period_history(
        session,
        period_type=AggregationPeriod.MONTHLY,
        data_class=data_class,
        limit=limit,
    )


@router.post(
    "/admin/index/recalculate",
    response_model=DailyIndexResponse,
    dependencies=[Depends(require_admin_token)],
)
def recalculate_index(
    run_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
) -> DailyIndexResponse:
    try:
        result = calculate_index_for_run(session, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return daily_index_response(session, result.daily_index)


@router.post(
    "/admin/index/aggregate",
    response_model=list[PeriodIndexResponse],
    dependencies=[Depends(require_admin_token)],
)
def recalculate_period_aggregates(
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
) -> list[PeriodIndex]:
    daily_indices = list(
        session.scalars(_base_query(data_class).order_by(DailyIndex.methodological_date))
    )
    refreshed: dict[uuid.UUID, PeriodIndex] = {}
    for index in daily_indices:
        for aggregate in refresh_periods_for_index(session, index):
            refreshed[aggregate.id] = aggregate
    return sorted(
        refreshed.values(),
        key=lambda item: (item.period_start, item.period_type.value),
    )
