#!/usr/bin/env python3
"""Held-out accuracy of the card engines against the official 1986 set.

Rebuilds a stratified sample from the counting stats printed on the 1986
cards. Each player's own card is left out of the hitter comp pool. The
pitcher search is run twice: the tracker widening rule, and rulebook
page 39. Nothing here writes data/cards.json.
"""
from __future__ import annotations

import json
import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "engines", "hitter-v0.5"))
sys.path.insert(0, os.path.join(ROOT, "engines", "pitcher-v0.2.3"))
sys.path.insert(0, os.path.join(ROOT, "engines", "sim"))

import hitter_solver as hs  # noqa: E402
from calibration import full_pipeline  # noqa: E402
from historical_solver import solve_historical  # noqa: E402
from pa_sim import Batter, Pitcher, Tally, resolve_pa  # noqa: E402

REF = os.path.join(ROOT, "historical-cards", "reference")
OUT = os.path.join(ROOT, "historical-cards", "accuracy", "baseline.json")
SECTIONS = ("WHEELHOUSE", "PATIENT", "TOUGH", "IN-PLAY")
HANDS = ("vsLHP", "vsRHP")
WIDTH_KEYS = ("HR", "3B", "2B", "1B", "BB", "HBP", "SO")
SIM_N = 4000


def _load():
    cards = json.load(open(os.path.join(REF, "cards_1986.json")))["players"]
    parks = json.load(open(os.path.join(REF, "ballparks.json")))
    profiles = {row["name"]: row for row in json.load(open(os.path.join(REF, "card_profiles.json")))}
    hitters = [p for p in cards if not p.get("pitcher")]
    pitchers = [p for p in cards if p.get("pitcher")]
    return hitters, pitchers, parks, profiles


def _pa(player):
    return sum(side["AB"] + side["BB"] for side in player["stats_split"].values())


def _combine(player):
    totals = {"AB": 0, "H": 0, "2B": 0, "3B": 0, "HR": 0, "BB": 0, "SO": 0}
    for side in player["stats_split"].values():
        for key in totals:
            totals[key] += side[key]
    return totals


def _hitter_row(player):
    totals = _combine(player)
    pa = totals["AB"] + totals["BB"]
    pos = next((chip["pos"] for chip in player["positions"] if chip.get("pos")), "DH")
    return {
        "Name": player["name"],
        "Team": player.get("team") or "",
        "Bats": player.get("bats") or "R",
        "Throws": "R",
        "Position": pos,
        "Fielding": "average",
        "Arm": "average",
        "PA": pa,
        "AB": totals["AB"],
        "H": totals["H"],
        "2B": totals["2B"],
        "3B": totals["3B"],
        "HR": totals["HR"],
        "BB": totals["BB"],
        "IBB": 0,
        "SO": totals["SO"],
        "HBP": 0,
        "SB": 0,
        "CS": 0,
    }


def _width(table, key):
    rng = (table or {}).get(key)
    if not rng:
        return 0
    return int(rng[1]) - int(rng[0]) + 1


def _face_labels(rows):
    labels = {}
    for row in rows or []:
        lo, hi = row["range"]
        for face in range(int(lo), int(hi) + 1):
            labels[face] = row["result"]
    return labels


def _pick_hitters(hitters, profiles):
    pool = [p for p in hitters if _pa(p) >= 300 and not p.get("partial")]
    def rate(player, key):
        return profiles[player["name"]][key]
    picked = []
    seen = set()

    def take(rows, role):
        for player in rows:
            if player["name"] in seen:
                continue
            seen.add(player["name"])
            picked.append((player, role))
            if sum(1 for _p, r in picked if r == role) >= _need[role]:
                return

    _need = {"slugger": 10, "walker": 8, "contact": 8, "whiff": 8, "regular": 6}
    take(sorted(pool, key=lambda p: -rate(p, "hrp")), "slugger")
    take(sorted(pool, key=lambda p: -rate(p, "bbp")), "walker")
    median_hr = sorted(rate(p, "hrp") for p in pool)[len(pool) // 2]
    contact = [p for p in pool if rate(p, "hrp") <= median_hr]
    take(sorted(contact, key=lambda p: -rate(p, "avg")), "contact")
    take(sorted(pool, key=lambda p: -rate(p, "sop")), "whiff")
    rest = sorted((p for p in pool if p["name"] not in seen), key=lambda p: p["name"])
    step = max(1, len(rest) // 6)
    take(rest[::step], "regular")
    return picked


def _pick_pitchers(pitchers):
    def bf(player):
        stats = player["stats"]
        return stats["IP"] * 3.0 + stats["H"] + stats["BB"]

    def rate(player, key):
        stats = player["stats"]
        return stats[key] / bf(player) if bf(player) else 0

    by_name = {}
    for player in pitchers:
        by_name.setdefault(player["name"], player)
    chosen = []
    seen = set()

    def add(player, role):
        if player is None or player["name"] in seen:
            return
        if not player.get("stats"):
            return
        if bf(player) < 40 and role != "morris":
            return
        seen.add(player["name"])
        chosen.append((player, role))

    add(by_name.get("Jack Morris"), "morris")
    for name, role in (
        ("Bobby Witt", "range50"),
        ("Tom Henke", "range50"),
        ("Randy Myers", "range50"),
        ("Mark Clear", "range50"),
        ("Jose DeLeon (Chicago)", "range50"),
        ("Steve Davis", "range50"),
        ("Eric Plunk", "range50"),
        ("Dwayne Henry", "range50"),
    ):
        add(by_name.get(name), role)
    starters = [p for p in pitchers if p["stats"]["GS"] >= 20 and p["stats"]["IP"] >= 180]
    for player in sorted(starters, key=lambda p: -rate(p, "SO"))[:6]:
        add(player, "ace")
    relievers = [p for p in pitchers if p["stats"]["GS"] == 0 and p["stats"]["IP"] >= 55]
    for player in sorted(relievers, key=lambda p: -rate(p, "SO"))[:6]:
        add(player, "reliever")
    control = [p for p in pitchers if p["stats"]["GS"] >= 15 and p["stats"]["IP"] >= 150]
    for player in sorted(control, key=lambda p: rate(p, "BB"))[:4]:
        add(player, "control")
    pounded = [p for p in pitchers if p["stats"]["IP"] >= 120]
    for player in sorted(pounded, key=lambda p: -rate(p, "H"))[:4]:
        add(player, "contact-against")
    return chosen


def _band_errors(official, engine):
    rows = []
    for section in SECTIONS:
        for hand in HANDS:
            off = official["sections"][section][hand]
            eng = engine["sections"][section][hand]
            for key in WIDTH_KEYS:
                rows.append({
                    "section": section,
                    "hand": hand,
                    "key": key,
                    "official": _width(off, key),
                    "engine": _width(eng, key),
                })
    return rows


def _out_agreement(official, engine):
    off = _face_labels(official.get("out_table"))
    eng = _face_labels(engine.get("out_table"))
    if not off:
        return None
    same = sum(1 for face, label in off.items() if eng.get(face) == label)
    return {"faces": len(off), "same_label": same, "rate": same / len(off)}


def _slot_agreement(official, engine):
    off = official["pitcher"]["results"]
    same = sum(1 for slot in range(2, 13) if off.get(str(slot)) == engine.get(str(slot)))
    return {"slots": 11, "same": same}


def _as_batter(name, bats, run, sections):
    card = {
        "name": name,
        "card_bat": {"bats": bats or "R", "run": run, "sections": sections},
        "peak_bat": {},
    }
    return Batter(name, card)


def _as_pitcher(name, throws, table, bump):
    card = {
        "name": name,
        "card_pit": {
            "throws": throws or "R",
            "so_modifier": "+%d" % bump if bump else "NONE",
            "table_2d6": {str(n): table[str(n)] for n in range(2, 13)},
        },
        "peak_pit": {},
    }
    return Pitcher(name, card)


def _sim_hitter(batter, pitchers, parks, seed, n=SIM_N):
    rng = random.Random(seed)
    tally = Tally()
    guard = 0
    while tally.pa < n and guard < n * 4:
        guard += 1
        pitcher, so_range = pitchers[rng.randrange(len(pitchers))]
        event = resolve_pa(rng, batter, pitcher, parks=parks, so_range=so_range)
        tally.add(event)
    return tally.rates()


def _sim_pitcher(pitcher, batters, parks, so_range, seed, n=SIM_N):
    rng = random.Random(seed)
    tally = Tally()
    guard = 0
    while tally.pa < n and guard < n * 4:
        guard += 1
        batter = batters[rng.randrange(len(batters))]
        event = resolve_pa(rng, batter, pitcher, parks=parks, so_range=so_range)
        tally.add(event)
    rates = tally.rates()
    ab_bf = (tally.ab / tally.pa) if tally.pa else 1
    return {
        "k": rates["so"],
        "bb": rates["bb"],
        "hr": rates["hr"],
        "h": rates["avg"] * ab_bf,
        "pa": rates["pa"],
    }


def _mae(rows, pred):
    if not rows:
        return None
    return sum(abs(pred(row)) for row in rows) / len(rows)


def _bias(rows, pred):
    if not rows:
        return None
    return sum(pred(row) for row in rows) / len(rows)


def _round(value, digits=4):
    if value is None:
        return None
    return round(value, digits)


def main():
    hitters, pitchers, parks, profiles = _load()
    hitter_sample = _pick_hitters(hitters, profiles)
    pitcher_sample = _pick_pitchers(pitchers)
    print("hitter sample", len(hitter_sample), "pitcher sample", len(pitcher_sample))

    # Opponents for the hitter sim: every 1986 pitcher, with the printed
    # page-39 bump or the page-11 range when the card has one.
    opponents = []
    for player in pitchers:
        rating = (player["pitcher"].get("so_rating") or {})
        bump = rating.get("bump") or 0 if rating.get("kind") == "roll" else 0
        so_range = None
        if rating.get("kind") == "range":
            so_range = (rating["lo"], rating["hi"])
        table = player["pitcher"]["results"]
        if len(table) < 11:
            continue
        opponents.append((
            _as_pitcher(player["name"], player.get("throws"), table, bump),
            so_range,
        ))
    batter_pool = [
        _as_batter(player["name"], player.get("bats"), player.get("run"), player["sections"])
        for player in hitters
    ]

    hitter_rows = []
    band_rows = []
    out_rates = []
    for index, (player, role) in enumerate(hitter_sample, 1):
        row = _hitter_row(player)
        built = hs.build_one(row, exclude={player["name"]})
        card = built[0]
        bands = _band_errors(player, card)
        band_rows.extend(bands)
        out = _out_agreement(player, card)
        if out:
            out_rates.append(out["rate"])
        official = _as_batter(player["name"], player.get("bats"), player.get("run"), player["sections"])
        engine = _as_batter(player["name"], player.get("bats"), player.get("run"), card["sections"])
        seed = 1000 + index
        off_rates = _sim_hitter(official, opponents, parks, seed)
        eng_rates = _sim_hitter(engine, opponents, parks, seed + 50000)
        real = _combine(player)
        pa = real["AB"] + real["BB"]
        real_line = {
            "avg": real["H"] / real["AB"],
            "obp": (real["H"] + real["BB"]) / pa,
            "slg": (real["H"] + real["2B"] + 2 * real["3B"] + 3 * real["HR"]) / real["AB"],
            "hr": real["HR"] / pa,
            "bb": real["BB"] / pa,
            "so": real["SO"] / pa,
        }
        hitter_rows.append({
            "name": player["name"],
            "role": role,
            "pa": pa,
            "out_agreement": None if not out else _round(out["rate"], 3),
            "width_mae": _round(_mae(bands, lambda item: item["engine"] - item["official"]), 2),
            "sim_official": {key: _round(off_rates[key], 3) for key in ("avg", "obp", "slg", "hr", "bb", "so")},
            "sim_engine": {key: _round(eng_rates[key], 3) for key in ("avg", "obp", "slg", "hr", "bb", "so")},
            "real": {key: _round(real_line[key], 3) for key in real_line},
            "comp": built[3],
        })
        print("hitter", index, player["name"], hitter_rows[-1]["width_mae"])

    def summarize_bands(rows):
        summary = {"mae": _round(_mae(rows, lambda item: item["engine"] - item["official"]), 3),
                   "bias_engine_minus_official": _round(_bias(rows, lambda item: item["engine"] - item["official"]), 3)}
        by_key = {}
        for key in WIDTH_KEYS:
            subset = [item for item in rows if item["key"] == key]
            by_key[key] = {
                "mae": _round(_mae(subset, lambda item: item["engine"] - item["official"]), 3),
                "bias": _round(_bias(subset, lambda item: item["engine"] - item["official"]), 3),
            }
        summary["by_outcome"] = by_key
        return summary

    pitcher_rows = []
    for index, (player, role) in enumerate(pitcher_sample, 1):
        stats = player["stats"]
        bf = stats["IP"] * 3.0 + stats["H"] + stats["BB"]
        raw = {
            "h_bf": stats["H"] / bf,
            "bb_bf": stats["BB"] / bf,
            "so_bf": stats["SO"] / bf,
            "hr_bf": stats["HR"] / bf,
            "hbp_bf": 0.0053,
        }
        target = full_pipeline(raw, 1986)["solver_target"]
        hand = player.get("throws") or "R"
        widening = solve_historical(target, hand, restarts=8, seed=20 + index, so_rule="widening")
        printed = solve_historical(target, hand, restarts=8, seed=20 + index, so_rule="printed")
        rating = player["pitcher"].get("so_rating") or {}
        off_bump = rating.get("bump") if rating.get("kind") == "roll" else 0
        off_range = (rating["lo"], rating["hi"]) if rating.get("kind") == "range" else None
        official_p = _as_pitcher(player["name"], hand, player["pitcher"]["results"], off_bump or 0)
        wide_p = _as_pitcher(player["name"], hand, widening["table"], 0)
        # The printed solver's modifier is a page-39 shift. Simulate it that way.
        print_bump = 0 if printed["so_modifier"] == "NONE" else int(printed["so_modifier"])
        print_p = _as_pitcher(player["name"], hand, printed["table"], print_bump)
        # Widening's chosen +10/+20 is not a page-39 shift. The rulebook sim
        # leaves that card unshifted so the comparison is the chart itself.
        batters = [b for b in batter_pool if b.name != player["name"]]
        seed = 8000 + index
        off_sim = _sim_pitcher(official_p, batters, parks, off_range, seed)
        wide_sim = _sim_pitcher(wide_p, batters, parks, None, seed + 1)
        print_sim = _sim_pitcher(print_p, batters, parks, None, seed + 2)
        pitcher_rows.append({
            "name": player["name"],
            "role": role,
            "bf_estimate": round(bf, 1),
            "printed_so": rating or None,
            "widening_modifier": widening["so_modifier"],
            "printed_modifier": printed["so_modifier"],
            "slot_widening": _slot_agreement(player, widening["table"]),
            "slot_printed": _slot_agreement(player, printed["table"]),
            "real": {key: _round(raw[key], 3) for key in ("h_bf", "bb_bf", "so_bf", "hr_bf")},
            "sim_official": {key: _round(off_sim[key], 3) for key in ("k", "bb", "hr", "h")},
            "sim_widening": {key: _round(wide_sim[key], 3) for key in ("k", "bb", "hr", "h")},
            "sim_printed": {key: _round(print_sim[key], 3) for key in ("k", "bb", "hr", "h")},
            "official_table": player["pitcher"]["results"],
            "widening_table": widening["table"],
            "printed_table": printed["table"],
        })
        print("pitcher", index, player["name"], "slots", pitcher_rows[-1]["slot_widening"]["same"], pitcher_rows[-1]["slot_printed"]["same"])

    def sim_gap(rows, side, keys):
        out = {}
        for key in keys:
            gaps = [abs(row[side][key] - row["sim_official"][key]) for row in rows]
            out[key] = _round(sum(gaps) / len(gaps), 4)
        return out

    report = {
        "sample": {
            "hitters": [{"name": row["name"], "role": row["role"]} for row in hitter_rows],
            "pitchers": [{"name": row["name"], "role": row["role"]} for row in pitcher_rows],
        },
        "hitters": {
            "n": len(hitter_rows),
            "bands": summarize_bands(band_rows),
            "out_table_label_rate": _round(sum(out_rates) / len(out_rates), 3) if out_rates else None,
            "sim_gap_vs_official_card": sim_gap(hitter_rows, "sim_engine", ("avg", "obp", "slg", "hr", "bb", "so")),
            "players": hitter_rows,
        },
        "pitchers": {
            "n": len(pitcher_rows),
            "slot_rate_widening": _round(sum(row["slot_widening"]["same"] for row in pitcher_rows) / (11 * len(pitcher_rows)), 3),
            "slot_rate_printed": _round(sum(row["slot_printed"]["same"] for row in pitcher_rows) / (11 * len(pitcher_rows)), 3),
            "sim_gap_widening": sim_gap(pitcher_rows, "sim_widening", ("k", "bb", "hr", "h")),
            "sim_gap_printed": sim_gap(pitcher_rows, "sim_printed", ("k", "bb", "hr", "h")),
            "players": pitcher_rows,
        },
        "notes": [
            "Hitter plate appearances are AB+BB. The 1986 card does not print HBP, IBB, or SF.",
            "Pitcher batters faced is IP*3 + H + BB. The card does not print BF or HBP.",
            "Own card excluded from hitter comps. A pitcher is not in the hitter pool.",
            "Page 39 shift is not applied to TOUGH-OUT, and face 00 is not shifted.",
            "Page 11 range is applied only when simulating an official card that prints one.",
            "Tracker widening is unchanged. The printed column is a separate search.",
        ],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as handle:
        json.dump(report, handle, indent=1)
        handle.write("\n")
    print("wrote", OUT)
    print("hitter band MAE", report["hitters"]["bands"]["mae"], "bias", report["hitters"]["bands"]["bias_engine_minus_official"])
    print("hitter by outcome", report["hitters"]["bands"]["by_outcome"])
    print("out table", report["hitters"]["out_table_label_rate"])
    print("hitter sim gap", report["hitters"]["sim_gap_vs_official_card"])
    print("pitcher slots widening/printed", report["pitchers"]["slot_rate_widening"], report["pitchers"]["slot_rate_printed"])
    print("pitcher sim widening", report["pitchers"]["sim_gap_widening"])
    print("pitcher sim printed", report["pitchers"]["sim_gap_printed"])


if __name__ == "__main__":
    main()
