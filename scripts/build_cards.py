#!/usr/bin/env python3
"""Build the roster and player-card data the site serves.

Reads the converted Payoff Pitch sets and the master tournament archive
from the workspace, and writes two files the viewer loads at boot:

  data/rosters.json  one entry per converted club: the 26 roster spots
                     in set order (lineup, bench, rotation, bullpen)
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
  the repo's own tournament_results.json supplies club names, seeds, and
  the player ids the site already publishes

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
The build is deterministic: a second run with unchanged inputs writes
byte-identical files.
"""

import csv
import json
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

BAT_COUNTING = ["G", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB",
                "IBB", "SO", "HBP", "SB", "CS", "GIDP", "SF"]
ARCHIVE_BAT = [("ab", "ab"), ("r", "r"), ("h", "h"), ("doubles", "2b"),
               ("triples", "3b"), ("hr", "hr"), ("rbi", "rbi"), ("bb", "bb"),
               ("k", "so"), ("hbp", "hbp"), ("sb", "sb"), ("cs", "cs"),
               ("sac", "sac"), ("sf", "sf"), ("gidp", "gidp")]
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
                "peak_pit": None,
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

    return cards, rosters, reconciliations


def dump(obj, path):
    text = json.dumps(obj, indent=1, sort_keys=True) + "\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def main():
    cards, rosters, reconciliations = build()
    dump(rosters, os.path.join(ROOT, "data", "rosters.json"))
    dump(cards, os.path.join(ROOT, "data", "cards.json"))
    with_stats = sum(1 for c in cards.values() if c["tournament"])
    print("clubs: %d" % len(rosters))
    print("players: %d" % len(cards))
    print("players with tournament lines: %d" % with_stats)
    print("roster spots: %d" % sum(len(r["players"]) for r in rosters.values()))
    for line in reconciliations:
        print("reconciled: " + line)
    print("wrote data/rosters.json and data/cards.json")


if __name__ == "__main__":
    sys.exit(main())
