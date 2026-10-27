#!/usr/bin/env python3
"""Build the five franchise hitter cards the set files never contained.

David Peralta, Moises Alou, Brian Giles, Aubrey Huff, and Elmer Valo.
The window is the five franchise seasons with the best one-decimal
league OPS+, among seasons of at least 300 plate appearances. Plate
appearances are AB + BB + HBP + SF. Sacrifice hits are not included.
A tie at one decimal between the fifth and sixth season stops the
build. Dice come from Hitter v0.5. Fielding stays the engine Average
default. No 2026 line is invented.
"""
from __future__ import annotations

import json
import math
import os
import sys
import tarfile
from decimal import Decimal, ROUND_HALF_UP

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "engines", "hitter-v0.5"))

import build_cards  # noqa: E402
import build_peak162 as peak  # noqa: E402
import hitter_solver as hs  # noqa: E402
from partition import validate_hitter_card  # noqa: E402

CARDS = os.path.join(ROOT, "data", "cards.json")
ROSTERS = os.path.join(ROOT, "data", "rosters.json")
REPORT = os.path.join(ROOT, "historical-cards", "accuracy", "missing_hitters.json")

FRANCHISE = {
    "ARI": ["ARI"],
    "COL": ["COL"],
    "MON": ["MON"],
    "PHA": ["PHA"],
    "PIT": ["PIT"],
    "SD": ["SDN"],
    "STL": ["SLN"],
    "TB": ["TBA", "TBD"],
}
YEAR_BOUNDS = {"PHA": (1901, 1954), "MON": (1969, 2004)}
TEAM_LINE = {
    "ARI": "Arizona Diamondbacks",
    "MON": "Montreal Expos",
    "PHA": "Philadelphia Athletics",
    "SD": "San Diego Padres",
    "TB": "Tampa Bay Rays",
}
# Counting stats the solver reads. A null in one of these on a window
# season is a hole, not a zero the card may quietly absorb, except IBB,
# HBP, SB, and CS, which Lahman leaves empty in some early seasons.
STRICT = ("G", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO")
NULLABLE = ("IBB", "HBP", "SB", "CS", "GIDP", "SF", "SH")
PA_FLOOR = 300

CHECKS = (
    ("STL", "musiast01", (1943, 1946, 1948, 1949, 1951)),
    ("STL", "pujolal01", (2003, 2004, 2006, 2008, 2009)),
    ("COL", "heltoto01", (2000, 2001, 2002, 2003, 2004)),
    ("COL", "walkela01", (1997, 1998, 1999, 2001, 2002)),
    ("ARI", "marteke01", (2019, 2021, 2023, 2024, 2025)),
)
PLAYERS = (
    {
        "key": "ARI|peralda01",
        "id": "peralda01",
        "team": "ARI",
        "hands": ("L", "L"),
        "years": (2014, 2015, 2018, 2019, 2022),
    },
    {
        "key": "MON|aloumo01",
        "id": "aloumo01",
        "team": "MON",
        "hands": ("R", "R"),
        "years": (1992, 1993, 1994, 1995, 1996),
    },
    {
        "key": "SD|gilesbr02",
        "id": "gilesbr02",
        "team": "SD",
        "hands": ("L", "L"),
        "years": (2004, 2005, 2006, 2007, 2008),
    },
    {
        "key": "TB|huffau01",
        "id": "huffau01",
        "team": "TB",
        "hands": ("L", "R"),
        "years": (2001, 2002, 2003, 2004, 2005),
    },
    {
        "key": "PHA|valoel01",
        "id": "valoel01",
        "team": "PHA",
        "hands": ("L", "R"),
        "years": (1946, 1947, 1948, 1951, 1952),
    },
)


def one_decimal(value):
    return value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def is_null(value):
    if value is None:
        return True
    text = str(value)
    if text in {"<NA>", "NA", "nan", "None", ""}:
        return True
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return True


def cell(value):
    if is_null(value):
        return 0, True
    return int(float(value)), False


def column(frame, name):
    if name not in frame.columns:
        raise SystemExit("Lahman table is missing %s" % name)
    return frame[name].tolist()


def load_lahman():
    path = peak.lahman_path()
    with tarfile.open(path) as tar:
        batting = peak.load_table(tar, "Batting")
        teams = peak.load_table(tar, "Teams")
        people = peak.load_table(tar, "People")
    return batting, teams, people


def league_rates(teams):
    years = [peak.as_int(value) for value in column(teams, "yearID")]
    leagues = [peak.blank(value) for value in column(teams, "lgID")]
    names = ["AB", "H", "X2B", "X3B", "HR", "BB", "HBP", "SF"]
    nums = {name: [peak.as_int(value) for value in column(teams, name)] for name in names}
    raw = {}
    for index, year in enumerate(years):
        key = (year, leagues[index])
        bucket = raw.setdefault(key, {name: 0 for name in names})
        for name in names:
            bucket[name] += nums[name][index]
    rates = {}
    max_year = 0
    for key, stats in raw.items():
        max_year = max(max_year, key[0])
        den = stats["AB"] + stats["BB"] + stats["HBP"] + stats["SF"]
        obp = (Decimal(stats["H"] + stats["BB"] + stats["HBP"]) / Decimal(den)
               if den else None)
        slg = (Decimal(stats["H"] + stats["X2B"] + 2 * stats["X3B"] + 3 * stats["HR"])
               / Decimal(stats["AB"]) if stats["AB"] else None)
        rates[key] = {"obp": obp, "slg": slg}
    return rates, max_year


def people_index(people):
    ids = [str(value) for value in column(people, "playerID")]
    bats = [peak.blank(value) for value in column(people, "bats")]
    throws = [peak.blank(value) for value in column(people, "throws")]
    return {pid: {"bats": bats[i], "throws": throws[i]} for i, pid in enumerate(ids)}


def collect(batting, wanted):
    """Franchise and other-club batting rows for the wanted player ids."""
    ids = [str(value) for value in column(batting, "playerID")]
    years = [peak.as_int(value) for value in column(batting, "yearID")]
    teams = [peak.blank(value) for value in column(batting, "teamID")]
    leagues = [peak.blank(value) for value in column(batting, "lgID")]
    fields = {
        "G": "G", "AB": "AB", "R": "R", "H": "H", "2B": "X2B", "3B": "X3B",
        "HR": "HR", "RBI": "RBI", "SB": "SB", "CS": "CS", "BB": "BB",
        "SO": "SO", "IBB": "IBB", "HBP": "HBP", "SH": "SH", "SF": "SF",
        "GIDP": "GIDP",
    }
    raw = {name: column(batting, source) for name, source in fields.items()}
    max_year = 0
    by_player = {pid: [] for pid in wanted}
    for index, pid in enumerate(ids):
        max_year = max(max_year, years[index])
        if pid not in by_player:
            continue
        counted = {}
        nulls = []
        for name in fields:
            value, missing = cell(raw[name][index])
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


def combine(rows):
    total = {name: 0 for name in ("G", "AB", "R", "H", "2B", "3B", "HR", "RBI",
                                  "SB", "CS", "BB", "SO", "IBB", "HBP", "SH",
                                  "SF", "GIDP")}
    nulls = []
    leagues = {}
    teams = []
    for row in rows:
        for name in total:
            total[name] += row["line"][name]
        for name in row["nulls"]:
            if name not in nulls:
                nulls.append(name)
        leagues[row["lg"]] = leagues.get(row["lg"], 0) + 1
        if row["team"] not in teams:
            teams.append(row["team"])
    return total, nulls, sorted(leagues), teams


def season_ops(rows, rates):
    weighted_obp = Decimal(0)
    weighted_slg = Decimal(0)
    weight = Decimal(0)
    for row in rows:
        line = row["line"]
        pa = line["AB"] + line["BB"] + line["HBP"] + line["SF"]
        rate = rates.get((row["year"], row["lg"]))
        if pa <= 0 or not row["lg"] or rate is None:
            continue
        if rate["obp"] is None or rate["slg"] is None or rate["obp"] <= 0 or rate["slg"] <= 0:
            continue
        weighted_obp += Decimal(pa) * rate["obp"]
        weighted_slg += Decimal(pa) * rate["slg"]
        weight += Decimal(pa)
    if weight <= 0:
        return None
    total, _, _, _ = combine(rows)
    den = total["AB"] + total["BB"] + total["HBP"] + total["SF"]
    if den <= 0 or total["AB"] <= 0:
        return None
    obp = Decimal(total["H"] + total["BB"] + total["HBP"]) / Decimal(den)
    slg = Decimal(total["H"] + total["2B"] + 2 * total["3B"] + 3 * total["HR"]) / Decimal(total["AB"])
    lg_obp = weighted_obp / weight
    lg_slg = weighted_slg / weight
    return one_decimal(100 * (obp / lg_obp + slg / lg_slg - 1))


def franchise_seasons(pid, code, rows, rates):
    allowed = set(FRANCHISE[code])
    lo, hi = YEAR_BOUNDS.get(code, (0, 9999))
    grouped = {}
    others = {}
    for row in rows:
        year = row["year"]
        if row["team"] in allowed and lo <= year <= hi:
            grouped.setdefault(year, []).append(row)
        else:
            others.setdefault(year, [])
            if row["team"] not in others[year]:
                others[year].append(row["team"])
    seasons = []
    for year in sorted(grouped):
        stints = grouped[year]
        total, nulls, leagues, teams = combine(stints)
        pa = total["AB"] + total["BB"] + total["HBP"] + total["SF"]
        seasons.append({
            "year": year,
            "teams": teams,
            "leagues": leagues,
            "pa": pa,
            "pa_with_sh": pa + total["SH"],
            "ops_plus": season_ops(stints, rates),
            "nulls": nulls,
            "other_clubs": others.get(year, []),
            "line": total,
        })
    return seasons, others


def qualifying(seasons):
    rows = [s for s in seasons if s["pa"] >= PA_FLOOR and s["ops_plus"] is not None]
    rows.sort(key=lambda s: (-s["ops_plus"], -s["pa"], s["year"]))
    return rows


def window_years(seasons, label):
    rows = qualifying(seasons)
    if len(rows) < 5:
        raise SystemExit("%s has %d qualifying seasons" % (label, len(rows)))
    if len(rows) > 5 and rows[4]["ops_plus"] == rows[5]["ops_plus"]:
        raise SystemExit(
            "%s ties at %s between %s and %s" % (
                label, rows[4]["ops_plus"], rows[4]["year"], rows[5]["year"]))
    for row in rows:
        if row["pa"] >= PA_FLOOR and row["ops_plus"] is None:
            raise SystemExit("%s %s has no league rate" % (label, row["year"]))
    return tuple(sorted(row["year"] for row in rows[:5])), rows


def show(label, seasons, chosen):
    print(label)
    for row in qualifying(seasons):
        mark = "IN" if row["year"] in chosen else "  "
        print("  %s %s  OPS+ %s  PA %d" % (mark, row["year"], row["ops_plus"], row["pa"]))
    for row in seasons:
        if row["pa"] < PA_FLOOR:
            ops = "n/a" if row["ops_plus"] is None else str(row["ops_plus"])
            print("  -- %s  OPS+ %s  PA %d" % (row["year"], ops, row["pa"]))


def assert_known(by_player, rates):
    for code, pid, expected in CHECKS:
        seasons, _ = franchise_seasons(pid, code, by_player[pid], rates)
        chosen, _ = window_years(seasons, "%s %s" % (code, pid))
        if chosen != expected:
            show("%s %s" % (code, pid), seasons, chosen)
            raise SystemExit("%s %s window %s != %s" % (code, pid, chosen, expected))
        print("check %s %s %s" % (code, pid, list(chosen)))
    seasons, _ = franchise_seasons("mazerbi01", "PIT", by_player["mazerbi01"], rates)
    rows = qualifying(seasons)
    fifth = rows[4]["ops_plus"]
    sixth = rows[5]["ops_plus"]
    tied = {rows[4]["year"], rows[5]["year"]}
    ahead = {row["year"] for row in rows if row["ops_plus"] > fifth}
    if fifth != sixth or fifth != Decimal("98.9") or tied != {1964, 1966}:
        show("PIT mazerbi01", seasons, ())
        raise SystemExit("Mazeroski tie check failed: %s %s %s" % (fifth, sixth, tied))
    if ahead != {1962, 1958, 1960, 1957}:
        raise SystemExit("Mazeroski seasons ahead of the tie: %s" % sorted(ahead))
    print("check PIT mazerbi01 tie 1964/1966 at 98.9")


def peak_block(seasons, years, team_line):
    chosen = [row for row in seasons if row["year"] in years]
    if len(chosen) != 5:
        raise SystemExit("window seasons missing: %s" % years)
    total = {name: 0 for name in chosen[0]["line"]}
    nulls = []
    for row in chosen:
        for name in STRICT:
            if name in row["nulls"]:
                raise SystemExit("%s %s is null" % (row["year"], name))
        for name in total:
            total[name] += row["line"][name]
        for name in row["nulls"]:
            nulls.append({"year": row["year"], "field": name})
    pa = total["AB"] + total["BB"] + total["HBP"] + total["SF"]
    block = {
        "G": total["G"],
        "PA": pa,
        "AB": total["AB"],
        "R": total["R"],
        "H": total["H"],
        "2B": total["2B"],
        "3B": total["3B"],
        "HR": total["HR"],
        "RBI": total["RBI"],
        "BB": total["BB"],
        "IBB": total["IBB"],
        "SO": total["SO"],
        "HBP": total["HBP"],
        "SB": total["SB"],
        "CS": total["CS"],
        "GIDP": total["GIDP"],
        "SF": total["SF"],
        "window_years": list(years),
        "team_line": team_line,
    }
    return block, nulls


def rates_of(peak_line):
    ab = float(peak_line["AB"])
    hits = float(peak_line["H"])
    doubles = float(peak_line["2B"])
    triples = float(peak_line["3B"])
    hr = float(peak_line["HR"])
    bb = float(peak_line["BB"])
    ibb = float(peak_line["IBB"])
    hbp = float(peak_line["HBP"])
    so = float(peak_line["SO"])
    pa = float(peak_line["PA"])
    singles = hits - doubles - triples - hr
    return {
        "avg": hits / ab,
        "obp": (hits + bb + hbp) / pa,
        "obp_ubb": (hits + (bb - ibb) + hbp) / pa,
        "slg": (hits + doubles + 2 * triples + 3 * hr) / ab,
        "1b": singles / pa,
        "2b": doubles / pa,
        "3b": triples / pa,
        "hr": hr / pa,
        "so": so / pa,
        "bb": bb / pa,
        "ubb": (bb - ibb) / pa,
    }


def card_rates(exp):
    return {
        "avg": exp["avg"],
        "obp": exp["obp"],
        "slg": exp["slg"],
        "1b": exp["1bp"],
        "2b": exp["2bp"],
        "3b": exp["3bp"],
        "hr": exp["hrp"],
        "so": exp["sop"],
        "bb": exp["bbp"],
    }


def round_rates(block):
    return {key: round(value, 4) for key, value in block.items()}


def hr_ceiling(sections):
    hands = []
    for hand in ("vsLHP", "vsRHP"):
        band = ((sections.get("WHEELHOUSE") or {}).get(hand) or {}).get("HR")
        if band == [1, 99]:
            hands.append(hand)
    return hands


def roster_spot(rosters, code, pid):
    matches = [p for p in rosters[code]["players"] if p["id"] == pid]
    if len(matches) != 1:
        raise SystemExit("%s %s roster entries: %d" % (code, pid, len(matches)))
    return matches[0]


def build_player(spec, seasons, person, spot):
    code = spec["team"]
    bats, throws = person["bats"], person["throws"]
    if (bats, throws) != spec["hands"]:
        raise SystemExit("%s hands %s/%s != %s" % (spec["key"], bats, throws, spec["hands"]))
    years, ranked = window_years(seasons, spec["key"])
    if years != spec["years"]:
        show(spec["key"], seasons, years)
        raise SystemExit("%s window %s != %s" % (spec["key"], years, spec["years"]))
    block, nulls = peak_block(seasons, years, TEAM_LINE[code])
    scaled = build_cards.scale_bat_162(block)
    row = {
        "Name": spot["name"],
        "Team": TEAM_LINE[code],
        "Bats": bats,
        "Throws": throws,
        "Position": spot["pos"],
        "Fielding": "average",
        "Arm": "average",
        "PA": block["PA"],
        "AB": block["AB"],
        "H": block["H"],
        "2B": block["2B"],
        "3B": block["3B"],
        "HR": block["HR"],
        "BB": block["BB"],
        "IBB": block["IBB"],
        "SO": block["SO"],
        "HBP": block["HBP"],
        "SB": block["SB"],
        "CS": block["CS"],
    }
    if os.environ.get("PP_WINDOWS_ONLY") == "1":
        return {
            "peak_bat": block,
            "peak_bat_162": scaled,
            "card_bat": None,
            "spot": spot,
            "report": {"nulls": nulls, "counting": {key: block[key] for key in build_cards.BAT_COUNTING}},
        }
    print("solving %s" % spec["key"])
    built = hs.build_one(row)
    if built is None:
        raise SystemExit("solver skipped %s" % spec["key"])
    solved, exp, tgt, _comp, _slug, actual_err, best_err, _diag = built
    rating = hs.ratings(row)
    chip = rating["positions"][0]
    if (chip["range"], chip["e"], chip["arm"], rating["dp"], rating["sac_bunt"]) != ("C", 4, 6, 7, "F"):
        raise SystemExit("engine fielding default changed: %s" % rating)
    if chip["pos"] != spot["pos"] or solved["run"] != rating["run"]:
        raise SystemExit("position or run mismatch for %s" % spec["key"])
    lines, _fit, old_status = hs.fit_report(exp, tgt)
    status, reason = hs.classify_review(old_status == "PASS", actual_err, best_err)
    card_bat = {
        "arm": "Average",
        "bats": bats,
        "dp": rating["dp"],
        "fielding": "Average",
        "out_table": solved["out_table"],
        "positions": [{
            "pos": spot["pos"],
            "range": chip["range"],
            "e": chip["e"],
            "arm": chip["arm"],
        }],
        "qa_status": status,
        "run": rating["run"],
        "sac_bunt": rating["sac_bunt"],
        "sections": solved["sections"],
        "steal": rating["steal"],
        "throws": throws,
    }
    problems = validate_hitter_card(card_bat, exact=False)
    if problems:
        raise SystemExit("%s partition: %s" % (spec["key"], "; ".join(problems[:6])))
    real = rates_of(block)
    card = card_rates(exp)
    return {
        "peak_bat": block,
        "peak_bat_162": scaled,
        "card_bat": card_bat,
        "spot": spot,
        "report": report_for(spec, seasons, ranked, block, nulls, real, card, tgt,
                             status, reason, actual_err, best_err, lines, solved),
    }


def report_for(spec, seasons, ranked, block, nulls, real, card, tgt, status,
               reason, actual_err, best_err, lines, solved):
    fifth = ranked[4]
    sixth = ranked[5] if len(ranked) > 5 else None
    flags = [
        "Fielding, arm, double-play, and sac bunt are the engine defaults "
        "(Average, range C, error 4, arm 6, DP 7, sac F), not a measured label.",
        "Steal and run come from the solver's SB, CS, and triple formula.",
    ]
    if sixth is not None:
        gap = fifth["ops_plus"] - sixth["ops_plus"]
        if gap <= Decimal("0.2"):
            flags.append(
                "%s is the last included season at OPS+ %s. %s is next at "
                "OPS+ %s, %s behind." % (
                    fifth["year"], fifth["ops_plus"], sixth["year"],
                    sixth["ops_plus"], gap))
    for row in seasons:
        if row["year"] in spec["years"]:
            continue
        if row["pa"] >= PA_FLOOR:
            continue
        if row["ops_plus"] is not None and row["ops_plus"] >= fifth["ops_plus"]:
            flags.append(
                "%s has %d plate appearances and OPS+ %s. The 300 floor "
                "leaves it out, and that OPS+ would rank inside the five." % (
                    row["year"], row["pa"], row["ops_plus"]))
        elif row["pa"] >= 250:
            ops = "n/a" if row["ops_plus"] is None else str(row["ops_plus"])
            flags.append(
                "%s has %d plate appearances, under the 300 floor. OPS+ %s "
                "would not enter the five." % (row["year"], row["pa"], ops))
        if row["pa"] < PA_FLOOR <= row["pa_with_sh"]:
            flags.append(
                "%s crosses 300 plate appearances only when sacrifice hits "
                "are counted (%d without, %d with)." % (
                    row["year"], row["pa"], row["pa_with_sh"]))
    if spec["id"] == "aloumo01":
        cameo = [row for row in seasons if row["year"] == 1990]
        if len(cameo) != 1:
            raise SystemExit("Alou 1990 franchise row missing")
        flags.append(
            "1990 is the documented Expos cameo: %d games and %d plate "
            "appearances (%d if sacrifice hits are counted). It stays out." % (
                cameo[0]["line"]["G"], cameo[0]["pa"], cameo[0]["pa_with_sh"]))
    if spec["id"] == "valoel01":
        flags.append(
            "IBB and SF are null in every window season. Lahman had not "
            "started recording them. The card stores zero, so every walk is "
            "unintentional and the on-base denominator has no sacrifice flies. "
            "HBP is recorded.")
    for row in seasons:
        if row["year"] in spec["years"] and row["other_clubs"]:
            flags.append(
                "%s also has a %s stint. Only the %s line is in the window." % (
                    row["year"], ", ".join(row["other_clubs"]), spec["team"]))
    if nulls:
        grouped = {}
        for item in nulls:
            grouped.setdefault(item["field"], []).append(item["year"])
        flags.append(
            "Lahman nulls treated as zero, the file's own recording: "
            + "; ".join("%s %s" % (field, grouped[field]) for field in sorted(grouped)))
    if spec["id"] == "peralda01":
        flags.append(
            "No 2025 or 2026 season is on the card. Lahman in this repo "
            "stops at 2025, and Peralta has no 2025 batting row. AP reported "
            "on 2026-02-04 that he retired after 11 seasons and did not play "
            "in 2025 (https://apnews.com/article/peralta-retires-diamondbacks-padres-b7812bda15fbd8e2f1b535e23590dbd9). "
            "MLB.com posted a Diamondbacks retirement video dated 2026-02-06.")
        flags.append(
            "AP and ESPN record a 2019 Gold Glove. That was not turned into "
            "a range grade. The card stays Average.")
    if status == "ARCHITECTURE-LIMITED":
        flags.append(
            "QA status ARCHITECTURE-LIMITED. The shipped card is the solver's "
            "best legal card and sits just outside the engine's tight slash "
            "tolerance. %s" % reason)
    elif status != "PASS":
        flags.append("QA status %s. %s" % (status, reason))
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
    if abs(gaps["obp_real"]) >= 0.008 and abs(gaps["obp_ubb"]) < 0.008:
        flags.append(
            "Card OBP is %.3f against the real on-base percentage. The "
            "solver target leaves intentional walks out, and the card is "
            "%.3f from that target." % (gaps["obp_real"], gaps["obp_ubb"]))
    if abs(gaps["avg"]) > 0.010:
        flags.append("AVG is %.3f off the real window." % gaps["avg"])
    if abs(gaps["slg"]) > 0.020:
        flags.append("SLG is %.3f off the real window." % gaps["slg"])
    if abs(gaps["obp_ubb"]) > 0.010:
        flags.append("OBP is %.3f off the unintentional-walk target." % gaps["obp_ubb"])
    for label, limit in (("1b", 0.008), ("2b", 0.008), ("3b", 0.008),
                         ("hr", 0.008), ("so", 0.008)):
        if abs(gaps[label]) > limit:
            flags.append("%s per PA is %.4f off the real window." % (label.upper(), gaps[label]))
    ceiling = hr_ceiling(solved["sections"])
    if ceiling:
        flags.append("Wheelhouse HR is 1-99 versus %s." % ", ".join(ceiling))
    if solved["run"] >= 10:
        flags.append(
            "Run is 10, the formula's cap. It is not a separate measured grade.")
    return {
        "key": spec["key"],
        "name": spec["key"],
        "window_years": list(spec["years"]),
        "qa_status": status,
        "qa_reason": reason,
        "fit_error": round(actual_err, 4),
        "best_possible": round(best_err, 4),
        "fit_lines": lines,
        "nulls": nulls,
        "counting": {key: block[key] for key in build_cards.BAT_COUNTING},
        "real": round_rates(real),
        "card": round_rates(card),
        "target_obp": round(tgt["obp"], 4),
        "delta": {key: round(value, 4) for key, value in gaps.items()},
        "seasons": [{
            "year": row["year"],
            "included": row["year"] in spec["years"],
            "g": row["line"]["G"],
            "pa": row["pa"],
            "pa_with_sh": row["pa_with_sh"],
            "ops_plus": None if row["ops_plus"] is None else str(row["ops_plus"]),
            "teams": row["teams"],
            "other_clubs": row["other_clubs"],
            "nulls": row["nulls"],
        } for row in seasons],
        "flags": flags,
    }


def dump(obj, path):
    text = json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return text


def main():
    batting, teams, people = load_lahman()
    rates, team_max = league_rates(teams)
    wanted = {pid for _c, pid, _y in CHECKS}
    wanted.update(spec["id"] for spec in PLAYERS)
    wanted.add("mazerbi01")
    by_player, bat_max = collect(batting, wanted)
    if bat_max != 2025 or team_max < 2025:
        raise SystemExit("Lahman year span is batting %s teams %s" % (bat_max, team_max))
    for pid in wanted:
        if not by_player[pid]:
            raise SystemExit("no batting rows for %s" % pid)
    assert_known(by_player, rates)
    hands = people_index(people)
    rosters = json.loads(open(ROSTERS, encoding="utf-8").read())
    original = open(CARDS, encoding="utf-8").read()
    cards = json.loads(original)
    if dump_text(cards) != original:
        raise SystemExit("cards.json does not round-trip")
    before = {key: json.dumps(value, sort_keys=True) for key, value in cards.items()}
    reports = []
    for spec in PLAYERS:
        seasons, others = franchise_seasons(spec["id"], spec["team"], by_player[spec["id"]], rates)
        show(spec["key"], seasons, spec["years"])
        if spec["id"] == "peralda01":
            latest = max(row["year"] for row in by_player[spec["id"]])
            if latest != 2024 or any(row["year"] >= 2025 for row in by_player[spec["id"]]):
                raise SystemExit("Peralta batting years reach %s" % latest)
            ari_years = [row["year"] for row in seasons]
            if any(year > 2022 for year in ari_years):
                raise SystemExit("Peralta has an Arizona season after 2022")
        built = build_player(spec, seasons, hands[spec["id"]], roster_spot(rosters, spec["team"], spec["id"]))
        if os.environ.get("PP_WINDOWS_ONLY") == "1":
            print("  nulls %s" % built["report"]["nulls"])
            print("  line %s" % built["report"]["counting"])
            continue
        built["report"]["name"] = roster_spot(rosters, spec["team"], spec["id"])["name"]
        reports.append(built["report"])
        entry = cards.get(spec["key"])
        spot = {
            "group": built["spot"]["group"],
            "kind": "hitter",
            "pos": built["spot"]["pos"],
            "slot": built["spot"]["slot"],
        }
        if entry is None:
            cards[spec["key"]] = {
                "id": spec["id"],
                "name": built["spot"]["name"],
                "team": spec["team"],
                "spots": [spot],
                "peak_bat": built["peak_bat"],
                "peak_bat_162": built["peak_bat_162"],
                "peak_pit": None,
                "peak_pit_162": None,
                "card_bat": built["card_bat"],
                "card_pit": None,
                "tournament": None,
            }
        else:
            entry["peak_bat"] = built["peak_bat"]
            entry["peak_bat_162"] = built["peak_bat_162"]
            entry["card_bat"] = built["card_bat"]
            entry["spots"] = [spot]
            entry.pop("conversion_status", None)
        print("%s %s AVG %+.4f SLG %+.4f OBP(uBB) %+.4f" % (
            spec["key"], built["report"]["qa_status"],
            built["report"]["delta"]["avg"],
            built["report"]["delta"]["slg"],
            built["report"]["delta"]["obp_ubb"]))
    if os.environ.get("PP_WINDOWS_ONLY") == "1":
        print("windows only; cards.json not written")
        return 0
    after = {key: json.dumps(value, sort_keys=True) for key, value in cards.items()}
    changed = sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))
    expected_keys = sorted(spec["key"] for spec in PLAYERS)
    unexpected = [key for key in changed if key not in expected_keys]
    if unexpected:
        raise SystemExit("unexpected card changes: %s" % unexpected)
    for key in expected_keys:
        if not ((cards.get(key) or {}).get("card_bat") or {}).get("sections"):
            raise SystemExit("missing playable card %s" % key)
    import card_postpass
    card_postpass.finalize(cards, expected_keys)
    dump(cards, CARDS)
    report = {
        "lahman_sha256": peak.LAHMAN_SHA256,
        "lahman_max_batting_year": bat_max,
        "pa_floor": PA_FLOOR,
        "pa_definition": "AB + BB + HBP + SF; sacrifice hits excluded",
        "rank": "league OPS+ rounded half up to one decimal, no park factor",
        "players": reports,
    }
    dump(report, REPORT)
    print("wrote %s" % REPORT)
    return 0


def dump_text(obj):
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    sys.exit(main())
