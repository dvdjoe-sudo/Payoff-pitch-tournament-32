#!/usr/bin/env python3
"""Re-solve every pitcher card's 2d6 table with solver v0.3.

engines/pitcher-v0.3/solver.py (see its docstring): realistic DEFENSE
measured in game.py, full H/HR/BB/SO/HBP target from the card's own
window (peak_pit, relative to the league in the same seasons), result
shares held to the printed 1986 distribution. Only card_pit.table_2d6
changes (plus a table_basis note; special cleared since TOUGH-OUT /
PATIENT-OUT are no longer used). so_modifier, stamina, WP, hold, DP,
pickoff, injury and fielding are untouched. build_cards.py calls
apply() so a rebuild gives the same tables; the search is seeded by
the card key, so it is deterministic.
"""
import json
import os
import sys
import zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "engines", "pitcher-v0.3"))
import solver  # noqa: E402

CARDS = os.path.join(ROOT, "data", "cards.json")
_CAL = None


def apply(entry, key=None):
    global _CAL
    cp, peak = entry.get("card_pit"), entry.get("peak_pit")
    if not cp or not peak or not peak.get("bf") or not peak.get("window_years"):
        return None
    _CAL = _CAL or solver.load_calibration()
    hand = "L" if cp.get("throws") == "L" else "R"
    bump = solver.bump_of(cp.get("so_modifier"))
    years = [int(y) for y in peak["window_years"]]
    totals = {k: peak.get(k) or 0 for k in solver.STATS}
    totals["bf"] = peak["bf"]
    rel = solver.relative(totals, years)
    seed = zlib.crc32((key or entry.get("id", "")).encode())
    res = solver.solve(solver.target_from(rel, _CAL), hand, bump, _CAL, seed=seed)
    old = cp.get("table_2d6")
    prev = (cp.get("table_basis") or {}).get("previous_table", old)
    cp["table_2d6"] = res["table"]
    last = max(solver.league())
    basis = {
        "solver": "engines/pitcher-v0.3 (DEFENSE from game.py, H/HR/BB/SO/HBP target, 1986 shares)",
        "relative_to_league": {k: round(v, 3) for k, v in rel.items()},
        "target": res["target"], "card_rates": res["card_rates"],
        "previous_table": prev, "previous_special": (cp.get("table_basis") or {}).get("previous_special", cp.get("special")),
    }
    flags = []
    if any(y > last for y in years):
        flags.append("league rate for %s uses %d (no Lahman season yet)" % ([y for y in years if y > last], last))
    if peak["bf"] < 300:
        flags.append("thin window: %d BF" % peak["bf"])
    if flags:
        basis["flag"] = "; ".join(flags)
    cp["table_basis"] = basis
    cp["special"] = []
    return prev, res["table"]


def main():
    cards = json.load(open(CARDS, encoding="utf-8"))
    n = ch = 0
    for key, entry in cards.items():
        got = apply(entry, key)
        if got:
            n += 1
            ch += got[0] != got[1]
    with open(CARDS, "w", encoding="utf-8") as h:
        h.write(json.dumps(cards, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    print("pitcher cards re-solved:", n, "tables changed:", ch)


if __name__ == "__main__":
    main()
