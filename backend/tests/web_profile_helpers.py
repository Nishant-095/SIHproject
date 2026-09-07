from __future__ import annotations

from app.collectors.web_profile import WebExtractionProfile


def web_profile(base_url: str = "https://portal.example.com") -> WebExtractionProfile:
    return WebExtractionProfile.model_validate(
        {
            "profile_version": "test-portal-v1",
            "source_code": "PERMISSIONED_WEB",
            "source_name": "Permissioned Test Portal",
            "source_type": "AIRLINE_DIRECT",
            "base_url": base_url,
            "robots_url": f"{base_url}/robots.txt",
            "search_url_template": (
                f"{base_url}/search?origin={{origin}}&destination={{destination}}"
                "&date={travel_date}&adults={passenger_count}&cabin={cabin}"
                "&currency={currency}"
            ),
            "quote_selector": "[data-airfare-quote]",
            "no_results_selector": "[data-no-flight-results]",
            "max_quotes": 20,
            "fields": {
                "airline_name": {"attribute": "data-airline-name"},
                "carrier_code": {"attribute": "data-carrier-code"},
                "flight_number": {"attribute": "data-flight-number"},
                "origin": {"attribute": "data-origin"},
                "destination": {"attribute": "data-destination"},
                "departure_time": {"selector": ".departure-time"},
                "arrival_time": {"selector": ".arrival-time"},
                "currency": {"attribute": "data-currency"},
                "base_fare": {"selector": ".base-fare"},
                "taxes": {"selector": ".taxes"},
                "udf": {"selector": ".udf"},
                "convenience_fee": {"selector": ".convenience-fee"},
                "other_fees": {"selector": ".other-fees"},
                "total_fare": {"selector": ".total-fare"},
                "fare_class": {"attribute": "data-fare-class"},
                "cabin_class": {"attribute": "data-cabin-class"},
                "is_nonstop": {"attribute": "data-is-nonstop"},
                "availability": {"attribute": "data-availability"},
            },
        }
    )


def valid_card(
    *,
    origin: str = "DEL",
    destination: str = "BOM",
    travel_date: str = "2099-01-08",
) -> dict[str, str | None]:
    return {
        "airline_name": "Air India",
        "carrier_code": "AI",
        "flight_number": "AI 2421",
        "origin": origin,
        "destination": destination,
        "departure_time": f"{travel_date}T09:20:00+05:30",
        "arrival_time": f"{travel_date}T11:35:00+05:30",
        "currency": "INR",
        "base_fare": "₹ 4,500.00",
        "taxes": "500.00",
        "udf": "150.00",
        "convenience_fee": "100.00",
        "other_fees": "0.00",
        "total_fare": "INR 5,250.00",
        "fare_class": "PUBLIC_ECONOMY",
        "cabin_class": "economy",
        "is_nonstop": "direct",
        "availability": "available",
    }
