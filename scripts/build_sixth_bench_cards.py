#!/usr/bin/env python3
"""Franchise cards for the 22 active players added in the six-bench moves.

Twenty-one bench hitters and one reliever (Bobby Shantz, PHA). The method
is the current franchise-card method (build_empty_team_cards.py, PR #40
solvers): hitters use the five best franchise seasons by one-decimal
league OPS+ with PA>=300 (Hitter v0.5 dice); pitchers use the five best
franchise seasons by one-decimal ERA+ times IP with a 30 IP bullpen floor
(Pitcher v0.2.3 2d6 table). A tie between the fifth and sixth season stops
the build. None of the 22 has a 2026 franchise line, so none is added.
Hitter fielding stays the engine Average default, as on every other
franchise-built card. Rosters and tournament_results.json are not written.
"""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_cards  # noqa: E402
import build_empty_team_cards as empty  # noqa: E402
import build_missing_hitters as miss  # noqa: E402
import build_peak162 as peak  # noqa: E402

CARDS = os.path.join(ROOT, "data", "cards.json")
ROSTERS = os.path.join(ROOT, "data", "rosters.json")
RESULTS = os.path.join(ROOT, "tournament_results.json")
REPORT = os.path.join(ROOT, "historical-cards", "accuracy", "sixth_bench_cards.json")

FRANCHISE = {
    "ATL": ["BSN", "ML1", "ATL"], "BAL": ["SLA"], "COL": ["COL"], "CWS": ["CHA"],
    "DET": ["DET"], "HOU": ["HOU"], "KC": ["KCA"], "LAA": ["CAL", "ANA", "LAA"],
    "MIA": ["FLO", "MIA"], "MIL": ["ML4", "MIL"], "MIN": ["WS1", "MIN"],
    "NYM": ["NYN"], "NYY": ["NYA"], "OAK": ["OAK"], "PHA": ["PHA"], "PHI": ["PHI"],
    "PIT": ["PIT"], "SEA": ["SEA"], "SF": ["NY1", "SFN"], "TEX": ["TEX"],
    "TOR": ["TOR"], "WSH": ["WAS"],
}
TEAM_LINE = {
    "ATL": "Atlanta Braves", "BAL": "St. Louis Browns", "COL": "Colorado Rockies",
    "CWS": "Chicago White Sox", "DET": "Detroit Tigers", "HOU": "Houston Astros",
    "KC": "Kansas City Royals", "LAA": "California Angels", "MIA": "Miami Marlins",
    "MIL": "Milwaukee Brewers", "MIN": "Minnesota Twins", "NYM": "New York Mets",
    "NYY": "New York Yankees", "OAK": "Oakland Athletics", "PHA": "Philadelphia Athletics",
    "PHI": "Philadelphia Phillies", "PIT": "Pittsburgh Pirates", "SEA": "Seattle Mariners",
    "SF": "San Francisco Giants", "TEX": "Texas Rangers", "TOR": "Toronto Blue Jays",
    "WSH": "Washington Nationals",
}


def main() -> int:
    before_results = open(RESULTS, "rb").read()
    rosters = json.loads(open(ROSTERS, encoding="utf-8").read())
    before_rosters = json.dumps(rosters, sort_keys=True)
    cards = json.loads(open(CARDS, encoding="utf-8").read())
    # The catcher re-rate wrote catcher_arm_method out of key order; writing
    # with sorted keys reorders those 64 entries only. Values must not change.
    if json.loads(empty.dump_text(cards)) != cards:
        raise SystemExit("cards.json does not round-trip")
    players = []
    for code, team in rosters.items():
        for row in team["players"]:
            key = "%s|%s" % (code, row["id"])
            if key not in cards:
                players.append(dict(row, team=code, key=key))
    print("missing cards", len(players))
    empty.FRANCHISE.update(FRANCHISE)
    empty.TEAM_LINE.update(TEAM_LINE)
    miss.FRANCHISE.update(FRANCHISE)
    miss.YEAR_BOUNDS.update(empty.BOUNDS)
    batting, pitching, teams, people = empty.load_lahman()
    empty.install_team_games(teams)
    hit_rates, team_max = miss.league_rates(teams)
    pit_rates = empty.league_era(teams)
    persons = empty.people_index(people)
    by_bat, bat_max = miss.collect(batting, {p["id"] for p in players if p["kind"] == "hitter"})
    by_pit, pit_max = empty.collect_pitching(pitching, {p["id"] for p in players if p["kind"] == "pitcher"})
    if bat_max != 2025 or pit_max != 2025 or team_max < 2025:
        raise SystemExit("Lahman span %s %s %s" % (bat_max, pit_max, team_max))
    reports = []
    for player in players:
        person = persons.get(player["id"])
        if not person:
            raise SystemExit("no People row for " + player["key"])
        player["bats"], player["throws"] = empty.hands_of(person, player["key"])
        player["lahman_name"] = person["name"]
        player["y2026"] = None
        spot = {"group": player["group"], "kind": player["kind"], "pos": player["pos"], "slot": player["slot"]}
        if player["kind"] == "hitter":
            seasons, _o = miss.franchise_seasons(player["id"], player["team"], by_bat[player["id"]], hit_rates)
            latest = max((r["year"] for r in seasons), default=0)
            if latest >= 2024:
                raise SystemExit(player["key"] + " needs a 2026 check")
            player["latest"] = latest
            years, ranked = empty.choose_hitter(seasons, player["key"])
            block, nulls = empty.sum_hitter(seasons, years, TEAM_LINE[player["team"]])
            card_bat, exp, _t, status, reason, actual, best, solved = empty.solve_hitter(player, block)
            real = miss.rates_of(block)
            played = miss.card_rates(exp)
            flags, gaps = empty.hitter_flags(player, seasons, ranked, years, nulls, real, played, status, reason, solved)
            cards[player["key"]] = {
                "id": player["id"], "name": player["name"], "team": player["team"],
                "spots": [spot], "peak_bat": block, "peak_bat_162": build_cards.scale_bat_162(block),
                "peak_pit": None, "peak_pit_162": None, "card_bat": card_bat,
                "card_pit": None, "tournament": None,
            }
            reports.append({
                "key": player["key"], "name": player["name"], "kind": "hitter",
                "window_years": list(years), "qa_status": status, "fit_error": round(actual, 4),
                "real": miss.round_rates(real), "card": miss.round_rates(played),
                "delta": {k: round(v, 4) for k, v in gaps.items()}, "nulls": nulls, "flags": flags,
                "seasons": [empty.season_brief(r, "hitter") for r in seasons],
            })
            print("%s %s %s AVG %+.4f SLG %+.4f" % (player["key"], status, list(years), gaps["avg"], gaps["slg"]))
        else:
            floor = Decimal(100) if player["group"] == "rotation" else Decimal(30)
            seasons = empty.franchise_pitching(player["id"], player["team"], by_pit[player["id"]], pit_rates)
            years, ranked = empty.choose_pitcher(seasons, floor, player["key"])
            block, nulls, _tot = empty.sum_pitcher(seasons, years, TEAM_LINE[player["team"]])
            card_pit, raw, target, played, status, fit_error, mid = empty.solve_pitcher(player, block)
            notes = []
            scaled = build_cards.scale_pit_162(player["team"], player["name"], block, notes)
            player.update(y2026=None)
            flags = empty.pitcher_flags(player, seasons, ranked, years, floor, nulls, raw, target, played, status)
            cards[player["key"]] = {
                "id": player["id"], "name": player["name"], "team": player["team"],
                "spots": [spot], "peak_bat": None, "peak_bat_162": None,
                "peak_pit": block, "peak_pit_162": scaled, "card_bat": None,
                "card_pit": card_pit, "tournament": None,
            }
            reports.append({
                "key": player["key"], "name": player["name"], "kind": "pitcher",
                "window_years": list(years), "qa_status": status, "fit_error": fit_error,
                "calibration_year": mid, "raw": empty.round_rate(raw), "target": empty.round_rate(target),
                "card": empty.round_rate(played), "nulls": nulls, "flags": flags + notes,
                "seasons": [empty.season_brief(r, "pitcher") for r in seasons],
            })
            print("%s %s %s fit %s" % (player["key"], status, list(years), fit_error))
    if json.dumps(rosters, sort_keys=True) != before_rosters:
        raise SystemExit("rosters changed")
    import card_postpass
    card_postpass.finalize(cards, [p["key"] for p in players])
    empty.write_json(cards, CARDS)
    empty.write_json({"summary": {
        "players": [r["key"] for r in reports], "lahman_max_year": bat_max,
        "lahman_sha256": peak.LAHMAN_SHA256,
        "window_rule": {
            "hitters": "five best franchise seasons by league OPS+ (one decimal), PA>=300",
            "pitchers": "five best franchise seasons by one-decimal ERA+ times IP, bullpen floor 30 IP",
        }}, "players": reports}, REPORT)
    if open(RESULTS, "rb").read() != before_results:
        raise SystemExit("tournament_results.json changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
