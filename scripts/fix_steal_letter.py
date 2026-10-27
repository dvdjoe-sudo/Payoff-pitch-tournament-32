#!/usr/bin/env python3
"""Set each hitter's Steal letter (A-F, rulebook page 7) from real base
stealing, calibrated to the printed 1986 cards.

Why: the set-file letters run about one grade harsh against the 1986 set.
Real window SB% by set-file letter is B .87, C .79, D .71, F .56; on the
1986 cards (1985 Lahman, 305 matched hitters) it is A .79, B .74, C .69,
D .65, F .59, and the set files have no A at all (1986: 11% A).

Score = shrunk SB% ((SB + 20*.65) / (SB+CS+20)) + 4 * attempt rate
((SB+CS) / (1B+BB+HBP)). Cut points are the 1986 letter shares on that
score (305 cards: exact 32%, within one grade 68%). The 1986 letter is
only loosely tied to one season's SB% and rate, so single letters are
uncertain; the grade distribution is what the calibration fixes.
Cards whose window kept no caught stealing keep their letter (flagged).

Recalibrated 2026-10-27 on the real 1986 season (the 1986 set prints 1986
stats, not 1985): cut points come from historical-cards/reference/
steal_calibration_1986.json, written by scripts/calibrate_steal_1986.py.
"""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CARDS = os.path.join(ROOT, "data", "cards.json")
CUTS = json.load(open(os.path.join(ROOT, "historical-cards", "reference", "steal_calibration_1986.json")))["letter"]["cuts_FDCBA"]
LETTERS = "FDCBA"


def letter_from_window(peak):
    if not peak:
        return None, None
    opp = (peak.get("H") or 0) - (peak.get("2B") or 0) - (peak.get("3B") or 0) - (peak.get("HR") or 0) \
        + (peak.get("BB") or 0) + (peak.get("HBP") or 0)
    sb, cs = peak.get("SB") or 0, peak.get("CS")
    if opp < 50 or cs is None or (cs == 0 and sb > 5):
        return None, None
    score = (sb + 20 * 0.65) / (sb + cs + 20) + 4 * (sb + cs) / opp
    return LETTERS[sum(score > c for c in CUTS)], round(score, 4)


def apply(card):
    bat = card.get("card_bat") or {}
    steal = bat.get("steal")
    if not steal or not steal.get("rating"):
        return None
    peak = card.get("peak_bat")
    new, score = letter_from_window(peak)
    basis = steal.setdefault("letter_basis", {})
    basis.setdefault("set_file_letter", steal["rating"])
    if new is None:
        basis["note"] = "kept set-file letter: no caught-stealing data in the window"
        return steal["rating"], steal["rating"], None
    old = steal["rating"]
    steal["rating"] = new
    basis.update({"score": score, "calibration": "1986 printed letters vs 1986 SB%/attempt rate (scripts/calibrate_steal_1986.py) (scripts/fix_steal_letter.py)"})
    return old, new, score


def main():
    cards = json.load(open(CARDS, encoding="utf-8"))
    rows = []
    for key, card in cards.items():
        got = apply(card)
        if got:
            rows.append((key, card["name"]) + got)
    with open(CARDS, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(cards, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    print("cards:", len(rows), "changed:", sum(1 for r in rows if r[2] != r[3]),
          "kept (no CS):", sum(1 for r in rows if r[4] is None))


if __name__ == "__main__":
    main()
