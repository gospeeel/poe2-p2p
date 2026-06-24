from __future__ import annotations

import logging
from pathlib import Path
import sys


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "poe2-p2p.log"


def configure_logging() -> Path:
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        encoding="utf-8",
    )
    sys.excepthook = _log_exception
    logging.getLogger(__name__).info("Логирование запущено.")
    return LOG_FILE


def _log_exception(exc_type, exc_value, exc_traceback) -> None:
    logging.getLogger("poe2_p2p").exception(
        "Необработанная ошибка",
        exc_info=(exc_type, exc_value, exc_traceback),
    )
    sys.__excepthook__(exc_type, exc_value, exc_traceback)
