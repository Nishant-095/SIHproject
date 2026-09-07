from __future__ import annotations

from app.collectors.base import FareSourceAdapter
from app.collectors.duffel import DuffelAdapter
from app.collectors.fixture import FixtureAdapter
from app.collectors.permissioned_web import PermissionedWebAdapter
from app.collectors.web_profile import load_web_extraction_profile
from app.core.config import Settings


class AdapterRegistry:
    def __init__(self, adapters: list[FareSourceAdapter] | None = None) -> None:
        self._adapters: dict[str, FareSourceAdapter] = {}
        for adapter in adapters or []:
            self.register(adapter)

    def register(self, adapter: FareSourceAdapter) -> None:
        self._adapters[adapter.source_code] = adapter

    def get(self, source_code: str) -> FareSourceAdapter:
        try:
            return self._adapters[source_code]
        except KeyError as exc:
            raise KeyError(f"No adapter registered for source {source_code}") from exc


def default_registry(settings: Settings | None = None) -> AdapterRegistry:
    adapters: list[FareSourceAdapter] = [FixtureAdapter()]
    if settings is not None and settings.duffel_access_token is not None:
        adapters.append(
            DuffelAdapter(
                access_token=settings.duffel_access_token.get_secret_value(),
                base_url=settings.duffel_api_base_url,
                expected_live_mode=settings.duffel_live_mode,
                supplier_timeout_ms=settings.duffel_supplier_timeout_ms,
            )
        )
    if settings is not None and settings.web_source_profile_path is not None:
        profile = load_web_extraction_profile(settings.web_source_profile_path)
        adapters.append(
            PermissionedWebAdapter(
                profile=profile,
                permission_confirmed=settings.web_source_approved,
                permission_reference=settings.web_source_permission_reference,
                user_agent=settings.web_source_user_agent,
                browser_timeout_ms=settings.web_source_browser_timeout_ms,
            )
        )
    return AdapterRegistry(adapters)
