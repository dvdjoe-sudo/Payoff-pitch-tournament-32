#!/usr/bin/env python3
"""Pitcher 2d6 solver v0.3.

Replaces the v0.2.3 solver's DEFENSE placeholder (25% singles, no
errors) and its SO/BB/HR-only target.

Result vectors (what one 2d6 result does to a league-average batter):
- WHEELHOUSE, PATIENT, TOUGH, IN-PLAY: the mean over the 596 printed 1986
  hitter cards, faces 01-99 (00 is a rare play), with the page-39 +10/+20
  shift on TOUGH (engines/pitcher-v0.2.3/printed_shift.py), as game.py
  reads it.
- BALLPARK: the 1986 park cards' WHEELHOUSE faces (wh_l / wh_r out of 99,
  by the batter's side against this hand) re-roll to WHEELHOUSE, the
  rest to IN-PLAY.
- DEFENSE: measured in game.py itself (defense_probe.py): FAC defense
  line, park range/error band, tournament fielders, FAC HIT/ERR/OUT cell.
  Reached-on-error and fielder's choice are at-bats with no hit.

Target (per batter faced): H, HR, BB, SO, HBP. Each is the pitcher's
window rate relative to the league in the same seasons (Lahman Pitching
totals), mapped to card space by a line fitted on the printed 1986
cards (card rate of the printed table vs the pitcher's 1985 relative
rate). 2B/3B allowed are not in pitching records, so they are not
targeted (the card's doubles/triples come from the hitter cards).

Shares: the fit adds a penalty pulling each result's share of the 36
2d6 outcomes toward the printed 1986 mean (263 pitchers, 60+ IP), scaled
by the 1986 spread, and keeps each share inside the 1986 range.
TOUGH-OUT / PATIENT-OUT are not used (2 of 2,893 printed 1986 slots).
"""
import csv
import json
import os
import random
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "engines", "pitcher-v0.2.3"))
REF = os.path.join(ROOT, "historical-cards", "reference")
LAHMAN = os.environ.get("LAHMAN", "/workspace/legacy_lore/data/lahman/")
CALIB = os.path.join(HERE, "calibration_1986.json")

D6_W = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1}
OUTCOMES = ["WHEELHOUSE", "PATIENT", "TOUGH", "IN-PLAY", "BALLPARK", "DEFENSE"]
EV = ("1B", "2B", "3B", "HR", "BB", "HBP", "SO", "ROE", "FC", "OUT")
STATS = ("h", "hr", "bb", "so", "hbp")

_VEC = {}
_REF = None


def _ref():
    global _REF
    if _REF is None:
        players = json.load(open(os.path.join(REF, "cards_1986.json")))["players"]
        hitters = [p for p in players if not p.get("pitcher")]
        parks = json.load(open(os.path.join(REF, "ballparks.json")))
        _REF = (players, hitters, parks)
    return _REF


def _clean(vec):
    out = {k: float(vec.get(k, 0.0)) for k in EV}
    tot = sum(out.values())
    return {k: v / tot for k, v in out.items()}


def vectors(hand="R", bump=0):
    key = (hand, bump)
    if key in _VEC:
        return _VEC[key]
    from printed_shift import vectors_for_bump
    players, hitters, parks = _ref()
    base = vectors_for_bump(hand, bump, hitters=hitters)
    v = {k: _clean(base[k]) for k in ("WHEELHOUSE", "PATIENT", "TOUGH", "IN-PLAY", "TOUGH-OUT", "PATIENT-OUT")}
    # BALLPARK: share of batters standing L against this hand.
    sides = [h.get("bats") for h in hitters]
    n = float(len(sides))
    left = sum(1 for s in sides if s == "L" or (s == "S" and hand == "R")) / n
    wh_l = sum(int(p["wh_l"]) for p in parks) / len(parks) / 99.0
    wh_r = sum(int(p["wh_r"]) for p in parks) / len(parks) / 99.0
    wheel = left * wh_l + (1 - left) * wh_r
    v["BALLPARK"] = {k: wheel * v["WHEELHOUSE"][k] + (1 - wheel) * v["IN-PLAY"][k] for k in EV}
    probe = json.load(open(os.path.join(HERE, "defense_vector.json")))["vector"]
    d = {k: probe.get(k, 0.0) for k in EV}
    d["OUT"] += probe.get("RARE", 0.0)
    v["DEFENSE"] = _clean(d)
    _VEC[key] = v
    return v


def shares(table):
    s = {o: 0.0 for o in OUTCOMES + ["TOUGH-OUT", "PATIENT-OUT"]}
    for roll, o in table.items():
        s[o] = s.get(o, 0.0) + D6_W[int(roll)] / 36.0
    return s


def evaluate(table, hand="R", bump=0):
    vec = vectors(hand, bump)
    tot = {k: 0.0 for k in EV}
    for roll, o in table.items():
        w = D6_W[int(roll)] / 36.0
        for k in EV:
            tot[k] += w * vec[o][k]
    return {
        "h": tot["1B"] + tot["2B"] + tot["3B"] + tot["HR"], "hr": tot["HR"], "bb": tot["BB"],
        "so": tot["SO"], "hbp": tot["HBP"], "roe": tot["ROE"],
    }


# ---- league rates and 1986 calibration ---------------------------------

_LG = None


def league():
    global _LG
    if _LG is None:
        lg = defaultdict(lambda: defaultdict(float))
        for r in csv.DictReader(open(LAHMAN + "Pitching.csv", encoding="utf-8-sig")):
            y = int(r["yearID"])
            for k, c in (("h", "H"), ("hr", "HR"), ("bb", "BB"), ("so", "SO"), ("hbp", "HBP"), ("bf", "BFP")):
                lg[y][k] += float(r[c] or 0)
        _LG = {y: {k: t[k] / t["bf"] for k in STATS} for y, t in lg.items() if t["bf"]}
    return _LG


def league_rate(years):
    lg = league()
    last = max(lg)
    use = [min(y, last) for y in years if y >= 1871]
    if not use:
        return None
    return {k: sum(lg[y][k] for y in use) / len(use) for k in STATS}


def relative(totals, years):
    """Pitcher rate / league rate over the same seasons."""
    bf = float(totals["bf"])
    lr = league_rate(years)
    return {k: (float(totals.get(k) or 0) / bf) / lr[k] for k in STATS}


def load_calibration():
    return json.load(open(CALIB))


def target_from(rel, calib, hand="R"):
    t = {}
    for k in STATS:
        line = calib["lines"][k]
        off = (line.get("hand_offset") or {}).get("L" if hand == "L" else "R", 0.0)
        t[k] = max(0.0, line["a"] + line["b"] * rel[k] + off)
    return t


# ---- search ------------------------------------------------------------

def objective(table, target, hand, bump, calib, lam):
    ev = evaluate(table, hand, bump)
    e = 0.0
    for k in STATS:
        e += ((ev[k] - target[k]) / calib["lines"][k]["scale"]) ** 2
    sh = shares(table)
    for o in OUTCOMES:
        mu, sd, lo, hi = (calib["shares"][o][x] for x in ("mean", "sd", "min", "max"))
        e += lam * ((sh[o] - mu) / sd) ** 2
        if sh[o] < lo - 1e-9 or sh[o] > hi + 1e-9:
            e += 1e3
    return e


def solve(target, hand="R", bump=0, calib=None, lam=None, restarts=12, iters=1500, seed=0):
    calib = calib or load_calibration()
    lam = calib.get("lambda", 0.05) if lam is None else lam
    rng = random.Random(seed)
    best = (float("inf"), None)
    rolls = [str(r) for r in range(2, 13)]
    mean = calib["shares"]
    for _ in range(restarts):
        # Start from the 1986 mean mix.
        tbl = {r: rng.choices(OUTCOMES, weights=[mean[o]["mean"] for o in OUTCOMES])[0] for r in rolls}
        e = objective(tbl, target, hand, bump, calib, lam)
        for _ in range(iters):
            nt = dict(tbl)
            if rng.random() < 0.3:
                a, b = rng.sample(rolls, 2)
                nt[a], nt[b] = nt[b], nt[a]
            else:
                r = rng.choice(rolls)
                nt[r] = rng.choice([o for o in OUTCOMES if o != nt[r]])
            ne = objective(nt, target, hand, bump, calib, lam)
            if ne <= e:
                tbl, e = nt, ne
        if e < best[0]:
            best = (e, tbl)
    e, tbl = best
    return {"table": dict(sorted(tbl.items(), key=lambda t: int(t[0]))), "objective": round(e, 4),
            "card_rates": {k: round(v, 4) for k, v in evaluate(tbl, hand, bump).items()},
            "target": {k: round(v, 4) for k, v in target.items()}}


def batter_card_out_rate(table, hand="R", bump=0):
    """Per batter faced: outs read off the batter's card (any result but DEFENSE)."""
    vec = vectors(hand, bump)
    return sum(D6_W[int(r)] / 36.0 * vec[o]["OUT"] for r, o in table.items() if o != "DEFENSE")


SUPP_SO_START = 50   # rulebook page 11: the band starts at 50 or 90 by set; the 2024 set prints 50 - nn
SUPP_SO_MIN_GAP = 0.015  # about 0.6 K per 9 IP; smaller gaps are fit noise


def supplemental_so_band(table, target_so, hand="R", bump=0):
    """Rulebook page 11 optional Supplemental Strikeout band, sized to the
    card's strikeout shortfall. When a batter makes an out on his card and the
    percentile falls in the band, it is a strikeout. Each face of the band
    turns 1/100 of those outs into strikeouts. None when the table already
    reaches the target."""
    gap = target_so - evaluate(table, hand, bump)["so"]
    if gap < SUPP_SO_MIN_GAP:
        return None
    outs = batter_card_out_rate(table, hand, bump)
    if outs <= 0:
        return None
    width = min(100 - SUPP_SO_START, int(round(gap / outs * 100)))
    if width < 1:
        return None
    return [SUPP_SO_START, SUPP_SO_START + width - 1]


def bump_of(mod):
    return {"+10": 10, "+20": 20}.get(str(mod or "NONE"), 0)
