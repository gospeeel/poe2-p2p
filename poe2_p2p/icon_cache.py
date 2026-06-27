from __future__ import annotations

import json
import re
from pathlib import Path

from .models import Candidate
from .poe_ninja import fetch_currency_candidates


SAFE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9._-]+")

STATIC_ICON_URLS = {
    "Exalted Orb": "https://web.poecdn.com/gen/image/WzI1LDE0LHsiZiI6IjJESXRlbXMvQ3VycmVuY3kvQ3VycmVuY3lBZGRNb2RUb1JhcmUiLCJzY2FsZSI6MSwicmVhbG0iOiJwb2UyIn1d/f7dd55a5bd/CurrencyAddModToRare.png",
    "Divine Orb": "https://web.poecdn.com/gen/image/WzI1LDE0LHsiZiI6IjJESXRlbXMvQ3VycmVuY3kvQ3VycmVuY3lNb2RWYWx1ZXMiLCJzY2FsZSI6MSwicmVhbG0iOiJwb2UyIn1d/44ec975882/CurrencyModValues.png",
    "Chaos Orb": "https://web.poecdn.com/gen/image/WzI1LDE0LHsiZiI6IjJESXRlbXMvQ3VycmVuY3kvQ3VycmVuY3lSZXJvbGxSYXJlIiwic2NhbGUiOjEsInJlYWxtIjoicG9lMiJ9XQ/5abe6073f4/CurrencyRerollRare.png",
    "Omen of Whittling": "https://web.poecdn.com/gen/image/WzI1LDE0LHsiZiI6IjJESXRlbXMvQ3VycmVuY3kvT21lbnMvVm9vZG9vT21lbnMxRGFyayIsInNjYWxlIjoxLCJyZWFsbSI6InBvZTIifV0/2dea0999d5/VoodooOmens1Dark.png",
}


class IconCache:
    def __init__(self, root: str | Path = "icon_cache") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self.index = self._load_index()

    def cached_icon_path(self, name: str) -> Path | None:
        path = self.index.get(name)
        if not path:
            return None
        candidate = self.root / path
        return candidate if candidate.exists() else None

    def cache_candidates(self, candidates: list[Candidate]) -> int:
        return self.cache_icon_urls(
            {candidate.name: candidate.image_url for candidate in candidates if candidate.image_url}
        )

    def cache_static_icons(self, names: list[str] | tuple[str, ...] | set[str] | None = None) -> int:
        urls = STATIC_ICON_URLS
        if names is not None:
            requested = set(names)
            urls = {name: url for name, url in STATIC_ICON_URLS.items() if name in requested}
        return self.cache_icon_urls(urls)

    def cache_poe_ninja_icons_for_names(
        self,
        names: list[str] | tuple[str, ...] | set[str],
        league: str | None = None,
        limit: int = 200,
    ) -> int:
        requested = set(names)
        if not requested:
            return 0
        candidates = fetch_currency_candidates(league=league, limit=limit)
        matches = [
            candidate
            for candidate in candidates
            if candidate.name in requested and candidate.image_url
        ]
        return self.cache_candidates(matches)

    def cache_icon_urls(self, icon_urls: dict[str, str | None]) -> int:
        try:
            import requests
        except ImportError as error:
            raise RuntimeError("Для загрузки иконок нужен пакет requests.") from error

        saved = 0
        for name, image_url in icon_urls.items():
            if not image_url:
                continue
            filename = f"{_safe_name(name)}{_extension_from_url(image_url)}"
            output = self.root / filename
            if not output.exists():
                response = requests.get(image_url, timeout=15)
                response.raise_for_status()
                output.write_bytes(response.content)
                saved += 1
            self.index[name] = filename
        self._save_index()
        return saved

    def _load_index(self) -> dict[str, str]:
        if not self.index_path.exists():
            return {}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _save_index(self) -> None:
        self.index_path.write_text(
            json.dumps(self.index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def cache_poe_ninja_icons(
    cache_dir: str | Path = "icon_cache",
    league: str | None = None,
    limit: int = 100,
) -> int:
    candidates = fetch_currency_candidates(league=league, limit=limit)
    return IconCache(cache_dir).cache_candidates(candidates)


def _safe_name(name: str) -> str:
    return SAFE_NAME_PATTERN.sub("_", name).strip("_").lower()


def _extension_from_url(url: str) -> str:
    suffix = Path(url.split("?", 1)[0]).suffix.lower()
    return suffix if suffix in {".png", ".jpg", ".jpeg", ".webp"} else ".png"
