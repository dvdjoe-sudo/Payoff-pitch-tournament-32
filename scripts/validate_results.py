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
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "tournament_results.json"
GAMES = ROOT / "games"

# Fingerprint of scores, lines, batting, pitching, decisions, rolls, and
# manager logs. Reset when R1-03 Games 3-7 were added from Joe's box scores.
# Games 1-2 of that series were checked against those box scores and left as stored.
# Locked games only (box score, decisions, rolls). The previous fingerprint also
# covered every series slot and the team won-lost lines; those move when a new
# game is imported. Team lines are still reconciled below. The old value was
# 7ab032794ae6f1b3c47184df4bf99ab8827c76ea50d9734bc8b10c118da41cf4.
# Reset 2026-10-25 under Joe's correction ruling: a bunt fielder's-choice
# play is scored a sacrifice (a plate appearance, not an at-bat), so ten
# recorded batting lines moved AB to SAC (R1-02: Kent G1, Murphy G2 and G3,
# Johnson G2; R1-03: Garciaparra G5; R1-04: Williams G1, Moreno G2,
# Trammell G4, G5, and G6). No score, result, or pitching line changed.
# The old value was
# d2b7b66dfb53fd57e5593a4207278a76cf8860fc662b9655d661ba6eca7aef45.
# Reset 2026-10-25 under Joe's ruling that a starter removed before his
# first plate appearance is carried on a zero line: twelve all-zero
# starter rows were inserted ahead of the men who batted in their slots
# (R1-01 G3 Realmuto; R1-03 Diaz in G1, G2, G3, G4, G6, G7, Crawford,
# Pena, Lowe, and Kiermaier in G5; R1-04 G3 Freehan). No score, result,
# or existing line changed. The old value was
# 7b12e577dbfe542585fb0fb1dd4bce53b9fd5515b5a894940685968e28182f4d.
# PDF-based recovery 2026-10-26: restored original R1-03 G3-G7 FAC histories (128, 164, 183, 137, 159 entries) from the owner-provided 101-page record. Only per-game detail rolls and the locked fingerprint changed; official game summaries and manager_log stay unchanged.
FINGERPRINT = "70d18c865b46f9fb73c9cae8b124c6e4077b930f21a60ba67f7b87b5799a44dc"
# Hash of R1-01, R1-02, and R1-03 only. Later series may gain games.
# The full series-array hash was ef0dbf3849d62473ee2884ced2cb575e6bf66fd4c171b9d6ed95dc2eb7ac8613.
FROZEN_SERIES = ("R1-01", "R1-02", "R1-03")
FROZEN_SERIES_HASH = "7839af494aa7882786c7d5b9268e8f9826bdd8903b49c7d27f1d151ca2eb4df2"
FORMAT_HASH = "f3dda1d7ca63d1ce87e1f751e6ef7e27646cfd6e9d8df420c178db03d0475363"
LOCKED_GAME_IDS = (
    "R1-01-G1", "R1-01-G2", "R1-01-G3", "R1-01-G4",
    "R1-02-G1", "R1-02-G2", "R1-02-G3", "R1-02-G4", "R1-02-G5",
    "R1-03-G1", "R1-03-G2", "R1-03-G3", "R1-03-G4", "R1-03-G5", "R1-03-G6", "R1-03-G7",
)

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

EXPECTED_TOTALS = {"H": 246, "HR": 49, "RBI": 148, "K": 301, "ER": 148, "OUTS": 832}
ROLL_COUNTS = {"R1-01-G1": 72, "R1-02-G1": 161, "R1-03-G1": 148, "R1-03-G2": 135, "R1-03-G3": 128, "R1-03-G4": 164, "R1-03-G5": 183, "R1-03-G6": 137, "R1-03-G7": 159}
DATED = {"R1-02": "2026-10-24", "R1-03": "2026-10-23"}
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
    by_id = {game["id"]: game for game in data["games"]}
    games = []
    for game_id in LOCKED_GAME_IDS:
        game = by_id.get(game_id)
        if game is None:
            continue
        detail = details[game["id"]]
        games.append({
            "id": game["id"],
            "score": game["score"],
            "winner": game["winner"],
            "home": game["home"],
            "away": game["away"],
            "seed": game["rng_seed"] if "rng_seed" in game else game.get("seed"),
            "line": game["line"],
            "batting": [{key: line[key] for key in BATTING_FIELDS} for line in game["batting"]],
            "pitching": [{key: line.get(key) for key in PITCHING_FIELDS} for line in game["pitching"]],
            "wls": game["wls"],
            "n_rolls": len(detail["rolls"]),
            "rolls": detail["rolls"],
            "manager_log": detail.get("manager_log", None),
            "team_errors": game["team_errors"],
        })
    return digest({"games": games})


def reconcile(data: dict, details: dict[str, dict], check: Check) -> None:
    check.expect(data.get("schema_version") == 1, "schema_version is 1")
    check.expect(data.get("version") == 1, "archive version left at 1")
    check.expect(len(data["teams"]) == 32, "32 teams")
    check.expect(len(data["series"]) == 63, "63 series slots")
    ids = [game["id"] for game in data["games"]]
    check.expect(ids[:len(LOCKED_GAME_IDS)] == list(LOCKED_GAME_IDS), "locked games stay first, in order")
    check.expect(len(ids) == len(set(ids)), "game ids are unique")
    frozen = [item for item in data["series"] if item["id"] in FROZEN_SERIES]
    check.expect([item["id"] for item in frozen] == list(FROZEN_SERIES), "frozen series stay in order")
    check.expect(digest(frozen) == FROZEN_SERIES_HASH, "frozen series objects unchanged")
    check.expect(digest(data["format"]) == FORMAT_HASH, "format object unchanged")
    check.expect(fingerprint(data, details) == FINGERPRINT, "locked game stat fingerprint")

    totals = {key: 0 for key in EXPECTED_TOTALS}
    game_wins: dict[str, int] = {}
    game_losses: dict[str, int] = {}
    for game in data["games"]:
        check.expect("rolls" not in game and "manager_log" not in game and "seed" not in game, f"{game['id']} summary still holds detail or the old seed key")
        check.expect(game.get("detail") == f"games/{game['id']}.json", f"{game['id']} detail path")
        detail = details[game["id"]]
        check.expect(detail["id"] == game["id"] and detail["series_id"] == game["series_id"], f"{game['id']} detail identity")
        check.expect(detail["game_in_series"] == game["game_in_series"], f"{game['id']} detail game number")
        if game["id"] in set(LOCKED_GAME_IDS):
            if game["series_id"] in DATED:
                check.expect(game.get("date") == DATED[game["series_id"]], f"{game['id']} date")
            else:
                check.expect(game.get("date") is None, f"{game['id']} date should be null")
        else:
            dated = game.get("date")
            check.expect(dated is None or bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", dated or "")), f"{game['id']} date")
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
        if game["id"] in set(LOCKED_GAME_IDS):
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
    check.expect(data["games"][0].get("rng_seed", data["games"][0].get("seed")) == 1101, "R1-01-G1 rng seed")
    check.expect(data["games"][4].get("rng_seed", data["games"][4].get("seed")) == 20261101, "R1-02-G1 rng seed")
    check.expect(data["games"][9].get("rng_seed", data["games"][9].get("seed")) == 20261201, "R1-03-G1 rng seed")

    series_wins: dict[str, int] = {}
    series_losses: dict[str, int] = {}
    by_id = {game["id"]: game for game in data["games"]}
    for series in data["series"]:
        from collections import Counter
        if series["status"] not in {"complete", "in-progress"}:
            continue
        won = Counter(by_id[game_id]["winner"] for game_id in series["games"])
        recorded = {code: won.get(code, 0) for code in series["wins"]}
        check.expect(recorded == series["wins"], f"{series['id']} wins {recorded} vs {series['wins']}")
        if series["status"] == "in-progress":
            check.expect(series["winner"] is None and series["loser"] is None, f"{series['id']} stays undecided")
            check.expect(all(value < 4 for value in series["wins"].values()), f"{series['id']} has not reached 4")
            continue
        check.expect(series["wins"][series["winner"]] == 4, f"{series['id']} winner reached 4")
        series_wins[series["winner"]] = series_wins.get(series["winner"], 0) + 1
        series_losses[series["loser"]] = series_losses.get(series["loser"], 0) + 1

    for team in data["teams"]:
        code = team["code"]
        check.expect(team["game_wins"] == game_wins.get(code, 0), f"{code} game wins")
        check.expect(team["game_losses"] == game_losses.get(code, 0), f"{code} game losses")
        check.expect(team["series_wins"] == series_wins.get(code, 0), f"{code} series wins")
        check.expect(team["series_losses"] == series_losses.get(code, 0), f"{code} series losses")
        check.expect(team.get("losses") == team["series_losses"], f"{code} losses field")
        if team["eliminated"] or team["series_losses"] >= 2:
            expected = "eliminated"
        elif team["series_losses"] == 1:
            expected = "losers"
        else:
            expected = "winners"
        check.expect(team.get("bracket") == expected, f"{code} bracket")
        check.expect("seed" in team, f"{code} still has its tournament seed")


def data_game_svg(publish) -> tuple[str, str]:
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    game = next(item for item in data["games"] if item["id"] == "R1-03-G1")
    written = (ROOT / "graphics" / "games" / "R1-03-G1.svg").read_text(encoding="utf-8")
    return written, publish.game_svg(game)


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
    check.expect("4-3" in readme and "Pedro" in readme and "Complete" in readme, "readme records R1-03")
    check.expect("4-3" in bracket and "Complete" in bracket, "bracket records R1-03")
    check.expect("MODELS.md" in readme and "feed/games.xml" in readme, "readme links the models and the feed")
    check.expect("muse.ai" not in readme and "muse.ai" not in (ROOT / "index.html").read_text(encoding="utf-8"), "walkthrough video link removed")
    check.expect("in-progress" in (ROOT / "SCHEMA.md").read_text(encoding="utf-8"), "schema names in-progress")
    for name in (
        "BRACKET.md", "TOURNAMENT_RULES.md", "TOURNAMENT_SEEDS.md", "ROSTERS.md",
        "LEADERS.md", "CHANGELOG.md", "SCHEMA.md", "LICENSE", "index.html",
    ):
        check.expect(name in readme, f"readme links {name}")
    check.expect("Joe's picks" in readme or "Joe's pins" in readme, "readme names the six pins")
    for club in ("Philadelphia Athletics", "Oakland Athletics", "Montreal Expos", "Washington Nationals", "Miami Marlins", "New York Yankees"):
        check.expect(club in readme, f"readme names {club}")
    # Rules-content checks replaced 2026-10-25 under Joe's ruling of that
    # date ("Remove all APBA items except Yankees series"): the old checks
    # required the rules to keep the APBA boards (Version 23), the card-41
    # injury check, the SCBL Rule 34 steal gate, and the duplicated
    # 3-inning reliever wording. The rewritten rules are a Payoff Pitch
    # document; the checks below pin its standing content instead.
    check.expect("FAC deck" in rules, "rules state FAC deck mode")
    check.expect("house hard rule" in rules, "rules state the house hard rule")
    check.expect("closer branch" in rules, "rules state the closer branch")
    check.expect("R1-01" in rules and "played under APBA" in rules, "rules keep the R1-01 provenance")
    check.expect("Open questions" in rules, "rules keep the open questions")
    check.expect("TOURNAMENT_SEEDS.md" in rules, "rules point at the seed file")
    check.expect("Seeds 1-29 are unchanged" not in rules and "SUPERSEDED" not in seeds, "stale seed tables removed from the current docs")
    check.expect(all(year in changelog for year in ("2026-10-22", "2026-10-23", "2026-10-24")), "changelog has the ruling dates")
    leaders = load_mod(ROOT / "scripts" / "build_leaders.py", "build_leaders")
    rosters = load_mod(ROOT / "scripts" / "build_rosters.py", "build_rosters")
    check.expect((ROOT / "LEADERS.md").read_text(encoding="utf-8") == leaders.build(), "LEADERS.md matches the script")
    check.expect((ROOT / "ROSTERS.md").read_text(encoding="utf-8") == rosters.build(), "ROSTERS.md matches the script")
    publish = load_mod(ROOT / "scripts" / "publish.py", "publish_docs")
    check.expect((ROOT / "TEAM_STATS.md").read_text(encoding="utf-8") == publish.team_stats_markdown(), "TEAM_STATS.md matches the script")
    check.expect((ROOT / "box_scores" / "R1-03-G1.md").read_text(encoding="utf-8") == publish.box_markdown("R1-03-G1"), "R1-03-G1 box score matches the script")
    check.expect((ROOT / "AWARDS.md").read_text(encoding="utf-8") == publish.awards_markdown(), "AWARDS.md matches the script")
    check.expect((ROOT / "RECORDS.md").read_text(encoding="utf-8") == publish.records_markdown(), "RECORDS.md matches the script")
    check.expect("Pedro Martinez" in (ROOT / "RECORDS.md").read_text(encoding="utf-8"), "records include the no-hitter")
    check.expect((ROOT / "feed" / "tournament.json").read_text(encoding="utf-8") == publish.feed_json_text(), "JSON feed matches the script")
    check.expect((ROOT / "feed" / "games.xml").read_text(encoding="utf-8") == publish.rss_text(), "RSS feed matches the script")
    sample = data_game_svg(publish)
    check.expect(sample[0] == sample[1], "score graphic matches the script")
    check.expect("LEADERS.md" in (ROOT / "LEADERBOARDS.md").read_text(encoding="utf-8"), "old leaderboard file points at the one board")
    leaders_text = (ROOT / "LEADERS.md").read_text(encoding="utf-8")
    check.expect("| Roger Clemens | Boston Red Sox | 1.12 |" in leaders_text, "Clemens ERA is 1.12")
    check.expect("| Carl Hubbell | San Francisco Giants | 1.12 |" in leaders_text, "Hubbell ERA is 1.12")
    check.expect("TODO for Joe" in (ROOT / "ROSTERS.md").read_text(encoding="utf-8"), "roster stubs")
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "js" / "bracket.js").read_text(encoding="utf-8")
    check.expect("css/styles.css" in html and "js/bracket.js" in html, "viewer assets")
    check.expect("function convertedClubs()" in script and "var clubs = convertedClubs()" in script and
                 "var converted = convertedClubs()" in script,
                 "roster and about pages calculate converted-club counts from the live roster data")
    check.expect("exist for 11 clubs" not in script and "exist for eleven clubs" not in script and
                 "Converted Payoff Pitch cards exist for eleven clubs" not in readme,
                 "converted-club counts are not hardcoded in the website or README")
    check.expect("tournament_results.json" in script, "viewer reads the results file")
    check.expect("detail" in script, "viewer follows detail links")
    css = (ROOT / "css" / "styles.css").read_text(encoding="utf-8")
    check.expect((ROOT / "css" / "styles.css").exists() and (ROOT / ".nojekyll").exists(), "pages files exist")
    check.expect("@media (max-width: 720px)" in css, "mobile layout")
    check.expect('data-theme="dark"' in css, "dark theme")
    check.expect("theme-toggle" in html and "next-up" in html and "feed/games.xml" in html, "viewer chrome")
    check.expect("0.55" in script and "1.35" in script, "viewer carries the display-model constants")
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    check.expect("validate_results.py" in workflow and "deploy-pages" in workflow, "pages workflow validates and deploys")
    models = (ROOT / "MODELS.md").read_text(encoding="utf-8")
    check.expect("0.55" in models and "1.35" in models and "5×SV" in models, "models document the formulas")

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


def detail_for(game: dict, check: Check):
    """Load rolls from games/<id>.json, or from the game object when it is still inline."""
    if game.get("detail"):
        path = ROOT / game["detail"]
        check.expect(path.is_file(), f"missing {game['detail']}")
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    if "rolls" not in game:
        check.expect(False, f"{game.get('id')} has neither detail nor rolls")
        return None
    return {
        "id": game["id"],
        "series_id": game["series_id"],
        "game_in_series": game["game_in_series"],
        "rolls": game["rolls"],
        "manager_log": game.get("manager_log"),
    }



def check_pha_roster_alignment(check: Check) -> None:
    """Owner-approved card roster, without inventing Valo's frozen conversion."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["PHA"]
    pha = rosters["PHA"]["players"]
    count = lambda group: sum(p["group"] == group for p in pha)
    check.expect(len(pha) == 26 and len({p["id"] for p in pha}) == 26, "PHA exactly 26 distinct players")
    check.expect((count("lineup"), count("bench"), count("rotation"), count("bullpen")) == (9, 7, 5, 5),
                 "PHA owner-approved 9/7/5/5 slot distribution")
    by_id = {p["id"]: p for p in pha}
    for pid, group, slot, pos in (
        ("fainfe01", "lineup", 9, "DH"),
        ("bishoma01", "bench", 6, "2B"),
        ("valoel01", "bench", 7, "OF"),
    ):
        spot = by_id.get(pid, {})
        check.expect((spot.get("group"), spot.get("slot"), spot.get("pos")) == (group, slot, pos),
                     "PHA approved slot " + pid)
        c = cards.get("PHA|" + pid, {})
        check.expect(bool(c) and any(s.get("group") == group and s.get("slot") == slot for s in c.get("spots", [])),
                     "PHA card spot matches roster for " + pid)
    check.expect("earnsge01" not in by_id and "PHA|earnsge01" not in cards,
                 "Earnshaw absent from PHA owner-approved cards")
    check.expect({k.split("|", 1)[1] for k in cards if k.startswith("PHA|")} == set(by_id),
                 "PHA roster and card catalog have identical player ids")
    check.expect(any("Elmer Valo" in s for s in announced["bench"]) and
                 any("Ferris Fain DH" in s for s in announced["lineup"]) and
                 any("Max Bishop" in s for s in announced["bench"]),
                 "PHA owner-announced card amendments remain present")
    valo = cards.get("PHA|valoel01", {})
    check.expect(bool(valo.get("card_bat")) or bool(valo.get("conversion_status")),
                 "Valo has genuine converted card or explicit nonplayable status")


def check_card_partitions(check: Check) -> None:
    """Every hitter hand resolves 01-99 once, and every 2d6 chart is complete.

    The resolved reading gives a result band the face when the shared
    out table also lists it, and requires the out table to cover every
    hole. Face 00 is outside the partition. A pending card with no
    sections is skipped.
    """
    path = ROOT / "engines" / "hitter-v0.5" / "partition.py"
    spec = importlib.util.spec_from_file_location("card_partition", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    failures = []
    checked = 0
    for key, card in cards.items():
        bat = card.get("card_bat") or {}
        if bat.get("sections"):
            checked += 1
            for problem in module.validate_hitter_card(bat, exact=False):
                failures.append("%s: %s" % (key, problem))
        table = (card.get("card_pit") or {}).get("table_2d6")
        if table:
            checked += 1
            for problem in module.validate_pitcher_table(table):
                failures.append("%s: %s" % (key, problem))
    check.expect(checked > 0, "card partition check found no cards")
    if failures:
        preview = "; ".join(failures[:6])
        check.expect(False, "card partitions failed %d: %s" % (len(failures), preview))
    else:
        check.expect(True, "card partitions")


def main() -> int:
    check = Check()
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    details = {}
    for game in data["games"]:
        detail = detail_for(game, check)
        if detail is not None:
            details[game["id"]] = detail
    if len(details) == len(data["games"]):
        reconcile(data, details, check)
    documents(check)
    check_pha_roster_alignment(check)
    check_card_partitions(check)
    return check.done()


if __name__ == "__main__":
    sys.exit(main())
