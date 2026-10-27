#!/usr/bin/env python3
"""Diagnostic: why do the top hitters hit less in the sim than in real life?

For the top hitters by real OPS+ (window line vs MLB in the same years),
measure the line at each step so the gap can be split into causes:

  real     the card's window line (peak_bat)
  A0       pa_sim, hitter-solver pitcher mix, card BEFORE the platoon re-split
  A        pa_sim, hitter-solver pitcher mix, current card  (card build)
  B        pa_sim vs every tournament pitcher card, uniform   (opponent quality)
  game     full-game stress output, if a stress JSON is given (parks, fatigue,
           fielders, FAC deck, strategy)

Usage: hitter_gap_trace.py [stress.json] [--n 40000] [--top 20]
Writes nothing; prints a table and JSON to stdout.
"""
import argparse, collections, csv, json, os, random, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "engines", "sim"))
import pa_sim  # noqa: E402

LAHMAN = os.environ.get("LAHMAN", "/workspace/legacy_lore/data/lahman/")


def league_by_year():
    t = collections.defaultdict(collections.Counter)
    with open(os.path.join(LAHMAN, "Batting.csv"), encoding="latin1") as f:
        for r in csv.DictReader(f):
            c = t[int(r["yearID"])]
            for k in ("AB", "H", "2B", "3B", "HR", "BB", "HBP", "SF"):
                c[k] += int(r[k] or 0)
    return t


def ops_plus(pb, lg):
    yrs = pb.get("window_years") or []
    L = collections.Counter()
    for y in yrs:
        L.update(lg[int(y)])
    if not L["AB"]:
        return None
    def slash(s):
        tb = s["H"] + s["2B"] + 2 * s["3B"] + 3 * s["HR"]
        pa = s["AB"] + s["BB"] + s["HBP"] + s["SF"]
        return (s["H"] + s["BB"] + s["HBP"]) / pa, tb / s["AB"]
    o, sl = slash({k: pb.get(k) or 0 for k in ("AB", "H", "2B", "3B", "HR", "BB", "HBP", "SF")})
    lo, ls = slash(L)
    return round(100 * (o / lo + sl / ls - 1))


def game_lines(path):
    B = collections.defaultdict(collections.Counter)
    for r in json.load(open(path)):
        if "fail" in r:
            continue
        for k, v in r["box"].items():
            if k.endswith("|field"):
                continue
            for f in ("ab", "h", "hr", "bb", "hbp", "sf", "tb"):
                B[k][f] += v.get(f, 0)
    out = {}
    for k, s in B.items():
        if s["ab"] < 200:
            continue
        pa = s["ab"] + s["bb"] + s["hbp"] + s["sf"]
        out[k] = {"avg": s["h"] / s["ab"], "obp": (s["h"] + s["bb"] + s["hbp"]) / pa,
                  "slg": s["tb"] / s["ab"], "hr": s["hr"] / pa, "pa": pa}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stress", nargs="?")
    ap.add_argument("--n", type=int, default=40000)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--name", action="append", help="trace these players (substring) instead of the top N")
    a = ap.parse_args()
    cards = json.load(open(os.path.join(ROOT, "data", "cards.json")))
    batters, pitchers = pa_sim.load_pool()
    lg = league_by_year()
    games = game_lines(a.stress) if a.stress else {}
    ranked = []
    for b in batters:
        pb = cards[b.key].get("peak_bat") or {}
        if (pb.get("PA") or 0) < 400 or (games and b.key not in games):
            continue
        ranked.append((ops_plus(pb, lg) or 0, b))
    ranked.sort(key=lambda x: -x[0])
    rows = []
    pick = [x for x in ranked if any(n.lower() in x[1].name.lower() for n in a.name)] if a.name else ranked[: a.top]
    for opsp, b in pick:
        card = cards[b.key]
        rng = random.Random(1)
        A = pa_sim.simulate_hitter_solver_mix(rng, b, a.n).rates()
        prev = (card["card_bat"].get("platoon_basis") or {}).get("previous_sections")
        A0 = None
        if prev:
            c0 = json.loads(json.dumps(card)); c0["card_bat"]["sections"] = prev
            A0 = pa_sim.simulate_hitter_solver_mix(random.Random(1), pa_sim.Batter(b.key, c0), a.n).rates()
        Bv = pa_sim.simulate_hitter(random.Random(1), b, pitchers, a.n).rates()
        hand = {}
        for h, pool in (("vsL", [p for p in pitchers if p.throws == "L"]), ("vsR", [p for p in pitchers if p.throws != "L"])):
            hand[h] = pa_sim.simulate_hitter(random.Random(2), b, pool, a.n // 2).rates()
        rows.append({"key": b.key, "name": b.name, "bats": b.bats, "ops_plus": opsp,
                     "window": card["peak_bat"].get("window_years"),
                     "real": b.source, "A0": A0, "A": A, "B": Bv, "hand": hand, "game": games.get(b.key)})
    f = lambda r: ("%.3f/%.3f/%.3f %4.1f%%" % (r["avg"], r["obp"], r["slg"], 100 * r["hr"])) if r else "-"
    for r in rows:
        print("%-22s %s OPS+%3d real %s | A0 %s | A %s | B %s | game %s" % (
            r["name"], r["bats"], r["ops_plus"], f(r["real"]), f(r["A0"]), f(r["A"]), f(r["B"]), f(r["game"])))
    print(json.dumps(rows))


if __name__ == "__main__":
    main()
