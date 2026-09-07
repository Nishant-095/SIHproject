from __future__ import annotations

from decimal import Decimal


def validate_weights(weights: list[Decimal]) -> Decimal:
    if not weights:
        raise ValueError("index basket must contain at least one weight")
    if any(weight <= 0 for weight in weights):
        raise ValueError("every basket weight must be positive")
    return sum(weights, Decimal("0"))


def coverage_percent(*, available_weight: Decimal, total_weight: Decimal) -> Decimal:
    if available_weight < 0 or available_weight > total_weight:
        raise ValueError("available weight must be within the configured basket weight")
    return Decimal("100") * available_weight / total_weight
