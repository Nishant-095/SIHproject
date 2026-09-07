from __future__ import annotations

import asyncio
import io
import zipfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.enums import DataClass, RunTrigger
from app.indexing.service import calculate_index_for_run
from app.schemas.historical import HistoricalDatasetImportRequest
from app.services.collection import CollectionService
from app.services.historical import build_backtest, import_historical_dataset, payload_from_csv

REFERENCE_CSV = Path(__file__).parents[2] / "data/reference/mospi-airfare-cpi-sample.csv"
DATASET_CODE = "MOSPI-AIRFARE-CPI-2012-2025-10-SAMPLE"
SOURCE_URL = "https://cpi.mospi.gov.in/PDFile/Press/PR%20October%202025.pdf"


def _reference_payload() -> HistoricalDatasetImportRequest:
    return payload_from_csv(
        REFERENCE_CSV.read_text(encoding="utf-8-sig"),
        code=DATASET_CODE,
        title="MoSPI All India CPI air fare item sample",
        publisher="Ministry of Statistics and Programme Implementation",
        source_url=SOURCE_URL,
        license_name="Government Open Data License - India",
        metric_name="Air fare (normal): economy class (adult), All India Combined CPI",
        frequency="MONTHLY",
        base_period="2012=100",
        notes="Four values transcribed from Annexure V of the October 2025 CPI release.",
    )


def test_historical_import_api_is_protected_idempotent_and_immutable(
    client: TestClient,
) -> None:
    payload = _reference_payload().model_dump(mode="json")
    endpoint = "/api/v1/admin/historical/datasets"
    assert client.post(endpoint, json=payload).status_code == 401

    created = client.post(
        endpoint,
        json=payload,
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert created.status_code == 200
    assert created.json()["row_count"] == 4
    assert created.json()["data_class"] == "HISTORICAL"
    assert len(created.json()["observations"]) == 4

    repeated = client.post(
        endpoint,
        json=payload,
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert repeated.status_code == 200
    assert repeated.json()["id"] == created.json()["id"]

    changed = dict(payload)
    changed["title"] = "Changed content under the same immutable dataset code"
    conflict = client.post(
        endpoint,
        json=changed,
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert conflict.status_code == 409
    assert "versioned code" in conflict.json()["detail"]


def test_thirty_day_backtest_and_all_phase_15_exports(
    session: Session,
    client: TestClient,
) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        enforce_source_rate_limits=False,
    )
    service = CollectionService(settings)
    start_date = date(2025, 9, 15)
    for offset in range(30):
        planned = asyncio.run(
            service.run_fixture(
                session,
                methodological_date=start_date + timedelta(days=offset),
                trigger=RunTrigger.BACKFILL,
            )
        )
        calculate_index_for_run(session, planned.run.id)

    dataset, created = import_historical_dataset(session, _reference_payload())
    assert created is True
    report = build_backtest(
        session,
        dataset_code=dataset.code,
        data_class=DataClass.SYNTHETIC,
    )

    assert report.overlap_month_count == 2
    assert len(report.points) == 2
    assert len(report.route_comparisons) == 6
    assert report.correlation is None
    assert report.correlation_status == "INSUFFICIENT_OVERLAP"
    assert "CORRELATION_INSUFFICIENT_OVERLAP" in report.warnings
    assert {point.reference_status.value for point in report.points} == {
        "FINAL",
        "PROVISIONAL",
    }
    assert {point.internal_coverage_percent for point in report.points} == {
        Decimal("62.5000"),
        Decimal("100.0000"),
    }

    query = f"?data_class=SYNTHETIC&dataset_code={DATASET_CODE}"
    backtest_api = client.get(f"/api/v1/historical/backtest{query}")
    assert backtest_api.status_code == 200
    assert backtest_api.json()["overlap_month_count"] == 2

    package = client.get(f"/api/v1/exports/package.json{query}")
    assert package.status_code == 200
    package_body = package.json()
    assert package_body["metadata"]["methodology_version"] == "prototype-v0.1.0"
    assert package_body["metadata"]["generated_at"]
    assert package_body["current_coverage"]["data_class"] == "SYNTHETIC"
    assert package_body["historical_datasets"][0]["publisher"].startswith("Ministry")
    assert package_body["backtest"]["overlap_month_count"] == 2

    period_csv = client.get("/api/v1/exports/period-index.csv?data_class=SYNTHETIC")
    backtest_csv = client.get(
        f"/api/v1/exports/backtest.csv?dataset_code={DATASET_CODE}&data_class=SYNTHETIC"
    )
    assert period_csv.status_code == 200
    assert "missing_data_policy" in period_csv.text.splitlines()[0]
    assert "export_generated_at" in period_csv.text.splitlines()[0]
    assert backtest_csv.status_code == 200
    assert SOURCE_URL in backtest_csv.text
    assert "prototype-v0.1.0" in backtest_csv.text

    excel = client.get(f"/api/v1/exports/analysis.xlsx{query}")
    assert excel.status_code == 200
    assert excel.content.startswith(b"PK")
    with zipfile.ZipFile(io.BytesIO(excel.content)) as workbook:
        workbook_names = set(workbook.namelist())
        assert "xl/workbook.xml" in workbook_names
        assert sum(name.startswith("xl/worksheets/sheet") for name in workbook_names) == 6


def test_historical_csv_rejects_missing_required_columns() -> None:
    try:
        payload_from_csv(
            "period_start,index_value\n2025-01-01,100\n",
            code="INVALID-SAMPLE",
            title="Invalid historical sample",
            publisher="Example publisher",
            source_url="https://example.com/reference.csv",
            license_name="Example license",
            metric_name="Example metric",
            frequency="MONTHLY",
            base_period=None,
            notes=None,
        )
    except ValueError as exc:
        assert "missing columns" in str(exc)
    else:
        raise AssertionError("invalid historical CSV was accepted")
