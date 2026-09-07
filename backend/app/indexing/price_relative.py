from __future__ import annotations

from decimal import Decimal


def price_relative(current_price: Decimal, base_price: Decimal) -> Decimal:
    if current_price <= 0:
        raise ValueError("current price must be positive")
    if base_price <= 0:
        raise ValueError("base price must be positive")
    return Decimal("100") * current_price / base_price
