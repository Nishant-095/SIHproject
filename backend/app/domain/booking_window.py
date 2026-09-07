from __future__ import annotations

from datetime import date, timedelta

from app.domain.enums import AdvanceWindow

WINDOW_DAYS: tuple[int, ...] = (1, 7, 15, 30, 45)
WINDOW_BY_DAYS: dict[int, AdvanceWindow] = {
    1: AdvanceWindow.T1,
    7: AdvanceWindow.T7,
    15: AdvanceWindow.T15,
    30: AdvanceWindow.T30,
    45: AdvanceWindow.T45,
}


def classify_advance_window(advance_days: int) -> AdvanceWindow:
    return WINDOW_BY_DAYS.get(advance_days, AdvanceWindow.OTHER)


def travel_date_for(observation_date: date, advance_days: int) -> date:
    if advance_days < 0:
        raise ValueError("advance_days cannot be negative")
    return observation_date + timedelta(days=advance_days)
