#!/usr/bin/env python3
"""Write one PDF scorecard per stored game.

The pages are the line score, the batting lines, the pitching lines, and
the decisions. A missing inning is left blank for the visitors and marked
x for the home club when that half was not played. The PDF creation date
is fixed so a rebuild does not change the bytes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "scorecards"
CREATED = datetime(2026, 10, 25, tzinfo=timezone.utc)


def nz(value) -> int:
    return value or 0


def ip_label(outs: int) -> str:
    return f"{outs // 3}.{outs % 3}"


def latin(text: str) -> str:
    return str(text).encode("latin-1", "replace").decode("latin-1")


def write_scorecards(data: dict, root: Path | None = None) -> None:
    folder = (root or ROOT) / "scorecards"
    folder.mkdir(exist_ok=True)
    keep = set()
    for game in data["games"]:
        path = folder / f"{game['id']}.pdf"
        path.write_bytes(render(game))
        keep.add(path.name)
    for path in folder.glob("*.pdf"):
        if path.name not in keep:
            path.unlink()


def render(game: dict) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="letter")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.set_title(f"{game['id']} scorecard")
    pdf.set_author("Payoff Pitch")
    pdf.set_creator("scripts/scorecards.py")
    pdf.set_creation_date(CREATED)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    away, home = game["away"], game["home"]
    away_name = game["teams"][away]
    home_name = game["teams"][home]
    pdf.cell(0, 8, latin("Payoff Pitch scorecard"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(
        0, 7,
        latin(f"{away_name} {game['score'][away]} at {home_name} {game['score'][home]}"),
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 10)
    when = game.get("date") or "Date not stored"
    pdf.cell(0, 6, latin(f"{game['id']}  ·  {when}  ·  {decisions(game)}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    line_table(pdf, game)
    pdf.ln(3)
    for code, name in ((away, away_name), (home, home_name)):
        batting_table(pdf, game, code, name)
        pitching_table(pdf, game, code, name)
    pdf.set_font("Helvetica", "", 8)
    pdf.ln(2)
    pdf.multi_cell(0, 4, latin("Printed from the stored box score. This file does not change a result."))
    payload = pdf.output()
    return bytes(payload)


def decisions(game: dict) -> str:
    parts = []
    for key, label in (("W", "W"), ("L", "L"), ("S", "SV")):
        award = (game.get("wls") or {}).get(key)
        if award:
            parts.append(f"{label} {award['name']}")
    return " · ".join(parts) if parts else "No decision recorded"


def row(pdf: FPDF, widths: list[float], values: list[str], bold: bool = False, size: int = 8) -> None:
    if pdf.get_y() > 255:
        pdf.add_page()
    pdf.set_font("Helvetica", "B" if bold else "", size)
    height = 5.5
    for index, (width, value) in enumerate(zip(widths, values)):
        pdf.cell(width, height, latin(value), border=1, align="L" if index == 0 else "C")
    pdf.ln(height)


def line_table(pdf: FPDF, game: dict) -> None:
    away, home = game["away"], game["home"]
    innings = max(len(game["line"][away]), len(game["line"][home]))
    name_w = 42
    cell_w = min(10, (190 - name_w - 24) / max(innings, 1))
    widths = [name_w] + [cell_w] * innings + [8, 8, 8]
    headers = ["Team"] + [str(n) for n in range(1, innings + 1)] + ["R", "H", "E"]
    row(pdf, widths, headers, bold=True)
    for code, name in ((away, game["teams"][away]), (home, game["teams"][home])):
        inn = list(game["line"][code])
        cells = [name]
        for index in range(innings):
            if index < len(inn):
                cells.append(str(inn[index]))
            elif code == home:
                cells.append("x")
            else:
                cells.append("")
        hits = sum(nz(line["h"]) for line in game["batting"] if line["team"] == code)
        errors = (game.get("team_errors") or {}).get(code, 0)
        cells += [str(game["score"][code]), str(hits), str(errors)]
        row(pdf, widths, cells)


def batting_table(pdf: FPDF, game: dict, code: str, name: str) -> None:
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, latin(f"{name} batting"), new_x="LMARGIN", new_y="NEXT")
    headers = ["Player", "AB", "R", "H", "HR", "RBI", "BB", "SO"]
    widths = [70, 14, 14, 14, 14, 16, 14, 14]
    row(pdf, widths, headers, bold=True)
    lines = [line for line in game["batting"] if line["team"] == code]
    lines.sort(key=lambda line: (line.get("lineup_slot") or 99, line.get("entry_order") or 0, line["name"]))
    for line in lines:
        label = line["name"] + (" (sub)" if line.get("is_substitute") else "")
        row(pdf, widths, [
            label, nz(line["ab"]), nz(line["r"]), nz(line["h"]), nz(line["hr"]),
            nz(line["rbi"]), nz(line["bb"]), nz(line["k"]),
        ])


def pitching_table(pdf: FPDF, game: dict, code: str, name: str) -> None:
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, latin(f"{name} pitching"), new_x="LMARGIN", new_y="NEXT")
    headers = ["Player", "IP", "H", "R", "ER", "BB", "SO"]
    widths = [70, 16, 14, 14, 14, 14, 14]
    row(pdf, widths, headers, bold=True)
    arms = [line for line in game["pitching"] if line["team"] == code]
    arms.sort(key=lambda line: line["appearance_order"])
    for line in arms:
        row(pdf, widths, [
            line["name"], ip_label(nz(line["outs"])), nz(line["h"]), nz(line["r"]),
            nz(line["er"]), nz(line["bb"]), nz(line["k"]),
        ])
