from __future__ import annotations

import re

AIRPORT_ALIASES: dict[str, str] = {
    "DEL": "DEL",
    "DELHI": "DEL",
    "NEW DELHI": "DEL",
    "INDIRA GANDHI INTERNATIONAL": "DEL",
    "BOM": "BOM",
    "MUMBAI": "BOM",
    "CHHATRAPATI SHIVAJI MAHARAJ INTERNATIONAL": "BOM",
    "BLR": "BLR",
    "BENGALURU": "BLR",
    "BANGALORE": "BLR",
    "KEMPEGOWDA INTERNATIONAL": "BLR",
}

CARRIER_NAMES: dict[str, str] = {
    "6E": "IndiGo",
    "AI": "Air India",
    "IX": "Air India Express",
    "SG": "SpiceJet",
    "QP": "Akasa Air",
    "UK": "Vistara",
    "G8": "Go First",
    "I5": "AIX Connect",
}

CARRIER_ALIASES: dict[str, str] = {
    **{code: code for code in CARRIER_NAMES},
    "INDIGO": "6E",
    "INTERGLOBE AVIATION": "6E",
    "AIR INDIA": "AI",
    "AIR INDIA LIMITED": "AI",
    "AIR INDIA EXPRESS": "IX",
    "SPICEJET": "SG",
    "AKASA": "QP",
    "AKASA AIR": "QP",
    "VISTARA": "UK",
    "TATA SIA AIRLINES": "UK",
    "GO FIRST": "G8",
    "GOAIR": "G8",
    "AIX CONNECT": "I5",
    "AIRASIA INDIA": "I5",
}


def _key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().upper())


def normalize_airport(value: str | None) -> str | None:
    if not value:
        return None
    return AIRPORT_ALIASES.get(_key(value))


def normalize_carrier(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    candidate = _key(value)
    code = CARRIER_ALIASES.get(candidate)
    if code is None and re.fullmatch(r"[A-Z0-9]{2,3}", candidate):
        code = candidate
    if code is None:
        return None, value.strip()
    return code, CARRIER_NAMES.get(code, value.strip())
