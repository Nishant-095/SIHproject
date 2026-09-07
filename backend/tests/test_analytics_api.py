from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import DataClass
from app.indexing.basket import ensure_mvp_basket, set_seeded_base_prices
from app.models import BasketItem, Source


def _create_index(client: TestClient, session: Session) -> dict[str, object]:
    collection = client.post(
        "/api/v1/admin/collection-runs/fixture?methodological_date=2027-05-01",
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert collection.status_code == 200
    basket = ensure_mvp_basket(session, DataClass.SYNTHETIC)
    items = list(
        session.scalars(select(BasketItem).where(BasketItem.basket_version_id == basket.id))
    )
    set_seeded_base_prices(
        session,
        basket,
        {item.id: Decimal("5000") for item in items},
        base_date=date(2027, 4, 30),
    )
    response = client.post(
        f"/api/v1/admin/index/recalculate?run_id={collection.json()['id']}",
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert response.status_code == 200
    return response.json()


def test_index_endpoints_publish_persisted_components(
    client: TestClient,
    session: Session,
) -> None:
    unauthorized = client.post(
        "/api/v1/admin/index/recalculate?run_id=00000000-0000-0000-0000-000000000000"
    )
    assert unauthorized.status_code == 401
    created = _create_index(client, session)
    assert created["publication_status"] == "PUBLISHED"
    assert created["index_value"] is not None
    assert created["coverage_percent"] == "100.0000"
    assert len(created["components"]) == 15

    current = client.get("/api/v1/index/current")
    daily = client.get("/api/v1/index/daily/2027-05-01")
    history = client.get("/api/v1/index/history")
    assert current.status_code == daily.status_code == history.status_code == 200
    assert current.json()["id"] == created["id"]
    assert daily.json()["methodology_version"] == "prototype-v0.1.0"
    assert history.json()[0]["index_value"] == created["index_value"]


def test_dashboard_read_apis_cover_routes_quality_operations_and_exports(
    client: TestClient,
    session: Session,
) -> None:
    _create_index(client, session)

    observations = client.get(
        "/api/v1/observations?origin=del&destination=bom&included_in_index=true"
    )
    route = client.get("/api/v1/routes/DEL/BOM")
    history = client.get("/api/v1/routes/DEL/BOM/history")
    lead_time = client.get("/api/v1/routes/DEL/BOM/lead-time")
    quality = client.get("/api/v1/quality/summary")
    runs = client.get("/api/v1/collection-runs")
    fare_export = client.get("/api/v1/exports/fare-observations.csv")
    index_export = client.get("/api/v1/exports/index.csv")

    assert observations.status_code == 200
    assert observations.json()
    assert all(item["origin_iata"] == "DEL" for item in observations.json())
    assert route.status_code == 200
    assert route.json()["latest_route_index"] is not None
    assert history.status_code == 200 and len(history.json()) == 1
    assert lead_time.status_code == 200 and lead_time.json()["points"]
    assert quality.status_code == 200
    assert quality.json()["total_observations"] == 30
    assert quality.json()["included_observations"] == 30
    assert runs.status_code == 200 and len(runs.json()) == 1
    assert fare_export.status_code == 200
    assert "observation_id,raw_quote_id,data_class" in fare_export.text
    assert index_export.status_code == 200
    assert "daily_index_id,collection_run_id" in index_export.text


def test_phase_13_coverage_and_period_aggregates_are_explicit(
    client: TestClient,
    session: Session,
) -> None:
    _create_index(client, session)
    coverage = client.get("/api/v1/index/current/coverage")
    weekly = client.get("/api/v1/index/weekly")
    monthly = client.get("/api/v1/index/monthly")

    assert coverage.status_code == weekly.status_code == monthly.status_code == 200
    payload = coverage.json()
    assert payload["coverage_percent"] == "100.0000"
    assert payload["source_count"] == 1
    assert payload["confidence_level"] == "LOW"
    assert payload["missing_data_policy"]["imputation"] == "NONE"
    assert payload["missing_data_policy"]["minimum_publication_coverage_percent"] == "80"
    assert len(payload["routes"]) == 3
    assert all(route["coverage_percent"] == "100.0000" for route in payload["routes"])
    assert payload["source_dispersion"] == [
        {"source_code": "FIXTURE_LOCAL", "observation_count": 30, "share_percent": "100.00"}
    ]
    assert payload["warnings"] == ["SINGLE_SOURCE"]

    assert len(weekly.json()) == len(monthly.json()) == 1
    assert weekly.json()[0]["period_type"] == "WEEKLY"
    assert weekly.json()[0]["aggregation_status"] == "PARTIAL"
    assert weekly.json()[0]["confidence_level"] == "LOW"
    assert "PARTIAL_PERIOD" in weekly.json()[0]["warnings"]
    assert monthly.json()[0]["period_type"] == "MONTHLY"
    assert client.post("/api/v1/admin/index/aggregate").status_code == 401


def test_source_controls_are_protected_and_preserve_review_approval(
    client: TestClient,
    session: Session,
) -> None:
    _create_index(client, session)
    source = session.scalar(select(Source).where(Source.code == "FIXTURE_LOCAL"))
    assert source is not None
    assert client.post(f"/api/v1/admin/sources/{source.id}/disable").status_code == 401

    disabled = client.post(
        f"/api/v1/admin/sources/{source.id}/disable",
        headers={"X-Admin-Token": "test-admin-token"},
    )
    enabled = client.post(
        f"/api/v1/admin/sources/{source.id}/enable",
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert disabled.status_code == enabled.status_code == 200
    assert disabled.json()["enabled"] is False
    assert enabled.json()["enabled"] is True
    assert enabled.json()["review_status"] == "APPROVED"


def test_openapi_contains_complete_phase_9_surface(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    expected = {
        "/api/v1/index/current",
        "/api/v1/index/history",
        "/api/v1/index/daily/{methodological_date}",
        "/api/v1/routes/{origin}/{destination}",
        "/api/v1/routes/{origin}/{destination}/history",
        "/api/v1/routes/{origin}/{destination}/lead-time",
        "/api/v1/observations",
        "/api/v1/collection-runs",
        "/api/v1/sources/health",
        "/api/v1/quality/summary",
        "/api/v1/exports/fare-observations.csv",
        "/api/v1/exports/index.csv",
        "/api/v1/admin/index/recalculate",
        "/api/v1/admin/collection-runs",
        "/api/v1/admin/sources/{source_id}/enable",
        "/api/v1/admin/sources/{source_id}/disable",
        "/api/v1/index/current/coverage",
        "/api/v1/index/weekly",
        "/api/v1/index/monthly",
        "/api/v1/admin/index/aggregate",
    }
    assert expected <= set(paths)


def test_generic_admin_collection_run_dispatches_fixture(client: TestClient) -> None:
    response = client.post(
        "/api/v1/admin/collection-runs",
        headers={"X-Admin-Token": "test-admin-token"},
        json={"source": "fixture", "methodological_date": "2027-05-02"},
    )
    assert response.status_code == 200
    assert response.json()["methodological_date"] == "2027-05-02"
    assert response.json()["created"] is True
