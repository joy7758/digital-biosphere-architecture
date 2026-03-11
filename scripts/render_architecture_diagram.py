from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1600
HEIGHT = 1700
BACKGROUND = "#FFFFFF"
TEXT = "#1F2933"
SUBTLE = "#52606D"
BORDER = "#364152"
BOX_FILL = "#FAFBFC"
LINE = "#4B5563"

TITLE = "Digital Biosphere Architecture"
SUBTITLE = "A governance-oriented architecture for autonomous AI systems"
FOOTER = "A layered model for identity, interaction, control, runtime truth, and evidence."

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "assets/architecture"
SVG_PATH = OUTPUT_DIR / "digital-biosphere-architecture-stack.svg"
PNG_PATH = OUTPUT_DIR / "digital-biosphere-architecture-stack.png"


@dataclass(frozen=True)
class Layer:
    title: str
    label: str


LAYERS = [
    Layer("Persona Layer", "POP"),
    Layer("Interaction Layer", "Agent Intent Protocol"),
    Layer("Governance Layer", "Token Governor"),
    Layer("Execution Integrity Layer", "MVK"),
    Layer("Audit Evidence Layer", "ARO-Audit"),
]


def load_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/Library/Fonts/Arial Bold.ttf",
            ]
        )
    candidates.extend(
        [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        ]
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def layout():
    box_width = 860
    box_height = 140
    top = 260
    gap = 70
    left = (WIDTH - box_width) // 2
    right = left + box_width
    boxes = []
    y = top
    for layer in LAYERS:
        boxes.append(
            {
                "layer": layer,
                "x": left,
                "y": y,
                "width": box_width,
                "height": box_height,
                "right": right,
                "bottom": y + box_height,
            }
        )
        y += box_height + gap
    return boxes


def center_text(draw: ImageDraw.ImageDraw, text: str, font, y: int, fill: str):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (WIDTH - (bbox[2] - bbox[0])) / 2
    draw.text((x, y), text, font=font, fill=fill)


def render_png():
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    title_font = load_font(54, bold=True)
    subtitle_font = load_font(27)
    box_title_font = load_font(40, bold=True)
    box_label_font = load_font(30)
    footer_font = load_font(24)

    center_text(draw, TITLE, title_font, 92, TEXT)
    center_text(draw, SUBTITLE, subtitle_font, 160, SUBTLE)

    for i, box in enumerate(layout()):
        x = box["x"]
        y = box["y"]
        w = box["width"]
        h = box["height"]
        bottom = box["bottom"]
        center_x = WIDTH / 2

        draw.rounded_rectangle(
            [x, y, x + w, y + h],
            radius=18,
            fill=BOX_FILL,
            outline=BORDER,
            width=2,
        )

        title = box["layer"].title
        label = box["layer"].label
        title_bbox = draw.textbbox((0, 0), title, font=box_title_font)
        title_x = (WIDTH - (title_bbox[2] - title_bbox[0])) / 2
        draw.text((title_x, y + 32), title, font=box_title_font, fill=TEXT)

        label_bbox = draw.textbbox((0, 0), label, font=box_label_font)
        label_x = (WIDTH - (label_bbox[2] - label_bbox[0])) / 2
        draw.text((label_x, y + 90), label, font=box_label_font, fill=SUBTLE)

        if i < len(LAYERS) - 1:
            next_y = layout()[i + 1]["y"]
            line_top = bottom + 20
            line_bottom = next_y - 24
            draw.line(
                [(center_x, line_top), (center_x, line_bottom)],
                fill=LINE,
                width=4,
            )
            arrow = [
                (center_x, next_y - 14),
                (center_x - 12, next_y - 34),
                (center_x + 12, next_y - 34),
            ]
            draw.polygon(arrow, fill=LINE)

    center_text(draw, FOOTER, footer_font, 1580, SUBTLE)
    image.save(PNG_PATH, format="PNG", optimize=True)


def render_svg():
    boxes = layout()
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
            f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" '
            'role="img" aria-labelledby="title subtitle">'
        ),
        "  <defs>",
        (
            '    <marker id="arrow" markerWidth="12" markerHeight="12" '
            'refX="6" refY="6" orient="auto" markerUnits="strokeWidth">'
        ),
        f'      <path d="M 0 0 L 12 6 L 0 12 z" fill="{LINE}"/>',
        "    </marker>",
        "  </defs>",
        f'  <rect width="{WIDTH}" height="{HEIGHT}" fill="{BACKGROUND}"/>',
        f'  <title id="title">{escape(TITLE)}</title>',
        f'  <desc id="subtitle">{escape(SUBTITLE)}</desc>',
        (
            '  <text x="800" y="130" text-anchor="middle" '
            'font-family="Helvetica, Arial, sans-serif" font-size="54" '
            f'font-weight="700" fill="{TEXT}">{escape(TITLE)}</text>'
        ),
        (
            '  <text x="800" y="190" text-anchor="middle" '
            'font-family="Helvetica, Arial, sans-serif" font-size="27" '
            f'fill="{SUBTLE}">{escape(SUBTITLE)}</text>'
        ),
    ]

    center_x = WIDTH / 2
    for i, box in enumerate(boxes):
        x = box["x"]
        y = box["y"]
        w = box["width"]
        h = box["height"]
        bottom = box["bottom"]
        parts.extend(
            [
                (
                    f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
                    'rx="18" ry="18" '
                    f'fill="{BOX_FILL}" stroke="{BORDER}" stroke-width="2"/>'
                ),
                (
                    f'  <text x="{center_x}" y="{y + 58}" text-anchor="middle" '
                    'font-family="Helvetica, Arial, sans-serif" font-size="40" '
                    f'font-weight="700" fill="{TEXT}">'
                    f'{escape(box["layer"].title)}</text>'
                ),
                (
                    f'  <text x="{center_x}" y="{y + 112}" text-anchor="middle" '
                    'font-family="Helvetica, Arial, sans-serif" font-size="30" '
                    f'fill="{SUBTLE}">{escape(box["layer"].label)}</text>'
                ),
            ]
        )
        if i < len(boxes) - 1:
            next_y = boxes[i + 1]["y"]
            parts.append(
                (
                    f'  <line x1="{center_x}" y1="{bottom + 20}" '
                    f'x2="{center_x}" y2="{next_y - 22}" '
                    f'stroke="{LINE}" stroke-width="4" marker-end="url(#arrow)"/>'
                )
            )

    parts.append(
        (
            '  <text x="800" y="1600" text-anchor="middle" '
            'font-family="Helvetica, Arial, sans-serif" font-size="24" '
            f'fill="{SUBTLE}">{escape(FOOTER)}</text>'
        )
    )
    parts.append("</svg>")
    SVG_PATH.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    render_svg()
    render_png()
    print(f"Generated {SVG_PATH.relative_to(REPO_ROOT)}")
    print(f"Generated {PNG_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
