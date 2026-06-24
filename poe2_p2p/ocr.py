from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from .parser import parse_ratio


class OCRDependencyError(RuntimeError):
    pass


@dataclass(frozen=True)
class RatioOCRResult:
    raw_text: str
    ratio: tuple[float, float]
    confidence: float


def preprocess_ratio_image(image_path: str | Path):
    try:
        import cv2
    except ImportError as error:
        raise OCRDependencyError(
            "opencv-python is required for OCR preprocessing. Install requirements.txt."
        ) from error

    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    scaled = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    denoised = cv2.GaussianBlur(scaled, (3, 3), 0)
    _, threshold = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return threshold


def read_ratio_from_image(image_path: str | Path) -> RatioOCRResult:
    try:
        import pytesseract
    except ImportError as error:
        raise OCRDependencyError(
            "pytesseract is required for OCR. Install requirements.txt and Tesseract OCR."
        ) from error
    _configure_tesseract_cmd(pytesseract)

    processed = preprocess_ratio_image(image_path)
    config = "--psm 7 -c tessedit_char_whitelist=0123456789:.,"
    try:
        raw_text = pytesseract.image_to_string(processed, config=config).strip()
    except Exception as error:
        if error.__class__.__name__ == "TesseractNotFoundError":
            raise OCRDependencyError(
                "Tesseract OCR binary is not installed or is not in PATH."
            ) from error
        raise
    ratio = parse_ratio(raw_text)

    confidence = 0.80
    try:
        data = pytesseract.image_to_data(processed, config=config, output_type=pytesseract.Output.DICT)
        values = [float(value) for value in data.get("conf", []) if float(value) >= 0]
        if values:
            confidence = sum(values) / len(values) / 100
    except Exception:
        pass

    return RatioOCRResult(raw_text=raw_text, ratio=ratio, confidence=confidence)


def _configure_tesseract_cmd(pytesseract_module) -> None:
    configured = os.environ.get("TESSERACT_CMD")
    if configured:
        pytesseract_module.pytesseract.tesseract_cmd = configured
        return

    common_windows_path = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
    if common_windows_path.exists():
        pytesseract_module.pytesseract.tesseract_cmd = str(common_windows_path)
