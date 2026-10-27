#!/usr/bin/env python3
"""Rebuild window-changed hitters whose extra-base bands drifted off the real line.

The 215-card rebuild scored AVG, OBP, and SLG and never scored doubles or
triples. Random restarts added up to 15 triple faces. The tuner has no 3B
cell, so those faces stayed, and lay_out dropped the doubles that would
have clipped them. This pass rebuilds only the hitters that show that
pattern, with the comp-shaped solver. Pitchers are left as they are.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import rebuild_window_cards as base  # noqa: E402

REPORT = os.path.join(ROOT, "historical-cards", "accuracy", "xbh_fix.json")
HANDS = ("vsLHP", "vsRHP")


def _width(table, key):
    band = (table or {}).get(key)
    if not band:
        return 0
    return int(band[1]) - int(band[0]) + 1


def _faces(sections, outcome):
    found = {}
    for section, hands in (sections or {}).items():
        for hand in HANDS:
            found[(section, hand)] = _width((hands or {}).get(hand), outcome)
    return found


def _real(peak):
    pa = float(peak["PA"])
    ab = float(peak["AB"])
    hits = float(peak["H"])
    doubles = float(peak.get("2B") or 0)
    triples = float(peak.get("3B") or 0)
    homers = float(peak.get("HR") or 0)
    walks = float(peak.get("BB") or 0)
    ibb = float(peak.get("IBB") or 0)
    hbp = float(peak.get("HBP") or 0)
    strikeouts = float(peak.get("SO") or 0)
    singles = hits - doubles - triples - homers
    return {
        "1bp": singles / pa,
        "2bp": doubles / pa,
        "3bp": triples / pa,
        "hrp": homers / pa,
        "bbp": (walks - ibb) / pa,
        "sop": strikeouts / pa,
        "hbpp": hbp / pa,
        "avg": hits / ab,
        "slg": (hits + doubles + 2 * triples + 3 * homers) / ab,
        "doubles": doubles,
        "triples": triples,
        "homers": homers,
        "pa": pa,
    }


def _penalty(exp, real):
    return (abs(exp["1bp"] - real["1bp"])
            + abs(exp["2bp"] - real["2bp"])
            + abs(exp["3bp"] - real["3bp"]))


def _reasons(real, exp, sections):
    triples = _faces(sections, "3B")
    doubles = _faces(sections, "2B")
    wheel_3b = max(triples[("WHEELHOUSE", hand)] for hand in HANDS)
    wheel_2b = sum(doubles[("WHEELHOUSE", hand)] for hand in HANDS)
    found = []
    if abs(exp["3bp"] - real["3bp"]) >= 0.005:
        found.append("3B rate")
    if abs(exp["2bp"] - real["2bp"]) >= 0.015:
        found.append("2B rate")
    if abs(exp["1bp"] - real["1bp"]) >= 0.015:
        found.append("1B rate")
    if wheel_3b >= 8:
        found.append("wide WHEEL 3B")
    if wheel_2b == 0 and real["2bp"] >= 0.04:
        found.append("no WHEEL 2B")
    return found


def _wheel(sections):
    wheel = (sections or {}).get("WHEELHOUSE") or {}
    out = {}
    for hand in HANDS:
        table = wheel.get(hand) or {}
        out[hand] = {
            key: table[key] for key in ("HR", "3B", "2B", "1B") if table.get(key)
        }
    return out


def _rates(exp):
    return {key: round(exp[key], 4) for key in ("1bp", "2bp", "3bp", "hrp", "avg", "obp", "slg")}


def _keep(old_exp, new_exp, real, old_sections, new_sections):
    old_pen = _penalty(old_exp, real)
    new_pen = _penalty(new_exp, real)
    if new_pen < old_pen - 0.001:
        return True
    if new_pen > old_pen + 0.003:
        return False
    old_3b = max(_width((old_sections.get("WHEELHOUSE") or {}).get(hand), "3B") for hand in HANDS)
    new_3b = max(_width((new_sections.get("WHEELHOUSE") or {}).get(hand), "3B") for hand in HANDS)
    old_2b = sum(_width((old_sections.get("WHEELHOUSE") or {}).get(hand), "2B") for hand in HANDS)
    new_2b = sum(_width((new_sections.get("WHEELHOUSE") or {}).get(hand), "2B") for hand in HANDS)
    if new_3b < old_3b:
        return True
    if old_2b == 0 and new_2b > 0 and real["2bp"] >= 0.04:
        return True
    return new_pen <= old_pen


def main():
    import hitter_solver as hs

    old = base._git_cards(base.WIPED)
    restored = base._git_cards(base.RESTORED)
    bat_keys, _pit_keys = base._window_keys(old, restored)
    cards = json.loads(open(base.CARDS).read())
    affected = []
    for key in bat_keys:
        card = cards[key]
        bat = card.get("card_bat") or {}
        peak = card.get("peak_bat") or {}
        if not bat.get("sections") or not peak.get("PA") or not peak.get("AB"):
            continue
        real = _real(peak)
        exp = hs.expected(bat["sections"], bat.get("bats") or "R")
        reasons = _reasons(real, exp, bat["sections"])
        if reasons:
            affected.append((key, reasons, real, exp))
    print("affected", len(affected), "of", len(bat_keys))

    kept_n = 0
    reverted = []
    failures = []
    rows = []
    for index, (key, reasons, real, old_exp) in enumerate(affected, start=1):
        card = cards[key]
        bat = card["card_bat"]
        old_sections = bat["sections"]
        positions = json.dumps(bat.get("positions"), sort_keys=True)
        rebuilt, reason = base._rebuild_hitter(card)
        if rebuilt is None:
            failures.append({"key": key, "name": card["name"], "reason": reason})
            rows.append({
                "key": key, "name": card["name"], "reasons": reasons,
                "status": "failed", "real": {k: round(real[k], 4) for k in ("1bp", "2bp", "3bp", "hrp", "avg", "slg")},
                "before": _rates(old_exp), "wheel_before": _wheel(old_sections),
            })
            continue
        if json.dumps(rebuilt.get("positions"), sort_keys=True) != positions:
            failures.append({"key": key, "name": card["name"], "reason": "fielding changed"})
            continue
        new_exp = hs.expected(rebuilt["sections"], rebuilt.get("bats") or bat.get("bats") or "R")
        status = "rebuilt"
        if _keep(old_exp, new_exp, real, old_sections, rebuilt["sections"]):
            card["card_bat"] = rebuilt
            kept_n += 1
        else:
            status = "reverted"
            reverted.append(key)
        rows.append({
            "key": key,
            "name": card["name"],
            "reasons": reasons,
            "status": status,
            "doubles": real["doubles"],
            "triples": real["triples"],
            "homers": real["homers"],
            "pa": real["pa"],
            "real": {k: round(real[k], 4) for k in ("1bp", "2bp", "3bp", "hrp", "avg", "slg")},
            "before": _rates(old_exp),
            "after": _rates(new_exp),
            "wheel_before": _wheel(old_sections),
            "wheel_after": _wheel(rebuilt["sections"]),
            "penalty_before": round(_penalty(old_exp, real), 4),
            "penalty_after": round(_penalty(new_exp, real), 4),
        })
        if index % 20 == 0:
            print("solved", index, "kept", kept_n)

    text = json.dumps(cards, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    with open(base.CARDS, "w") as handle:
        handle.write(text)

    # Rulebook sim of the cards that actually changed.
    changed = [row for row in rows if row["status"] == "rebuilt"]
    pitchers = []
    batters = []
    for key, card in cards.items():
        bat = card.get("card_bat") or {}
        if bat.get("sections"):
            batters.append(base.Batter(key, card))
        pit = card.get("card_pit") or {}
        if pit.get("table_2d6"):
            pitchers.append(base.Pitcher(key, card))
    sim_rows = []
    for index, row in enumerate(changed):
        card = cards[row["key"]]
        batter = next(item for item in batters if item.key == row["key"])
        sim = base._sim_hitter(batter, pitchers, base.SIM_N, 4000 + index)
        real_line = base._real_hitter(card["peak_bat"])
        sim_rows.append({
            "key": row["key"],
            "name": row["name"],
            "sim": {stat: round(sim[stat], 3) for stat in ("avg", "obp", "slg", "hr", "bb", "so")},
            "real": {stat: round(real_line[stat], 3) for stat in real_line},
        })
        if (index + 1) % 20 == 0:
            print("simmed", index + 1)

    def mae(stat):
        if not sim_rows:
            return None
        return round(sum(abs(row["sim"][stat] - row["real"][stat]) for row in sim_rows) / len(sim_rows), 4)

    report = {
        "affected": len(affected),
        "rebuilt": kept_n,
        "reverted": reverted,
        "failures": failures,
        "thresholds": {
            "3B_per_pa": 0.005,
            "2B_per_pa": 0.015,
            "1B_per_pa": 0.015,
            "wheel_3b_faces": 8,
            "missing_wheel_2b_when_2bp_at_least": 0.04,
        },
        "sim_mae": {stat: mae(stat) for stat in ("avg", "obp", "slg", "hr", "bb", "so")},
        "sim_n": base.SIM_N,
        "cards": rows,
        "notes": [
            "Card-implied rates use the solver's section probabilities, not a sampled opponent.",
            "A 5.06% defensive-out term adds a hitless at-bat. Matching 1B/2B/3B/HR per plate appearance therefore plays under the real AVG and SLG. The previous fit hid that by turning doubles into triples.",
            "Comp shapes are the eight 1986 cards with at least 300 AB+BB closest to the target rate. IN-PLAY is the fallback section when every comp printed none of an outcome.",
            "Pitchers were not rebuilt. TOUGH-OUT is not shifted. Face 00 is not shifted.",
        ],
    }
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    print("rebuilt", kept_n, "reverted", len(reverted), "failures", len(failures))
    print("sim mae", report["sim_mae"])


if __name__ == "__main__":
    main()
