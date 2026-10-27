#!/usr/bin/env python3
"""Franchise hitter cards for bench players added when a club went to 6/6.

Rickey Henderson (Yankees), Juan Pierre (Marlins), and Monte Irvin
(Giants). The window is the same rule as the empty-team cards: the five
best franchise seasons by one-decimal league OPS+, among seasons of at
least 300 plate appearances (AB + BB + HBP + SF). A tie between the
fifth and sixth season stops the build. Dice come from Hitter v0.5.
Fielding stays the engine Average default. No 2026 line is invented.
Played games are not written.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "engines", "hitter-v0.5"))

import build_cards  # noqa: E402
import build_empty_team_cards as empty  # noqa: E402
import build_missing_hitters as miss  # noqa: E402

CARDS = os.path.join(ROOT, "data", "cards.json")
ROSTERS = os.path.join(ROOT, "data", "rosters.json")
RESULTS = os.path.join(ROOT, "tournament_results.json")
REPORT = os.path.join(ROOT, "historical-cards", "accuracy", "bench_six_hitters.json")
USER_ROSTERS = "2c600f1db7fc9d7ff63d125e2555e201ce2c0ea7"

PLAYERS = (
    {
        "team": "NYY", "id": "henderi01", "name": "Rickey Henderson",
        "group": "bench", "slot": 6, "pos": "OF",
        "franchise": ["NYA"], "team_line": "New York Yankees",
    },
    {
        "team": "MIA", "id": "pierrju01", "name": "Juan Pierre",
        "group": "bench", "slot": 6, "pos": "CF",
        "franchise": ["FLO", "MIA"], "team_line": "Miami Marlins",
    },
    {
        "team": "SF", "id": "irvinmo01", "name": "Monte Irvin",
        "group": "bench", "slot": 6, "pos": "LF",
        "franchise": ["SFN", "NY1"], "team_line": "San Francisco Giants",
    },
)
ARCHIVED = ("MIA|burneaj01", "NYY|stantmi02")


def main() -> int:
    before_results = open(RESULTS, "rb").read()
    for spec in PLAYERS:
        empty.FRANCHISE[spec["team"]] = spec["franchise"]
        empty.TEAM_LINE[spec["team"]] = spec["team_line"]
    batting, _pitching, teams, people = empty.load_lahman()
    empty.install_team_games(teams)
    hit_rates, team_max = miss.league_rates(teams)
    persons = empty.people_index(people)
    miss.FRANCHISE.update(empty.FRANCHISE)
    wanted = {spec["id"] for spec in PLAYERS}
    by_bat, bat_max = miss.collect(batting, wanted)
    if bat_max != 2025 or team_max < 2025:
        raise SystemExit("Lahman span batting %s teams %s" % (bat_max, team_max))
    cards = json.loads(open(CARDS, encoding="utf-8").read())
    if empty.dump_text(cards) != open(CARDS, encoding="utf-8").read():
        raise SystemExit("cards.json does not round-trip")
    rosters = json.loads(open(ROSTERS, encoding="utf-8").read())
    user = json.loads(subprocess.check_output(
        ["git", "show", "%s:data/rosters.json" % USER_ROSTERS]))
    for code in ("MIA", "NYY"):
        rosters[code]["players"] = user[code]["players"]
        if [p["id"] for p in rosters[code]["players"]] != [p["id"] for p in user[code]["players"]]:
            raise SystemExit("roster copy failed for " + code)

    reports = []
    for spec in PLAYERS:
        player = {
            "team": spec["team"], "group": spec["group"], "slot": spec["slot"],
            "pos": spec["pos"], "kind": "hitter", "name": spec["name"],
            "id": spec["id"], "key": "%s|%s" % (spec["team"], spec["id"]),
        }
        person = persons.get(player["id"])
        if not person:
            raise SystemExit("no People row for " + player["key"])
        player["bats"], player["throws"] = empty.hands_of(person, player["key"])
        player["lahman_name"] = person["name"]
        seasons, _others = miss.franchise_seasons(
            player["id"], player["team"], by_bat[player["id"]], hit_rates)
        latest = max((row["year"] for row in seasons), default=0)
        if latest >= 2024:
            raise SystemExit("%s needs a 2026 franchise check; latest year %s" % (
                player["key"], latest))
        player["y2026"] = None
        player["latest"] = latest
        years, ranked = empty.choose_hitter(seasons, player["key"])
        block, nulls = empty.sum_hitter(seasons, years, spec["team_line"])
        card_bat, exp, _tgt, status, reason, actual, best, solved = empty.solve_hitter(player, block)
        real = miss.rates_of(block)
        played = miss.card_rates(exp)
        flags, gaps = empty.hitter_flags(
            player, seasons, ranked, years, nulls, real, played, status, reason, solved)
        scaled = build_cards.scale_bat_162(block)
        spot = {
            "group": player["group"], "kind": "hitter",
            "pos": player["pos"], "slot": player["slot"],
        }
        previous = cards.get(player["key"]) or {}
        cards[player["key"]] = {
            "id": player["id"], "name": player["name"], "team": player["team"],
            "spots": [spot], "peak_bat": block, "peak_bat_162": scaled,
            "peak_pit": None, "peak_pit_162": None, "card_bat": card_bat,
            "card_pit": None, "tournament": previous.get("tournament"),
        }
        print("%s %s years %s %s AVG %+.4f SLG %+.4f" % (
            player["key"], status, list(years), player["bats"], gaps["avg"], gaps["slg"]))
        reports.append({
            "key": player["key"], "name": player["name"], "team": player["team"],
            "kind": "hitter", "window_years": list(years), "qa_status": status,
            "fit_error": round(actual, 4), "best_possible": round(best, 4),
            "counting": {key: block[key] for key in build_cards.BAT_COUNTING},
            "real": miss.round_rates(real), "card": miss.round_rates(played),
            "delta": {key: round(value, 4) for key, value in gaps.items()},
            "nulls": nulls, "flags": flags,
            "seasons": [empty.season_brief(row, "hitter") for row in seasons],
        })

    for code in ("MIA", "NYY"):
        for player in rosters[code]["players"]:
            key = "%s|%s" % (code, player["id"])
            card = cards.get(key)
            if not card:
                raise SystemExit("active player has no card: " + key)
            card["spots"] = [{
                "group": player["group"], "kind": player["kind"],
                "pos": player["pos"], "slot": player["slot"],
            }]
    for key in ARCHIVED:
        card = cards.get(key)
        if not ((card or {}).get("card_bat") or {}).get("sections") and not (
                (card or {}).get("card_pit") or {}).get("table_2d6"):
            raise SystemExit("archived card missing: " + key)
        card["spots"] = []
    irvin = cards["SF|irvinmo01"]
    irvin["spots"] = [{"group": "bench", "kind": "hitter", "pos": "LF", "slot": 6}]

    empty.write_json(cards, CARDS)
    empty.write_json(rosters, ROSTERS)
    empty.write_json({
        "summary": {
            "players": [row["key"] for row in reports],
            "lahman_max_year": bat_max,
            "lahman_sha256": __import__("build_peak162").LAHMAN_SHA256,
            "window_rule": (
                "five best franchise seasons by league OPS+ rounded half up "
                "to one decimal, PA>=300 where PA=AB+BB+HBP+SF"
            ),
        },
        "players": reports,
    }, REPORT)
    after_results = open(RESULTS, "rb").read()
    if after_results != before_results:
        raise SystemExit("tournament_results.json changed")
    print("wrote", REPORT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
