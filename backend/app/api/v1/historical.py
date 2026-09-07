from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin_token
from app.db.session import get_db
from app.domain.enums import DataClass
from app.models import HistoricalDataset
from app.schemas.historical import (
    BacktestResponse,
    HistoricalDatasetImportRequest,
    HistoricalDatasetResponse,
)
from app.services.historical import build_backtest, dataset_response, import_historical_dataset

router = APIRouter(tags=["historical"])


@router.get("/historical/datasets", response_model=list[HistoricalDatasetResponse])
def list_historical_datasets(
    session: Annotated[Session, Depends(get_db)],
) -> list[HistoricalDatasetResponse]:
    return [
        dataset_response(session, row, include_observations=False)
        for row in session.scalars(select(HistoricalDataset).order_by(HistoricalDataset.code))
    ]


@router.get("/historical/datasets/{dataset_code}", response_model=HistoricalDatasetResponse)
def get_historical_dataset(
    dataset_code: str,
    session: Annotated[Session, Depends(get_db)],
) -> HistoricalDatasetResponse:
    dataset = session.scalar(
        select(HistoricalDataset).where(HistoricalDataset.code == dataset_code)
    )
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset_response(session, dataset)


@router.post(
    "/admin/historical/datasets",
    response_model=HistoricalDatasetResponse,
    dependencies=[Depends(require_admin_token)],
)
def create_historical_dataset(
    payload: HistoricalDatasetImportRequest,
    session: Annotated[Session, Depends(get_db)],
) -> HistoricalDatasetResponse:
    try:
        dataset, _ = import_historical_dataset(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return dataset_response(session, dataset)


@router.get("/historical/backtest", response_model=BacktestResponse)
def historical_backtest(
    dataset_code: str,
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
) -> BacktestResponse:
    try:
        return build_backtest(session, dataset_code=dataset_code, data_class=data_class)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
