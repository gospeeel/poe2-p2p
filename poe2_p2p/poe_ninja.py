from __future__ import annotations

from urllib.parse import urlencode

from .candidates import parse_poe_ninja_currency_rows, shortlist_candidates
from .models import Candidate


DEFAULT_POE_NINJA_LEAGUE = "Runes of Aldur"
DEFAULT_POE_NINJA_POE2_CURRENCY_URL = (
    "https://poe.ninja/poe2/api/economy/exchange/current/overview?"
    + urlencode({"league": DEFAULT_POE_NINJA_LEAGUE, "type": "Currency"})
)


def fetch_currency_candidates(
    url: str | None = DEFAULT_POE_NINJA_POE2_CURRENCY_URL,
    league: str | None = None,
    limit: int = 25,
    min_volume_per_hour: float = 0.0,
) -> list[Candidate]:
    try:
        import requests
    except ImportError as error:
        raise RuntimeError("requests is required to fetch poe.ninja data") from error

    request_url = url or DEFAULT_POE_NINJA_POE2_CURRENCY_URL
    if league:
        request_url = (
            "https://poe.ninja/poe2/api/economy/exchange/current/overview?"
            + urlencode({"league": league, "type": "Currency"})
        )
    response = requests.get(request_url, timeout=15)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as error:
        content_type = response.headers.get("content-type", "unknown")
        raise RuntimeError(f"poe.ninja returned non-JSON response: {content_type}") from error
    candidates = parse_poe_ninja_currency_rows(payload)
    return shortlist_candidates(
        candidates,
        limit=limit,
        min_volume_per_hour=min_volume_per_hour,
    )
