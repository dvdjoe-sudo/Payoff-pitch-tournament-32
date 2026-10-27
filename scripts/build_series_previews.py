#!/usr/bin/env python3
"""Write a 1200x1500 lineup card for each upcoming series.

An upcoming series is scheduled or in progress and already has both clubs.
The card uses the owner roster and the stored Peak 162 line. It does not
invent a player or a stat, and it does not change a game result.

The lineup leader is the hitter with the highest OPS on his peak line.
The starter leader is the rotation arm with the lowest ERA on his peak line.
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "graphics" / "previews"
WIDTH = 1200
HEIGHT = 1500
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

PAPER = (243, 234, 215)
CARD = (255, 250, 241)
NAVY = (18, 38, 63)
GOLD = (198, 161, 90)
MUTED = (92, 86, 76)
LINE = (217, 203, 179)

BAT_RATE = re.compile(r"(\.\d{3}/\.\d{3}/\.\d{3}/(?:\d+\.\d+|\.\d+))\s*$")
ERA_RATE = re.compile(r"(\d+\.\d+) ERA")
YEARS = re.compile(r"\((\d{4})(?:[–-](\d{4}))?\)")


def load(name: str):
    path = ROOT / name
    return json.loads(path.read_text())


def peak_bits(text: str) -> dict | None:
    if not text:
        return None
    years = YEARS.search(text)
    bat = BAT_RATE.search(text)
    era = ERA_RATE.search(text)
    if not bat and not era:
        return None
    ops = None
    if bat:
        ops = float(bat.group(1).split("/")[-1])
    span = ""
    if years:
        span = years.group(1) if not years.group(2) else years.group(1) + "–" + years.group(2)
    return {
        "years": span,
        "rate": bat.group(1) if bat else era.group(1) + " ERA",
        "ops": ops,
        "era": float(era.group(1)) if era else None,
    }


def club_name(teams: dict, code: str) -> str:
    team = teams.get(code) or {}
    return team.get("name") or code


def club_means(roster: dict | None, peak_clubs: dict, code: str) -> tuple[float, float] | None:
    if not roster:
        return None
    book = peak_clubs.get(code) or {}
    ops_values = []
    era_values = []
    for line in roster.get("lineup") or []:
        row = book.get(line) or {}
        bits = peak_bits(row.get("text") or "") if row.get("status") == "ok" else None
        if bits and bits["ops"] is not None:
            ops_values.append(bits["ops"])
    for line in roster.get("rotation") or []:
        row = book.get(line) or {}
        bits = peak_bits(row.get("text") or "") if row.get("status") == "ok" else None
        if bits and bits["era"] is not None:
            era_values.append(bits["era"])
    if not ops_values or not era_values:
        return None
    return sum(ops_values) / len(ops_values), sum(era_values) / len(era_values)


def projection_label(series: dict, rosters: dict, peak_clubs: dict) -> str:
    """Same display model as peakProjection in js/bracket.js."""
    rated = {}
    for code, roster in rosters.items():
        means = club_means(roster, peak_clubs, code)
        if means:
            rated[code] = means
    a = series.get("team_a")
    b = series.get("team_b")
    if not a or not b or a not in rated or b not in rated or not rated:
        return "Projection: Odds TBD"
    league_ops = sum(item[0] for item in rated.values()) / len(rated)
    league_era = sum(item[1] for item in rated.values()) / len(rated)
    if not league_ops or not league_era:
        return "Projection: Odds TBD"

    def win_pct(means: tuple[float, float]) -> float:
        offense = means[0] / league_ops
        pitching = means[1] / league_era
        return (offense * offense) / (offense * offense + pitching * pitching)

    wa = win_pct(rated[a])
    wb = win_pct(rated[b])
    left = wa * (1 - wb)
    right = wb * (1 - wa)
    game_p = 0.5 if left + right == 0 else left / (left + right)
    wins = series.get("wins") or {}
    memo: dict[tuple[int, int], float] = {}

    def walk(need_a: int, need_b: int) -> float:
        key = (need_a, need_b)
        if key in memo:
            return memo[key]
        if need_a <= 0:
            value = 1.0
        elif need_b <= 0:
            value = 0.0
        else:
            value = game_p * walk(need_a - 1, need_b) + (1 - game_p) * walk(need_a, need_b - 1)
        memo[key] = value
        return value

    series_p = walk(4 - int(wins.get(a) or 0), 4 - int(wins.get(b) or 0))
    return "Projection " + a + " " + one_decimal(series_p) + "% · " + b + " " + one_decimal(1 - series_p) + "%"


def one_decimal(value: float) -> str:
    """Match percent() in js/bracket.js: Math.round(value * 1000) / 10."""
    tenths = int(value * 1000 + 0.5)
    return f"{tenths / 10:.1f}"


def leaders(roster: dict | None, peak_clubs: dict, code: str) -> tuple[str, str]:
    if not roster:
        return ("Roster not announced yet", "")
    book = peak_clubs.get(code) or {}
    best_hit = None
    for line in roster.get("lineup") or []:
        bits = peak_bits((book.get(line) or {}).get("text") or "")
        if not bits or bits["ops"] is None:
            continue
        if best_hit is None or bits["ops"] > best_hit[0]:
            best_hit = (bits["ops"], line, bits["rate"])
    best_arm = None
    for line in roster.get("rotation") or []:
        bits = peak_bits((book.get(line) or {}).get("text") or "")
        if not bits or bits["era"] is None:
            continue
        if best_arm is None or bits["era"] < best_arm[0]:
            best_arm = (bits["era"], line, bits["rate"])
    hit = "No Peak 162 batting line is stored."
    if best_hit:
        hit = "Peak 162 leader: " + best_hit[1] + ", " + best_hit[2]
    arm = "No Peak 162 pitching line is stored."
    if best_arm:
        arm = "Peak 162 starter: " + best_arm[1] + ", " + best_arm[2]
    return (hit, arm)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def wrap(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = current + " " + word
        if draw.textlength(trial, font=face) <= width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_column(draw: ImageDraw.ImageDraw, x: int, y: int, width: int, name: str, roster, peak_clubs, code: str) -> None:
    draw.rounded_rectangle((x, y, x + width, HEIGHT - 78), radius=18, fill=CARD, outline=LINE, width=2)
    draw.rectangle((x, y, x + width, y + 8), fill=GOLD)
    name_face = font(28, True)
    body = font(18)
    small = font(16)
    cursor = y + 22
    for line in wrap(draw, name, name_face, width - 36)[:2]:
        draw.text((x + 18, cursor), line, font=name_face, fill=NAVY)
        cursor += 34
    hit, arm = leaders(roster, peak_clubs, code)
    for line in (hit, arm):
        if not line:
            continue
        for part in wrap(draw, line, small, width - 36)[:2]:
            draw.text((x + 18, cursor), part, font=small, fill=MUTED)
            cursor += 22
    cursor += 8
    if not roster:
        draw.text((x + 18, cursor + 12), "Roster not announced yet", font=font(22, True), fill=NAVY)
        return
    lineup = roster.get("lineup") or []
    book = peak_clubs.get(code) or {}
    row_h = 78
    for line in lineup:
        bits = peak_bits((book.get(line) or {}).get("text") or "")
        draw.text((x + 18, cursor), line, font=body, fill=NAVY)
        rate = bits["rate"] if bits else "Peak stats unavailable"
        years = ""
        if bits and bits["years"]:
            years = "Peak 162 (" + bits["years"] + ")"
        draw.text((x + 18, cursor + 24), rate, font=small, fill=MUTED)
        if years:
            draw.text((x + 18, cursor + 46), years, font=small, fill=MUTED)
        cursor += row_h


def render(series: dict, teams: dict, rosters: dict, peak_clubs: dict) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    draw.text((48, 36), "Payoff Pitch", font=font(28, True), fill=GOLD)
    title = series.get("label") or series["id"]
    draw.text((48, 78), title, font=font(40, True), fill=NAVY)
    sub = series["id"] + "  ·  " + series.get("status", "").replace("-", " ")
    sub += "  ·  " + projection_label(series, rosters, peak_clubs)
    draw.text((48, 132), sub, font=font(22), fill=MUTED)
    draw.rectangle((48, 176, WIDTH - 48, 182), fill=GOLD)
    col_w = 528
    top = 206
    for index, code in enumerate((series["team_a"], series["team_b"])):
        x = 48 + index * (col_w + 48)
        draw_column(draw, x, top, col_w, club_name(teams, code), rosters.get(code), peak_clubs, code)
    note = "Peak 162 lines are the stored franchise peaks. They are not tournament stats."
    draw.text((48, HEIGHT - 52), note, font=font(18), fill=MUTED)
    return image


def main() -> None:
    results = load("tournament_results.json")
    rosters = load("data/announced_rosters.json")
    peak = load("data/peak162.json")
    teams = {team["code"]: team for team in results["teams"]}
    peak_clubs = peak.get("clubs") or {}
    upcoming = [
        series for series in results["series"]
        if series.get("status") in ("scheduled", "in-progress") and series.get("team_a") and series.get("team_b")
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    keep = set()
    for series in upcoming:
        image = render(series, teams, rosters, peak_clubs)
        dest = OUT / (series["id"] + ".png")
        image.save(dest, "PNG", optimize=True)
        # TEMPORARY CI extraction of the deterministic Royals matchup preview.
        # Remove this logging before merging; only binary graphics change.
        if series["id"] == "R1-15":
            encoded = base64.b64encode(dest.read_bytes()).decode("ascii")
            print("PREVIEW_B64_BEGIN")
            for offset in range(0, len(encoded), 4000):
                print("PREVIEW_B64:" + encoded[offset:offset + 4000])
            print("PREVIEW_B64_END")
        keep.add(dest.name)
        print("wrote", dest.relative_to(ROOT))
    for old in OUT.glob("*.png"):
        if old.name not in keep:
            old.unlink()
            print("removed", old.name)


if __name__ == "__main__":
    main()
