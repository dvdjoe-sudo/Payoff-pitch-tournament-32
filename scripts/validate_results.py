#!/usr/bin/env python3
"""Reconcile the split archive with the stat lines recorded before the split.

Exits 0 when scores, series, team records, and the pre-split fingerprint
still match, and when the docs agree on the played series. Exits 1
otherwise.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "tournament_results.json"
GAMES = ROOT / "games"

# Fingerprint of scores, lines, batting, pitching, decisions, rolls, and
# manager logs, taken from tournament_results.json before rolls were split
# out and before the per-game RNG field was renamed.
FINGERPRINT = "7c5c6ca912ef46b1c734e09381aad73db9271a2023b5eb9601f8705281aab189"
SERIES_HASH = "a6d65b8759e4ec89a76c3a9079d726ddb88a3e59c212dd3cfd2b731c44babf45"
FORMAT_HASH = "f3dda1d7ca63d1ce87e1f751e6ef7e27646cfd6e9d8df420c178db03d0475363"

BATTING_FIELDS = (
    "team", "player_id", "name", "lineup_slot", "entry_order", "is_substitute",
    "ab", "r", "h", "rbi", "bb", "k", "hbp", "sb", "cs", "sac", "sf", "gidp",
    "ibb", "doubles", "triples", "hr",
)
PITCHING_FIELDS = (
    "team", "player_id", "name", "appearance_order", "outs", "h", "r", "er",
    "bb", "k", "bf", "hb", "hr",
)
TEAM_FIELDS = (
    "seed", "code", "name", "index", "game_wins", "game_losses", "series_wins",
    "series_losses", "eliminated", "champion",
)

EXPECTED_TOTALS = {"H": 158, "HR": 35, "RBI": 105, "K": 165, "ER": 104, "OUTS": 468}
ROLL_COUNTS = {"R1-01-G1": 72, "R1-02-G1": 161}
THREE_INNINGS = (
    "A reliever is lifted when he reaches 3 innings pitched in one appearance, "
    "unless he is the last available arm. The last available arm stays in and "
    "pitches under the fatigue rules, including after a run hook or a grade "
    "hook is armed, because a starter cannot relieve and no other reliever remains."
)
FORBIDDEN = (
    "superseded_r1_02",
    "tournament_results.py",
    "verify_reseed.py",
    "migrate_reseed.py",
    "index_calibration",
    "BOARDS_V23",
    "boards_v23.json",
    "MASTER_SYMBOLS",
    "BUILD_REPORT.md",
    "SERIES_SO_FAR",
    "APBA_CARD_BUILDER_RULES",
    "POOL_GRADES_PREVIEW",
    "tournament app",
    "conversion_work/",
)
VIDEO = "https://muse.ai/s/payoff-pitch-top-32-tournament-xck6hxnxfvxsxmfi/CveOB6LiiLsVcK7Go4H5MqGh_DyskYPHOntiaN4jpvs"


def digest(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def load_mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Check:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def expect(self, condition: bool, message: str) -> None:
        if not condition:
            self.failures.append(message)

    def done(self) -> int:
        if self.failures:
            print(f"{len(self.failures)} check(s) failed:")
            for message in self.failures:
                print(f"  - {message}")
            return 1
        print("all checks passed")
        return 0


def fingerprint(data: dict, details: dict[str, dict]) -> str:
    games = []
    for game in data["games"]:
        detail = details[game["id"]]
        games.append({
            "id": game["id"],
            "score": game["score"],
            "winner": game["winner"],
            "home": game["home"],
            "away": game["away"],
            "seed": game["rng_seed"],
            "line": game["line"],
            "batting": [{key: line[key] for key in BATTING_FIELDS} for line in game["batting"]],
            "pitching": [{key: line.get(key) for key in PITCHING_FIELDS} for line in game["pitching"]],
            "wls": game["wls"],
            "n_rolls": len(detail["rolls"]),
            "rolls": detail["rolls"],
            "manager_log": detail.get("manager_log", None),
            "team_errors": game["team_errors"],
        })
    teams = [{key: team[key] for key in TEAM_FIELDS} for team in data["teams"]]
    series = [{
        key: item[key] for key in (
            "id", "status", "winner", "loser", "wins", "games", "team_a", "team_b", "seed_a", "seed_b",
        )
    } for item in data["series"]]
    return digest({"games": games, "teams": teams, "series": series})


def reconcile(data: dict, details: dict[str, dict], check: Check) -> None:
    check.expect(data.get("schema_version") == 1, "schema_version is 1")
    check.expect(data.get("version") == 1, "archive version left at 1")
    check.expect(len(data["teams"]) == 32, "32 teams")
    check.expect(len(data["series"]) == 63, "63 series slots")
    check.expect(len(data["games"]) == 9, "9 games")
    check.expect(digest(data["series"]) == SERIES_HASH, "series objects unchanged")
    check.expect(digest(data["format"]) == FORMAT_HASH, "format object unchanged")
    check.expect(fingerprint(data, details) == FINGERPRINT, "pre-split stat fingerprint")

    totals = {key: 0 for key in EXPECTED_TOTALS}
    game_wins: dict[str, int] = {}
    game_losses: dict[str, int] = {}
    for game in data["games"]:
        check.expect("rolls" not in game and "manager_log" not in game and "seed" not in game, f"{game['id']} summary still holds detail or the old seed key")
        check.expect(game.get("detail") == f"games/{game['id']}.json", f"{game['id']} detail path")
        detail = details[game["id"]]
        check.expect(detail["id"] == game["id"] and detail["series_id"] == game["series_id"], f"{game['id']} detail identity")
        check.expect(detail["game_in_series"] == game["game_in_series"], f"{game['id']} detail game number")
        if game["series_id"] == "R1-02":
            check.expect(game["date"] == "2026-10-24", f"{game['id']} date")
        else:
            check.expect(game["date"] is None, f"{game['id']} date should be null")
        for code in (game["home"], game["away"]):
            batting_runs = sum(line["r"] or 0 for line in game["batting"] if line["team"] == code)
            check.expect(batting_runs == game["score"][code], f"{game['id']} {code} batting runs")
            check.expect(sum(game["line"][code]) == game["score"][code], f"{game['id']} {code} line score")
            opponent = game["away"] if code == game["home"] else game["home"]
            allowed = sum(line["r"] or 0 for line in game["pitching"] if line["team"] == code)
            check.expect(allowed == game["score"][opponent], f"{game['id']} {code} runs allowed")
        hits_b = sum(line["h"] or 0 for line in game["batting"])
        hits_p = sum(line["h"] or 0 for line in game["pitching"])
        strike_b = sum(line["k"] or 0 for line in game["batting"])
        strike_p = sum(line["k"] or 0 for line in game["pitching"])
        check.expect(hits_b == hits_p, f"{game['id']} hits")
        check.expect(strike_b == strike_p, f"{game['id']} strikeouts")
        for line in game["batting"]:
            totals["H"] += line["h"] or 0
            totals["HR"] += line["hr"] or 0
            totals["RBI"] += line["rbi"] or 0
            totals["K"] += line["k"] or 0
        for line in game["pitching"]:
            totals["ER"] += line["er"] or 0
            totals["OUTS"] += line["outs"] or 0
        winner = game["winner"]
        loser = game["away"] if winner == game["home"] else game["home"]
        game_wins[winner] = game_wins.get(winner, 0) + 1
        game_losses[loser] = game_losses.get(loser, 0) + 1

    check.expect(totals == EXPECTED_TOTALS, f"counting totals {totals}")
    for game_id, count in ROLL_COUNTS.items():
        check.expect(len(details[game_id]["rolls"]) == count, f"{game_id} roll count")
    check.expect(details["R1-01-G2"]["manager_log"] is None, "R1-01-G2 manager log stays null")
    check.expect(data["games"][0]["rng_seed"] == 1101, "R1-01-G1 rng seed")
    check.expect(data["games"][4]["rng_seed"] == 20261101, "R1-02-G1 rng seed")

    series_wins: dict[str, int] = {}
    series_losses: dict[str, int] = {}
    by_id = {game["id"]: game for game in data["games"]}
    for series in data["series"]:
        if series["status"] != "complete":
            continue
        from collections import Counter
        won = Counter(by_id[game_id]["winner"] for game_id in series["games"])
        recorded = {code: won.get(code, 0) for code in series["wins"]}
        check.expect(recorded == series["wins"], f"{series['id']} wins {recorded} vs {series['wins']}")
        check.expect(series["wins"][series["winner"]] == 4, f"{series['id']} winner reached 4")
        series_wins[series["winner"]] = series_wins.get(series["winner"], 0) + 1
        series_losses[series["loser"]] = series_losses.get(series["loser"], 0) + 1

    for team in data["teams"]:
        code = team["code"]
        check.expect(team["game_wins"] == game_wins.get(code, 0), f"{code} game wins")
        check.expect(team["game_losses"] == game_losses.get(code, 0), f"{code} game losses")
        check.expect(team["series_wins"] == series_wins.get(code, 0), f"{code} series wins")
        check.expect(team["series_losses"] == series_losses.get(code, 0), f"{code} series losses")
        check.expect(team["losses"] == team["series_losses"], f"{code} losses field")
        if team["eliminated"] or team["series_losses"] >= 2:
            expected = "eliminated"
        elif team["series_losses"] == 1:
            expected = "losers"
        else:
            expected = "winners"
        check.expect(team["bracket"] == expected, f"{code} bracket")
        check.expect("seed" in team, f"{code} still has its tournament seed")


def documents(check: Check) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    bracket = (ROOT / "BRACKET.md").read_text(encoding="utf-8")
    rules = (ROOT / "TOURNAMENT_RULES.md").read_text(encoding="utf-8")
    seeds = (ROOT / "TOURNAMENT_SEEDS.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    check.expect(bracket.startswith("# Payoff Pitch Tournament 32"), "bracket title")
    check.expect("Giants 4-1" in bracket and "R1-02" in bracket, "bracket records R1-02")
    check.expect("only R1-01" not in bracket and "Only R1-01" not in bracket, "bracket no longer says only R1-01")
    check.expect("Yankees 4-0" in readme and "Giants 4-1" in readme, "readme results")
    check.expect(VIDEO in readme, "readme video")
    for name in (
        "BRACKET.md", "TOURNAMENT_RULES.md", "TOURNAMENT_SEEDS.md", "ROSTERS.md",
        "LEADERS.md", "CHANGELOG.md", "SCHEMA.md", "LICENSE", "index.html",
    ):
        check.expect(name in readme, f"readme links {name}")
    check.expect("Joe's picks" in readme or "Joe's pins" in readme, "readme names the six pins")
    for club in ("Philadelphia Athletics", "Oakland Athletics", "Montreal Expos", "Washington Nationals", "Miami Marlins", "New York Yankees"):
        check.expect(club in readme, f"readme names {club}")
    check.expect(rules.count(THREE_INNINGS) == 2, "the 3-inning rule is worded the same in both sections")
    check.expect("TOURNAMENT_SEEDS.md" in rules, "rules point at the seed file")
    check.expect("Seeds 1-29 are unchanged" not in rules and "SUPERSEDED" not in seeds, "stale seed tables removed from the current docs")
    for marker in ("Version 23", "card-41", "Rule 34", "TODO for Joe"):
        check.expect(marker in rules, f"rules keep {marker}")
    check.expect(all(year in changelog for year in ("2026-10-22", "2026-10-23", "2026-10-24")), "changelog has the ruling dates")
    leaders = load_mod(ROOT / "scripts" / "build_leaders.py", "build_leaders")
    rosters = load_mod(ROOT / "scripts" / "build_rosters.py", "build_rosters")
    check.expect((ROOT / "LEADERS.md").read_text(encoding="utf-8") == leaders.build(), "LEADERS.md matches the script")
    check.expect((ROOT / "ROSTERS.md").read_text(encoding="utf-8") == rosters.build(), "ROSTERS.md matches the script")
    check.expect("1.13" in (ROOT / "LEADERS.md").read_text(encoding="utf-8"), "Hubbell ERA rounding")
    check.expect("TODO for Joe" in (ROOT / "ROSTERS.md").read_text(encoding="utf-8"), "roster stubs")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "js" / "bracket.js").read_text(encoding="utf-8")
    check.expect("css/styles.css" in html and "js/bracket.js" in html, "viewer assets")
    check.expect("tournament_results.json" in script and "games/" not in script or "detail" in script, "viewer reads the JSON")
    check.expect((ROOT / "css" / "styles.css").exists() and (ROOT / ".nojekyll").exists(), "pages files exist")
    check.expect("@media (max-width: 720px)" in (ROOT / "css" / "styles.css").read_text(encoding="utf-8"), "mobile layout")

    skip = {ROOT / "scripts" / "validate_results.py"}
    for path in ROOT.rglob("*"):
        if path.suffix not in {".md", ".html", ".js", ".css", ".py"} and path.name != "LICENSE":
            continue
        if path in skip or ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN:
            if token in text:
                check.failures.append(f"{path.relative_to(ROOT)} still mentions {token}")


def main() -> int:
    check = Check()
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    details = {}
    for game in data["games"]:
        path = ROOT / game["detail"]
        check.expect(path.is_file(), f"missing {game['detail']}")
        if path.is_file():
            details[game["id"]] = json.loads(path.read_text(encoding="utf-8"))
    if len(details) == len(data["games"]):
        reconcile(data, details, check)
    documents(check)
    return check.done()


if __name__ == "__main__":
    sys.exit(main())
