#!/usr/bin/env python3
"""One generator for the tournament's derived documents and site files.

Reads tournament_results.json. Writes LEADERS.md, TEAM_STATS.md,
box_scores/*.md, AWARDS.md, RECORDS.md, feed/tournament.json,
feed/games.xml, scorecards/*.pdf, and the share graphics. Does not change a stat line.
"""

from __future__ import annotations

import json
import struct
import zlib
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "tournament_results.json"
SITE = "https://dvdjoe-sudo.github.io/Payoff-pitch-tournament-32/"

# Display formulas. MODELS.md states the same rules.
HIGHER_SEED_GAME_P = Decimal("0.55")
MIN_PA = 10
MIN_RATE_OUTS = 15  # 5 innings
COUNTING_LIMIT = 10
HIGH_K = 10
BIG_RUNS = 10


def load() -> dict:
    with RESULTS.open(encoding="utf-8") as handle:
        return json.load(handle)


def q2(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def q1(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}"


def ip_label(outs: int) -> str:
    return f"{outs // 3}.{outs % 3}"


def avg_label(numer: int, denom: int) -> str:
    if denom <= 0:
        return "—"
    average = Decimal(numer) / Decimal(denom)
    if average >= 1:
        return "1.000"
    text = f"{average.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)}"
    if text.startswith("0"):
        return text[1:]
    return text


def era_label(earned: int, outs: int) -> str:
    """ERA as Baseball-Reference prints it.

    Innings are thirds of an inning (outs / 3). The rate is 9 * ER / IP,
    which is 27 * ER / outs. A value that lands exactly on a half hundredth
    rounds to the even hundredth, so 1.125 is 1.12.
    """
    if outs <= 0:
        return "—"
    era = (Decimal(27) * Decimal(earned)) / Decimal(outs)
    return f"{era.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)}"


def whip_label(hits: int, walks: int, outs: int) -> str:
    if outs <= 0:
        return "—"
    return q2((Decimal(3) * Decimal(hits + walks)) / Decimal(outs))


def nz(value) -> int:
    return value or 0


def pa_of(stats: dict) -> int:
    return stats["ab"] + stats["bb"] + stats["hbp"] + stats["sac"] + stats["sf"]


def total_bases(stats: dict) -> int:
    return stats["h"] + stats["doubles"] + (2 * stats["triples"]) + (3 * stats["hr"])


def obp_label(stats: dict) -> str:
    numer = stats["h"] + stats["bb"] + stats["hbp"]
    denom = stats["ab"] + stats["bb"] + stats["hbp"] + stats["sf"]
    return avg_label(numer, denom)


def slg_label(stats: dict) -> str:
    return avg_label(total_bases(stats), stats["ab"])


def row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def md_table(headers: list[str], lines: list[list[str]]) -> list[str]:
    align = []
    for header in headers:
        align.append("---:" if header in {"AVG", "OBP", "SLG", "ERA", "WHIP", "IP", "Pts"} or header[:1].isdigit() else "---")
    # Keep a simple left-aligned rule. Numeric columns stay readable either way.
    block = [row(headers), row(["---"] * len(headers))]
    if not lines:
        block.append(row(["—"] * len(headers)))
    for line in lines:
        block.append(row(line))
    block.append("")
    return block


def blank():
    return defaultdict(int)


def accumulate(data: dict):
    names: dict[tuple[str, str], str] = {}
    batting: dict[tuple[str, str], dict[str, int]] = defaultdict(blank)
    pitching: dict[tuple[str, str], dict[str, int]] = defaultdict(blank)
    for game in data["games"]:
        for line in game["batting"]:
            key = (line["team"], line["player_id"])
            names[key] = line["name"]
            bucket = batting[key]
            for field in ("ab", "r", "h", "rbi", "bb", "k", "hbp", "sb", "cs", "sac", "sf", "gidp", "ibb", "doubles", "triples", "hr"):
                bucket[field] += nz(line[field])
        started = set()
        for line in game["pitching"]:
            key = (line["team"], line["player_id"])
            names[key] = line["name"]
            bucket = pitching[key]
            for field in ("outs", "h", "r", "er", "bb", "k", "bf", "hb", "hr"):
                if field in line:
                    bucket[field] += nz(line[field])
                    bucket[field + "_seen"] += 1
            if line["appearance_order"] == 1:
                bucket["gs"] += 1
                started.add(key)
        for decision, field in (("W", "w"), ("L", "l"), ("S", "sv")):
            award = (game.get("wls") or {}).get(decision)
            if not award:
                continue
            key = (award["team"], award["player_id"])
            names[key] = award["name"]
            pitching[key][field] += 1
    return names, batting, pitching


def clubs_of(data: dict) -> dict[str, dict]:
    return {team["code"]: team for team in data["teams"]}


def series_of(data: dict) -> dict[str, dict]:
    return {series["id"]: series for series in data["series"]}


def top_ties(rows: list[tuple], limit: int = COUNTING_LIMIT) -> list[tuple]:
    if len(rows) <= limit:
        return rows
    border = rows[limit - 1][0]
    kept = []
    for item in rows:
        if len(kept) < limit or item[0] == border:
            kept.append(item)
        else:
            break
    return kept


def system_of(game: dict) -> str:
    if game["series_id"] == "R1-01":
        return "APBA (adopted)"
    return "Payoff Pitch"


def dash(value) -> str:
    if value is None:
        return "—"
    return str(value)


def leaders_markdown(data: dict | None = None) -> str:
    data = data or load()
    names, batting, pitching = accumulate(data)
    clubs = clubs_of(data)
    played = len(data["games"])

    def club(code: str) -> str:
        team = clubs.get(code)
        return team["name"] if team else code

    def counting(title: str, note: str, headers: list[str], rows: list[tuple]) -> list[str]:
        block = [f"### {title}", "", note, ""]
        block += md_table(headers, [item[-1] for item in top_ties(rows)])
        return block

    hit_rows = {
        "h": [],
        "hr": [],
        "rbi": [],
        "r": [],
        "sb": [],
    }
    rate_rows = {"avg": [], "obp": [], "slg": []}
    for key, stats in batting.items():
        code, pid = key
        name = names[key]
        label = [name, club(code)]
        for field in hit_rows:
            if stats[field] < 1:
                continue
            hit_rows[field].append((stats[field], stats["h"], name, label + [str(stats[field])]))
        if pa_of(stats) < MIN_PA:
            continue
        average = Decimal(stats["h"]) / Decimal(stats["ab"]) if stats["ab"] else Decimal(0)
        obp_n = stats["h"] + stats["bb"] + stats["hbp"]
        obp_d = stats["ab"] + stats["bb"] + stats["hbp"] + stats["sf"]
        obp = Decimal(obp_n) / Decimal(obp_d) if obp_d else Decimal(0)
        slg = Decimal(total_bases(stats)) / Decimal(stats["ab"]) if stats["ab"] else Decimal(0)
        rate_rows["avg"].append((average, stats["h"], name, label + [avg_label(stats["h"], stats["ab"]), str(stats["h"]), str(stats["ab"]), str(pa_of(stats))]))
        rate_rows["obp"].append((obp, stats["h"], name, label + [obp_label(stats), str(pa_of(stats))]))
        rate_rows["slg"].append((slg, total_bases(stats), name, label + [slg_label(stats), str(total_bases(stats)), str(stats["ab"])]))

    for rows in hit_rows.values():
        rows.sort(key=lambda item: (-item[0], -item[1], item[2]))
    for rows in rate_rows.values():
        rows.sort(key=lambda item: (-item[0], -item[1], item[2]))

    era_rows = []
    whip_rows = []
    k_rows = []
    w_rows = []
    sv_rows = []
    ip_rows = []
    for key, stats in pitching.items():
        code, _pid = key
        name = names[key]
        label = [name, club(code)]
        outs = stats["outs"]
        if outs >= MIN_RATE_OUTS:
            era = (Decimal(27) * Decimal(stats["er"])) / Decimal(outs)
            whip = (Decimal(3) * Decimal(stats["h"] + stats["bb"])) / Decimal(outs)
            era_rows.append((era, -outs, name, label + [era_label(stats["er"], outs), ip_label(outs), str(stats["er"]), str(stats["k"])]))
            whip_rows.append((whip, -outs, name, label + [whip_label(stats["h"], stats["bb"], outs), ip_label(outs)]))
        if stats["k"] >= 1:
            k_rows.append((stats["k"], outs, name, label + [str(stats["k"]), ip_label(outs)]))
        if stats["w"] >= 1:
            w_rows.append((stats["w"], -stats["l"], name, label + [str(stats["w"]), str(stats["l"])]))
        if stats["sv"] >= 1:
            sv_rows.append((stats["sv"], outs, name, label + [str(stats["sv"]), ip_label(outs)]))
        if outs >= 1:
            ip_rows.append((outs, stats["k"], name, label + [ip_label(outs), str(stats["k"])]))
    era_rows.sort(key=lambda item: (item[0], item[1], item[2]))
    whip_rows.sort(key=lambda item: (item[0], item[1], item[2]))
    for rows in (k_rows, w_rows, sv_rows, ip_rows):
        rows.sort(key=lambda item: (-item[0], -item[1], item[2]))

    parts = [
        "# Payoff Pitch Tournament 32 — Leaders",
        "",
        "Generated by `scripts/build_leaders.py` from `tournament_results.json`. Re-run the script when games are added. This file is not edited by hand.",
        "",
        f"Cumulative through {played} games. Stats are keyed per (team, player): a player rostered by two clubs carries one line per club, never merged.",
        "",
        "Two systems, one book. R1-01 was played under APBA and adopted into the tournament by Joe's ruling. R1-02 and R1-03 were played in Payoff Pitch. These leaders are the tournament's cumulative book as adopted.",
        "",
        "## Definitions and limits",
        "",
        "- Plate appearances: AB + BB + HBP + SAC + SF as recorded. In the Payoff Pitch series, sacrifice flies are folded into the single SAC category and SF is not split out, so those plate appearances ride in SAC, and OBP uses SF as recorded (0 where the source does not split it).",
        "- Home runs allowed is recorded for the Payoff Pitch series only. The APBA-played R1-01 records do not carry it, so no tournament HR-allowed leaderboard is kept.",
        "- Rate hitting (AVG, OBP, SLG): 10 plate appearances.",
        "- Rate pitching (ERA, WHIP): 5 innings, which is 15 outs. ERA is 27 × ER / outs. A half hundredth rounds to the even hundredth, the Baseball-Reference rule, so 1 earned run in 8 innings (1.125) is 1.12. WHIP still rounds half up.",
        "- Counting tables list the top 10, with ties at the cutoff included. A counting row needs at least 1 of that stat.",
        "- Innings are baseball innings: 7.2 is seven innings and two outs.",
        "",
        "## Hitting: rate",
        "",
    ]
    parts += ["### Batting average", "", f"At least {MIN_PA} plate appearances.", ""]
    parts += md_table(["Player", "Team", "AVG", "H", "AB", "PA"], [item[-1] for item in rate_rows["avg"]])
    parts += ["### On-base percentage", "", f"At least {MIN_PA} plate appearances. (H + BB + HBP) / (AB + BB + HBP + SF).", ""]
    parts += md_table(["Player", "Team", "OBP", "PA"], [item[-1] for item in rate_rows["obp"]])
    parts += ["### Slugging", "", f"At least {MIN_PA} plate appearances. Total bases are H + 2B + 2×3B + 3×HR.", ""]
    parts += md_table(["Player", "Team", "SLG", "TB", "AB"], [item[-1] for item in rate_rows["slg"]])
    parts += ["## Hitting: counting", ""]
    parts += counting("Hits", "Top 10, ties included.", ["Player", "Team", "H"], hit_rows["h"])
    parts += counting("Home runs", "Top 10, ties included.", ["Player", "Team", "HR"], hit_rows["hr"])
    parts += counting("Runs batted in", "Top 10, ties included.", ["Player", "Team", "RBI"], hit_rows["rbi"])
    parts += counting("Runs scored", "Top 10, ties included.", ["Player", "Team", "R"], hit_rows["r"])
    parts += counting("Stolen bases", "Top 10, ties included.", ["Player", "Team", "SB"], hit_rows["sb"])
    parts += ["## Pitching: rate", ""]
    parts += ["### Earned run average", "", "At least 5 innings.", ""]
    parts += md_table(["Player", "Team", "ERA", "IP", "ER", "K"], [item[-1] for item in era_rows])
    parts += ["### WHIP", "", "At least 5 innings. (H + BB) / IP. Walks here are pitching BB. Hit batsmen are not in the numerator, because HB is not recorded for every series.", ""]
    parts += md_table(["Player", "Team", "WHIP", "IP"], [item[-1] for item in whip_rows])
    parts += ["## Pitching: counting", ""]
    parts += counting("Strikeouts", "Top 10, ties included.", ["Player", "Team", "K", "IP"], k_rows)
    parts += counting("Wins", "Top 10, ties included. A win is the W decision.", ["Player", "Team", "W", "L"], w_rows)
    parts += counting("Saves", "Top 10, ties included. A save is the S decision, and S can be null.", ["Player", "Team", "SV", "IP"], sv_rows)
    parts += counting("Innings pitched", "Top 10, ties included.", ["Player", "Team", "IP", "K"], ip_rows)
    parts += [
        "Award points and the milestone list are in [AWARDS.md](AWARDS.md) and [RECORDS.md](RECORDS.md). The formulas are in [MODELS.md](MODELS.md).",
        "",
    ]
    return "\n".join(parts).rstrip() + "\n"


def team_lines(data: dict):
    names, batting, pitching = accumulate(data)
    clubs = clubs_of(data)
    runs_for: dict[str, int] = defaultdict(int)
    runs_against: dict[str, int] = defaultdict(int)
    for game in data["games"]:
        for code, scored in game["score"].items():
            runs_for[code] += scored
            opp = game["away"] if code == game["home"] else game["home"]
            runs_against[code] += game["score"][opp]
    return names, batting, pitching, clubs, runs_for, runs_against


def team_stats_markdown(data: dict | None = None) -> str:
    data = data or load()
    names, batting, pitching, clubs, runs_for, runs_against = team_lines(data)
    played = {line["team"] for game in data["games"] for line in game["batting"]}
    parts = [
        "# Tournament Team Stats",
        "",
        f"Generated by `scripts/build_leaders.py` from `tournament_results.json`. Cumulative through {len(data['games'])} games. R1-01 was played under APBA and adopted; R1-02 and R1-03 were played in Payoff Pitch. Definitions and limits are in [LEADERS.md](LEADERS.md).",
        "",
        "## Club records",
        "",
        "| Team | Series W-L | Games W-L | Runs for | Runs against | Diff |",
        "|---|---|---|---:|---:|---:|",
    ]
    ordered = sorted(clubs.values(), key=lambda team: team["seed"])
    for team in ordered:
        if team["code"] not in played:
            continue
        code = team["code"]
        diff = runs_for[code] - runs_against[code]
        sign = f"{diff:+d}"
        parts.append(
            f"| {team['name']} ({code}) | {team['series_wins']}-{team['series_losses']} | {team['game_wins']}-{team['game_losses']} | {runs_for[code]} | {runs_against[code]} | {sign} |"
        )
    parts += ["", "Clubs with no game yet are listed after the clubs that have played.", ""]
    for team in ordered:
        code = team["code"]
        parts += [f"## {team['name']} ({code})", "", f"Seed {team['seed']}. Series record: {team['series_wins']}-{team['series_losses']} · Game record: {team['game_wins']}-{team['game_losses']}."]
        if code not in played:
            parts += ["", "No game yet.", ""]
            continue
        diff = runs_for[code] - runs_against[code]
        parts += ["", f"Runs {runs_for[code]}-{runs_against[code]}, differential {diff:+d}.", ""]
        bat_rows = []
        for (tcode, pid), stats in batting.items():
            if tcode != code:
                continue
            bat_rows.append((pa_of(stats), names[(tcode, pid)], stats, pid))
        bat_rows.sort(key=lambda item: (-item[0], item[1]))
        parts += ["### Batting", ""]
        headers = ["Player", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "SB", "AVG", "OBP", "SLG"]
        lines = []
        totals = blank()
        for _pa, name, stats, _pid in bat_rows:
            for field in ("ab", "r", "h", "doubles", "triples", "hr", "rbi", "bb", "k", "hbp", "sb", "cs", "sac", "sf"):
                totals[field] += stats[field]
            lines.append([
                name, str(pa_of(stats)), str(stats["ab"]), str(stats["r"]), str(stats["h"]),
                str(stats["doubles"]), str(stats["triples"]), str(stats["hr"]), str(stats["rbi"]),
                str(stats["bb"]), str(stats["k"]), str(stats["sb"]),
                avg_label(stats["h"], stats["ab"]), obp_label(stats), slg_label(stats),
            ])
        lines.append([
            "**Team**", str(pa_of(totals)), str(totals["ab"]), str(totals["r"]), str(totals["h"]),
            str(totals["doubles"]), str(totals["triples"]), str(totals["hr"]), str(totals["rbi"]),
            str(totals["bb"]), str(totals["k"]), str(totals["sb"]),
            avg_label(totals["h"], totals["ab"]), obp_label(totals), slg_label(totals),
        ])
        parts += md_table(headers, lines)
        pit_rows = []
        for (tcode, pid), stats in pitching.items():
            if tcode != code or stats["outs"] + stats["w"] + stats["l"] + stats["sv"] == 0:
                continue
            pit_rows.append((stats["outs"], names[(tcode, pid)], stats))
        pit_rows.sort(key=lambda item: (-item[0], item[1]))
        parts += ["### Pitching", ""]
        plines = []
        pt = blank()
        for _outs, name, stats in pit_rows:
            for field in ("w", "l", "sv", "outs", "h", "r", "er", "bb", "k"):
                pt[field] += stats[field]
            plines.append([
                name, str(stats["w"]), str(stats["l"]), str(stats["sv"]), ip_label(stats["outs"]),
                str(stats["h"]), str(stats["r"]), str(stats["er"]), str(stats["bb"]), str(stats["k"]),
                era_label(stats["er"], stats["outs"]), whip_label(stats["h"], stats["bb"], stats["outs"]),
            ])
        plines.append([
            "**Team**", str(pt["w"]), str(pt["l"]), str(pt["sv"]), ip_label(pt["outs"]),
            str(pt["h"]), str(pt["r"]), str(pt["er"]), str(pt["bb"]), str(pt["k"]),
            era_label(pt["er"], pt["outs"]), whip_label(pt["h"], pt["bb"], pt["outs"]),
        ])
        parts += md_table(["Player", "W", "L", "SV", "IP", "H", "R", "ER", "BB", "SO", "ERA", "WHIP"], plines)
    return "\n".join(parts).rstrip() + "\n"


def box_markdown(game_id: str, data: dict | None = None) -> str:
    data = data or load()
    game = next(game for game in data["games"] if game["id"] == game_id)
    series = series_of(data)[game["series_id"]]
    clubs = clubs_of(data)
    away, home = game["away"], game["home"]
    away_name = game["teams"][away]
    home_name = game["teams"][home]
    winner = game["winner"]
    loser = away if winner == home else home
    title = f"# {game['series_id']} Game {game['game_in_series']}: {away_name} at {home_name}"
    final = f"**Series:** {series['label']} ({series['id']}) · **Final:** {game['teams'][winner]} {game['score'][winner]}, {game['teams'][loser]} {game['score'][loser]} · **System:** {system_of(game)} · **Seed:** {game['rng_seed']}"
    innings = max(len(game["line"][away]), len(game["line"][home]), 9)
    header = ["Team"] + [str(n) for n in range(1, innings + 1)] + ["R", "H", "E"]
    parts = [title, "", final, ""]

    def line_row(code: str, name: str) -> list[str]:
        inn = list(game["line"][code])
        cells = [name]
        for index in range(innings):
            if index < len(inn):
                cells.append(str(inn[index]))
            elif code == home:
                cells.append("x")
            else:
                cells.append("0")
        hits = sum(nz(line["h"]) for line in game["batting"] if line["team"] == code)
        errors = game["team_errors"].get(code, 0)
        cells += [str(game["score"][code]), str(hits), str(errors)]
        return cells

    parts += md_table(header, [line_row(away, away_name), line_row(home, home_name)])
    decisions = []
    for key, label in (("W", "W"), ("L", "L"), ("S", "SV")):
        award = (game.get("wls") or {}).get(key)
        if award:
            decisions.append(f"{label}: {award['name']} ({clubs[award['team']]['name']})")
    parts += [f"**Decisions:** {' · '.join(decisions)}", ""]

    def bat_section(code: str, name: str) -> None:
        lines = [line for line in game["batting"] if line["team"] == code]
        lines.sort(key=lambda line: (line.get("lineup_slot") or 99, line.get("entry_order") or 0, line["name"]))
        parts.append(f"## {name} batting")
        parts.append("")
        headers = ["#", "Player", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "HBP", "SB", "CS", "SAC", "GIDP"]
        show_sf = any(line.get("sf") is not None for line in lines)
        if show_sf:
            headers.append("SF")
        body = []
        totals = {field: 0 for field in ("ab", "r", "h", "doubles", "triples", "hr", "rbi", "bb", "k", "hbp", "sb", "cs", "sac", "gidp", "sf")}
        any_sub = False
        for line in lines:
            any_sub = any_sub or bool(line.get("is_substitute"))
            star = " *" if line.get("is_substitute") else ""
            cells = [
                str(line["lineup_slot"]) if line.get("lineup_slot") else "",
                f"{line['name']}{star}",
                str(nz(line["ab"])), str(nz(line["r"])), str(nz(line["h"])),
                str(nz(line["doubles"])), str(nz(line["triples"])), str(nz(line["hr"])),
                str(nz(line["rbi"])), str(nz(line["bb"])), str(nz(line["k"])),
                str(nz(line["hbp"])), str(nz(line["sb"])), str(nz(line["cs"])),
                str(nz(line["sac"])), str(nz(line["gidp"])),
            ]
            if show_sf:
                cells.append(dash(line.get("sf")))
            body.append(cells)
            for field in totals:
                totals[field] += nz(line[field])
        total_cells = [
            "", "**Totals**", str(totals["ab"]), str(totals["r"]), str(totals["h"]),
            str(totals["doubles"]), str(totals["triples"]), str(totals["hr"]),
            str(totals["rbi"]), str(totals["bb"]), str(totals["k"]), str(totals["hbp"]),
            str(totals["sb"]), str(totals["cs"]), str(totals["sac"]), str(totals["gidp"]),
        ]
        if show_sf:
            total_cells.append(str(totals["sf"]))
        body.append(total_cells)
        parts.extend(md_table(headers, body))
        plate = totals["ab"] + totals["bb"] + totals["hbp"] + totals["sac"] + totals["sf"]
        parts.append(f"Plate appearances: {plate}.")
        if any_sub:
            parts.append("* Entered as a substitute.")
        parts.append("")

    def pit_section(code: str, name: str) -> None:
        lines = [line for line in game["pitching"] if line["team"] == code]
        lines.sort(key=lambda line: line["appearance_order"])
        parts.append(f"## {name} pitching")
        parts.append("")
        headers = ["Player", "IP", "H", "R", "ER", "BB", "SO", "HR", "HB", "BF"]
        body = []
        outs = 0
        totals = {field: 0 for field in ("h", "r", "er", "bb", "k", "bf")}
        hr_total = 0
        hb_total = 0
        hr_known = True
        hb_known = True
        marks = {}
        for key, tag in (("W", "W"), ("L", "L"), ("S", "SV")):
            award = (game.get("wls") or {}).get(key)
            if award and award["team"] == code:
                marks[award["player_id"]] = tag
        for line in lines:
            tag = marks.get(line["player_id"])
            label = line["name"] + (f" ({tag})" if tag else "")
            hr = line["hr"] if "hr" in line else None
            hb = line["hb"] if "hb" in line else None
            if hr is None:
                hr_known = False
            else:
                hr_total += hr
            if hb is None:
                hb_known = False
            else:
                hb_total += hb
            outs += nz(line["outs"])
            for field in totals:
                totals[field] += nz(line[field])
            body.append([
                label, ip_label(nz(line["outs"])), str(nz(line["h"])), str(nz(line["r"])),
                str(nz(line["er"])), str(nz(line["bb"])), str(nz(line["k"])),
                dash(hr), dash(hb), str(nz(line["bf"])),
            ])
        body.append([
            "**Totals**", ip_label(outs), str(totals["h"]), str(totals["r"]), str(totals["er"]),
            str(totals["bb"]), str(totals["k"]), dash(hr_total if hr_known else None),
            dash(hb_total if hb_known else None), str(totals["bf"]),
        ])
        parts.extend(md_table(headers, body))

    bat_section(away, away_name)
    pit_section(away, away_name)
    bat_section(home, home_name)
    pit_section(home, home_name)
    parts += [
        f"**Game recap (from the archive):** {game.get('game_recap') or '—'}",
        "",
        f"**Series state after this game:** {game.get('series_recap') or '—'}",
        "",
        f"Generated from tournament_results.json (game record {game['id']}) by scripts/build_leaders.py. APBA-only counters with no Payoff Pitch equivalent, and the reverse, stay empty in the archive; HR allowed and HB are shown where the record carries them.",
        "",
    ]
    return "\n".join(parts).rstrip() + "\n"


def award_boards(data: dict):
    names, batting, pitching = accumulate(data)
    clubs = clubs_of(data)
    mvp = []
    for key, stats in batting.items():
        if pa_of(stats) <= 0 and stats["h"] <= 0:
            continue
        points = (
            Decimal(total_bases(stats) + stats["r"] + stats["rbi"] + stats["sb"] - stats["cs"])
            + (Decimal("0.5") * Decimal(stats["bb"]))
            + (Decimal("0.5") * Decimal(stats["hbp"]))
        )
        mvp.append((points, names[key], key, stats))
    mvp.sort(key=lambda item: (-item[0], item[1]))
    cy = []
    relief = []
    for key, stats in pitching.items():
        if stats["outs"] + stats["w"] + stats["sv"] == 0:
            continue
        ip = Decimal(stats["outs"]) / Decimal(3)
        code, _pid = key
        if stats["gs"] >= 1:
            points = ip + (Decimal("0.4") * Decimal(stats["k"])) + (Decimal(5) * Decimal(stats["w"])) - (Decimal("1.5") * Decimal(stats["er"])) - (Decimal("0.3") * Decimal(stats["bb"]))
            cy.append((points, names[key], key, stats))
        elif stats["gs"] == 0:
            points = (Decimal(5) * Decimal(stats["sv"])) + (Decimal(2) * ip) + (Decimal("0.4") * Decimal(stats["k"])) - (Decimal("1.5") * Decimal(stats["er"]))
            relief.append((points, names[key], key, stats))
    cy.sort(key=lambda item: (-item[0], item[1]))
    relief.sort(key=lambda item: (-item[0], item[1]))
    return clubs, mvp, cy, relief


def awards_markdown(data: dict | None = None) -> str:
    data = data or load()
    clubs, mvp, cy, relief = award_boards(data)
    parts = [
        "# Awards race",
        "",
        "Generated by `scripts/build_leaders.py`. These points are a tournament display. They are not an official vote and they are not a Major League award. The formula is stated in [MODELS.md](MODELS.md).",
        "",
        "## Most valuable player",
        "",
        "Hitters. Total bases + R + RBI + SB + 0.5×BB + 0.5×HBP − CS. Total bases = H + 2B + 2×3B + 3×HR.",
        "",
    ]
    parts += md_table(
        ["Player", "Team", "Pts", "TB", "R", "RBI", "HR"],
        [[
            name, clubs[key[0]]["name"], q1(points), str(total_bases(stats)), str(stats["r"]), str(stats["rbi"]), str(stats["hr"]),
        ] for points, name, key, stats in mvp[:15]],
    )
    parts += [
        "## Cy Young",
        "",
        "Pitchers with at least one start. IP + 0.4×K + 5×W − 1.5×ER − 0.3×BB. IP is outs / 3.",
        "",
    ]
    parts += md_table(
        ["Player", "Team", "Pts", "IP", "W", "K", "ER"],
        [[
            name, clubs[key[0]]["name"], q1(points), ip_label(stats["outs"]), str(stats["w"]), str(stats["k"]), str(stats["er"]),
        ] for points, name, key, stats in cy[:15]],
    )
    parts += [
        "## Reliever",
        "",
        "Pitchers with zero starts. 5×SV + 2×IP + 0.4×K − 1.5×ER.",
        "",
    ]
    parts += md_table(
        ["Player", "Team", "Pts", "SV", "IP", "K", "ER"],
        [[
            name, clubs[key[0]]["name"], q1(points), str(stats["sv"]), ip_label(stats["outs"]), str(stats["k"]), str(stats["er"]),
        ] for points, name, key, stats in relief[:15]],
    )
    return "\n".join(parts).rstrip() + "\n"


def milestones(data: dict) -> dict:
    nohitters = []
    high_k = []
    big = []
    for game in data["games"]:
        for line in game["pitching"]:
            if line["appearance_order"] == 1 and nz(line["h"]) == 0 and nz(line["outs"]) >= 27:
                nohitters.append({
                    "game": game["id"],
                    "name": line["name"],
                    "team": line["team"],
                    "ip": ip_label(line["outs"]),
                    "k": nz(line["k"]),
                    "bb": nz(line["bb"]),
                })
            if nz(line["k"]) >= HIGH_K:
                high_k.append({
                    "game": game["id"],
                    "name": line["name"],
                    "team": line["team"],
                    "k": nz(line["k"]),
                    "ip": ip_label(line["outs"]),
                })
        for code, scored in game["score"].items():
            if scored >= BIG_RUNS:
                big.append({"game": game["id"], "team": code, "runs": scored, "opponent": game["away"] if code == game["home"] else game["home"]})
    high_k.sort(key=lambda item: (-item["k"], item["game"], item["name"]))
    return {"nohitters": nohitters, "high_k": high_k, "big_games": big}


def records_markdown(data: dict | None = None) -> str:
    data = data or load()
    clubs = clubs_of(data)
    found = milestones(data)
    parts = [
        "# Records and milestones",
        "",
        "Generated by `scripts/build_leaders.py` from the box scores. A line appears only when the recorded stats meet the bar in [MODELS.md](MODELS.md). Nothing here is estimated.",
        "",
        "## No-hitters",
        "",
        "A start of at least 9 innings (27 outs) with 0 hits.",
        "",
    ]
    if not found["nohitters"]:
        parts += ["None on record.", ""]
    for item in found["nohitters"]:
        parts.append(f"- {item['name']} ({clubs[item['team']]['name']}), {item['game']}: {item['ip']} IP, 0 H, {item['k']} K, {item['bb']} BB.")
    parts += ["", "## Ten or more strikeouts", ""]
    for item in found["high_k"]:
        parts.append(f"- {item['name']} ({clubs[item['team']]['name']}), {item['game']}: {item['k']} K in {item['ip']} IP.")
    parts += ["", "## Games with 10 or more runs", ""]
    for item in found["big_games"]:
        parts.append(f"- {clubs[item['team']]['name']} scored {item['runs']} against {clubs[item['opponent']]['name']} in {item['game']}.")
    parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def series_prob(wins_for: int, wins_against: int, p: Decimal = HIGHER_SEED_GAME_P) -> Decimal:
    """Probability `wins_for` side reaches 4 first. Each game is an independent `p`."""
    need_for = 4 - wins_for
    need_against = 4 - wins_against
    memo: dict[tuple[int, int], Decimal] = {}

    def walk(left: int, opp: int) -> Decimal:
        if left <= 0:
            return Decimal(1)
        if opp <= 0:
            return Decimal(0)
        key = (left, opp)
        if key in memo:
            return memo[key]
        value = p * walk(left - 1, opp) + (Decimal(1) - p) * walk(left, opp - 1)
        memo[key] = value
        return value

    return walk(need_for, need_against)


def feed_document(data: dict | None = None) -> dict:
    data = data or load()
    clubs = clubs_of(data)
    games = []
    for game in data["games"]:
        games.append({
            "id": game["id"],
            "series_id": game["series_id"],
            "game_in_series": game["game_in_series"],
            "date": game.get("date"),
            "away": game["away"],
            "home": game["home"],
            "away_name": game["teams"][game["away"]],
            "home_name": game["teams"][game["home"]],
            "away_runs": game["score"][game["away"]],
            "home_runs": game["score"][game["home"]],
            "winner": game["winner"],
            "recap": game.get("game_recap"),
            "rng_seed": game.get("rng_seed"),
            "url": f"{SITE}#/game/{game['id']}",
        })
    nxt = None
    for series in data["series"]:
        if series["status"] != "in-progress":
            continue
        number = len(series["games"]) + 1
        home = (series.get("home_by_game") or {}).get(str(number))
        if not home or not series.get("team_a"):
            continue
        away = series["team_b"] if home == series["team_a"] else series["team_a"]
        starters = (series.get("carry") or {}).get("rotation_next_start") or {}
        nxt = {
            "series_id": series["id"],
            "game_in_series": number,
            "home": home,
            "away": away,
            "home_name": clubs[home]["name"],
            "away_name": clubs[away]["name"],
            "starters": starters,
        }
        break
    return {
        "title": "Payoff Pitch Tournament 32",
        "site": SITE,
        "games_played": len(data["games"]),
        "next_up": nxt,
        "games": games,
    }


def feed_json_text(data: dict | None = None) -> str:
    return json.dumps(feed_document(data), indent=1, ensure_ascii=False) + "\n"


def rss_text(data: dict | None = None) -> str:
    data = data or load()
    doc = feed_document(data)
    items = []
    for game in reversed(doc["games"]):
        title = f"{game['id']}: {game['away_name']} {game['away_runs']}, {game['home_name']} {game['home_runs']}"
        description = game["recap"] or title
        day = game["date"] or "2026-10-24"
        items.append(
            "    <item>\n"
            f"      <title>{escape(title)}</title>\n"
            f"      <link>{escape(game['url'])}</link>\n"
            f"      <guid>{escape(game['url'])}</guid>\n"
            f"      <pubDate>{day}</pubDate>\n"
            f"      <description>{escape(description)}</description>\n"
            "    </item>"
        )
    body = "\n".join(items)
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<rss version=\"2.0\">\n"
        "  <channel>\n"
        "    <title>Payoff Pitch Tournament 32</title>\n"
        f"    <link>{SITE}</link>\n"
        "    <description>Final scores from the Payoff Pitch 32-team tournament.</description>\n"
        f"{body}\n"
        "  </channel>\n"
        "</rss>\n"
    )


# 5x7 glyphs, top row first, bit 4 is the left pixel.
FONT = {
    "A": "01110,10001,10001,11111,10001,10001,10001",
    "B": "11110,10001,10001,11110,10001,10001,11110",
    "C": "01110,10001,10000,10000,10000,10001,01110",
    "D": "11110,10001,10001,10001,10001,10001,11110",
    "E": "11111,10000,10000,11110,10000,10000,11111",
    "F": "11111,10000,10000,11110,10000,10000,10000",
    "G": "01110,10001,10000,10111,10001,10001,01110",
    "H": "10001,10001,10001,11111,10001,10001,10001",
    "I": "01110,00100,00100,00100,00100,00100,01110",
    "J": "00111,00010,00010,00010,10010,10010,01100",
    "K": "10001,10010,10100,11000,10100,10010,10001",
    "L": "10000,10000,10000,10000,10000,10000,11111",
    "M": "10001,11011,10101,10101,10001,10001,10001",
    "N": "10001,11001,10101,10011,10001,10001,10001",
    "O": "01110,10001,10001,10001,10001,10001,01110",
    "P": "11110,10001,10001,11110,10000,10000,10000",
    "Q": "01110,10001,10001,10001,10101,10010,01101",
    "R": "11110,10001,10001,11110,10100,10010,10001",
    "S": "01111,10000,10000,01110,00001,00001,11110",
    "T": "11111,00100,00100,00100,00100,00100,00100",
    "U": "10001,10001,10001,10001,10001,10001,01110",
    "V": "10001,10001,10001,10001,10001,01010,00100",
    "W": "10001,10001,10001,10101,10101,10101,01010",
    "X": "10001,10001,01010,00100,01010,10001,10001",
    "Y": "10001,10001,01010,00100,00100,00100,00100",
    "Z": "11111,00001,00010,00100,01000,10000,11111",
    "0": "01110,10001,10011,10101,11001,10001,01110",
    "1": "00100,01100,00100,00100,00100,00100,01110",
    "2": "01110,10001,00001,00010,00100,01000,11111",
    "3": "11110,00001,00001,01110,00001,00001,11110",
    "4": "00010,00110,01010,10010,11111,00010,00010",
    "5": "11111,10000,10000,11110,00001,00001,11110",
    "6": "01110,10000,10000,11110,10001,10001,01110",
    "7": "11111,00001,00010,00100,01000,01000,01000",
    "8": "01110,10001,10001,01110,10001,10001,01110",
    "9": "01110,10001,10001,01111,00001,00001,01110",
    " ": "00000,00000,00000,00000,00000,00000,00000",
    ".": "00000,00000,00000,00000,00000,01100,01100",
    "-": "00000,00000,00000,11111,00000,00000,00000",
    ":": "00000,01100,01100,00000,01100,01100,00000",
}


def _png(width: int, height: int, rows: list[bytes]) -> bytes:
    raw = b"".join(b"\x00" + row for row in rows)
    def chunk(tag: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def _canvas(width: int, height: int, color: tuple[int, int, int]) -> bytearray:
    pixel = bytes(color)
    return bytearray(pixel * (width * height))


def _set(buf: bytearray, width: int, x: int, y: int, color: tuple[int, int, int]) -> None:
    height_limit = len(buf) // (width * 3)
    if x < 0 or y < 0 or x >= width or y >= height_limit:
        return
    index = (y * width + x) * 3
    buf[index:index + 3] = bytes(color)


def _fill(buf: bytearray, width: int, x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            _set(buf, width, xx, yy, color)


def _text(buf: bytearray, width: int, x: int, y: int, text: str, color: tuple[int, int, int], scale: int = 3) -> None:
    cursor = x
    for char in text.upper():
        glyph = FONT.get(char, FONT[" "])
        rows = [int(part, 2) for part in glyph.split(",")]
        for row_index, bits in enumerate(rows):
            for col in range(5):
                if bits & (1 << (4 - col)):
                    _fill(buf, width, cursor + col * scale, y + row_index * scale, scale, scale, color)
        cursor += 6 * scale


def _rows(buf: bytearray, width: int, height: int) -> list[bytes]:
    row_bytes = width * 3
    return [bytes(buf[y * row_bytes:(y + 1) * row_bytes]) for y in range(height)]


def _card_png(lines: list[tuple[str, int]]) -> bytes:
    width, height = 640, 360
    navy = (18, 38, 63)
    gold = (198, 161, 90)
    cream = (246, 241, 230)
    buf = _canvas(width, height, navy)
    _fill(buf, width, 0, 0, width, 8, gold)
    _fill(buf, width, 0, height - 8, width, 8, gold)
    y = 28
    for text, scale in lines:
        _text(buf, width, 28, y, text, cream if scale < 5 else gold, scale)
        y += 8 * scale + 12
    return _png(width, height, _rows(buf, width, height))


def game_png(game: dict) -> bytes:
    away, home = game["away"], game["home"]
    lines = [
        ("PAYOFF PITCH", 3),
        (f"{game['id']}  FINAL", 3),
        (f"{away}  {game['score'][away]}", 5),
        (f"{home}  {game['score'][home]}", 5),
        (game["teams"][game["winner"]].upper()[:22], 3),
    ]
    return _card_png(lines)


def series_png(series: dict, clubs: dict[str, dict]) -> bytes:
    a, b = series["team_a"], series["team_b"]
    wins = series.get("wins") or {}
    state = "FINAL" if series["status"] == "complete" else series["status"].upper()
    lines = [
        ("PAYOFF PITCH", 3),
        (f"{series['id']}  {state}", 3),
        (f"{a}  {wins.get(a, 0)}", 5),
        (f"{b}  {wins.get(b, 0)}", 5),
        ((clubs[series["winner"]]["name"].upper()[:22]) if series.get("winner") else "SERIES OPEN", 3),
    ]
    return _card_png(lines)


def _svg(lines: list[str]) -> str:
    body = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360" role="img">',
        '<rect width="640" height="360" fill="#12263f"/>',
        '<rect width="640" height="8" fill="#c6a15a"/>',
        '<rect y="352" width="640" height="8" fill="#c6a15a"/>',
    ]
    y = 64
    for text, size in lines:
        body.append(
            f'<text x="32" y="{y}" fill="#f6f1e6" font-family="Georgia, serif" font-size="{size}">{escape(text)}</text>'
        )
        y += size + 18
    body.append("</svg>")
    return "\n".join(body) + "\n"


def game_svg(game: dict) -> str:
    away, home = game["away"], game["home"]
    return _svg([
        ("Payoff Pitch", 22),
        (f"{game['id']} final", 28),
        (f"{game['teams'][away]} {game['score'][away]}", 36),
        (f"{game['teams'][home]} {game['score'][home]}", 36),
        (f"Winner {game['teams'][game['winner']]}", 22),
    ])


def series_svg(series: dict, clubs: dict[str, dict]) -> str:
    a, b = series["team_a"], series["team_b"]
    wins = series.get("wins") or {}
    status = "Final" if series["status"] == "complete" else "In progress"
    last = clubs[series["winner"]]["name"] if series.get("winner") else "Series open"
    return _svg([
        ("Payoff Pitch", 22),
        (f"{series['id']} {status}", 28),
        (f"{clubs[a]['name']} {wins.get(a, 0)}", 36),
        (f"{clubs[b]['name']} {wins.get(b, 0)}", 36),
        (last, 22),
    ])


def write_all() -> None:
    data = load()
    (ROOT / "LEADERS.md").write_text(leaders_markdown(data), encoding="utf-8")
    (ROOT / "TEAM_STATS.md").write_text(team_stats_markdown(data), encoding="utf-8")
    box_dir = ROOT / "box_scores"
    box_dir.mkdir(exist_ok=True)
    keep = set()
    for game in data["games"]:
        path = box_dir / f"{game['id']}.md"
        path.write_text(box_markdown(game["id"], data), encoding="utf-8")
        keep.add(path.name)
    for path in box_dir.glob("*.md"):
        if path.name not in keep:
            path.unlink()
    (ROOT / "AWARDS.md").write_text(awards_markdown(data), encoding="utf-8")
    (ROOT / "RECORDS.md").write_text(records_markdown(data), encoding="utf-8")
    feed = ROOT / "feed"
    feed.mkdir(exist_ok=True)
    (feed / "tournament.json").write_text(feed_json_text(data), encoding="utf-8")
    (feed / "games.xml").write_text(rss_text(data), encoding="utf-8")
    clubs = clubs_of(data)
    game_dir = ROOT / "graphics" / "games"
    series_dir = ROOT / "graphics" / "series"
    game_dir.mkdir(parents=True, exist_ok=True)
    series_dir.mkdir(parents=True, exist_ok=True)
    game_keep = set()
    for game in data["games"]:
        (game_dir / f"{game['id']}.svg").write_text(game_svg(game), encoding="utf-8")
        (game_dir / f"{game['id']}.png").write_bytes(game_png(game))
        game_keep.add(game["id"])
    series_keep = set()
    for series in data["series"]:
        if series["status"] not in {"complete", "in-progress"} or not series.get("team_a"):
            continue
        (series_dir / f"{series['id']}.svg").write_text(series_svg(series, clubs), encoding="utf-8")
        (series_dir / f"{series['id']}.png").write_bytes(series_png(series, clubs))
        series_keep.add(series["id"])
    for folder, keep_ids in ((game_dir, game_keep), (series_dir, series_keep)):
        for path in folder.iterdir():
            if path.stem not in keep_ids:
                path.unlink()
    import importlib.util
    for name in ("odds", "sharekit"):
        spec = importlib.util.spec_from_file_location(name + "_build", Path(__file__).with_name(name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if name == "odds":
            (ROOT / "feed" / "odds.json").write_text(module.text(data), encoding="utf-8")
        else:
            module.write_share(data)
    cards = importlib.util.spec_from_file_location("scorecards_build", Path(__file__).with_name("scorecards.py"))
    scorecards = importlib.util.module_from_spec(cards)
    cards.loader.exec_module(scorecards)
    scorecards.write_scorecards(data)
    print(f"wrote leaders, team stats, {len(data['games'])} box scores, awards, records, feeds, graphics, scorecards")


if __name__ == "__main__":
    write_all()
