#!/usr/bin/env python3
"""Set each hitter's Jump number from his real steal attempts, calibrated
to the printed 1986 cards.

Rulebook page 7: the auto steal goes when 2d6 <= Jump, so Jump is the
attempt frequency; players "without a Jump rating will not attempt".
The set-file Jump was capped at 5 and given to 298 of 480 hitters,
including slow, rarely-running D and F runners, so they went on 28% of
times on base. The 1986 set ties Jump to how often a player ran:
(SB+CS) / (1B+BB+HBP) in 1985 Lahman for 268 matched 1986 hitters gives
medians 1: .020, 2: .035, 3: .095, 4: .161, 5: .280, 6: .349, 7: .369,
8: .714, 9: .826. The cut points below were fit to those cards (exact on
49%, within one on 92%); 7-9 rest on six cards and are a judgment.

The rate uses the card's own window (peak_bat). Where CS was not kept
(pre-1951, or 0 CS with more than 5 SB) attempts are estimated as SB/0.7
and the card is flagged jump_basis "estimated". Steal letter, jump +/-,
and cards with no Jump (no number on the card) are not changed.
"""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CARDS = os.path.join(ROOT, "data", "cards.json")
CUTS = [0.011, 0.06, 0.145, 0.293, 0.38, 0.55, 0.77, 0.95]


def jump_from_window(peak):
    if not peak:
        return None, None, None
    opp = (peak.get("H") or 0) - (peak.get("2B") or 0) - (peak.get("3B") or 0) - (peak.get("HR") or 0) \
        + (peak.get("BB") or 0) + (peak.get("HBP") or 0)
    if opp < 50:
        return None, None, None
    sb, cs = peak.get("SB") or 0, peak.get("CS")
    known = cs is not None and not (cs == 0 and sb > 5)
    att = sb + (cs or 0) if known else sb / 0.7
    rate = att / opp
    return 1 + sum(rate > c for c in CUTS), round(rate, 4), "SB+CS" if known else "estimated (no CS kept): SB/0.7"


def apply(card):
    bat = card.get("card_bat") or {}
    steal = bat.get("steal")
    if not steal or not steal.get("jump"):
        return None
    new, rate, basis = jump_from_window(card.get("peak_bat"))
    if new is None:
        return None
    old = steal["jump"]
    steal["jump"] = new
    steal["jump_basis"] = {"attempt_rate": rate, "attempts": basis, "set_file_jump": steal.get("jump_basis", {}).get("set_file_jump", old),
                           "calibration": "1986 printed cards vs 1985 SB+CS per time on first (scripts/fix_jump_from_attempts.py)"}
    return old, new, rate, basis


def main():
    cards = json.load(open(CARDS, encoding="utf-8"))
    rows = []
    for key, card in cards.items():
        got = apply(card)
        if got:
            rows.append((key, card["name"]) + got)
    with open(CARDS, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(cards, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    for r in rows:
        if r[2] != r[3] or "estimated" in r[5]:
            print(*r)
    print("cards:", len(rows), "changed:", sum(1 for r in rows if r[2] != r[3]))


if __name__ == "__main__":
    main()
