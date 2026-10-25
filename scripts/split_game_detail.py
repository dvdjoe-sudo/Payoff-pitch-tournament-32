#!/usr/bin/env python3
"""Split play-by-play detail out of tournament_results.json.

Moves each game's ``rolls`` and ``manager_log`` into ``games/<id>.json``,
renames the per-game RNG field ``seed`` to ``rng_seed``, and records a
date where one is known. Adds ``schema_version`` and, on each team,
``bracket`` and ``losses``. Series objects, scores, and stat lines are
copied through unchanged.

Safe to re-run: a file that is already split is left in place, and the
derived team fields are recomputed from ``series_losses``.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "tournament_results.json"
GAMES_DIR = ROOT / "games"

# Series whose games have a known calendar date. The date is not a stat.
DATED_SERIES = {"R1-02": "2026-10-24", "R1-03": "2026-10-24"}
SCHEMA_VERSION = 1


def load() -> dict:
    with RESULTS.open(encoding="utf-8") as handle:
        return json.load(handle)


def dump(data: dict) -> None:
    text = json.dumps(data, indent=1)
    RESULTS.write_text(text + "\n", encoding="utf-8")


def bracket_and_losses(team: dict) -> tuple[str, int]:
    losses = team["series_losses"]
    if team.get("eliminated") or losses >= 2:
        return "eliminated", losses
    if losses == 1:
        return "losers", losses
    return "winners", losses


def apply_team_fields(data: dict) -> None:
    for team in data["teams"]:
        bracket, losses = bracket_and_losses(team)
        team["bracket"] = bracket
        team["losses"] = losses


def already_split(game: dict) -> bool:
    return "detail" in game and "rolls" not in game and "rng_seed" in game and "seed" not in game


def transform_game(game: dict) -> dict:
    """Return the detail object and mutate ``game`` into the summary shape."""
    if already_split(game):
        return {}

    rolls = game.pop("rolls")
    if "manager_log" in game:
        manager_log = game.pop("manager_log")
    else:
        manager_log = None

    summary: dict = {}
    for key, value in game.items():
        if key == "game_in_series":
            summary[key] = value
            summary["date"] = DATED_SERIES.get(game["series_id"])
            continue
        if key == "seed":
            summary["rng_seed"] = value
            continue
        summary[key] = value
    summary["detail"] = f"games/{game['id']}.json"
    game.clear()
    game.update(summary)
    return {
        "id": game["id"],
        "series_id": game["series_id"],
        "game_in_series": game["game_in_series"],
        "rolls": rolls,
        "manager_log": manager_log,
    }


def main() -> None:
    data = load()
    data.pop("schema_version", None)
    data = {"schema_version": SCHEMA_VERSION, **data}
    apply_team_fields(data)

    GAMES_DIR.mkdir(exist_ok=True)
    written = 0
    for game in data["games"]:
        if already_split(game):
            # Date stays null except where a date is known.
            game["date"] = DATED_SERIES.get(game["series_id"])
            continue
        detail = transform_game(game)
        path = ROOT / game["detail"]
        path.write_text(json.dumps(detail, indent=1) + "\n", encoding="utf-8")
        written += 1

    dump(data)
    print(f"schema_version {SCHEMA_VERSION}; detail files written {written}; games {len(data['games'])}")


if __name__ == "__main__":
    main()
