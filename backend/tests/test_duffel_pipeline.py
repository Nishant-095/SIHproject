from __future__ import annotations

import asyncio
import json
from datetime import date

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.collectors.duffel import DuffelAdapter
from app.collectors.registry import AdapterRegistry
from app.core.config import Settings
from app.domain.enums import DataClass, RunStatus
from app.models import CanonicalFare, FareObservation, RawQuote
from app.services.collection import CollectionService


def test_duffel_contract_fixture_runs_full_pipeline_without_live_claim(
    session: Session,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        search_slice = body["data"]["slices"][0]
        origin = search_slice["origin"]
        destination = search_slice["destination"]
        travel_date = search_slice["departure_date"]
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": f"orq_{origin}_{destination}_{travel_date}",
                    "live_mode": False,
                    "fixture_origin": "HAND_AUTHORED_CONTRACT_FIXTURE",
                    "offers": [
                        {
                            "id": f"off_{origin}_{destination}_{travel_date}",
                            "total_amount": "5000.00",
                            "total_currency": "INR",
                            "base_amount": "4300.00",
                            "tax_amount": "700.00",
                            "expires_at": f"{travel_date}T06:00:00Z",
                            "slices": [
                                {
                                    "segments": [
                                        {
                                            "origin": {"iata_code": origin},
                                            "destination": {"iata_code": destination},
                                            "departing_at": f"{travel_date}T09:20:00",
                                            "arriving_at": f"{travel_date}T11:30:00",
                                            "marketing_carrier": {
                                                "iata_code": "AI",
                                                "name": "Air India",
                                            },
                                            "operating_carrier": {
                                                "iata_code": "AI",
                                                "name": "Air India",
                                            },
                                            "marketing_carrier_flight_number": "2421",
                                        }
                                    ]
                                }
                            ],
                        }
                    ],
                }
            },
        )

    async def run_pipeline():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            settings = Settings(
                app_env="test",
                database_url="sqlite+pysqlite:///:memory:",
                duffel_access_token="recorded-test-token",
                duffel_source_enabled=True,
                duffel_source_approved=True,
                duffel_live_mode=False,
                adapter_max_retries=0,
                enforce_source_rate_limits=False,
            )
            adapter = DuffelAdapter(
                access_token="recorded-test-token",
                expected_live_mode=False,
                client=client,
            )
            return await CollectionService(settings, AdapterRegistry([adapter])).run_duffel(
                session,
                methodological_date=date(2026, 9, 9),
            )

    result = asyncio.run(run_pipeline())
    assert result.run.status is RunStatus.COMPLETED
    assert result.run.data_class is DataClass.RECORDED_DEMO
    assert result.run.planned_jobs == 15
    assert result.run.successful_jobs == 15
    assert result.run.failed_jobs == 0
    assert result.run.valid_observations == 15
    assert session.scalar(select(func.count(RawQuote.id))) == 15
    assert session.scalar(select(func.count(FareObservation.id))) == 15
    assert session.scalar(select(func.count(CanonicalFare.id))) == 15
    assert all(session.scalars(select(FareObservation.included_in_index)))
    for payload in session.scalars(select(RawQuote.raw_payload)):
        assert payload["live_mode"] is False
        assert "recorded-test-token" not in json.dumps(payload)
