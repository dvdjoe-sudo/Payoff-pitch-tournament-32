#!/usr/bin/env python3
"""Restore the printed 1986 platoon split on hitter cards.

Why: hitter_solver.select_comps picked section comps by stats only, not
by the batter's side. A left-handed batter's comps were mostly
right-handed 1986 cards, which print almost no split, so our left-handed
batters hit left-handed pitchers nearly as well as right-handers
(1986 printed L batters: WHEELHOUSE HR 10.6 faces vs LHP, 33.2 vs RHP).
Pitcher cards are solved against the printed 1986 hitters, so left-handed
pitchers were charged for a platoon edge the tournament hitters did not
give them.

What: for every section and outcome, the face total weighted by how often
a batter sees each hand (0.28 vsLHP, 0.72 vsRHP, the weights the hitter
solver itself uses) is kept, so the card's overall expected line stays
put. The vsLHP:vsRHP ratio is set to the ratio on qualified printed 1986
cards (300+ PA) of the same batting side. If a hand would pass face 99,
it is clipped and the clipped faces move to the other hand at the same
weighted value. The previous sections are kept in
card_bat.platoon_basis.previous_sections.
"""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "engines", "hitter-v0.5"))
import hitter_solver as hs

WL, WR = 0.28, 0.72
SIDE = {"L": "L", "R": "R", "S": "S", "B": "S"}


def ratios():
    ref = hs.reference()["cards"]
    tot = {}
    for c in ref:
        if c.get("pitcher") or not c.get("sections") or hs.plate_appearances(c) < hs.MIN_COMP_PA:
            continue
        side = SIDE.get((c.get("bats") or "R")[0])
        w = hs.widths_from_sections(c["sections"])
        for (sec, hand, k), v in w.items():
            t = tot.setdefault((side, sec, k), [0, 0])
            t[0 if hand == "vsLHP" else 1] += v
    return {key: (l / r if r else None) for key, (l, r) in tot.items()}


def resplit(sections, side, R):
    w = hs.widths_from_sections(sections)
    new = dict(w)
    for sec, keys in hs.CANON.items():
        for k in keys:
            l, r = w[(sec, "vsLHP", k)], w[(sec, "vsRHP", k)]
            mass = WL * l + WR * r
            q = R.get((side, sec, k))
            if q is None or mass == 0:
                continue
            rr = mass / (WL * q + WR)
            new[(sec, "vsLHP", k)] = q * rr
            new[(sec, "vsRHP", k)] = rr
        # capacity: each hand holds 99 faces
        for hand, other, wh, wo in (("vsLHP", "vsRHP", WL, WR), ("vsRHP", "vsLHP", WR, WL)):
            tot = sum(new[(sec, hand, k)] for k in keys)
            if tot > 99:
                f = 99 / tot
                for k in keys:
                    cut = new[(sec, hand, k)] * (1 - f)
                    new[(sec, hand, k)] -= cut
                    new[(sec, other, k)] += cut * wh / wo
    out = {key: int(round(v)) for key, v in new.items()}
    for sec, keys in hs.CANON.items():
        for hand in ("vsLHP", "vsRHP"):
            while sum(out[(sec, hand, k)] for k in keys) > 99:
                k = max(keys, key=lambda k: out[(sec, hand, k)])
                out[(sec, hand, k)] -= 1
    return hs.lay_out(out)


def apply(card, R):
    bat = card.get("card_bat") or {}
    if not bat.get("sections"):
        return False
    side = SIDE.get((bat.get("bats") or "R")[0], "R")
    basis = bat.get("platoon_basis") or {}
    prev = basis.get("previous_sections") or bat["sections"]
    prev_out = basis.get("previous_out_table", bat.get("out_table")) or []
    bat["sections"] = resplit(prev, side, R)
    # Holes move when bands move, so the shared out table is rebuilt as the
    # union of both hands' holes; labels come from the old table (P4 where
    # it had none, the solver's fallback).
    _per, bat["out_table"] = hs.out_tables_from_holes(bat["sections"], prev_out)
    bat["platoon_basis"] = {"side": side, "method": "1986 same-side ratio, 0.28/0.72 weighted total kept",
                            "previous_sections": prev, "previous_out_table": prev_out}
    return True


def main():
    path = os.path.join(ROOT, "data", "cards.json")
    cards = json.load(open(path))
    R = ratios()
    n = sum(apply(card, R) for card in cards.values())
    with open(path, "w") as h:
        h.write(json.dumps(cards, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    print("resplit", n, "hitter cards")
    print({"%s %s %s" % k: round(v, 2) for k, v in sorted(R.items()) if v is not None and k[2] in ("HR", "SO", "BB", "1B")})


if __name__ == "__main__":
    main()
