#!/usr/bin/env python3
"""Replace the engine 'Average' fielding default on hitter cards with real ratings.

Cards built from franchise windows got range C / error 4 with the label
"Average" (build_missing_hitters.py, build_empty_team_cards.py), which is
not a rating. This derives range and error for the card's position from
real fielding stats over the card's own franchise window, calibrated to
the printed 1986 cards the same way as pitcher fielding:

    range  (PO+A) per inning at the position, relative to the league
           at that position in the same season  -> F D C B A
           (per game, with its own fitted cuts, when Lahman lacks innings)
    error  E per chance (PO+A+E) at the position, relative to the league
           -> 5 (fewest errors) .. 1 (most); the park error chart reads
           5 as the smallest error band

Cutpoints are fitted per position on every printed 1986 hitter fielding
row matched to that player's 1986 Lahman line (LF/CF/RF from
FieldingOFsplit). Only cards whose fielding is still the default
(label Average, range C, error 4) change, and only range, error and the
label. Arms, rosters, 2d6 and result tables, and played results stay.
Window seasons are franchise-only; 2026 comes from the MLB Stats API.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tarfile
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_peak162 as peak  # noqa: E402
from derive_pitcher_ratings import CLUB, fit_cuts, classify, score, fold, num  # noqa: E402

CARDS = os.path.join(ROOT, "data", "cards.json")
ROSTERS = os.path.join(ROOT, "data", "rosters.json")
RESULTS = os.path.join(ROOT, "tournament_results.json")
REF = os.path.join(ROOT, "historical-cards", "reference", "cards_1986.json")
API2026 = os.path.join(ROOT, "historical-cards", "sources", "mlb_hitter_fielding_2026.json")
METHOD = os.path.join(ROOT, "engines", "sim", "hitter_fielding_method.json")
REPORT = os.path.join(ROOT, "historical-cards", "accuracy", "hitter_fielding.json")

POSITIONS = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"]
RANGE = ["F", "D", "C", "B", "A"]
ERROR = [5, 4, 3, 2, 1]
THIN_GAMES = 50
MIN_GAMES = 20
OFS_IDS: set = set()
FIT_MIN_GAMES = 10
LABEL = "Derived"


def rows(frame, cols):
    data = {c: list(frame[c]) for c in cols}
    return [dict(zip(cols, v)) for v in zip(*(data[c] for c in cols))]


def load():
    with tarfile.open(peak.lahman_path()) as tar:
        fld = peak.load_table(tar, "Fielding")
        ofs = peak.load_table(tar, "FieldingOFsplit")
        teams = peak.load_table(tar, "Teams")
        people = peak.load_table(tar, "People")
    cols = ["playerID", "yearID", "teamID", "POS", "G", "InnOuts", "PO", "A", "E"]
    fld, ofs = rows(fld, cols), rows(ofs, cols)
    teams = rows(teams, ["yearID", "teamID", "franchID"])
    people = rows(people, ["playerID", "nameFirst", "nameLast"])
    for group in (fld, ofs, teams):
        for r in group:
            r["yearID"] = int(r["yearID"])
            for k in ("G", "InnOuts", "PO", "A", "E"):
                if k in r:
                    r[k] = num(r[k]) or 0
    return fld, ofs, teams, people


def add(total, r):
    total["G"] += r["G"]; total["I"] += r.get("InnOuts") or 0
    total["CH"] += r["PO"] + r["A"]; total["E"] += r["E"]; total["TC"] += r["PO"] + r["A"] + r["E"]


def league(fld, ofs, api):
    lg = defaultdict(Counter)
    for r in fld:
        if r["POS"] in ("C", "1B", "2B", "3B", "SS", "OF"):
            t = lg[(r["yearID"], r["POS"])]
            add(lg[(r["yearID"], r["POS"])], r)
    for r in ofs:
        add(lg[(r["yearID"], r["POS"])], r)
    for pos, t in api["league"].items():
        for p in ([pos, "OF"] if pos in ("LF", "CF", "RF") else [pos]):
            row = lg[(2026, p)]
            add(row, t)
    return lg


def rel(seasons, lg, force_game=False):
    """seasons: [(year, pos, G, InnOuts, PO, A, E)].

    Returns range (PO+A per inning vs league when every season has innings,
    else per game, with which basis), error (E per chance vs league), games."""
    per_inn = not force_game and all(inn for (_y, _p, g, inn, *_r) in seasons if g)
    ch = e = exp_ch = exp_e = games = 0.0
    for y, pos, g, inn, po, a, err in seasons:
        t = lg.get((y, pos))
        if not t or not t["G"] or not g:
            continue
        den, lden = (inn, t["I"]) if per_inn else (g, t["G"])
        if not lden:
            continue
        ch += po + a; e += err; games += g
        exp_ch += den * t["CH"] / lden
        exp_e += (po + a + err) * (t["E"] / t["TC"] if t["TC"] else 0)
    if not games or not exp_ch:
        return None, None, games, None
    return ch / exp_ch, (e / exp_e if exp_e else 0.0), games, ("inning" if per_inn else "game")


def calibrate(fld, ofs, people, lg):
    ref = json.load(open(REF, encoding="utf-8"))["players"]
    names = {r["playerID"]: (fold(r["nameFirst"]), fold(r["nameLast"])) for r in people}
    by86 = defaultdict(list)
    for r in fld + ofs:
        if r["yearID"] == 1986:
            by86[r["playerID"]].append(r)
    by_last = defaultdict(set)
    for pid in by86:
        by_last[names.get(pid, ("", ""))[1]].add(pid)
    pts = defaultdict(lambda: {"range": [], "e": [], "range_game": []})
    skipped = []
    for card in ref:
        if card.get("pitcher") or card.get("partial") or not card.get("positions"):
            continue
        parts = re.sub(r" \(.*\)$", "", card["name"]).replace(" Jr.", "").split()
        cands = [p for p in by_last.get(fold(parts[-1]), ()) if names[p][0][:3] == fold(parts[0])[:3]]
        if len(cands) != 1:
            skipped.append(card["name"])
            continue
        mine = by86[cands[0]]
        for row in card["positions"]:
            pos = row["pos"]
            if pos not in POSITIONS or row["range"] is None or row["e"] is None:
                continue
            got = [r for r in mine if r["POS"] == pos]
            seasons = [(1986, pos, r["G"], r["InnOuts"], r["PO"], r["A"], r["E"]) for r in got]
            r_rel, e_rel, games, _basis = rel(seasons, lg)
            g_rel = rel(seasons, lg, force_game=True)[0]
            if r_rel is None or games < FIT_MIN_GAMES:
                continue
            pts[pos]["range"].append((r_rel, row["range"]))
            pts[pos]["e"].append((e_rel, row["e"]))
            pts[pos]["range_game"].append((g_rel, row["range"]))
    method = {"positions": {}, "skipped_unmatched_1986": skipped}
    for pos in POSITIONS:
        out = {}
        for key, labels in (("range", RANGE), ("range_game", RANGE), ("e", ERROR)):
            cuts, _ = fit_cuts(pts[pos][key], labels)
            out[key] = {"labels": labels, "cuts": cuts, "fit_1986": score(pts[pos][key], labels, cuts)}
        method["positions"][pos] = out
    # OF (no split) uses the three outfield cutpoints pooled.
    pooled = {k: [p for pos in ("LF", "CF", "RF") for p in pts[pos][k]] for k in ("range", "range_game", "e")}
    out = {}
    for key, labels in (("range", RANGE), ("range_game", RANGE), ("e", ERROR)):
        cuts, _ = fit_cuts(pooled[key], labels)
        out[key] = {"labels": labels, "cuts": cuts, "fit_1986": score(pooled[key], labels, cuts)}
    method["positions"]["OF"] = out
    return method


def window(pid, club, years, pos, fld, ofs, teams, api):
    franch, lo, hi, api_team = CLUB[club]
    tids = {(t["yearID"], t["teamID"]) for t in teams if t["franchID"] == franch and lo <= t["yearID"] <= hi}
    mine = [r for r in fld + ofs if r["playerID"] == pid and r["yearID"] in years and (r["yearID"], r["teamID"]) in tids]
    arow = [r for r in (api["players"].get(pid) or {}).get("rows", []) if r["team_id"] == api_team]
    def seasons_at(p):
        out = []
        for y in years:
            if y >= 2026:
                for r in arow:
                    if r["pos"] == p or (p == "OF" and r["pos"] in ("LF", "CF", "RF")):
                        out.append((2026, p, r["G"], r["InnOuts"], r["PO"], r["A"], r["E"]))
                continue
            src = [r for r in mine if r["yearID"] == y and r["POS"] == p and (id(r) in OFS_IDS) == (p in ("LF", "CF", "RF"))]
            for r in src:
                out.append((y, p, r["G"], r["InnOuts"], r["PO"], r["A"], r["E"]))
        return out
    return seasons_at, mine, arow


def main():
    before = open(RESULTS, "rb").read()
    fld, ofs, teams, people = load()
    ofs_ids = {id(r) for r in ofs}
    OFS_IDS.update(ofs_ids)
    api = json.load(open(API2026, encoding="utf-8"))
    lg = league(fld, ofs, api)
    method = calibrate(fld, ofs, people, lg)
    method["source"] = ("1986 Payoff Pitch season PDF hitter fielding rows (as parsed in cards_1986.json) vs "
                        "Lahman 1986 Fielding / FieldingOFsplit; a row is fitted when the player had at least %d games there."
                        % FIT_MIN_GAMES)
    method["thin_games"] = THIN_GAMES
    method["min_games"] = MIN_GAMES
    cards = json.load(open(CARDS, encoding="utf-8"))
    rosters = json.load(open(ROSTERS, encoding="utf-8"))
    report, seen = [], set()
    for club, team in rosters.items():
        for row in team["players"]:
            key = "%s|%s" % (club, row["id"])
            if key in seen:
                continue
            seen.add(key)
            bat = cards[key].get("card_bat") or {}
            pos_rows = bat.get("positions") or []
            if bat.get("fielding") != "Average" or not pos_rows or not all(
                    r.get("range") == "C" and r.get("e") == 4 for r in pos_rows):
                continue
            years = (cards[key].get("peak_bat") or {}).get("window_years") or []
            flags = []
            for prow in pos_rows:
                card_pos = prow["pos"]
                seasons_at, mine, arow = window(row["id"], club, years, card_pos, fld, ofs, teams, api)
                rate_pos = card_pos
                if card_pos not in POSITIONS + ["OF"]:
                    games = Counter()
                    for r in mine:
                        if r["POS"] in ("C", "1B", "2B", "3B", "SS", "OF") and id(r) not in ofs_ids:
                            games[r["POS"]] += r["G"]
                    for r in arow:
                        if r["pos"] in ("C", "1B", "2B", "3B", "SS"):
                            games[r["pos"]] += r["G"]
                        elif r["pos"] in ("LF", "CF", "RF"):
                            games["OF"] += r["G"]
                    if not games:
                        flags.append("Card position %s and no fielding games in the window; default kept (any player may DH)." % card_pos)
                        continue
                    rate_pos = games.most_common(1)[0][0]
                    flags.append("Card position %s: rated at %s, his most-played position in the window (%d games)."
                                 % (card_pos, rate_pos, games[rate_pos]))
                seasons = seasons_at(rate_pos)
                if rate_pos in ("LF", "CF", "RF") and not seasons:
                    seasons = [(y, "OF", g, inn, po, a, e) for (y, _p, g, inn, po, a, e) in seasons_at("OF")]
                    if seasons:
                        flags.append("No %s split for the window (FieldingOFsplit starts 1954 and is incomplete); rated on all OF games." % rate_pos)
                        rate_pos_fit = "OF"
                    else:
                        rate_pos_fit = rate_pos
                else:
                    rate_pos_fit = rate_pos
                r_rel, e_rel, games, basis = rel(seasons, lg)
                if r_rel is None:
                    flags.append("No %s fielding games in the franchise window; default kept." % rate_pos)
                    continue
                if games < MIN_GAMES:
                    flags.append("Only %d games at %s in the franchise window (under %d); default kept." % (games, rate_pos, MIN_GAMES))
                    continue
                m = method["positions"][rate_pos_fit]
                new_range = classify(r_rel, RANGE, m["range" if basis == "inning" else "range_game"]["cuts"])
                if basis == "game":
                    flags.append("Range per game: Lahman has no innings at the position for some window season (mostly 1910s-1950s).")
                new_e = classify(e_rel, ERROR, m["e"]["cuts"])
                if games < THIN_GAMES:
                    flags.append("Thin data: %d games at %s in the window." % (games, rate_pos))
                if years and min(years) < 1920:
                    flags.append("Window starts %d: dead-ball era chance and error rates, rated against that league." % min(years))
                report.append({"key": key, "name": row["name"], "pos": card_pos, "rated_at": rate_pos_fit,
                               "window_years": years, "games": int(games),
                               "range_basis": basis, "range_rel": round(r_rel, 3), "error_rel": round(e_rel, 3),
                               "old": "C 4", "new": "%s %d" % (new_range, new_e), "flags": flags})
                prow["range"], prow["e"] = new_range, new_e
            if any(r["key"] == key for r in report):
                bat["fielding"] = LABEL
                bat["fielding_method"] = "derived: engines/sim/hitter_fielding_method.json"
            elif flags:
                report.append({"key": key, "name": row["name"], "pos": pos_rows[0]["pos"], "new": None,
                               "window_years": years, "flags": flags})
    json.dump(method, open(METHOD, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open(METHOD, "a").write("\n")
    changed = [r for r in report if r.get("new")]
    summary = {"cards_changed": len({r["key"] for r in changed}), "position_rows_changed": len(changed),
               "unchanged_default": [r["key"] for r in report if not r.get("new")],
               "flagged": sum(1 for r in report if r["flags"]),
               "new_values": dict(Counter(r["new"] for r in changed))}
    with open(REPORT, "w", encoding="utf-8") as handle:
        json.dump({"summary": summary, "players": report}, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    with open(CARDS, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(cards, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    if open(RESULTS, "rb").read() != before:
        raise SystemExit("tournament_results.json changed")
    for pos, m in method["positions"].items():
        print(pos, "range", m["range"]["cuts"], m["range"]["fit_1986"], "| e", m["e"]["cuts"], m["e"]["fit_1986"])
    print(json.dumps(summary)[:1500])


if __name__ == "__main__":
    main()
