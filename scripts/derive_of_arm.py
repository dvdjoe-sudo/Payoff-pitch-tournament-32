#!/usr/bin/env python3
"""Rate outfield arms on Derived-fielding cards from real assists.

The Derived cards (scripts/derive_hitter_fielding.py) rated range and
error but left the arm on the engine default 6. This rates the arm on the
rulebook page 8 scale (3 best .. 10 worst) from outfield assists per
outfield game over the card's window seasons, relative to the league
outfield rate in each season (Lahman Fielding POS=OF, all clubs that
season). Cut points are fitted to the printed 1986 outfield arms
matched to each player's 1985 line, keeping the 1986 share of each arm.
Only Derived cards with an outfield row change, only the arm. Fewer than
THIN outfield games in the window is flagged thin; fewer than MIN keeps 6.
Runner-advance (hold/kill) data is not in Lahman, so it is not used.
"""
import csv
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CARDS = os.path.join(ROOT, "data", "cards.json")
REF = os.path.join(ROOT, "historical-cards", "reference", "cards_1986.json")
LAHMAN = os.environ.get("LAHMAN", "/workspace/legacy_lore/data/lahman/")
REPORT = os.path.join(ROOT, "historical-cards", "accuracy", "derived_of_arms.json")
OF = ("LF", "CF", "RF")
THIN, MIN = 100, 30


def load():
    per = defaultdict(lambda: [0, 0])        # (pid, year) -> [G, A]
    lg = defaultdict(lambda: [0, 0])
    for r in csv.DictReader(open(LAHMAN + "Fielding.csv")):
        if r["POS"] != "OF":
            continue
        y, g, a = int(r["yearID"]), int(r["G"] or 0), int(r["A"] or 0)
        per[(r["playerID"], y)][0] += g
        per[(r["playerID"], y)][1] += a
        lg[y][0] += g
        lg[y][1] += a
    return per, lg


def rel(per, lg, pid, years):
    g = a = exp = 0.0
    used = []
    for y in years:
        pg, pa = per.get((pid, y), (0, 0))
        if pg and lg[y][0]:
            g += pg; a += pa; exp += pg * lg[y][1] / lg[y][0]; used.append(y)
    return (a / exp if exp else None), int(g), int(a), used


def fit(per, lg):
    ppl = {r["playerID"]: r["nameFirst"] + " " + r["nameLast"]
           for r in csv.DictReader(open(LAHMAN + "People.csv", encoding="latin1"))}
    byname = defaultdict(list)
    for (pid, y), (g, a) in per.items():
        if y == 1985 and g >= 40:
            byname[ppl.get(pid, "")].append(pid)
    ref = json.load(open(REF))
    pts = []
    for v in ref.values():
        if not isinstance(v, list):
            continue
        for p in v:
            arms = [q.get("arm") for q in p.get("positions") or [] if q.get("pos") in OF and q.get("arm")]
            ids = byname.get(p.get("name"), [])
            if arms and len(ids) == 1:
                r = rel(per, lg, ids[0], [1985])[0]
                if r is not None:
                    pts.append((r, min(arms)))
    pts.sort(key=lambda t: -t[0])            # strongest arm first
    share = Counter(a for _, a in pts)
    cuts, acc = [], 0
    for arm in sorted(share)[:-1]:
        acc += share[arm]
        cuts.append((pts[acc - 1][0] + pts[acc][0]) / 2)
    pred = [sorted(share)[sum(r < c for c in cuts)] for r, _ in pts]
    exact = sum(p == a for p, (_, a) in zip(pred, pts)) / len(pts)
    near = sum(abs(p - a) <= 1 for p, (_, a) in zip(pred, pts)) / len(pts)
    return sorted(share), cuts, {"matched": len(pts), "exact": round(exact, 3), "within_one": round(near, 3),
                                 "shares": dict(sorted(share.items()))}


def main():
    per, lg = load()
    arms, cuts, fitinfo = fit(per, lg)
    cards = json.load(open(CARDS, encoding="utf-8"))
    out = []
    for key, c in cards.items():
        bat = c.get("card_bat") or {}
        if bat.get("fielding") != "Derived":
            continue
        rows = [q for q in bat.get("positions") or [] if q.get("pos") in OF]
        if not rows:
            continue
        years = (c.get("peak_bat") or {}).get("window_years") or []
        r, g, a, used = rel(per, lg, c["id"], years)
        rec = {"key": key, "name": c["name"], "window": years, "years_used": used, "of_g": g, "of_a": a,
               "rel_assist_rate": None if r is None else round(r, 3), "old_arm": rows[0].get("arm")}
        if r is None or g < MIN:
            rec.update(new_arm=rows[0].get("arm"), flag="no/too few outfield games in Lahman; default kept")
        else:
            new = arms[sum(r < cc for cc in cuts)]
            rec["new_arm"] = new
            if g < THIN:
                rec["flag"] = "thin: fewer than %d OF games" % THIN
            if len(used) < len(years):
                rec["flag"] = (rec.get("flag", "") + "; window seasons missing from Lahman: %s"
                               % sorted(set(years) - set(used))).lstrip("; ")
            for q in rows:
                q["arm"] = new
            bat["of_arm_basis"] = {k: rec[k] for k in ("of_g", "of_a", "rel_assist_rate", "years_used")}
            bat["of_arm_basis"]["method"] = "scripts/derive_of_arm.py: OF assists/G vs league, fitted to 1986 printed arms"
        out.append(rec)
    with open(CARDS, "w", encoding="utf-8") as h:
        h.write(json.dumps(cards, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    json.dump({"fit": fitinfo, "cuts_rel": [round(x, 3) for x in cuts], "arms": arms, "cards": out},
              open(REPORT, "w"), indent=1)
    print(fitinfo, [round(x, 3) for x in cuts])
    print("cards", len(out), "changed", sum(r["new_arm"] != r["old_arm"] for r in out),
          "flagged", sum("flag" in r for r in out), Counter(r["new_arm"] for r in out))


if __name__ == "__main__":
    main()
