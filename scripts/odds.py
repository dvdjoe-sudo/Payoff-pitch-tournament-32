#!/usr/bin/env python3
"""Monte Carlo series and title odds from Full 26 Index strength.

Display only. The simulation does not edit tournament_results.json.
The draw is seeded so a rebuild writes the same feed/odds.json.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "tournament_results.json"
OUT = ROOT / "feed" / "odds.json"

# A gap of SCALE index points is a 1/(1+e^-1) game win, about 0.73.
SCALE = 80.0
ITERATIONS = 4000
DRAW = 20261025


def win_prob(index_a: float, index_b: float) -> float:
    return 1.0 / (1.0 + math.exp(-(index_a - index_b) / SCALE))


def play_series(rng: random.Random, a: str, b: str, wins: dict, indexes: dict) -> str:
    wa = int((wins or {}).get(a, 0))
    wb = int((wins or {}).get(b, 0))
    pa = win_prob(indexes[a], indexes[b])
    while wa < 4 and wb < 4:
        if rng.random() < pa:
            wa += 1
        else:
            wb += 1
    return a if wa >= 4 else b


def pair(codes: list[str], seeds: dict) -> list[tuple[str, str]]:
    ordered = sorted(codes, key=lambda code: seeds[code])
    count = len(ordered)
    return [(ordered[i], ordered[count - 1 - i]) for i in range(count // 2)]


def round_robin(rng, codes, seeds, indexes):
    winners = []
    losers = []
    for a, b in pair(codes, seeds):
        winner = play_series(rng, a, b, {}, indexes)
        winners.append(winner)
        losers.append(b if winner == a else a)
    return winners, losers


def opening_results(rng, data, indexes):
    winners = []
    losers = []
    for series in sorted((item for item in data["series"] if item["id"].startswith("R1-")), key=lambda item: item["id"]):
        if series["status"] == "complete":
            winners.append(series["winner"])
            losers.append(series["loser"])
            continue
        winner = play_series(rng, series["team_a"], series["team_b"], series.get("wins") or {}, indexes)
        loser = series["team_b"] if winner == series["team_a"] else series["team_a"]
        winners.append(winner)
        losers.append(loser)
    return winners, losers


def champion(rng, data, seeds, indexes) -> str:
    winners, losers = opening_results(rng, data, indexes)
    w2_w, w2_l = round_robin(rng, winners, seeds, indexes)
    l1_w, _l1_l = round_robin(rng, losers, seeds, indexes)
    l2_w, _l2_l = round_robin(rng, l1_w + w2_l, seeds, indexes)
    w3_w, w3_l = round_robin(rng, w2_w, seeds, indexes)
    l3_w, _l3_l = round_robin(rng, l2_w, seeds, indexes)
    l4_w, _l4_l = round_robin(rng, l3_w + w3_l, seeds, indexes)
    w4_w, w4_l = round_robin(rng, w3_w, seeds, indexes)
    l5_w, _l5_l = round_robin(rng, l4_w, seeds, indexes)
    l6_w, _l6_l = round_robin(rng, l5_w + w4_l, seeds, indexes)
    l7_w, _l7_l = round_robin(rng, l6_w, seeds, indexes)
    w5_w, w5_l = round_robin(rng, w4_w, seeds, indexes)
    l8_w, _l8_l = round_robin(rng, l7_w + w5_l, seeds, indexes)
    undefeated = w5_w[0]
    one_loss = l8_w[0]
    final_winner = play_series(rng, undefeated, one_loss, {}, indexes)
    if final_winner == undefeated:
        return undefeated
    return play_series(rng, undefeated, one_loss, {}, indexes)


def series_table(data, indexes) -> dict:
    table = {}
    for series in data["series"]:
        if not series.get("team_a") or not series.get("team_b"):
            continue
        a, b = series["team_a"], series["team_b"]
        if series["status"] == "complete" and series.get("winner"):
            table[series["id"]] = {a: 1.0 if series["winner"] == a else 0.0, b: 1.0 if series["winner"] == b else 0.0}
            continue
        rng = random.Random(DRAW + sum(ord(ch) for ch in series["id"]))
        wins = {a: 0, b: 0}
        for _ in range(ITERATIONS):
            winner = play_series(rng, a, b, series.get("wins") or {}, indexes)
            wins[winner] += 1
        table[series["id"]] = {code: round(wins[code] / ITERATIONS, 4) for code in (a, b)}
    return table


def title_table(data, seeds, indexes) -> dict:
    counts = {code: 0 for code in indexes}
    rng = random.Random(DRAW)
    for _ in range(ITERATIONS):
        counts[champion(rng, data, seeds, indexes)] += 1
    return {code: round(counts[code] / ITERATIONS, 4) for code in sorted(counts, key=lambda code: seeds[code])}


def build(data: dict | None = None) -> dict:
    if data is None:
        data = json.loads(RESULTS.read_text(encoding="utf-8"))
    indexes = {team["code"]: float(team["index"]) for team in data["teams"]}
    seeds = {team["code"]: team["seed"] for team in data["teams"]}
    return {
        "model": "monte-carlo",
        "iterations": ITERATIONS,
        "draw": DRAW,
        "scale": SCALE,
        "series": series_table(data, indexes),
        "title": title_table(data, seeds, indexes),
    }


def text(data: dict | None = None) -> str:
    return json.dumps(build(data), indent=1, sort_keys=True) + "\n"


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(text(), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
