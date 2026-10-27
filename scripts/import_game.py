#!/usr/bin/env python3
"""Turn a box score into tournament game files and check their shape.

Accepts a GameChanger or Game Pulse CSV, one markdown box score, or a
whole-series markdown file in the R1-03 layout (`# R1-03 Game N: Away at Home`,
a linescore, then `## Club batting` and `## Club pitching` tables).

The default write goes to imports/ and does not touch the archive.
`--check` compares a file with the games already stored.
`--apply` adds games that are not already stored, refuses a changed line,
validates, and regenerates the generated pages.

See ADDING_GAMES.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "tournament_results.json"
GAMES = ROOT / "games"
FROZEN_SERIES = {"R1-01", "R1-02", "R1-03"}

ALIASES = {
    "player": "name", "batter": "name", "pitcher": "name", "name": "name",
    "team": "team", "club": "team", "ab": "ab", "r": "r", "h": "h", "hr": "hr",
    "rbi": "rbi", "bb": "bb", "so": "k", "k": "k", "so_b": "k", "hbp": "hbp",
    "sb": "sb", "cs": "cs", "2b": "doubles", "doubles": "doubles", "3b": "triples",
    "triples": "triples", "sac": "sac", "gidp": "gidp", "ip": "ip", "outs": "outs",
    "er": "er", "bf": "bf", "h_allowed": "p_h", "bb_allowed": "p_bb",
    "k_allowed": "p_k", "so_allowed": "p_k", "ra": "p_r", "r_allowed": "p_r",
    "runs_allowed": "p_r", "role": "role", "id": "player_id", "player_id": "player_id",
    "pitches": "pitches", "pitch": "pitches", "pc": "pitches", "np": "pitches", "hb": "hb",
}

GAME_HEADING = re.compile(
    r"^#\s+([A-Za-z0-9]+-\d+)\s+Game\s+(\d+)\s*:\s*(.+?)\s+at\s+(.+?)\s*$",
    re.M,
)
DATE_RE = re.compile(r"\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})")
SEED_RE = re.compile(r"\*\*Seed:\*\*\s*(\d+)")
DECISION_RE = re.compile(r"\b(W|L|SV)\s*:\s*(.+?)\s*\((.+?)\)")
RECAP_RE = re.compile(r"\*\*Game recap(?: \(from the archive\))?:\*\*\s*(.+)")
SERIES_RECAP_RE = re.compile(r"\*\*Series state after this game:\*\*\s*(.+)")
HEADER_MAP = {
    "#": "slot", "2b": "doubles", "3b": "triples", "so": "k", "player": "name",
    "pitches": "pitches", "pc": "pitches", "np": "pitches",
}


def slug(name: str) -> str:
    letters = "".join(ch for ch in name.lower() if ch.isalpha())
    return (letters[:8] or "player") + "01"


def parse_ip(value: str) -> int:
    text = (value or "").strip().replace("*", "")
    if not text or text in {"—", "–", "-"}:
        return 0
    if "." in text:
        whole, frac = text.split(".", 1)
        return int(whole) * 3 + int(frac[:1] or "0")
    return int(float(text) * 3)


def num(value: str) -> int:
    text = (value or "").strip().replace("*", "").replace(",", "")
    if text in {"", "—", "–", "-", "x", "X"}:
        return 0
    return int(float(text))


def norm_key(name: str) -> str:
    cleaned = name.replace("**", "").replace("*", "")
    cleaned = re.sub(r"\((?:W|L|SV|S)\)", "", cleaned)
    return " ".join(cleaned.split()).casefold()


def display_name(name: str) -> str:
    cleaned = name.replace("**", "")
    cleaned = re.sub(r"\((?:W|L|SV|S)\)", "", cleaned)
    return " ".join(cleaned.replace("*", "").split())


def load_archive() -> dict:
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def club_index(data: dict) -> dict[str, str]:
    index: dict[str, str] = {}
    for team in data["teams"]:
        index[team["name"].casefold()] = team["code"]
        index[team["code"].casefold()] = team["code"]
    return index


def player_index(data: dict) -> dict[tuple[str, str], str]:
    found: dict[tuple[str, str], str] = {}
    for game in data["games"]:
        lines = list(game.get("batting") or []) + list(game.get("pitching") or [])
        for line in lines:
            found[(line["team"], norm_key(line["name"]))] = line["player_id"]
        for side in ("W", "L", "S"):
            award = (game.get("wls") or {}).get(side)
            if award:
                found[(award["team"], norm_key(award["name"]))] = award["player_id"]
    return found


def resolve_id(team: str, name: str, players: dict[tuple[str, str], str]) -> str:
    return players.get((team, norm_key(name))) or slug(name)


def read_table(path: Path) -> tuple[dict, list[dict]]:
    meta: dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    raw = [line for line in text.splitlines() if line.strip() and not line.strip().startswith("# ")]
    comments = [line.strip()[2:] for line in text.splitlines() if line.strip().startswith("# ")]
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
    rows: list[dict] = []
    for source in reader:
        row = {}
        for key, value in zip(fields, source.values()):
            if key:
                row[key] = (value or "").strip()
        if any(row.values()):
            rows.append(row)
    return meta, rows


def check_shape(away: str, home: str, score: dict, batting: list, pitching: list, strict: bool = False) -> list[str]:
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
        if strict:
            if sum(line["h"] for line in batting) != sum(line["h"] for line in pitching):
                problems.append("batting hits do not match pitching hits")
            if sum(line["k"] for line in batting) != sum(line["k"] for line in pitching):
                problems.append("batting strikeouts do not match pitching strikeouts")
    return problems


def blank_game(game_id, series, game_no, away, home, names, score, line, winner, wls, batting, pitching, team_errors, recap, series_recap, seed, date):
    game = {
        "id": game_id,
        "series_id": series,
        "game_in_series": game_no,
        "date": date,
        "away": away,
        "home": home,
        "teams": names,
        "score": score,
        "line": line,
        "winner": winner,
        "wls": wls,
        "resolutions": None,
        "batting": batting,
        "pitching": pitching,
        "errors_by": [],
        "team_errors": team_errors,
        "final_grades": {},
        "fatigue_end_states": {},
        "game_recap": recap,
        "series_recap": series_recap,
        "rng_seed": seed,
        "scoring_plays": [],
        "injuries": [],
        "n41": None,
        "caps_in": {away: {}, home: {}},
        "caps_out": {away: {}, home: {}},
        "detail": f"games/{game_id}.json",
    }
    detail = {
        "id": game_id,
        "series_id": series,
        "game_in_series": game_no,
        "rolls": [],
        "manager_log": None,
    }
    return game, detail


def build(meta: dict, rows: list[dict], players: dict | None = None):
    players = players or {}
    for key in ("series", "game", "away", "home"):
        if key not in meta:
            raise SystemExit(f"missing # {key}")
    game_no = int(meta["game"])
    series = meta["series"]
    game_id = f"{series}-G{game_no}"
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
        player_id = row.get("player_id") or resolve_id(team, name, players)
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
                "hr": num(row["hr"]) if row.get("hr") not in (None, "") else 0,
                "hb": None,
                "bf": num(row.get("bf") or "0"),
                "entry_diff": None,
                "entry_inning": 1 if not any(line["team"] == team for line in pitching) else None,
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
                "doubles": num(row.get("doubles") or "0"),
                "triples": num(row.get("triples") or "0"),
                "hr": num(row.get("hr") or "0"),
                "rbi": num(row.get("rbi") or "0"),
                "bb": num(row.get("bb") or "0"),
                "k": num(row.get("k") or "0"),
                "hbp": num(row.get("hbp") or "0"),
                "sb": num(row.get("sb") or "0"),
                "cs": num(row.get("cs") or "0"),
                "sac": num(row.get("sac") or "0"),
                "sf": None,
                "gidp": num(row.get("gidp") or "0"),
                "ibb": None,
            })
    score, line = {}, {}
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
    wls = {
        "W": {"team": winner, "player_id": resolve_id(winner, meta.get("winner_name", "Winner"), players), "name": meta.get("winner_name", "Winner")},
        "L": {"team": loser, "player_id": resolve_id(loser, meta.get("loser_name", "Loser"), players), "name": meta.get("loser_name", "Loser")},
        "S": None,
    }
    if meta.get("save_name"):
        wls["S"] = {"team": winner, "player_id": resolve_id(winner, meta["save_name"], players), "name": meta["save_name"]}
    game, detail = blank_game(
        game_id, series, game_no, away, home, names, score, line, winner, wls, batting, pitching,
        {away: 0, home: 0}, meta.get("recap", ""), meta.get("series_recap", ""), int(meta.get("rng_seed") or 0),
        meta.get("date") or None,
    )
    return game, detail, problems


def markdown_tables(section: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in section.splitlines():
        if line.strip().startswith("|"):
            current.append([cell.strip() for cell in line.strip().strip("|").split("|")])
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def table_dicts(table: list[list[str]]) -> list[dict]:
    if len(table) < 2:
        return []
    header = []
    for cell in table[0]:
        key = cell.strip().lower().replace(" ", "").replace("#", "slot")
        header.append(HEADER_MAP.get(key, key))
    rows = []
    for raw in table[2:]:
        if raw and all(set(cell) <= set("-: ") for cell in raw):
            continue
        rows.append({key: cell for key, cell in zip(header, raw)})
    return rows


def parse_linescore(table: list[list[str]], clubs: dict[str, str]):
    header = [cell.strip() for cell in table[0]]
    try:
        r_at = header.index("R")
        e_at = header.index("E")
    except ValueError:
        return {}, {}, {}, {}, ["linescore is missing R or E"]
    line, score, errors, hits = {}, {}, {}, {}
    problems = []
    h_at = header.index("H") if "H" in header else None
    for raw in table[2:]:
        if not raw or not raw[0].strip():
            continue
        code = clubs.get(" ".join(raw[0].split()).casefold())
        if not code:
            problems.append(f"linescore club {raw[0]!r} is not in the field")
            continue
        innings = []
        for cell in raw[1:r_at]:
            if cell.strip().lower() == "x":
                continue
            innings.append(num(cell))
        line[code] = innings
        score[code] = num(raw[r_at]) if r_at < len(raw) else sum(innings)
        if h_at is not None and h_at < len(raw):
            hits[code] = num(raw[h_at])
        errors[code] = num(raw[e_at]) if e_at < len(raw) else 0
    return line, score, errors, hits, problems


def section_club(title: str, clubs: dict[str, str]):
    match = re.match(r"\s*(.+?)\s+(batting|pitching)\s*$", title, re.I)
    if not match:
        return None
    code = clubs.get(" ".join(match.group(1).split()).casefold())
    if not code:
        return None
    return code, match.group(2).lower()


def parse_markdown(text: str, data: dict, clubs: dict[str, str], players: dict[tuple[str, str], str]):
    marks = list(GAME_HEADING.finditer(text))
    if not marks:
        raise SystemExit("markdown has no '# SERIES Game N: Away at Home' heading")
    archive_names = {team["code"]: team["name"] for team in data["teams"]}
    parsed = []
    for index, mark in enumerate(marks):
        series, game_no_text, away_name, home_name = mark.groups()
        game_no = int(game_no_text)
        body = text[mark.end(): marks[index + 1].start() if index + 1 < len(marks) else len(text)]
        problems: list[str] = []
        away = clubs.get(" ".join(away_name.split()).casefold())
        home = clubs.get(" ".join(home_name.split()).casefold())
        label = f"{series}-G{game_no}"
        if not away or not home:
            parsed.append(({}, {}, [f"{label}: unknown club in heading: {away_name} at {home_name}"]))
            continue
        names = {
            away: archive_names.get(away, " ".join(away_name.split())),
            home: archive_names.get(home, " ".join(home_name.split())),
        }
        tables = markdown_tables(body)
        if not tables:
            parsed.append(({}, {}, [f"{label} has no table"]))
            continue
        line, score, errors, hit_col, line_problems = parse_linescore(tables[0], clubs)
        problems.extend(line_problems)
        if away not in score or home not in score:
            parsed.append(({}, {}, problems + [f"{label} linescore is missing a club"]))
            continue
        if score[away] == score[home]:
            problems.append(f"{label} is tied")
        batting, pitching = [], []
        for part in re.split(r"^##\s+", body, flags=re.M)[1:]:
            title, _, rest = part.partition("\n")
            found = section_club(title, clubs)
            if not found:
                continue
            code, kind = found
            part_tables = markdown_tables(rest)
            if not part_tables:
                problems.append(f"{label} {names[code]} {kind} has no table")
                continue
            if kind == "batting":
                slot_seen: dict[int, int] = {}
                for row in table_dicts(part_tables[0]):
                    raw_name = row.get("name") or ""
                    if "total" in norm_key(raw_name):
                        continue
                    sub = "*" in raw_name.replace("**", "")
                    name = display_name(raw_name)
                    if not name:
                        continue
                    slot_text = (row.get("slot") or "").strip()
                    if slot_text:
                        slot = num(slot_text)
                    elif batting and batting[-1]["team"] == code:
                        slot = batting[-1]["lineup_slot"]
                    else:
                        slot = 1 + len([item for item in batting if item["team"] == code])
                    slot_seen[slot] = slot_seen.get(slot, 0) + 1
                    batting.append({
                        "team": code,
                        "player_id": resolve_id(code, name, players),
                        "name": name,
                        "lineup_slot": slot,
                        "entry_order": 2 if sub or slot_seen[slot] > 1 else 1,
                        "is_substitute": bool(sub or slot_seen[slot] > 1),
                        "ab": num(row.get("ab")),
                        "r": num(row.get("r")),
                        "h": num(row.get("h")),
                        "doubles": num(row.get("doubles")),
                        "triples": num(row.get("triples")),
                        "hr": num(row.get("hr")),
                        "rbi": num(row.get("rbi")),
                        "bb": num(row.get("bb")),
                        "k": num(row.get("k")),
                        "hbp": num(row.get("hbp")),
                        "sb": num(row.get("sb")),
                        "cs": num(row.get("cs")),
                        "sac": num(row.get("sac")),
                        "sf": None,
                        "gidp": num(row.get("gidp")),
                        "ibb": None,
                    })
            else:
                for row in table_dicts(part_tables[0]):
                    raw_name = row.get("name") or row.get("player") or ""
                    if "total" in norm_key(raw_name):
                        continue
                    name = display_name(raw_name)
                    if not name:
                        continue
                    arm = {
                        "team": code,
                        "player_id": resolve_id(code, name, players),
                        "name": name,
                        "appearance_order": 1 + sum(1 for item in pitching if item["team"] == code),
                        "outs": parse_ip(row.get("ip") or "0"),
                        "h": num(row.get("h")),
                        "r": num(row.get("r")),
                        "er": num(row.get("er")),
                        "bb": num(row.get("bb")),
                        "k": num(row.get("k")),
                        "hr": num(row.get("hr")),
                        "hb": None,
                        "bf": num(row.get("bf")),
                        "entry_diff": None,
                        "entry_inning": 1 if not any(item["team"] == code for item in pitching) else None,
                    }
                    if (row.get("pitches") or "").strip():
                        arm["pitches"] = num(row.get("pitches"))
                    pitching.append(arm)
        winner = away if score.get(away, 0) > score.get(home, 0) else home
        loser = home if winner == away else away
        decisions = {}
        for kind, who, club in DECISION_RE.findall(body):
            decisions[kind] = (display_name(who), clubs.get(" ".join(club.split()).casefold()))
        wls = {"W": None, "L": None, "S": None}
        for label_key, side in (("W", "W"), ("L", "L"), ("SV", "S")):
            if label_key not in decisions:
                continue
            who, code = decisions[label_key]
            code = code or (winner if side != "L" else loser)
            wls[side] = {"team": code, "player_id": resolve_id(code, who, players), "name": who}
        if wls["W"] is None:
            problems.append(f"{label} has no winning pitcher")
            wls["W"] = {"team": winner, "player_id": slug("Winner"), "name": "Winner"}
        if wls["L"] is None:
            problems.append(f"{label} has no losing pitcher")
            wls["L"] = {"team": loser, "player_id": slug("Loser"), "name": "Loser"}
        problems.extend(check_shape(away, home, score, batting, pitching, strict=True))
        for code, hit_total in hit_col.items():
            counted = sum(item["h"] for item in batting if item["team"] == code)
            if counted != hit_total:
                problems.append(f"{label} {code} batting hits {counted} do not match the linescore H {hit_total}")
        recap_match = RECAP_RE.search(body)
        series_match = SERIES_RECAP_RE.search(body)
        date_match = DATE_RE.search(body)
        seed_match = SEED_RE.search(body)
        game, detail = blank_game(
            label, series, game_no, away, home, names, score, line, winner, wls, batting, pitching,
            {away: errors.get(away, 0), home: errors.get(home, 0)},
            recap_match.group(1).strip() if recap_match else "",
            series_match.group(1).strip() if series_match else "",
            int(seed_match.group(1)) if seed_match else 0,
            date_match.group(1) if date_match else None,
        )
        parsed.append((game, detail, problems))
    return parsed


def load_path(path: Path, data: dict | None = None):
    data = data or load_archive()
    clubs = club_index(data)
    players = player_index(data)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".md" or GAME_HEADING.search(text):
        return parse_markdown(text, data, clubs, players)
    meta, rows = read_table(path)
    return [build(meta, rows, players)]


BAT_COMPARE = (
    "lineup_slot", "entry_order", "is_substitute", "ab", "r", "h", "doubles", "triples",
    "hr", "rbi", "bb", "k", "hbp", "sb", "cs", "sac", "gidp",
)
PIT_COMPARE = ("appearance_order", "outs", "h", "r", "er", "bb", "k", "hr", "bf")


def compare_game(parsed: dict, stored: dict) -> list[str]:
    diffs = []
    game_id = stored["id"]
    for key in ("away", "home", "winner"):
        if parsed.get(key) != stored.get(key):
            diffs.append(f"{game_id} {key} {parsed.get(key)!r} != {stored.get(key)!r}")
    if parsed.get("score") != stored.get("score"):
        diffs.append(f"{game_id} score {parsed.get('score')} != {stored.get('score')}")
    if parsed.get("line") != stored.get("line"):
        diffs.append(f"{game_id} line {parsed.get('line')} != {stored.get('line')}")
    if parsed.get("rng_seed") and parsed.get("rng_seed") != stored.get("rng_seed"):
        diffs.append(f"{game_id} seed {parsed.get('rng_seed')} != {stored.get('rng_seed')}")
    if parsed.get("team_errors") != stored.get("team_errors"):
        diffs.append(f"{game_id} errors {parsed.get('team_errors')} != {stored.get('team_errors')}")
    for side in ("W", "L", "S"):
        got = (parsed.get("wls") or {}).get(side)
        have = (stored.get("wls") or {}).get(side)
        if bool(have) != bool(got):
            diffs.append(f"{game_id} decision {side} presence differs")
            continue
        if have and (norm_key(got["name"]) != norm_key(have["name"]) or got["team"] != have["team"]):
            diffs.append(f"{game_id} decision {side} {got['name']} ({got['team']}) != {have['name']} ({have['team']})")
    if parsed.get("game_recap") and " ".join(parsed["game_recap"].split()) != " ".join((stored.get("game_recap") or "").split()):
        diffs.append(f"{game_id} recap does not match")

    def bat_key(line):
        return (line["team"], norm_key(line["name"]), bool(line.get("is_substitute")))

    def pit_key(line):
        return (line["team"], norm_key(line["name"]), line.get("appearance_order"))

    got_b = {bat_key(line): line for line in parsed.get("batting") or []}
    have_b = {bat_key(line): line for line in stored.get("batting") or []}
    if set(got_b) != set(have_b):
        diffs.append(f"{game_id} batting names differ")
    for key in set(got_b) & set(have_b):
        for field in BAT_COMPARE:
            if got_b[key].get(field) != have_b[key].get(field):
                diffs.append(f"{game_id} {got_b[key]['name']} {field} {got_b[key].get(field)} != {have_b[key].get(field)}")
                break
    got_p = {pit_key(line): line for line in parsed.get("pitching") or []}
    have_p = {pit_key(line): line for line in stored.get("pitching") or []}
    if set(got_p) != set(have_p):
        diffs.append(f"{game_id} pitching names differ")
    for key in set(got_p) & set(have_p):
        for field in PIT_COMPARE:
            if got_p[key].get(field) != have_p[key].get(field):
                diffs.append(f"{game_id} {got_p[key]['name']} {field} {got_p[key].get(field)} != {have_p[key].get(field)}")
                break
    return diffs


def recompute_teams(data: dict) -> None:
    wins: dict[str, int] = {}
    losses: dict[str, int] = {}
    for game in data["games"]:
        loser = game["away"] if game["winner"] == game["home"] else game["home"]
        wins[game["winner"]] = wins.get(game["winner"], 0) + 1
        losses[loser] = losses.get(loser, 0) + 1
    series_wins: dict[str, int] = {}
    series_losses: dict[str, int] = {}
    for series in data["series"]:
        if series.get("status") == "complete" and series.get("winner") and series.get("loser"):
            series_wins[series["winner"]] = series_wins.get(series["winner"], 0) + 1
            series_losses[series["loser"]] = series_losses.get(series["loser"], 0) + 1
    for team in data["teams"]:
        code = team["code"]
        team["game_wins"] = wins.get(code, 0)
        team["game_losses"] = losses.get(code, 0)
        team["series_wins"] = series_wins.get(code, 0)
        team["series_losses"] = series_losses.get(code, 0)
        team["losses"] = team["series_losses"]
        team["eliminated"] = team["series_losses"] >= 2
        if team["eliminated"]:
            team["bracket"] = "eliminated"
        elif team["series_losses"] == 1:
            team["bracket"] = "losers"
        else:
            team["bracket"] = "winners"


def refresh_series(series: dict, data: dict) -> list[str]:
    games = sorted((game for game in data["games"] if game["series_id"] == series["id"]), key=lambda game: game["game_in_series"])
    problems = []
    clubs = {series.get("team_a"), series.get("team_b")}
    wins = {series["team_a"]: 0, series["team_b"]: 0}
    for game in games:
        if {game["away"], game["home"]} != clubs:
            problems.append(f"{game['id']} clubs do not match {series['id']}")
        if game["winner"] in wins:
            wins[game["winner"]] += 1
    if problems:
        return problems
    if sum(1 for value in wins.values() if value >= 4) > 1:
        return [f"{series['id']} has two clubs at 4 wins"]
    series["games"] = [game["id"] for game in games]
    series["wins"] = wins
    if any(value >= 4 for value in wins.values()):
        winner = max(wins, key=lambda code: (wins[code], code == series["team_a"]))
        series["status"] = "complete"
        series["winner"] = winner
        series["loser"] = series["team_b"] if winner == series["team_a"] else series["team_a"]
    elif games:
        series["status"] = "in-progress"
        series["winner"] = None
        series["loser"] = None
    return []


def dump(obj) -> str:
    return json.dumps(obj, indent=1) + "\n"


def regenerate() -> None:
    """Rewrite every file the site workflow checks with git diff --exit-code.

    build_cards.py runs in its preserve mode: the tournament block on
    each existing card is refreshed from tournament_results.json, and
    the repaired windows, dice, and pitching charts are not rebuilt
    from the set archive.
    """
    scripts = (
        "build_peak162.py",
        "build_rosters.py",
        "build_leaders.py",
        "build_series_previews.py",
        "build_bracket_image.py",
        "build_cards.py",
    )
    for name in scripts:
        completed = subprocess.run([sys.executable, str(ROOT / "scripts" / name)], cwd=ROOT)
        if completed.returncode != 0:
            raise RuntimeError(name + " failed")


def restore_archive(original: str, details: dict[str, str]) -> None:
    RESULTS.write_text(original, encoding="utf-8")
    for path in GAMES.glob("*.json"):
        if path.name not in details:
            path.unlink()
    for name, text in details.items():
        (GAMES / name).write_text(text, encoding="utf-8")
    regenerate()


def apply_games(parsed) -> list[str]:
    data = load_archive()
    by_id = {game["id"]: game for game in data["games"]}
    series_by_id = {series["id"]: series for series in data["series"]}
    problems: list[str] = []
    fresh = []
    for game, detail, shape_problems in parsed:
        label = game.get("id") or "game"
        if shape_problems or not game:
            problems.extend(f"{label}: {item}" for item in (shape_problems or ["could not be read"]))
            continue
        stored = by_id.get(game["id"])
        if stored:
            problems.extend(compare_game(game, stored))
            continue
        series = series_by_id.get(game["series_id"])
        if series is None:
            problems.append(f"{game['id']} series {game['series_id']} is not on the bracket")
            continue
        if series["id"] in FROZEN_SERIES:
            problems.append(f"{game['id']} would change locked series {series['id']}")
            continue
        if {game["away"], game["home"]} != {series.get("team_a"), series.get("team_b")}:
            problems.append(f"{game['id']} is {game['away']} at {game['home']}, not {series.get('team_a')} vs {series.get('team_b')}")
            continue
        expected_home = (series.get("home_by_game") or {}).get(str(game["game_in_series"]))
        if expected_home and expected_home != game["home"]:
            problems.append(f"{game['id']} home is {game['home']}; {series['id']} game {game['game_in_series']} is at {expected_home}")
            continue
        fresh.append((game, detail))
    if problems:
        return problems
    if not fresh:
        return []
    original = RESULTS.read_text(encoding="utf-8")
    detail_texts = {path.name: path.read_text(encoding="utf-8") for path in GAMES.glob("*.json")}
    try:
        touched = set()
        for game, detail in fresh:
            data["games"].append(game)
            (GAMES / f"{game['id']}.json").write_text(dump(detail), encoding="utf-8")
            touched.add(game["series_id"])
        for series_id in touched:
            problems.extend(refresh_series(series_by_id[series_id], data))
        if problems:
            raise RuntimeError("series update failed")
        recompute_teams(data)
        RESULTS.write_text(dump(data), encoding="utf-8")
        regenerate()
        completed = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_results.py")], cwd=ROOT)
        if completed.returncode != 0:
            problems.append("validator failed after the import")
            raise RuntimeError("validator failed")
    except Exception:
        restore_archive(original, detail_texts)
        if not problems:
            problems.append("import failed and the archive was restored")
        return problems
    print(f"applied {len(fresh)} game(s)")
    return []


def write_preview(parsed, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    failed = False
    for game, detail, problems in parsed:
        if not game:
            failed = True
            print("shape check failed:")
            for problem in problems:
                print(f"  - {problem}")
            continue
        (out_dir / f"{game['id']}.json").write_text(dump(game), encoding="utf-8")
        (out_dir / f"{game['id']}.detail.json").write_text(dump(detail), encoding="utf-8")
        if problems:
            failed = True
            print(f"{game['id']} shape check failed:")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"wrote {out_dir / (game['id'] + '.json')} and the detail file")
            print(f"{game['id']} shape check passed")
    return 1 if failed else 0


def check_against_archive(parsed) -> int:
    by_id = {game["id"]: game for game in load_archive()["games"]}
    failed = False
    for game, _detail, problems in parsed:
        if problems or not game:
            failed = True
            for problem in problems:
                print(f"  - {problem}")
            continue
        stored = by_id.get(game["id"])
        if stored is None:
            print(f"{game['id']} is not in the archive")
            continue
        diffs = compare_game(game, stored)
        if diffs:
            failed = True
            for diff in diffs:
                print(f"  - {diff}")
        else:
            print(f"{game['id']} matches the archive")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a box score into game JSON and check it.")
    parser.add_argument("path", help="CSV, one markdown box score, or a whole-series markdown file")
    parser.add_argument("--out", default="imports", help="Preview directory. Ignored with --check and --apply.")
    parser.add_argument("--check", action="store_true", help="Compare with games already in the archive. Write nothing.")
    parser.add_argument("--apply", action="store_true", help="Add new games, validate, and regenerate. Refuse a changed line.")
    args = parser.parse_args()
    if args.check and args.apply:
        print("use either --check or --apply")
        return 1
    path = Path(args.path)
    if not path.is_file():
        print(f"no such file: {path}")
        return 1
    try:
        parsed = load_path(path)
    except SystemExit as exc:
        print(exc)
        return 1
    if args.check:
        return check_against_archive(parsed)
    if args.apply:
        problems = apply_games(parsed)
        if problems:
            print("import failed:")
            for problem in problems:
                print(f"  - {problem}")
            return 1
        print("archive matches the validator")
        return 0
    return write_preview(parsed, ROOT / args.out)


if __name__ == "__main__":
    sys.exit(main())
