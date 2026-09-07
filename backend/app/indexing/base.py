from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import PublicationStatus


@dataclass(frozen=True, slots=True)
class IndexComponentInput:
    basket_item_id: uuid.UUID
    daily_route_window_price_id: uuid.UUID | None
    current_price: Decimal | None
    base_price: Decimal | None
    configured_weight: Decimal


@dataclass(frozen=True, slots=True)
class IndexComponentResult:
    basket_item_id: uuid.UUID
    daily_route_window_price_id: uuid.UUID | None
    current_price: Decimal | None
    base_price: Decimal | None
    price_relative: Decimal | None
    configured_weight: Decimal
    effective_weight: Decimal | None
    contribution: Decimal | None
    availability_reason: str


@dataclass(frozen=True, slots=True)
class IndexResult:
    index_value: Decimal | None
    coverage_percent: Decimal
    publication_status: PublicationStatus
    components: tuple[IndexComponentResult, ...]


class IndexMethodology(ABC):
    version: str

    @abstractmethod
    def calculate(
        self,
        observations: list[IndexComponentInput],
        *,
        basket_complete: bool,
    ) -> IndexResult:
        """Calculate an index without database or collection concerns."""
