#!/usr/bin/env python3
"""Dual appearance regression test (2026-10-30).

Joe ruled on R1-06 Game 4 (2026-10-29) that Andre Dawson batting
for both Chicago and Montreal counts exactly as played, because
they are different teams. The book keys stats per (team,
player_id) end to end, so one man's two lines must stay two lines:
through the validator's reconcile, through the roster-membership
check, through publish.accumulate, and onto the leaders boards.
The 2026-10-29 multi-roster audit found 66 ids on two or more of
the 32 rosters (Fingers, A. Rodriguez, and Ryan on three each),
and no gate had ever exercised a dual appearance.

The synthetic game below lives only in memory. It never enters
tournament_results.json or games/. It replaces R1-06 Game 4 inside
a deep copy of the book, same id and same winner, so series and
team records reconcile exactly as the real book does, while
dawsoan01 bats for both clubs with every cross-check live:
pitching HR and HB recorded on every line, SAC and SF split,
batters faced filled in. The leaders half runs on the synthetic
game alone, so Dawson's two rows stand or fall on their own.

Run with the pipeline venv python:
  ~/workspace/.venv-pp-t32/bin/python scripts/test_dual_appearance.py
Exit 1 on any failed check.
"""

from __future__ import annotations

import copy
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import publish  # noqa: E402
import validate_results as vr  # noqa: E402

RESULTS: list[tuple[str, bool]] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    RESULTS.append((label, bool(cond)))
    print(("PASS " if cond else "FAIL ") + label + ("" if cond else " -- " + str(detail)))


def roster_entry(rosters: dict, code: str, name: str) -> dict:
    for player in rosters[code]["players"]:
        if player["name"] == name:
            return player
    raise AssertionError(f"{name} is not on the {code} roster")


def bat(team: str, entry: dict, slot: int, **stats) -> dict:
    line = {
        "team": team, "player_id": entry["id"], "name": entry["name"],
        "lineup_slot": slot, "entry_order": 1, "is_substitute": False,
        "ab": 0, "r": 0, "h": 0, "doubles": 0, "triples": 0, "hr": 0,
        "rbi": 0, "bb": 0, "k": 0, "hbp": 0, "sb": 0, "cs": 0,
        "sac": 0, "sf": 0, "gidp": 0, "ibb": None,
    }
    line.update(stats)
    return line


def pit(team: str, entry: dict, order: int, **stats) -> dict:
    line = {
        "team": team, "player_id": entry["id"], "name": entry["name"],
        "appearance_order": order, "outs": 0, "h": 0, "r": 0, "er": 0,
        "bb": 0, "k": 0, "hr": 0, "hb": 0, "bf": 0,
        "entry_diff": None, "entry_inning": 1 if order == 1 else None,
    }
    line.update(stats)
    return line


def synthetic_game(rosters: dict, base: dict) -> dict:
    """Chicago 5, Montreal 3, Dawson batting for both clubs.

    Club totals tie in both directions: hits 10 and 10, strikeouts
    6 and 5, pitching HR equals opposing batting HR (1 and 1), HB
    equals opposing HBP (1 and 0), and derived PA equals opposing
    BF (Chicago 39, Montreal 35).
    """
    chc = lambda name: roster_entry(rosters, "CHC", name)  # noqa: E731
    mon = lambda name: roster_entry(rosters, "MON", name)  # noqa: E731
    game = copy.deepcopy(base)
    game["score"] = {"CHC": 5, "MON": 3}
    game["line"] = {"CHC": [2, 0, 1, 0, 0, 0, 0, 2, 0], "MON": [1, 0, 0, 0, 1, 0, 0, 0, 1]}
    game["winner"] = "CHC"
    game["team_errors"] = {"CHC": 0, "MON": 0}
    game["game_recap"] = "Synthetic dual appearance regression fixture. Not a played game."
    game["batting"] = [
        bat("CHC", chc("Ryne Sandberg"), 1, ab=5, r=1, h=2, doubles=1, rbi=1, k=1),
        bat("CHC", chc("Mark Grace"), 2, ab=4, h=1, bb=1, gidp=1),
        bat("CHC", chc("Ron Santo"), 3, ab=4, r=1, h=1, k=2),
        bat("CHC", chc("Sammy Sosa"), 4, ab=4, h=1, rbi=1, k=1, sf=1),
        bat("CHC", chc("Billy Williams"), 5, ab=3, r=1, h=1, bb=1, hbp=1),
        bat("CHC", chc("Ernie Banks"), 6, ab=4, k=1),
        bat("CHC", chc("Hack Wilson"), 7, ab=3, h=1, sac=1),
        bat("CHC", chc("Gabby Hartnett"), 8, ab=3, k=1),
        bat("CHC", chc("Andre Dawson"), 9, ab=4, r=2, h=3, doubles=1, hr=1, rbi=3),
        bat("MON", mon("Tim Raines"), 1, ab=4, r=1, h=1, bb=1, sb=1),
        bat("MON", mon("Jose Vidro"), 2, ab=4, h=1, rbi=1, k=1),
        bat("MON", mon("Larry Walker"), 3, ab=4, h=2, doubles=1),
        bat("MON", mon("Vladimir Guerrero"), 4, ab=4, r=1, h=2, rbi=1),
        bat("MON", mon("Andre Dawson"), 5, ab=4, r=1, h=2, hr=1, rbi=1, k=1),
        bat("MON", mon("Gary Carter"), 6, ab=4, h=1, k=1),
        bat("MON", mon("Ron Fairly"), 7, ab=3, sac=1),
        bat("MON", mon("Tim Wallach"), 8, ab=3, h=1),
        bat("MON", mon("Orlando Cabrera"), 9, ab=3, k=2),
    ]
    game["pitching"] = [
        pit("CHC", chc("Pete Alexander"), 1, outs=24, h=8, r=2, er=2, bb=1, k=4, hr=1, hb=0, bf=29),
        pit("CHC", chc("Bruce Sutter"), 2, outs=3, h=2, r=1, er=1, bb=0, k=1, hr=0, hb=0, bf=6),
        pit("MON", mon("Bryn Smith"), 1, outs=18, h=7, r=3, er=3, bb=1, k=4, hr=1, hb=1, bf=26),
        pit("MON", mon("Andy McGaffigan"), 2, outs=9, h=3, r=2, er=2, bb=1, k=2, hr=0, hb=0, bf=13),
    ]
    alexander = roster_entry(rosters, "CHC", "Pete Alexander")
    sutter = roster_entry(rosters, "CHC", "Bruce Sutter")
    smith = roster_entry(rosters, "MON", "Bryn Smith")
    game["wls"] = {
        "W": {"team": "CHC", "player_id": alexander["id"], "name": alexander["name"]},
        "L": {"team": "MON", "player_id": smith["id"], "name": smith["name"]},
        "S": {"team": "CHC", "player_id": sutter["id"], "name": sutter["name"]},
    }
    return game


def book_index(book: dict) -> int:
    return next(index for index, game in enumerate(book["games"]) if game["id"] == "R1-06-G4")


def load_details(data: dict) -> dict:
    probe = vr.Check()
    details = {}
    for game in data["games"]:
        detail = vr.detail_for(game, probe)
        assert detail is not None, game["id"]
        details[game["id"]] = detail
    return details


def main() -> int:
    data = json.loads((ROOT / "tournament_results.json").read_text(encoding="utf-8"))
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    base = next(game for game in data["games"] if game["id"] == "R1-06-G4")
    game = synthetic_game(rosters, base)

    # The full book, with the synthetic game standing in for the
    # played Game 4, reconciles with no failure and no unchecked
    # cross-check on the synthetic game.
    book = copy.deepcopy(data)
    for index, stored in enumerate(book["games"]):
        if stored["id"] == "R1-06-G4":
            book["games"][index] = game
    details = load_details(data)
    details["R1-06-G4"] = {
        "id": "R1-06-G4", "series_id": "R1-06", "game_in_series": 4,
        "rolls": [], "manager_log": None,
    }
    verdict = vr.Check()
    spoken = io.StringIO()
    with redirect_stdout(spoken):
        vr.reconcile(book, details, verdict)
    check("reconcile passes with dawsoan01 batting for both clubs",
          verdict.failures == [], "; ".join(verdict.failures[:4]))
    unchecked = [line for line in spoken.getvalue().splitlines()
                 if "R1-06-G4" in line and "unchecked" in line]
    check("synthetic game HR, HB, and derived PA cross-checks all run live",
          unchecked == [], "; ".join(unchecked))

    # Roster membership: the real book passes, the synthetic copy
    # passes, and Dawson's Chicago line relabeled as a St. Louis
    # line (a club whose roster he is not on) fails by name.
    for label, subject in (("real book", data), ("synthetic copy", book)):
        verdict = vr.Check()
        vr.check_roster_membership(subject, verdict)
        check(f"roster membership passes on the {label}", verdict.failures == [],
              "; ".join(verdict.failures[:4]))
    swapped = copy.deepcopy(book)
    for line in swapped["games"][book_index(swapped)]["batting"]:
        if line["team"] == "CHC" and line["player_id"] == "dawsoan01":
            line["team"] = "STL"
    verdict = vr.Check()
    vr.check_roster_membership(swapped, verdict)
    check("a shared player's line under the wrong club fails membership",
          any("dawsoan01" in failure for failure in verdict.failures),
          "; ".join(verdict.failures[:4]))

    # Accumulate and leaders on the synthetic game alone: two
    # buckets, two names entries, two leaders rows per board.
    small = {
        "teams": [team for team in data["teams"] if team["code"] in ("CHC", "MON")],
        "series": [],
        "games": [game],
    }
    names, batting, pitching = publish.accumulate(small)
    chc_dawson = batting.get(("CHC", "dawsoan01"), {})
    mon_dawson = batting.get(("MON", "dawsoan01"), {})
    check("accumulate keeps two Dawson batting buckets",
          len([key for key in batting if key[1] == "dawsoan01"]) == 2
          and chc_dawson.get("h") == 3 and chc_dawson.get("hr") == 1 and chc_dawson.get("rbi") == 3
          and mon_dawson.get("h") == 2 and mon_dawson.get("hr") == 1 and mon_dawson.get("rbi") == 1,
          f"CHC {dict(chc_dawson)} MON {dict(mon_dawson)}")
    check("accumulate names both Dawson lines",
          names.get(("CHC", "dawsoan01")) == "Andre Dawson"
          and names.get(("MON", "dawsoan01")) == "Andre Dawson")
    text = publish.leaders_markdown(small)
    check("leaders print Dawson once per club on the home run board",
          "| Andre Dawson | Chicago Cubs | 1 |" in text
          and "| Andre Dawson | Montreal Expos | 1 |" in text)
    check("leaders print Dawson once per club on the hits board",
          "| Andre Dawson | Chicago Cubs | 3 |" in text
          and "| Andre Dawson | Montreal Expos | 2 |" in text)

    failed = [label for label, ok in RESULTS if not ok]
    print(f"DUAL APPEARANCE: {len(RESULTS) - len(failed)}/{len(RESULTS)} checks pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
