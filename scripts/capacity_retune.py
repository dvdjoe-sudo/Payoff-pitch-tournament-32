#!/usr/bin/env python3
"""Hitter card repair: intentional walks, then hits a full section pushed off.

1. Intentional walks count as walks (owner ruling 2026-10-27). The
   engine has no intentional walk, so the card's walk target is BB
   (which includes IBB) over full PA. The solver had dropped IBB from BB but
   left it in PA, so each IBB became an out (Barry Bonds, IBB 10.5% of PA,
   came out .301 against .346). This pass adds PATIENT BB faces, both hands
   alike, taken from empty (out) faces first and then from PATIENT hit
   faces (step 2 puts those hits back in IN-PLAY/TOUGH), until the expected walk rate
   reaches the target. PATIENT holds at most 99 faces (about 22.9% of PA);
   a card that cannot reach its walk target is flagged walk_cap_hit, and
   the walks it cannot print are dropped as plate appearances (other bands
   scaled by 1/(1-shortfall)) instead of becoming outs, so only OBP is short.
   hitter_solver.build_one now builds targets the same way.

The hitter solver keeps 1B/2B/3B on the comp cards' section mix
(project_shaped). When PATIENT or WHEELHOUSE is already full (99 faces of
walks or homers), the share of hits sent there is clipped at face 99 and
lost, and the projection will not let the tuner move them to IN-PLAY or
TOUGH, which still have room. Babe Ruth's card came out .294 against a
.375 target this way, with 69 empty IN-PLAY faces.

This pass re-tunes only the IN-PLAY and TOUGH hit bands, both hands
together, against the card's own window line (all walks, IBB included), never above the widest band printed on a 1986 card
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
    pa, ab = g("PA"), g("AB")
    if pa <= 0 or ab <= 0:
        return None
    h, ubb, hbp, hr = g("H"), g("BB"), g("HBP"), g("HR")  # BB includes IBB
    d, t = g("2B"), g("3B")
    return {"avg": h / ab, "obp": (h + ubb + hbp) / pa, "slg": (h + d + 2 * t + 3 * hr) / ab,
            "bbp": ubb / pa, "sop": g("SO") / pa, "hrp": hr / pa, "hbpp": hbp / pa,
            "1bp": (h - d - t - hr) / pa, "2bp": d / pa, "3bp": t / pa}


def _bats(bat):
    b = (bat.get("bats") or "R")[0]
    return b if b in "LRS" else ("S" if b == "B" else "R")


def add_walks(sections, tgt, bats, run):
    """Widen PATIENT BB one face per hand at a time, from empty faces, then hit faces,
    until the expected walk rate reaches the target. Returns (sections, capped)."""
    W = hs.widths_from_sections(sections)
    keys = hs.CANON["PATIENT"]
    while hs.expected(hs.lay_out(W), bats, run)["bbp"] < tgt["bbp"] - 1e-9:
        room = [99 - sum(W[("PATIENT", h, k)] for k in keys) for h in ("vsLHP", "vsRHP")]
        moved = False
        for h, r in zip(("vsLHP", "vsRHP"), room):
            if r <= 0:  # no empty face: take a PATIENT hit face (re-tuned into IN-PLAY/TOUGH below)
                k = next((x for x in ("1B", "2B", "3B") if W[("PATIENT", h, x)] > 0), None)
                if k is None:
                    continue
                W[("PATIENT", h, k)] -= 1
            W[("PATIENT", h, "BB")] += 1
            moved = True
        if not moved:
            return hs.lay_out(W), True
    return hs.lay_out(W), False


def cap_rescale(sections, f):
    """A capped card cannot print every walk. Those plate appearances are
    dropped rather than turned into outs: every other band is scaled by
    f = 1 / (1 - walk shortfall), so AVG and SLG keep their real values and
    only OBP falls short. Overflow trims 1B, 2B, 3B, HBP, SO, HR."""
    W = hs.widths_from_sections(sections)
    for sec, keys in hs.CANON.items():
        for hand in ("vsLHP", "vsRHP"):
            for k in keys:
                if not (sec == "PATIENT" and k == "BB"):
                    W[(sec, hand, k)] = int(round(W[(sec, hand, k)] * f))
            over = sum(W[(sec, hand, k)] for k in keys) - 99
            for k in ("1B", "2B", "3B", "HBP", "SO", "HR"):
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
    new, capped = add_walks(prev, tgt, bats, run)
    shortfall = 0.0
    if capped:
        shortfall = tgt["bbp"] - hs.expected(new, bats, run)["bbp"]
        f = 1.0 / (1.0 - shortfall)
        new = cap_rescale(new, f)
        # the hit re-tune aims at the same rates on the PA that remain
        tgt = dict(tgt, **{k: tgt[k] * f for k in ("1bp", "2bp", "3bp", "hrp", "hbpp", "sop")})
        tgt["bbp"] = hs.expected(new, bats, run)["bbp"]
        tgt["obp"] = min(tgt["obp"], tgt["avg"] * (1 - tgt["bbp"] - tgt["hbpp"]) + tgt["bbp"] + tgt["hbpp"])
    retuned = False
    mid = hs.expected(new, bats, run)
    if saturated(new) and mid["avg"] <= tgt["avg"] - MIN_SHORT:
        cand, _e = retune(new, tgt, bats, run)
        after = hs.expected(cand, bats, run)
        # keep only a real gain in AVG without losing SLG
        if after["avg"] >= mid["avg"] + 0.001 and after["slg"] >= mid["slg"]:
            new, retuned = cand, True
    if new == prev and not capped:
        bat.pop("capacity_basis", None)
        return False
    after = hs.expected(new, bats, run)
    bat["sections"] = new
    _per, bat["out_table"] = hs.out_tables_from_holes(new, prev_out)
    r3 = lambda e: {k: round(e[k], 3) for k in ("avg", "obp", "slg")}
    bat["capacity_basis"] = {
        "method": "IBB counted as BB (owner ruling 2026-10-27): PATIENT BB widened from empty faces to BB/PA; "
                  "IN-PLAY/TOUGH hit bands re-tuned within printed 1986 maxima where a full section clipped hits",
        "ibb": int(pb.get("IBB") or 0), "walk_target_bbp": round(tgt["bbp"], 4),
        "walk_expected_bbp": round(after["bbp"], 4), "walk_cap_hit": capped, "walk_shortfall": round(shortfall, 4), "retuned": retuned,
        "target": r3(target(pb)), "retune_target": r3(tgt), "expected_before": r3(before), "expected_after": r3(after),
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
                print(key, card["name"], "target", cb["target"], "CAP" if cb["walk_cap_hit"] else "", "before", cb["expected_before"], "after", cb["expected_after"])
    open(path, "w").write(json.dumps(cards, sort_keys=True, indent=1) + "\n")
    print("re-tuned", n)


if __name__ == "__main__":
    main()
