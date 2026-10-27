#!/usr/bin/env python3
"""Hitter card repair: intentional walks, then hits a full section pushed off.

1. Intentional walks. The solver drops IBB from the walk target (the
   engine has no intentional walk, and the rulebook does not mention one),
   but it divided every event by PA that still counted those IBB. The
   card's plate appearances have no IBB, so each lost IBB became an out:
   Barry Bonds (IBB 10.5% of PA) came out .305 against .346. Every result
   band is scaled by PA / (PA - IBB), so per-PA rates on the card are the
   real rates without IBB. A section that would pass 99 trims singles,
   then doubles, then triples (step 2 puts hits back where there is room).
   hitter_solver.build_one now builds targets the same way.

The hitter solver keeps 1B/2B/3B on the comp cards' section mix
(project_shaped). When PATIENT or WHEELHOUSE is already full (99 faces of
walks or homers), the share of hits sent there is clipped at face 99 and
lost, and the projection will not let the tuner move them to IN-PLAY or
TOUGH, which still have room. Babe Ruth's card came out .294 against a
.375 target this way, with 69 empty IN-PLAY faces.

This pass re-tunes only the IN-PLAY and TOUGH hit bands, both hands
together, against the card's own window line (unintentional walks, as the
solver does), never above the widest band printed on a 1986 card
(IN-PLAY 1B 52, 2B 19, 3B 5; TOUGH 1B 17, 2B 6, 3B 3). WHEELHOUSE,
PATIENT, SO, BB and HBP bands are untouched. It runs only on a card with
a full section whose expected AVG is .005 or more under target, and keeps the result only
when AVG rises and SLG does not fall. The
previous sections are kept in card_bat.capacity_basis.
"""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "engines", "hitter-v0.5"))
import hitter_solver as hs  # noqa: E402

CELLS = [("IN-PLAY", "1B"), ("IN-PLAY", "2B"), ("IN-PLAY", "3B"),
         ("TOUGH", "1B"), ("TOUGH", "2B"), ("TOUGH", "3B")]
PRINTED_MAX = {("IN-PLAY", "1B"): 52, ("IN-PLAY", "2B"): 19, ("IN-PLAY", "3B"): 5,
               ("TOUGH", "1B"): 17, ("TOUGH", "2B"): 6, ("TOUGH", "3B"): 3}
MIN_SHORT = 0.005


def target(pb):
    g = lambda k: float(pb.get(k) or 0)
    pa, ab = g("PA") - g("IBB"), g("AB")
    if pa <= 0 or ab <= 0:
        return None
    h, ubb, hbp, hr = g("H"), g("BB") - g("IBB"), g("HBP"), g("HR")
    d, t = g("2B"), g("3B")
    return {"avg": h / ab, "obp": (h + ubb + hbp) / pa, "slg": (h + d + 2 * t + 3 * hr) / ab,
            "bbp": ubb / pa, "sop": g("SO") / pa, "hrp": hr / pa, "hbpp": hbp / pa,
            "1bp": (h - d - t - hr) / pa, "2bp": d / pa, "3bp": t / pa}


def _bats(bat):
    b = (bat.get("bats") or "R")[0]
    return b if b in "LRS" else ("S" if b == "B" else "R")


def ibb_factor(pb):
    pa, ibb = float(pb.get("PA") or 0), float(pb.get("IBB") or 0)
    return pa / (pa - ibb) if pa > ibb > 0 else 1.0


def ibb_rescale(sections, f):
    W = hs.widths_from_sections(sections)
    for sec, keys in hs.CANON.items():
        for hand in ("vsLHP", "vsRHP"):
            for k in keys:
                W[(sec, hand, k)] = int(round(W[(sec, hand, k)] * f))
            over = sum(W[(sec, hand, k)] for k in keys) - 99
            for k in ("1B", "2B", "3B", "HBP", "BB", "SO", "HR"):
                if over <= 0:
                    break
                if k in keys:
                    cut = min(over, W[(sec, hand, k)])
                    W[(sec, hand, k)] -= cut
                    over -= cut
    return hs.lay_out(W)


def saturated(sections):
    return any(sum(hs.width(t[h], k) for k in t[h]) >= 99
               for t in sections.values() for h in t)


def retune(sections, tgt, bats, run):
    W = hs.widths_from_sections(sections)
    score = lambda w: hs.err(hs.expected(hs.lay_out(w), bats, run), tgt)
    best = score(W)
    step = 8
    while step >= 1:
        improved = True
        while improved:
            improved = False
            for sec, k in CELLS:
                for delta in (step, -step):
                    W2 = dict(W)
                    ok = True
                    for hand in ("vsLHP", "vsRHP"):
                        v = W2[(sec, hand, k)] + delta
                        room = 99 - sum(W2[(sec, hand, x)] for x in hs.CANON[sec])
                        if v < 0 or v > PRINTED_MAX[(sec, k)] or (delta > 0 and delta > room):
                            ok = False
                        W2[(sec, hand, k)] = v
                    if not ok:
                        continue
                    e = score(W2)
                    if e < best - 1e-10:
                        best, W, improved = e, W2, True
                        break
        step //= 2
    return hs.lay_out(W), best


def apply(card, fresh=False):
    """fresh=True: the caller just rebuilt the sections (card_postpass runs
    platoon_resplit first), so start from them, not from the stored basis."""
    bat = card.get("card_bat") or {}
    old = bat.get("capacity_basis")
    if old and not fresh:  # start again from the card the pass first saw
        bat["sections"], bat["out_table"] = old["previous_sections"], old["previous_out_table"]
    pb = card.get("peak_bat") or {}
    tgt = target(pb)
    if not bat.get("sections") or not tgt:
        bat.pop("capacity_basis", None)
        return False
    bats, run = _bats(bat), bat.get("run")
    prev, prev_out = bat["sections"], bat.get("out_table") or []
    before = hs.expected(prev, bats, run)
    f = ibb_factor(pb)
    new = ibb_rescale(prev, f) if f > 1 else prev
    retuned = False
    mid = hs.expected(new, bats, run)
    if saturated(new) and mid["avg"] <= tgt["avg"] - MIN_SHORT:
        cand, _e = retune(new, tgt, bats, run)
        after = hs.expected(cand, bats, run)
        # keep only a real gain in AVG without losing SLG
        if after["avg"] >= mid["avg"] + 0.001 and after["slg"] >= mid["slg"]:
            new, retuned = cand, True
    if new == prev:
        bat.pop("capacity_basis", None)
        return False
    after = hs.expected(new, bats, run)
    bat["sections"] = new
    _per, bat["out_table"] = hs.out_tables_from_holes(new, prev_out)
    r3 = lambda e: {k: round(e[k], 3) for k in ("avg", "obp", "slg")}
    bat["capacity_basis"] = {
        "method": "bands scaled by PA/(PA-IBB) (IBB had been left in the PA divisor); "
                  "IN-PLAY/TOUGH hit bands re-tuned within printed 1986 maxima where a full section clipped hits",
        "ibb_factor": round(f, 4), "retuned": retuned,
        "target_no_ibb": r3(tgt), "expected_before": r3(before), "expected_after": r3(after),
        "previous_sections": prev, "previous_out_table": prev_out}
    return True


def main():
    path = os.path.join(ROOT, "data", "cards.json")
    cards = json.load(open(path))
    n = 0
    for key, card in cards.items():
        if apply(card):
            n += 1
            cb = card["card_bat"]["capacity_basis"]
            if abs(cb["expected_after"]["avg"] - cb["expected_before"]["avg"]) >= 0.005:
                print(key, card["name"], "target", cb["target_no_ibb"], "before", cb["expected_before"], "after", cb["expected_after"])
    open(path, "w").write(json.dumps(cards, sort_keys=True, indent=1) + "\n")
    print("re-tuned", n)


if __name__ == "__main__":
    main()
