#!/usr/bin/env python3
"""Re-solve the printed 1986 pitchers from their real 1986 stats and compare.

For each matched 1986 pitcher (calibrate.matched), solve from his 1986
relative rates and compare with the printed table: result-share mean
absolute gap, slots identical, and card-rate gaps (H, HR, BB, SO per BF).
Usage: validate.py [lambda ...]. Writes validation_1986.json for the
calibrated lambda.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import calibrate  # noqa: E402
import solver  # noqa: E402


def run(lam, restarts=6, iters=800):
    calib = solver.load_calibration()
    lg = solver.league()[1986]
    rows = []
    for p, t in calibrate.matched():
        if not t or not t["bf"]:
            continue
        hand = "L" if p.get("throws") == "L" else "R"
        rel = {k: t[k] / t["bf"] / lg[k] for k in solver.STATS}
        res = solver.solve(solver.target_from(rel, calib), hand, 0, calib, lam, restarts, iters)
        printed = p["pitcher"]["results"]
        ps, ss = solver.shares(printed), solver.shares(res["table"])
        pr = solver.evaluate(printed, hand, 0)
        rows.append({
            "name": p["name"], "printed": printed, "solved": res["table"],
            "share_gap": sum(abs(ps[o] - ss[o]) for o in solver.OUTCOMES) / 2,
            "slots_same": sum(printed[r] == res["table"][r] for r in printed),
            "rate_gap_vs_printed": {k: round(res["card_rates"][k] - pr[k], 4) for k in ("h", "hr", "bb", "so")},
            "rate_gap_vs_target": {k: round(res["card_rates"][k] - res["target"][k], 4) for k in ("h", "hr", "bb", "so")},
            "shares_printed": ps, "shares_solved": ss,
        })
    n = len(rows)
    mean_sh = {o: (round(sum(r["shares_printed"][o] for r in rows) / n, 4), round(sum(r["shares_solved"][o] for r in rows) / n, 4)) for o in solver.OUTCOMES}
    summ = {
        "lambda": lam, "pitchers": n,
        "mean_share_gap": round(sum(r["share_gap"] for r in rows) / n, 4),
        "mean_slots_same_of_11": round(sum(r["slots_same"] for r in rows) / n, 2),
        "mean_abs_rate_gap_vs_printed": {k: round(sum(abs(r["rate_gap_vs_printed"][k]) for r in rows) / n, 4) for k in ("h", "hr", "bb", "so")},
        "mean_abs_rate_gap_vs_target": {k: round(sum(abs(r["rate_gap_vs_target"][k]) for r in rows) / n, 4) for k in ("h", "hr", "bb", "so")},
        "mean_shares_printed_vs_solved": mean_sh,
    }
    return summ, rows


def main():
    lams = [float(x) for x in sys.argv[1:]] or [solver.load_calibration()["lambda"]]
    for lam in lams:
        summ, rows = run(lam)
        print(json.dumps(summ))
    if len(lams) == 1:
        json.dump({"summary": summ, "pitchers": rows}, open(os.path.join(HERE, "validation_1986.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
