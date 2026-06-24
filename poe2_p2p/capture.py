from __future__ import annotations

from pathlib import Path

from .config import CropRegion


class CaptureDependencyError(RuntimeError):
    pass


def crop_image_file(image_path: str | Path, region: CropRegion, output_path: str | Path):
    try:
        from PIL import Image
    except ImportError as error:
        raise CaptureDependencyError(
            "Pillow is required for image cropping. Install requirements.txt."
        ) from error

    with Image.open(image_path) as image:
        cropped = image.crop(region.as_box())
        cropped.save(output_path)
        return cropped


def capture_screen_region(region: CropRegion, output_path: str | Path | None = None):
    try:
        import mss
        from PIL import Image
    except ImportError as error:
        raise CaptureDependencyError(
            "mss and Pillow are required for screen capture. Install requirements.txt."
        ) from error

    with mss.mss() as screen:
        raw = screen.grab(region.as_mss())
        image = Image.frombytes("RGB", raw.size, raw.rgb)
        if output_path:
            image.save(output_path)
        return image
