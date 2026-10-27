#!/usr/bin/env python3
"""Rebuild dice for the 215 cards whose peak window changed.

The 215 are the cards whose peak_bat or peak_pit window_years differ
between 526fb9c (windows wiped) and 8188680 (windows restored). Cards
whose only change was a dice repair are left alone. Fielding, stamina,
played games, and peak stat lines stay as they are.

Pitcher charts are fit with the page-39 percentile shift. The tracker's
band-widening evaluation is not used.
"""
from __future__ import annotations

import json
import os
import random
import statistics
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "engines", "hitter-v0.5"))
sys.path.insert(0, os.path.join(ROOT, "engines", "pitcher-v0.2.3"))
sys.path.insert(0, os.path.join(ROOT, "engines", "sim"))

import hitter_solver as hs  # noqa: E402
from calibration import full_pipeline  # noqa: E402
from historical_solver import solve_historical  # noqa: E402
from partition import validate_hitter_card, validate_pitcher_table  # noqa: E402
from pa_sim import Batter, Pitcher, Tally, parks_1986, resolve_pa  # noqa: E402

CARDS = os.path.join(ROOT, "data", "cards.json")
REPORT = os.path.join(ROOT, "historical-cards", "accuracy", "rebuild_215.json")
WIPED = "526fb9c"
RESTORED = "8188680"
SIM_N = 2500
SHOW = ("COL|heltoto01", "BOS|willite01", "COL|tulowtr01")


def _git_cards(rev):
    raw = subprocess.check_output(["git", "show", "%s:data/cards.json" % rev])
    return json.loads(raw)


def _years(card, side):
    block = card.get(side) or {}
    return tuple(block.get("window_years") or [])


def _window_keys(old, new):
    bat_keys = []
    pit_keys = []
    for key, card in new.items():
        if key not in old:
            continue
        if _years(old[key], "peak_bat") != _years(card, "peak_bat"):
            bat_keys.append(key)
        if _years(old[key], "peak_pit") != _years(card, "peak_pit"):
            pit_keys.append(key)
    return bat_keys, pit_keys


def _pos(bat):
    for chip in bat.get("positions") or []:
        if chip.get("pos"):
            return chip["pos"]
    return "UT"


def _hitter_row(card):
    peak = card["peak_bat"]
    bat = card["card_bat"]
    return {
        "Name": card["name"],
        "Team": peak.get("team_line") or "",
        "Bats": (bat.get("bats") or "R"),
        "Throws": (bat.get("throws") or "R"),
        "Position": _pos(bat),
        "Fielding": "average",
        "Arm": "average",
        "PA": peak["PA"],
        "AB": peak["AB"],
        "H": peak["H"],
        "2B": peak["2B"],
        "3B": peak["3B"],
        "HR": peak["HR"],
        "BB": peak["BB"],
        "IBB": peak.get("IBB") or 0,
        "SO": peak["SO"],
        "HBP": peak.get("HBP") or 0,
        "SB": peak.get("SB") or 0,
        "CS": peak.get("CS") or 0,
    }


def _bands(sections):
    out = {}
    for section, hands in (sections or {}).items():
        out[section] = {}
        for hand, table in hands.items():
            out[section][hand] = {
                key: value for key, value in (table or {}).items() if value
            }
    return out


def _seed(key):
    return sum(ord(ch) for ch in key) % 100000


def _rebuild_hitter(card):
    row = _hitter_row(card)
    if not row["PA"] or not row["AB"]:
        return None, "no plate appearances on the card"
    built = hs.build_one(row, run=(card.get("card_bat") or {}).get("run"))
    if built is None:
        return None, "solver skipped the row"
    new_card = built[0]
    bat = card["card_bat"]
    kept = {key: bat[key] for key in bat if key not in ("sections", "out_table")}
    kept["sections"] = new_card["sections"]
    kept["out_table"] = new_card["out_table"]
    problems = validate_hitter_card(kept, exact=False)
    if problems:
        return None, "; ".join(problems[:4])
    return kept, None


def _rebuild_pitcher(card, key):
    peak = card["peak_pit"]
    pit = card["card_pit"]
    bf = float(peak.get("bf") or 0)
    if bf <= 0:
        return None, "no batters faced on the card"
    years = list(peak.get("window_years") or [])
    year = int(round(statistics.median(years))) if years else 1986
    raw = {
        "h_bf": float(peak.get("h") or 0) / bf,
        "bb_bf": float(peak.get("bb") or 0) / bf,
        "so_bf": float(peak.get("so") or 0) / bf,
        "hr_bf": float(peak.get("hr") or 0) / bf,
        "hbp_bf": float(peak.get("hbp") or 0) / bf,
    }
    target = full_pipeline(raw, year)["solver_target"]
    hand = pit.get("throws") or "R"
    result = solve_historical(
        target, hand, restarts=8, seed=_seed(key), so_rule="printed")
    kept = {field: pit[field] for field in pit if field not in ("table_2d6", "so_modifier")}
    kept["table_2d6"] = {str(slot): result["table"][str(slot)] for slot in range(2, 13)}
    kept["so_modifier"] = result["so_modifier"]
    problems = validate_pitcher_table(kept["table_2d6"])
    if problems:
        return None, "; ".join(problems)
    return kept, {
        "so_modifier": result["so_modifier"],
        "fit_error": round(result["fit_error"], 4),
        "status": result["status"],
        "specials": result.get("special_required") or [],
        "year": year,
    }


def _real_hitter(peak):
    ab = float(peak["AB"])
    h = float(peak["H"])
    bb = float(peak.get("BB") or 0)
    hbp = float(peak.get("HBP") or 0)
    hr = float(peak.get("HR") or 0)
    doubles = float(peak.get("2B") or 0)
    triples = float(peak.get("3B") or 0)
    so = float(peak.get("SO") or 0)
    pa = float(peak["PA"])
    return {
        "avg": h / ab,
        "obp": (h + bb + hbp) / pa,
        "slg": (h + doubles + 2 * triples + 3 * hr) / ab,
        "hr": hr / pa,
        "bb": bb / pa,
        "so": so / pa,
    }


def _real_pitcher(peak):
    bf = float(peak["bf"])
    return {
        "k": float(peak.get("so") or 0) / bf,
        "bb": float(peak.get("bb") or 0) / bf,
        "hr": float(peak.get("hr") or 0) / bf,
        "h": float(peak.get("h") or 0) / bf,
    }


def _sim_hitter(batter, pitchers, n, seed):
    rng = random.Random(seed)
    tally = Tally()
    parks = parks_1986()
    guard = 0
    while tally.pa < n and guard < n * 4:
        guard += 1
        pitcher = pitchers[rng.randrange(len(pitchers))]
        tally.add(resolve_pa(rng, batter, pitcher, parks=parks))
    return tally.rates()


def _sim_pitcher(pitcher, batters, n, seed):
    rng = random.Random(seed)
    tally = Tally()
    parks = parks_1986()
    guard = 0
    while tally.pa < n and guard < n * 4:
        guard += 1
        batter = batters[rng.randrange(len(batters))]
        tally.add(resolve_pa(rng, batter, pitcher, parks=parks))
    rates = tally.rates()
    ab_share = (tally.ab / tally.pa) if tally.pa else 1
    return {"k": rates["so"], "bb": rates["bb"], "hr": rates["hr"], "h": rates["avg"] * ab_share}


def main():
    old = _git_cards(WIPED)
    restored = _git_cards(RESTORED)
    bat_keys, pit_keys = _window_keys(old, restored)
    print("window hitters", len(bat_keys), "window pitchers", len(pit_keys),
          "unique", len(set(bat_keys) | set(pit_keys)))
    cards = json.loads(open(CARDS).read())
    missing = [key for key in set(bat_keys) | set(pit_keys) if key not in cards]
    if missing:
        raise SystemExit("missing keys on current cards: %s" % missing[:8])

    before = {}
    for key in SHOW:
        card = cards[key]
        before[key] = {
            "name": card["name"],
            "sections": _bands((card.get("card_bat") or {}).get("sections")),
            "table": (card.get("card_pit") or {}).get("table_2d6"),
            "so_modifier": (card.get("card_pit") or {}).get("so_modifier"),
            "bat_years": list(_years(card, "peak_bat")),
            "pit_years": list(_years(card, "peak_pit")),
        }

    failures = []
    rebuilt_bat = []
    rebuilt_pit = []
    modifier_changes = []
    for key in bat_keys:
        card = cards[key]
        if not (card.get("card_bat") or {}).get("sections"):
            failures.append({"key": key, "side": "bat", "reason": "no hitter sections to replace"})
            continue
        kept_positions = json.dumps((card["card_bat"].get("positions")), sort_keys=True)
        kept, reason = _rebuild_hitter(card)
        if kept is None:
            failures.append({"key": key, "side": "bat", "reason": reason})
            continue
        if json.dumps(kept.get("positions"), sort_keys=True) != kept_positions:
            failures.append({"key": key, "side": "bat", "reason": "fielding changed"})
            continue
        card["card_bat"] = kept
        rebuilt_bat.append(key)
    for key in pit_keys:
        card = cards[key]
        pit = card.get("card_pit") or {}
        if not pit.get("table_2d6"):
            failures.append({"key": key, "side": "pit", "reason": "no pitcher table to replace"})
            continue
        previous = pit.get("so_modifier")
        kept, info = _rebuild_pitcher(card, key)
        if kept is None:
            failures.append({"key": key, "side": "pit", "reason": info})
            continue
        card["card_pit"] = kept
        rebuilt_pit.append(key)
        if info["so_modifier"] != previous:
            modifier_changes.append({
                "key": key, "was": previous, "now": info["so_modifier"],
                "fit_error": info["fit_error"],
            })

    text = json.dumps(cards, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    with open(CARDS, "w") as handle:
        handle.write(text)
    print("rebuilt hitters", len(rebuilt_bat), "pitchers", len(rebuilt_pit), "failures", len(failures))

    # Rulebook sim against the other converted cards.
    pitchers = []
    batters = []
    for key, card in cards.items():
        bat = card.get("card_bat") or {}
        if bat.get("sections"):
            batters.append(Batter(key, card))
        pit = card.get("card_pit") or {}
        if pit.get("table_2d6"):
            pitchers.append(Pitcher(key, card))
    hitter_gaps = []
    pitcher_gaps = []
    for index, key in enumerate(rebuilt_bat):
        card = cards[key]
        batter = next(item for item in batters if item.key == key)
        sim = _sim_hitter(batter, pitchers, SIM_N, 3000 + index)
        real = _real_hitter(card["peak_bat"])
        hitter_gaps.append({
            "key": key,
            "name": card["name"],
            "sim": {stat: round(sim[stat], 3) for stat in ("avg", "obp", "slg", "hr", "bb", "so")},
            "real": {stat: round(real[stat], 3) for stat in real},
        })
    for index, key in enumerate(rebuilt_pit):
        card = cards[key]
        pitcher = next(item for item in pitchers if item.key == key)
        sim = _sim_pitcher(pitcher, batters, SIM_N, 9000 + index)
        real = _real_pitcher(card["peak_pit"])
        pitcher_gaps.append({
            "key": key,
            "name": card["name"],
            "modifier": card["card_pit"]["so_modifier"],
            "sim": {stat: round(sim[stat], 3) for stat in ("k", "bb", "hr", "h")},
            "real": {stat: round(real[stat], 3) for stat in real},
        })

    def mae(rows, stat):
        return round(sum(abs(row["sim"][stat] - row["real"][stat]) for row in rows) / len(rows), 4)

    after = {}
    for key in SHOW:
        card = cards[key]
        after[key] = {
            "name": card["name"],
            "sections": _bands((card.get("card_bat") or {}).get("sections")),
            "table": (card.get("card_pit") or {}).get("table_2d6"),
            "so_modifier": (card.get("card_pit") or {}).get("so_modifier"),
        }
    report = {
        "window_hitters": len(bat_keys),
        "window_pitchers": len(pit_keys),
        "unique": len(set(bat_keys) | set(pit_keys)),
        "rebuilt_hitters": len(rebuilt_bat),
        "rebuilt_pitchers": len(rebuilt_pit),
        "failures": failures,
        "modifier_changes": modifier_changes,
        "hitter_sim_mae": {stat: mae(hitter_gaps, stat) for stat in ("avg", "obp", "slg", "hr", "bb", "so")},
        "pitcher_sim_mae": {stat: mae(pitcher_gaps, stat) for stat in ("k", "bb", "hr", "h")},
        "showcase": {key: {"before": before[key], "after": after[key]} for key in SHOW},
        "hitter_outliers": sorted(hitter_gaps, key=lambda row: -abs(row["sim"]["avg"] - row["real"]["avg"]))[:8],
        "pitcher_outliers": sorted(pitcher_gaps, key=lambda row: -abs(row["sim"]["k"] - row["real"]["k"]))[:8],
        "notes": [
            "Fielding, stamina, and peak lines were not rewritten.",
            "Pitcher search used the page-39 shift. TOUGH-OUT was not shifted. Face 00 was not shifted.",
            "The sim draws the other converted cards and the 26 official 1986 parks. League-average defense is an assumption (range C, error 3). Reached-on-error is an at-bat and not a hit.",
        ],
    }
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    print("hitter mae", report["hitter_sim_mae"])
    print("pitcher mae", report["pitcher_sim_mae"])
    print("failures", len(failures))
    print("modifier changes", len(modifier_changes))


if __name__ == "__main__":
    main()
