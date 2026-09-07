from __future__ import annotations

import asyncio
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import FareObservation
from app.services.collection import CollectionService


def test_health_and_database_readiness(client: TestClient) -> None:
    health = client.get("/health")
    readiness = client.get("/ready")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert readiness.status_code == 200
    assert readiness.json() == {"status": "ready", "database": "connected"}


def test_fixture_admin_api_is_protected_and_idempotent(client: TestClient) -> None:
    assert client.post("/api/v1/admin/collection-runs/fixture").status_code == 401

    response = client.post(
        "/api/v1/admin/collection-runs/fixture?methodological_date=2026-09-05",
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["created"] is True
    assert body["data_class"] == "SYNTHETIC"
    assert body["planned_jobs"] == 15
    assert body["successful_jobs"] == 15
    assert len(body["jobs"]) == 15

    repeated = client.post(
        "/api/v1/admin/collection-runs/fixture?methodological_date=2026-09-05",
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert repeated.status_code == 200
    assert repeated.json()["created"] is False
    assert repeated.json()["id"] == body["id"]


def test_duffel_admin_api_is_protected_and_fails_closed_without_configuration(
    client: TestClient,
) -> None:
    endpoint = "/api/v1/admin/collection-runs/duffel?methodological_date=2026-09-05"
    assert client.post(endpoint).status_code == 401
    response = client.post(endpoint, headers={"X-Admin-Token": "test-admin-token"})
    assert response.status_code == 409
    assert response.json()["detail"] == "DUFFEL_ACCESS_TOKEN is required"


def test_permissioned_web_admin_api_is_protected_and_fails_closed_without_approval(
    client: TestClient,
) -> None:
    endpoint = "/api/v1/admin/collection-runs/permissioned-web?methodological_date=2026-09-05"
    assert client.post(endpoint).status_code == 401
    response = client.post(endpoint, headers={"X-Admin-Token": "test-admin-token"})
    assert response.status_code == 409
    assert response.json()["detail"] == "WEB_SOURCE_APPROVED must be true"


def test_routes_observation_and_provenance_api(client: TestClient, session: Session) -> None:
    asyncio.run(
        CollectionService(
            Settings(app_env="test", database_url="sqlite+pysqlite:///:memory:")
        ).run_fixture(
            session,
            methodological_date=date(2026, 9, 7),
        )
    )
    routes = client.get("/api/v1/routes")
    assert routes.status_code == 200
    assert {(item["origin_iata"], item["destination_iata"]) for item in routes.json()} == {
        ("DEL", "BOM"),
        ("DEL", "BLR"),
        ("BOM", "BLR"),
    }

    observation = session.scalar(select(FareObservation).order_by(FareObservation.id))
    assert observation is not None
    response = client.get(f"/api/v1/observations/{observation.id}")
    provenance = client.get(f"/api/v1/observations/{observation.id}/provenance")
    assert response.status_code == 200
    assert response.json()["included_in_index"] is True
    assert provenance.status_code == 200
    assert provenance.json()["source_code"] == "FIXTURE_LOCAL"
    assert provenance.json()["raw_quote"]["raw_payload"]["fixture"] is True
