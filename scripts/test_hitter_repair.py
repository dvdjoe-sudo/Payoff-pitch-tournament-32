#!/usr/bin/env python3
"""capacity_retune: IBB divisor and full-section hit recovery."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capacity_retune as cr  # noqa: E402
hs = cr.hs
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def main():
    # IBB count as walks over full PA (owner ruling 2026-10-27).
    pb = {"PA": 1000, "IBB": 100, "AB": 800, "H": 270, "BB": 180, "HBP": 10, "HR": 60,
          "2B": 40, "3B": 5, "SO": 120}
    t = cr.target(pb)
    assert abs(t["hrp"] - 60 / 1000) < 1e-12 and abs(t["bbp"] - 180 / 1000) < 1e-12
    # Walk cap: scaling the rest keeps every hand inside 99 faces, PATIENT BB untouched.
    sec = {s: {h: {} for h in ("vsLHP", "vsRHP")} for s in hs.CANON}
    for h in ("vsLHP", "vsRHP"):
        sec["PATIENT"][h] = {"BB": [1, 90], "1B": [91, 99]}
        sec["WHEELHOUSE"][h] = {"HR": [1, 99]}
        sec["IN-PLAY"][h] = {"1B": [1, 20]}
        sec["TOUGH"][h] = {"SO": [1, 30]}
    out = cr.cap_rescale(sec, 1.2)
    for s, t2 in out.items():
        for h, tbl in t2.items():
            assert sum(hs.width(tbl, k) for k in tbl) <= 99, (s, h)
    assert hs.width(out["IN-PLAY"]["vsLHP"], "1B") == 24
    assert hs.width(out["PATIENT"]["vsLHP"], "BB") == 90
    # The shipped cards: the pass is recorded and idempotent, and Ruth's
    # card is back near his window AVG.
    cards = json.load(open(os.path.join(ROOT, "data", "cards.json")))
    ruth = cards["NYY|ruthba01"]
    cb = ruth["card_bat"]["capacity_basis"]
    bonds = cards["SF|bondsba01"]["card_bat"]["capacity_basis"]
    assert bonds["walk_cap_hit"] and bonds["walk_expected_bbp"] > 0.21
    assert bonds["expected_after"]["obp"] > 0.47 and bonds["expected_after"]["avg"] > 0.32
    # A low-IBB hitter with room reaches his walk target exactly.
    for k, c in cards.items():
        b = (c.get("card_bat") or {}).get("capacity_basis")
        if b and not b["walk_cap_hit"]:
            assert b["walk_expected_bbp"] >= b["walk_target_bbp"] - 1e-6, k
    assert cb["retuned"] and cb["expected_after"]["avg"] - cb["expected_before"]["avg"] > 0.05
    again = json.loads(json.dumps(ruth))
    cr.apply(again)
    assert again["card_bat"]["sections"] == ruth["card_bat"]["sections"]
    for key in ("IN-PLAY", "TOUGH"):
        for k, mx in (("1B", cr.PRINTED_MAX[(key, "1B")]), ("2B", cr.PRINTED_MAX[(key, "2B")])):
            for h in ("vsLHP", "vsRHP"):
                assert hs.width(ruth["card_bat"]["sections"][key][h], k) <= mx
    print("hitter repair tests passed")


if __name__ == "__main__":
    main()
