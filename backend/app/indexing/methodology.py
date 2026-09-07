from __future__ import annotations

from decimal import Decimal

from app.domain.enums import PublicationStatus
from app.indexing.base import (
    IndexComponentInput,
    IndexComponentResult,
    IndexMethodology,
    IndexResult,
)
from app.indexing.price_relative import price_relative
from app.indexing.weights import coverage_percent, validate_weights

METHODOLOGY_VERSION = "prototype-v0.1.0"


class PrototypeFixedWeightMethodology(IndexMethodology):
    version = METHODOLOGY_VERSION

    def __init__(self, minimum_coverage_percent: Decimal = Decimal("80")) -> None:
        if minimum_coverage_percent < 0 or minimum_coverage_percent > 100:
            raise ValueError("minimum coverage must be between 0 and 100")
        self.minimum_coverage_percent = minimum_coverage_percent

    def calculate(
        self,
        observations: list[IndexComponentInput],
        *,
        basket_complete: bool,
    ) -> IndexResult:
        ordered = sorted(observations, key=lambda item: str(item.basket_item_id))
        total_weight = validate_weights([item.configured_weight for item in ordered])
        available = [
            item
            for item in ordered
            if item.current_price is not None
            and item.current_price > 0
            and item.base_price is not None
            and item.base_price > 0
        ]
        available_weight = sum(
            (item.configured_weight for item in available),
            Decimal("0"),
        )
        coverage = coverage_percent(
            available_weight=available_weight,
            total_weight=total_weight,
        )

        components: list[IndexComponentResult] = []
        contributions: list[Decimal] = []
        for item in ordered:
            reason = self._availability_reason(item)
            if reason != "AVAILABLE" or available_weight == 0:
                components.append(
                    IndexComponentResult(
                        basket_item_id=item.basket_item_id,
                        daily_route_window_price_id=item.daily_route_window_price_id,
                        current_price=item.current_price,
                        base_price=item.base_price,
                        price_relative=None,
                        configured_weight=item.configured_weight,
                        effective_weight=None,
                        contribution=None,
                        availability_reason=reason,
                    )
                )
                continue
            assert item.current_price is not None
            assert item.base_price is not None
            relative = price_relative(item.current_price, item.base_price)
            effective_weight = item.configured_weight / available_weight
            contribution = effective_weight * relative
            contributions.append(contribution)
            components.append(
                IndexComponentResult(
                    basket_item_id=item.basket_item_id,
                    daily_route_window_price_id=item.daily_route_window_price_id,
                    current_price=item.current_price,
                    base_price=item.base_price,
                    price_relative=relative,
                    configured_weight=item.configured_weight,
                    effective_weight=effective_weight,
                    contribution=contribution,
                    availability_reason=reason,
                )
            )

        calculated_value = sum(contributions, Decimal("0")) if contributions else None
        if not basket_complete:
            status = PublicationStatus.PROVISIONAL_BASE
            index_value = None
        elif coverage >= self.minimum_coverage_percent:
            status = PublicationStatus.PUBLISHED
            index_value = calculated_value
        else:
            status = PublicationStatus.INSUFFICIENT_COVERAGE
            index_value = calculated_value
        return IndexResult(
            index_value=index_value,
            coverage_percent=coverage,
            publication_status=status,
            components=tuple(components),
        )

    @staticmethod
    def _availability_reason(item: IndexComponentInput) -> str:
        if item.current_price is None or item.current_price <= 0:
            return "MISSING_CURRENT_PRICE"
        if item.base_price is None or item.base_price <= 0:
            return "MISSING_BASE_PRICE"
        return "AVAILABLE"
