#!/usr/bin/env python3
"""Build the roster and player-card data the site serves.

Reads the converted Payoff Pitch sets and the master tournament archive
from the workspace, and writes two files the viewer loads at boot:

  data/rosters.json  one entry per converted club: role entries for 26
                     distinct active players in set order (lineup,
                     bench, rotation, bullpen). True two-way players may
                     appear twice under one ID without taking two places.
  data/cards.json    one entry per rostered player, keyed "CODE|player_id"
                     the way data/bios.json is keyed: his prime-window
                     (peak) line, his converted card, and his tournament
                     line aggregated from the master archive

Inputs (workspace paths; override with the environment variables shown):

  PP_SETS_ROOT   not one folder: each club's set folder is named in SETS
                 below, under ~/workspace
  PP_INPUT_STATS ~/workspace/apba-card-builder/all_time_rosters/teams
                 (each club's input_stats.csv carries the Lahman player
                 id and the prime-window years for every rostered player)
  PP_ARCHIVE     ~/workspace/apba-card-builder/all_time_rosters/apba_games/
                 tournament_results.json  (the master archive; only its
                 games count as tournament stats)
  PP_LAHMAN_TEAMS ~/workspace/apba-card-builder/all_time_rosters/lahman/
                 Teams.csv  (the Lahman Teams table; only its yearID,
                 teamID, and G columns are read, for the pitcher scaling
                 below)
  the repo's own tournament_results.json supplies club names, seeds, and
  the player ids the site already publishes

Peak display: the 162-game average. Each entry also carries a
peak_bat_162 / peak_pit_162 block: the prime-window line rescaled the
way Joe asked for it, as one 162-game season. The raw window totals stay
in peak_bat / peak_pit untouched (they are the card's build line and
feed the rates); the viewer displays the 162 blocks and computes AVG,
OBP, SLG, and ERA from the raw line, so the rates are the window's own
and never move.

  Batters: every counting stat is scaled by 162 / (games played in the
  window) and rounded half up; the games column shows 162.
  Pitchers: the window becomes an average season on a 162-game
  schedule: the per-season average (window total / window seasons)
  rescaled by (162 x seasons) / (the club's total team games across the
  window seasons, from the Lahman Teams table), which multiplies out to
  window total x 162 / team games. Counting stats round half up. IP is
  scaled in outs and stored both as outs and in baseball thirds
  ("307.1" is 307 and a third). A window season with no Lahman row for
  the club counts as 162 team games, and the build log names it.

Player identity: the Lahman id from input_stats.csv, unless the site's
published results file already carries the same player (same club, same
name) under a different id; then the published id wins so every link on
the site keeps working, and the difference is printed below as a
reconciliation. Tournament lines are matched to players by club and
name, so an id difference never loses a player's stats.

Adding a club: convert its set, add one row to SETS (club code, set
folder, input_stats slug), rerun this script, and commit the two data
files with the change note. Nothing here edits a game, a series, or a
locked line; the validator's locked checks are untouched.

Run from anywhere:  python3 scripts/build_cards.py

Once data/cards.json exists, a run refreshes only the tournament
block from this repo's tournament_results.json. Peak windows, dice,
pitching charts, ids, and roster spots stay as repaired. data/rosters.json
is not rewritten. A game import uses that same path, so a new game
never rebuilds card bodies from the set archive.

PP_REBUILD_CARDS_FROM_SETS=1 is the explicit full rebuild from the set
folders. It replaces card bodies and roster spots. Game import does
not set it.

The full rebuild is deterministic: a second run with unchanged inputs
writes byte-identical files.
"""

import csv
import json
import math
import os
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE = os.path.expanduser("~/workspace")

# club code -> (converted set folder under ~/workspace, input_stats slug)
SETS = [
    ("BOS", "payoff-pitch-alltime-teams", "bos"),
    ("PHA", "payoff-pitch-alltime-teams", "pha"),
    ("SF", "payoff-pitch-giants-expos", "sf"),
    ("MON", "payoff-pitch-giants-expos", "mon"),
    ("WSH", "payoff-pitch-nationals", "wsh"),
    ("TB", "payoff-pitch-rays", "tb"),
    ("DET", "payoff-pitch-tigers", "det"),
    ("ARI", "payoff-pitch-diamondbacks", "ari"),
    ("CHC", "payoff-pitch-cubs", "chc"),
    ("COL", "payoff-pitch-rockies", "col"),
    ("STL", "payoff-pitch-cardinals", "stl"),
    ("ATL", "payoff-pitch-braves", "atl"),
    ("SD", "payoff-pitch-padres", "sd"),
    ("PIT", "payoff-pitch-pirates", "pit"),
    ("TOR", "payoff-pitch-bluejays", "tor"),
    ("CIN", "payoff-pitch-reds", "cin"),
    ("TEX", "payoff-pitch-rangers", "tex"),
    ("LAD", "payoff-pitch-dodgers", "lad"),
]

# Window years for a card whose input line the APBA files do not carry.
# Babe Ruth's Boston hitter card was built from standard records because
# the APBA build carries him as a pitcher only; the set's SET_REPORT.md
# (ruling 5) records the card as the 1918 and 1919 seasons combined.
WINDOW_EXCEPTIONS = {("BOS", "babe ruth"): [1918, 1919]}

INPUT_STATS_ROOT = os.environ.get(    "PP_INPUT_STATS",
    os.path.join(WORKSPACE, "apba-card-builder", "all_time_rosters", "teams"))
ARCHIVE_PATH = os.environ.get(
    "PP_ARCHIVE",
    os.path.join(WORKSPACE, "apba-card-builder", "all_time_rosters",
                 "apba_games", "tournament_results.json"))
LAHMAN_TEAMS_PATH = os.environ.get(
    "PP_LAHMAN_TEAMS",
    os.path.join(WORKSPACE, "apba-card-builder", "all_time_rosters",
                 "lahman", "Teams.csv"))

# Lahman team ids per converted club, across the eras its prime windows
# reach: the Giants' New York years are NY1 in the Lahman table, and
# Tampa Bay's early years are TBD in some releases, TBA in others.
TEAM_IDS = {
    "BOS": ["BOS"],
    "PHA": ["PHA"],
    "SF": ["SFN", "NY1"],
    "MON": ["MON"],
    "WSH": ["WAS"],
    "TB": ["TBA", "TBD"],
    "DET": ["DET"],
    "ARI": ["ARI"],
    "CHC": ["CHN"], "STL": ["SLN"],
    "COL": ["COL"],
    "ATL": ["BSN", "ML1", "ATL"],
    "SD": ["SDN"],
    "PIT": ["PIT"],
    "TOR": ["TOR"],
    "CIN": ["CIN"],
    "TEX": ["TEX", "WS2"],
    "LAD": ["BRO", "LAN"],
}

BAT_COUNTING = ["G", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB",
                "IBB", "SO", "HBP", "SB", "CS", "GIDP", "SF"]
ARCHIVE_BAT = [("ab", "ab"), ("r", "r"), ("h", "h"), ("doubles", "2b"),
               ("triples", "3b"), ("hr", "hr"), ("rbi", "rbi"), ("bb", "bb"),
               ("k", "so"), ("hbp", "hbp"), ("sb", "sb"), ("cs", "cs"),
               ("sac", "sac"), ("sf", "sf"), ("gidp", "gidp"), ("ci", "ci")]
ARCHIVE_PIT = [("h", "h"), ("r", "r"), ("er", "er"), ("bb", "bb"),
               ("k", "so"), ("hr", "hr"), ("bf", "bf")]


def norm_name(name):
    """Match key for a player name across files: accents, periods, and
    spacing differ between the set files and the archive."""
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace(".", " ")
    return " ".join(text.split()).casefold()


def display_name(set_name):
    """set_index disambiguates a few names with a club suffix, e.g.
    'Jimmie Foxx (PHA)'. The card itself carries the plain name."""
    name = set_name.strip()
    for suffix in (" (PHA)", " (BOS)"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def as_int(value):
    if value in (None, ""):
        return None
    return int(float(value))


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def window_years(row):
    raw = (row or {}).get("window_years") or ""
    return [int(y) for y in raw.split(";") if y.strip()]


def round_half_up(value):
    return int(math.floor(value + 0.5))


_team_games_cache = None


def load_team_games():
    """(team id, year) -> games played, from the Lahman Teams table.
    An empty map when the file is not on hand; every lookup then falls
    back to a 162-game season, and the build log names the seasons."""
    global _team_games_cache
    if _team_games_cache is None:
        _team_games_cache = {}
        if os.path.exists(LAHMAN_TEAMS_PATH):
            for row in read_csv(LAHMAN_TEAMS_PATH):
                year = as_int(row.get("yearID"))
                games = as_int(row.get("G"))
                if year is not None and games is not None:
                    _team_games_cache[(row.get("teamID"), year)] = games
    return _team_games_cache


def team_games_total(code, years):
    """The club's total team games across the window seasons, and the
    seasons no Lahman row covered (each counted as 162)."""
    table = load_team_games()
    total = 0
    missing = []
    for year in years:
        games = None
        for team_id in TEAM_IDS.get(code, []):
            games = table.get((team_id, year))
            if games is not None:
                break
        if games is None:
            games = 162
            missing.append(year)
        total += games
    return total, missing


def scale_bat_162(peak):
    """The window's batting line as a 162-game average: every counting
    stat scaled by 162 / window games, rounded half up, games shown as
    162. Rates are not carried here; the viewer computes them from the
    raw peak_bat line, so they are the window's own."""
    games = peak.get("G")
    if not games:
        return None
    factor = 162.0 / games
    block = {f: (round_half_up(peak[f] * factor)
                 if peak.get(f) is not None else None)
             for f in BAT_COUNTING}
    block["G"] = 162
    block["window_years"] = peak.get("window_years")
    block["team_line"] = peak.get("team_line")
    block["window_games"] = games
    return block


PIT_COUNTING_162 = ("w", "l", "g", "gs", "sv", "h", "r", "er", "hr",
                    "bb", "so", "hbp", "bf")


def scale_pit_162(code, name, peak, notes):
    """The window's pitching line as an average season on a 162-game
    schedule (the arithmetic is in the header). IP scales in outs and
    renders back in baseball thirds. ERA is not carried here; the
    viewer computes it from the raw peak_pit line, unchanged."""
    years = peak.get("window_years") or []
    if not years:
        return None
    total, missing = team_games_total(code, years)
    if not total:
        return None
    factor = 162.0 / total
    block = {f: (round_half_up(peak[f] * factor)
                 if peak.get(f) is not None else None)
             for f in PIT_COUNTING_162}
    ip = peak.get("ip")
    if ip is not None:
        outs = round_half_up(round(float(ip) * 3) * factor)
        block["ip_outs"] = outs
        block["ip"] = "%d.%d" % (outs // 3, outs % 3)
    else:
        block["ip_outs"] = None
        block["ip"] = None
    block["window_years"] = years
    block["seasons"] = len(years)
    block["team_games"] = total
    if missing:
        block["team_games_fallback"] = missing
        notes.append(
            "%s %s: no Lahman team-games row for %s; counted as 162 "
            "team games" % (code, name,
                            ", ".join(str(y) for y in missing)))
    return block


def tournament_index(archive):
    """Per (club, normalized name): the archive ids seen, and per game id
    the batting and pitching lines, from one archive file."""
    ids = {}
    lines = {}
    for game in archive["games"]:
        for kind, field in (("bat", "batting"), ("pit", "pitching")):
            for line in game[field]:
                key = (line["team"], norm_name(line["name"]))
                ids.setdefault(key, set()).add(line["player_id"])
                lines.setdefault(key, {}).setdefault(
                    game["id"], {})[kind] = line
    decisions = {}
    for game in archive["games"]:
        for kind, entry in (game.get("wls") or {}).items():
            if entry:
                decisions.setdefault(
                    (entry["team"], entry["player_id"]), []).append(
                    (game["id"], kind))
    return ids, lines, decisions


def aggregate_tournament(key, lines, decisions, master_ids):
    """One player's tournament line from the master archive lines."""
    per_game = lines.get(key)
    if not per_game:
        return None
    batting = None
    pitching = None
    game_ids = []
    for game_id in per_game:  # archive order is insertion order
        game_ids.append(game_id)
        entry = per_game[game_id]
        if "bat" in entry:
            line = entry["bat"]
            if batting is None:
                batting = {"g": 0}
                for _, out in ARCHIVE_BAT:
                    batting[out] = 0
            batting["g"] += 1
            for src, out in ARCHIVE_BAT:
                value = line.get(src)
                if value is not None:
                    batting[out] += value
        if "pit" in entry:
            line = entry["pit"]
            if pitching is None:
                pitching = {"g": 0, "gs": 0, "outs": 0, "w": 0, "l": 0,
                            "sv": 0}
                for _, out in ARCHIVE_PIT:
                    pitching[out] = 0
            pitching["g"] += 1
            if line.get("appearance_order") == 1:
                pitching["gs"] += 1
            pitching["outs"] += line.get("outs") or 0
            for src, out in ARCHIVE_PIT:
                value = line.get(src)
                if value is not None:
                    pitching[out] += value
    club = key[0]
    for player_id in master_ids.get(key, ()):  # decisions key on the id
        for game_id, kind in decisions.get((club, player_id), []):
            if pitching is None:
                continue
            if kind == "W":
                pitching["w"] += 1
            elif kind == "L":
                pitching["l"] += 1
            elif kind == "S":
                pitching["sv"] += 1
    return {"batting": batting, "pitching": pitching, "games": game_ids}


def build():
    site = load_json(os.path.join(ROOT, "tournament_results.json"))
    archive = load_json(ARCHIVE_PATH)
    teams = {t["code"]: t for t in site["teams"]}
    site_ids, _, _ = tournament_index(site)
    master_ids, master_lines, master_decisions = tournament_index(archive)

    reconciliations = []
    peak_notes = []
    cards = {}
    rosters = {}

    for code, set_folder, slug in SETS:
        set_dir = os.path.join(WORKSPACE, set_folder)
        index_rows = [r for r in read_csv(os.path.join(set_dir, "set_index.csv"))
                      if r["team"] == code and r["kind"] in ("hitter", "pitcher")]
        input_rows = read_csv(os.path.join(INPUT_STATS_ROOT, slug,
                                           "input_stats.csv"))
        input_by_key = {}
        for row in input_rows:
            input_by_key[(row["type"], norm_name(row["name"]))] = row
        v2_by_name = {norm_name(p["name"]): p for p in load_json(
            os.path.join(set_dir, "pitcher_output_v2", "pitchers_v2.json"))
            if p["team"] == code}
        addendum = load_json(os.path.join(set_dir, "pitcher_addendum.json"))
        add_by_name = {norm_name(p["name"]): p for p in addendum["pitchers"]
                       if p["team"] == code}
        qa_by_key = {(r["kind"], norm_name(display_name(r["name"]))): r
                     for r in index_rows}

        hitters = [r for r in index_rows if r["kind"] == "hitter"]
        pitchers = [r for r in index_rows if r["kind"] == "pitcher"]
        spots = []  # (kind, row, group, slot)
        for i, row in enumerate(hitters):
            if i < 9:
                spots.append(("hitter", row, "lineup", i + 1))
            else:
                spots.append(("hitter", row, "bench", i - 8))
        sp_i = rp_i = 0
        for row in pitchers:
            if row["pos_or_role"] == "SP":
                sp_i += 1
                spots.append(("pitcher", row, "rotation", sp_i))
            else:
                rp_i += 1
                spots.append(("pitcher", row, "bullpen", rp_i))

        people = {}
        order = []
        for kind, row, group, slot in spots:
            name = display_name(row["name"])
            key = norm_name(name)
            person = people.get(key)
            if person is None:
                person = {"name": name, "spots": []}
                people[key] = person
                order.append(key)
            person["spots"].append({
                "group": group, "slot": slot,
                "pos": row["pos_or_role"], "kind": kind})

        roster_players = []
        for key in order:
            person = people[key]
            name = person["name"]
            bat_row = input_by_key.get(("H", key))
            pit_row = input_by_key.get(("P", key))
            id_row = bat_row or pit_row
            player_id = id_row["player_id"] if id_row else None
            site_key = (code, key)
            if site_key in site_ids:
                published = sorted(site_ids[site_key])[0]
                if player_id and published != player_id:
                    if player_id == "mcclash01" and published == "mcclasha01":
                        reconciliations.append(
                            "%s %s: results still use %s; the card keeps "
                            "the Lahman id %s" % (
                                code, name, published, player_id))
                    else:
                        reconciliations.append(
                            "%s %s: input_stats/archive id %s, site publishes "
                            "%s; the card data keys on the published id" % (
                                code, name, player_id, published))
                        player_id = published
            if not player_id:
                raise SystemExit("no player id found for %s %s" % (code, name))
            if site_key in master_ids:
                for mid in sorted(master_ids[site_key]):
                    if mid != (input_by_key.get(("H", key)) or {}).get(
                            "player_id") and mid != (input_by_key.get(
                                ("P", key)) or {}).get("player_id"):
                        reconciliations.append(
                            "%s %s: master archive id %s differs from "
                            "input_stats id %s; stats matched by name" % (
                                code, name, mid, player_id))

            entry = {
                "id": player_id,
                "name": name,
                "team": code,
                "spots": person["spots"],
                "peak_bat": None,
                "peak_bat_162": None,
                "peak_pit": None,
                "peak_pit_162": None,
                "card_bat": None,
                "card_pit": None,
                "tournament": aggregate_tournament(
                    site_key, master_lines, master_decisions, master_ids),
            }

            hit_row = qa_by_key.get(("hitter", key))
            if hit_row is not None:
                card = load_json(os.path.join(set_dir, hit_row["file"]))
                line = card["stat_line"]
                peak = {f: as_int(line.get(f)) for f in BAT_COUNTING}
                peak["window_years"] = window_years(bat_row) or \
                    WINDOW_EXCEPTIONS.get((code, key), [])
                peak["team_line"] = line.get("Team")
                entry["peak_bat"] = peak
                entry["peak_bat_162"] = scale_bat_162(peak)
                entry["card_bat"] = {
                    "bats": card.get("bats"),
                    "throws": card.get("throws"),
                    "positions": card.get("positions"),
                    "sections": card.get("sections"),
                    "out_table": card.get("out_table"),
                    "dp": card.get("dp"),
                    "steal": card.get("steal"),
                    "run": card.get("run"),
                    "sac_bunt": card.get("sac_bunt"),
                    "fielding": line.get("Fielding"),
                    "arm": line.get("Arm"),
                    "qa_status": hit_row["qa_status"],
                }

            if key in v2_by_name:
                v2 = v2_by_name[key]
                src = v2["input_row"]
                peak = {
                    "window_years": v2.get("window"),
                    "w": as_int(src.get("W")), "l": as_int(src.get("L")),
                    "ip": src.get("IP"), "h": as_int(src.get("H")),
                    "hr": as_int(src.get("HR")), "bb": as_int(src.get("BB")),
                    "so": as_int(src.get("SO")), "hbp": as_int(src.get("HBP")),
                    "bf": as_int(src.get("BF")),
                }
                if pit_row is not None:
                    peak["g"] = as_int(pit_row.get("G"))
                    peak["gs"] = as_int(pit_row.get("GS"))
                    peak["sv"] = as_int(pit_row.get("SV"))
                    peak["er"] = as_int(pit_row.get("ER"))
                    peak["r"] = as_int(pit_row.get("R"))
                entry["peak_pit"] = peak
                entry["peak_pit_162"] = scale_pit_162(
                    code, name, peak, peak_notes)
                add = add_by_name.get(key, {})
                ratings = add.get("ratings", {})
                stamina = (ratings.get("stamina") or {}).get("value") or {}
                entry["card_pit"] = {
                    "throws": v2.get("throws"),
                    "card_type": v2.get("card_type"),
                    "table_2d6": v2.get("card_table_2d6"),
                    "so_modifier": v2.get("so_modifier"),
                    "special": v2.get("special_required"),
                    "qa_status": v2.get("qa_classification"),
                    "stamina": {"start": stamina.get("start"),
                                "relief": stamina.get("relief")},
                    "addendum": {
                        "wp": (ratings.get("wp") or {}).get("value"),
                        "dp": (ratings.get("dp") or {}).get("value"),
                        "hold": (ratings.get("hold") or {}).get("value"),
                        "pickoff": (ratings.get("pickoff") or {}).get("value"),
                        "inj": (ratings.get("inj") or {}).get("value"),
                    },
                }

            cards["%s|%s" % (code, player_id)] = entry
            for spot in person["spots"]:
                roster_players.append({
                    "id": player_id, "name": name, "group": spot["group"],
                    "slot": spot["slot"], "pos": spot["pos"],
                    "kind": spot["kind"]})

        played = any(
            line["team"] == code
            for game in archive["games"]
            for line in game["batting"] + game["pitching"])
        rosters[code] = {
            "code": code,
            "name": teams[code]["name"],
            "seed": teams[code]["seed"],
            "played": played,
            "players": roster_players,
        }

    apply_owner_roster_amendments(cards, rosters)
    apply_padres_roster_amendment(cards, rosters)
    apply_expos_roster_amendment(cards, rosters)
    apply_diamondbacks_roster_amendment(cards, rosters)
    apply_rays_roster_amendment(cards, rosters)
    apply_nationals_roster_amendment(cards, rosters)
    apply_giants_roster_amendment(cards, rosters)
    apply_tigers_roster_amendment(cards, rosters)
    apply_braves_roster_amendment(cards, rosters)
    apply_pirates_roster_amendment(cards, rosters)
    apply_phillies_roster_amendment(cards, rosters)
    apply_twins_roster_amendment(cards, rosters)
    apply_white_sox_roster_amendment(cards, rosters)
    apply_orioles_roster_amendment(cards, rosters)
    apply_philadelphia_athletics_2026_roster_amendment(cards, rosters)
    apply_astros_roster_amendment(cards, rosters)
    apply_kansas_city_roster_amendment(cards, rosters)
    apply_mariners_roster_amendment(cards, rosters)
    apply_angels_roster_amendment(cards, rosters)
    apply_mets_roster_amendment(cards, rosters)
    apply_oakland_roster_amendment(cards, rosters)
    apply_milwaukee_roster_amendment(cards, rosters)
    apply_texas_roster_amendment(cards, rosters)
    apply_toronto_roster_amendment(cards, rosters)
    apply_colorado_roster_amendment(cards, rosters)
    retain_authorized_hitters(cards)
    retain_empty_team_cards(cards, rosters)
    apply_remaining_six_bench_swaps(cards, rosters)
    return cards, rosters, reconciliations, peak_notes


# These five were built from Lahman franchise seasons because the set
# files had no frozen card. A full rebuild starts from those files, so
# it has to copy the playable bodies back or the next build would drop
# them. A game import never reaches this path.
AUTHORIZED_HITTERS = (
    "ARI|peralda01",
    "MON|aloumo01",
    "HOU|aloumo01",
    "KC|maybejo01",
    "SEA|beltrad01",
    "LAA|carewro01",
    "NYM|johnsho01",
    "OAK|chaveer01",
    "MIL|oglivbe01",
    "TEX|sierrru01",
    "TOR|cartejo01",
    "COL|gonzaca01",
    "NYY|henderi01",
    "MIA|lowelmi01",
    "SD|gilesbr02",
    "TB|huffau01",
    "PHA|valoel01",
    "SF|irvinmo01",
    "DET|gibsoki01",
    "ATL|hornebo01",
    "PIT|wanerpa01",
    "PHI|kleinch01",
    "MIN|allisbo01",
)


def retain_authorized_hitters(cards):
    path = os.path.join(ROOT, "data", "cards.json")
    if not os.path.exists(path):
        return
    existing = load_json(path)
    for key in AUTHORIZED_HITTERS:
        old = existing.get(key) or {}
        if not (old.get("card_bat") or {}).get("sections"):
            continue
        entry = cards.get(key)
        if entry is None:
            cards[key] = old
            continue
        entry["card_bat"] = old["card_bat"]
        entry["peak_bat"] = old.get("peak_bat")
        entry["peak_bat_162"] = old.get("peak_bat_162")
        entry.pop("conversion_status", None)



# These clubs had no set-file cards. The sandbox build wrote their
# bodies from franchise seasons. A full rebuild starts from the set
# files, so it has to copy those bodies and the roster rows back. A
# game import never reaches this path.
EMPTY_TEAM_CODES = ("BAL", "CLE", "CWS", "HOU", "KC", "LAA", "MIL", "MIN", "NYM", "OAK", "PHI", "SEA", "MIA", "NYY")


def retain_empty_team_cards(cards, rosters):
    cards_path = os.path.join(ROOT, "data", "cards.json")
    rosters_path = os.path.join(ROOT, "data", "rosters.json")
    if not os.path.exists(cards_path) or not os.path.exists(rosters_path):
        return
    old_cards = load_json(cards_path)
    old_rosters = load_json(rosters_path)
    for code in EMPTY_TEAM_CODES:
        old_roster = old_rosters.get(code) or {}
        players = old_roster.get("players") or []
        if not players:
            continue
        rosters[code] = old_roster
        for player in players:
            key = "%s|%s" % (code, player["id"])
            previous = old_cards.get(key) or {}
            playable = (previous.get("card_bat") or {}).get("sections") or (
                previous.get("card_pit") or {}).get("table_2d6")
            if not playable:
                continue
            entry = cards.get(key)
            if entry is None:
                cards[key] = previous
                continue
            for field in ("card_bat", "card_pit", "peak_bat", "peak_bat_162",
                          "peak_pit", "peak_pit_162", "spots", "name"):
                if previous.get(field) is not None:
                    entry[field] = previous[field]
            entry.pop("conversion_status", None)
    # Preserve the two retired bullpen cards as immutable historical cards.
    # Neither pitched card may vanish after the active roster swaps.
    for frozen_key in ("NYY|reynoal01", "MIA|burneaj01"):
        if frozen_key in old_cards:
            cards[frozen_key] = old_cards[frozen_key]







def apply_remaining_six_bench_swaps(cards, rosters):
    """Approved Yankees / Marlins changes, after historical R1-01 games."""
    swaps = [
        ("NYY", "henderi01", "Rickey Henderson", "LF", "reynoal01"),
        ("MIA", "lowelmi01", "Mike Lowell", "3B", "burneaj01"),
    ]
    for code, player_id, name, pos, inactive_id in swaps:
        roster = rosters.get(code)
        if roster is None:
            continue
        players = roster["players"]
        players[:] = [p for p in players if p["id"] != inactive_id]
        found = [p for p in players if p["id"] == player_id]
        if not found:
            players.append({"group": "bench", "slot": 6, "id": player_id,
                            "name": name, "kind": "hitter", "pos": pos})
        elif len(found) != 1:
            raise SystemExit(code + " duplicate approved bench hitter")
        else:
            found[0].update(group="bench", slot=6, kind="hitter", pos=pos)
        order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
        players.sort(key=lambda p: (order[p["group"]], p["slot"]))
        counts = {g: sum(p["group"] == g for p in players) for g in order}
        if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
            raise SystemExit(code + " must remain 9/6/5/6")
        if len({p["id"] for p in players}) != 26:
            raise SystemExit(code + " must retain 26 unique active people")
        # Keep frozen original card contents, scores and recorded dice untouched.


def apply_colorado_roster_amendment(cards, rosters):
    """Owner-approved Carlos González for Ian Desmond, future games only.

    Only González's Colorado Rockies 2009-2018 seasons may be used for
    a frozen Hitter v0.5 or Peak 162. Preserve the Desmond source card,
    all original dice/FAC records and completed games.
    """
    roster = rosters.get("COL")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "desmoia01"]
    carlos_id = "gonzaca01"
    present = [p for p in players if p["id"] == carlos_id]
    if not present:
        players.append({"group": "bench", "id": carlos_id, "kind": "hitter",
                        "name": "Carlos González", "pos": "OF", "slot": 5})
    elif len(present) != 1:
        raise SystemExit("Duplicate Carlos González Colorado roster entry")
    else:
        present[0].update(group="bench", kind="hitter", pos="OF", slot=5)
    gonzalez_card = cards.get("COL|" + carlos_id)
    if gonzalez_card:
        gonzalez_card["spots"] = [{"group": "bench", "slot": 5,
                                  "pos": "OF", "kind": "hitter"}]
    # Keep the original COL|desmoia01 genuine card as historical data.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Colorado approved 9/6/5/6 mismatch: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Colorado must have 26 unique active players")
    dh = [p for p in players if p["group"] == "lineup" and p["slot"] == 9]
    if len(dh) != 1 or dh[0]["id"] != "galaran01" or dh[0]["pos"] != "DH":
        raise SystemExit("Colorado Galarraga DH changed without approval")


def apply_toronto_roster_amendment(cards, rosters):
    """Owner approved Joe Carter for Jim Clancy, Toronto 1991-1997 only.

    Keep all historical pitcher cards, original 9/5 starting lineup and
    five-man rotation, especially José Bautista batting fifth at DH.
    """
    roster = rosters.get("TOR")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "clancji01"]
    carter_id = "cartejo01"
    matches = [p for p in players if p["id"] == carter_id]
    if not matches:
        players.append({"group": "bench", "id": carter_id,
                        "kind": "hitter", "name": "Joe Carter",
                        "pos": "RF", "slot": 6})
    elif len(matches) != 1:
        raise SystemExit("Duplicate active Toronto Joe Carter")
    else:
        matches[0].update(group="bench", kind="hitter", pos="RF", slot=6)
    card = cards.get("TOR|" + carter_id)
    if card:
        card["spots"] = [{"group": "bench", "slot": 6,
                          "pos": "RF", "kind": "hitter"}]
    # The original authentic TOR|clancji01 historical card is retained.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Toronto approved active roster must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Toronto must retain 26 unique active players")
    if len([p for p in players if p["group"] == "lineup"
            and p["slot"] == 5 and p["id"] == "bautijo02"
            and p["pos"] == "DH"]) != 1:
        raise SystemExit("Toronto José Bautista starting DH altered")


def apply_texas_roster_amendment(cards, rosters):
    """Owner-approved Rubén Sierra for Kenny Rogers, Texas franchise only.

    Sierra's Rangers performance (1986-1992, 2000-2001, 2003) alone
    qualifies for his future frozen Hitter v0.5 card. Retain Rogers's
    original archived card and every already played game.
    """
    roster = rosters.get("TEX")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "rogerke01"]
    sierra_id = "sierrru01"
    found = [p for p in players if p["id"] == sierra_id]
    if not found:
        players.append({"group": "bench", "id": sierra_id,
                        "kind": "hitter", "name": "Rubén Sierra",
                        "pos": "RF", "slot": 6})
    elif len(found) != 1:
        raise SystemExit("Duplicate Texas Rubén Sierra active entry")
    else:
        found[0].update(group="bench", kind="hitter", pos="RF", slot=6)
    sierra_card = cards.get("TEX|" + sierra_id)
    if sierra_card:
        sierra_card["spots"] = [{"group": "bench", "slot": 6,
                                "pos": "RF", "kind": "hitter"}]
    knowles = [p for p in players if p["id"] == "knowlda01"
               and p["group"] == "bullpen"]
    if len(knowles) != 1:
        raise SystemExit("Darold Knowles missing from Texas bullpen")
    knowles[0]["slot"] = 6
    knowles_card = cards.get("TEX|knowlda01")
    if knowles_card:
        knowles_card["spots"] = [{"group": "bullpen", "slot": 6,
                                 "pos": "RP", "kind": "pitcher"}]
    # Never remove/modify the original TEX|rogerke01 historical pitching card.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Texas approved active roster must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Texas must have 26 distinct active players")
    dh = [p for p in players if p["group"] == "lineup" and p["slot"] == 9]
    if len(dh) != 1 or dh[0]["id"] != "seageco01" or dh[0]["pos"] != "DH":
        raise SystemExit("Texas Corey Seager DH changed without approval")


def apply_milwaukee_roster_amendment(cards, rosters):
    """Owner-approved Ben Oglivie for Freddy Peralta, Milwaukee-only 1978-1986.

    Preserve Peralta's original historical card; never fabricate Oglivie's
    frozen Hitter v0.5 conversion or alter any lineup, DH, SP or played game.
    """
    roster = rosters.get("MIL")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "peralfr01"]
    player_id = "oglivbe01"
    found = [p for p in players if p["id"] == player_id]
    if not found:
        players.append({"group": "bench", "id": player_id, "kind": "hitter",
                        "name": "Ben Oglivie", "pos": "LF", "slot": 6})
    elif len(found) != 1:
        raise SystemExit("Duplicate Milwaukee Ben Oglivie roster entries")
    else:
        found[0].update(group="bench", kind="hitter", pos="LF", slot=6)
    card = cards.get("MIL|" + player_id)
    if card:
        card["spots"] = [{"group": "bench", "slot": 6,
                          "pos": "LF", "kind": "hitter"}]
    # The original genuine MIL|peralfr01 card stays archived, unmodified.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Milwaukee approved roster must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Milwaukee must have 26 unique active players")
    dh = [p for p in players if p["group"] == "lineup" and p["slot"] == 4]
    if len(dh) != 1 or dh[0]["id"] != "fieldpr01" or dh[0]["pos"] != "DH":
        raise SystemExit("Milwaukee Prince Fielder DH changed without approval")


def apply_oakland_roster_amendment(cards, rosters):
    """Owner-approved Oakland Chavez for Gene Nelson; maintain DH untouched.

    Only Eric Chavez's Oakland Athletics (1998–2010) statistics qualify.
    Never remove archived Nelson conversion or fabricate Chavez's Hitter v0.5.
    PED decisions are separate and no starter may be changed here.
    """
    roster = rosters.get("OAK")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "nelsoge01"]
    chavez_id = "chaveer01"
    matches = [p for p in players if p["id"] == chavez_id]
    if not matches:
        players.append({"group": "bench", "id": chavez_id,
                        "kind": "hitter", "name": "Eric Chavez",
                        "pos": "3B", "slot": 6})
    elif len(matches) != 1:
        raise SystemExit("Oakland Eric Chavez appears more than once")
    else:
        matches[0].update(group="bench", kind="hitter", pos="3B", slot=6)
    card = cards.get("OAK|" + chavez_id)
    if card:
        card["spots"] = [{"group": "bench", "slot": 6,
                          "pos": "3B", "kind": "hitter"}]
    honey = [p for p in players if p["id"] == "honeyri01" and p["group"] == "bullpen"]
    if len(honey) != 1:
        raise SystemExit("Rick Honeycutt missing from Oakland bullpen")
    honey[0]["slot"] = 6
    historical_honey = cards.get("OAK|honeyri01")
    if historical_honey:
        historical_honey["spots"] = [{"group": "bullpen", "slot": 6,
                                      "pos": "RP", "kind": "pitcher"}]
    # OAK|nelsoge01 stays in historical converted card catalog unchanged.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {group: sum(p["group"] == group for p in players) for group in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Oakland requires exactly 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Oakland has duplicate or missing active players")
    if not any(p["group"] == "lineup" and p["slot"] == 5
               and p["id"] == "cansejo01" and p["pos"] == "DH" for p in players):
        raise SystemExit("Oakland DH changed without PED review approval")


def apply_mets_roster_amendment(cards, rosters):
    """Owner-approved Howard Johnson NYM 1985–1993 for Sid Fernandez.

    Keep Alonso DH sixth, Olerud fifth reserve and original historical
    converted cards/results. Never fabricate HoJo's frozen Hitter v0.5 card.
    """
    roster = rosters.get("NYM")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "fernasi01"]
    target = "johnsho01"
    existing = [p for p in players if p["id"] == target]
    if not existing:
        players.append({"group": "bench", "id": target, "kind": "hitter",
                        "name": "Howard Johnson", "pos": "3B", "slot": 6})
    elif len(existing) != 1:
        raise SystemExit("Duplicate Mets Howard Johnson active roster entries")
    else:
        existing[0].update(group="bench", kind="hitter", pos="3B", slot=6)
    card = cards.get("NYM|" + target)
    if card:
        card["spots"] = [{"group": "bench", "slot": 6,
                          "pos": "3B", "kind": "hitter"}]
    # The real NYM|fernasi01 historical pitching card remains in the catalog.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    totals = {g: sum(p["group"] == g for p in players) for g in order}
    if totals != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Mets approved roster must be 9/6/5/6: " + str(totals))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Mets must have 26 unique active players")
    for pid, group, slot, pos in (
        ("alonspe01", "lineup", 6, "DH"),
        ("olerujo01", "bench", 5, "UT"),
    ):
        if len([p for p in players if p["id"] == pid and p["group"] == group
                and p["slot"] == slot and p["pos"] == pos]) != 1:
            raise SystemExit("Mets approved DH / Olerud position changed: " + pid)


def apply_angels_roster_amendment(cards, rosters):
    """Owner approved Rod Carew (California 1979-1985) for Doug Corbett.

    Keep Ohtani leading off at DH and all other starting nine unchanged.
    Preserve Corbett's historical genuine card; Carew's Hitter v0.5
    conversion must be authentic and Angels-only, never fabricated.
    """
    roster = rosters.get("LAA")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "corbedo01"]
    carew_id = "carewro01"
    carew = [p for p in players if p["id"] == carew_id]
    if not carew:
        players.append({"group": "bench", "id": carew_id,
                        "kind": "hitter", "name": "Rod Carew",
                        "pos": "1B", "slot": 6})
    elif len(carew) != 1:
        raise SystemExit("Duplicate California Angels Rod Carew roster entries")
    else:
        carew[0].update(group="bench", slot=6, pos="1B", kind="hitter")
    card = cards.get("LAA|" + carew_id)
    if card:
        card["spots"] = [{"group": "bench", "slot": 6,
                          "pos": "1B", "kind": "hitter"}]
    for pid, slot in (("downssc01", 5), ("oliveda02", 6)):
        matches = [p for p in players if p["id"] == pid and p["group"] == "bullpen"]
        if len(matches) != 1:
            raise SystemExit("Angels missing remaining reliever: " + pid)
        matches[0]["slot"] = slot
        card = cards.get("LAA|" + pid)
        if card:
            card["spots"] = [{"group": "bullpen", "slot": slot,
                              "pos": "RP", "kind": "pitcher"}]
    # LAA|corbedo01 remains a historical genuine converted pitcher card.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Angels owner-approved active roster not 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Angels must have exactly 26 unique active players")
    if not any(p["group"] == "lineup" and p["slot"] == 1
               and p["id"] == "ohtansh01" and p["pos"] == "DH" for p in players):
        raise SystemExit("Shohei Ohtani must remain starting DH batting first")


def apply_mariners_roster_amendment(cards, rosters):
    """Owner-approved Seattle Beltré for Mike Moore, preserving historical cards.

    Beltré's eligibility and genuine future card use ONLY his 2005-2009
    Mariners seasons; no other franchise counts. All 26 slots validated.
    """
    roster = rosters.get("SEA")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "mooremi01"]
    beltre_id = "beltrad01"
    beltre = [p for p in players if p["id"] == beltre_id]
    if not beltre:
        players.append({"group": "bench", "id": beltre_id,
                        "kind": "hitter", "name": "Adrián Beltré",
                        "pos": "3B", "slot": 6})
    elif len(beltre) != 1:
        raise SystemExit("Duplicate Seattle Adrián Beltré entries")
    else:
        beltre[0].update(group="bench", kind="hitter", pos="3B", slot=6)
    card = cards.get("SEA|" + beltre_id)
    if card:
        card["spots"] = [{"group": "bench", "slot": 6,
                          "pos": "3B", "kind": "hitter"}]
    relief_ids = ("putzjj01", "munozan01", "diazed04",
                  "nelsoje01", "rhodear01", "sasakka01")
    for slot, pid in enumerate(relief_ids, 1):
        matches = [p for p in players if p["id"] == pid and p["group"] == "bullpen"]
        if len(matches) != 1:
            raise SystemExit("Seattle missing reliever " + pid)
        matches[0]["slot"] = slot
        card = cards.get("SEA|" + pid)
        if card:
            card["spots"] = [{"group": "bullpen", "slot": slot,
                              "pos": "RP", "kind": "pitcher"}]
    # SEA|mooremi01 must remain a genuine historical converted card.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Seattle approved roster must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Seattle must have 26 unique active players")
    if [(p["id"], p["pos"]) for p in players
        if p["group"] == "lineup" and p["slot"] == 4] != [("martied01", "DH")]:
        raise SystemExit("Edgar Martinez must remain starting DH batting fourth")


def apply_kansas_city_roster_amendment(cards, rosters):
    """Approved KC 9/6/5/6: Tartabull DH, McRae bench, Mayberry for Leibrandt.

    Count only Mayberry's Kansas City 1972-1977 franchise seasons.
    Preserve Leibrandt's original historical pitcher conversion and every
    earlier game. Never fabricate a Mayberry playable Hitter v0.5 card.
    """
    roster = rosters.get("KC")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "leibrch01"]
    for pid, group, slot, pos in (
        ("tartada01", "lineup", 2, "DH"),
        ("mcraeha01", "bench", 5, "DH"),
    ):
        matching = [p for p in players if p["id"] == pid]
        if len(matching) != 1:
            raise SystemExit("Kansas City required hitter missing or repeated: " + pid)
        matching[0].update(group=group, slot=slot, pos=pos, kind="hitter")
        card = cards.get("KC|" + pid)
        if card:
            card["spots"] = [{"group": group, "slot": slot, "pos": pos,
                              "kind": "hitter"}]
    mayberry = [p for p in players if p["id"] == "maybejo01"]
    if not mayberry:
        players.append({"group": "bench", "id": "maybejo01",
                        "kind": "hitter", "name": "John Mayberry",
                        "pos": "1B", "slot": 6})
    elif len(mayberry) != 1:
        raise SystemExit("Duplicate John Mayberry on the Royals roster")
    else:
        mayberry[0].update(group="bench", slot=6, pos="1B", kind="hitter")
    existing = cards.get("KC|maybejo01")
    if existing:
        existing["spots"] = [{"group": "bench", "slot": 6,
                              "pos": "1B", "kind": "hitter"}]
    # KC|leibrch01 remains in the converted-card catalog as historical.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Kansas City approved 9/6/5/6 mismatch: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Kansas City must have exactly 26 distinct players")


def apply_philadelphia_athletics_2026_roster_amendment(cards, rosters):
    """Owner-approved 1901-1954 Philadelphia Athletics 9/6/5/6 roster.

    Foxx becomes DH and Fain moves to 1B without changing batting order.
    Barry remains an original historical converted card; never delete it.
    Shantz is the sixth, left-handed long/swing arm (not an SP rotation
    promotion). No fake pitcher card is generated. Every earlier game stays
    untouched.
    """
    roster = rosters.get("PHA")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "barryja01"]
    index = {p["id"]: p for p in players}
    for pid, group, slot, pos, kind in (
        ("foxxji01", "lineup", 4, "DH", "hitter"),
        ("fainfe01", "lineup", 9, "1B", "hitter"),
        ("bishoma01", "bench", 5, "2B", "hitter"),
        ("valoel01", "bench", 6, "OF", "hitter"),
    ):
        if pid not in index:
            raise SystemExit("Philadelphia Athletics required player missing: " + pid)
        index[pid].update(group=group, slot=slot, pos=pos, kind=kind)
        card = cards.get("PHA|" + pid)
        if card:
            card["spots"] = [{"group": group, "slot": slot,
                              "pos": pos, "kind": kind}]
    pitcher_id = "shantbo01"
    found = [p for p in players if p["id"] == pitcher_id]
    if not found:
        players.append({
            "group": "bullpen", "id": pitcher_id,
            "kind": "pitcher", "name": "Bobby Shantz", "pos": "RP", "slot": 6,
        })
    elif len(found) != 1:
        raise SystemExit("Duplicate Bobby Shantz Athletics roster records")
    else:
        found[0].update(group="bullpen", kind="pitcher", pos="RP", slot=6)
    shantz_card = cards.get("PHA|" + pitcher_id)
    if shantz_card is None:
        shantz_card = {
            "id": pitcher_id, "name": "Bobby Shantz", "team": "PHA",
            "spots": [], "card_bat": None, "card_pit": None,
            "peak_bat": None, "peak_bat_162": None,
            "peak_pit": None, "peak_pit_162": None, "tournament": None,
        }
        cards["PHA|" + pitcher_id] = shantz_card
    shantz_card["spots"] = [{
        "group": "bullpen", "slot": 6, "pos": "RP", "kind": "pitcher",
    }]
    if not shantz_card.get("card_pit"):
        shantz_card["conversion_status"] = (
            "PENDING: frozen Pitcher v0.2.3 Philadelphia-only conversion;"
            " not yet playable. Includes Philadelphia seasons 1949-1954 only."
        )
    else:
        shantz_card.pop("conversion_status", None)
    # Preserve PHA|barryja01 unchanged as an archived former roster player.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {group: sum(p["group"] == group for p in players) for group in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Philadelphia Athletics approved 9/6/5/6 invalid: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Philadelphia Athletics need 26 unique active people")


def apply_owner_roster_amendments(cards, rosters):
    """Keep the staged PHA converted-set view aligned with Joe's dated owner card.

    The original external set directory has not yet been regenerated. This
    function does not invent dice. A playable Valo card already stored in
    data/cards.json is copied back by retain_authorized_hitters.
    """
    roster = rosters.get("PHA")
    if roster is None:
        return
    players = roster["players"]
    index = {p["id"]: p for p in players}
    for player_id in ("fainfe01", "bishoma01"):
        if player_id not in index:
            raise SystemExit("PHA roster amendment missing " + player_id)

    index["fainfe01"].update(group="lineup", slot=9, pos="DH")
    index["bishoma01"].update(group="bench", slot=6, pos="2B")

    players[:] = [p for p in players if p["id"] != "earnsge01"]
    cards.pop("PHA|earnsge01", None)
    valo_id = "valoel01"
    if valo_id not in index:
        players.append({
            "group": "bench", "id": valo_id, "kind": "hitter",
            "name": "Elmer Valo", "pos": "OF", "slot": 7,
        })
    else:
        index[valo_id].update(group="bench", slot=7, pos="OF")

    for player_id in ("fainfe01", "bishoma01"):
        card = cards["PHA|" + player_id]
        spot = index[player_id]
        card["spots"] = [{
            "group": spot["group"], "kind": "hitter",
            "pos": spot["pos"], "slot": spot["slot"],
        }]

    # No dice are invented here. A missing card stays pending. A playable
    # body already on disk is restored by retain_authorized_hitters.
    valocard = cards.get("PHA|" + valo_id)
    if valocard is None:
        valocard = {
            "id": valo_id, "name": "Elmer Valo", "team": "PHA",
            "spots": [], "card_bat": None, "card_pit": None,
            "peak_bat": None, "peak_bat_162": None,
            "peak_pit": None, "peak_pit_162": None, "tournament": None,
        }
        cards["PHA|" + valo_id] = valocard
    valocard["spots"] = [{
        "group": "bench", "kind": "hitter", "pos": "OF", "slot": 7,
    }]
    if valocard.get("card_bat") is None:
        valocard["conversion_status"] = (
            "PENDING: frozen Hitter v0.5 card source not available; "
            "not yet playable"
        )
    else:
        valocard.pop("conversion_status", None)

    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {group: sum(p["group"] == group for p in players) for group in order}
    if counts != {"lineup": 9, "bench": 7, "rotation": 5, "bullpen": 5}:
        raise SystemExit("PHA owner roster slot mismatch: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("PHA owner roster requires 26 distinct players")


def apply_padres_roster_amendment(cards, rosters):
    """Owner-approved San Diego 6 bench / 6 relievers roster amendment.

    Brian Giles replaces Craig Lefferts on the ACTIVE 26. This function
    does not invent dice. A playable Giles card already stored in
    data/cards.json is copied back by retain_authorized_hitters. Preserve
    the already-converted Lefferts card as a historical record, without
    listing him as active.
    """
    roster = rosters.get("SD")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "leffecr01"]
    giles_id = "gilesbr02"
    existing = [p for p in players if p["id"] == giles_id]
    if not existing:
        players.append({
            "group": "bench", "id": giles_id, "kind": "hitter",
            "name": "Brian Giles", "pos": "OF", "slot": 6,
        })
    else:
        if len(existing) != 1:
            raise SystemExit("duplicate Padres Brian Giles roster entries")
        existing[0].update(group="bench", slot=6, pos="OF", kind="hitter")
    if "SD|" + giles_id in cards:
        card = cards["SD|" + giles_id]
        card["spots"] = [
            {"group": "bench", "slot": 6, "pos": "OF", "kind": "hitter"},
        ]
    # Approved lineup semantics: Ken Caminiti starts at DH, while 3B
    # remains an eligible alternative. Machado is the starting third baseman.
    # Only active roster metadata changes; frozen historical card is retained.
    caminiti = [p for p in players if p["id"] == "caminke01"
                and p["group"] == "lineup" and p["slot"] == 4]
    machado = [p for p in players if p["id"] == "machama01"
               and p["group"] == "lineup" and p["slot"] == 6]
    if len(caminiti) != 1 or len(machado) != 1 or machado[0]["pos"] != "3B":
        raise SystemExit("San Diego original fourth and sixth batting slots were altered")
    caminiti[0]["pos"] = "DH"
    caminiti[0]["eligible_positions"] = ["3B", "DH"]
    # Do not rewrite SD|caminke01's historical card spots/dice source.

    # Lefferts stays in cards if present as archived source data, but no
    # longer occupies an active roster slot. No data is destroyed here.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    groups = {name: sum(p["group"] == name for p in players) for name in order}
    if groups != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Padres owner roster must be 9/6/5/6: " + str(groups))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Padres owner roster requires 26 distinct players")



def apply_expos_roster_amendment(cards, rosters):
    """Owner-approved Montreal Alou/Fassero swap; no invented hitter card.

    The original set may still list Fassero. Keep that existing pitcher
    card for historical inspection, but not among the active 26. This
    function does not invent dice. A playable Alou card already stored
    in data/cards.json is copied back by retain_authorized_hitters.
    """
    roster = rosters.get("MON")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "fasseje01"]
    alou_id = "aloumo01"
    matching = [p for p in players if p["id"] == alou_id]
    if not matching:
        players.append({
            "group": "bench", "id": alou_id, "kind": "hitter",
            "name": "Moises Alou", "pos": "OF", "slot": 6,
        })
    else:
        if len(matching) != 1:
            raise SystemExit("duplicate Expos Moises Alou roster entries")
        matching[0].update(group="bench", kind="hitter", pos="OF", slot=6)
    if "MON|" + alou_id in cards:
        cards["MON|" + alou_id]["spots"] = [
            {"group": "bench", "kind": "hitter", "pos": "OF", "slot": 6},
        ]
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {group: sum(p["group"] == group for p in players) for group in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Expos owner roster must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Expos owner roster requires 26 distinct players")



def apply_diamondbacks_roster_amendment(cards, rosters):
    """Joe-approved Arizona 6/6 switch after R1-04.

    The original converted set contains Juan Cruz. Keep that card and
    any R1-04 results unchanged as historical data, but remove Cruz
    from the active roster. David Peralta occupies bench LF6. This
    function does not invent dice. A playable Peralta card already
    stored in data/cards.json is copied back by retain_authorized_hitters.
    """
    roster = rosters.get("ARI")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "cruzju02"]
    player_id = "peralda01"
    matches = [p for p in players if p["id"] == player_id]
    if not matches:
        players.append({
            "group": "bench", "id": player_id, "kind": "hitter",
            "name": "David Peralta", "pos": "LF", "slot": 6,
        })
    else:
        if len(matches) != 1:
            raise SystemExit("duplicate Diamondbacks David Peralta roster entries")
        matches[0].update(group="bench", kind="hitter", pos="LF", slot=6)
    card = cards.get("ARI|" + player_id)
    if card:
        card["spots"] = [
            {"group": "bench", "kind": "hitter", "pos": "LF", "slot": 6},
        ]
    # Owner-approved Arizona lineup metadata correction, effective after R1-04.
    # Walker starts DH in batting slot 5 but is also eligible at first base.
    # Goldschmidt is the unchanged 1B starter in batting slot 2.
    # Do NOT mutate any frozen historical card/spot or prior game.
    walker = [p for p in players if p["id"] == "walkech02"
              and p["group"] == "lineup" and p["slot"] == 5]
    goldschmidt = [p for p in players if p["id"] == "goldspa01"
                   and p["group"] == "lineup" and p["slot"] == 2]
    if len(walker) != 1 or len(goldschmidt) != 1 or goldschmidt[0]["pos"] != "1B":
        raise SystemExit("Arizona Walker DH / Goldschmidt 1B lineup roles changed")
    walker[0]["pos"] = "DH"
    walker[0]["eligible_positions"] = ["1B", "DH"]
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {group: sum(p["group"] == group for p in players) for group in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Arizona owner roster must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Arizona owner roster requires 26 distinct players")



def apply_rays_roster_amendment(cards, rosters):
    """Joe-approved 2026-10-26 Tampa Bay 6-bench/6-reliever roster.

    Huff replaces Kevin Kelly on the active 26 after R1-03. Preserve
    Kelly's previously converted card, appearances and tournament lines
    as historical records. This function does not invent dice. A playable
    Huff card already stored in data/cards.json is copied back by
    retain_authorized_hitters.
    """
    roster = rosters.get("TB")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "kellyke02"]
    huff_id = "huffau01"
    matching = [p for p in players if p["id"] == huff_id]
    if not matching:
        players.append({
            "group": "bench", "id": huff_id, "kind": "hitter",
            "name": "Aubrey Huff", "pos": "OF", "slot": 6,
        })
    else:
        if len(matching) != 1:
            raise SystemExit("duplicate Tampa Bay Aubrey Huff roster entries")
        matching[0].update(group="bench", slot=6, pos="OF", kind="hitter")
    if "TB|" + huff_id in cards:
        cards["TB|" + huff_id]["spots"] = [
            {"group": "bench", "slot": 6, "pos": "OF", "kind": "hitter"},
        ]
    # The surviving long/left-handed reliever moves from old RP7 to RP6.
    howell = [p for p in players if p["id"] == "howeljp01"]
    if len(howell) != 1 or howell[0]["group"] != "bullpen":
        raise SystemExit("Rays missing J.P. Howell in active bullpen")
    howell[0]["slot"] = 6
    if "TB|howeljp01" in cards:
        card = cards["TB|howeljp01"]
        card["spots"] = [
            {"group": "bullpen", "kind": "pitcher", "pos": "RP", "slot": 6},
        ]
    # Do NOT remove TB|kellyke02 from the archive. A missing Huff card
    # stays missing until retain_authorized_hitters copies a stored one.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    groups = {group: sum(p["group"] == group for p in players) for group in order}
    if groups != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Rays owner roster must be 9/6/5/6: " + str(groups))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Rays owner roster requires 26 distinct players")



def apply_nationals_roster_amendment(cards, rosters):
    """Joe-approved 2026-10-26 Washington roster change, future games only.

    Jayson Werth replaces Craig Stammen in the active 26 after R1-02.
    Preserve Stammen's original converted card and all archived series
    results. Never invent a Hitter v0.5 card for Werth.
    """
    roster = rosters.get("WSH")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "stammcr01"]
    werth_id = "werthja01"
    existing = [p for p in players if p["id"] == werth_id]
    if not existing:
        players.append({
            "group": "bench", "id": werth_id, "kind": "hitter",
            "name": "Jayson Werth", "pos": "OF", "slot": 6,
        })
    else:
        if len(existing) != 1:
            raise SystemExit("duplicate Nationals Jayson Werth roster entries")
        existing[0].update(group="bench", kind="hitter", pos="OF", slot=6)
    if "WSH|" + werth_id in cards:
        cards["WSH|" + werth_id]["spots"] = [{
            "group": "bench", "kind": "hitter", "pos": "OF", "slot": 6,
        }]
    # Stammen's original card remains in cards as historical data;
    # the roster membership is the only removal performed.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Nationals owner roster must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Nationals owner roster requires 26 distinct players")


def apply_giants_roster_amendment(cards, rosters):
    """Joe-approved 2026-10-27 Giants post-R1-02 6/6 active roster.

    Monte Irvin takes bench LF6 in place of Javier Lopez as a reliever.
    Archive all prior cards and games; never fabricate the genuine
    frozen Hitter v0.5 conversion or a Giants-franchise-only peak line.
    """
    roster = rosters.get("SF")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "lopezja02"]
    irvin_id = "irvinmo01"
    matches = [p for p in players if p["id"] == irvin_id]
    if not matches:
        players.append({
            "group": "bench", "id": irvin_id, "kind": "hitter",
            "name": "Monte Irvin", "pos": "LF", "slot": 6,
        })
    else:
        if len(matches) != 1:
            raise SystemExit("duplicate Giants Monte Irvin roster entries")
        matches[0].update(group="bench", kind="hitter", pos="LF", slot=6)
    # An existing authentic Irvin card may be used, not invented.
    # retain_authorized_hitters() preserves any original conversion
    # already present in data/cards.json on a full set-file rebuild.
    if "SF|" + irvin_id in cards:
        cards["SF|" + irvin_id]["spots"] = [
            {"group": "bench", "kind": "hitter", "pos": "LF", "slot": 6}
        ]
    # Do not delete or modify SF|lopezja02 (historical card).
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Giants owner roster must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Giants owner roster requires 26 distinct players")


def apply_tigers_roster_amendment(cards, rosters):
    """Joe-approved 2026-10-27 active Detroit 6/6 after completed R1-04.

    Add Kirk Gibson OF/PR at bench6, inactivate Tyler Holton. Preserve
    all original converted cards, including Holton's, and played games.
    Keep existing authentic Kirk Gibson cards if one was already stored;
    never generate placeholder dice or fictional franchise peak ratings.
    """
    roster = rosters.get("DET")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "holtoty01"]
    gibson_id = "gibsoki01"
    matching = [p for p in players if p["id"] == gibson_id]
    if not matching:
        players.append({
            "group": "bench", "id": gibson_id, "kind": "hitter",
            "name": "Kirk Gibson", "pos": "OF", "slot": 6,
        })
    else:
        if len(matching) != 1:
            raise SystemExit("duplicate Detroit Kirk Gibson roster entries")
        matching[0].update(group="bench", kind="hitter", pos="OF", slot=6)
    # Existing cards can point at updated roster spots; never remove
    # or rewrite Holton's archived chart or historical pitching stats.
    for player_id, group, slot, pos, kind in (
        (gibson_id, "bench", 6, "OF", "hitter"),
        ("troutdi01", "bullpen", 5, "RP", "pitcher"),
        ("mclaide01", "bullpen", 6, "RP", "pitcher"),
    ):
        found = [p for p in players if p["id"] == player_id]
        if len(found) != 1:
            raise SystemExit("Detroit missing active role: " + player_id)
        found[0].update(group=group, slot=slot, pos=pos, kind=kind)
        card = cards.get("DET|" + player_id)
        if card:
            card["spots"] = [{
                "group": group, "slot": slot, "pos": pos, "kind": kind,
            }]
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Detroit approved 26 must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Detroit must carry 26 unique active players")


def apply_braves_roster_amendment(cards, rosters):
    """Joe-approved Atlanta 6/6: Horner for Wohlers, future games only.

    Keep Niekro in long/emergency relief and preserve all existing
    Mark Wohlers cards and any historical records unchanged.
    Bob Horner requires a genuine Braves-only Hitter v0.5 conversion.
    """
    roster = rosters.get("ATL")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "wohlema01"]
    horner_id = "hornebo01"
    found = [p for p in players if p["id"] == horner_id]
    if not found:
        players.append({
            "group": "bench", "id": horner_id, "kind": "hitter",
            "name": "Bob Horner", "pos": "3B", "slot": 6,
        })
    elif len(found) != 1:
        raise SystemExit("duplicate Atlanta Bob Horner roster entries")
    else:
        found[0].update(group="bench", kind="hitter", pos="3B", slot=6)
    # A stored authentic Horner card survives complete set rebuilds.
    # Never invent card bands, statistical peaks or performance ratings.
    for player_id, group, slot, pos, kind in (
        (horner_id, "bench", 6, "3B", "hitter"),
        ("ventejo01", "bullpen", 5, "RP", "pitcher"),
        ("niekrph01", "bullpen", 6, "RP", "pitcher"),
    ):
        match = [p for p in players if p["id"] == player_id]
        if len(match) != 1:
            raise SystemExit("Atlanta missing active role: " + player_id)
        match[0].update(group=group, slot=slot, pos=pos, kind=kind)
        card = cards.get("ATL|" + player_id)
        if card:
            card["spots"] = [{
                "group": group, "slot": slot, "pos": pos, "kind": kind,
            }]
    # Historical ATL|wohlema01 is not deleted or edited here.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Atlanta approved 26 must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Atlanta requires 26 unique active players")


def apply_pirates_roster_amendment(cards, rosters):
    """Joe-approved Pittsburgh Waner-for-McBean active 6/6 amendment.

    Active roster for future games only: bench6 Paul Waner, remove
    Al McBean; preserve every original converted card (including the
    inactive McBean card), completed game and FAC/dice archive.
    Waner's genuine Pittsburgh-only Hitter v0.5 conversion is pending.
    """
    roster = rosters.get("PIT")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "mcbeaal01"]
    waner_id = "wanerpa01"
    matching = [p for p in players if p["id"] == waner_id]
    if not matching:
        players.append({
            "group": "bench", "id": waner_id, "kind": "hitter",
            "name": "Paul Waner", "pos": "RF", "slot": 6,
        })
    elif len(matching) != 1:
        raise SystemExit("Duplicate Paul Waner roster entries for Pirates")
    else:
        matching[0].update(group="bench", kind="hitter", pos="RF", slot=6)
    for player_id, group, slot, pos, kind in (
        (waner_id, "bench", 6, "RF", "hitter"),
        ("jacksgr01", "bullpen", 5, "RP", "pitcher"),
        ("leevesa01", "bullpen", 6, "RP", "pitcher"),
    ):
        role = [p for p in players if p["id"] == player_id]
        if len(role) != 1:
            raise SystemExit("Pirates missing roster role: " + player_id)
        role[0].update(group=group, slot=slot, pos=pos, kind=kind)
        if "PIT|" + player_id in cards:
            cards["PIT|" + player_id]["spots"] = [{
                "group": group, "slot": slot, "pos": pos, "kind": kind,
            }]
    # Never delete PIT|mcbeaal01: its pitching chart is historical.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Pirates must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Pirates must have 26 unique active players")


def apply_phillies_roster_amendment(cards, rosters):
    """Joe-approved Phillies Chuck Klein/Ryan Madson 9/6/5/6 active 26.

    Keep all original converted player cards (including Ryan Madson)
    and historical games unchanged. Klein's authentic Phillies-only
    Hitter v0.5 card must be converted later without invented values.
    """
    roster = rosters.get("PHI")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "madsory01"]
    klein_id = "kleinch01"
    matches = [p for p in players if p["id"] == klein_id]
    if not matches:
        players.append({
            "group": "bench", "id": klein_id, "kind": "hitter",
            "name": "Chuck Klein", "pos": "RF", "slot": 6,
        })
    elif len(matches) != 1:
        raise SystemExit("duplicate Chuck Klein Phillies roster entries")
    else:
        matches[0].update(group="bench", kind="hitter", pos="RF", slot=6)
    # Genuine historic converted cards remain, including PHI|madsory01.
    # All existing active late-bullpen pitchers shift up one slot.
    for player_id, group, slot, pos, kind in (
        (klein_id, "bench", 6, "RF", "hitter"),
        ("mcgratu01", "bullpen", 3, "RP", "pitcher"),
        ("reedro01", "bullpen", 4, "RP", "pitcher"),
        ("lidgebr01", "bullpen", 5, "RP", "pitcher"),
        ("suarera01", "bullpen", 6, "RP", "pitcher"),
    ):
        found = [p for p in players if p["id"] == player_id]
        if len(found) != 1:
            raise SystemExit("Phillies active role missing: " + player_id)
        found[0].update(group=group, slot=slot, pos=pos, kind=kind)
        card = cards.get("PHI|" + player_id)
        if card:
            card["spots"] = [{
                "group": group, "slot": slot, "pos": pos, "kind": kind,
            }]
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Phillies approved roster must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Phillies approved roster needs 26 distinct active players")


def apply_astros_roster_amendment(cards, rosters):
    """Owner-approved Houston Alou 1998/2000/2001 for Octavio Dotel.

    All original conversions, including HOU Dotel and MON Alou, remain
    archived. Never fabricate a Houston Hitter v0.5 card or rewrite games.
    """
    roster = rosters.get("HOU")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "doteloc01"]
    alou_id = "aloumo01"
    found = [p for p in players if p["id"] == alou_id]
    if not found:
        players.append({"group": "bench", "id": alou_id, "kind": "hitter",
                        "name": "Moisés Alou", "pos": "LF", "slot": 6})
    elif len(found) != 1:
        raise SystemExit("Houston Moises Alou appears more than once")
    else:
        found[0].update(group="bench", kind="hitter", pos="LF", slot=6)
    for pid, group, slot, pos, kind in (
        (alou_id, "bench", 6, "LF", "hitter"),
        ("sambijo01", "bullpen", 5, "RP", "pitcher"),
        ("smithda02", "bullpen", 6, "RP", "pitcher"),
    ):
        matches = [p for p in players if p["id"] == pid]
        if len(matches) != 1:
            raise SystemExit("Houston active role missing: " + pid)
        matches[0].update(group=group, slot=slot, pos=pos, kind=kind)
        card = cards.get("HOU|" + pid)
        if card:
            card["spots"] = [{"group": group, "slot": slot,
                              "pos": pos, "kind": kind}]
    # HOU|doteloc01 remains historical; MON|aloumo01 is a separate club.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Houston active roster must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Houston active roster needs 26 distinct players")


def apply_orioles_roster_amendment(cards, rosters):
    """Owner-approved Browns George Sisler replaces Sammy Stewart, BAL 9/6/5/6.

    Keep all genuine prior conversions and original played-game archives.
    Sisler's Hitter v0.5 card needs authentic Browns-only input; never
    invent dice values or silently discard Stewart's historical card.
    """
    roster = rosters.get("BAL")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "stewasa01"]
    sisler_id = "sislege01"
    matches = [p for p in players if p["id"] == sisler_id]
    if not matches:
        players.append({"group": "bench", "id": sisler_id, "kind": "hitter",
                        "name": "George Sisler", "pos": "1B", "slot": 6})
    elif len(matches) != 1:
        raise SystemExit("duplicate BAL George Sisler roster entries")
    else:
        matches[0].update(group="bench", kind="hitter", pos="1B", slot=6)
    card = cards.get("BAL|" + sisler_id)
    if card:
        card["spots"] = [{"group": "bench", "kind": "hitter",
                          "pos": "1B", "slot": 6}]
    # BAL|stewasa01 remains an original archived historical conversion.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Baltimore approved roster must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Baltimore needs exactly 26 distinct active players")


def apply_white_sox_roster_amendment(cards, rosters):
    """Owner-approved Chicago Dick Allen / Bob Locker 9/6/5/6."""
    roster = rosters.get("CWS")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "lockebo02"]
    matching = [p for p in players if p["id"] == "allendi01"]
    if not matching:
        players.append({"group": "bench", "id": "allendi01", "kind": "hitter",
                        "name": "Dick Allen", "pos": "1B", "slot": 6})
    elif len(matching) != 1:
        raise SystemExit("duplicate Chicago Dick Allen roster entry")
    else:
        matching[0].update(group="bench", kind="hitter", pos="1B", slot=6)
    for pid, group, slot, pos, kind in (
        ("allendi01", "bench", 6, "1B", "hitter"),
        ("marteda01", "bullpen", 5, "RP", "pitcher"),
        ("cicoted01", "bullpen", 6, "RP", "pitcher"),
    ):
        found = [p for p in players if p["id"] == pid]
        if len(found) != 1:
            raise SystemExit("Chicago active role missing: " + pid)
        found[0].update(group=group, slot=slot, pos=pos, kind=kind)
        card = cards.get("CWS|" + pid)
        if card:
            card["spots"] = [{"group": group, "slot": slot,
                              "pos": pos, "kind": kind}]
    # The original CWS|lockebo02 pitching card remains archived and intact.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Chicago active roster must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Chicago must have 26 distinct active players")


def apply_twins_roster_amendment(cards, rosters):
    """Joe-approved Twins Allison replaces Marberry, future active 9/6/5/6.

    Archive all genuine converted cards (including Firpo Marberry),
    older data and any completed game; never create a guessed hitter
    card for Bob Allison. Franchise seasons include Senators/Twins.
    """
    roster = rosters.get("MIN")
    if roster is None:
        return
    players = roster["players"]
    players[:] = [p for p in players if p["id"] != "marbefi01"]
    allison_id = "allisbo01"
    existing = [p for p in players if p["id"] == allison_id]
    if not existing:
        players.append({
            "group": "bench", "id": allison_id, "kind": "hitter",
            "name": "Bob Allison", "pos": "RF", "slot": 6,
        })
    elif len(existing) != 1:
        raise SystemExit("duplicate Bob Allison Minnesota roster entries")
    else:
        existing[0].update(group="bench", kind="hitter", pos="RF", slot=6)
    for player_id, group, slot, pos, kind in (
        (allison_id, "bench", 6, "RF", "hitter"),
        ("duranjh01", "bullpen", 4, "RP", "pitcher"),
        ("rogerta01", "bullpen", 5, "RP", "pitcher"),
        ("perryji01", "bullpen", 6, "RP", "pitcher"),
    ):
        found = [p for p in players if p["id"] == player_id]
        if len(found) != 1:
            raise SystemExit("Twins approved active role missing: " + player_id)
        found[0].update(group=group, slot=slot, pos=pos, kind=kind)
        card = cards.get("MIN|" + player_id)
        if card:
            card["spots"] = [{
                "group": group, "slot": slot, "pos": pos, "kind": kind,
            }]
    # MIN|marbefi01 remains untouched as a historical converted card.
    order = {"lineup": 0, "bench": 1, "rotation": 2, "bullpen": 3}
    players.sort(key=lambda p: (order[p["group"]], p["slot"]))
    counts = {g: sum(p["group"] == g for p in players) for g in order}
    if counts != {"lineup": 9, "bench": 6, "rotation": 5, "bullpen": 6}:
        raise SystemExit("Minnesota approved roster must be 9/6/5/6: " + str(counts))
    if len({p["id"] for p in players}) != 26:
        raise SystemExit("Minnesota approved roster needs 26 distinct active players")


def dump(obj, path):
    text = json.dumps(obj, indent=1, sort_keys=True) + "\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def refresh_tournament_lines(cards, archive):
    """Replace only each card's tournament block.

    Matching is by club and normalized name, the same key the archive
    uses. A card with no appearance gets tournament null. Nothing else
    on the card is read for writing.
    """
    master_ids, master_lines, master_decisions = tournament_index(archive)
    changed = 0
    for card in cards.values():
        key = (card.get("team"), norm_name(card.get("name")))
        updated = aggregate_tournament(
            key, master_lines, master_decisions, master_ids)
        if card.get("tournament") != updated:
            card["tournament"] = updated
            changed += 1
    return changed


def preserve_existing_cards():
    """Refresh tournament lines and leave repaired card bodies in place."""
    cards_path = os.path.join(ROOT, "data", "cards.json")
    cards = load_json(cards_path)
    archive = load_json(os.path.join(ROOT, "tournament_results.json"))
    changed = refresh_tournament_lines(cards, archive)
    dump(cards, cards_path)
    print("preserved repaired card bodies")
    print("players: %d" % len(cards))
    print("tournament lines refreshed: %d" % changed)
    print("data/rosters.json was not rewritten")
    return 0


def main():
    cards_path = os.path.join(ROOT, "data", "cards.json")
    rebuild = os.environ.get("PP_REBUILD_CARDS_FROM_SETS") == "1"
    if os.path.exists(cards_path) and not rebuild:
        return preserve_existing_cards()
    cards, rosters, reconciliations, peak_notes = build()
    dump(rosters, os.path.join(ROOT, "data", "rosters.json"))
    dump(cards, os.path.join(ROOT, "data", "cards.json"))
    with_stats = sum(1 for c in cards.values() if c["tournament"])
    print("clubs: %d" % len(rosters))
    print("players: %d" % len(cards))
    print("players with tournament lines: %d" % with_stats)
    print("roster spots: %d" % sum(len(r["players"]) for r in rosters.values()))
    print("peak 162 blocks: %d batting, %d pitching" % (
        sum(1 for c in cards.values() if c["peak_bat_162"]),
        sum(1 for c in cards.values() if c["peak_pit_162"])))
    for line in reconciliations:
        print("reconciled: " + line)
    for line in peak_notes:
        print("peak scale: " + line)
    print("wrote data/rosters.json and data/cards.json")


if __name__ == "__main__":
    sys.exit(main())
