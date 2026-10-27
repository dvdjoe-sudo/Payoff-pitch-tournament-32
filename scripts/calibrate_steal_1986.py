#!/usr/bin/env python3
"""Fit the Jump and Steal-letter cut points on the printed 1986 cards
against the players' real 1986 stats (Lahman Batting.csv, yearID 1986).

The 1986 set prints 1986 season stats (e.g. Boddicker 218 IP, 214 H), so
the card is matched to the Lahman 1986 line whose AB and H equal the
card's printed split totals. The earlier cut points were fit against 1985.

Jump: rate = (SB+CS) / (1B+BB+HBP). Each boundary k|k+1 takes the
threshold that best separates cards printed <= k from cards printed > k,
kept increasing. Letter: score = (SB + 20*.65) / (SB+CS+20) + 4 * rate;
cuts sit at the 1986 letter shares. Writes steal_calibration_1986.json.
"""
import collections, csv, json, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LAHMAN = os.environ.get("LAHMAN", "/workspace/legacy_lore/data/lahman/")
OUT = os.path.join(ROOT, "historical-cards", "reference", "steal_calibration_1986.json")


def rows():
    ppl = {r["playerID"]: (r["nameFirst"] + " " + r["nameLast"]) for r in csv.DictReader(open(LAHMAN + "People.csv", encoding="utf-8-sig"))}
    bat = collections.defaultdict(collections.Counter)
    for r in csv.DictReader(open(LAHMAN + "Batting.csv", encoding="utf-8-sig")):
        if r["yearID"] == "1986":
            for k in ("AB", "H", "2B", "3B", "HR", "BB", "HBP", "SB", "CS"):
                bat[r["playerID"]][k] += int(r[k] or 0)
    byname = collections.defaultdict(list)
    for pid, c in bat.items():
        byname[ppl.get(pid, "")].append(c)
    cards = json.load(open(os.path.join(ROOT, "historical-cards", "reference", "cards_1986.json")))["players"]
    out, unmatched = [], 0
    for p in cards:
        if p.get("pitcher") or not p.get("steal"):
            continue
        sp = p.get("stats_split") or {}
        ab = sum(int((s or {}).get("AB") or 0) for s in sp.values())
        h = sum(int((s or {}).get("H") or 0) for s in sp.values())
        if ab < 100:
            continue
        c = [c for c in byname.get(p["name"], []) if c["AB"] == ab and (not h or c["H"] == h)]
        if len(c) != 1:
            unmatched += 1
            continue
        c = c[0]
        opp = c["H"] - c["2B"] - c["3B"] - c["HR"] + c["BB"] + c["HBP"]
        if opp < 30:
            continue
        s = p["steal"]
        rate = (c["SB"] + c["CS"]) / opp
        score = (c["SB"] + 20 * 0.65) / (c["SB"] + c["CS"] + 20) + 4 * rate
        out.append({"name": p["name"], "jump": s.get("jump"), "letter": s.get("rating"), "rate": rate, "score": score,
                    "sb": c["SB"], "cs": c["CS"]})
    return out, unmatched


def main():
    rs, unmatched = rows()
    jr = [r for r in rs if isinstance(r["jump"], int)]
    levels = sorted(set(r["jump"] for r in jr))
    cuts, lo = [], 0.0
    for k in levels[:-1]:
        cand = sorted(set(round(r["rate"], 4) for r in jr if r["rate"] >= lo))
        best = min(cand, key=lambda t: sum((r["rate"] > t) != (r["jump"] > k) for r in jr))
        cuts.append(best)
        lo = best
    pred = lambda x: levels[0] + sum(x > c for c in cuts)
    exact = sum(pred(r["rate"]) == r["jump"] for r in jr) / len(jr)
    within = sum(abs(pred(r["rate"]) - r["jump"]) <= 1 for r in jr) / len(jr)
    lr = [r for r in rs if r["letter"] in tuple("ABCDF")]
    share = collections.Counter(r["letter"] for r in lr)
    sc = sorted(r["score"] for r in lr)
    lcuts, acc = [], 0
    for L in "FDCB":
        acc += share[L]
        lcuts.append(round(sc[min(len(sc) - 1, acc)] if acc < len(sc) else sc[-1], 4))
    lp = lambda x: "FDCBA"[sum(x > c for c in lcuts)]
    order = "FDCBA"
    lex = sum(lp(r["score"]) == r["letter"] for r in lr) / len(lr)
    lwi = sum(abs(order.index(lp(r["score"])) - order.index(r["letter"])) <= 1 for r in lr) / len(lr)
    med = {k: round(sorted(r["rate"] for r in jr if r["jump"] == k)[len([r for r in jr if r["jump"] == k]) // 2], 3) for k in levels}
    out = {"season": 1986, "matched": len(rs), "unmatched_or_ambiguous": unmatched,
           "jump": {"levels": levels, "cuts": cuts, "exact": round(exact, 3), "within_one": round(within, 3),
                    "n": len(jr), "median_rate_by_jump": med},
           "letter": {"cuts_FDCBA": lcuts, "shares": dict(share), "exact": round(lex, 3), "within_one": round(lwi, 3), "n": len(lr)}}
    json.dump(out, open(OUT, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
