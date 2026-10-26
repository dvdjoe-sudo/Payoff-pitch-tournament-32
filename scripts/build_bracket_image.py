#!/usr/bin/env python3
"""Write the Facebook bracket image, 1200 by 1500.

Winners are gold and tagged WIN. Losers are dimmed. A series that is
scheduled or in progress is labeled UPCOMING. The footer says that later
rounds are re-seeded. The image has no site address. It does not change
a game result.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "graphics" / "bracket.png"
WIDTH = 1200
HEIGHT = 1500
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

PAPER = (243, 234, 215)
CARD = (255, 250, 241)
NAVY = (18, 38, 63)
GOLD = (198, 161, 90)
INK = (27, 23, 20)
MUTED = (92, 86, 76)
DIM = (168, 160, 148)
LINE = (217, 203, 179)

SECTIONS = [
    ("Opening round", "R1-"),
    ("Winners round 2", "W2-"),
    ("Winners round 3", "W3-"),
    ("Winners round 4", "W4-"),
    ("Winners final", "W5-"),
    ("Losers round 1", "L1-"),
    ("Losers round 2", "L2-"),
    ("Losers round 3", "L3-"),
    ("Losers round 4", "L4-"),
    ("Losers round 5", "L5-"),
    ("Losers round 6", "L6-"),
    ("Losers round 7", "L7-"),
    ("Losers final", "L8-"),
    ("Championship", "F-"),
]


def face(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def fit(draw: ImageDraw.ImageDraw, text: str, bold: bool, size: int, width: int) -> tuple[ImageFont.FreeTypeFont, str]:
    current = text
    for candidate in range(size, 10, -1):
        used = face(candidate, bold)
        if draw.textlength(current, font=used) <= width:
            return used, current
    used = face(11, bold)
    while current and draw.textlength(current + "…", font=used) > width:
        current = current[:-1]
    return used, (current + "…") if current else ""


def draw_series(draw: ImageDraw.ImageDraw, series: dict, names: dict, box: tuple[int, int, int, int]) -> None:
    x, y, w, h = box
    draw.rounded_rectangle((x, y, x + w, y + h), radius=8, fill=CARD, outline=LINE, width=1)
    ident = series["id"]
    if series.get("status") in ("scheduled", "in-progress"):
        ident += "  UPCOMING"
    id_font, ident = fit(draw, ident, False, 12, w - 14)
    draw.text((x + 6, y + 3), ident, font=id_font, fill=MUTED)
    winner = series.get("winner")
    loser = series.get("loser")
    for index, code in enumerate((series.get("team_a"), series.get("team_b"))):
        yy = y + 17 + index * 16
        label = "TBD" if not code else names.get(code, code)
        if code and code == winner:
            name_font, shown = fit(draw, label + "  WIN", True, 13, w - 18)
            text_w = draw.textlength(shown, font=name_font)
            draw.rounded_rectangle((x + 5, yy - 1, x + 11 + text_w, yy + 15), radius=3, fill=GOLD)
            draw.text((x + 8, yy), shown, font=name_font, fill=INK)
        elif code and code == loser:
            name_font, shown = fit(draw, label, False, 13, w - 14)
            draw.text((x + 7, yy), shown, font=name_font, fill=DIM)
        else:
            name_font, shown = fit(draw, label, False, 13, w - 14)
            draw.text((x + 7, yy), shown, font=name_font, fill=NAVY)


def main() -> None:
    results = json.loads((ROOT / "tournament_results.json").read_text())
    names = {team["code"]: team["name"] for team in results["teams"]}
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    title = "Payoff Pitch Tournament 32"
    title_font = face(36, True)
    title_w = draw.textlength(title, font=title_font)
    draw.text(((WIDTH - title_w) / 2, 22), title, font=title_font, fill=NAVY)
    draw.rectangle((36, 72, WIDTH - 36, 78), fill=GOLD)

    y = 84
    margin = 28
    gap = 4
    card_h = 50
    section_font = face(14, True)
    for title, prefix in SECTIONS:
        rows = [series for series in results["series"] if series["id"].startswith(prefix)]
        rows.sort(key=lambda series: series["id"])
        if not rows:
            continue
        draw.text((margin, y), title, font=section_font, fill=NAVY)
        y += 18
        cols = 4 if len(rows) >= 4 else max(1, len(rows))
        card_w = (WIDTH - margin * 2 - gap * (cols - 1)) / cols
        for index, series in enumerate(rows):
            col = index % cols
            row = index // cols
            x = margin + col * (card_w + gap)
            yy = y + row * (card_h + gap)
            draw_series(draw, series, names, (int(x), int(yy), int(card_w), card_h))
        used = math.ceil(len(rows) / cols)
        y += used * (card_h + gap) + 2

    footer = "All rounds will be re-seeded"
    footer_font = face(18, True)
    footer_w = draw.textlength(footer, font=footer_font)
    draw.text(((WIDTH - footer_w) / 2, HEIGHT - 36), footer, font=footer_font, fill=NAVY)
    if y > HEIGHT - 48:
        raise SystemExit("bracket image overflowed: content ended at %s" % y)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT, "PNG", optimize=True)
    print("wrote", OUT.relative_to(ROOT), "content y", y)


if __name__ == "__main__":
    main()
