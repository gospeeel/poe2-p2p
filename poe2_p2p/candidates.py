from __future__ import annotations

from .models import Candidate


def parse_poe_ninja_currency_rows(payload: dict) -> list[Candidate]:
    rows = payload.get("lines") or payload.get("currencies") or payload.get("items") or []
    item_names = {
        item.get("id"): item.get("name")
        for item in payload.get("items", [])
        if isinstance(item, dict)
    }
    item_images = {
        item.get("id"): item.get("image")
        for item in payload.get("items", [])
        if isinstance(item, dict)
    }
    item_names.update(
        {
            item.get("id"): item.get("name")
            for item in payload.get("core", {}).get("items", [])
            if isinstance(item, dict)
        }
    )
    item_images.update(
        {
            item.get("id"): item.get("image")
            for item in payload.get("core", {}).get("items", [])
            if isinstance(item, dict)
        }
    )
    candidates: list[Candidate] = []
    for index, row in enumerate(rows, start=1):
        name = (
            row.get("currencyTypeName")
            or row.get("name")
            or row.get("currency_name")
            or item_names.get(row.get("id"))
            or row.get("id")
        )
        if not name:
            continue
        value = (
            row.get("chaosEquivalent")
            or row.get("value_in_chaos")
            or row.get("primaryValue")
            or row.get("maxVolumeRate")
            or row.get("receive", {}).get("value")
            or 0
        )
        volume = (
            row.get("volume_per_hour")
            or row.get("volumePrimaryValue")
            or row.get("listing_count")
            or row.get("count")
            or 0
        )
        trend = (
            row.get("details", {}).get("change")
            or row.get("sparkline", {}).get("totalChange")
            or row.get("seven_day_change")
            or row.get("7day_change")
            or 0
        )
        candidates.append(
            Candidate(
                name=str(name),
                value_in_chaos=float(value),
                volume_per_hour=float(volume),
                seven_day_change_percent=_parse_percent(trend),
                popularity_rank=int(row.get("popularity_rank") or index),
                image_url=_normalize_image_url(row.get("image") or item_images.get(row.get("id"))),
            )
        )
    return candidates


def shortlist_candidates(
    candidates: list[Candidate],
    limit: int = 25,
    min_volume_per_hour: float = 0.0,
) -> list[Candidate]:
    filtered = [
        candidate
        for candidate in candidates
        if candidate.volume_per_hour >= min_volume_per_hour
    ]
    return sorted(filtered, key=_candidate_score, reverse=True)[:limit]


def _candidate_score(candidate: Candidate) -> float:
    trend_factor = 1 + max(candidate.seven_day_change_percent, 0) / 100
    return candidate.volume_score * trend_factor


def _parse_percent(value) -> float:
    if isinstance(value, str):
        value = value.strip().replace("%", "")
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _normalize_image_url(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("/"):
        return f"https://poe.ninja{value}"
    return value
