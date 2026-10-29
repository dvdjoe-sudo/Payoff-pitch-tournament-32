#!/usr/bin/env python3
"""Build data/series_r106.json for Series Play (SERIES_PLAY_SPEC.md
section 3.2): the "Play next game" assembly for the R1-06 fixture,
baked from the book (tournament_results.json) plus the fixture file
(data/playable_r106.json) and nothing else.

The generator never imports a set home's governed stack and reads
nothing outside the repo. It is deterministic (sorted keys, fixed
separators, like build_playable_data.py), so the pages workflow's
generated-files check can diff its output.

The completeness verdict and the decision order are section 3.2's,
evaluated in the spec's order at every bake:
  (1) stored numbers not a dense prefix -> next_game null, "gap";
  (2) series complete (a club at 4+ wins, or the book's status is
      "complete") -> next_game null, "complete";
  (3) playable_data_complete false -> next_game null,
      "not-playable-data-complete";
  (4) else assemble the next game.

Run from the pinned pipeline venv:
  ~/workspace/tools/pp-t32-venv/bin/python scripts/build_series_data.py
Optional overrides (the spec's section 4.6 scratch cases run the
generator against copies): --root, --book, --fixture, --out.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.dirname(HERE)


def park_slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def series_file_name(series_id):
    return "series_" + re.sub(r"[^a-z0-9]", "", series_id.lower()) + ".json"


def availability_status(outs):
    """The house outs convention (SERIES_PLAY_SPEC section 3.2,
    assembly item 4): under 6 outs free; 6-8 capped at 3; 9 or
    more unavailable. Role-blind, one game only."""
    if outs >= 9:
        return "unavailable", None
    if outs >= 6:
        return "capped", 3
    return "free", None


def aggregate_appearances(game, club):
    """One appearance per pitcher for a club in a stored game:
    split lines for the same name sum their outs (the input-schema
    aggregation fallback); appearance order is the first line's."""
    apps = {}
    for line in game.get("pitching") or []:
        if line.get("team") != club:
            continue
        name = line["name"]
        if name not in apps:
            apps[name] = {"name": name, "outs": 0,
                          "order": line.get("appearance_order") or 99}
        apps[name]["outs"] += line.get("outs") or 0
        apps[name]["order"] = min(apps[name]["order"],
                                  line.get("appearance_order") or 99)
    return sorted(apps.values(), key=lambda a: (a["order"], a["name"]))


def build(root, book_path, fixture_path):
    notes = []
    book = json.load(open(book_path))
    fixture = None
    if os.path.exists(fixture_path):
        fixture = json.load(open(fixture_path))
    series_id = (fixture or {}).get("fixture", {}).get("id") or "R1-06"
    entry = None
    for s in book.get("series") or []:
        if s.get("id") == series_id:
            entry = s
            break

    fx = (fixture or {}).get("fixture") or {}
    clubs = fx.get("clubs") or {}
    pair = []
    if entry:
        pair = [entry.get("team_a"), entry.get("team_b")]

    # ---- completeness verdict (section 3.2, computed here only)
    complete = True
    reasons = []
    if entry is None:
        complete = False
        reasons.append("no series entry in the book")
    else:
        hbg = entry.get("home_by_game") or {}
        if any(str(n) not in hbg for n in range(1, 8)):
            complete = False
            reasons.append("home_by_game lacks a key in 1..7")
    if fixture is None:
        complete = False
        reasons.append("fixture file missing")
    else:
        for club in pair:
            c = clubs.get(club) or {}
            if not c.get("park"):
                complete = False
                reasons.append(f"{club}: no park named")
            if len((fx.get("lineups") or {}).get(club) or []) != 9:
                complete = False
                reasons.append(f"{club}: lineup is not exactly 9")
            if len((fx.get("benches") or {}).get(club) or []) < 6:
                complete = False
                reasons.append(f"{club}: bench under 6")
            if len((fx.get("pens") or {}).get(club) or []) < 6:
                complete = False
                reasons.append(f"{club}: pen under 6")
            if not ((fx.get("rotations") or {}).get(club) or []):
                complete = False
                reasons.append(f"{club}: rotation empty")
            if club not in (fx.get("closers") or {}):
                complete = False
                reasons.append(f"{club}: no closer entry")
            park = c.get("park")
            if park:
                if park not in (fixture.get("parks") or {}):
                    complete = False
                    reasons.append(f"{club}: park {park!r} has no fixture record")
                face = os.path.join(root, "assets", "parks",
                                    park_slug(park) + ".webp")
                if not os.path.exists(face):
                    complete = False
                    reasons.append(f"{club}: park face missing ({face})")

    out = {
        "series_id": series_id,
        "team_a": entry.get("team_a") if entry else None,
        "team_b": entry.get("team_b") if entry else None,
        "status": entry.get("status") if entry else None,
        "wins": {},
        "stored_games": [],
        "playable_data_complete": complete,
        "blocked_reason": None,
        "next_game": None,
    }
    if entry:
        wins = entry.get("wins") or {}
        out["wins"] = {entry["team_a"]: wins.get(entry["team_a"], 0),
                       entry["team_b"]: wins.get(entry["team_b"], 0)}
        games = [g for g in book.get("games") or []
                 if g.get("series_id") == series_id]
        games.sort(key=lambda g: g.get("game_in_series") or 0)
        out["stored_games"] = [
            {"number": g["game_in_series"], "id": g["id"],
             "away": g["away"], "home": g["home"]} for g in games]

    def finish(blocked):
        out["blocked_reason"] = blocked
        return out, notes

    if entry is None:
        return finish("not-playable-data-complete")

    numbers = [g["number"] for g in out["stored_games"]]
    # (1) dense prefix
    if numbers != list(range(1, len(numbers) + 1)):
        missing = next(n for n in range(1, (max(numbers) if numbers else 1) + 1)
                       if n not in numbers)
        notes.append(f"gap: stored game numbers {numbers} are not a dense "
                     f"prefix; game {missing} is missing")
        return finish("gap")
    # (2) complete
    if (max(out["wins"].values() or [0]) >= 4
            or entry.get("status") == "complete"):
        return finish("complete")
    # (3) completeness
    if not complete:
        notes.append("playable data incomplete: " + "; ".join(reasons))
        return finish("not-playable-data-complete")

    # (4) assemble game N
    n = len(numbers) + 1
    hbg = entry.get("home_by_game") or {}
    home = hbg.get(str(n))
    if home is None:
        raise SystemExit(f"build_series_data: FAIL: no home club scheduled "
                         f"for game {n} of {series_id}")
    away = entry["team_b"] if home == entry["team_a"] else entry["team_a"]
    by_number = {g["game_in_series"]: g for g in
                 (g for g in book.get("games") or []
                  if g.get("series_id") == series_id)}

    availability = {}
    status_of = {}
    for club in pair:
        rows = []
        if n > 1:
            prev = by_number.get(n - 1)
            if prev is not None:
                for app in aggregate_appearances(prev, club):
                    status, cap = availability_status(app["outs"])
                    rows.append({"name": app["name"],
                                 "prev_outs": app["outs"],
                                 "status": status, "cap_outs": cap})
        availability[club] = rows
        status_of[club] = {r["name"]: r["status"] for r in rows}

    def avail(club, name):
        return status_of[club].get(name, "free")

    proposed = {}
    blocked_clubs = []
    for club in pair:
        rotation = list((fx.get("rotations") or {}).get(club) or [])
        # Pointer: the chair following the most recent booked chair
        # starter (scanning booked games newest first); chair 1 when
        # no booked game has a chair starter.
        start_idx = 0
        booked = sorted((g for g in by_number.values()),
                        key=lambda g: g["game_in_series"], reverse=True)
        for g in booked:
            apps = aggregate_appearances(g, club)
            starter = next((a["name"] for a in apps if a["order"] == 1), None)
            if starter in rotation:
                start_idx = (rotation.index(starter) + 1) % len(rotation)
                break
        pick = None
        for step in range(len(rotation)):
            cand = rotation[(start_idx + step) % len(rotation)]
            if avail(club, cand) == "free":
                pick = cand
                break
        proposed[club] = pick
        if pick is None:
            blocked_clubs.append(club)
            notes.append(f"starter blocked: {club} has no free rotation "
                         f"chair for game {n}")

    pens = {}
    for club in pair:
        pens[club] = [name for name in (fx.get("pens") or {}).get(club) or []
                      if avail(club, name) != "unavailable"]

    out["next_game"] = {
        "number": n,
        "id": f"{series_id}-G{n}",
        "home": home,
        "away": away,
        "park": clubs[home]["park"],
        "lineups": {club: (fx.get("lineups") or {}).get(club) or []
                    for club in pair},
        "benches": {club: list((fx.get("benches") or {}).get(club) or [])
                    for club in pair},
        "rotation": {club: list((fx.get("rotations") or {}).get(club) or [])
                     for club in pair},
        "proposed_starters": proposed,
        "starter_blocked": blocked_clubs,
        "pens": pens,
        "availability": availability,
    }
    return finish(None)


def main():
    ap = argparse.ArgumentParser(description="Bake the Series Play series file.")
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--book", default=None)
    ap.add_argument("--fixture", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = args.root
    book_path = args.book or os.path.join(root, "tournament_results.json")
    fixture_path = args.fixture or os.path.join(root, "data", "playable_r106.json")
    fixture = json.load(open(fixture_path)) if os.path.exists(fixture_path) else {}
    series_id = (fixture.get("fixture") or {}).get("id") or "R1-06"
    out_path = args.out or os.path.join(root, "data", series_file_name(series_id))
    data, notes = build(root, book_path, fixture_path)
    for note in notes:
        print("build_series_data: " + note)
    text = json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n"
    with open(out_path, "w") as f:
        f.write(text)
    ng = data["next_game"]
    desc = (f"next game {ng['id']} ({ng['away']} at {ng['home']}, {ng['park']})"
            if ng else f"no next game ({data['blocked_reason']})")
    print(f"build_series_data: wrote {out_path} ({len(text)} bytes); "
          f"playable_data_complete={data['playable_data_complete']}; {desc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
