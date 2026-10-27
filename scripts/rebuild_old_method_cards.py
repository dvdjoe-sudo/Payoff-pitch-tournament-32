#!/usr/bin/env python3
"""Refit the 252 old-method roster cards with the PR #40 solver.

These are the active hitters and pitchers on the 18 converted clubs
whose windows did not change, so the 215-card rebuild left their dice
alone. Windows, peak lines, fielding, stamina, and played games stay.
Pitcher charts use the page-39 percentile shift. Hitter dice are fit
with 1B/2B/3B in the objective and the rulebook defense model.

The 215, the missing hitters, and Elmer Valo's placeholder are not
touched.
"""
from __future__ import annotations

import json
import os
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "engines", "hitter-v0.5"))
sys.path.insert(0, os.path.join(ROOT, "engines", "pitcher-v0.2.3"))

import hitter_solver as hs  # noqa: E402
import rebuild_window_cards as base  # noqa: E402
from calibration import full_pipeline  # noqa: E402
from pitcher_solver import evaluate_vs_hitters  # noqa: E402
from printed_shift import vectors_for_bump  # noqa: E402

CARDS = os.path.join(ROOT, "data", "cards.json")
ROSTERS = os.path.join(ROOT, "data", "rosters.json")
REPORT = os.path.join(ROOT, "historical-cards", "accuracy", "rebuild_252.json")

AVG_FLAG = 0.010
SLG_FLAG = 0.020
OBP_FLAG = 0.010
EVENT_FLAG = 0.008
WORSE_FLAG = 0.005
PITCH_RATE_FLAG = {"so_bf": 0.010, "bb_bf": 0.010, "hr_bf": 0.005, "h_bf": 0.020}


def _dump(cards):
    return json.dumps(cards, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def _roster_sides():
    rosters = json.loads(open(ROSTERS).read())
    hitters = []
    pitchers = []
    for code in sorted(rosters):
        for player in rosters[code]["players"]:
            key = "%s|%s" % (code, player["id"])
            slot = {"key": key, "team": code, "name": player["name"], "id": player["id"]}
            if player["kind"] == "hitter":
                hitters.append(slot)
            else:
                pitchers.append(slot)
    return hitters, pitchers


def _old_method(cards):
    wiped = base._git_cards(base.WIPED)
    restored = base._git_cards(base.RESTORED)
    bat_215, pit_215 = base._window_keys(wiped, restored)
    bat_215 = set(bat_215)
    pit_215 = set(pit_215)
    hitters, pitchers = _roster_sides()
    old_bat = []
    old_pit = []
    for slot in hitters:
        card = cards.get(slot["key"]) or {}
        if slot["key"] in bat_215:
            continue
        if (card.get("card_bat") or {}).get("sections"):
            old_bat.append(slot)
    for slot in pitchers:
        card = cards.get(slot["key"]) or {}
        if slot["key"] in pit_215:
            continue
        if (card.get("card_pit") or {}).get("table_2d6"):
            old_pit.append(slot)
    return old_bat, old_pit


def _round(value):
    return None if value is None else round(value, 4)


def _pack(rates, keys):
    return {key: _round(rates[key]) for key in keys}


def _gap(left, right, keys):
    return {key: _round(left[key] - right[key]) for key in keys}


def _hitter_lines(peak):
    ab = float(peak["AB"])
    pa = float(peak["PA"])
    h = float(peak["H"])
    bb = float(peak.get("BB") or 0)
    ibb = float(peak.get("IBB") or 0)
    hbp = float(peak.get("HBP") or 0)
    hr = float(peak.get("HR") or 0)
    doubles = float(peak.get("2B") or 0)
    triples = float(peak.get("3B") or 0)
    so = float(peak.get("SO") or 0)
    singles = h - doubles - triples - hr
    tb = h + doubles + 2 * triples + 3 * hr
    ubb = bb - ibb
    real = {
        "avg": h / ab,
        "obp": (h + bb + hbp) / pa,
        "slg": tb / ab,
        "1bp": singles / pa,
        "2bp": doubles / pa,
        "3bp": triples / pa,
        "hrp": hr / pa,
        "bbp": bb / pa,
        "sop": so / pa,
    }
    target = dict(real)
    target["obp"] = (h + ubb + hbp) / pa
    target["bbp"] = ubb / pa
    return real, target, int(ibb)


def _hitter_expected(card):
    bat = card["card_bat"]
    exp = hs.expected(bat["sections"], bat.get("bats") or "R", run=bat.get("run"))
    keys = ("avg", "obp", "slg", "1bp", "2bp", "3bp", "hrp", "bbp", "sop")
    return {key: exp[key] for key in keys}


def _hitter_flags(real, target, before, after):
    flags = []
    checks = (
        ("avg", real, AVG_FLAG),
        ("slg", real, SLG_FLAG),
        ("obp", target, OBP_FLAG),
        ("1bp", real, EVENT_FLAG),
        ("2bp", real, EVENT_FLAG),
        ("3bp", real, EVENT_FLAG),
        ("hrp", real, EVENT_FLAG),
        ("sop", real, EVENT_FLAG),
        ("bbp", target, EVENT_FLAG),
    )
    for key, baseline, limit in checks:
        gap = after[key] - baseline[key]
        if abs(gap) > limit:
            flags.append("%s %+.4f" % (key, gap))
    for key in ("avg", "slg"):
        if abs(after[key] - real[key]) > abs(before[key] - real[key]) + WORSE_FLAG:
            flags.append("%s worse than the previous dice" % key)
    return flags


def _pitcher_raw(peak):
    bf = float(peak["bf"])
    return {
        "h_bf": float(peak.get("h") or 0) / bf,
        "bb_bf": float(peak.get("bb") or 0) / bf,
        "so_bf": float(peak.get("so") or 0) / bf,
        "hr_bf": float(peak.get("hr") or 0) / bf,
        "hbp_bf": float(peak.get("hbp") or 0) / bf,
    }


def _bump(modifier):
    return {"NONE": 0, "+10": 10, "+20": 20}.get(modifier or "NONE", 0)


_VECTORS = {}


def _vectors(hand, modifier):
    key = (hand, modifier or "NONE")
    if key not in _VECTORS:
        _VECTORS[key] = vectors_for_bump(hand, _bump(key[1]))
    return _VECTORS[key]


def _pitcher_played(card):
    """Rates the current rulebook engine reads off the printed chart."""
    pit = card["card_pit"]
    hand = pit.get("throws") or "R"
    modifier = pit.get("so_modifier") or "NONE"
    played = evaluate_vs_hitters(pit["table_2d6"], hand, "NONE", _vectors(hand, modifier))
    keys = ("h_bf", "bb_bf", "so_bf", "hr_bf", "hbp_bf")
    return {key: played[key] for key in keys}, modifier


def _pitcher_target(peak):
    raw = _pitcher_raw(peak)
    years = list(peak.get("window_years") or [])
    year = int(round(statistics.median(years))) if years else 1986
    pipe = full_pipeline(raw, year)
    return raw, pipe["solver_target"], year


def _pitcher_flags(target, before, after, info):
    flags = []
    if info and "REVIEW" in (info.get("status") or ""):
        flags.append(info["status"])
    for key, limit in PITCH_RATE_FLAG.items():
        gap = after[key] - target[key]
        if abs(gap) > limit:
            flags.append("vs target %s %+.4f" % (key, gap))
        if abs(after[key] - target[key]) > abs(before[key] - target[key]) + WORSE_FLAG:
            flags.append("%s worse than the previous chart" % key)
    return flags


def _mae_bias(rows, block, baseline, keys):
    out = {}
    for key in keys:
        gaps = [row[block][key] - row[baseline][key] for row in rows]
        out[key] = {
            "mae": round(sum(abs(gap) for gap in gaps) / len(gaps), 4),
            "bias": round(sum(gaps) / len(gaps), 4),
        }
    return out


def _worst(rows, block, baseline, key, n=8):
    return sorted(rows, key=lambda row: -abs(row[block][key] - row[baseline][key]))[:n]


def _brief(row, keys):
    return {
        "key": row["key"],
        "name": row["name"],
        "team": row["team"],
        "flags": row["flags"],
        "real": {key: row["real"][key] for key in keys if key in row["real"]},
        "before": {key: row["before"][key] for key in keys},
        "after": {key: row["after"][key] for key in keys},
    }


def main():
    cards = json.loads(open(CARDS).read())
    old_bat, old_pit = _old_method(cards)
    if len(old_bat) != 120 or len(old_pit) != 132:
        raise SystemExit("expected 120 hitters and 132 pitchers, found %d and %d" % (
            len(old_bat), len(old_pit)))
    frozen = {}
    for slot in old_bat + old_pit:
        card = cards[slot["key"]]
        frozen[slot["key"]] = {
            "peak_bat": json.dumps(card.get("peak_bat"), sort_keys=True),
            "peak_pit": json.dumps(card.get("peak_pit"), sort_keys=True),
            "tournament": json.dumps(card.get("tournament"), sort_keys=True),
            "positions": json.dumps((card.get("card_bat") or {}).get("positions"), sort_keys=True),
            "stamina": json.dumps((card.get("card_pit") or {}).get("stamina"), sort_keys=True),
            "throws": (card.get("card_pit") or {}).get("throws"),
            "bats": (card.get("card_bat") or {}).get("bats"),
            "run": (card.get("card_bat") or {}).get("run"),
        }

    hitter_rows = []
    failures = []
    for index, slot in enumerate(old_bat, start=1):
        card = cards[slot["key"]]
        real, target, ibb = _hitter_lines(card["peak_bat"])
        if ibb > float(card["peak_bat"].get("BB") or 0):
            failures.append({"key": slot["key"], "side": "bat", "reason": "IBB exceeds BB"})
            continue
        before = _hitter_expected(card)
        positions = frozen[slot["key"]]["positions"]
        kept, reason = base._rebuild_hitter(card)
        if kept is None:
            failures.append({"key": slot["key"], "side": "bat", "reason": reason})
            continue
        if json.dumps(kept.get("positions"), sort_keys=True) != positions:
            failures.append({"key": slot["key"], "side": "bat", "reason": "fielding changed"})
            continue
        card["card_bat"] = kept
        after = _hitter_expected(card)
        slash = ("avg", "obp", "slg")
        events = ("1bp", "2bp", "3bp", "hrp", "bbp", "sop")
        hitter_rows.append({
            "key": slot["key"],
            "name": slot["name"],
            "team": slot["team"],
            "years": list(card["peak_bat"].get("window_years") or []),
            "ibb": ibb,
            "real": _pack(real, slash + events),
            "target": _pack(target, ("obp", "bbp")),
            "before": _pack(before, slash + events),
            "after": _pack(after, slash + events),
            "gap_before": _gap(before, real, slash + ("1bp", "2bp", "3bp", "hrp", "sop")),
            "gap_after": _gap(after, real, slash + ("1bp", "2bp", "3bp", "hrp", "sop")),
            "obp_vs_target_before": _round(before["obp"] - target["obp"]),
            "obp_vs_target_after": _round(after["obp"] - target["obp"]),
            "flags": _hitter_flags(real, target, before, after),
        })
        if index % 20 == 0:
            print("hitters", index, flush=True)

    # Solve with the same call the 215 used, and keep its fit record.
    pitcher_rows = []
    modifier_changes = []
    for index, slot in enumerate(old_pit, start=1):
        card = cards[slot["key"]]
        raw, target, year = _pitcher_target(card["peak_pit"])
        before, before_mod = _pitcher_played(card)
        kept, info = base._rebuild_pitcher(card, slot["key"])
        if kept is None:
            failures.append({"key": slot["key"], "side": "pit", "reason": info})
            continue
        card["card_pit"] = kept
        after, after_mod = _pitcher_played(card)
        keys = ("h_bf", "bb_bf", "so_bf", "hr_bf", "hbp_bf")
        pitcher_rows.append({
            "key": slot["key"],
            "name": slot["name"],
            "team": slot["team"],
            "years": list(card["peak_pit"].get("window_years") or []),
            "year_used": year,
            "so_modifier_before": before_mod,
            "so_modifier_after": after_mod,
            "fit_error": info["fit_error"],
            "status": info["status"],
            "real": _pack(raw, keys),
            "target": _pack(target, keys),
            "before": _pack(before, keys),
            "after": _pack(after, keys),
            "gap_vs_real_before": _gap(before, raw, keys),
            "gap_vs_real_after": _gap(after, raw, keys),
            "gap_vs_target_before": _gap(before, target, keys),
            "gap_vs_target_after": _gap(after, target, keys),
            "flags": _pitcher_flags(target, before, after, info),
        })
        if after_mod != before_mod:
            modifier_changes.append({
                "key": slot["key"], "name": slot["name"],
                "was": before_mod, "now": after_mod,
            })
        if index % 20 == 0:
            print("pitchers", index, flush=True)

    for key, snap in frozen.items():
        card = cards[key]
        if json.dumps(card.get("peak_bat"), sort_keys=True) != snap["peak_bat"]:
            raise SystemExit("peak batting line changed: %s" % key)
        if json.dumps(card.get("peak_pit"), sort_keys=True) != snap["peak_pit"]:
            raise SystemExit("peak pitching line changed: %s" % key)
        if json.dumps(card.get("tournament"), sort_keys=True) != snap["tournament"]:
            raise SystemExit("tournament line changed: %s" % key)
        if json.dumps((card.get("card_bat") or {}).get("positions"), sort_keys=True) != snap["positions"]:
            raise SystemExit("fielding changed: %s" % key)
        if json.dumps((card.get("card_pit") or {}).get("stamina"), sort_keys=True) != snap["stamina"]:
            raise SystemExit("stamina changed: %s" % key)

    text = _dump(cards)
    with open(CARDS, "w") as handle:
        handle.write(text)

    slash = ("avg", "obp", "slg")
    # OBP in gap_after is versus the real line, IBB included.
    hitter_vs_real = _mae_bias(hitter_rows, "after", "real", slash + ("1bp", "2bp", "3bp", "hrp", "sop"))
    hitter_vs_real_before = _mae_bias(hitter_rows, "before", "real", slash + ("1bp", "2bp", "3bp", "hrp", "sop"))
    pit_keys = ("so_bf", "bb_bf", "hr_bf", "h_bf")
    report = {
        "hitters": len(hitter_rows),
        "pitchers": len(pitcher_rows),
        "failures": failures,
        "modifier_changes": modifier_changes,
        "hitter_vs_real_before": hitter_vs_real_before,
        "hitter_vs_real_after": hitter_vs_real,
        "hitter_obp_vs_target": {
            "before": {
                "mae": round(sum(abs(row["obp_vs_target_before"]) for row in hitter_rows) / len(hitter_rows), 4),
                "bias": round(sum(row["obp_vs_target_before"] for row in hitter_rows) / len(hitter_rows), 4),
            },
            "after": {
                "mae": round(sum(abs(row["obp_vs_target_after"]) for row in hitter_rows) / len(hitter_rows), 4),
                "bias": round(sum(row["obp_vs_target_after"] for row in hitter_rows) / len(hitter_rows), 4),
            },
        },
        "pitcher_vs_target_before": _mae_bias(pitcher_rows, "before", "target", pit_keys),
        "pitcher_vs_target_after": _mae_bias(pitcher_rows, "after", "target", pit_keys),
        "pitcher_vs_real_before": _mae_bias(pitcher_rows, "before", "real", pit_keys),
        "pitcher_vs_real_after": _mae_bias(pitcher_rows, "after", "real", pit_keys),
        "hitter_flags": [row for row in hitter_rows if row["flags"]],
        "pitcher_flags": [row for row in pitcher_rows if row["flags"]],
        "hitter_worst_avg": [_brief(row, slash) for row in _worst(hitter_rows, "after", "real", "avg")],
        "hitter_worst_slg": [_brief(row, slash) for row in _worst(hitter_rows, "after", "real", "slg")],
        "pitcher_worst_so": [_brief(row, ("so_bf",)) for row in _worst(pitcher_rows, "after", "target", "so_bf")],
        "cards_hitters": hitter_rows,
        "cards_pitchers": pitcher_rows,
        "notes": [
            "Windows, peak counting lines, fielding, stamina, and the tournament block were not rewritten.",
            "Hitter rates are the solver's completed-PA expectation, including rulebook defense and the 1986 parks. A reached-on-error is an at-bat and not a hit.",
            "Card OBP excludes intentional walks. obp_vs_target is the fit. obp inside gap_after is versus the real line, which includes intentional walks.",
            "Pitcher charts were fit with the page-39 shift. TOUGH-OUT was not shifted. Face 00 was not shifted.",
            "Pitcher 'target' is the era-normalized, 1986-calibrated rate the solver aims at. 'real' is the raw window rate. A gap versus real with a tight gap versus target is the translation, not a missed fit.",
            "The 215 window-changed cards, the four missing hitters, and Elmer Valo were not in this set.",
        ],
    }
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    print("rebuilt", len(hitter_rows), len(pitcher_rows), "failures", len(failures))
    print("hitter flags", len(report["hitter_flags"]), "pitcher flags", len(report["pitcher_flags"]))
    print("hitter avg after", hitter_vs_real["avg"])
    print("pitcher so vs target after", report["pitcher_vs_target_after"]["so_bf"])


if __name__ == "__main__":
    main()
