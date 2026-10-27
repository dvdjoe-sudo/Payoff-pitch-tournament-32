#!/usr/bin/env python3
"""Stress-test the game engine. Writes nothing to tournament files.

Every ordered pair of clubs (home and away) plays SEEDS games on the Fast
Action Cards. Each game runs under a time limit and is checked for crashes,
impossible states, box-score consistency and rule-path coverage. Output is a
JSON summary to stdout (or --out PATH outside the data folders).
"""
import argparse
import collections
import json
import multiprocessing
import os
import re
import signal
import sys
import time
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "engines", "sim"))
import game as G  # noqa: E402

ROSTERS = json.load(open(os.path.join(ROOT, "data", "rosters.json")))
CARDS = json.load(open(os.path.join(ROOT, "data", "cards.json")))
TIMEOUT = 20
PATHS = ["_rare", "_injury", "_resolve_steal", "_pickoff_runner", "_bunt", "_hit_and_run",
         "_play_at_home", "_infield_in", "_fac_steal_error", "_fac_steal_drop", "_hold_steal",
         "_wild_reroll", "_extra_base", "_supplemental_strikeout"]


class Timeout(Exception):
    pass


def _alarm(*_):
    raise Timeout()


class Checked(G.Game):
    def __init__(self, *a, **k):
        self.problems = []
        self.calls = collections.Counter()
        self.pa = collections.Counter()      # batting box key -> plate appearances
        self.pa_by_pitcher = collections.Counter()
        self.removed_batted = []
        self.restarts = 0
        self.matchups = []   # [batter key, pitcher key, ab, h, tb, bb, hbp, so, reached_without_hit]
        self.steals = []     # [runner key, jump, letter, catcher arm, outcome, auto]
        super().__init__(*a, **k)
        for name in PATHS:
            orig = getattr(self, name, None)
            if orig is None:
                continue

            def wrap(*args, _o=orig, _n=name, **kw):
                self.calls[_n] += 1
                return _o(*args, **kw)
            setattr(self, name, wrap)

    def _resolve_steal(self, base, letter, runner):
        key = self.batting["code"] + "|" + runner["id"]
        before = dict(self.box.get(key) or {})
        arm = self._arm_of(self._fielder("C"))
        super()._resolve_steal(base, letter, runner)
        after = self.box.get(key) or {}
        out = "sb" if after.get("sb", 0) > before.get("sb", 0) else \
            "cs" if after.get("cs", 0) > before.get("cs", 0) else "none"
        st = runner.get("steal") or {}
        self.steals.append([key, st.get("jump"), letter, arm, out, base])

    def _check_state(self, where):
        if self.outs > 3:
            self.problems.append("outs %d %s" % (self.outs, where))
        ids = [b["id"] for b in self.bases if b]
        if len(ids) != len(set(ids)):
            self.problems.append("same runner on two bases %s" % where)
        bat_ids = {p["id"] for p in self.batting["people"]}
        for b in self.bases:
            if b and b["id"] not in bat_ids:
                self.problems.append("fielding-side runner on base %s" % where)

    def _plate(self):
        club = self.batting
        idx = self.order_index[club["code"]] % 9
        batter = club["lineup"][idx]
        before = len(self.log)
        order_before = self.order_index[club["code"]]
        state = self.pitcher[self.fielding["code"]]
        pkey = self.fielding["code"] + "|" + state["player"]["id"]
        if batter["removed"]:
            self.removed_batted.append(batter["name"])
        bkey = club["code"] + "|" + batter["id"]
        line0 = dict(self.box.get(bkey) or {})
        super()._plate()
        line1 = self.box.get(bkey) or {}
        d = {f: line1.get(f, 0) - line0.get(f, 0) for f in ("ab", "h", "tb", "bb", "hbp", "so")}
        on = any(b is not None and b["id"] == batter["id"] for b in self.bases)
        if self.order_index[club["code"]] != order_before:
            self.matchups.append([bkey, pkey, d["ab"], d["h"], d["tb"], d["bb"], d["hbp"], d["so"],
                                  int(d["ab"] == 1 and d["h"] == 0 and d["so"] == 0 and on)])
        said = [l for l in self.log[before:] if " vs " in l and l.startswith(batter["name"] + " (")]
        if self.order_index[club["code"]] == order_before:
            self.restarts += 1
        elif said:
            self.pa[club["code"] + "|" + batter["id"]] += 1
            self.pa_by_pitcher[pkey] += 1
        else:
            self.problems.append("BF/order spent with no plate appearance: %s inning %d %s" % (batter["name"], self.inning, self.half))
        self._check_state("after PA inning %d" % self.inning)


PROXY_PARK = None
OPTS = {}


def one(job):
    home, away, seed = job
    if PROXY_PARK and G.park_for(home) is None:
        # Stress-only stand-in so these clubs' home games exercise the engine.
        # Not a ruling on which park they use; nothing here is written to data.
        G.HOME_PARK[home] = PROXY_PARK
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(TIMEOUT)
    t0 = time.time()
    try:
        g = Checked(G.load_club(home, ROSTERS, CARDS), G.load_club(away, ROSTERS, CARDS), seed=seed, **OPTS)
        rep = g.play()
    except Timeout:
        return {"job": job, "fail": "timeout"}
    except BaseException:
        return {"job": job, "fail": traceback.format_exc()[-800:]}
    finally:
        signal.alarm(0)
    probs = list(g.problems)
    if g.removed_batted:
        probs.append("removed (injured/ejected) player batted: %s" % sorted(set(g.removed_batted)))
    box, pit = rep["box"], rep["pitching"]
    for code in (home, away):
        runs = sum(v.get("r", 0) for k, v in box.items() if k.startswith(code + "|") and not k.endswith("|field"))
        if runs != rep["score"][code]:
            probs.append("%s box runs %d != score %d" % (code, runs, rep["score"][code]))
        allowed = sum(v["r"] for k, v in pit.items() if k.startswith(code + "|"))
        other = away if code == home else home
        if allowed != rep["score"][other]:
            probs.append("%s pitchers' R %d != %s score %d" % (code, allowed, other, rep["score"][other]))
    for k, v in box.items():
        if k.endswith("|field"):
            continue
        parts = v["ab"] + v["bb"] + v["hbp"] + v["sf"] + v["sh"]
        if parts != g.pa.get(k, 0):
            probs.append("PA %s: AB+BB+HBP+SF+SH %d != PA %d" % (v["name"], parts, g.pa.get(k, 0)))
        if v["h"] > v["ab"] or v["hr"] > v["h"]:
            probs.append("H/HR > AB %s" % v["name"])
    for k, v in pit.items():
        if v["bf"] != g.pa_by_pitcher.get(k, 0):
            probs.append("BF %s %d != PA faced %d" % (v["name"], v["bf"], g.pa_by_pitcher.get(k, 0)))
    total_bf = sum(v["bf"] for v in pit.values())
    total_pa = sum(g.pa.values())
    if total_bf != total_pa:
        probs.append("total BF %d != total PA %d" % (total_bf, total_pa))
    outs = {code: sum(v["outs"] for k, v in pit.items() if k.startswith(code + "|")) for code in (home, away)}
    inn = rep["innings"]
    if not rep["postponed"]:
        if rep["score"][home] == rep["score"][away]:
            probs.append("finished tied")
        if outs[away] < 3 * (inn - 1) or outs[away] > 3 * inn:
            probs.append("home batters made %d outs in %d innings" % (outs[away], inn))
        if outs[home] != 3 * inn:
            probs.append("away batters made %d outs in %d innings" % (outs[home], inn))
    zero_bf = [v["name"] for v in pit.values() if v["bf"] == 0]
    joined = "\n".join(rep["log"])
    return {
        "job": job, "secs": time.time() - t0, "problems": probs, "score": rep["score"],
        "innings": inn, "postponed": rep["postponed"], "box": box, "pit": pit,
        "calls": dict(g.calls), "wp": rep["wp"], "zero_bf": zero_bf,
        "dp": len(re.findall(r"[Dd]ouble play", joined)),
        "gaps": rep["gaps"], "safety30": "Safety stop at 30" in joined,
        "matchups": g.matchups, "steals": g.steals,
        "subs": len(re.findall(r"^Substitution: ", joined, re.M)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--out", default="/tmp/stress_results.json")
    ap.add_argument("--proxy-park", default=None,
                    help="stand-in park name for clubs with no 1986 park card (stress only)")
    ap.add_argument("--supplemental-so", action="store_true",
                    help="page 11 optional Supplemental Strikeout band (on by default; kept for old commands)")
    ap.add_argument("--no-supplemental-so", action="store_true",
                    help="turn off the page 11 optional Supplemental Strikeout band")
    args = ap.parse_args()
    if args.no_supplemental_so:
        OPTS["supplemental_so"] = False
    global PROXY_PARK
    PROXY_PARK = args.proxy_park
    codes = sorted(ROSTERS)
    jobs = [(h, a, 1000 * s + i) for s in range(1, args.seeds + 1)
            for i, (h, a) in enumerate((h, a) for h in codes for a in codes if h != a)]
    with multiprocessing.Pool() as pool:
        results = pool.map(one, jobs, chunksize=8)
    json.dump(results, open(args.out, "w"))
    fails = [r for r in results if "fail" in r]
    bad = [r for r in results if r.get("problems")]
    print("games", len(results), "failures", len(fails), "games with problems", len(bad))


if __name__ == "__main__":
    main()
