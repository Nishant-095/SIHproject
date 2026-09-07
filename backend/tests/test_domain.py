from datetime import date, time

import pytest

from app.domain.booking_window import classify_advance_window, travel_date_for
from app.domain.enums import AdvanceWindow
from app.domain.flight_identity import canonical_flight_identity_input, flight_identity_hash


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (1, AdvanceWindow.T1),
        (7, AdvanceWindow.T7),
        (15, AdvanceWindow.T15),
        (30, AdvanceWindow.T30),
        (45, AdvanceWindow.T45),
        (2, AdvanceWindow.OTHER),
    ],
)
def test_booking_window_classification(days: int, expected: AdvanceWindow) -> None:
    assert classify_advance_window(days) is expected


def test_travel_date_calculation() -> None:
    assert travel_date_for(date(2026, 9, 5), 45) == date(2026, 10, 20)
    with pytest.raises(ValueError):
        travel_date_for(date(2026, 9, 5), -1)


def test_flight_identity_is_canonical_and_deterministic() -> None:
    identity = canonical_flight_identity_input(
        carrier_code=" 6e ",
        flight_number="6e 1234",
        origin_iata="del",
        destination_iata="bom",
        travel_date=date(2026, 9, 12),
        scheduled_departure_local=time(9, 20),
    )
    assert identity == "6E|6E1234|DEL|BOM|2026-09-12|09:20"
    assert flight_identity_hash(identity) == flight_identity_hash(identity)
    assert len(flight_identity_hash(identity)) == 64
