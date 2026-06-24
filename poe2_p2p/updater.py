from __future__ import annotations

from dataclasses import dataclass

from . import __version__


DEFAULT_RELEASE_API_URL = "https://api.github.com/repos/gospeeel/poe2-p2p/releases/latest"


@dataclass(frozen=True)
class UpdateStatus:
    checked: bool
    update_available: bool
    current_version: str
    latest_version: str | None = None
    download_url: str | None = None
    message: str = ""


def check_for_updates(api_url: str = DEFAULT_RELEASE_API_URL) -> UpdateStatus:
    try:
        import requests
    except ImportError as error:
        return UpdateStatus(
            checked=False,
            update_available=False,
            current_version=__version__,
            message=f"Не удалось проверить обновления: не установлен requests ({error}).",
        )

    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except Exception as error:
        return UpdateStatus(
            checked=False,
            update_available=False,
            current_version=__version__,
            message=f"Не удалось проверить обновления: {error}",
        )

    latest = str(payload.get("tag_name") or "").lstrip("v")
    asset_url = _installer_asset_url(payload)
    update_available = _version_tuple(latest) > _version_tuple(__version__)
    if update_available:
        message = f"Доступна версия {latest}. Скачай установщик из Releases."
    else:
        message = f"Установлена актуальная версия {__version__}."
    return UpdateStatus(
        checked=True,
        update_available=update_available,
        current_version=__version__,
        latest_version=latest,
        download_url=asset_url,
        message=message,
    )


def _installer_asset_url(payload: dict) -> str | None:
    for asset in payload.get("assets", []):
        name = str(asset.get("name", ""))
        if name.endswith("Setup.exe"):
            return asset.get("browser_download_url")
    return payload.get("html_url")


def _version_tuple(value: str) -> tuple[int, ...]:
    parts = []
    for part in value.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts or [0])
