from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.enums import DataClass
from app.indexing.methodology import METHODOLOGY_VERSION
from app.models import DailyIndex, FareObservation, PeriodIndex, RawQuote
from app.services.exports import build_excel_export, build_json_export
from app.services.historical import build_backtest

router = APIRouter(prefix="/exports", tags=["exports"])


def _csv_response(content: str, filename: str) -> StreamingResponse:
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/fare-observations.csv")
def export_fare_observations(
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
) -> StreamingResponse:
    rows = session.execute(
        select(FareObservation, RawQuote)
        .join(RawQuote, FareObservation.raw_quote_id == RawQuote.id)
        .where(RawQuote.data_class == data_class)
        .order_by(FareObservation.methodological_date, FareObservation.id)
    ).all()
    output = io.StringIO()
    generated_at = datetime.now(UTC).isoformat()
    writer = csv.writer(output)
    writer.writerow(
        [
            "observation_id",
            "raw_quote_id",
            "data_class",
            "methodological_date",
            "observed_at_utc",
            "origin_iata",
            "destination_iata",
            "travel_date",
            "advance_window",
            "carrier_code",
            "flight_number",
            "currency",
            "total_fare",
            "quality_status",
            "included_in_index",
            "exclusion_reason",
            "normalization_version",
            "export_generated_at",
        ]
    )
    for observation, raw in rows:
        writer.writerow(
            [
                observation.id,
                observation.raw_quote_id,
                raw.data_class.value,
                observation.methodological_date,
                observation.observed_at_utc.isoformat(),
                observation.origin_iata,
                observation.destination_iata,
                observation.travel_date,
                observation.advance_window.value,
                observation.carrier_code,
                observation.flight_number,
                observation.currency,
                observation.total_fare,
                observation.quality_status.value,
                observation.included_in_index,
                observation.exclusion_reason,
                observation.normalization_version,
                generated_at,
            ]
        )
    return _csv_response(output.getvalue(), f"fare-observations-{data_class.value.lower()}.csv")


@router.get("/index.csv")
def export_index(
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
) -> StreamingResponse:
    indices = list(
        session.scalars(
            select(DailyIndex)
            .where(DailyIndex.data_class == data_class)
            .order_by(DailyIndex.methodological_date)
        )
    )
    output = io.StringIO()
    generated_at = datetime.now(UTC).isoformat()
    writer = csv.writer(output)
    writer.writerow(
        [
            "daily_index_id",
            "collection_run_id",
            "methodological_date",
            "data_class",
            "index_value",
            "coverage_percent",
            "publication_status",
            "methodology_version",
            "canonicalization_version",
            "calculated_at",
            "export_generated_at",
        ]
    )
    for index in indices:
        writer.writerow(
            [
                index.id,
                index.collection_run_id,
                index.methodological_date,
                index.data_class.value,
                index.index_value,
                index.coverage_percent,
                index.publication_status.value,
                index.methodology_version,
                index.canonicalization_version,
                index.calculated_at.isoformat(),
                generated_at,
            ]
        )
    return _csv_response(output.getvalue(), f"apix-{data_class.value.lower()}.csv")


@router.get("/period-index.csv")
def export_period_index(
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
) -> StreamingResponse:
    rows = list(
        session.scalars(
            select(PeriodIndex)
            .where(PeriodIndex.data_class == data_class)
            .order_by(PeriodIndex.period_start, PeriodIndex.period_type)
        )
    )
    generated_at = datetime.now(UTC).isoformat()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "period_index_id",
            "period_type",
            "period_start",
            "period_end",
            "data_class",
            "index_value",
            "average_coverage_percent",
            "minimum_coverage_percent",
            "expected_day_count",
            "observed_day_count",
            "valued_day_count",
            "low_coverage_day_count",
            "source_count",
            "confidence_level",
            "aggregation_status",
            "warnings",
            "methodology_version",
            "missing_data_policy",
            "calculated_at",
            "export_generated_at",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.period_type.value,
                row.period_start,
                row.period_end,
                row.data_class.value,
                row.index_value,
                row.average_coverage_percent,
                row.minimum_coverage_percent,
                row.expected_day_count,
                row.observed_day_count,
                row.valued_day_count,
                row.low_coverage_day_count,
                row.source_count,
                row.confidence_level.value,
                row.aggregation_status.value,
                "|".join(row.warnings),
                row.methodology_version,
                row.missing_data_policy,
                row.calculated_at.isoformat(),
                generated_at,
            ]
        )
    return _csv_response(output.getvalue(), f"period-apix-{data_class.value.lower()}.csv")


@router.get("/backtest.csv")
def export_backtest(
    dataset_code: str,
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
) -> StreamingResponse:
    try:
        report = build_backtest(session, dataset_code=dataset_code, data_class=data_class)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    generated_at = datetime.now(UTC).isoformat()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "dataset_code",
            "source_url",
            "comparison_method",
            "period_start",
            "period_end",
            "internal_rebased",
            "reference_rebased",
            "deviation_points",
            "deviation_percent",
            "internal_coverage_percent",
            "internal_status",
            "reference_status",
            "correlation",
            "correlation_status",
            "methodology_version",
            "export_generated_at",
        ]
    )
    for point in report.points:
        writer.writerow(
            [
                report.dataset.code,
                report.dataset.source_url,
                report.comparison_method,
                point.period_start,
                point.period_end,
                point.internal_rebased,
                point.reference_rebased,
                point.deviation_points,
                point.deviation_percent,
                point.internal_coverage_percent,
                point.internal_status,
                point.reference_status.value,
                report.correlation,
                report.correlation_status,
                METHODOLOGY_VERSION,
                generated_at,
            ]
        )
    return _csv_response(output.getvalue(), f"backtest-{dataset_code}.csv")


@router.get("/package.json")
def export_json_package(
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
    dataset_code: str | None = None,
) -> Response:
    try:
        package = build_json_export(
            session, data_class=data_class, dataset_code=dataset_code
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    filename = f"airfare-apix-{data_class.value.lower()}.json"
    return Response(
        content=json.dumps(jsonable_encoder(package), indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/analysis.xlsx")
def export_excel_package(
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
    dataset_code: str | None = None,
) -> Response:
    try:
        content = build_excel_export(
            session, data_class=data_class, dataset_code=dataset_code
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    filename = f"airfare-apix-{data_class.value.lower()}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
