from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.enums import DataClass, QualityStatus
from app.models import CollectionJob, CollectionRun, FareObservation, RawQuote, Route, Source
from app.schemas.fare import (
    FareObservationResponse,
    ObservationProvenanceResponse,
    RawQuoteResponse,
)

router = APIRouter(prefix="/observations", tags=["observations"])


def _observation_or_404(session: Session, observation_id: uuid.UUID) -> FareObservation:
    observation = session.get(FareObservation, observation_id)
    if observation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Observation not found")
    return observation


@router.get("", response_model=list[FareObservationResponse])
def list_observations(
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
    origin: Annotated[str | None, Query(min_length=3, max_length=3)] = None,
    destination: Annotated[str | None, Query(min_length=3, max_length=3)] = None,
    quality_status: Annotated[QualityStatus | None, Query()] = None,
    included_in_index: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[FareObservation]:
    query = (
        select(FareObservation)
        .join(RawQuote, FareObservation.raw_quote_id == RawQuote.id)
        .where(RawQuote.data_class == data_class)
    )
    if origin is not None:
        query = query.where(FareObservation.origin_iata == origin.upper())
    if destination is not None:
        query = query.where(FareObservation.destination_iata == destination.upper())
    if quality_status is not None:
        query = query.where(FareObservation.quality_status == quality_status)
    if included_in_index is not None:
        query = query.where(FareObservation.included_in_index == included_in_index)
    return list(
        session.scalars(
            query.order_by(FareObservation.observed_at_utc.desc(), FareObservation.id)
            .offset(offset)
            .limit(limit)
        )
    )


@router.get("/{observation_id}", response_model=FareObservationResponse)
def get_observation(
    observation_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
) -> FareObservation:
    return _observation_or_404(session, observation_id)


@router.get("/{observation_id}/provenance", response_model=ObservationProvenanceResponse)
def get_observation_provenance(
    observation_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
) -> ObservationProvenanceResponse:
    observation = _observation_or_404(session, observation_id)
    raw = session.get(RawQuote, observation.raw_quote_id)
    if raw is None:
        raise HTTPException(status_code=500, detail="Raw provenance is missing")
    job = session.get(CollectionJob, raw.collection_job_id)
    if job is None:
        raise HTTPException(status_code=500, detail="Collection job provenance is missing")
    run = session.get(CollectionRun, job.collection_run_id)
    route = session.get(Route, job.route_id)
    source = session.get(Source, job.source_id)
    if run is None or route is None or source is None:
        raise HTTPException(status_code=500, detail="Collection provenance is incomplete")
    return ObservationProvenanceResponse(
        source_code=source.code,
        source_name=source.name,
        route=f"{route.origin_iata}-{route.destination_iata}",
        collection_run_id=run.id,
        collection_job_id=job.id,
        observation=FareObservationResponse.model_validate(observation),
        raw_quote=RawQuoteResponse.model_validate(raw),
    )
