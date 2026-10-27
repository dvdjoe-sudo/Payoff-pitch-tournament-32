#!/usr/bin/env python3
"""Page-39 percentile shift, for fitting a pitcher card.

The tracker (apply_so_modifier) widens the SO band. This module does
not. It reads each hitter face the way the rulebook does:

- Faces are 01-99. Face 00 is a rare play and is not an out.
- On a plain TOUGH result, add the pitcher's +10 or +20. If the sum is
  greater than 99, the original face is used. 00 is not shifted.
- TOUGH-OUT is not shifted. The book names TOUGH only.

The vectors are the mean over the 1986 hitters, with the player's own
card left out when a name is passed. Importing this module does not
open the reference files.
"""
from __future__ import annotations

EVENTS = ("1B", "2B", "3B", "HR", "BB", "HBP", "SO", "OUT", "RARE_PLAY")


def _faces(table):
    faces = [None] * 100
    spans = []
    for outcome, rng in (table or {}).items():
        if outcome.endswith("_extra"):
            base = outcome[: -len("_extra")]
            for part in rng or []:
                if part and len(part) >= 2:
                    spans.append((base, int(part[0]), int(part[1])))
            continue
        if not rng or len(rng) < 2 or not isinstance(rng[0], (int, float)):
            continue
        spans.append((outcome, int(rng[0]), int(rng[1])))
    for outcome, lo, hi in spans:
        if outcome not in EVENTS:
            continue
        for face in range(max(1, lo), min(99, hi) + 1):
            if faces[face] is None:
                faces[face] = outcome
    return faces


def _count(faces, bump):
    counts = {key: 0.0 for key in EVENTS}
    for face in range(1, 100):
        use = face
        if bump:
            adjusted = face + bump
            if adjusted <= 99:
                use = adjusted
        outcome = faces[use] or "OUT"
        if outcome not in counts or outcome == "RARE_PLAY":
            outcome = "OUT"
        counts[outcome] += 1.0
    for key in counts:
        counts[key] /= 99.0
    counts["RARE_PLAY"] = 0.0
    return counts


def _mean(rows):
    total = {key: 0.0 for key in EVENTS}
    if not rows:
        return dict(total)
    for row in rows:
        for key in total:
            total[key] += row[key]
    n = float(len(rows))
    return {key: total[key] / n for key in total}


def vectors_for_bump(pitcher_hand="R", bump=0, exclude_name=None, hitters=None):
    """Category event vectors with the printed TOUGH shift baked into TOUGH.

    TOUGH-OUT keeps the unshifted strikeout rate. Pass the returned dict
    to evaluate_vs_hitters with so_modifier NONE so the tracker does not
    widen the band a second time.
    """
    if hitters is None:
        from event_vectors import load_players
        _all, hitters = load_players()
    if exclude_name:
        hitters = [h for h in hitters if h.get("name") != exclude_name]
    hand = "vsLHP" if pitcher_hand == "L" else "vsRHP"
    buckets = {name: [] for name in ("WHEELHOUSE", "PATIENT", "TOUGH", "IN-PLAY")}
    tough_plain = []
    for hitter in hitters:
        sections = hitter.get("sections") or {}
        for name in buckets:
            table = (sections.get(name) or {}).get(hand)
            if table is None:
                continue
            faces = _faces(table)
            if name == "TOUGH":
                tough_plain.append(_count(faces, 0))
                buckets[name].append(_count(faces, bump))
            else:
                buckets[name].append(_count(faces, 0))
    vectors = {name: _mean(rows) for name, rows in buckets.items()}
    patient = vectors["PATIENT"]
    walk = patient["BB"] + patient["HBP"]
    vectors["PATIENT-OUT"] = {
        "1B": 0.0, "2B": 0.0, "3B": 0.0, "HR": 0.0,
        "BB": patient["BB"], "HBP": patient["HBP"], "SO": 0.0,
        "OUT": 1.0 - walk, "RARE_PLAY": 0.0,
    }
    plain = _mean(tough_plain)
    vectors["TOUGH-OUT"] = {
        "1B": 0.0, "2B": 0.0, "3B": 0.0, "HR": 0.0, "BB": 0.0, "HBP": 0.0,
        "SO": plain["SO"], "OUT": 1.0 - plain["SO"], "RARE_PLAY": 0.0,
    }
    wheel, in_play = vectors["WHEELHOUSE"], vectors["IN-PLAY"]
    vectors["BALLPARK"] = {key: 0.5 * wheel[key] + 0.5 * in_play[key] for key in EVENTS}
    vectors["DEFENSE"] = {
        "1B": 0.25, "2B": 0.02, "3B": 0.005, "HR": 0.0, "BB": 0.0,
        "HBP": 0.0, "SO": 0.0, "OUT": 0.725, "RARE_PLAY": 0.0,
    }
    return vectors
