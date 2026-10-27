#!/usr/bin/env python3
"""Fit the v0.3 card-rate lines and result shares on the printed 1986 cards.

Pitchers: 1986 cards with 60+ IP printed, matched by name to one Lahman
1986 pitching line (IP within 1 and H equal); the printed card stats are the
1986 season (Boddicker 218 IP, 214 H). Card rate = the printed 2d6 table evaluated with solver.py's
vectors. Relative rate = 1986 rate / 1986 league rate. Line: card rate =
a + b * relative (least squares, BF weighted); scale = weighted residual
SD. Shares: mean, SD, min, max of each result's 2d6 share. Writes
calibration_1986.json.
"""
import csv
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver  # noqa: E402


def matched():
    players, _h, _p = solver._ref()
    lah = {}
    ppl = {r["playerID"]: r["nameFirst"] + " " + r["nameLast"]
           for r in csv.DictReader(open(solver.LAHMAN + "People.csv", encoding="utf-8-sig", errors="replace"))}
    rows = {}
    for r in csv.DictReader(open(solver.LAHMAN + "Pitching.csv", encoding="utf-8-sig")):
        if r["yearID"] != "1986":
            continue
        t = rows.setdefault(r["playerID"], {"ipouts": 0, "h": 0, "hr": 0, "bb": 0, "so": 0, "hbp": 0, "bf": 0})
        for k, c in (("ipouts", "IPouts"), ("h", "H"), ("hr", "HR"), ("bb", "BB"), ("so", "SO"), ("hbp", "HBP"), ("bf", "BFP")):
            t[k] += int(r[c] or 0)
    for pid, t in rows.items():
        lah.setdefault(ppl.get(pid, ""), []).append((pid, t))
    out = []
    for p in players:
        if not p.get("pitcher"):
            continue
        st = p.get("stats") or {}
        if (st.get("IP") or 0) < 60:
            continue
        cands = [t for pid, t in lah.get(p["name"], []) if t["h"] == st.get("H") and abs(t["ipouts"] / 3 - st["IP"]) < 1]
        out.append((p, cands[0] if len(cands) == 1 else None))
    return out


def fit(xs, ys, ws):
    sw = sum(ws)
    mx = sum(w * x for x, w in zip(xs, ws)) / sw
    my = sum(w * y for y, w in zip(ys, ws)) / sw
    sxx = sum(w * (x - mx) ** 2 for x, w in zip(xs, ws))
    sxy = sum(w * (x - mx) * (y - my) for x, y, w in zip(xs, ys, ws))
    b = sxy / sxx
    a = my - b * mx
    res = math.sqrt(sum(w * (y - a - b * x) ** 2 for x, y, w in zip(xs, ys, ws)) / sw)
    ss = sum(w * (y - my) ** 2 for y, w in zip(ys, ws))
    r2 = 1 - sum(w * (y - a - b * x) ** 2 for x, y, w in zip(xs, ys, ws)) / ss
    return {"a": round(a, 5), "b": round(b, 5), "scale": round(res, 5), "r2": round(r2, 3)}


def main():
    pairs = matched()
    allp = [p for p, _ in pairs]
    share_rows = [solver.shares(p["pitcher"]["results"]) for p in allp]
    shares = {}
    for o in solver.OUTCOMES:
        v = [s[o] for s in share_rows]
        mu = sum(v) / len(v)
        sd = math.sqrt(sum((x - mu) ** 2 for x in v) / len(v))
        shares[o] = {"mean": round(mu, 4), "sd": round(sd, 4), "min": round(min(v), 4), "max": round(max(v), 4)}
    good = [(p, t) for p, t in pairs if t and t["bf"]]
    lg = solver.league()[1986]
    xs = {k: [] for k in solver.STATS}
    ys = {k: [] for k in solver.STATS}
    ws = []
    for p, t in good:
        card = solver.evaluate(p["pitcher"]["results"], "L" if p.get("throws") == "L" else "R", 0)
        for k in solver.STATS:
            xs[k].append(t[k] / t["bf"] / lg[k])
            ys[k].append(card[k])
        ws.append(t["bf"])
    lines = {k: fit(xs[k], ys[k], ws) for k in solver.STATS}
    # Hand offset: the printed tables are evaluated against the 1986 hitters'
    # vsLHP / vsRHP sections, and left-handed batters print a large split. A
    # pooled line overstates a left-hander's card rate (h -.008, hr -.0015
    # mean residual for the 67 matched LHP) and understates a right-hander's.
    # The offset is the BF-weighted mean residual by hand, slope shared.
    hands = ["L" if p.get("throws") == "L" else "R" for p, t in good]
    for k in solver.STATS:
        a, b = lines[k]["a"], lines[k]["b"]
        off = {}
        for h in ("L", "R"):
            idx = [i for i, x in enumerate(hands) if x == h]
            sw = sum(ws[i] for i in idx)
            off[h] = round(sum(ws[i] * (ys[k][i] - a - b * xs[k][i]) for i in idx) / sw, 5)
        lines[k]["hand_offset"] = off
    out = {"pitchers_60ip": len(pairs), "matched_lahman_1986": len(good), "lines": lines, "shares": shares,
           "lambda": 0.2, "league_1986": {k: round(v, 4) for k, v in lg.items()}}
    json.dump(out, open(solver.CALIB, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
