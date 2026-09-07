from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.enums import DataClass
from app.schemas.analytics import QualitySummaryResponse
from app.services.analytics import quality_summary

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/summary", response_model=QualitySummaryResponse)
def get_quality_summary(
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
) -> QualitySummaryResponse:
    return quality_summary(session, data_class)
