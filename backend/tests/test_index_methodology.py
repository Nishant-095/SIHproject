from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.domain.enums import PublicationStatus
from app.indexing.base import IndexComponentInput
from app.indexing.methodology import PrototypeFixedWeightMethodology


def _item(
    number: int,
    current: str | None,
    base: str | None,
    weight: str,
) -> IndexComponentInput:
    return IndexComponentInput(
        basket_item_id=uuid.UUID(int=number),
        daily_route_window_price_id=uuid.UUID(int=100 + number),
        current_price=None if current is None else Decimal(current),
        base_price=None if base is None else Decimal(base),
        configured_weight=Decimal(weight),
    )


def test_hand_calculated_fixed_weight_apix_is_exact_and_order_independent() -> None:
    inputs = [
        _item(1, "110", "100", "0.5"),
        _item(2, "90", "100", "0.3"),
        _item(3, "100", "100", "0.2"),
    ]
    methodology = PrototypeFixedWeightMethodology()

    forward = methodology.calculate(inputs, basket_complete=True)
    reverse = methodology.calculate(list(reversed(inputs)), basket_complete=True)

    assert forward == reverse
    assert forward.index_value == Decimal("102.0")
    assert forward.coverage_percent == Decimal("100")
    assert forward.publication_status is PublicationStatus.PUBLISHED
    assert sum(
        (component.contribution or Decimal("0") for component in forward.components),
        Decimal("0"),
    ) == Decimal("102.0")


def test_missing_items_are_not_imputed_and_available_weights_are_renormalized() -> None:
    result = PrototypeFixedWeightMethodology().calculate(
        [
            _item(1, "110", "100", "0.5"),
            _item(2, "90", "100", "0.3"),
            _item(3, None, "100", "0.2"),
        ],
        basket_complete=True,
    )

    assert result.coverage_percent == Decimal("80.0")
    assert result.index_value == Decimal("102.500")
    assert result.publication_status is PublicationStatus.PUBLISHED
    missing = next(component for component in result.components if component.current_price is None)
    assert missing.price_relative is None
    assert missing.contribution is None
    assert missing.availability_reason == "MISSING_CURRENT_PRICE"


def test_below_threshold_and_unfrozen_base_are_not_published() -> None:
    insufficient = PrototypeFixedWeightMethodology().calculate(
        [
            _item(1, "110", "100", "0.6"),
            _item(2, None, "100", "0.4"),
        ],
        basket_complete=True,
    )
    assert insufficient.coverage_percent == Decimal("60.0")
    assert insufficient.index_value == Decimal("110.0")
    assert insufficient.publication_status is PublicationStatus.INSUFFICIENT_COVERAGE

    provisional = PrototypeFixedWeightMethodology().calculate(
        [_item(1, "110", "100", "1")],
        basket_complete=False,
    )
    assert provisional.index_value is None
    assert provisional.publication_status is PublicationStatus.PROVISIONAL_BASE


def test_invalid_price_and_weight_inputs_fail_explicitly() -> None:
    with pytest.raises(ValueError, match="positive"):
        PrototypeFixedWeightMethodology().calculate(
            [_item(1, "100", "100", "0")],
            basket_complete=True,
        )
    with pytest.raises(ValueError, match="coverage"):
        PrototypeFixedWeightMethodology(Decimal("101"))
