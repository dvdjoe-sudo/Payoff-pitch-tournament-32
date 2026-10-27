#!/usr/bin/env python3
"""Measure what a DEFENSE result does in the game engine.

Every pitcher table is set to DEFENSE and full games are played
(FAC deck, all tournament clubs, their own parks and fielders). Each
DEFENSE plate appearance is classified by the batter's result:
1B/2B/3B/HR (hit), ROE (reached on an error, not a hit), FC (reached,
no hit, no error), OUT, RARE (defense rare play), REROLL (dropped foul,
at-bat restarts; left out of the denominator). The result is the
DEFENSE event vector the solver uses. Writes defense_vector.json.
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "engines", "sim"))
import game  # noqa: E402

OUT = os.path.join(HERE, "defense_vector.json")


def probe(seeds=2):
    tally = Counter()
    orig_load = game.load_club

    def load_all_defense(code):
        club = orig_load(code)
        for group in ("rotation", "bullpen"):
            for p in club.get(group) or []:
                if p.get("table"):
                    p["table"] = {str(k): "DEFENSE" for k in range(2, 13)}
        return club

    orig_def = game.Game._defense_fac
    state = {"on": False, "seen": False}

    def wrap_def(self, batter, pitcher, reading):
        state["on"], state["seen"] = True, False
        before = self.order_index[self.batting["code"]]
        try:
            orig_def(self, batter, pitcher, reading)
        finally:
            state["on"] = False
        if self.order_index[self.batting["code"]] < before:
            tally["REROLL"] += 1
        elif not state["seen"]:
            tally["RARE"] += 1

    orig_reach, orig_out = game.Game._reach, game.Game._record_out

    def wrap_reach(self, batter, bb, rb, text, hit, error=False, hold_lead=False):
        if state["on"] and not state["seen"]:
            state["seen"] = True
            if hit:
                tally[{1: "1B", 2: "2B", 3: "3B"}.get(bb, "HR")] += 1
            else:
                tally["ROE" if error else "FC"] += 1
        return orig_reach(self, batter, bb, rb, text, hit, error, hold_lead)

    def wrap_out(self, batter, kind, text):
        if state["on"] and not state["seen"]:
            state["seen"] = True
            tally["OUT"] += 1
        return orig_out(self, batter, kind, text)

    game.load_club = load_all_defense
    game.Game._defense_fac, game.Game._reach, game.Game._record_out = wrap_def, wrap_reach, wrap_out
    try:
        codes = sorted(json.load(open(os.path.join(ROOT, "data", "rosters.json"))))
        for seed in range(1, seeds + 1):
            for home in codes:
                for away in codes:
                    if home != away:
                        try:
                            game.play(home, away, seed=seed)
                        except SystemExit:
                            pass
    finally:
        game.load_club = orig_load
        game.Game._defense_fac, game.Game._reach, game.Game._record_out = orig_def, orig_reach, orig_out
    return tally


def main():
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    t = probe(seeds)
    n = sum(v for k, v in t.items() if k != "REROLL")
    vec = {k: round(t.get(k, 0) / n, 5) for k in ("1B", "2B", "3B", "HR", "ROE", "FC", "OUT", "RARE")}
    out = {"method": __doc__.strip().splitlines()[0], "plate_appearances": n, "counts": dict(t), "vector": vec}
    json.dump(out, open(OUT, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
