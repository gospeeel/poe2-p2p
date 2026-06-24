from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)


def main() -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []
    for size in sizes:
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            (1, 1, size - 2, size - 2),
            radius=max(3, size // 7),
            fill=(28, 36, 45, 255),
            outline=(92, 142, 255, 255),
            width=max(1, size // 18),
        )
        draw.ellipse(
            (size * 0.18, size * 0.16, size * 0.82, size * 0.80),
            fill=(217, 177, 95, 255),
        )
        text = "P2P"
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", max(8, size // 4))
        except OSError:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (size - (bbox[2] - bbox[0])) / 2
        y = (size - (bbox[3] - bbox[1])) / 2 - 1
        draw.text((x, y), text, fill=(16, 19, 22, 255), font=font)
        images.append(image)

    images[-1].save(ASSETS / "app_icon.png")
    images[-1].save(ASSETS / "app_icon.ico", sizes=[(size, size) for size in sizes])


if __name__ == "__main__":
    main()
