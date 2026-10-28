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
# Reset 2026-10-27 under Joe's correction ruling: a sacrifice fly is
# scored a plate appearance, not an at-bat (extending his 2026-10-25
# sacrifice ruling), so four locked batting lines moved AB to SF
# (R1-02: Ott G2, Bonds G4, Williams G5; R1-03: Foxx G2). The same
# correction moved four more lines in the unlocked series (R1-04:
# Perdomo G3; R1-05: Walker G1, Medwick G4, Arenado G4). No score,
# result, or pitching line changed. The old value was
# 70d18c865b46f9fb73c9cae8b124c6e4077b930f21a60ba67f7b87b5799a44dc.
FINGERPRINT = "5cf9eb317919fe731906b59dffbc3745cf50171a5891cb7cb8b35a5a85dda0ae"
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
    """Approved PHA Foxx/Fain defensive swap and Shantz for Barry 9/6/5/6."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["PHA"]
    players = rosters["PHA"]["players"]
    ids = [p["id"] for p in players]
    check.expect(len(players) == len(set(ids)) == 26,
                 "PHA approved roster has 26 distinct active people")
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "PHA approved 9/6/5/6 slot distribution")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "PHA lineup, bench, rotation and bullpen slots are sequential")
    index = {p["id"]: p for p in players}
    for pid, group, slot, pos in (
        ("foxxji01", "lineup", 4, "DH"),
        ("fainfe01", "lineup", 9, "1B"),
        ("bishoma01", "bench", 5, "2B"),
        ("valoel01", "bench", 6, "OF"),
        ("shantbo01", "bullpen", 6, "RP"),
    ):
        p = index.get(pid, {})
        check.expect((p.get("group"), p.get("slot"), p.get("pos")) == (group, slot, pos),
                     "PHA active player position/slot approved: " + pid)
    check.expect("barryja01" not in index,
                 "Jack Barry no longer occupies an active bench slot")
    check.expect([p["id"] for p in players if p["group"] == "bullpen"]
                 == ["berryjo03", "chrisru01", "walberu01",
                     "rommeed01", "quinnja01", "shantbo01"],
                 "PHA retains five pitchers and adds Shantz as LH swing/long relief")
    check.expect("PHA|barryja01" in cards,
                 "Jack Barry original converted card preserved as historical")
    check.expect("PHA|foxxji01" in cards and "PHA|fainfe01" in cards
                 and "PHA|bishoma01" in cards and "PHA|valoel01" in cards,
                 "All prior first-base, DH and reserve player card bodies preserved")
    check.expect("earnsge01" not in index and "PHA|earnsge01" not in cards,
                 "Older Earnshaw exclusion remains intact")
    # The static card catalog preserves original player cards and historical
    # spot metadata. Active assignments are authoritative in data/rosters.json
    # and in announced_rosters.json, including before Shantz is converted.
    available_ids = {key.split("|", 1)[1] for key in cards if key.startswith("PHA|")}
    check.expect((set(ids) - {"shantbo01"}).issubset(available_ids),
                 "Existing PHA active players still retain their original cards")
    check.expect("PHA|shantbo01" not in cards
                 or bool(cards["PHA|shantbo01"].get("card_pit"))
                 or bool(cards["PHA|shantbo01"].get("conversion_status")),
                 "Shantz is either authentically converted or explicitly pending")
    peaks = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["PHA"]
    shantz_peak = peaks.get("LHS/LONG Bobby Shantz 1949-1954 (Philadelphia only)") or {}
    check.expect(shantz_peak.get("lahman_id") == "shantbo01"
                 and shantz_peak.get("years") == [1949, 1950, 1951, 1952, 1953]
                 and shantz_peak.get("status") == "ok"
                 and "not a relief-only projection" in (shantz_peak.get("text") or ""),
                 "Shantz Peak 162 uses Philadelphia-only franchise window with starter caveat")
    check.expect("IF2 Jack Barry 8" not in peaks
                 and "4 Jimmie Foxx DH 11" in peaks
                 and "9 Ferris Fain 1B L 6" in peaks,
                 "PHA Peak 162 agrees with Foxx/Fain position switch and Barry removal")
    check.expect(any("Ferris Fain 1B" in row for row in announced["lineup"])
                 and any("Jimmie Foxx DH" in row for row in announced["lineup"])
                 and len(announced["bench"]) == 6
                 and len(announced["bullpen"]) == 6
                 and any("Bobby Shantz" in row for row in announced["bullpen"])
                 and not any("Jack Barry" in row for row in announced["bench"]),
                 "PHA published/owner lineup and approved active 9/6/5/6 agree")
    valo = cards.get("PHA|valoel01", {})
    check.expect(bool(valo.get("card_bat")) or bool(valo.get("conversion_status")),
                 "Valo remains authentically converted or pending")
    published = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Jimmie Foxx (`foxxji01`) is now the **designated hitter**" in published
                 and "Bobby Shantz (`shantbo01`)" in published,
                 "Approved PHA positions and Shantz are documented in published roster")
    builder = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_philadelphia_athletics_2026_roster_amendment(cards, rosters)" in builder,
                 "Full converted-card rebuild preserves the approved PHA active 26")



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


def check_padres_roster_amendment(check: Check) -> None:
    """The active 26 follows Joe's approved 6/6 Padres amendment."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["SD"]
    players = rosters["SD"]["players"]
    ids = {p["id"] for p in players}
    check.expect(len(players) == len(ids) == 26, "Padres 26 distinct active players")
    counts = {g: sum(p["group"] == g for p in players)
              for g in ("lineup", "bench", "rotation", "bullpen")}
    check.expect(counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Padres lineup/bench/rotation/bullpen is 9/6/5/6")
    giles = [p for p in players if p["id"] == "gilesbr02"]
    check.expect(len(giles) == 1 and giles[0]["group"] == "bench" and
                 giles[0]["slot"] == 6 and giles[0]["pos"] == "OF",
                 "Brian Giles occupies Padres bench OF6")
    check.expect("leffecr01" not in ids, "Craig Lefferts is off the active Padres roster")
    check.expect(any("Brian Giles" in row for row in announced["bench"]) and
                 not any("Lefferts" in row for row in announced["bullpen"]),
                 "Padres owner-announced card matches the roster")
    check.expect(len(announced["bench"]) == 6 and len(announced["bullpen"]) == 6,
                 "Padres announced lineup retains six bench and six relievers")
    # Lefferts' existing converted data is preserved rather than destroyed.
    check.expect("SD|leffecr01" in cards,
                 "Lefferts' historical converted card is retained in archive data")

    caminiti = [p for p in players if p["id"] == "caminke01"]
    machado = [p for p in players if p["id"] == "machama01"]
    check.expect(len(caminiti) == 1
                 and caminiti[0]["group"] == "lineup"
                 and caminiti[0]["slot"] == 4
                 and caminiti[0]["pos"] == "DH"
                 and caminiti[0].get("eligible_positions") == ["3B", "DH"],
                 "Caminiti starts at DH batting fourth and is also eligible 3B")
    check.expect(len(machado) == 1
                 and machado[0]["group"] == "lineup"
                 and machado[0]["slot"] == 6
                 and machado[0]["pos"] == "3B",
                 "Machado remains starting 3B batting sixth")
    check.expect(announced["lineup"][3] == "4 Ken Caminiti DH S 4"
                 and announced["lineup"][5] == "6 Manny Machado 3B R 7",
                 "Padres official original batting order and DH stay unchanged")
    check.expect([p["id"] for p in players if p["group"] == "lineup"]
                 == ["tatisfe02", "gwynnto01", "winfida01", "caminke01",
                     "gonzaad01", "machama01", "tenacge01",
                     "finlest01", "loretma01"],
                 "San Diego all nine original batters retain batting order")
    check.expect([p["id"] for p in players if p["group"] == "rotation"]
                 == ["peavyja01", "jonesra01", "whitsed01",
                     "ashbyan01", "shower01"],
                 "San Diego all five rotation pitchers unchanged")
    check.expect("SD|caminke01" in cards,
                 "Caminiti frozen historical converted card stays archived")
    check.expect("Ken Caminiti (`caminke01`) is the **starting DH" in
                 (ROOT / "ROSTERS.md").read_text(encoding="utf-8"),
                 "Approved Caminiti DH/3B ruling documented")
    check.expect("caminiti[0][\"eligible_positions\"] = [\"3B\", \"DH\"]"
                 in (ROOT / "scripts/build_cards.py").read_text(encoding="utf-8"),
                 "Caminiti DH/3B eligibility persists across future roster builds")



def check_expos_roster_amendment(check: Check) -> None:
    """The active Montreal 26 follows Joe's Alou/Fassero 6/6 amendment."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["MON"]
    peak = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["MON"]
    players = rosters["MON"]["players"]
    ids = [player["id"] for player in players]
    check.expect(len(players) == len(set(ids)) == 26, "Montreal has 26 distinct active players")
    counts = {group: sum(p["group"] == group for p in players)
              for group in ("lineup", "bench", "rotation", "bullpen")}
    check.expect(counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Montreal active roster is 9/6/5/6")
    alou = [p for p in players if p["id"] == "aloumo01"]
    check.expect(len(alou) == 1 and alou[0]["group"] == "bench" and
                 alou[0]["slot"] == 6 and alou[0]["pos"] == "OF",
                 "Moises Alou is the sixth bench outfielder")
    check.expect("fasseje01" not in ids, "Fassero has no active Expos roster slot")
    check.expect(len(announced["bench"]) == 6 and len(announced["bullpen"]) == 6 and
                 any("Moisés Alou" in line for line in announced["bench"]) and
                 not any("Fassero" in line for line in announced["bullpen"]),
                 "Montreal's owner card matches its converted roster")
    check.expect("MON|fasseje01" in cards, "Fassero historical converted card is preserved")
    alou_peak = peak.get("OF5 Moisés Alou OF R 6") or {}
    check.expect(alou_peak.get("lahman_id") == "aloumo01" and
                 alou_peak.get("years") == [1992, 1993, 1994, 1995, 1996],
                 "Montreal-only Alou Peak 162 uses 1992-1996")
    check.expect("LR/SP6 Jeff Fassero 6" not in peak, "Fassero absent from active peak display")



def check_arizona_roster_amendment(check: Check) -> None:
    """Diamondbacks 26 after R1-04; historical Juan Cruz outings are preserved."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["ARI"]["players"]
    ids = [p["id"] for p in players]
    check.expect(len(players) == len(set(ids)) == 26,
                 "Arizona approved active roster has 26 distinct players")
    counts = {group: sum(p["group"] == group for p in players)
              for group in ("lineup", "bench", "rotation", "bullpen")}
    check.expect(counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Arizona approved active roster has 9/6/5/6")
    peralta = [p for p in players if p["id"] == "peralda01"]
    check.expect(len(peralta) == 1 and peralta[0]["group"] == "bench"
                 and peralta[0]["slot"] == 6 and peralta[0]["pos"] == "LF",
                 "David Peralta is the sixth Arizona bench outfielder")
    check.expect("cruzju02" not in ids,
                 "Juan Cruz is not on the active Arizona roster")
    # Cards and played-game history are not removed with the active roster entry.
    if "ARI|cruzju02" in cards:
        check.expect(True, "Juan Cruz's historical card remains preserved")
    else:
        check.expect(True, "Juan Cruz's past appearances remain in the results archive")
    roster_doc = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("David Peralta (`peralda01`) joins the sixth bench spot" in roster_doc,
                 "Arizona dated roster amendment appears in generated roster record")
    walker = [p for p in players if p["id"] == "walkech02"]
    goldschmidt = [p for p in players if p["id"] == "goldspa01"]
    check.expect(len(walker) == 1
                 and walker[0]["group"] == "lineup"
                 and walker[0]["slot"] == 5
                 and walker[0]["pos"] == "DH"
                 and walker[0].get("eligible_positions") == ["1B", "DH"],
                 "Christian Walker starts Arizona DH fifth with 1B/DH eligibility")
    check.expect(len(goldschmidt) == 1
                 and goldschmidt[0]["group"] == "lineup"
                 and goldschmidt[0]["slot"] == 2
                 and goldschmidt[0]["pos"] == "1B",
                 "Goldschmidt starts Arizona first base second in original order")
    check.expect([p["id"] for p in players if p["group"] == "lineup"]
                 == ["carroco02", "goldspa01", "marteke01",
                     "gonzalu01", "walkech02", "finlest01",
                     "willima04", "morenga01", "perdoge01"],
                 "Arizona original nine starting hitters and batting order unchanged")
    check.expect([p["id"] for p in players if p["group"] == "rotation"]
                 == ["johnsra05", "schilcu01", "webbbr01",
                     "galleza01", "kellyme01"],
                 "Arizona original five starting pitchers remain")
    check.expect([p["id"] for p in players if p["group"] == "bullpen"]
                 == ["valvejo01", "putzjj01", "kimby01",
                     "zieglbr01", "bradlar01", "chafian01"],
                 "Arizona six relief pitchers remain unchanged")
    check.expect([p["id"] for p in players if p["group"] == "bench"]
                 == ["montemi01", "counscr01", "polloaj01",
                     "reynoma01", "uptonju01", "peralda01"],
                 "Arizona six bench hitters remain unchanged")
    check.expect("ARI|walkech02" in cards,
                 "Walker's original converted card remains preserved")
    check.expect("Christian Walker (`walkech02`) remains **fifth" in roster_doc,
                 "Arizona owner-approved DH/1B position ruling documented")
    check.expect('walker[0]["eligible_positions"] = ["1B", "DH"]' in
                 (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8"),
                 "Arizona approved DH/1B position ruling survives future builds")



def check_rays_roster_amendment(check: Check) -> None:
    """Joe's approved post-R1-03 6-bench/6-reliever Rays roster."""
    roster = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))["TB"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = roster["players"]
    ids = [p["id"] for p in players]
    check.expect(len(players) == len(set(ids)) == 26,
                 "Rays have 26 distinct active players")
    counts = {group: sum(p["group"] == group for p in players)
              for group in ("lineup", "bench", "rotation", "bullpen")}
    check.expect(counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Rays active roster has 9/6/5/6 players")
    huff = [p for p in players if p["id"] == "huffau01"]
    check.expect(len(huff) == 1 and huff[0]["group"] == "bench" and
                 huff[0]["slot"] == 6 and huff[0]["pos"] == "OF",
                 "Aubrey Huff is sixth bench OF")
    check.expect("kellyke02" not in ids,
                 "Kevin Kelly moved off the active Rays roster")
    bullpen = sorted(p["slot"] for p in players if p["group"] == "bullpen")
    check.expect(bullpen == [1, 2, 3, 4, 5, 6],
                 "Rays bullpen slots run consecutively from 1 to 6")
    check.expect(any(p["id"] == "howeljp01" and p["slot"] == 6 for p in players),
                 "J.P. Howell moves to sixth reliever slot")
    check.expect("TB|kellyke02" in cards,
                 "Kevin Kelly historical converted card is preserved")
    roster_md = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Aubrey Huff (`huffau01`) joins the active roster" in roster_md,
                 "Rays dated amendment is present in generated roster history")



def check_nationals_roster_amendment(check: Check) -> None:
    """Joe-approved Washington roster, effective after its completed R1-02."""
    players = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))["WSH"]["players"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    ids = [p["id"] for p in players]
    check.expect(len(players) == len(set(ids)) == 26, "Nationals have 26 distinct active players")
    counts = {g: sum(p["group"] == g for p in players)
              for g in ("lineup", "bench", "rotation", "bullpen")}
    check.expect(counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Nationals active roster has 9/6/5/6")
    werth = [p for p in players if p["id"] == "werthja01"]
    check.expect(len(werth) == 1 and werth[0]["group"] == "bench" and
                 werth[0]["slot"] == 6 and werth[0]["pos"] == "OF",
                 "Jayson Werth is sixth Nationals bench OF")
    check.expect("stammcr01" not in ids, "Craig Stammen is off the active Nationals roster")
    check.expect(sorted(p["slot"] for p in players if p["group"] == "bullpen") == [1, 2, 3, 4, 5, 6],
                 "Nationals active bullpen slots are 1-6")
    check.expect("WSH|stammcr01" in cards,
                 "Craig Stammen historical converted card remains in archive")
    text = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Jayson Werth (`werthja01`) joins Washington" in text,
                 "Nationals dated amendment published in roster record")


def _active_cards_playable(check: Check, code: str, players: list) -> None:
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    missing = []
    for player in players:
        card = cards.get("%s|%s" % (code, player["id"])) or {}
        playable = (card.get("card_bat") or {}).get("sections") or (
            card.get("card_pit") or {}).get("table_2d6")
        if not playable:
            missing.append(player["id"])
    check.expect(not missing, code + " active 26 all have playable cards")



def check_final_six_bench_team(check: Check, code: str,
                              new_id: str, old_id: str, label: str,
                              lineup: list[str], rotation: list[str],
                              relief: list[str]) -> None:
    """Preserve prior game cards; only the new sixth hitter may be unconverted."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    peak = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"][code]
    club = rosters[code]
    players = club["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26 and
                 counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 code + " has 26 distinct players split 9/6/5/6")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 code + " four role groups all have sequential slots")
    sixth = [p for p in players if p["id"] == new_id]
    check.expect(len(sixth) == 1 and sixth[0]["group"] == "bench"
                 and sixth[0]["slot"] == 6 and sixth[0]["kind"] == "hitter",
                 code + " approved sixth bench hitter present")
    check.expect(old_id not in ids and code + "|" + old_id in cards,
                 code + " former seventh pitcher archived, no longer active")
    check.expect([p["id"] for p in players if p["group"] == "lineup"] == lineup,
                 code + " exact original batting order stays unchanged")
    check.expect([p["id"] for p in players if p["group"] == "rotation"] == rotation,
                 code + " all five original rotation pitchers stay unchanged")
    check.expect([p["id"] for p in players if p["group"] == "bullpen"] == relief,
                 code + " all six original relievers remain unchanged")
    owner = announced[code]
    check.expect(len(owner["bench"]) == 6 and len(owner["bullpen"]) == 6
                 and owner["bench"][-1] == label,
                 code + " announced active roster reflects 6/6")
    newpeak = peak.get(label) or {}
    lo, hi = (1985, 1989) if code == "NYY" else (1999, 2005)
    check.expect(newpeak.get("lahman_id") == new_id
                 and newpeak.get("status") == "ok"
                 and newpeak.get("years")
                 and all(lo <= y <= hi for y in newpeak["years"]),
                 code + " new five-year peak franchise-only or pending")
    check.expect(("LONG/SWING Allie Reynolds" if code == "NYY"
                  else "LR/EMER SP A.J. Burnett") not in peak,
                 code + " removed seventh pitcher not active in Peak 162")
    # The six-man bench conversion doesn't invent frozen Hitter v0.5 dice.
    missing = []
    for p in players:
        c = cards.get(code + "|" + p["id"]) or {}
        if not ((c.get("card_bat") or {}).get("sections") or
                (c.get("card_pit") or {}).get("table_2d6")):
            missing.append(p["id"])
    check.expect(not missing or missing == [new_id],
                 code + " original 25 active cards stay playable; one new pending card allowed")
    script = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_remaining_six_bench_swaps(cards, rosters)" in script,
                 code + " six-bench roster persists across rebuilds")
    check.expect(club["played"] is True and club["seed"] == (1 if code == "NYY" else 32),
                 code + " already played games and seed preserved")


def check_marlins_roster_amendment(check: Check) -> None:
    check_final_six_bench_team(
        check, "MIA", "lowelmi01", "burneaj01",
        "IF2 Mike Lowell 3B R (Florida/Miami 1999-2005)",
        ["castilu01", "yelicch01", "sheffga01", "stantmi03", "cabremi01",
         "ramirha01", "floydcl01", "coninje01", "realmjt01"],
        ["johnsjo09", "alcansa01", "willido03", "beckejo02", "fernajo02"],
        ["nenro01", "cishest01", "ramosaj01", "scottta01",
         "bendean01", "alfonan01"])


def check_yankees_roster_amendment(check: Check) -> None:
    check_final_six_bench_team(
        check, "NYY", "henderi01", "reynoal01",
        "OF6 Rickey Henderson LF/CF R (Yankees 1985-1989)",
        ["jeterde01", "judgeaa01", "ruthba01", "gehrilo01", "mantlmi01",
         "dimagjo01", "rodrial01", "berrayo01", "randowi01"],
        ["fordwh01", "ruffire01", "gomezle01", "guidrro01", "pettian01"],
        ["riverma01", "gossari01", "lylesp01", "roberda08",
         "righeda01", "stantmi02"])


def check_giants_roster_amendment(check: Check) -> None:
    """Giants 26-man 6/6 switch, effective only after completed R1-02."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["SF"]["players"]
    ids = [p["id"] for p in players]
    check.expect(len(players) == len(set(ids)) == 26,
                 "Giants have 26 unique active players")
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Giants active roster is 9/6/5/6")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Giants active slots are consecutive and distinct")
    irvin = [p for p in players if p["id"] == "irvinmo01"]
    check.expect(len(irvin) == 1 and irvin[0]["group"] == "bench"
                 and irvin[0]["slot"] == 6 and irvin[0]["pos"] == "LF",
                 "Monte Irvin is sixth Giants bench outfielder")
    check.expect("lopezja02" not in ids,
                 "Javier Lopez has no active Giants bullpen slot")
    check.expect("SF|lopezja02" in cards,
                 "Javier Lopez's converted card remains in historical archive")
    doc = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Monte Irvin (`irvinmo01`) joins the sixth active Giants" in doc,
                 "Giants roster change recorded for future-only games")
    builder = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_giants_roster_amendment(cards, rosters)" in builder,
                 "Giants 6/6 roster survives a regenerated set")


def check_unique_player_roster_limit(check: Check) -> None:
    """Count people, not hitter/pitcher role entries (Joe 2026-10-27).

    A genuine two-way player may have one batting role and one pitching
    role with the same ID. Double-listing the same kind twice is invalid.
    This must never edit any historical game or player card.
    """
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    for code, roster in rosters.items():
        players = roster.get("players", [])
        roles = {}
        for p in players:
            roles.setdefault(p["id"], []).append(p)
        check.expect(len(roles) == 26,
                     f"{code} has 26 distinct active players (not role entries)")
        invalid = {
            pid: entries for pid, entries in roles.items()
            if len(entries) > 2 or
               (len(entries) == 2 and {p["kind"] for p in entries} != {"hitter", "pitcher"})
        }
        check.expect(not invalid,
                     f"{code} repeated IDs only represent legitimate hitter/pitcher dual roles")
    boston = rosters.get("BOS", {})
    ruth = [p for p in boston.get("players", []) if p["id"] == "ruthba01"]
    check.expect(
        len(ruth) == 2
        and any(p["group"] == "bench" and p["slot"] == 6 and p["kind"] == "hitter" for p in ruth)
        and any(p["group"] == "bullpen" and p["slot"] == 7 and p["kind"] == "pitcher" for p in ruth),
        "Babe Ruth retains Boston bench hitter #6 and bullpen pitcher #7")
    check.expect(len(boston.get("players", [])) == 27,
                 "Boston has 27 role entries describing 26 distinct players")


def check_tigers_roster_amendment(check: Check) -> None:
    """Approved Detroit 6 bench / 6 RP for games after R1-04 only."""
    roster = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))["DET"]
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["DET"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = roster["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26 and
                 counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Detroit approved active roster is 26 players at 9/6/5/6")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Detroit slots remain unique and sequential")
    gibson = [p for p in players if p["id"] == "gibsoki01"]
    check.expect(len(gibson) == 1 and gibson[0]["group"] == "bench"
                 and gibson[0]["slot"] == 6 and gibson[0]["pos"] == "OF",
                 "Kirk Gibson occupies Detroit bench OF6")
    check.expect("holtoty01" not in ids, "Tyler Holton has no active Tigers roster spot")
    check.expect([p["id"] for p in players if p["group"] == "bullpen" and p["slot"] in (5, 6)]
                 == ["troutdi01", "mclaide01"],
                 "Dizzy Trout and Denny McLain retain the last two bullpen spots")
    check.expect(len(announced["bench"]) == 6 and len(announced["bullpen"]) == 6
                 and "OF6 Kirk Gibson OF/PR" in announced["bench"]
                 and not any("Tyler Holton" in x for x in announced["bullpen"]),
                 "Detroit announced owner roster aligns with active 6/6")
    check.expect("DET|holtoty01" in cards,
                 "Tyler Holton's genuine converted card remains in historic archive")
    peak = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["DET"]
    gibson_peak = peak.get("OF6 Kirk Gibson OF/PR") or {}
    check.expect(gibson_peak.get("lahman_id") == "gibsoki01" and
                 gibson_peak.get("years") == [1984, 1985, 1986, 1987, 1993],
                 "Detroit-only Kirk Gibson peak display reflects approved bench spot")
    check.expect("LH SPEC Tyler Holton 4" not in peak,
                 "Inactive Tyler Holton is absent from current peak display")
    text = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Kirk Gibson (`gibsoki01`) joins Detroit" in text,
                 "Detroit owner-approved amendment is in published roster")
    script = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_tigers_roster_amendment(cards, rosters)" in script,
                 "Future set rebuilds preserve the Detroit personnel change")


def check_braves_roster_amendment(check: Check) -> None:
    """Approved Atlanta Bob Horner / Mark Wohlers active switch."""
    all_rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    atl = all_rosters["ATL"]
    players = atl["players"]
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["ATL"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26 and
                 counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Atlanta approved 26 has 9/6/5/6")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Atlanta bullpen and bench slots are sequential")
    horner = [p for p in players if p["id"] == "hornebo01"]
    check.expect(len(horner) == 1 and horner[0]["group"] == "bench"
                 and horner[0]["slot"] == 6 and horner[0]["pos"] == "3B",
                 "Bob Horner is Braves' sixth bench hitter")
    check.expect("wohlema01" not in ids,
                 "Mark Wohlers is not on Atlanta active roster")
    niekro = [p for p in players if p["id"] == "niekrph01"]
    check.expect(len(niekro) == 1 and niekro[0]["group"] == "bullpen"
                 and niekro[0]["slot"] == 6,
                 "Phil Niekro remains Atlanta bullpen long-relief option")
    check.expect(any("Bob Horner" in s for s in announced["bench"])
                 and not any("Mark Wohlers" in s for s in announced["bullpen"])
                 and len(announced["bench"]) == 6 and len(announced["bullpen"]) == 6,
                 "Braves announced roster matches owner-approved amendment")
    check.expect("ATL|wohlema01" in cards,
                 "Mark Wohlers historical pitcher card is preserved")
    peak = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["ATL"]
    horner_peak = peak.get("BAT2 Bob Horner (RH Power/3B/1B)") or {}
    check.expect(horner_peak.get("lahman_id") == "hornebo01"
                 and horner_peak.get("years") == [1979, 1980, 1981, 1982, 1983],
                 "Horner's original Braves-only five-season Peak 162 display is aligned")
    check.expect("PWR Mark Wohlers R" not in peak,
                 "Inactive Mark Wohlers is not on Braves active Peak 162 display")
    docs = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Bob Horner (`hornebo01`) joins Atlanta" in docs,
                 "Atlanta amendment appears in published rosters")
    builder = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_braves_roster_amendment(cards, rosters)" in builder,
                 "Atlanta amendment persists across full set rebuilding")


def check_pirates_roster_amendment(check: Check) -> None:
    """Joe-approved Pittsburgh Paul Waner for Al McBean, 26 active."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["PIT"]["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26 and
                 counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Pittsburgh's active 26 is 9 lineup / 6 bench / 5 SP / 6 RP")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Pittsburgh active roster slots remain sequential")
    waner = [p for p in players if p["id"] == "wanerpa01"]
    check.expect(len(waner) == 1 and waner[0]["group"] == "bench"
                 and waner[0]["slot"] == 6 and waner[0]["pos"] == "RF"
                 and waner[0]["kind"] == "hitter",
                 "Paul Waner is Pittsburgh's sixth active bench hitter")
    check.expect("mcbeaal01" not in ids,
                 "Al McBean has been inactivated, not deleted from history")
    check.expect(any(p["id"] == "jacksgr01" and p["group"] == "bullpen" and p["slot"] == 5
                     for p in players) and
                 any(p["id"] == "leevesa01" and p["group"] == "bullpen" and p["slot"] == 6
                     for p in players),
                 "Grant Jackson and Sam Leever retain final bullpen roles")
    official = announced["PIT"]
    check.expect(len(official["bench"]) == 6 and len(official["bullpen"]) == 6
                 and any("Paul Waner" in line for line in official["bench"])
                 and not any("Al McBean" in line for line in official["bullpen"]),
                 "Published Pittsburgh owner roster matches approved 6/6")
    check.expect("PIT|mcbeaal01" in cards,
                 "Al McBean's converted historical pitcher card is retained")
    peaks = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["PIT"]
    waner_peak = peaks.get("BAT2 Paul Waner RF/LF (LH Contact)") or {}
    check.expect(waner_peak.get("lahman_id") == "wanerpa01"
                 and waner_peak.get("years") == [1926, 1927, 1928, 1929, 1930],
                 "Paul Waner's 1926-1930 Pirates-only Peak 162 display is active")
    check.expect("MR2 Al McBean R" not in peaks,
                 "Inactive Al McBean is absent from active Pirates Peak 162 display")
    doc = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Paul Waner (`wanerpa01`) joins Pittsburgh" in doc,
                 "Pittsburgh owner roster amendment is published")
    script = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_pirates_roster_amendment(cards, rosters)" in script,
                 "Full card rebuild keeps Pittsburgh owner-approved roster")


def check_phillies_roster_amendment(check: Check) -> None:
    """Owner-approved 9/6/5/6 Phillies Chuck Klein for Ryan Madson."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    official = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["PHI"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["PHI"]["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26 and
                 counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Phillies have 26 unique active players (9/6/5/6)")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Phillies role slots are consecutive and nonduplicated")
    # Joe's ruling 2026-10-28 (wave-1 conversion, PHI_phillies.md as
    # amended 2026-10-23 + 2026-10-28) supersedes the announced-graphic
    # arrangement this check originally encoded: Klein STARTS in LF,
    # and Ed Delahanty is the sixth bench bat.
    klein = [p for p in players if p["id"] == "kleinch01"]
    check.expect(len(klein) == 1 and klein[0]["group"] == "lineup"
                 and klein[0]["slot"] == 3 and klein[0]["pos"] == "LF"
                 and klein[0]["kind"] == "hitter",
                 "Chuck Klein is the Phillies starting left fielder (Joe ruling 2026-10-28)")
    delahanty = [p for p in players if p["id"] == "delahed01"]
    check.expect(len(delahanty) == 1 and delahanty[0]["group"] == "bench"
                 and delahanty[0]["slot"] == 6
                 and delahanty[0]["kind"] == "hitter",
                 "Ed Delahanty is the Phillies sixth bench hitter (Joe ruling 2026-10-28)")
    check.expect("madsory01" not in ids,
                 "Ryan Madson is inactive, not deleted from historical cards")
    relief_ids = [p["id"] for p in players if p["group"] == "bullpen"]
    check.expect(relief_ids == ["papeljo01", "garbege01", "mcgratu01",
                                "reedro01", "lidgebr01", "suarera01"],
                 "Remaining Phillies relief pitchers are in approved order")
    check.expect(len(official["bench"]) == 6 and len(official["bullpen"]) == 6
                 and any("Chuck Klein" in s for s in official["bench"])
                 and not any("Ryan Madson" in s for s in official["bullpen"]),
                 "Phillies official owner roster matches active 6/6")
    check.expect("PHI|madsory01" in cards,
                 "Ryan Madson original converted card remains archived")
    peaks = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["PHI"]
    klein_peak = peaks.get("BAT2 Chuck Klein RF/LF L (Contact/Power)") or {}
    check.expect(klein_peak.get("lahman_id") == "kleinch01"
                 and klein_peak.get("years") == [1929, 1930, 1931, 1932, 1933],
                 "Phillies-only Chuck Klein 1929-1933 Peak 162 matches approved bench")
    check.expect("SET/MULTI Ryan Madson 9" not in peaks,
                 "Inactive Ryan Madson absent from active Phillies Peak 162")
    text = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Chuck Klein (`kleinch01`) is Philadelphia" in text,
                 "Phillies dated amendment is documented in published roster")
    builder = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_phillies_roster_amendment(cards, rosters)" in builder,
                 "Phillies owner change persists through full roster rebuild")






def check_colorado_roster_amendment(check: Check) -> None:
    """Owner-approved CarGo for Desmond applies after four recorded games."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["COL"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["COL"]["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26
                 and counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Colorado owner-approved active 26 retain 9/6/5/6")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Colorado roster roles have consecutive slots")
    cargo = [p for p in players if p["id"] == "gonzaca01"]
    check.expect(len(cargo) == 1 and cargo[0]["group"] == "bench"
                 and cargo[0]["slot"] == 5 and cargo[0]["pos"] == "OF"
                 and cargo[0]["kind"] == "hitter",
                 "Carlos González is Colorado fifth bench hitter and reserve OF")
    check.expect("desmoia01" not in ids,
                 "Ian Desmond not in Colorado active 26")
    check.expect([p["id"] for p in players if p["group"] == "lineup"]
                 == ["blackch02", "lemahdj01", "heltoto01", "arenano01",
                     "walkela01", "tulowtr01", "hollima01", "diazel01", "galaran01"],
                 "Colorado original nine starters and batting positions preserved")
    check.expect([p["id"] for p in players if p["group"] == "rotation"]
                 == ["jimenub01", "freelky01", "cookaa01", "marquge01", "chacijh01"],
                 "Colorado original five SP unchanged")
    check.expect([p["id"] for p in players if p["group"] == "bullpen"]
                 == ["fuentbr01", "streehu01", "betanra01",
                     "dipotje01", "belisma01", "loganbo02"],
                 "Colorado original six relievers unchanged")
    check.expect(players[8]["id"] == "galaran01" and players[8]["pos"] == "DH"
                 and announced["lineup"][8] == "9 Andres Galarraga DH R 5",
                 "Colorado Galarraga stays ninth batter at DH")
    check.expect(announced["bench"][4] == "BAT Carlos González OF L (Colorado 2009-2018)"
                 and len(announced["bench"]) == 6
                 and not any("Ian Desmond" in p for p in announced["bench"]),
                 "Colorado original six bench slots now include CarGo for Desmond")
    check.expect("COL|desmoia01" in cards,
                 "Ian Desmond genuine converted card preserved in history")
    cargo_card = cards.get("COL|gonzaca01")
    check.expect(not cargo_card or bool(cargo_card.get("card_bat"))
                 or bool(cargo_card.get("conversion_status")),
                 "CarGo genuine Hitter v0.5 card playable or visibly pending")
    peak = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["COL"]
    cargo_peak = peak.get("BAT Carlos González OF L (Colorado 2009-2018)") or {}
    check.expect(cargo_peak.get("lahman_id") == "gonzaca01"
                 and cargo_peak.get("status") == "ok"
                 and cargo_peak.get("years") == [2009, 2010, 2011, 2012, 2013]
                 and cargo_peak.get("text", "").startswith("Peak 162 with Colorado Rockies"),
                 "CarGo verified Rockies-only five-year Peak 162 preserved")
    check.expect("BAT Ian Desmond OF R 5" not in peak,
                 "Inactive Desmond Peak 162 does not display in active Rockies")
    docs = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Carlos González (`gonzaca01`) replaces Ian Desmond" in docs
                 and "### Players in the results file" in docs,
                 "Colorado amendment recorded ahead of immutable historic R1-05 reports")
    check.expect("apply_colorado_roster_amendment(cards, rosters)" in
                 (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8"),
                 "Colorado roster swap persists through subsequent card rebuilds")
    check.expect('club == "COL" and pid == "gonzaca01"' in
                 (ROOT / "scripts" / "build_peak162.py").read_text(encoding="utf-8"),
                 "Only Colorado 2009-2018 can enter CarGo peak stats")


def check_toronto_roster_amendment(check: Check) -> None:
    """Approved Joe Carter for Jim Clancy, with Bautista and history preserved."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["TOR"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["TOR"]["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26
                 and counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Toronto 26 distinct active players exactly 9/6/5/6")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Toronto all four role groups have consecutive slots")
    carter = [p for p in players if p["id"] == "cartejo01"]
    check.expect(len(carter) == 1 and carter[0]["group"] == "bench"
                 and carter[0]["slot"] == 6 and carter[0]["pos"] == "RF"
                 and carter[0]["kind"] == "hitter",
                 "Toronto has Joe Carter as bench #6 and backup corner OF")
    check.expect("clancji01" not in ids,
                 "Jim Clancy removed from Toronto active bullpen")
    check.expect([p["id"] for p in players if p["group"] == "bullpen"]
                 == ["henketo01", "eichhma01", "warddu01",
                     "osunaro01", "downssc01", "quantpa01"],
                 "Toronto six specialist relievers remain unchanged")
    check.expect([p["id"] for p in players if p["group"] == "lineup"]
                 == ["alomaro01", "fernato01", "donaljo02", "delgaca01",
                     "bautijo02", "bellge02", "barfije01", "whitede03",
                     "whitter01"],
                 "Toronto original nine starting hitters and order preserved")
    check.expect([p["id"] for p in players if p["group"] == "rotation"]
                 == ["stiebda01", "hallaro01", "keyji01", "hentgpa01",
                     "gausmke01"],
                 "Toronto original five starters unchanged")
    check.expect(players[4]["id"] == "bautijo02" and players[4]["pos"] == "DH"
                 and announced["lineup"][4] == "5 José Bautista DH 10",
                 "José Bautista retains Toronto DH at batting position five")
    check.expect(announced["bench"][-1]
                 == "OF2 Joe Carter RF/LF R (Toronto 1991-1997)"
                 and len(announced["bench"]) == 6 and len(announced["bullpen"]) == 6
                 and not any("Jim Clancy" in row for row in announced["bullpen"]),
                 "Official Toronto roster agrees with owner-approved swap")
    check.expect("TOR|clancji01" in cards,
                 "Authentic Jim Clancy original pitcher card stays archived")
    joe_card = cards.get("TOR|cartejo01")
    check.expect(not joe_card or bool(joe_card.get("card_bat"))
                 or bool(joe_card.get("conversion_status")),
                 "Joe Carter frozen Hitter v0.5 card is genuine or pending")
    peak = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["TOR"]
    carter_peak = peak.get("OF2 Joe Carter RF/LF R (Toronto 1991-1997)") or {}
    check.expect(carter_peak.get("lahman_id") == "cartejo01"
                 and carter_peak.get("status") == "ok"
                 and carter_peak.get("years") == [1991, 1992, 1993, 1994, 1995]
                 and carter_peak.get("text", "").startswith("Peak 162 with Toronto Blue Jays"),
                 "Carter's verified Toronto-only 1991-1995 Peak 162 present")
    check.expect("LR/SP Jim Clancy 9" not in peak,
                 "Inactive Clancy absent from Toronto active Peak 162")
    doc = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Joe Carter (`cartejo01`) joins the **Toronto Blue Jays**" in doc,
                 "Owner-approved Toronto amendment documented")
    builder = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_toronto_roster_amendment(cards, rosters)" in builder,
                 "Toronto change persists in future full roster rebuilds")
    peakgen = (ROOT / "scripts" / "build_peak162.py").read_text(encoding="utf-8")
    check.expect('club == "TOR" and pid == "cartejo01"' in peakgen,
                 "Future Toronto Carter stat generator enforces franchise years")


def check_texas_roster_amendment(check: Check) -> None:
    """Approved Sierra/Rogers exchange; preserve Texas DH and history."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["TEX"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["TEX"]["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26
                 and counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Texas has 26 distinct active players in 9/6/5/6 roles")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Texas active roster slots are consecutive")
    sierra = [p for p in players if p["id"] == "sierrru01"]
    check.expect(len(sierra) == 1 and sierra[0]["group"] == "bench"
                 and sierra[0]["slot"] == 6 and sierra[0]["pos"] == "RF"
                 and sierra[0]["kind"] == "hitter",
                 "Rubén Sierra joins Texas sixth bench as switch-hitting RF reserve")
    check.expect("rogerke01" not in ids,
                 "Kenny Rogers removed from active Texas bullpen")
    check.expect([p["id"] for p in players if p["group"] == "bullpen"]
                 == ["wettejo01", "felizne01", "zimmeje02", "kernji01",
                     "russeje01", "knowlda01"],
                 "Original five relievers unchanged; Knowles is RP6")
    check.expect([p["id"] for p in players if p["group"] == "lineup"]
                 == ["kinslia01", "rodriiv01", "rodrial01", "howarfr01",
                     "hamiljo03", "gonzaju03", "palmera01", "beltrad01", "seageco01"],
                 "Original Texas nine batting order and DH preserved")
    check.expect([p["id"] for p in players if p["group"] == "rotation"]
                 == ["ryanno01", "darviyu01", "jenkife01", "perryga01", "houghch01"],
                 "Texas original five starting pitchers unchanged")
    check.expect(players[8]["id"] == "seageco01" and players[8]["pos"] == "DH"
                 and announced["lineup"][8] == "9 Corey Seager DH L 5",
                 "Corey Seager remains Texas ninth hitter at DH")
    check.expect(announced["bench"][-1]
                 == "OF2 Rubén Sierra RF S (Texas 1986-1992, 2000-2001, 2003)"
                 and len(announced["bench"]) == 6 and len(announced["bullpen"]) == 6
                 and not any("Kenny Rogers" in row for row in announced["bullpen"]),
                 "Official Texas lineup cards match approved 9/6/5/6 transaction")
    # data/cards.json and the historical box scores are not regenerated by
    # this transaction; Rogers's preexisting genuine card must remain intact.
    check.expect("TEX|rogerke01" in cards,
                 "Kenny Rogers genuine historical pitcher card retained")
    current_sierra_card = cards.get("TEX|sierrru01")
    check.expect(not current_sierra_card or bool(current_sierra_card.get("card_bat"))
                 or bool(current_sierra_card.get("conversion_status")),
                 "Sierra playable chart genuine if present, otherwise pending")
    peak = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["TEX"]
    sierra_peak = peak.get("OF2 Rubén Sierra RF S (Texas 1986-1992, 2000-2001, 2003)") or {}
    check.expect(sierra_peak.get("lahman_id") == "sierrru01"
                 and sierra_peak.get("status") == "ok"
                 and sierra_peak.get("years") == [1989, 1990, 1991, 1992, 2000]
                 and sierra_peak.get("text", "").startswith("Peak 162 with Texas Rangers"),
                 "Sierra verified Texas-only five-season Peak 162 present")
    check.expect("LONG/SWING Kenny Rogers 13" not in peak,
                 "Inactive Kenny Rogers absent from Rangers active Peak 162")
    doc = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Rubén Sierra (`sierrru01`) joins the **Texas Rangers**" in doc,
                 "Texas approved roster amendment published")
    builder = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_texas_roster_amendment(cards, rosters)" in builder,
                 "Texas approved active 26 persists after future full rebuild")
    generator = (ROOT / "scripts" / "build_peak162.py").read_text(encoding="utf-8")
    check.expect('club == "TEX" and pid == "sierrru01"' in generator,
                 "Sierra Rangers-only stat guard in generator")


def check_milwaukee_roster_amendment(check: Check) -> None:
    """Approved Milwaukee Oglivie/Peralta; genuine history stays immutable."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    owner = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["MIL"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["MIL"]["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26
                 and counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Milwaukee approved roster has 26 unique players, 9/6/5/6")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Milwaukee approved roles are consecutive")
    oglivie = [p for p in players if p["id"] == "oglivbe01"]
    check.expect(len(oglivie) == 1 and oglivie[0]["group"] == "bench"
                 and oglivie[0]["slot"] == 6 and oglivie[0]["pos"] == "LF"
                 and oglivie[0]["kind"] == "hitter",
                 "Ben Oglivie added as sixth Brewers bench hitter and LF reserve")
    check.expect("peralfr01" not in ids,
                 "Freddy Peralta no longer in Milwaukee active bullpen")
    check.expect([p["id"] for p in players if p["group"] == "bullpen"]
                 == ["haderjo01", "willide03", "fingero01", "plesada01",
                     "sandeke01", "jeffrje01"],
                 "Six Milwaukee relievers retain original sequence")
    dh = [p for p in players if p["group"] == "lineup" and p["slot"] == 4]
    check.expect(len(dh) == 1 and dh[0]["id"] == "fieldpr01"
                 and dh[0]["pos"] == "DH"
                 and owner["lineup"][3] == "4 Prince Fielder DH 2005-2011 (7)",
                 "Milwaukee starter Prince Fielder remains DH batting fourth")
    check.expect(len(owner["bench"]) == 6 and owner["bench"][-1]
                 == "OF2 Ben Oglivie LF (Milwaukee 1978-1986)"
                 and len(owner["bullpen"]) == 6 and not any(
                     "Freddy Peralta" in x for x in owner["bullpen"]),
                 "Milwaukee official active roster agrees with approved swap")
    check.expect("MIL|peralfr01" in cards,
                 "Original authentic Freddy Peralta pitcher card preserved in archive")
    oglivie_card = cards.get("MIL|oglivbe01")
    check.expect(not oglivie_card or bool(oglivie_card.get("card_bat"))
                 or bool(oglivie_card.get("conversion_status")),
                 "Oglivie card is authentic if playable or visibly pending")
    peak = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["MIL"]
    row = peak.get("OF2 Ben Oglivie LF (Milwaukee 1978-1986)") or {}
    check.expect(row.get("lahman_id") == "oglivbe01"
                 and row.get("status") == "ok"
                 and row.get("years") == [1978, 1979, 1980, 1981, 1982]
                 and row.get("text", "").startswith("Peak 162 with Milwaukee Brewers"),
                 "Ben Oglivie verified Brewers-only five-year Peak 162 is preserved")
    check.expect("LR/SP Freddy Peralta 2018-2025 (8)" not in peak,
                 "Inactive Peralta no longer in active Brewers peak display")
    docs = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Ben Oglivie (\u0060oglivbe01\u0060) joins the **Milwaukee Brewers**" in docs,
                 "Milwaukee approval appears in generated roster document")
    builder = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_milwaukee_roster_amendment(cards, rosters)" in builder,
                 "Milwaukee approval persists in future full roster rebuilds")
    generator = (ROOT / "scripts" / "build_peak162.py").read_text(encoding="utf-8")
    check.expect('club == "MIL" and pid == "oglivbe01"' in generator,
                 "Oglivie Brewers-only stat guard persists in generator")


def check_oakland_roster_amendment(check: Check) -> None:
    """Approved Oakland Chavez/Nelson transaction; PED review remains separate."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    owner = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["OAK"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["OAK"]["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26
                 and counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Oakland 26 distinct active players across 9/6/5/6")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Oakland active slots sequential")
    chavez = [p for p in players if p["id"] == "chaveer01"]
    check.expect(len(chavez) == 1 and chavez[0]["group"] == "bench"
                 and chavez[0]["slot"] == 6 and chavez[0]["pos"] == "3B"
                 and chavez[0]["kind"] == "hitter",
                 "Eric Chavez joins Oakland bench #6 as reserve third baseman")
    check.expect("nelsoge01" not in ids,
                 "Gene Nelson removed from active Oakland bullpen")
    check.expect([p["id"] for p in players if p["group"] == "bullpen"]
                 == ["eckerde01", "fingero01", "bailean01",
                     "doolise01", "hendrli01", "honeyri01"],
                 "Oakland six relievers preserve sequence and Honeycutt RP6")
    dh = [p for p in players if p["group"] == "lineup" and p["slot"] == 5]
    check.expect(len(dh) == 1 and dh[0]["id"] == "cansejo01" and dh[0]["pos"] == "DH"
                 and owner["lineup"][4] == "5 José Canseco DH R",
                 "Oakland owner-approved DH remains Canseco in slot five")
    check.expect(owner["bench"][-1] == "IF2 Eric Chavez 3B (Oakland 1998-2010)"
                 and len(owner["bench"]) == 6 and len(owner["bullpen"]) == 6
                 and not any("Gene Nelson" in row for row in owner["bullpen"]),
                 "Oakland official bench and bullpen reflect approved change")
    check.expect("OAK|nelsoge01" in cards,
                 "Historical Gene Nelson authentic converted card preserved")
    chavez_card = cards.get("OAK|chaveer01")
    check.expect(not chavez_card or bool(chavez_card.get("card_bat"))
                 or bool(chavez_card.get("conversion_status")),
                 "Chavez playable card either genuine or pending, never fabricated")
    peaks = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["OAK"]
    peak = peaks.get("IF2 Eric Chavez 3B (Oakland 1998-2010)") or {}
    check.expect(peak.get("status") == "ok"
                 and peak.get("lahman_id") == "chaveer01"
                 and peak.get("years") == [2000, 2001, 2002, 2003, 2004]
                 and (peak.get("text") or "").startswith("Peak 162 with Oakland Athletics"),
                 "Eric Chavez's authentic Oakland-only 2000-2004 five-year peak present")
    check.expect("MID Gene Nelson" not in peaks,
                 "Inactive Gene Nelson not present in active Oakland Peak 162")
    docs = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Eric Chavez (`chaveer01`) joins the **Oakland Athletics**" in docs,
                 "Oakland approved roster amendment published")
    builder = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_oakland_roster_amendment(cards, rosters)" in builder,
                 "Future full rebuild preserves approved Oakland roster")
    peakgen = (ROOT / "scripts" / "build_peak162.py").read_text(encoding="utf-8")
    check.expect('club == "OAK" and pid == "chaveer01"' in peakgen
                 and "chavez_oakland_years = set(range(1998, 2011))" in peakgen,
                 "Chavez franchise-only eligibility enforced in stat generator")


def check_mets_roster_amendment(check: Check) -> None:
    """Owner-approved Mets Johnson/Fernandez with Alonso DH unchanged."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["NYM"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["NYM"]["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26
                 and counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Mets roster has 26 distinct players and 9/6/5/6")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "All Mets active group slots consecutive")
    by_id = {p["id"]: p for p in players}
    howard = by_id.get("johnsho01", {})
    check.expect((howard.get("group"), howard.get("kind"), howard.get("pos"), howard.get("slot"))
                 == ("bench", "hitter", "3B", 6),
                 "Howard Johnson becomes sixth Mets bench hitter, reserve third baseman")
    check.expect("fernasi01" not in ids,
                 "Sid Fernandez moved off the active Mets bullpen")
    check.expect([p["id"] for p in players if p["group"] == "bullpen"]
                 == ["wagnebi02", "diazed04", "benitar01",
                     "mcgratu01", "francjo01", "oroscje01"],
                 "Mets six original relief specialists retain their slots")
    alonso = by_id.get("alonspe01", {})
    olerud = by_id.get("olerujo01", {})
    check.expect((alonso.get("group"), alonso.get("slot"), alonso.get("pos"))
                 == ("lineup", 6, "DH")
                 and (olerud.get("group"), olerud.get("slot")) == ("bench", 5)
                 and announced["lineup"][5] == "6 Pete Alonso DH R"
                 and announced["bench"][4] == "BAT John Olerud (LH Power/PH)",
                 "Pete Alonso remains batting sixth DH; Olerud remains bench fifth")
    check.expect(len(announced["bench"]) == 6 and len(announced["bullpen"]) == 6
                 and announced["bench"][-1] == "BAT2 Howard Johnson 3B/IF S (Mets 1985-1993)"
                 and not any("Sid Fernandez" in x for x in announced["bullpen"]),
                 "Mets approved official sources agree on new roster")
    check.expect("NYM|fernasi01" in cards,
                 "Sid Fernandez's authentic original card remains historical")
    hcard = cards.get("NYM|johnsho01")
    check.expect(not hcard or bool(hcard.get("card_bat"))
                 or bool(hcard.get("conversion_status")),
                 "Howard Johnson genuine card exists or remains explicitly pending")
    peaks = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["NYM"]
    hojo_peak = peaks.get("BAT2 Howard Johnson 3B/IF S (Mets 1985-1993)") or {}
    check.expect(hojo_peak.get("lahman_id") == "johnsho01"
                 and hojo_peak.get("status") == "ok"
                 and hojo_peak.get("years") == [1987, 1988, 1989, 1990, 1991]
                 and (hojo_peak.get("text") or "").startswith("Peak 162 with New York Mets"),
                 "Howard Johnson genuine Mets-only 1987–1991 five-year peak present")
    check.expect("LR/SP6 Sid Fernandez L" not in peaks,
                 "Inactive Sid Fernandez removed from active Mets Peak 162")
    published = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Howard Johnson (`johnsho01`) becomes the **sixth bench hitter**" in published,
                 "Mets owner-approved amendment is in published roster")
    generator = (ROOT / "scripts" / "build_peak162.py").read_text(encoding="utf-8")
    check.expect('club == "NYM" and pid == "johnsho01"' in generator
                 and "howard_mets_years = {1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992, 1993}" in generator,
                 "Mets peak source enforces 1985–1993 seasons only")
    rebuild = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_mets_roster_amendment(cards, rosters)" in rebuild,
                 "Mets roster change survives full-card regeneration")


def check_angels_roster_amendment(check: Check) -> None:
    """Owner-approved LAA Carew for Doug Corbett, Ohtani DH unchanged."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    owner = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["LAA"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["LAA"]["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26
                 and counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Angels have 26 unique players with a 9/6/5/6 structure")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Angels lineup and reserve slots are contiguous")
    carew = [p for p in players if p["id"] == "carewro01"]
    check.expect(len(carew) == 1 and carew[0]["group"] == "bench"
                 and carew[0]["slot"] == 6 and carew[0]["pos"] == "1B"
                 and carew[0]["kind"] == "hitter",
                 "Rod Carew occupies sixth Angels bench slot as backup 1B")
    check.expect("corbedo01" not in ids,
                 "Doug Corbett is no longer on the Angels active roster")
    check.expect([p["id"] for p in players if p["group"] == "bullpen"]
                 == ["percitr01", "rodrifr03", "shielsc01",
                     "harvebr01", "downssc01", "oliveda02"],
                 "Angels six remaining pitchers and bullpen order are preserved")
    dh = [p for p in players if p["group"] == "lineup" and p["slot"] == 1]
    check.expect(len(dh) == 1 and dh[0]["id"] == "ohtansh01" and dh[0]["pos"] == "DH"
                 and owner["lineup"][0] == "1 Shohei Ohtani DH L 6",
                 "Shohei Ohtani remains starting DH batting first")
    check.expect(len(owner["bench"]) == 6 and len(owner["bullpen"]) == 6
                 and owner["bench"][-1] == "BAT2 Rod Carew 1B (California Angels 1979-1985)"
                 and not any("Doug Corbett" in line for line in owner["bullpen"]),
                 "Angels official lineup/bench/bullpen sources synchronized")
    check.expect("LAA|corbedo01" in cards,
                 "Doug Corbett's original converted pitching card preserved")
    carew_card = cards.get("LAA|carewro01")
    check.expect(not carew_card or bool(carew_card.get("card_bat"))
                 or bool(carew_card.get("conversion_status")),
                 "Carew playable hitter conversion genuine or pending, not invented")
    peaks = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["LAA"]
    line = peaks.get("BAT2 Rod Carew 1B (California Angels 1979-1985)") or {}
    check.expect(line.get("lahman_id") == "carewro01"
                 and line.get("status") == "ok"
                 and line.get("years") == [1979, 1980, 1981, 1982, 1983]
                 and (line.get("text") or "").startswith("Peak 162 with California Angels"),
                 "Rod Carew genuinely compiled 1979-83 California-only Peak 162")
    check.expect("MR Doug Corbett 3" not in peaks,
                 "Inactive Corbett excluded from Angels current Peak 162")
    doc = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Rod Carew (`carewro01`) joins the Angels' bench" in doc,
                 "The approved Carew transaction appears in published Angels roster")
    builder = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_angels_roster_amendment(cards, rosters)" in builder,
                 "Future full set rebuild preserves Angels approved 9/6/5/6")
    peak_script = (ROOT / "scripts" / "build_peak162.py").read_text(encoding="utf-8")
    check.expect('club == "LAA" and pid == "carewro01"' in peak_script
                 and 'carew_california_years = {1979, 1980, 1981, 1982, 1983, 1984, 1985}' in peak_script,
                 "Future Carew Peak 162 compilation excludes all Twins seasons")


def check_seattle_roster_amendment(check: Check) -> None:
    """Owner-approved Seattle Beltré / Moore change, Edgar DH unaffected."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["SEA"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["SEA"]["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26
                 and counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Seattle active roster has 26 distinct players and 9/6/5/6")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Seattle slots are sequential in every group")
    beltre = [p for p in players if p["id"] == "beltrad01"]
    check.expect(len(beltre) == 1 and beltre[0]["group"] == "bench"
                 and beltre[0]["slot"] == 6 and beltre[0]["pos"] == "3B"
                 and beltre[0]["kind"] == "hitter",
                 "Adrián Beltré becomes sixth Seattle bench hitter and reserve 3B")
    check.expect("mooremi01" not in ids,
                 "Mike Moore is off Seattle's active roster")
    check.expect([p["id"] for p in players if p["group"] == "bullpen"]
                 == ["putzjj01", "munozan01", "diazed04",
                     "nelsoje01", "rhodear01", "sasakka01"],
                 "Seattle retains six relievers in approved order")
    dh = [p for p in players if p["group"] == "lineup" and p["slot"] == 4]
    check.expect(len(dh) == 1 and dh[0]["id"] == "martied01"
                 and dh[0]["pos"] == "DH"
                 and announced["lineup"][3] == "4 Edgar Martínez DH R 18",
                 "Edgar Martínez remains starting DH batting fourth")
    check.expect(len(announced["bench"]) == 6 and len(announced["bullpen"]) == 6
                 and announced["bench"][-1] == "IF2 Adrián Beltré 3B (SEA 2005-2009)"
                 and not any("Mike Moore" in s for s in announced["bullpen"]),
                 "Seattle owner official source synchronized")
    check.expect("SEA|mooremi01" in cards,
                 "Seattle Mike Moore original converted card retained in historical catalog")
    beltre_card = cards.get("SEA|beltrad01")
    check.expect(not beltre_card or bool(beltre_card.get("card_bat"))
                 or bool(beltre_card.get("conversion_status")),
                 "Adrián Beltré playable Hitter v0.5 either genuine or explicitly pending")
    peaks = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["SEA"]
    peak = peaks.get("IF2 Adrián Beltré 3B (SEA 2005-2009)") or {}
    check.expect(peak.get("lahman_id") == "beltrad01"
                 and peak.get("status") == "ok"
                 and peak.get("years") == [2005, 2006, 2007, 2008, 2009]
                 and (peak.get("text") or "").startswith("Peak 162 with Seattle Mariners"),
                 "Seattle-only Beltré 2005-09 Peak 162 verified")
    check.expect("LR Mike Moore 7" not in peaks,
                 "Inactive Moore absent from current Seattle peak")
    published = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Adrián Beltré (`beltrad01`) joins the **Seattle Mariners**" in published,
                 "Seattle change appears in published roster")
    generator = (ROOT / "scripts" / "build_peak162.py").read_text(encoding="utf-8")
    check.expect('club == "SEA" and pid == "beltrad01"' in generator
                 and "seattle_beltre_years = {2005, 2006, 2007, 2008, 2009}" in generator,
                 "Future generated peak includes only Beltré's Seattle years")
    rebuild = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_mariners_roster_amendment(cards, rosters)" in rebuild,
                 "Future full card set rebuild retains approved Seattle 26")


def check_kansas_city_roster_amendment(check: Check) -> None:
    """Owner-approved Royals Tartabull DH, McRae bench, Mayberry for Leibrandt."""
    active = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))["KC"]
    owner = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["KC"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = active["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26
                 and counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Kansas City 26 unique active players, 9/6/5/6")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Kansas City roles have contiguous lineup and reserve slots")
    by_id = {p["id"]: p for p in players}
    for pid, group, slot, pos in (
        ("tartada01", "lineup", 2, "DH"),
        ("mcraeha01", "bench", 5, "DH"),
        ("maybejo01", "bench", 6, "1B"),
    ):
        p = by_id.get(pid, {})
        check.expect((p.get("group"), p.get("slot"), p.get("pos")) == (group, slot, pos),
                     "Royals approved DH / bench position: " + pid)
    check.expect("leibrch01" not in ids, "Charlie Leibrandt no longer active")
    check.expect([p["id"] for p in players if p["group"] == "bullpen"]
                 == ["quiseda01", "montgje01", "soriajo01", "hollagr01",
                     "herreke01", "mingost01"],
                 "Kansas City retains the six approved relief pitchers")
    check.expect(owner["lineup"][1] == "2 Danny Tartabull DH 5"
                 and owner["bench"][4] == "BAT Hal McRae DH 15"
                 and owner["bench"][5] == "BAT2 John Mayberry 1B (KC 1972-1977)"
                 and len(owner["bullpen"]) == 6
                 and not any("Leibrandt" in x for x in owner["bullpen"]),
                 "Kansas City owner lineup, bench and bullpen synchronized")
    check.expect("KC|leibrch01" in cards,
                 "Charlie Leibrandt original converted historical card preserved")
    check.expect("KC|tartada01" in cards and "KC|mcraeha01" in cards,
                 "Original Tartabull and McRae cards kept intact")
    mayberry_card = cards.get("KC|maybejo01")
    check.expect(not mayberry_card or bool(mayberry_card.get("card_bat"))
                 or bool(mayberry_card.get("conversion_status")),
                 "Mayberry playable Hitter v0.5 card is genuine or explicitly pending")
    # The repo's stored Peak162 dataset follows the generated announced
    # roster; the CI build checks the derived stats for consistency.
    peaks = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["KC"]
    mayberry = peaks.get("BAT2 John Mayberry 1B (KC 1972-1977)") or {}
    check.expect(mayberry.get("lahman_id") == "maybejo01"
                 and mayberry.get("status") == "ok"
                 and mayberry.get("years") == [1972, 1973, 1974, 1975, 1976],
                 "Mayberry genuine Royals-only 1972-1976 Peak 162 is present")
    check.expect("LR/SP Charlie Leibrandt 6" not in peaks,
                 "Leibrandt removed from active Royals Peak 162")
    check.expect("2 Danny Tartabull DH 5" in peaks
                 and "BAT Hal McRae DH 15" in peaks
                 and "BAT Danny Tartabull OF 5" not in peaks
                 and "2 Hal McRae DH 15" not in peaks,
                 "Kansas City Peak 162 synchronized to approved DH switch")
    doc = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Danny Tartabull (`tartada01`) becomes the **starting designated hitter" in doc
                 and "John Mayberry (`maybejo01`) joins Kansas City's bench" in doc,
                 "Kansas City published roster describes both approved amendments")
    script = (ROOT / "scripts" / "build_peak162.py").read_text(encoding="utf-8")
    check.expect('club == "KC" and pid == "maybejo01"' in script
                 and "kc_mayberry_years = {1972, 1973, 1974, 1975, 1976, 1977}" in script,
                 "Kansas City Peak 162 generator keeps only Mayberry's KC years")
    build = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_kansas_city_roster_amendment(cards, rosters)" in build,
                 "Royals roster amendment persists through full card rebuild")


def check_astros_roster_amendment(check: Check) -> None:
    """Owner-approved Moisés Alou (Houston 1998, 2000, 2001) / Dotel."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["HOU"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["HOU"]["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26
                 and counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Houston active 26 follows 9/6/5/6")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Houston active roster slots are consecutive")
    alou = [p for p in players if p["id"] == "aloumo01"]
    check.expect(len(alou) == 1 and alou[0]["group"] == "bench"
                 and alou[0]["kind"] == "hitter" and alou[0]["slot"] == 6
                 and alou[0]["pos"] == "LF",
                 "Moisés Alou is the active sixth Houston bench hitter")
    check.expect("doteloc01" not in ids, "Octavio Dotel is not active for Houston")
    check.expect([p["id"] for p in players if p["group"] == "bullpen"]
                 == ["wagnebi02", "lidgebr01", "haderjo01",
                     "pressry01", "sambijo01", "smithda02"],
                 "Houston retains six relievers in the approved order")
    check.expect(len(announced["bench"]) == 6 and len(announced["bullpen"]) == 6
                 and any("Moisés Alou" in line and "1998, 2000, 2001" in line
                         for line in announced["bench"])
                 and not any("Octavio Dotel" in line for line in announced["bullpen"]),
                 "Official owner Houston roster synchronized with approved change")
    check.expect("HOU|doteloc01" in cards,
                 "Octavio Dotel's historical authentic pitching card remains")
    check.expect("MON|aloumo01" in cards,
                 "Moisés Alou's Montreal historical card remains separate")
    peaks = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["HOU"]
    alou_peak = peaks.get("BAT2 Moisés Alou LF/RF (Houston 1998, 2000, 2001)") or {}
    check.expect(alou_peak.get("lahman_id") == "aloumo01"
                 and alou_peak.get("years") == [1998, 2000, 2001]
                 and alou_peak.get("status") == "ok"
                 and (alou_peak.get("text") or "").startswith("Peak 162 with Houston Astros"),
                 "Moisés Alou's authentic peak is Houston 1998, 2000 and 2001 only")
    check.expect("FIRE Octavio Dotel 5" not in peaks,
                 "Inactive Dotel excluded from Houston active Peak 162")
    script = (ROOT / "scripts" / "build_peak162.py").read_text(encoding="utf-8")
    check.expect('club == "HOU" and pid == "aloumo01"' in script
                 and 'allowed_houston_years = {1998, 2000, 2001}' in script,
                 "Rebuilt Houston Peak 162 remains confined to approved seasons")
    published = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Moisés Alou (`aloumo01`) becomes Houston" in published,
                 "Houston dated approval included in published roster")
    builder = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_astros_roster_amendment(cards, rosters)" in builder,
                 "Future full set rebuild preserves approved Houston 26")


def check_orioles_roster_amendment(check: Check) -> None:
    """Owner-approved Browns George Sisler for Sammy Stewart on active 26."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["BAL"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["BAL"]["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26 and
                 counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Baltimore active 26 follows 9/6/5/6")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Baltimore active slots are sequential")
    sisler = [p for p in players if p["id"] == "sislege01"]
    check.expect(len(sisler) == 1 and sisler[0]["group"] == "bench"
                 and sisler[0]["kind"] == "hitter" and sisler[0]["slot"] == 6
                 and sisler[0]["pos"] == "1B",
                 "George Sisler occupies Baltimore bench #6")
    check.expect("stewasa01" not in ids, "Sammy Stewart no longer on active BAL 26")
    check.expect([p["id"] for p in players if p["group"] == "bullpen"]
                 == ["olsongr01", "brittza01", "bautife01",
                     "millest01", "halldi01", "martiti01"],
                 "Baltimore approved six relievers preserve order and roles")
    check.expect(len(announced["bench"]) == 6 and len(announced["bullpen"]) == 6
                 and any("George Sisler" in line and "St. Louis Browns" in line
                         for line in announced["bench"])
                 and not any("Sammy Stewart" in line for line in announced["bullpen"]),
                 "Baltimore announced roster is synced and limits Sisler to Browns")
    check.expect("BAL|stewasa01" in cards,
                 "Original Sammy Stewart pitcher card remains historical")
    peaks = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["BAL"]
    sisler_peak = peaks.get("BAT2 George Sisler 1B (St. Louis Browns 1915-1927)") or {}
    check.expect(sisler_peak.get("lahman_id") == "sislege01"
                 and sisler_peak.get("years") == [1918, 1919, 1920, 1921, 1922]
                 and sisler_peak.get("status") == "ok"
                 and (sisler_peak.get("text") or "").startswith("Peak 162 with St. Louis Browns"),
                 "George Sisler's Browns-only 1918-1922 franchise peak is active")
    check.expect("LR/SP6 Sammy Stewart 8" not in peaks,
                 "Inactive Sammy Stewart removed from current Baltimore Peak 162")
    peak_builder = (ROOT / "scripts" / "build_peak162.py").read_text(encoding="utf-8")
    check.expect('club == "BAL" and pid == "sislege01"' in peak_builder
                 and 'if 1915 <= year <= 1927' in peak_builder,
                 "Future Peak 162 rebuild limits Sisler to St. Louis Browns seasons")
    published = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("George Sisler (`sislege01`) joins Baltimore" in published,
                 "Baltimore owner approval appears in published roster")
    builder = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_orioles_roster_amendment(cards, rosters)" in builder,
                 "Future full rebuild retains approved Baltimore active 26")


def check_white_sox_roster_amendment(check: Check) -> None:
    """White Sox owner approval: Allen active and Locker archived."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["CWS"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["CWS"]["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26
                 and counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Chicago has 26 unique active players, 9/6/5/6")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Chicago active roles are sequential")
    allen = [p for p in players if p["id"] == "allendi01"]
    check.expect(len(allen) == 1 and allen[0]["group"] == "bench"
                 and allen[0]["kind"] == "hitter" and allen[0]["slot"] == 6
                 and allen[0]["pos"] == "1B",
                 "Dick Allen is the sixth Chicago bench hitter")
    check.expect("lockebo02" not in ids, "Bob Locker is not active")
    check.expect([p["id"] for p in players if p["group"] == "bullpen"]
                 == ["thigpbo01", "wilheho01", "jenksbo01",
                     "foulkke01", "marteda01", "cicoted01"],
                 "Chicago bullpen retains the six approved pitchers")
    check.expect(len(announced["bench"]) == 6 and len(announced["bullpen"]) == 6
                 and any("Dick Allen" in s for s in announced["bench"])
                 and not any("Bob Locker" in s for s in announced["bullpen"]),
                 "Owner Chicago source agrees with converted active 26")
    check.expect("CWS|lockebo02" in cards,
                 "Original Bob Locker pitcher card remains archived")
    peaks = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["CWS"]
    allen_peak = peaks.get("BAT2 Dick Allen 1B/DH (1972-1974)") or {}
    check.expect(allen_peak.get("lahman_id") == "allendi01"
                 and allen_peak.get("years") == [1972, 1973, 1974]
                 and allen_peak.get("status") == "ok",
                 "Dick Allen three-season White Sox-only Peak 162 is active")
    check.expect("MR2 Bob Locker" not in peaks,
                 "Inactive Bob Locker removed from current CWS Peak 162 display")
    roster_doc = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Dick Allen (`allendi01`) joins Chicago" in roster_doc,
                 "Chicago owner change appears in published roster")
    builder = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_white_sox_roster_amendment(cards, rosters)" in builder,
                 "Chicago change survives future full rebuilds")


def check_twins_roster_amendment(check: Check) -> None:
    """Owner-approved Bob Allison for Firpo Marberry active Minnesota 26."""
    rosters = json.loads((ROOT / "data" / "rosters.json").read_text(encoding="utf-8"))
    announced = json.loads((ROOT / "data" / "announced_rosters.json").read_text(encoding="utf-8"))["MIN"]
    cards = json.loads((ROOT / "data" / "cards.json").read_text(encoding="utf-8"))
    players = rosters["MIN"]["players"]
    ids = [p["id"] for p in players]
    groups = ("lineup", "bench", "rotation", "bullpen")
    counts = {g: sum(p["group"] == g for p in players) for g in groups}
    check.expect(len(players) == len(set(ids)) == 26 and
                 counts == {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6},
                 "Minnesota has 26 unique active players, 9/6/5/6")
    check.expect(all(sorted(p["slot"] for p in players if p["group"] == g)
                     == list(range(1, counts[g] + 1)) for g in groups),
                 "Minnesota active role slots are sequential")
    allison = [p for p in players if p["id"] == "allisbo01"]
    check.expect(len(allison) == 1 and allison[0]["group"] == "bench"
                 and allison[0]["slot"] == 6 and allison[0]["pos"] == "RF"
                 and allison[0]["kind"] == "hitter",
                 "Bob Allison is the Minnesota sixth active bench hitter")
    check.expect("marbefi01" not in ids,
                 "Firpo Marberry no longer occupies an active relief spot")
    relief_ids = [p["id"] for p in players if p["group"] == "bullpen"]
    check.expect(relief_ids == ["nathajo01", "worthal01", "aguilri01",
                                "duranjh01", "rogerta01", "perryji01"],
                 "Minnesota approved six bullpen pitchers stay in correct order")
    check.expect(len(announced["bench"]) == 6 and len(announced["bullpen"]) == 6
                 and any("Bob Allison" in line for line in announced["bench"])
                 and not any("Firpo Marberry" in line for line in announced["bullpen"]),
                 "Minnesota owner roster agrees with active 9/6/5/6")
    check.expect("MIN|marbefi01" in cards,
                 "Firpo Marberry historic converted pitching card is preserved")
    peaks = json.loads((ROOT / "data" / "peak162.json").read_text(encoding="utf-8"))["clubs"]["MIN"]
    allison_peak = peaks.get("BAT2 Bob Allison OF/1B 1958-1970 (13)") or {}
    check.expect(allison_peak.get("lahman_id") == "allisbo01"
                 and allison_peak.get("years") == [1963, 1964, 1965, 1966, 1967],
                 "Bob Allison's genuine Minnesota franchise five-season Peak 162 is active")
    check.expect("MR1 Firpo Marberry 1923-1932, 1936 (11)" not in peaks,
                 "Inactive Marberry no longer appears in Twins current Peak 162")
    doc = (ROOT / "ROSTERS.md").read_text(encoding="utf-8")
    check.expect("Bob Allison (`allisbo01`) joins Minnesota" in doc,
                 "Minnesota approval appears in published roster")
    builder = (ROOT / "scripts" / "build_cards.py").read_text(encoding="utf-8")
    check.expect("apply_twins_roster_amendment(cards, rosters)" in builder,
                 "Future full builds preserve approved Twins active 26")


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
    check_padres_roster_amendment(check)
    check_expos_roster_amendment(check)
    check_arizona_roster_amendment(check)
    check_rays_roster_amendment(check)
    check_nationals_roster_amendment(check)
    check_marlins_roster_amendment(check)
    check_yankees_roster_amendment(check)
    check_giants_roster_amendment(check)
    check_unique_player_roster_limit(check)
    check_tigers_roster_amendment(check)
    check_braves_roster_amendment(check)
    check_pirates_roster_amendment(check)
    check_phillies_roster_amendment(check)
    check_twins_roster_amendment(check)
    check_white_sox_roster_amendment(check)
    check_orioles_roster_amendment(check)
    check_astros_roster_amendment(check)
    check_kansas_city_roster_amendment(check)
    check_seattle_roster_amendment(check)
    check_angels_roster_amendment(check)
    check_mets_roster_amendment(check)
    check_oakland_roster_amendment(check)
    check_milwaukee_roster_amendment(check)
    check_texas_roster_amendment(check)
    check_toronto_roster_amendment(check)
    check_colorado_roster_amendment(check)
    check_card_partitions(check)
    return check.done()


if __name__ == "__main__":
    sys.exit(main())
