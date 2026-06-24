from __future__ import annotations

import json
import re
from pathlib import Path

from .models import Candidate
from .poe_ninja import fetch_currency_candidates


SAFE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9._-]+")


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
        try:
            import requests
        except ImportError as error:
            raise RuntimeError("Для загрузки иконок нужен пакет requests.") from error

        saved = 0
        for candidate in candidates:
            if not candidate.image_url:
                continue
            filename = f"{_safe_name(candidate.name)}.png"
            output = self.root / filename
            if not output.exists():
                response = requests.get(candidate.image_url, timeout=15)
                response.raise_for_status()
                output.write_bytes(response.content)
                saved += 1
            self.index[candidate.name] = filename
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
