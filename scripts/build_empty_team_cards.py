#!/usr/bin/env python3
"""Build franchise cards for the first empty-team batch.

Baltimore, Cleveland, the White Sox, and Houston. Hitters are the five
best franchise seasons by one-decimal league OPS+, among seasons of at
least 300 plate appearances (AB + BB + HBP + SF). Pitchers are the five
franchise seasons with the best one-decimal ERA+ times innings, among
seasons of at least 100 innings for a rotation spot and 30 for a
bullpen spot. A tie between the fifth and sixth season stops the build.

A 2026 line is added only from the MLB Stats API snapshot in
historical-cards/sources/mlb_2026_batch.json. Lahman in this repo stops
at 2025. No counting stat is invented. Fielding stays the engine
Average default. Pitcher stamina and the set-file addenda stay empty.
"""
from __future__ import annotations

import json
import os
import sys
import tarfile
from collections import defaultdict
from decimal import Decimal

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "engines", "hitter-v0.5"))
sys.path.insert(0, os.path.join(ROOT, "engines", "pitcher-v0.2.3"))

import build_cards  # noqa: E402
import build_missing_hitters as miss  # noqa: E402
import build_peak162 as peak  # noqa: E402
import hitter_solver as hs  # noqa: E402
from calibration import full_pipeline  # noqa: E402
from historical_solver import solve_historical  # noqa: E402
from partition import validate_hitter_card, validate_pitcher_table  # noqa: E402

CARDS = os.path.join(ROOT, "data", "cards.json")
ROSTERS = os.path.join(ROOT, "data", "rosters.json")
ANNOUNCED = os.path.join(ROOT, "data", "announced_rosters.json")
PEAK_PATH = os.path.join(ROOT, "data", "peak162.json")
RESULTS = os.path.join(ROOT, "tournament_results.json")
SIDECAR = os.path.join(ROOT, "historical-cards", "sources", "mlb_2026_batch.json")
REPORT = os.path.join(ROOT, "historical-cards", "accuracy", "empty_teams_batch.json")

CODES = ("BAL", "CLE", "CWS", "HOU")
FRANCHISE = {
    "ARI": ["ARI"],
    "ATL": ["BSN", "ML1", "ATL"],
    "BAL": ["MLA", "SLA", "BAL"],
    "BOS": ["BOS"],
    "CLE": ["CLE"],
    "COL": ["COL"],
    "CWS": ["CHA"],
    "HOU": ["HOU"],
    "MON": ["MON"],
    "PHA": ["PHA"],
    "TEX": ["WS2", "TEX"],
}
BOUNDS = {"PHA": (1901, 1954), "MON": (1969, 2004)}
TEAM_LINE = {
    "BAL": "Baltimore Orioles",
    "CLE": "Cleveland Guardians",
    "CWS": "Chicago White Sox",
    "HOU": "Houston Astros",
}
PITCH_FIELDS = {
    "W": "W", "L": "L", "G": "G", "GS": "GS", "SV": "SV", "H": "H", "R": "R",
    "ER": "ER", "HR": "HR", "BB": "BB", "SO": "SO", "HBP": "HBP", "BFP": "BFP",
    "IPouts": "IPouts",
}
# A null in one of these on a ranked season is a hole. HBP and R may be
# unrecorded; those are stored as zero and named in the report.
PITCH_STRICT = ("W", "L", "G", "GS", "SV", "H", "ER", "HR", "BB", "SO", "IPouts", "BFP")
PITCH_CHECKS = (
    "ARI|johnsra05",
    "ARI|schilcu01",
    "ATL|maddugr01",
    "BOS|clemero02",
    "PHA|grovele01",
    "COL|freelky01",
    "TEX|ryanno01",
    "MON|martipe02",
)
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
SOURCE = (
    "MLB Stats API, retrieved 2026-10-27. "
    "https://statsapi.mlb.com/api/v1/people/{mlb_id}/stats"
    "?stats=season&season=2026&group={group}&sportId=1"
)


def dump_text(obj):
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def write_json(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(dump_text(obj))


def fold(text):
    return peak.norm_name(text) if hasattr(peak, "norm_name") else " ".join(
        (text or "").split()).casefold()


def last_name(text):
    parts = fold(text).split()
    while parts and parts[-1] in SUFFIXES:
        parts.pop()
    return parts[-1] if parts else ""


def is_name_start(token):
    import re
    if re.match(r"^[A-Z](?:\.[A-Z]\.?)+$", token):
        return True
    if token in {"DJ", "AJ", "JJ"}:
        return True
    if "/" in token or any(ch.isdigit() for ch in token):
        return False
    return any(ch.islower() or "\u00e0" <= ch <= "\u00ff" for ch in token)


def parse_line(line):
    import re
    pos_re = re.compile(
        r"^(?:C|1B|2B|3B|SS|LF|CF|RF|DH|OF|IF|SP|RP|P|UT|INF|CI|MI|PH)"
        r"(?:/(?:C|1B|2B|3B|SS|LF|CF|RF|DH|OF|IF|SP|RP|P|UT|INF|CI|MI|PH|"
        r"Bat|Power|Utility|PR|DEF))*$", re.I)
    tokens = line.split()
    index = 0
    while index < len(tokens) and not is_name_start(tokens[index]):
        index += 1
    slot_token = " ".join(tokens[:index])
    rest = tokens[index:]
    cleaned = []
    depth = 0
    for token in rest:
        if "(" in token:
            depth += token.count("(")
        if depth:
            depth -= token.count(")")
            if depth < 0:
                depth = 0
            continue
        cleaned.append(token)
    rest = cleaned
    while len(rest) > 1 and (re.match(r"^\(?\d+\)?$", rest[-1]) or re.match(r"^[LRS]$", rest[-1])):
        rest.pop()
    pos = ""
    if len(rest) > 1 and pos_re.match(rest[-1]):
        pos = rest.pop().upper()
        while len(rest) > 1 and (re.match(r"^\(?\d+\)?$", rest[-1]) or re.match(r"^[LRS]$", rest[-1])):
            rest.pop()
    return slot_token, " ".join(rest), pos


def card_pos(group, slot_token, parsed):
    if group == "rotation":
        return "SP"
    if group == "bullpen":
        return "RP"
    if parsed:
        token = parsed.split("/")[0]
        return {"INF": "IF", "UT": "UT"}.get(token, token)
    prefix = slot_token.upper()
    if prefix.startswith("C"):
        return "C"
    if prefix.startswith("OF"):
        return "OF"
    if prefix.startswith("IF"):
        return "IF"
    if prefix.startswith("UTIL") or prefix.startswith("UT"):
        return "UT"
    if prefix.startswith("BAT"):
        return "PH"
    return "UT"


def load_players():
    announced = json.loads(open(ANNOUNCED, encoding="utf-8").read())
    book = json.loads(open(PEAK_PATH, encoding="utf-8").read())["clubs"]
    players = []
    for code in CODES:
        block = announced[code]
        for group in ("lineup", "bench", "rotation", "bullpen"):
            for slot, line in enumerate(block[group], start=1):
                slot_token, name, parsed = parse_line(line)
                info = book[code].get(line)
                if not info or info.get("status") != "ok" or not info.get("lahman_id"):
                    raise SystemExit("no peak id for %s %s" % (code, line))
                number = int(slot_token) if group == "lineup" and slot_token.isdigit() else slot
                kind = "pitcher" if group in ("rotation", "bullpen") else "hitter"
                players.append({
                    "team": code,
                    "group": group,
                    "slot": number,
                    "pos": card_pos(group, slot_token, parsed),
                    "kind": kind,
                    "name": name,
                    "id": info["lahman_id"],
                    "key": "%s|%s" % (code, info["lahman_id"]),
                    "line": line,
                    "manager": block.get("manager") or "",
                })
    keys = [player["key"] for player in players]
    if len(players) != 104 or len(set(keys)) != 104:
        raise SystemExit("expected 104 distinct cards, found %d (%d keys)" % (
            len(players), len(set(keys))))
    return players


def column(frame, name):
    if name not in frame.columns:
        raise SystemExit("Lahman table is missing %s" % name)
    return frame[name].tolist()


def load_lahman():
    path = peak.lahman_path()
    with tarfile.open(path) as tar:
        batting = peak.load_table(tar, "Batting")
        pitching = peak.load_table(tar, "Pitching")
        teams = peak.load_table(tar, "Teams")
        people = peak.load_table(tar, "People")
    return batting, pitching, teams, people


def people_index(people):
    ids = [str(value) for value in column(people, "playerID")]
    bats = [peak.blank(value) for value in column(people, "bats")]
    throws = [peak.blank(value) for value in column(people, "throws")]
    first = [peak.blank(value) for value in column(people, "nameFirst")]
    last = [peak.blank(value) for value in column(people, "nameLast")]
    found = {}
    for index, pid in enumerate(ids):
        found[pid] = {
            "bats": bats[index].upper(),
            "throws": throws[index].upper(),
            "name": (first[index] + " " + last[index]).strip(),
        }
    return found


def install_team_games(teams):
    ids = [peak.blank(value) for value in column(teams, "teamID")]
    years = [peak.as_int(value) for value in column(teams, "yearID")]
    games = [peak.as_int(value) for value in column(teams, "G")]
    cache = {}
    for index, team_id in enumerate(ids):
        if years[index] and games[index]:
            cache[(team_id, years[index])] = games[index]
    build_cards._team_games_cache = cache
    for code, members in FRANCHISE.items():
        build_cards.TEAM_IDS[code] = list(members)


def league_era(teams):
    years = [peak.as_int(value) for value in column(teams, "yearID")]
    leagues = [peak.blank(value) for value in column(teams, "lgID")]
    earned = [peak.as_int(value) for value in column(teams, "ER")]
    outs = [peak.as_int(value) for value in column(teams, "IPouts")]
    raw = {}
    for index, year in enumerate(years):
        bucket = raw.setdefault((year, leagues[index]), {"er": 0, "outs": 0})
        bucket["er"] += earned[index]
        bucket["outs"] += outs[index]
    return raw


def collect_pitching(pitching, wanted):
    ids = [str(value) for value in column(pitching, "playerID")]
    years = [peak.as_int(value) for value in column(pitching, "yearID")]
    teams = [peak.blank(value) for value in column(pitching, "teamID")]
    leagues = [peak.blank(value) for value in column(pitching, "lgID")]
    raw = {name: column(pitching, source) for name, source in PITCH_FIELDS.items()}
    by_player = {pid: [] for pid in wanted}
    max_year = 0
    for index, pid in enumerate(ids):
        max_year = max(max_year, years[index])
        if pid not in by_player:
            continue
        counted = {}
        nulls = []
        for name in PITCH_FIELDS:
            value, missing = miss.cell(raw[name][index])
            counted[name] = value
            if missing:
                nulls.append(name)
        by_player[pid].append({
            "year": years[index],
            "team": teams[index],
            "lg": leagues[index],
            "line": counted,
            "nulls": nulls,
        })
    return by_player, max_year


def hands_of(person, key):
    bats = person["bats"][:1]
    throws = person["throws"][:1]
    if bats == "S":
        bats = "B"
    if bats not in {"L", "R", "B"} or throws not in {"L", "R"}:
        raise SystemExit("%s hands %s/%s are not L, R, or B" % (
            key, person["bats"], person["throws"]))
    return bats, throws


def era_plus(year, stints, rates):
    leagues = {}
    for row in stints:
        if not row["lg"]:
            return None
        bucket = leagues.setdefault(row["lg"], {"outs": 0, "er": 0})
        bucket["outs"] += row["line"]["IPouts"]
        bucket["er"] += row["line"]["ER"]
    total_outs = sum(bucket["outs"] for bucket in leagues.values())
    total_er = sum(bucket["er"] for bucket in leagues.values())
    if total_outs <= 0:
        return None
    weighted = Decimal(0)
    for league, bucket in leagues.items():
        rate = rates.get((year, league))
        if not rate or rate["outs"] <= 0 or rate["er"] <= 0:
            return None
        weighted += Decimal(bucket["outs"]) * Decimal(rate["er"]) / Decimal(rate["outs"])
    rank_er = Decimal("0.5") if total_er == 0 else Decimal(total_er)
    value = Decimal(100) * (weighted / Decimal(total_outs)) * Decimal(total_outs) / rank_er
    return miss.one_decimal(value)


def franchise_pitching(pid, code, rows, rates):
    allowed = set(FRANCHISE[code])
    lo, hi = BOUNDS.get(code, (0, 9999))
    grouped = {}
    others = {}
    for row in rows:
        if row["team"] in allowed and lo <= row["year"] <= hi:
            grouped.setdefault(row["year"], []).append(row)
        else:
            others.setdefault(row["year"], [])
            if row["team"] not in others[row["year"]]:
                others[row["year"]].append(row["team"])
    seasons = []
    for year in sorted(grouped):
        stints = grouped[year]
        total = {name: 0 for name in PITCH_FIELDS}
        nulls = []
        leagues = []
        teams = []
        blocked = False
        for row in stints:
            for name in total:
                total[name] += row["line"][name]
            for name in row["nulls"]:
                if name not in nulls:
                    nulls.append(name)
                if name in ("IPouts", "ER", "H", "BB", "SO", "HR"):
                    blocked = True
            if row["lg"] and row["lg"] not in leagues:
                leagues.append(row["lg"])
            if row["team"] not in teams:
                teams.append(row["team"])
        outs = total["IPouts"]
        ip = Decimal(outs) / Decimal(3)
        plus = None if blocked else era_plus(year, stints, rates)
        product = None if plus is None else plus * ip
        seasons.append({
            "year": year,
            "teams": teams,
            "leagues": leagues,
            "ip": ip,
            "outs": outs,
            "era_plus": plus,
            "product": product,
            "zero_er": total["ER"] == 0 and "ER" not in nulls and outs > 0,
            "nulls": nulls,
            "blocked": blocked,
            "other_clubs": others.get(year, []),
            "line": total,
            "source": "",
        })
    return seasons


def pitcher_pool(seasons, floor):
    rows = [row for row in seasons
            if row["product"] is not None and row["ip"] >= floor and not row["blocked"]]
    rows.sort(key=lambda row: (-row["product"], -row["ip"], row["year"]))
    return rows


def choose_pitcher(seasons, floor, label):
    rows = pitcher_pool(seasons, floor)
    if not rows:
        raise SystemExit("%s has no season of at least %s innings" % (label, floor))
    if len(rows) >= 6 and rows[4]["product"] == rows[5]["product"]:
        raise SystemExit("%s ties at %s between %s and %s" % (
            label, rows[4]["product"], rows[4]["year"], rows[5]["year"]))
    chosen = rows[:5]
    return tuple(sorted(row["year"] for row in chosen)), rows


def choose_hitter(seasons, label):
    rows = miss.qualifying(seasons)
    if not rows:
        raise SystemExit("%s has no season of at least 300 plate appearances" % label)
    if len(rows) >= 6 and rows[4]["ops_plus"] == rows[5]["ops_plus"]:
        raise SystemExit("%s ties at %s between %s and %s" % (
            label, rows[4]["ops_plus"], rows[4]["year"], rows[5]["year"]))
    chosen = rows[:5]
    return tuple(sorted(row["year"] for row in chosen)), rows


def assert_pitchers(cards, rosters, by_player, rates):
    for key in PITCH_CHECKS:
        code, pid = key.split("|", 1)
        spot = next(player for player in rosters[code]["players"] if player["id"] == pid)
        if spot["group"] != "rotation":
            raise SystemExit("%s is %s; the stored-window check expects a starter" % (
                key, spot["group"]))
        seasons = franchise_pitching(pid, code, by_player[pid], rates)
        chosen, _rows = choose_pitcher(seasons, Decimal(100), key)
        expected = tuple(cards[key]["peak_pit"]["window_years"])
        if chosen != expected:
            print(key, "got", list(chosen), "card", list(expected))
            for row in pitcher_pool(seasons, Decimal(100))[:8]:
                print(" ", row["year"], "ERA+", row["era_plus"], "IP", row["ip"], "product", row["product"])
            raise SystemExit("pitcher window check failed for " + key)
        print("check %s %s" % (key, list(chosen)))


def load_sidecar():
    side = json.loads(open(SIDECAR, encoding="utf-8").read())
    if side.get("season") != 2026 or side.get("retrieved") != "2026-10-27":
        raise SystemExit("2026 sidecar is not the 2026-10-27 MLB Stats API pull")
    if side.get("source") != "MLB Stats API":
        raise SystemExit("2026 sidecar source is not the MLB Stats API")
    return side


def rates_2026(side):
    labels = {103: "AL", 104: "NL"}
    hitting = {}
    pitching = {}
    counts = {}
    for row in side["teams"]:
        league = labels.get(row["league_id"])
        if league is None:
            raise SystemExit("unexpected 2026 league id %s" % row["league_id"])
        counts[league] = counts.get(league, 0) + 1
        hit = hitting.setdefault(league, {name: 0 for name in (
            "ab", "h", "doubles", "triples", "hr", "bb", "hbp", "sf")})
        for name in hit:
            hit[name] += int(row[name])
        pit = pitching.setdefault(league, {"er": 0, "outs": 0})
        pit["er"] += int(row["er"])
        pit["outs"] += int(row["outs"])
    if counts != {"AL": 15, "NL": 15}:
        raise SystemExit("2026 league team counts %s" % counts)
    rates = {}
    for league, hit in hitting.items():
        den = hit["ab"] + hit["bb"] + hit["hbp"] + hit["sf"]
        if den <= 0 or hit["ab"] <= 0 or pitching[league]["outs"] <= 0:
            raise SystemExit("2026 league totals are empty for " + league)
        rates[league] = {
            "obp": Decimal(hit["h"] + hit["bb"] + hit["hbp"]) / Decimal(den),
            "slg": Decimal(hit["h"] + hit["doubles"] + 2 * hit["triples"] + 3 * hit["hr"]) / Decimal(hit["ab"]),
            "er": pitching[league]["er"],
            "outs": pitching[league]["outs"],
        }
    return rates


def baseball_outs(text):
    whole, frac = str(text).split(".")
    if frac not in {"0", "1", "2"}:
        raise SystemExit("innings pitched %s is not a baseball third" % text)
    return int(whole) * 3 + int(frac)


def stat_int(stat, name):
    value = stat.get(name)
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        return None
    return int(value)


def hitter_2026(player, entry, rates):
    splits = [row for row in entry["groups"]["hitting"]
              if row["team_id"] == entry.get("franchise_team_id")]
    others = [row for row in entry["groups"]["hitting"]
              if row["team_id"] != entry.get("franchise_team_id")]
    if len(splits) != 1:
        return None, others
    stat = splits[0]["stat"]
    league = {103: "AL", 104: "NL"}.get(splits[0]["league_id"])
    names = {
        "G": "gamesPlayed", "AB": "atBats", "R": "runs", "H": "hits", "2B": "doubles",
        "3B": "triples", "HR": "homeRuns", "RBI": "rbi", "SB": "stolenBases",
        "CS": "caughtStealing", "BB": "baseOnBalls", "SO": "strikeOuts",
        "IBB": "intentionalWalks", "HBP": "hitByPitch", "SH": "sacBunts",
        "SF": "sacFlies", "GIDP": "groundIntoDoublePlay",
    }
    line = {}
    for key, remote in names.items():
        value = stat_int(stat, remote)
        if value is None:
            return None, others
        line[key] = value
    if stat.get("outs") not in (None,) and baseball_outs(stat.get("inningsPitched") or "0.0") != stat.get("outs"):
        pass
    pa = line["AB"] + line["BB"] + line["HBP"] + line["SF"]
    rate = rates.get(league)
    ops = None
    if rate and line["AB"] > 0 and pa > 0:
        obp = Decimal(line["H"] + line["BB"] + line["HBP"]) / Decimal(pa)
        slg = Decimal(line["H"] + line["2B"] + 2 * line["3B"] + 3 * line["HR"]) / Decimal(line["AB"])
        ops = miss.one_decimal(Decimal(100) * (obp / rate["obp"] + slg / rate["slg"] - 1))
    mlb_pa = stat.get("plateAppearances")
    season = {
        "year": 2026,
        "teams": [player["team"]],
        "leagues": [league] if league else [],
        "pa": pa,
        "pa_with_sh": pa + line["SH"],
        "ops_plus": ops,
        "nulls": [],
        "other_clubs": [row.get("team_name") or str(row["team_id"]) for row in others],
        "line": line,
        "source": SOURCE.format(mlb_id=entry["mlb_id"], group="hitting"),
        "mlb_pa": mlb_pa,
        "team_name": splits[0].get("team_name"),
    }
    return season, others


def pitcher_2026(player, entry, rates):
    splits = [row for row in entry["groups"]["pitching"]
              if row["team_id"] == entry.get("franchise_team_id")]
    others = [row for row in entry["groups"]["pitching"]
              if row["team_id"] != entry.get("franchise_team_id")]
    if len(splits) != 1:
        return None, others
    stat = splits[0]["stat"]
    league = {103: "AL", 104: "NL"}.get(splits[0]["league_id"])
    outs = stat_int(stat, "outs")
    printed = stat.get("inningsPitched")
    if outs is None or printed is None or baseball_outs(printed) != outs:
        return None, others
    names = {
        "W": "wins", "L": "losses", "G": "gamesPlayed", "GS": "gamesStarted",
        "SV": "saves", "H": "hits", "R": "runs", "ER": "earnedRuns", "HR": "homeRuns",
        "BB": "baseOnBalls", "SO": "strikeOuts", "HBP": "hitByPitch", "BFP": "battersFaced",
    }
    line = {"IPouts": outs}
    for key, remote in names.items():
        value = stat_int(stat, remote)
        if value is None:
            return None, others
        line[key] = value
    rate = rates.get(league) if league else None
    plus = None
    if rate and outs > 0 and rate["outs"] > 0 and rate["er"] > 0:
        rank_er = Decimal("0.5") if line["ER"] == 0 else Decimal(line["ER"])
        plus = miss.one_decimal(
            Decimal(100) * Decimal(rate["er"]) / Decimal(rate["outs"]) * Decimal(outs) / rank_er)
    ip = Decimal(outs) / Decimal(3)
    season = {
        "year": 2026,
        "teams": [player["team"]],
        "leagues": [league] if league else [],
        "ip": ip,
        "outs": outs,
        "era_plus": plus,
        "product": None if plus is None else plus * ip,
        "zero_er": line["ER"] == 0,
        "nulls": [],
        "blocked": plus is None,
        "other_clubs": [row.get("team_name") or str(row["team_id"]) for row in others],
        "line": line,
        "source": SOURCE.format(mlb_id=entry["mlb_id"], group="pitching"),
        "team_name": splits[0].get("team_name"),
    }
    return season, others


def attach_2026(players, side, hitter_seasons, pitcher_seasons, rates):
    ids = {side["mlb_team_ids"][code]: code for code in CODES}
    by_key = {}
    for raw in side["franchise_players"]:
        row = dict(raw)
        row["franchise_team_id"] = side["mlb_team_ids"][row["team"]]
        by_key[(row["team"], row["lahman_id"])] = row
    checks = {}
    for row in side["other_checks"]:
        row = dict(row)
        row["franchise_team_id"] = side["mlb_team_ids"][row["team"]]
        checks[(row["team"], row["lahman_id"])] = row
    if set(ids) != {110, 114, 145, 117}:
        raise SystemExit("sidecar team ids changed")
    for player in players:
        key = (player["team"], player["id"])
        seasons = hitter_seasons[player["key"]] if player["kind"] == "hitter" else pitcher_seasons[player["key"]]
        latest = max((row["year"] for row in seasons), default=0)
        entry = by_key.get(key)
        check = checks.get(key)
        note = None
        if entry and check:
            raise SystemExit("%s is both a roster match and an other-club check" % player["key"])
        if player["kind"] == "hitter" and entry:
            season, _others = hitter_2026(player, entry, rates)
            if season is None:
                raise SystemExit("%s 2026 hitting line is incomplete; it was not invented" % player["key"])
            if any(row["year"] == 2026 for row in seasons):
                raise SystemExit("%s already has a 2026 Lahman row" % player["key"])
            seasons.append(season)
            note = season
        elif player["kind"] == "pitcher" and entry:
            season, _others = pitcher_2026(player, entry, rates)
            if season is None:
                raise SystemExit("%s 2026 pitching line is incomplete; it was not invented" % player["key"])
            if any(row["year"] == 2026 for row in seasons):
                raise SystemExit("%s already has a 2026 Lahman row" % player["key"])
            seasons.append(season)
            note = season
        elif check:
            group = "hitting" if player["kind"] == "hitter" else "pitching"
            found = check["groups"][group]
            where = ", ".join(
                "%s %s" % (row.get("team_name"), row["stat"].get("plateAppearances") or row["stat"].get("inningsPitched"))
                for row in found) or "no %s split" % group
            note = {
                "source": SOURCE.format(mlb_id=check["mlb_id"], group=group),
                "where": where,
                "mlb_id": check["mlb_id"],
                "absent": True,
            }
        elif latest >= 2024:
            raise SystemExit(
                "%s last franchise season is %s and the 2026 pull has neither a "
                "roster match nor an explicit check" % (player["key"], latest))
        player["y2026"] = note
        player["latest"] = latest


def sum_hitter(seasons, years, team_line):
    chosen = [row for row in seasons if row["year"] in years]
    if len(chosen) != len(years):
        raise SystemExit("window seasons missing: %s" % (years,))
    total = {name: 0 for name in chosen[0]["line"]}
    nulls = []
    for row in chosen:
        for name in miss.STRICT:
            if name in row["nulls"]:
                raise SystemExit("%s %s is null" % (row["year"], name))
        for name in total:
            total[name] += row["line"][name]
        for name in row["nulls"]:
            nulls.append({"year": row["year"], "field": name})
    pa = total["AB"] + total["BB"] + total["HBP"] + total["SF"]
    block = {
        "G": total["G"], "PA": pa, "AB": total["AB"], "R": total["R"], "H": total["H"],
        "2B": total["2B"], "3B": total["3B"], "HR": total["HR"], "RBI": total["RBI"],
        "BB": total["BB"], "IBB": total["IBB"], "SO": total["SO"], "HBP": total["HBP"],
        "SB": total["SB"], "CS": total["CS"], "GIDP": total["GIDP"], "SF": total["SF"],
        "window_years": list(years), "team_line": team_line,
    }
    return block, nulls


def ip_string(outs):
    whole, rem = divmod(int(outs), 3)
    text = "%d%s" % (whole, {0: ".0", 1: ".3333", 2: ".6667"}[rem])
    if round(float(text) * 3) != int(outs):
        raise SystemExit("IP text %s does not recover %s outs" % (text, outs))
    return text


def sum_pitcher(seasons, years, team_line):
    chosen = [row for row in seasons if row["year"] in years]
    if len(chosen) != len(years):
        raise SystemExit("window seasons missing: %s" % (years,))
    total = {name: 0 for name in PITCH_FIELDS}
    nulls = []
    for row in chosen:
        for name in PITCH_STRICT:
            if name in row["nulls"]:
                raise SystemExit("%s %s is null" % (row["year"], name))
        for name in total:
            total[name] += row["line"][name]
        for name in row["nulls"]:
            nulls.append({"year": row["year"], "field": name})
    block = {
        "window_years": list(years),
        "team_line": team_line,
        "w": total["W"], "l": total["L"], "g": total["G"], "gs": total["GS"],
        "sv": total["SV"], "ip": ip_string(total["IPouts"]), "h": total["H"],
        "r": total["R"], "er": total["ER"], "hr": total["HR"], "bb": total["BB"],
        "so": total["SO"], "hbp": total["HBP"], "bf": total["BFP"],
    }
    return block, nulls, total


def hitter_flags(player, seasons, ranked, years, nulls, real, card, status, reason, solved):
    flags = [
        "Fielding, arm, double-play, and sac bunt are the engine defaults "
        "(Average, range C, error 4, arm 6, DP 7, sac F), not a measured label.",
        "Steal and run come from the solver's SB, CS, and triple formula.",
    ]
    if player["bats"] == "B":
        flags.append(
            "Switch hitter. The solver stands him opposite the pitcher and "
            "uses the 0.28 left-handed / 0.72 right-handed park mix.")
    if len(ranked) >= 6:
        gap = ranked[4]["ops_plus"] - ranked[5]["ops_plus"]
        if gap <= Decimal("0.2"):
            flags.append("%s is last at OPS+ %s. %s is next at %s, %s behind." % (
                ranked[4]["year"], ranked[4]["ops_plus"], ranked[5]["year"],
                ranked[5]["ops_plus"], gap))
    fifth = ranked[min(4, len(ranked) - 1)]["ops_plus"]
    for row in seasons:
        if row["year"] in years:
            if row["other_clubs"]:
                flags.append("%s also has a %s stint. Only the %s line is in the window." % (
                    row["year"], ", ".join(row["other_clubs"]), player["team"]))
            continue
        if row["pa"] < miss.PA_FLOOR and row["ops_plus"] is not None and row["ops_plus"] >= fifth:
            flags.append("%s has %d plate appearances and OPS+ %s. The 300 floor leaves it out, and that OPS+ would rank inside the five." % (
                row["year"], row["pa"], row["ops_plus"]))
        elif row["pa"] >= 250 and row["pa"] < miss.PA_FLOOR:
            ops = "n/a" if row["ops_plus"] is None else str(row["ops_plus"])
            flags.append("%s has %d plate appearances, under the 300 floor. OPS+ %s." % (
                row["year"], row["pa"], ops))
        if row["pa"] < miss.PA_FLOOR <= row["pa_with_sh"]:
            flags.append("%s crosses 300 plate appearances only when sacrifice hits are counted (%d without, %d with)." % (
                row["year"], row["pa"], row["pa_with_sh"]))
    if len(years) < 5:
        flags.append("Only %d franchise seasons reach 300 plate appearances. The window is short." % len(years))
    if nulls:
        grouped = {}
        for item in nulls:
            grouped.setdefault(item["field"], []).append(item["year"])
        flags.append("Lahman nulls treated as zero: " + "; ".join(
            "%s %s" % (field, grouped[field]) for field in sorted(grouped)))
    note = player.get("y2026")
    if isinstance(note, dict) and note.get("year") == 2026:
        included = 2026 in years
        flags.append(
            "2026 %s is %s. Plate appearances are %d from AB+BB+HBP+SF"
            "%s. OPS+ %s. Source: %s. Team split: %s." % (
                "included" if included else "not included",
                "inside the five" if included else "outside the five or under the floor",
                note["pa"],
                "" if note.get("mlb_pa") in (None, note["pa"]) else
                "; MLB plateAppearances is %s and the difference was not added" % note["mlb_pa"],
                note["ops_plus"], note["source"], note.get("team_name")))
    elif isinstance(note, dict) and note.get("absent"):
        flags.append("No 2026 %s line is on the card. %s Returned %s. MLB id %s." % (
            player["team"], note["source"], note["where"], note["mlb_id"]))
    gaps = {
        "avg": card["avg"] - real["avg"],
        "obp_real": card["obp"] - real["obp"],
        "obp_ubb": card["obp"] - real["obp_ubb"],
        "slg": card["slg"] - real["slg"],
        "1b": card["1b"] - real["1b"],
        "2b": card["2b"] - real["2b"],
        "3b": card["3b"] - real["3b"],
        "hr": card["hr"] - real["hr"],
        "so": card["so"] - real["so"],
    }
    if abs(gaps["avg"]) > 0.010:
        flags.append("AVG is %.3f off the real window." % gaps["avg"])
    if abs(gaps["slg"]) > 0.020:
        flags.append("SLG is %.3f off the real window." % gaps["slg"])
    if abs(gaps["obp_ubb"]) > 0.010:
        flags.append("OBP is %.3f off the unintentional-walk target." % gaps["obp_ubb"])
    for label, limit in (("1b", 0.008), ("2b", 0.008), ("3b", 0.008), ("hr", 0.008), ("so", 0.008)):
        if abs(gaps[label]) > limit:
            flags.append("%s per PA is %.4f off the real window." % (label.upper(), gaps[label]))
    if status == "ARCHITECTURE-LIMITED":
        flags.append("QA status ARCHITECTURE-LIMITED. The shipped card is the solver's best legal card and sits just outside the tight slash tolerance. %s" % reason)
    elif status != "PASS":
        flags.append("QA status %s. %s" % (status, reason))
    ceiling = miss.hr_ceiling(solved["sections"])
    if ceiling:
        flags.append("Wheelhouse HR is 1-99 versus %s." % ", ".join(ceiling))
    if solved["run"] >= 10:
        flags.append("Run is 10, the formula's cap.")
    return flags, gaps


def pitcher_flags(player, seasons, ranked, years, floor, nulls, raw, target, played, status):
    flags = [
        "Stamina, wild pitch, double play, hold, pickoff, and injury are empty. "
        "There is no set-file addendum and no rulebook formula for them in the repo.",
        "The chart is fit to the 1986-calibrated target. The comparison below also shows the raw batters-faced rates.",
    ]
    other = Decimal(100) if floor == Decimal(30) else Decimal(30)
    other_years = tuple(sorted(row["year"] for row in pitcher_pool(seasons, other)[:5]))
    if other_years != years:
        flags.append("The %s-inning floor gives %s. The other floor (%s innings) would give %s." % (
            floor, list(years), other, list(other_years)))
    if len(ranked) >= 6:
        gap = ranked[4]["product"] - ranked[5]["product"]
        if gap <= Decimal("1"):
            flags.append("%s is last at ERA+×IP %s. %s is next at %s." % (
                ranked[4]["year"], ranked[4]["product"], ranked[5]["year"], ranked[5]["product"]))
    cutoff = ranked[min(4, len(ranked) - 1)]["product"]
    for row in seasons:
        if row["year"] in years:
            if row["zero_er"]:
                flags.append("%s allowed 0 earned runs. It is ranked as half a run. The printed ER stays 0." % row["year"])
            if row["other_clubs"]:
                flags.append("%s also has a %s stint. Only the %s line is in the window." % (
                    row["year"], ", ".join(row["other_clubs"]), player["team"]))
            continue
        if row["product"] is None:
            continue
        if row["ip"] < floor and row["product"] >= cutoff:
            flags.append("%s has %s innings, under the %s floor, and ERA+×IP %s would rank inside the five." % (
                row["year"], row["ip"], floor, row["product"]))
        elif floor - Decimal(10) <= row["ip"] < floor:
            flags.append("%s has %s innings, under the %s floor. ERA+×IP %s." % (
                row["year"], row["ip"], floor, row["product"]))
    if len(years) < 5:
        flags.append("Only %d franchise seasons reach the %s-inning floor. The window is short." % (
            len(years), floor))
    if nulls:
        grouped = {}
        for item in nulls:
            grouped.setdefault(item["field"], []).append(item["year"])
        flags.append("Lahman nulls treated as zero: " + "; ".join(
            "%s %s" % (field, grouped[field]) for field in sorted(grouped)))
    starts = sum(row["line"]["GS"] for row in seasons)
    games = sum(row["line"]["G"] for row in seasons)
    if player["group"] == "bullpen" and starts >= 80 and starts * 2 > games:
        flags.append(
            "The roster lists him in the bullpen. Franchise seasons show %d starts in %d games. "
            "The card uses the 30-inning relief floor because that is the roster group." % (starts, games))
    note = player.get("y2026")
    if isinstance(note, dict) and note.get("year") == 2026:
        flags.append(
            "2026 %s. %s IP, ERA+ %s, product %s. Source: %s. Team split: %s." % (
                "included" if 2026 in years else "not included",
                note["ip"], note["era_plus"], note["product"], note["source"], note.get("team_name")))
    elif isinstance(note, dict) and note.get("absent"):
        flags.append("No 2026 %s line is on the card. %s Returned %s. MLB id %s." % (
            player["team"], note["source"], note["where"], note["mlb_id"]))
    limits = {"so_bf": Decimal("0.010"), "bb_bf": Decimal("0.010"), "hr_bf": Decimal("0.005"), "h_bf": Decimal("0.020")}
    for key, limit in limits.items():
        gap = Decimal(str(played[key])) - Decimal(str(target[key]))
        if abs(gap) > limit:
            flags.append("Versus the calibrated target, %s is %+.4f." % (key, gap))
    if "REVIEW" in (status or ""):
        flags.append(status)
    return flags


def round_rate(block):
    return {key: round(value, 4) for key, value in block.items()}


def solve_hitter(player, block):
    row = {
        "Name": player["name"], "Team": TEAM_LINE[player["team"]],
        "Bats": player["bats"], "Throws": player["throws"], "Position": player["pos"],
        "Fielding": "average", "Arm": "average",
        "PA": block["PA"], "AB": block["AB"], "H": block["H"], "2B": block["2B"],
        "3B": block["3B"], "HR": block["HR"], "BB": block["BB"], "IBB": block["IBB"],
        "SO": block["SO"], "HBP": block["HBP"], "SB": block["SB"], "CS": block["CS"],
    }
    built = hs.build_one(row)
    if built is None:
        raise SystemExit("solver skipped " + player["key"])
    solved, exp, tgt, _comp, _slug, actual_err, best_err, _diag = built
    rating = hs.ratings(row)
    chip = rating["positions"][0]
    if (chip["range"], chip["e"], chip["arm"], rating["dp"], rating["sac_bunt"]) != ("C", 4, 6, 7, "F"):
        raise SystemExit("engine fielding default changed")
    if solved["bats"] != player["bats"] or solved["run"] != rating["run"]:
        raise SystemExit("solver hands or run changed for " + player["key"])
    _lines, _fit, old_status = hs.fit_report(exp, tgt)
    status, reason = hs.classify_review(old_status == "PASS", actual_err, best_err)
    card_bat = {
        "arm": "Average", "bats": player["bats"], "dp": rating["dp"],
        "fielding": "Average", "out_table": solved["out_table"],
        "positions": [{"pos": player["pos"], "range": chip["range"], "e": chip["e"], "arm": chip["arm"]}],
        "qa_status": status, "run": rating["run"], "sac_bunt": rating["sac_bunt"],
        "sections": solved["sections"], "steal": rating["steal"], "throws": player["throws"],
    }
    problems = validate_hitter_card(card_bat, exact=False)
    if problems:
        raise SystemExit("%s partition: %s" % (player["key"], "; ".join(problems[:6])))
    return card_bat, exp, tgt, status, reason, actual_err, best_err, solved


def solve_pitcher(player, block):
    bf = float(block["bf"])
    if bf <= 0:
        raise SystemExit(player["key"] + " has no batters faced")
    years = block["window_years"]
    import statistics
    mid = int(round(statistics.median(years)))
    raw = {
        "h_bf": float(block["h"]) / bf,
        "bb_bf": float(block["bb"]) / bf,
        "so_bf": float(block["so"]) / bf,
        "hr_bf": float(block["hr"]) / bf,
        "hbp_bf": float(block["hbp"]) / bf,
    }
    target = full_pipeline(raw, mid)["solver_target"]
    result = solve_historical(
        target, player["throws"], restarts=8,
        seed=sum(ord(ch) for ch in player["key"]) % 100000, so_rule="printed")
    table = {str(slot): result["table"][str(slot)] for slot in range(2, 13)}
    problems = validate_pitcher_table(table)
    if problems:
        raise SystemExit("%s chart: %s" % (player["key"], "; ".join(problems)))
    card_pit = {
        "throws": player["throws"],
        "card_type": "SP" if player["group"] == "rotation" else "RP",
        "table_2d6": table,
        "so_modifier": result["so_modifier"],
        "special": result.get("special_required") or [],
        "qa_status": result["status"],
        "stamina": {"start": None, "relief": None},
        "addendum": {"wp": None, "dp": None, "hold": None, "pickoff": None, "inj": None},
    }
    return card_pit, raw, target, result["events"], result["status"], round(result["fit_error"], 4), mid


def season_brief(row, kind):
    if kind == "hitter":
        return {
            "year": row["year"], "pa": row["pa"],
            "ops_plus": None if row["ops_plus"] is None else str(row["ops_plus"]),
            "teams": row["teams"], "other_clubs": row["other_clubs"], "nulls": row["nulls"],
        }
    return {
        "year": row["year"], "ip": str(row["ip"]),
        "era_plus": None if row["era_plus"] is None else str(row["era_plus"]),
        "product": None if row["product"] is None else str(row["product"]),
        "teams": row["teams"], "other_clubs": row["other_clubs"], "nulls": row["nulls"],
        "zero_er": row["zero_er"],
    }


def duplicate_flags(players):
    announced = json.loads(open(ANNOUNCED, encoding="utf-8").read())
    book = json.loads(open(PEAK_PATH, encoding="utf-8").read())["clubs"]
    rosters = json.loads(open(ROSTERS, encoding="utf-8").read())
    owners = defaultdict(set)
    for code, block in announced.items():
        if not isinstance(block, dict):
            continue
        for group in ("lineup", "bench", "rotation", "bullpen"):
            for line in block.get(group) or []:
                info = (book.get(code) or {}).get(line) or {}
                if info.get("status") == "ok" and info.get("lahman_id"):
                    owners[info["lahman_id"]].add(code)
    for code, roster in rosters.items():
        for spot in roster.get("players") or []:
            owners[spot["id"]].add(code)
    found = []
    for player in players:
        clubs = sorted(owners[player["id"]])
        if len(clubs) < 2:
            continue
        text = (
            "%s is on %s. The same player on more than one club is intentional. "
            "This card uses %s franchise seasons only." % (
                player["name"], ", ".join(clubs), player["team"]))
        player.setdefault("shared_flags", []).append(text)
        found.append({"id": player["id"], "name": player["name"], "clubs": clubs, "card": player["key"]})
    return found


def roster_flags(player):
    flags = []
    if player["id"] == "biggicr01" and player["pos"] == "C":
        flags.append(
            "The roster lists Craig Biggio at C. His career was mostly at second base. "
            "The card keeps the owner's C label.")
    if player["name"] and player["manager"] and player["name"] in player["manager"]:
        flags.append(
            "%s is also the listed manager. That is the player-manager, one person, not two roster rows." % player["name"])
    if last_name(player["name"]) and last_name(player["lahman_name"]) and last_name(player["name"]) != last_name(player["lahman_name"]):
        flags.append("Roster name %s does not share a last name with Lahman %s (%s)." % (
            player["name"], player["lahman_name"], player["id"]))
    return flags


def proposals():
    return {
        "built": False,
        "reason": "Surname lines stay unbuilt until the full names are confirmed.",
        "NYY": [
            {"line": "1 Jeter SS", "proposal": "Derek Jeter", "note": "Yankees shortstop."},
            {"line": "2 Judge RF", "proposal": "Aaron Judge", "note": "Yankees right fielder."},
            {"line": "3 Ruth DH", "proposal": "Babe Ruth", "note": "George Herman Ruth."},
            {"line": "4 Gehrig 1B", "proposal": "Lou Gehrig", "note": "Yankees first baseman."},
            {"line": "5 Mantle LF", "proposal": "Mickey Mantle", "note": "Yankees left fielder on this line."},
            {"line": "6 DiMaggio CF", "proposal": "Joe DiMaggio", "note": "Not Dom or Vince."},
            {"line": "7 A. Rodriguez 3B", "proposal": "Alex Rodriguez", "note": "The line already says A. Rodriguez. Not Sean or Ivan."},
            {"line": "8 Berra C", "proposal": "Yogi Berra", "note": "Lawrence Berra."},
            {"line": "9 Randolph 2B", "proposal": "Willie Randolph", "note": "Yankees second baseman."},
            {"line": "Munson (C2)", "proposal": "Thurman Munson", "note": "Yankees catcher."},
            {"line": "Lazzeri (IF/BAT)", "proposal": "Tony Lazzeri", "note": "Yankees infielder."},
            {"line": "Mattingly (1B/BAT)", "proposal": "Don Mattingly", "note": "Yankees first baseman."},
            {"line": "B. Williams (OF)", "proposal": "Bernie Williams", "note": "Yankees center fielder. Billy Williams is the other famous B. Williams and was a Cub."},
            {"line": "R. Jackson (OF/BAT)", "proposal": "Reggie Jackson", "note": "Not Randy Jackson or Ron Jackson. The role is OF/BAT."},
            {"line": "Ford", "proposal": "Whitey Ford", "note": "Edward Ford."},
            {"line": "Ruffing", "proposal": "Red Ruffing", "note": "Charles Ruffing."},
            {"line": "Gomez", "proposal": "Lefty Gomez", "note": "Vernon Gomez. The rotation slot is the Yankees left-hander, not a later Gomez."},
            {"line": "Guidry", "proposal": "Ron Guidry", "note": "Yankees left-hander."},
            {"line": "Pettitte", "proposal": "Andy Pettitte", "note": "Yankees left-hander."},
            {"line": "Rivera (CL)", "proposal": "Mariano Rivera", "note": "Yankees closer."},
            {"line": "Gossage (FIRE)", "proposal": "Goose Gossage", "note": "Richard Gossage."},
            {"line": "Lyle (LH FIRE)", "proposal": "Sparky Lyle", "note": "Albert Lyle."},
            {"line": "Robertson (RH SET)", "proposal": "David Robertson", "note": "Yankees right-handed setup man. Nate Robertson was a Tigers starter and does not fit RH SET."},
            {"line": "Righetti (LATE/MULTI)", "proposal": "Dave Righetti", "note": "Yankees reliever."},
            {"line": "Stanton (LH SPEC)", "proposal": "Mike Stanton", "note": "The left-handed specialist. Giancarlo Stanton is also a Yankee, and he is a right-handed hitter, so he does not fit LH SPEC."},
            {"line": "Reynolds (LONG/SWING)", "proposal": "Allie Reynolds", "note": "Yankees swingman. Not Shane Reynolds or Mark Reynolds."},
        ],
        "MIA": [
            {"line": "1 Castillo 2B", "proposal": "Luis Castillo", "note": "The Marlins second baseman. Another Luis Castillo is the Reds and Mariners pitcher. The 2B slot is the infielder."},
            {"line": "2 Yelich CF", "proposal": "Christian Yelich", "note": "Marlins center fielder."},
            {"line": "3 Sheffield DH", "proposal": "Gary Sheffield", "note": "Marlins hitter."},
            {"line": "4 Stanton RF", "proposal": "Giancarlo Stanton", "note": "Marlins right fielder. Mike Stanton, the left-handed pitcher, is the other Stanton and is the Yankees bullpen proposal above."},
            {"line": "5 Cabrera 3B", "proposal": "Miguel Cabrera", "note": "Marlins third baseman. Not Asdrubal or Fernando."},
            {"line": "6 Ramirez SS", "proposal": "Hanley Ramirez", "note": "Marlins shortstop. Not Manny, Aramis, or Alex. Alex Rodriguez is the Yankees proposal."},
            {"line": "7 Floyd LF", "proposal": "Cliff Floyd", "note": "Marlins left fielder. Not Gavin Floyd."},
            {"line": "8 Conine 1B", "proposal": "Jeff Conine", "note": "Marlins first baseman."},
            {"line": "9 Realmuto C", "proposal": "J.T. Realmuto", "note": "Jacob Realmuto."},
            {"line": "C. Johnson (C2)", "proposal": "Charles Johnson", "note": "Marlins catcher. The line already says C. Johnson. Not Randy, Josh, or Kelly."},
            {"line": "Lopez (UTIL)", "proposal": "Javy Lopez", "note": "Javier Lopez, the catcher who played for the Marlins. Uncertain against other Lopezes. The UTIL role is not the pitcher Rodrigo Lopez."},
            {"line": "Uggla (INF/POWER)", "proposal": "Dan Uggla", "note": "Marlins infielder."},
            {"line": "Ozuna (OF4)", "proposal": "Marcell Ozuna", "note": "Marlins outfielder."},
            {"line": "Lee (1B/POWER)", "proposal": "Derrek Lee", "note": "The 1B/POWER role. Not Cliff Lee, the pitcher, and not Carlos Lee."},
            {"line": "Johnson", "proposal": "Randy Johnson", "note": "Rotation ace. Not Charles Johnson, who is the catcher proposal above, and not Josh Johnson."},
            {"line": "Alcantara", "proposal": "Sandy Alcantara", "note": "Marlins starter."},
            {"line": "Willis", "proposal": "Dontrelle Willis", "note": "Marlins left-hander."},
            {"line": "Beckett", "proposal": "Josh Beckett", "note": "Marlins starter."},
            {"line": "Fernandez", "proposal": "Jose Fernandez", "note": "Marlins starter. Not Sid Fernandez or Tony Fernandez."},
            {"line": "Nen (CL)", "proposal": "Robb Nen", "note": "Marlins closer."},
            {"line": "Cishek (SU)", "proposal": "Steve Cishek", "note": "Marlins reliever."},
            {"line": "Ramos (SU)", "proposal": "A.J. Ramos", "note": "Marlins setup man. Wilson Ramos is a catcher and does not fit SU."},
            {"line": "Scott (LH)", "proposal": "Uncertain", "note": "Tanner Scott is the Marlins left-handed reliever whose role fits LH. Mike Scott was an Astros starter and is already the Houston card in this batch. Do not lock this name."},
            {"line": "Bender (MR)", "proposal": "Uncertain", "note": "Anthony Bender pitched in relief for the Marlins. Chief Bender is the Athletics pitcher, already identified on the Philadelphia club. Do not lock this name."},
            {"line": "Alfonseca (MR)", "proposal": "Antonio Alfonseca", "note": "Marlins reliever."},
            {"line": "Burnett (LR/EMER SP)", "proposal": "A.J. Burnett", "note": "Marlins starter and reliever. Not Sean Burnett."},
        ],
    }


def main():
    players = load_players()
    print("roster", len(players), "hitters", sum(p["kind"] == "hitter" for p in players),
          "pitchers", sum(p["kind"] == "pitcher" for p in players))
    batting, pitching, teams, people = load_lahman()
    install_team_games(teams)
    hit_rates, team_max = miss.league_rates(teams)
    pit_rates = league_era(teams)
    persons = people_index(people)
    miss.FRANCHISE.update(FRANCHISE)
    cards = json.loads(open(CARDS, encoding="utf-8").read())
    if dump_text(cards) != open(CARDS, encoding="utf-8").read():
        raise SystemExit("cards.json does not round-trip")
    rosters = json.loads(open(ROSTERS, encoding="utf-8").read())
    check_ids = [key.split("|", 1)[1] for key in PITCH_CHECKS]
    check_ids.append("mazerbi01")
    for code, pid, _years in miss.CHECKS:
        check_ids.append(pid)
    by_bat, bat_max = miss.collect(batting, set(check_ids) | {p["id"] for p in players if p["kind"] == "hitter"})
    by_pit, pit_max = collect_pitching(pitching, set(check_ids) | {p["id"] for p in players if p["kind"] == "pitcher"})
    if bat_max != 2025 or pit_max != 2025 or team_max < 2025:
        raise SystemExit("Lahman span batting %s pitching %s teams %s" % (bat_max, pit_max, team_max))
    miss.assert_known(by_bat, hit_rates)
    assert_pitchers(cards, rosters, by_pit, pit_rates)
    side = load_sidecar()
    modern = rates_2026(side)
    hitter_seasons = {}
    pitcher_seasons = {}
    for player in players:
        person = persons.get(player["id"])
        if not person:
            raise SystemExit("no People row for " + player["key"])
        player["bats"], player["throws"] = hands_of(person, player["key"])
        player["lahman_name"] = person["name"]
        if player["kind"] == "hitter":
            seasons, _others = miss.franchise_seasons(player["id"], player["team"], by_bat[player["id"]], hit_rates)
            hitter_seasons[player["key"]] = seasons
        else:
            pitcher_seasons[player["key"]] = franchise_pitching(
                player["id"], player["team"], by_pit[player["id"]], pit_rates)
    attach_2026(players, side, hitter_seasons, pitcher_seasons, modern)
    shared = duplicate_flags(players)
    windows = []
    for player in players:
        if player["kind"] == "hitter":
            seasons = hitter_seasons[player["key"]]
            years, ranked = choose_hitter(seasons, player["key"])
            block, nulls = sum_hitter(seasons, years, TEAM_LINE[player["team"]])
            player.update(seasons=seasons, years=years, ranked=ranked, block=block, nulls=nulls)
        else:
            floor = Decimal(100) if player["group"] == "rotation" else Decimal(30)
            seasons = pitcher_seasons[player["key"]]
            years, ranked = choose_pitcher(seasons, floor, player["key"])
            block, nulls, _total = sum_pitcher(seasons, years, TEAM_LINE[player["team"]])
            player.update(seasons=seasons, years=years, ranked=ranked, block=block, nulls=nulls, floor=floor)
        mark = " 2026" if 2026 in player["years"] else ""
        print(player["key"], player["kind"], list(player["years"]), mark)
        windows.append({"key": player["key"], "years": list(player["years"])})
    if os.environ.get("PP_WINDOWS_ONLY") == "1":
        print("windows only; cards.json not written")
        print("shared", len(shared))
        return 0
    before = {key: json.dumps(value, sort_keys=True) for key, value in cards.items()}
    before_rosters = {key: json.dumps(value, sort_keys=True) for key, value in rosters.items()}
    reports = []
    for player in players:
        spot = {"group": player["group"], "kind": player["kind"], "pos": player["pos"], "slot": player["slot"]}
        extra = list(player.get("shared_flags") or []) + roster_flags(player)
        if player["kind"] == "hitter":
            card_bat, exp, tgt, status, reason, actual, best, solved = solve_hitter(player, player["block"])
            real = miss.rates_of(player["block"])
            played = miss.card_rates(exp)
            flags, gaps = hitter_flags(
                player, player["seasons"], player["ranked"], player["years"], player["nulls"],
                real, played, status, reason, solved)
            flags.extend(extra)
            scaled = build_cards.scale_bat_162(player["block"])
            entry = {
                "id": player["id"], "name": player["name"], "team": player["team"],
                "spots": [spot], "peak_bat": player["block"], "peak_bat_162": scaled,
                "peak_pit": None, "peak_pit_162": None, "card_bat": card_bat,
                "card_pit": None, "tournament": None,
            }
            report = {
                "key": player["key"], "name": player["name"], "team": player["team"],
                "kind": "hitter", "window_years": list(player["years"]), "qa_status": status,
                "fit_error": round(actual, 4), "best_possible": round(best, 4),
                "counting": {key: player["block"][key] for key in build_cards.BAT_COUNTING},
                "real": miss.round_rates(real), "card": miss.round_rates(played),
                "delta": {key: round(value, 4) for key, value in gaps.items()},
                "nulls": player["nulls"], "flags": flags,
                "seasons": [season_brief(row, "hitter") for row in player["seasons"]],
            }
            print("%s %s AVG %+.4f SLG %+.4f" % (player["key"], status, gaps["avg"], gaps["slg"]))
        else:
            card_pit, raw, target, played, status, fit_error, mid = solve_pitcher(player, player["block"])
            notes = []
            scaled = build_cards.scale_pit_162(player["team"], player["name"], player["block"], notes)
            flags = pitcher_flags(
                player, player["seasons"], player["ranked"], player["years"], player["floor"],
                player["nulls"], raw, target, played, status)
            flags.extend(notes)
            flags.extend(extra)
            entry = {
                "id": player["id"], "name": player["name"], "team": player["team"],
                "spots": [spot], "peak_bat": None, "peak_bat_162": None,
                "peak_pit": player["block"], "peak_pit_162": scaled,
                "card_bat": None, "card_pit": card_pit, "tournament": None,
            }
            report = {
                "key": player["key"], "name": player["name"], "team": player["team"],
                "kind": "pitcher", "window_years": list(player["years"]), "qa_status": status,
                "fit_error": fit_error, "calibration_year": mid,
                "counting": {key: player["block"][key] for key in (
                    "w", "l", "g", "gs", "sv", "ip", "h", "r", "er", "hr", "bb", "so", "hbp", "bf")},
                "raw": round_rate(raw), "target": round_rate(target), "card": round_rate(played),
                "delta_target": {key: round(played[key] - target[key], 4) for key in raw},
                "delta_raw": {key: round(played[key] - raw[key], 4) for key in raw},
                "nulls": player["nulls"], "flags": flags,
                "seasons": [season_brief(row, "pitcher") for row in player["seasons"]],
            }
            print("%s %s SO %+.4f BB %+.4f" % (
                player["key"], status, report["delta_target"]["so_bf"], report["delta_target"]["bb_bf"]))
        cards[player["key"]] = entry
        reports.append(report)
    results = json.loads(open(RESULTS, encoding="utf-8").read())
    by_code = {team["code"]: team for team in results["teams"]}
    for code in CODES:
        team = by_code[code]
        roster_players = [{
            "group": player["group"], "id": player["id"], "kind": player["kind"],
            "name": player["name"], "pos": player["pos"], "slot": player["slot"],
        } for player in players if player["team"] == code]
        if len(roster_players) != 26 or len({row["id"] for row in roster_players}) != 26:
            raise SystemExit("%s roster is not 26 distinct players" % code)
        rosters[code] = {
            "code": code,
            "name": team["name"],
            "played": bool(team["game_wins"] or team["game_losses"]),
            "players": roster_players,
            "seed": team["seed"],
        }
        if rosters[code]["played"]:
            raise SystemExit(code + " already has a played game; this batch does not touch results")
    after = {key: json.dumps(value, sort_keys=True) for key, value in cards.items()}
    changed = sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))
    expected = sorted(player["key"] for player in players)
    if changed != expected:
        raise SystemExit("card key mismatch %s" % [key for key in changed if key not in expected][:8])
    for code, text in before_rosters.items():
        if json.dumps(rosters[code], sort_keys=True) != text:
            raise SystemExit("existing roster changed: " + code)
    write_json(cards, CARDS)
    write_json(rosters, ROSTERS)
    hit_rows = [row for row in reports if row["kind"] == "hitter"]
    pit_rows = [row for row in reports if row["kind"] == "pitcher"]

    def mae(rows, block, baseline, key):
        gaps = [abs(row[block][key] - row[baseline][key]) for row in rows]
        return round(sum(gaps) / len(gaps), 4)

    summary = {
        "teams": list(CODES),
        "cards": len(reports),
        "hitters": len(hit_rows),
        "pitchers": len(pit_rows),
        "lahman_max_year": bat_max,
        "lahman_sha256": peak.LAHMAN_SHA256,
        "source_2026": SIDECAR,
        "hitter_mae": {
            "avg": mae(hit_rows, "card", "real", "avg"),
            "obp_ubb": round(sum(abs(row["delta"]["obp_ubb"]) for row in hit_rows) / len(hit_rows), 4),
            "slg": mae(hit_rows, "card", "real", "slg"),
        },
        "pitcher_mae_vs_target": {
            key: mae(pit_rows, "card", "target", key) for key in ("so_bf", "bb_bf", "hr_bf", "h_bf")
        },
        "included_2026": [row["key"] for row in reports if 2026 in row["window_years"]],
        "duplicates": shared,
        "roster_shape": {
            code: {
                group: sum(player["team"] == code and player["group"] == group for player in players)
                for group in ("lineup", "bench", "rotation", "bullpen")
            } for code in CODES
        },
    }
    write_json({
        "summary": summary,
        "players": reports,
        "not_built": proposals(),
        "window_rule": {
            "hitters": "five best franchise seasons by league OPS+ rounded half up to one decimal, no park factor, PA>=300 where PA=AB+BB+HBP+SF",
            "pitchers": "five best franchise seasons by one-decimal ERA+ times IP, rotation floor 100 IP, bullpen floor 30 IP, no park factor",
            "2026": "MLB Stats API snapshot retrieved 2026-10-27; a line counts only for the franchise team split",
        },
    }, REPORT)
    print("wrote", REPORT)
    print("2026 in window", summary["included_2026"])
    print("hitter MAE", summary["hitter_mae"])
    print("pitcher MAE", summary["pitcher_mae_vs_target"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
