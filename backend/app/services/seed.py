from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.duffel import DuffelAdapter
from app.collectors.fixture import FixtureAdapter
from app.collectors.permissioned_web import PermissionedWebAdapter
from app.collectors.web_profile import load_web_extraction_profile
from app.core.config import Settings
from app.domain.enums import SourceReviewStatus, SourceType
from app.models import Route, Source

ROUTE_SEEDS: tuple[tuple[str, str, str], ...] = (
    ("DEL", "BOM", "Canonical north-west trunk example for the Level-A MVP."),
    ("DEL", "BLR", "Canonical north-south trunk example for the Level-A MVP."),
    ("BOM", "BLR", "Canonical west-south trunk example for the Level-A MVP."),
)


def seed_configuration(session: Session, settings: Settings | None = None) -> None:
    for origin, destination, basis in ROUTE_SEEDS:
        existing_route = session.scalar(
            select(Route).where(
                Route.origin_iata == origin,
                Route.destination_iata == destination,
            )
        )
        if existing_route is None:
            session.add(
                Route(
                    origin_iata=origin,
                    destination_iata=destination,
                    active=True,
                    selection_basis=basis,
                )
            )

    fixture_source = session.scalar(select(Source).where(Source.code == FixtureAdapter.source_code))
    if fixture_source is None:
        session.add(
            Source(
                code=FixtureAdapter.source_code,
                name="Local deterministic fixture",
                source_type=SourceType.FIXTURE,
                base_url=None,
                enabled=True,
                collection_method="FIXTURE",
                review_status=SourceReviewStatus.APPROVED,
                reviewed_at=None,
                rate_limit_per_minute=None,
                max_concurrency=1,
                parser_version=FixtureAdapter.parser_version,
            )
        )

    duffel_source = session.scalar(select(Source).where(Source.code == DuffelAdapter.source_code))
    duffel_enabled = bool(settings and settings.duffel_source_enabled)
    duffel_approved = bool(settings and settings.duffel_source_approved)
    if duffel_enabled and not duffel_approved:
        raise ValueError("DUFFEL_SOURCE_ENABLED requires DUFFEL_SOURCE_APPROVED")
    if duffel_source is None:
        session.add(
            Source(
                code=DuffelAdapter.source_code,
                name="Duffel Flights API",
                source_type=SourceType.OTA,
                base_url=(
                    f"{settings.duffel_api_base_url.rstrip('/')}/air/offer_requests"
                    if settings is not None
                    else "https://api.duffel.com/air/offer_requests"
                ),
                enabled=duffel_enabled,
                collection_method="DOCUMENTED_API",
                review_status=(
                    SourceReviewStatus.APPROVED
                    if duffel_approved
                    else SourceReviewStatus.PENDING_REVIEW
                ),
                reviewed_at=datetime.now(UTC) if duffel_approved else None,
                rate_limit_per_minute=(
                    settings.duffel_rate_limit_per_minute if settings is not None else 5
                ),
                max_concurrency=1,
                parser_version=DuffelAdapter.parser_version,
            )
        )
    else:
        duffel_source.enabled = duffel_enabled
        duffel_source.review_status = (
            SourceReviewStatus.APPROVED if duffel_approved else SourceReviewStatus.PENDING_REVIEW
        )
        if duffel_approved and duffel_source.reviewed_at is None:
            duffel_source.reviewed_at = datetime.now(UTC)
        if settings is not None:
            duffel_source.rate_limit_per_minute = settings.duffel_rate_limit_per_minute
        duffel_source.parser_version = DuffelAdapter.parser_version

    web_source = session.scalar(
        select(Source).where(Source.code == PermissionedWebAdapter.source_code)
    )
    web_enabled = bool(settings and settings.web_source_enabled)
    web_approved = bool(settings and settings.web_source_approved)
    permission_reference = settings.web_source_permission_reference if settings else None
    if web_enabled and not web_approved:
        raise ValueError("WEB_SOURCE_ENABLED requires WEB_SOURCE_APPROVED")
    if web_approved and not permission_reference:
        raise ValueError("WEB_SOURCE_APPROVED requires WEB_SOURCE_PERMISSION_REFERENCE")
    if web_enabled and (settings is None or settings.web_source_profile_path is None):
        raise ValueError("WEB_SOURCE_ENABLED requires WEB_SOURCE_PROFILE_PATH")
    profile = (
        None
        if settings is None or settings.web_source_profile_path is None
        else load_web_extraction_profile(settings.web_source_profile_path)
    )
    web_values = {
        "name": profile.source_name if profile else "Permission-gated web portal",
        "source_type": SourceType(profile.source_type) if profile else SourceType.AIRLINE_DIRECT,
        "base_url": profile.base_url if profile else None,
        "enabled": web_enabled,
        "collection_method": "PERMISSIONED_BROWSER",
        "review_status": (
            SourceReviewStatus.APPROVED if web_approved else SourceReviewStatus.PENDING_REVIEW
        ),
        "rate_limit_per_minute": (
            settings.web_source_rate_limit_per_minute if settings is not None else 2
        ),
        "parser_version": (
            f"{PermissionedWebAdapter.parser_version}:{profile.profile_version}"
            if profile
            else PermissionedWebAdapter.parser_version
        ),
    }
    if web_source is None:
        session.add(
            Source(
                code=PermissionedWebAdapter.source_code,
                reviewed_at=datetime.now(UTC) if web_approved else None,
                max_concurrency=1,
                **web_values,
            )
        )
    else:
        for field, value in web_values.items():
            setattr(web_source, field, value)
        if web_approved and web_source.reviewed_at is None:
            web_source.reviewed_at = datetime.now(UTC)
    session.commit()
