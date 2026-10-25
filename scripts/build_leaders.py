#!/usr/bin/env python3
"""Write LEADERS.md from tournament_results.json.

Counting stats are per (team, player_id), matching stat_keying in the
results file. Thresholds are constants below. They are sized for a
tournament that still has only a handful of games, not for a 162-game
season. Re-run this after the results file changes. Do not edit
LEADERS.md by hand.
"""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "tournament_results.json"
OUT = ROOT / "LEADERS.md"

# Qualification. Outs are used for the innings floor so a fractional
# inning cannot sneak under it: 6 innings is 18 outs.
MIN_AB = 10
MIN_HR = 1
MIN_RBI = 3
MIN_OUTS = 18
MIN_K = 5
MIN_SV = 1


def load() -> dict:
    with RESULTS.open(encoding="utf-8") as handle:
        return json.load(handle)


def ip_label(outs: int) -> str:
    return f"{outs // 3}.{outs % 3}"


def avg_label(hits: int, at_bats: int) -> str:
    if at_bats <= 0:
        return "—"
    average = hits / at_bats
    if average >= 1:
        return "1.000"
    return f"{average:.3f}"[1:]


def era_label(earned: int, outs: int) -> str:
    if outs <= 0:
        return "—"
    # 9 * ER / (outs/3) = 27 * ER / outs. Half-up matches the usual ERA rounding.
    value = (Decimal(27) * Decimal(earned)) / Decimal(outs)
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def accumulate(data: dict):
    names: dict[tuple[str, str], str] = {}
    batting: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    pitching: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for game in data["games"]:
        for line in game["batting"]:
            key = (line["team"], line["player_id"])
            names[key] = line["name"]
            for field in ("ab", "h", "hr", "rbi"):
                batting[key][field] += line[field] or 0
        for line in game["pitching"]:
            key = (line["team"], line["player_id"])
            names[key] = line["name"]
            pitching[key]["outs"] += line["outs"] or 0
            pitching[key]["er"] += line["er"] or 0
            pitching[key]["k"] += line["k"] or 0
        save = (game.get("wls") or {}).get("S")
        if save:
            key = (save["team"], save["player_id"])
            names[key] = save["name"]
            pitching[key]["sv"] += 1
    return names, batting, pitching


def team_names(data: dict) -> dict[str, str]:
    return {team["code"]: team["name"] for team in data["teams"]}


def row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def batting_table(title: str, note: str, headers: list[str], lines: list[list[str]]) -> list[str]:
    block = [f"## {title}", "", note, "", row(headers), row(["---"] * len(headers))]
    if not lines:
        block.append(row(["—"] * len(headers)))
        block.append("")
        block.append("Nobody qualified.")
        block.append("")
        return block
    for line in lines:
        block.append(row(line))
    block.append("")
    return block


def build() -> str:
    data = load()
    names, batting, pitching = accumulate(data)
    clubs = team_names(data)
    games = len(data["games"])

    def club(code: str) -> str:
        return clubs.get(code, code)

    avg_lines = []
    for (code, _pid), stats in batting.items():
        if stats["ab"] < MIN_AB:
            continue
        avg_lines.append(
            (
                stats["h"] / stats["ab"],
                stats["h"],
                stats["ab"],
                names[(code, _pid)],
                [names[(code, _pid)], club(code), avg_label(stats["h"], stats["ab"]), str(stats["h"]), str(stats["ab"])],
            )
        )
    avg_lines.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))

    hr_lines = []
    for (code, pid), stats in batting.items():
        if stats["hr"] < MIN_HR:
            continue
        hr_lines.append(
            (
                stats["hr"],
                stats["rbi"],
                stats["ab"],
                names[(code, pid)],
                [names[(code, pid)], club(code), str(stats["hr"]), str(stats["rbi"]), str(stats["ab"])],
            )
        )
    hr_lines.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))

    rbi_lines = []
    for (code, pid), stats in batting.items():
        if stats["rbi"] < MIN_RBI:
            continue
        rbi_lines.append(
            (
                stats["rbi"],
                stats["hr"],
                stats["ab"],
                names[(code, pid)],
                [names[(code, pid)], club(code), str(stats["rbi"]), str(stats["hr"]), str(stats["ab"])],
            )
        )
    rbi_lines.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))

    era_lines = []
    for (code, pid), stats in pitching.items():
        if stats["outs"] < MIN_OUTS:
            continue
        earned_average = (9 * stats["er"]) / (stats["outs"] / 3)
        era_lines.append(
            (
                earned_average,
                -stats["outs"],
                names[(code, pid)],
                [
                    names[(code, pid)],
                    club(code),
                    era_label(stats["er"], stats["outs"]),
                    ip_label(stats["outs"]),
                    str(stats["er"]),
                    str(stats["k"]),
                ],
            )
        )
    era_lines.sort(key=lambda item: (item[0], item[1], item[2]))

    k_lines = []
    for (code, pid), stats in pitching.items():
        if stats["k"] < MIN_K:
            continue
        k_lines.append(
            (
                stats["k"],
                stats["outs"],
                names[(code, pid)],
                [names[(code, pid)], club(code), str(stats["k"]), ip_label(stats["outs"])],
            )
        )
    k_lines.sort(key=lambda item: (-item[0], -item[1], item[2]))

    sv_lines = []
    for (code, pid), stats in pitching.items():
        if stats["sv"] < MIN_SV:
            continue
        sv_lines.append(
            (
                stats["sv"],
                stats["outs"],
                names[(code, pid)],
                [names[(code, pid)], club(code), str(stats["sv"]), ip_label(stats["outs"])],
            )
        )
    sv_lines.sort(key=lambda item: (-item[0], -item[1], item[2]))

    parts = [
        "# Payoff Pitch Tournament 32 — Leaders",
        "",
        "Generated by `scripts/build_leaders.py` from `tournament_results.json`. Re-run the script when games are added. This file is not edited by hand.",
        "",
        f"Games on record: {games}. A player who appears for two clubs is listed once per club.",
        "",
        "## Thresholds",
        "",
        "The archive is still a few series long, so these floors are tournament floors, not a season qualifier.",
        "",
        "| Board | Minimum |",
        "|---|---|",
        f"| Batting average | {MIN_AB} at-bats |",
        f"| Home runs | {MIN_HR} |",
        f"| RBI | {MIN_RBI} |",
        f"| ERA | {MIN_OUTS // 3} innings ({MIN_OUTS} outs) |",
        f"| Strikeouts | {MIN_K} |",
        f"| Saves | {MIN_SV} |",
        "",
        "Innings are baseball innings: 7.2 is seven innings and two outs. ERA divides earned runs by outs / 3.",
        "",
    ]
    parts += batting_table(
        "Batting average",
        f"At least {MIN_AB} at-bats.",
        ["Player", "Team", "AVG", "H", "AB"],
        [item[-1] for item in avg_lines],
    )
    parts += batting_table(
        "Home runs",
        f"At least {MIN_HR} home run.",
        ["Player", "Team", "HR", "RBI", "AB"],
        [item[-1] for item in hr_lines],
    )
    parts += batting_table(
        "Runs batted in",
        f"At least {MIN_RBI} RBI.",
        ["Player", "Team", "RBI", "HR", "AB"],
        [item[-1] for item in rbi_lines],
    )
    parts += batting_table(
        "Earned run average",
        f"At least {MIN_OUTS // 3} innings.",
        ["Player", "Team", "ERA", "IP", "ER", "K"],
        [item[-1] for item in era_lines],
    )
    parts += batting_table(
        "Strikeouts",
        f"At least {MIN_K} strikeouts.",
        ["Player", "Team", "K", "IP"],
        [item[-1] for item in k_lines],
    )
    parts += batting_table(
        "Saves",
        f"At least {MIN_SV} save. A save is the `S` decision on the game, and it can be null.",
        ["Player", "Team", "SV", "IP"],
        [item[-1] for item in sv_lines],
    )
    return "\n".join(parts).rstrip() + "\n"


def main() -> None:
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
