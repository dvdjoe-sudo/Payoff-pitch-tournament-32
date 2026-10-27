#!/usr/bin/env python3
"""One post-pass every card builder runs before it writes data/cards.json,
so a rebuild by any script gives the same cards:

- hitter platoon split restored to the 1986 same-side ratio (platoon_resplit)
- Jump and Steal letter from real steals, 1986 calibration (fix_jump_from_attempts, fix_steal_letter)
- pitcher 2d6 table, solver v0.3, plus the page 11 band (resolve_pitcher_tables)
- outfield arm on Derived cards from assists (derive_of_arm)

finalize(cards, keys) changes only the listed keys (all when keys is None).
Each step reads its own basis note, so running it twice gives the same card.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import derive_of_arm  # noqa: E402
import fix_jump_from_attempts as jump_fix  # noqa: E402
import fix_steal_letter as steal_fix  # noqa: E402
import platoon_resplit  # noqa: E402
import resolve_pitcher_tables as pitcher_resolve  # noqa: E402

_RATIOS = None


def finalize(cards, keys=None):
    global _RATIOS
    _RATIOS = _RATIOS or platoon_resplit.ratios()
    want = set(cards) if keys is None else set(keys)
    for key in want:
        card = cards.get(key)
        if not card:
            continue
        platoon_resplit.apply(card, _RATIOS)
        jump_fix.apply(card)
        steal_fix.apply(card)
        pitcher_resolve.apply(card, key)
    derive_of_arm.apply_all(cards, want)
    return cards
