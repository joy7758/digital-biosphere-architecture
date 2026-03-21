#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A1, A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


PRINT_FINAL = Path(__file__).resolve().parent.parent
SOURCE_OF_TRUTH = PRINT_FINAL / "source-of-truth"
POSTER_DIR = PRINT_FINAL / "poster"
CARD_DIR = PRINT_FINAL / "card"
BUSINESS_QR_DIR = PRINT_FINAL / "business-card" / "qr"
POSTER_QR_DIR = POSTER_DIR / "qr"
CARD_QR_DIR = CARD_DIR / "qr"
DESIGN_SRC = PRINT_FINAL / "design-src"

PRINT_COPY = SOURCE_OF_TRUTH / "print-copy.md"
QR_LINKS = POSTER_DIR / "qr-links-source.md"
SWIFT_TOOL = DESIGN_SRC / "qr_tools.swift"

EN = "Helvetica"
EN_BOLD = "Helvetica-Bold"
EN_MONO = "Courier"
CN = "STSong-Light"


def register_fonts() -> None:
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(CN))
    except Exception:
        pass


def slugify(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def ensure_dirs() -> None:
    for path in [
        POSTER_QR_DIR,
        CARD_QR_DIR,
        BUSINESS_QR_DIR,
        DESIGN_SRC / "poster",
        DESIGN_SRC / "card",
        DESIGN_SRC / "business-card",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def parse_sections(path: Path) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
    return {
        name: [line.strip() for line in lines if line.strip()]
        for name, lines in sections.items()
    }


def parse_qr_links(path: Path) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    current_title: str | None = None
    current: dict[str, str] | None = None

    def flush() -> None:
        nonlocal current_title, current
        if current_title and current:
            entries[current["label"]] = {
                "section": current_title,
                **current,
            }
        current_title = None
        current = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            if not line:
                flush()
            continue
        if line.startswith("- "):
            key, value = line[2:].split(":", 1)
            key = key.strip()
            value = value.strip().strip("`")
            if current is None:
                current = {}
            current[key] = value
            continue
        flush()
        current_title = line.rstrip(":")
        current = {}

    flush()
    return entries


def parse_poster(lines: list[str]) -> dict[str, object]:
    result: dict[str, object] = {"qrs": []}
    index = 0
    while index < len(lines):
        token = lines[index]
        if token in {"Title:", "Subtitle:", "Workflow:", "Callout:"}:
            result[token[:-1].lower()] = lines[index + 1]
            index += 2
            continue
        if token == "Scan order:":
            result["scan_order_en"] = lines[index + 1]
            result["scan_order_cn"] = lines[index + 2]
            index += 3
            continue
        if token.startswith("QR "):
            result["qrs"].append(
                {
                    "slot": token,
                    "label": lines[index + 1],
                    "display": lines[index + 2],
                }
            )
            index += 3
            continue
        raise ValueError(f"Unrecognized poster token: {token}")
    return result


def parse_card_front(lines: list[str]) -> dict[str, str]:
    return {
        "title": lines[0],
        "subtitle": lines[1],
        "subtitle_cn": lines[2],
        "sentence": lines[3],
        "sentence_cn": lines[4],
        "left_qr_label": lines[6],
        "left_qr_desc": lines[7],
        "right_qr_label": lines[9],
        "right_qr_desc": lines[10],
    }


def parse_name_card(lines: list[str]) -> dict[str, str]:
    return {
        "name": lines[0],
        "role": lines[1],
        "domain": lines[2],
        "github": lines[3],
        "orcid": lines[4],
        "qr_label": lines[6],
    }


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def compile_qr_tool() -> Path:
    binary = Path(tempfile.gettempdir()) / "digital-biosphere-qr-tools"
    subprocess.run(
        ["swiftc", str(SWIFT_TOOL), "-o", str(binary)],
        check=True,
    )
    return binary


def build_qr_png(binary: Path, label: str, url: str, output_dir: Path) -> Path:
    output_path = output_dir / f"{slugify(label)}.png"
    subprocess.run(
        [str(binary), "encode", url, str(output_path)],
        check=True,
    )
    return output_path


def decode_qr(binary: Path, path: Path) -> str:
    completed = subprocess.run(
        [str(binary), "decode", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def draw_lines(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    font_name: str,
    font_size: float,
    leading: float,
    color: colors.Color,
) -> float:
    c.setFont(font_name, font_size)
    c.setFillColor(color)
    cursor = y
    for line in simpleSplit(text, font_name, font_size, width):
        c.drawString(x, cursor, line)
        cursor -= leading
    return cursor


def draw_centered_lines(
    c: canvas.Canvas,
    text: str,
    center_x: float,
    y: float,
    width: float,
    font_name: str,
    font_size: float,
    leading: float,
    color: colors.Color,
) -> float:
    c.setFont(font_name, font_size)
    c.setFillColor(color)
    cursor = y
    for line in simpleSplit(text, font_name, font_size, width):
        c.drawCentredString(center_x, cursor, line)
        cursor -= leading
    return cursor


def draw_qr_tile(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    label: str,
    display: str,
    image_path: Path,
    accent: colors.Color,
) -> None:
    c.saveState()
    c.setFillColor(colors.white)
    c.setStrokeColor(accent)
    c.setLineWidth(3)
    c.roundRect(x, y, width, height, 18, fill=1, stroke=1)
    qr_size = min(width - 70, height * 0.55)
    qr_x = x + (width - qr_size) / 2
    qr_y = y + height - qr_size - 42
    c.drawImage(
        ImageReader(str(image_path)),
        qr_x,
        qr_y,
        qr_size,
        qr_size,
        mask="auto",
    )
    c.setFillColor(colors.HexColor("#10212B"))
    c.setFont(EN_BOLD, 26)
    c.drawCentredString(x + width / 2, y + 96, label)
    draw_centered_lines(
        c,
        display,
        x + width / 2,
        y + 64,
        width - 50,
        EN,
        16,
        20,
        colors.HexColor("#405261"),
    )
    c.restoreState()


def build_poster(
    poster_data: dict[str, object],
    qr_entries: dict[str, dict[str, str]],
    qr_paths: dict[str, Path],
) -> Path:
    output = POSTER_DIR / "A1-poster-final.pdf"
    c = canvas.Canvas(str(output), pagesize=A1)
    c.setTitle("A1 Poster Final")
    c.setAuthor("Zhang Bin")
    c.setSubject("Digital Biosphere Architecture poster")
    width, height = A1

    bg = colors.HexColor("#F5F0E8")
    dark = colors.HexColor("#10212B")
    accent = colors.HexColor("#C96F4A")
    blue = colors.HexColor("#355D7A")
    green = colors.HexColor("#5C7A63")
    gold = colors.HexColor("#B08C46")

    c.setFillColor(bg)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    c.setFillColor(dark)
    c.rect(0, height - 360, width, 360, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont(EN_BOLD, 86)
    c.drawString(110, height - 150, "The Digital Biosphere")
    c.setFont(EN, 34)
    c.drawString(110, height - 210, "Verifiable Digital Objects for Machine-Actionable Ecosystems")
    c.setFont(CN, 28)
    c.drawString(110, height - 255, "面向机器可行动生态的可验证数字对象架构")

    c.setFillColor(accent)
    c.roundRect(110, height - 470, width - 220, 84, 18, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(EN_BOLD, 30)
    c.drawCentredString(width / 2, height - 420, str(poster_data["callout"]))

    c.setFillColor(colors.white)
    c.roundRect(110, height - 620, width - 220, 92, 18, fill=1, stroke=0)
    c.setFillColor(dark)
    c.setFont(EN_BOLD, 27)
    c.drawCentredString(width / 2, height - 566, str(poster_data["workflow"]))

    c.setFillColor(dark)
    c.setFont(EN_BOLD, 44)
    c.drawString(110, height - 760, str(poster_data["title"]))
    c.setFont(CN, 24)
    c.setFillColor(colors.HexColor("#5A5A5A"))
    c.drawString(110, height - 800, str(poster_data["subtitle"]))

    draw_lines(
        c,
        str(poster_data["scan_order_en"]),
        110,
        height - 870,
        width - 220,
        EN,
        22,
        30,
        dark,
    )
    draw_lines(
        c,
        str(poster_data["scan_order_cn"]),
        110,
        height - 905,
        width - 220,
        CN,
        22,
        30,
        colors.HexColor("#5A5A5A"),
    )

    tiles = list(poster_data["qrs"])
    margin_x = 110
    gap = 32
    tile_width = (width - 2 * margin_x - 2 * gap) / 3
    tile_height = 620
    row_gap = 34
    top_row_y = 690
    bottom_row_y = top_row_y - tile_height - row_gap
    accents = [accent, blue, gold, green, dark, colors.HexColor("#8A5B2D")]

    for idx, qr_info in enumerate(tiles):
        row = 0 if idx < 3 else 1
        col = idx % 3
        x = margin_x + col * (tile_width + gap)
        y = top_row_y if row == 0 else bottom_row_y
        label = qr_info["label"]
        draw_qr_tile(
            c,
            x,
            y,
            tile_width,
            tile_height,
            label,
            qr_entries[label]["display"],
            qr_paths[label],
            accents[idx],
        )

    c.showPage()
    c.save()

    write_json(
        DESIGN_SRC / "poster" / "layout-source.json",
        {
            "pages": 1,
            "pagesize_points": [round(width, 2), round(height, 2)],
            "source": str(PRINT_COPY.relative_to(PRINT_FINAL)),
            "qr_labels": [item["label"] for item in tiles],
        },
    )
    return output


def build_one_pager(
    front: dict[str, str],
    back_lines: list[str],
    qr_paths: dict[str, Path],
) -> Path:
    output = CARD_DIR / "one-pager-front-back.pdf"
    c = canvas.Canvas(str(output), pagesize=A4)
    c.setTitle("One Pager Front Back")
    c.setAuthor("Zhang Bin")
    c.setSubject("Digital Biosphere Architecture one-pager")
    width, height = A4

    cream = colors.HexColor("#F7F2EA")
    dark = colors.HexColor("#10212B")
    accent = colors.HexColor("#C96F4A")
    teal = colors.HexColor("#3F6A69")

    c.setFillColor(cream)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(dark)
    c.rect(0, height - 130, width, 130, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont(EN_BOLD, 28)
    c.drawString(38, height - 52, front["title"])
    c.setFont(EN, 13)
    c.drawString(38, height - 78, front["subtitle"])

    c.setFillColor(dark)
    c.setFont(CN, 15)
    c.drawString(38, height - 168, front["subtitle_cn"])
    draw_lines(c, front["sentence"], 38, height - 218, width - 76, EN_BOLD, 18, 24, dark)
    draw_lines(c, front["sentence_cn"], 38, height - 278, width - 76, CN, 14, 20, colors.HexColor("#575757"))

    tile_y = 80
    tile_width = (width - 38 * 2 - 24) / 2
    tile_height = 300
    labels = [front["left_qr_label"], front["right_qr_label"]]
    descs = [front["left_qr_desc"], front["right_qr_desc"]]
    accents = [accent, teal]
    for idx in range(2):
        x = 38 + idx * (tile_width + 24)
        c.setFillColor(colors.white)
        c.setStrokeColor(accents[idx])
        c.setLineWidth(1.8)
        c.roundRect(x, tile_y, tile_width, tile_height, 14, fill=1, stroke=1)
        qr_size = 160
        qr_x = x + (tile_width - qr_size) / 2
        qr_y = tile_y + 104
        c.drawImage(ImageReader(str(qr_paths[labels[idx]])), qr_x, qr_y, qr_size, qr_size, mask="auto")
        c.setFillColor(dark)
        c.setFont(EN_BOLD, 16)
        c.drawCentredString(x + tile_width / 2, tile_y + 72, labels[idx])
        c.setFont(EN, 11)
        c.drawCentredString(x + tile_width / 2, tile_y + 52, descs[idx])

    c.showPage()

    c.setFillColor(cream)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(teal)
    c.rect(0, height - 100, width, 100, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(EN_BOLD, 28)
    c.drawString(38, height - 56, back_lines[0])

    cursor = height - 150
    for line in back_lines[1:]:
        if line in {"Paper", "Registry", "Demo Object", "Runnable Demo", "MVK", "论文", "注册页", "示例对象", "可运行 Demo", "MVK 证明"}:
            cursor -= 16
            c.setFillColor(dark)
            c.setFont(EN_BOLD if re.fullmatch(r"[A-Za-z ]+", line) else CN, 15)
            c.drawString(38, cursor, line)
            cursor -= 22
            continue
        font_name = CN if re.search(r"[\u4e00-\u9fff]", line) else EN
        c.setFillColor(colors.HexColor("#404040"))
        c.setFont(font_name, 12 if font_name == EN else 11.5)
        for wrapped in simpleSplit(line, font_name, 12 if font_name == EN else 11.5, width - 76):
            c.drawString(52, cursor, wrapped)
            cursor -= 18

    c.showPage()
    c.save()

    write_json(
        DESIGN_SRC / "card" / "layout-source.json",
        {
            "pages": 2,
            "pagesize_points": [round(width, 2), round(height, 2)],
            "source": str(PRINT_COPY.relative_to(PRINT_FINAL)),
            "qr_labels": labels,
        },
    )
    return output


def draw_business_card_face(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    name_card: dict[str, str],
    qr_path: Path,
) -> None:
    dark = colors.HexColor("#10212B")
    accent = colors.HexColor("#C96F4A")
    paper = colors.HexColor("#F7F2EA")

    c.saveState()
    c.setFillColor(dark)
    c.roundRect(x, y, width, height, 10, fill=1, stroke=0)
    c.setFillColor(accent)
    c.rect(x, y, 7, height, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont(EN_BOLD, 13)
    c.drawString(x + 12, y + height - 16, name_card["name"])
    c.setFont(EN, 6.8)
    c.drawString(x + 12, y + height - 28, name_card["role"])
    c.drawString(x + 12, y + height - 38, name_card["domain"])

    qr_size = 34 * mm
    qr_x = x + width - qr_size - 5
    qr_y = y + (height - qr_size) / 2
    c.setFillColor(paper)
    c.roundRect(qr_x - 2, qr_y - 2, qr_size + 4, qr_size + 4, 4, fill=1, stroke=0)
    c.drawImage(ImageReader(str(qr_path)), qr_x, qr_y, qr_size, qr_size, mask="auto")

    c.setFillColor(paper)
    c.setFont(EN, 6.6)
    c.drawString(x + 12, y + 18, name_card["github"])
    c.drawString(x + 12, y + 9, name_card["orcid"])
    c.restoreState()


def build_business_cards(name_card: dict[str, str], qr_paths: dict[str, Path]) -> tuple[Path, Path]:
    business_size = (90 * mm, 55 * mm)
    single_output = CARD_DIR / "business-card-final.pdf"
    sheet_output = CARD_DIR / "business-card-10up-A4.pdf"
    qr_path = qr_paths[name_card["qr_label"]]

    c = canvas.Canvas(str(single_output), pagesize=business_size)
    c.setTitle("Business Card Final")
    c.setAuthor("Zhang Bin")
    c.setSubject("Digital Biosphere Architecture business card")
    draw_business_card_face(c, 0, 0, business_size[0], business_size[1], name_card, qr_path)
    c.showPage()
    c.save()

    sheet = canvas.Canvas(str(sheet_output), pagesize=A4)
    sheet.setTitle("Business Card 10-up A4")
    sheet.setAuthor("Zhang Bin")
    sheet.setSubject("Digital Biosphere Architecture business card sheet")
    page_width, page_height = A4
    margin_x = 15 * mm
    margin_y = 11 * mm
    card_width, card_height = business_size
    gap_x = (page_width - 2 * margin_x - 2 * card_width) / 1
    gap_y = (page_height - 2 * margin_y - 5 * card_height) / 4
    for row in range(5):
        for col in range(2):
            x = margin_x + col * (card_width + gap_x)
            y = page_height - margin_y - (row + 1) * card_height - row * gap_y
            draw_business_card_face(sheet, x, y, card_width, card_height, name_card, qr_path)
            sheet.setStrokeColor(colors.HexColor("#D8D0C4"))
            sheet.setLineWidth(0.4)
            sheet.rect(x, y, card_width, card_height, fill=0, stroke=1)
    sheet.showPage()
    sheet.save()

    write_json(
        DESIGN_SRC / "business-card" / "layout-source.json",
        {
            "pages": 1,
            "pagesize_points": [round(business_size[0], 2), round(business_size[1], 2)],
            "sheet_pages": 1,
            "sheet_pagesize_points": [round(A4[0], 2), round(A4[1], 2)],
            "source": str(PRINT_COPY.relative_to(PRINT_FINAL)),
            "qr_labels": [name_card["qr_label"]],
        },
    )
    return single_output, sheet_output


def pdf_info(path: Path) -> tuple[int, str]:
    completed = subprocess.run(
        ["pdfinfo", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    pages_match = re.search(r"^Pages:\s+(\d+)$", completed.stdout, re.MULTILINE)
    size_match = re.search(r"^Page size:\s+([^\n]+)$", completed.stdout, re.MULTILINE)
    if not pages_match or not size_match:
        raise ValueError(f"Unable to parse pdfinfo for {path}")
    return int(pages_match.group(1)), size_match.group(1).strip()


def main() -> None:
    register_fonts()
    ensure_dirs()

    sections = parse_sections(PRINT_COPY)
    qr_entries = parse_qr_links(QR_LINKS)
    poster_data = parse_poster(sections["Poster QR Block"])
    card_front = parse_card_front(sections["Card Front"])
    card_back = sections["Card Back"]
    name_card = parse_name_card(sections["Name Card"])

    qr_tool = compile_qr_tool()

    poster_labels = [item["label"] for item in poster_data["qrs"]]
    card_labels = [card_front["left_qr_label"], card_front["right_qr_label"]]
    business_labels = [name_card["qr_label"]]

    for label in poster_labels + card_labels + business_labels:
        if label not in qr_entries:
            raise KeyError(f"Missing QR link for label: {label}")

    poster_qrs = {
        label: build_qr_png(qr_tool, label, qr_entries[label]["target"], POSTER_QR_DIR)
        for label in poster_labels
    }
    card_qrs = {
        label: build_qr_png(qr_tool, label, qr_entries[label]["target"], CARD_QR_DIR)
        for label in card_labels
    }
    business_qrs = {
        label: build_qr_png(qr_tool, label, qr_entries[label]["target"], BUSINESS_QR_DIR)
        for label in business_labels
    }

    all_qrs = {}
    all_qrs.update(poster_qrs)
    all_qrs.update(card_qrs)
    all_qrs.update(business_qrs)

    for label, path in list(poster_qrs.items()) + list(card_qrs.items()) + list(business_qrs.items()):
        decoded = decode_qr(qr_tool, path)
        expected = qr_entries[label]["target"]
        if decoded != expected:
            raise ValueError(f"QR decode mismatch for {label}: {decoded} != {expected}")

    poster_pdf = build_poster(poster_data, qr_entries, all_qrs)
    one_pager_pdf = build_one_pager(card_front, card_back, all_qrs)
    business_pdf, business_sheet_pdf = build_business_cards(name_card, all_qrs)

    pdfs = [poster_pdf, one_pager_pdf, business_pdf, business_sheet_pdf]
    pdf_summaries = []
    for pdf_path in pdfs:
        pages, size = pdf_info(pdf_path)
        pdf_summaries.append((pdf_path, pages, size))

    print("PRINT_BUILD_OK")
    print(f"QR_COUNT={len(list(POSTER_QR_DIR.glob('*.png'))) + len(list(CARD_QR_DIR.glob('*.png'))) + len(list(BUSINESS_QR_DIR.glob('*.png')))}")
    for pdf_path, pages, size in pdf_summaries:
        print(f"PDF {pdf_path.relative_to(PRINT_FINAL)} pages={pages} size={size}")


if __name__ == "__main__":
    main()
