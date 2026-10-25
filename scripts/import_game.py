#!/usr/bin/env python3
"""Turn a box-score CSV into a tournament game file and check its shape.

The archive is not modified. The script writes two JSON files under imports/
and exits 1 when the shape check fails. See ADDING_GAMES.md.

A GameChanger-style file uses Player, AB, R, H, RBI, BB, SO and a Team column.
A Game Pulse-style file uses the same columns, or IP for a pitching row.
Lines that start with # carry the series, clubs, date, and seed.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ALIASES = {
    "player": "name",
    "batter": "name",
    "pitcher": "name",
    "name": "name",
    "team": "team",
    "club": "team",
    "ab": "ab",
    "r": "r",
    "h": "h",
    "hr": "hr",
    "rbi": "rbi",
    "bb": "bb",
    "so": "k",
    "k": "k",
    "so_b": "k",
    "hbp": "hbp",
    "sb": "sb",
    "cs": "cs",
    "2b": "doubles",
    "doubles": "doubles",
    "3b": "triples",
    "triples": "triples",
    "sac": "sac",
    "ip": "ip",
    "outs": "outs",
    "er": "er",
    "bf": "bf",
    "h_allowed": "p_h",
    "bb_allowed": "p_bb",
    "k_allowed": "p_k",
    "so_allowed": "p_k",
    "ra": "p_r",
    "r_allowed": "p_r",
    "runs_allowed": "p_r",
    "role": "role",
    "id": "player_id",
    "player_id": "player_id",
}


def slug(name: str) -> str:
    letters = "".join(ch for ch in name.lower() if ch.isalpha())
    return (letters[:8] or "player") + "01"


def parse_ip(value: str) -> int:
    text = value.strip()
    if not text:
        return 0
    if "." in text:
        whole, frac = text.split(".", 1)
        return int(whole) * 3 + int(frac[:1] or "0")
    return int(float(text) * 3) if text else 0


def num(value: str) -> int:
    text = (value or "").strip()
    if not text:
        return 0
    return int(float(text))


def read_table(path: Path) -> tuple[dict, list[dict]]:
    meta: dict[str, str] = {}
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as handle:
        raw = [line for line in handle.read().splitlines() if line.strip() and not line.strip().startswith("# ")]
        comments = [line.strip()[2:] for line in path.read_text(encoding="utf-8").splitlines() if line.strip().startswith("# ")]
    for comment in comments:
        bits = comment.split(None, 1)
        if len(bits) == 2:
            meta[bits[0]] = bits[1]
    reader = csv.DictReader(raw)
    if not reader.fieldnames:
        raise SystemExit("CSV has no header row")
    fields = []
    for field in reader.fieldnames:
        key = ALIASES.get((field or "").strip().lower().replace(" ", "_"))
        fields.append(key or (field or "").strip().lower())
    for source in reader:
        row = {}
        for key, value in zip(fields, source.values()):
            if key:
                row[key] = (value or "").strip()
        if any(row.values()):
            rows.append(row)
    return meta, rows


def build(meta: dict, rows: list[dict]) -> tuple[dict, dict]:
    for key in ("series", "game", "away", "home"):
        if key not in meta:
            raise SystemExit(f"missing # {key}")
    game_no = int(meta["game"])
    game_id = f"{meta['series']}-G{game_no}"
    away, home = meta["away"], meta["home"]
    names = {away: meta.get("away_name", away), home: meta.get("home_name", home)}
    batting = []
    pitching = []
    for row in rows:
        team = row.get("team") or ""
        if team not in (away, home):
            raise SystemExit(f"row team {team!r} is not {away} or {home}")
        name = row.get("name") or ""
        if not name:
            raise SystemExit("a row is missing the player name")
        player_id = row.get("player_id") or slug(name)
        role = (row.get("role") or "").lower()
        is_pitch = role in {"p", "pitch", "pitching"} or (row.get("ip") or row.get("outs"))
        if is_pitch and role not in {"b", "bat", "batting"}:
            outs = num(row["outs"]) if row.get("outs") else parse_ip(row.get("ip") or "0")
            pitching.append({
                "team": team,
                "player_id": player_id,
                "name": name,
                "appearance_order": 1 + sum(1 for line in pitching if line["team"] == team),
                "outs": outs,
                "h": num(row.get("p_h") or row.get("h") or "0"),
                "r": num(row.get("p_r") if row.get("p_r") not in (None, "") else (row.get("r") or "0")),
                "er": num(row.get("er") or "0"),
                "bb": num(row.get("p_bb") or row.get("bb") or "0"),
                "k": num(row.get("p_k") or row.get("k") or "0"),
                "bf": num(row.get("bf") or "0"),
                "hb": None,
                "hr": None,
            })
        else:
            batting.append({
                "team": team,
                "player_id": player_id,
                "name": name,
                "lineup_slot": 1 + sum(1 for line in batting if line["team"] == team),
                "entry_order": 1,
                "is_substitute": False,
                "ab": num(row.get("ab") or "0"),
                "r": num(row.get("r") or "0"),
                "h": num(row.get("h") or "0"),
                "rbi": num(row.get("rbi") or "0"),
                "bb": num(row.get("bb") or "0"),
                "k": num(row.get("k") or "0"),
                "hbp": num(row.get("hbp") or "0"),
                "sb": num(row.get("sb") or "0"),
                "cs": num(row.get("cs") or "0"),
                "sac": num(row.get("sac") or "0"),
                "sf": None,
                "gidp": 0,
                "ibb": None,
                "doubles": num(row.get("doubles") or "0"),
                "triples": num(row.get("triples") or "0"),
                "hr": num(row.get("hr") or "0"),
            })
    score = {}
    line = {}
    for code in (away, home):
        if f"line_{code}" in meta:
            line[code] = [int(part) for part in meta[f"line_{code}"].split(",") if part != ""]
            score[code] = sum(line[code])
        else:
            score[code] = sum(item["r"] for item in batting if item["team"] == code)
            line[code] = [score[code]]
    if score[away] == score[home]:
        raise SystemExit("the score is tied; a tournament game needs a winner")
    winner = away if score[away] > score[home] else home
    loser = home if winner == away else away
    problems = check_shape(away, home, score, batting, pitching)
    game = {
        "id": game_id,
        "series_id": meta["series"],
        "game_in_series": game_no,
        "date": meta.get("date"),
        "away": away,
        "home": home,
        "teams": names,
        "score": score,
        "line": line,
        "winner": winner,
        "wls": {
            "W": {"team": winner, "player_id": "winner01", "name": meta.get("winner_name", "Winner")},
            "L": {"team": loser, "player_id": "loser01", "name": meta.get("loser_name", "Loser")},
            "S": None,
        },
        "batting": batting,
        "pitching": pitching,
        "errors_by": [],
        "team_errors": {away: 0, home: 0},
        "final_grades": {},
        "game_recap": meta.get("recap", ""),
        "series_recap": meta.get("series_recap", ""),
        "rng_seed": int(meta.get("rng_seed") or 0),
        "detail": f"games/{game_id}.json",
        "scoring_plays": [],
    }
    detail = {
        "id": game_id,
        "series_id": meta["series"],
        "game_in_series": game_no,
        "rolls": [],
        "manager_log": None,
    }
    return game, detail, problems


def check_shape(away: str, home: str, score: dict, batting: list, pitching: list) -> list[str]:
    problems = []
    if not batting:
        problems.append("no batting rows")
    for code in (away, home):
        runs = sum(line["r"] for line in batting if line["team"] == code)
        if runs != score[code]:
            problems.append(f"{code} batting runs {runs} do not match the score {score[code]}")
        if not any(line["team"] == code for line in batting):
            problems.append(f"no batting line for {code}")
    if pitching:
        for code in (away, home):
            allowed = sum(line["r"] for line in pitching if line["team"] == code)
            other = home if code == away else away
            if allowed != score[other]:
                problems.append(f"{code} pitching runs {allowed} do not match {other}'s score {score[other]}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a box-score CSV into game JSON and check it.")
    parser.add_argument("csv_path")
    parser.add_argument("--out", default="imports", help="Directory for the JSON files. The archive is not touched.")
    args = parser.parse_args()
    meta, rows = read_table(Path(args.csv_path))
    game, detail, problems = build(meta, rows)
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{game['id']}.json").write_text(json.dumps(game, indent=1) + "\n", encoding="utf-8")
    (out / f"{game['id']}.detail.json").write_text(json.dumps(detail, indent=1) + "\n", encoding="utf-8")
    if problems:
        print("shape check failed:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"wrote {out / (game['id'] + '.json')} and the detail file")
    print("shape check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
