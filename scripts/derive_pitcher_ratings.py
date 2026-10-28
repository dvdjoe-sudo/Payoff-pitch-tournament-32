#!/usr/bin/env python3
"""Derive the missing pitcher-card ratings from real stats.

The rulebook (pages 7-11, 18, 21, 39) defines how Start/Relief stamina,
WP, Hold, DP and Injury are used, not how they are rated. So each rating
is calibrated against the official 1986 card set: every 1986 pitcher card
(historical-cards/reference/pitcher_ratings_1986.json, read as printed)
is matched to that pitcher's 1986 Lahman line, and cutpoints on one stat
per rating are fitted to reproduce the printed labels. Rates are taken
relative to the league in the same season so one cutpoint set works for
any era (the same approach as the catcher-arm re-rate).

    Start      IP per start (relief innings removed at 1.5 per relief game)
    Relief     Short/Long from IP per relief game (pure relievers);
               a pitcher who also started is Long, the 1986 majority
    WP         wild pitches per batter faced vs league -> 30 .. 30-3x
    DP         GIDP per batter faced vs league -> 4 .. 10
    Hold       (SB+CS) per inning vs league -> 3 .. 10 (MLB API, 1974+)
    Injury     batters faced per season -> Prone / Normal / Durable
    Fielding   pitcher (PO+A) per inning and E per inning vs league ->
               range A-F and error 1-5, the 1986 pitcher FIELDING line

Stats come from the card's own franchise peak window (peak_pit.window_years,
franchise stints only; 2026 from the MLB Stats API sidecar). Only empty
ratings are filled; printed set-file values and every 2d6 table are left
alone. Ratings with no usable stat (Hold before 1974, DP with no GIDP)
get the label a league-average pitcher gets, and are flagged. Save
symbols are not derived: the 1986 printed + does not follow a stat rule.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tarfile
import unicodedata
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_peak162 as peak  # noqa: E402

CARDS = os.path.join(ROOT, "data", "cards.json")
ROSTERS = os.path.join(ROOT, "data", "rosters.json")
RESULTS = os.path.join(ROOT, "tournament_results.json")
REF = os.path.join(ROOT, "historical-cards", "reference", "pitcher_ratings_1986.json")
SIDECAR = os.path.join(ROOT, "historical-cards", "sources", "mlb_pitcher_ratings_sidecar.json")
METHOD = os.path.join(ROOT, "engines", "sim", "pitcher_rating_method.json")
REPORT = os.path.join(ROOT, "historical-cards", "accuracy", "pitcher_ratings.json")

# club -> (Lahman franchID, first year, last year, MLB Stats API team id)
CLUB = {
    "ARI": ("ARI", 1998, 2026, 109), "ATL": ("ATL", 1871, 2026, 144), "BAL": ("BAL", 1901, 2026, 110),
    "BOS": ("BOS", 1901, 2026, 111), "CHC": ("CHC", 1871, 2026, 112), "CIN": ("CIN", 1876, 2026, 113),
    "CLE": ("CLE", 1901, 2026, 114), "COL": ("COL", 1993, 2026, 115), "CWS": ("CHW", 1901, 2026, 145),
    "DET": ("DET", 1901, 2026, 116), "HOU": ("HOU", 1962, 2026, 117), "KC": ("KCR", 1969, 2026, 118),
    "LAA": ("ANA", 1961, 2026, 108), "LAD": ("LAD", 1884, 2026, 119), "MIA": ("FLA", 1993, 2026, 146),
    "MIL": ("MIL", 1969, 2026, 158), "MIN": ("MIN", 1901, 2026, 142), "MON": ("WSN", 1969, 2004, 120),
    "NYM": ("NYM", 1962, 2026, 121), "NYY": ("NYY", 1901, 2026, 147), "OAK": ("OAK", 1968, 2026, 133),
    "PHA": ("OAK", 1901, 1954, 133), "PHI": ("PHI", 1883, 2026, 143), "PIT": ("PIT", 1882, 2026, 134),
    "SD": ("SDP", 1969, 2026, 135), "SEA": ("SEA", 1977, 2026, 136), "SF": ("SFG", 1883, 2026, 137),
    "STL": ("STL", 1882, 2026, 138), "TB": ("TBD", 1998, 2026, 139), "TEX": ("TEX", 1961, 2026, 140),
    "TOR": ("TOR", 1977, 2026, 141), "WSH": ("WSN", 2005, 2026, 120),
}
RELIEF_IP_PER_GAME = 1.5  # used only to strip relief innings out of IP per start
PICKOFF = "chart p18, keyed to Hold"


def fold(text):
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower().replace(".", "").strip()


def num(value):
    try:
        if value is None:
            return None
        value = float(value)
        return None if value != value else value
    except (TypeError, ValueError):
        return None


def frame_rows(frame, cols):
    data = {c: list(frame[c]) for c in cols}
    return [dict(zip(cols, vals)) for vals in zip(*(data[c] for c in cols))]


def load():
    with tarfile.open(peak.lahman_path()) as tar:
        pit = peak.load_table(tar, "Pitching")
        fld = peak.load_table(tar, "Fielding")
        teams = peak.load_table(tar, "Teams")
        people = peak.load_table(tar, "People")
    pit = frame_rows(pit, ["playerID", "yearID", "teamID", "G", "GS", "SV", "IPouts", "BFP", "WP", "GIDP"])
    fld = [r for r in frame_rows(fld, ["playerID", "yearID", "teamID", "POS", "PO", "A", "E"]) if r["POS"] == "P"]
    teams = frame_rows(teams, ["yearID", "teamID", "franchID", "name"])
    people = frame_rows(people, ["playerID", "nameFirst", "nameLast"])
    for rows in (pit, fld, teams):
        for r in rows:
            r["yearID"] = int(r["yearID"])
    return pit, fld, teams, people


def league_tables(pit, fld, side):
    lg = defaultdict(lambda: defaultdict(float))
    for r in pit:
        y = r["yearID"]
        outs, bf = num(r["IPouts"]), num(r["BFP"])
        if outs:
            lg[y]["IPouts"] += outs
        if bf:
            lg[y]["BF"] += bf
            if num(r["WP"]) is not None:
                lg[y]["WP"] += num(r["WP"])
                lg[y]["BF_wp"] += bf
            if num(r["GIDP"]) is not None:
                lg[y]["GIDP"] += num(r["GIDP"])
                lg[y]["BF_gidp"] += bf
    for r in fld:
        y = r["yearID"]
        for k in ("PO", "A", "E"):
            lg[y]["F" + k] += num(r[k]) or 0
    for y, t in side["league"].items():
        y = int(y)
        lg[y]["ATT"] = t["SB"] + t["CS"]
        lg[y]["IPouts_api"] = t["IPouts"]
        if y == 2026:  # Lahman stops at 2025
            for k in ("IPouts", "BF", "WP", "GIDP"):
                lg[y][k] = t[k]
            lg[y]["BF_wp"] = lg[y]["BF_gidp"] = t["BF"]
    return lg


def rate(lg, y, key):
    t = lg[y]
    if key == "wp":
        return t["WP"] / t["BF_wp"] if t["BF_wp"] else None
    if key == "dp":
        return t["GIDP"] / t["BF_gidp"] if t["BF_gidp"] else None
    if key == "att":
        return t["ATT"] / t["IPouts_api"] if t.get("IPouts_api") else None
    if key == "rf":
        return (t["FPO"] + t["FA"]) / t["IPouts"] if t["IPouts"] and t["FPO"] + t["FA"] else None
    if key == "e":
        return t["FE"] / t["IPouts"] if t["IPouts"] and t["FPO"] + t["FA"] else None


def window_stats(seasons, lg):
    """seasons: list of dicts with year, G, GS, SV, IPouts, BF, WP, GIDP, SB, CS, PO, A, E."""
    s = defaultdict(float)
    exp = defaultdict(float)
    cov = defaultdict(float)
    for r in seasons:
        y = r["year"]
        for k in ("G", "GS", "SV", "IPouts", "BF"):
            s[k] += r.get(k) or 0
        if r.get("WP") is not None and rate(lg, y, "wp") is not None:
            s["WP"] += r["WP"]; exp["wp"] += r["BF"] * rate(lg, y, "wp"); cov["wp"] += r["BF"]
        if r.get("GIDP") is not None and rate(lg, y, "dp") is not None:
            s["GIDP"] += r["GIDP"]; exp["dp"] += r["BF"] * rate(lg, y, "dp"); cov["dp"] += r["BF"]
        if r.get("SB") is not None and r.get("CS") is not None and rate(lg, y, "att") is not None:
            s["ATT"] += r["SB"] + r["CS"]; exp["att"] += r["IPouts"] * rate(lg, y, "att"); cov["att"] += r["BF"]
        if r.get("PO") is not None and rate(lg, y, "rf") is not None:
            s["RF"] += r["PO"] + r["A"]; s["E"] += r["E"]
            exp["rf"] += r["IPouts"] * rate(lg, y, "rf"); exp["e"] += r["IPouts"] * rate(lg, y, "e"); cov["rf"] += r["BF"]
    out = {"G": s["G"], "GS": s["GS"], "SV": s["SV"], "IPouts": s["IPouts"], "BF": s["BF"], "seasons": len(seasons)}
    bf = s["BF"] or 1
    for key, stat in (("wp", "WP"), ("dp", "GIDP"), ("att", "ATT"), ("rf", "RF"), ("e", "E")):
        out[key] = s[stat] / exp[key] if exp[key] else None
        out[key + "_cov"] = (cov["rf" if key == "e" else key]) / bf
    ip = s["IPouts"] / 3
    relief_g = s["G"] - s["GS"]
    out["ip_per_start"] = (ip - RELIEF_IP_PER_GAME * relief_g) / s["GS"] if s["GS"] else None
    if out["ip_per_start"] is not None and s["GS"] and relief_g == 0:
        out["ip_per_start"] = ip / s["GS"]
    out["ip_per_relief"] = ip / relief_g if relief_g and not s["GS"] else None
    out["bf_per_season"] = s["BF"] / max(1, len(seasons))
    return out


# --- fitting -------------------------------------------------------------
def fit_cuts(points, labels):
    """Monotone cutpoints maximising exact matches. points: [(x, label)],
    labels ordered by increasing x. Returns cuts c[i] = lowest x for labels[i+1]."""
    pts = sorted(points)
    xs = [p[0] for p in pts]
    n, k = len(pts), len(labels)
    idx = {lab: i for i, lab in enumerate(labels)}
    # pref[j][i] = count of label j among first i points
    pref = [[0] * (n + 1) for _ in range(k)]
    for i, (_x, lab) in enumerate(pts):
        for j in range(k):
            pref[j][i + 1] = pref[j][i] + (1 if idx[lab] == j else 0)
    NEG = -1
    best = [[NEG] * (n + 1) for _ in range(k)]
    back = [[0] * (n + 1) for _ in range(k)]
    for i in range(n + 1):
        best[0][i] = pref[0][i]
    for j in range(1, k):
        for i in range(n + 1):
            top, arg = NEG, 0
            for m in range(i + 1):
                if m not in (0, n) and m < n and xs[m] == xs[m - 1]:
                    continue
                v = best[j - 1][m] + pref[j][i] - pref[j][m]
                if v > top:
                    top, arg = v, m
            best[j][i], back[j][i] = top, arg
    cuts, i = [], n
    for j in range(k - 1, 0, -1):
        m = back[j][i]
        if m <= 0:
            cuts.append(xs[0] - 1e-9)
        elif m >= n:
            cuts.append(xs[-1] + 1e-9)
        else:
            cuts.append((xs[m - 1] + xs[m]) / 2)
        i = m
    cuts.reverse()
    for a in range(1, len(cuts)):
        cuts[a] = max(cuts[a], cuts[a - 1])
    return [round(c, 4) for c in cuts], best[k - 1][n]


def classify(x, labels, cuts):
    lab = labels[0]
    for c, l in zip(cuts, labels[1:]):
        if x >= c:
            lab = l
    return lab


def score(points, labels, cuts):
    exact = near = 0
    for x, lab in points:
        got = classify(x, labels, cuts)
        exact += got == lab
        near += abs(labels.index(got) - labels.index(lab)) <= 1
    return {"n": len(points), "exact": exact, "within_one": near,
            "exact_pct": round(100 * exact / len(points), 1), "within_one_pct": round(100 * near / len(points), 1)}


def calibration(pit, fld, teams, people, lg, side):
    ref = json.load(open(REF, encoding="utf-8"))["pitchers"]
    names = {r["playerID"]: (r["nameFirst"], r["nameLast"]) for r in people}
    rows86 = defaultdict(list)
    for r in pit:
        if r["yearID"] == 1986:
            rows86[r["playerID"]].append(r)
    f86 = defaultdict(list)
    for r in fld:
        if r["yearID"] == 1986:
            f86[r["playerID"]].append(r)
    by_last = defaultdict(list)
    for pid in rows86:
        first, last = names.get(pid, ("", ""))
        by_last[fold(last)].append((pid, fold(first)))
    data, skipped = [], []
    for card in ref:
        if card["partial"]:
            continue
        name = re.sub(r" \(.*\)$", "", card["name"])
        parts = name.split()
        cands = [pid for pid, first in by_last.get(fold(parts[-1]), []) if first[:3] == fold(parts[0])[:3]]
        if len(cands) != 1 or len(rows86[cands[0]]) != 1:
            skipped.append(name)
            continue
        pid = cands[0]
        r = rows86[pid][0]
        fr = [x for x in f86[pid] if x["teamID"] == r["teamID"]]
        api = side["cal1986"].get(fold(name))
        season = {"year": 1986, "G": num(r["G"]), "GS": num(r["GS"]), "SV": num(r["SV"]),
                  "IPouts": num(r["IPouts"]), "BF": num(r["BFP"]), "WP": num(r["WP"]), "GIDP": num(r["GIDP"]),
                  "SB": api["SB"] if api and api["IPouts"] == num(r["IPouts"]) else None,
                  "CS": api["CS"] if api and api["IPouts"] == num(r["IPouts"]) else None}
        if fr:
            season.update(PO=sum(num(x["PO"]) or 0 for x in fr), A=sum(num(x["A"]) or 0 for x in fr),
                          E=sum(num(x["E"]) or 0 for x in fr))
        if not season["BF"]:
            continue
        data.append((card, window_stats([season], lg), season))
    return data, skipped


def printed(card):
    p = card["printed"]
    fat = p.get("fatigue", "")
    m = re.match(r"(\d)", fat)
    wp = p.get("wp", "")
    width = 0 if not wp else int(wp.split("-")[-1]) - 29
    rng, err = (p.get("fielding", "") + " ").split()[:2] if len(p.get("fielding", "").split()) == 2 else (None, None)
    return {"start": int(m.group(1)) if m else None,
            "relief": "Short" if "Short" in fat else "Long" if "Long" in fat else None,
            "wp": width, "dp": int(p["dp"]) if p.get("dp", "").isdigit() else None,
            "hold": int(p["hold"]) if p.get("hold", "").isdigit() else None,
            "inj": p.get("injury") or None, "range": rng, "e": int(err) if err else None}


def fit_all(data):
    method = {}
    pts = defaultdict(list)
    for card, st, season in data:
        lab = printed(card)
        if lab["start"] and st["ip_per_start"] is not None and season["GS"] >= 3:
            pts["start"].append((st["ip_per_start"], lab["start"]))
        if lab["relief"] and st["ip_per_relief"] is not None and season["G"] >= 5:
            pts["relief"].append((st["ip_per_relief"], lab["relief"]))
        if season["BF"] >= 100:
            pts["wp"].append((st["wp"], min(lab["wp"], 6)))
            if st["dp"] is not None and lab["dp"]:
                pts["dp"].append((st["dp"], lab["dp"]))
            if st["att"] is not None and lab["hold"]:
                pts["hold"].append((st["att"], lab["hold"]))
            if st["rf"] is not None and lab["range"]:
                pts["range"].append((st["rf"], lab["range"]))
                pts["e"].append((st["e"], lab["e"]))
        if lab["inj"]:
            pts["inj"].append((st["bf_per_season"], lab["inj"]))
    order = {
        "start": [1, 2, 3, 4, 5, 6, 7, 8], "relief": ["Short", "Long"], "wp": [0, 1, 2, 3, 4, 5, 6],
        "dp": [4, 5, 6, 7, 8, 9, 10], "hold": [3, 4, 5, 6, 7, 8, 9, 10], "range": ["F", "D", "C", "B", "A"],
        "e": [5, 4, 3, 2, 1], "inj": ["Prone", "Normal", "Durable"],
    }
    for key, labels in order.items():
        cuts, _ = fit_cuts(pts[key], labels)
        method[key] = {"labels": labels, "cuts": cuts, "fit_1986": score(pts[key], labels, cuts)}
    # The rulebook allows Start 1-9; 1986 prints nothing above 8. Start 9 is one
    # inning past the fitted 8 cut, the same one-inning spacing the 7 and 8 cuts show.
    s = method["start"]
    s["labels"].append(9)
    s["cuts"].append(round(s["cuts"][-1] + (s["cuts"][-1] - s["cuts"][-2]), 4))
    s["note"] = "9 is extrapolated: one cut-spacing above the fitted 8 cut (rulebook p10 allows 1-9)."
    w = method["wp"]
    w["note"] = ("Label is the range width: 0 = no WP rating (wild pitches only from Rare Play), "
                 "1 = 30, 2 = 30-31, ... 1986 widths above 6 are rare (11 cards) and are pooled into 6; "
                 "beyond the 6 cut one more number is added per further cut-spacing.")
    for key in ("dp", "hold", "range", "e"):
        method[key]["default"] = classify(1.0, method[key]["labels"], method[key]["cuts"])
        method[key]["default_note"] = "League-average value (relative rate 1.0), used only when the stat is missing."
    method["relief"]["mixed_rule"] = ("A pitcher with starts and relief games is Long: the 1986 set prints "
                                      "X/Long on 145 of 176 such pitchers.")
    return method


def wp_label(x, m):
    labels, cuts = m["labels"], m["cuts"]
    width = classify(x, labels, cuts)
    if width == 6:
        step = cuts[-1] - cuts[-2]
        width = 6 + int((x - cuts[-1]) // step) if step > 0 else 6
    return None if width == 0 else ("30" if width == 1 else "30-%d" % (29 + width))


def window_seasons(pid, club, years, pit, fld, teams, side):
    franch, lo, hi, api_team = CLUB[club]
    team_ids = {(t["yearID"], t["teamID"]) for t in teams if t["franchID"] == franch and lo <= t["yearID"] <= hi}
    api = (side["players"].get(pid) or {}).get("rows", [])
    seasons, notes = [], []
    for y in years:
        if y >= 2026:
            prow = [r for r in api if r["kind"] == "pit" and r["season"] == y and r["team_id"] == api_team]
            frow = [r for r in api if r["kind"] == "fld" and r["season"] == y and r["team_id"] == api_team]
            if not prow:
                notes.append("%s: no MLB API franchise line" % y)
                continue
            p = prow[0]
            s = {"year": y, "G": p["G"], "GS": p["GS"], "SV": p["SV"], "IPouts": p["IPouts"], "BF": p["BF"],
                 "WP": p["WP"], "GIDP": p["GIDP"], "SB": p["SB"], "CS": p["CS"]}
            if frow:
                s.update(PO=frow[0]["PO"], A=frow[0]["A"], E=frow[0]["E"])
            seasons.append(s)
            continue
        rows = [r for r in pit if r["playerID"] == pid and r["yearID"] == y and (y, r["teamID"]) in team_ids]
        if not rows:
            notes.append("%s: no Lahman franchise line" % y)
            continue
        s = {"year": y}
        for k, src in (("G", "G"), ("GS", "GS"), ("SV", "SV"), ("IPouts", "IPouts"), ("BF", "BFP"), ("WP", "WP"), ("GIDP", "GIDP")):
            vals = [num(r[src]) for r in rows]
            s[k] = None if any(v is None for v in vals) else sum(vals)
        tids = {r["teamID"] for r in rows}
        fr = [r for r in fld if r["playerID"] == pid and r["yearID"] == y and r["teamID"] in tids]
        if fr:
            s.update(PO=sum(num(r["PO"]) or 0 for r in fr), A=sum(num(r["A"]) or 0 for r in fr), E=sum(num(r["E"]) or 0 for r in fr))
        if y >= 1974:
            ap = [r for r in api if r["kind"] == "pit" and r["season"] == y and r["team_id"] == api_team]
            if len(ap) == 1 and ap[0]["IPouts"] == s["IPouts"] and ap[0]["SB"] is not None:
                s["SB"], s["CS"] = ap[0]["SB"], ap[0]["CS"]
            else:
                notes.append("%s: MLB API SB/CS split not matched to the Lahman franchise line" % y)
        seasons.append(s)
    return seasons, notes


def main():
    before = open(RESULTS, "rb").read()
    side = json.load(open(SIDECAR, encoding="utf-8"))
    pit, fld, teams, people = load()
    lg = league_tables(pit, fld, side)
    data, skipped = calibration(pit, fld, teams, people, lg, side)
    method = fit_all(data)
    method["calibration"] = {"cards_1986": len(json.load(open(REF))["pitchers"]), "matched_full_season": len(data),
                             "skipped_unmatched": skipped,
                             "source": "1986 Payoff Pitch season PDF (printed labels) vs Lahman 1986 + MLB Stats API 1986 SB/CS"}
    cards = json.load(open(CARDS, encoding="utf-8"))
    rosters = json.load(open(ROSTERS, encoding="utf-8"))
    report, counts = [], Counter()
    targets = []
    for club, team in rosters.items():
        for row in team["players"]:
            if row["group"] in ("rotation", "bullpen"):
                targets.append((club, row))
    # Cards outlive roster spots: a man dropped when a club went to a
    # six-man bench keeps his card in cards.json (build_cards never
    # deletes one), but the roster-driven loop above never visits him
    # again, so a card built with empty ratings (the empty-team batch
    # builder leaves stamina and the addenda empty on purpose) would
    # stay empty forever. Visit any pitcher card no roster row covers
    # whose stamina is still completely empty, on its own peak window.
    covered = {"%s|%s" % (club, row["id"]) for club, row in targets}
    for key in sorted(cards):
        if key in covered:
            continue
        cp0 = cards[key].get("card_pit")
        if not cp0:
            continue
        stam0 = cp0.get("stamina") or {}
        if stam0.get("start") is None and stam0.get("relief") is None:
            club, pid = key.split("|", 1)
            targets.append((club, {"id": pid, "group": "bullpen"}))
    for club, row in targets:
        key = "%s|%s" % (club, row["id"])
        card = cards[key]
        cp = card["card_pit"]
        add = cp.setdefault("addendum", {})
        stam = cp.setdefault("stamina", {"start": None, "relief": None})
        years = (card.get("peak_pit") or {}).get("window_years") or []
        seasons, notes = window_seasons(row["id"], club, years, pit, fld, teams, side)
        st = window_stats(seasons, lg)
        peak_outs = round(float((card.get("peak_pit") or {}).get("ip") or 0) * 3)
        flags = list(notes)
        if abs(st["IPouts"] - peak_outs) > 1:
            flags.append("Window IP %s outs does not match the card peak line %s outs." % (int(st["IPouts"]), peak_outs))
        filled = {}
        needs_stamina = stam.get("start") is None and stam.get("relief") is None
        if needs_stamina:
            if st["GS"]:
                stam["start"] = classify(st["ip_per_start"], method["start"]["labels"], method["start"]["cuts"])
                filled["start"] = stam["start"]
            if st["G"] > st["GS"]:
                if st["GS"]:
                    stam["relief"] = "Long"
                else:
                    stam["relief"] = classify(st["ip_per_relief"], method["relief"]["labels"], method["relief"]["cuts"])
                filled["relief"] = stam["relief"]
            if row["group"] == "rotation" and stam.get("start") is None:
                flags.append("Rotation spot but no franchise start in the window; no Start stamina.")
            if row["group"] == "bullpen" and stam.get("relief") is None:
                flags.append("Bullpen spot but every window game was a start; Relief is not rated.")
        if add.get("wp") in (None, ""):
            add["wp"] = wp_label(st["wp"], method["wp"]) if st["wp"] is not None else None
            filled["wp"] = add["wp"]
            if add["wp"] is None:
                flags.append("WP rate is below the 30 cut: no WP rating (page 10: Rare Play wild pitches only).")
        for key2, stat, mk in (("dp", "dp", "dp"), ("hold", "att", "hold")):
            if add.get(key2) is None:
                if st[stat] is not None and st[stat + "_cov"] >= 0.5:
                    add[key2] = classify(st[stat], method[mk]["labels"], method[mk]["cuts"])
                    if st[stat + "_cov"] < 0.999:
                        flags.append("%s uses %d%% of window batters faced (other seasons have no data)." % (key2.upper(), round(100 * st[stat + "_cov"])))
                else:
                    add[key2] = method[mk]["default"]
                    flags.append("%s defaulted to league-average %s: %s." % (
                        key2.upper(), add[key2],
                        "no SB/CS-against data before 1974" if key2 == "hold" else "no GIDP data for the window"))
                filled[key2] = add[key2]
        if add.get("pickoff") is None:
            add["pickoff"] = PICKOFF
        if add.get("inj") is None:
            add["inj"] = classify(st["bf_per_season"], method["inj"]["labels"], method["inj"]["cuts"])
            filled["inj"] = add["inj"]
        if not cp.get("fielding"):
            if st["rf"] is not None and st["rf_cov"] >= 0.5:
                rng = classify(st["rf"], method["range"]["labels"], method["range"]["cuts"])
                err = classify(st["e"], method["e"]["labels"], method["e"]["cuts"])
                if st["rf_cov"] < 0.999:
                    flags.append("Fielding uses %d%% of window batters faced." % round(100 * st["rf_cov"]))
            else:
                rng, err = method["range"]["default"], method["e"]["default"]
                flags.append("Fielding defaulted to league-average %s %s: no fielding line." % (rng, err))
            cp["fielding"] = [{"pos": "P", "range": rng, "e": err}]
            filled["fielding"] = "%s %s" % (rng, err)
        if filled:
            counts.update(filled.keys())
            report.append({"key": key, "name": card["name"], "group": row["group"], "window_years": years,
                           "filled": filled, "basis": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in st.items()},
                           "flags": flags})
    json.dump(method, open(METHOD, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open(METHOD, "a").write("\n")
    with open(REPORT, "w", encoding="utf-8") as handle:
        json.dump({"summary": {"cards_changed": len(report), "fields_filled": dict(counts),
                               "flagged": sum(1 for r in report if r["flags"])}, "players": report},
                  handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    with open(CARDS, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(cards, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    if open(RESULTS, "rb").read() != before:
        raise SystemExit("tournament_results.json changed")
    for k in ("start", "relief", "wp", "dp", "hold", "inj", "range", "e"):
        print(k, method[k]["cuts"], method[k]["fit_1986"])
    print("changed", len(report), dict(counts))


if __name__ == "__main__":
    main()
