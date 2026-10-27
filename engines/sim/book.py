"""Charts copied from the Payoff Pitch Baseball rulebook PDF.

Page numbers are the 146-page book (©2021 Sideline Strategy Games,
designed by Joe Bryan). The separate Quick Results booklet and the
two-page Ratings and Symbols sheet are not used. The Ratings and
Symbols Addendum printed on page 39 of the rulebook is part of the book.

The plate-appearance rate harness in pa_sim.py is a different tool.
Its error chart treats several page-20 error faces as outs and treats
SINGLE+error as a reached-on-error. The printed ERR chart does not.
This module follows the printed chart.
"""
from __future__ import annotations

# Defense position chart, percentile 01-99. Page 20. 00 is not on it.
DEFENSE_BANDS = (
    (1, 2, "RANGE", "P"),
    (3, 6, "RANGE", "1B"),
    (7, 12, "RANGE", "2B"),
    (13, 16, "RANGE", "3B"),
    (17, 22, "RANGE", "SS"),
    (23, 26, "RANGE", "LF"),
    (27, 31, "RANGE", "CF"),
    (32, 35, "RANGE", "RF"),
    (36, 42, "ERROR", "P"),
    (43, 43, "ERROR", "C"),
    (44, 50, "ERROR", "1B"),
    (51, 61, "ERROR", "2B"),
    (62, 75, "ERROR", "3B"),
    (76, 90, "ERROR", "SS"),
    (91, 93, "ERROR", "LF"),
    (94, 96, "ERROR", "CF"),
    (97, 99, "ERROR", "RF"),
)

# HIT chart, page 20. Groups are corners (1B, 3B), middle (2B, SS, P),
# outfield. Value is (batter result, runner bases, dagger).
# A dagger double is a triple when the batter's RUN is 8 or higher.
HIT_BY_D6 = {
    2: (("2B", 3, False), ("1B", 2, False), ("2B", 3, False)),
    3: (("1B", 2, False), ("1B", 1, False), ("1B", 2, False)),
    4: (("2B", 2, False), ("1B", 1, False), ("1B", 2, False)),
    5: (("1B", 1, False), ("1B", 1, False), ("1B", 2, False)),
    6: (("2B", 2, False), ("1B", 1, False), ("1B", 2, False)),
    7: (("1B", 1, False), ("1B", 2, False), ("2B", 2, False)),
    8: (("2B", 2, False), ("1B", 1, False), ("1B", 2, False)),
    9: (("1B", 1, False), ("1B", 1, False), ("1B", 2, False)),
    10: (("2B", 2, False), ("1B", 1, False), ("2B", 3, False)),
    11: (("1B", 2, False), ("1B", 2, False), ("2B", 3, False)),
    12: (("2B", 3, True), ("1B", 2, False), ("2B", 3, True)),
}

# ERR chart, page 20. Groups are C, pitcher and infield, outfield.
# A number is that many bases on the error. "FOUL" restarts the at-bat.
# "SINGLE+" is a hit plus one extra base for the batter and the runners.
ERR_BY_D6 = {
    2: (2, 2, 2),
    3: (2, 1, 3),
    4: ("FOUL", 2, 1),
    5: (1, 1, 1),
    6: (1, 1, 2),
    7: (1, 1, "SINGLE+"),
    8: (1, 1, "SINGLE+"),
    9: (1, "SINGLE+", 1),
    10: (1, 1, "SINGLE+"),
    11: (1, 1, 1),
    12: ("FOUL", 2, 2),
}

POS_HIT_GROUP = {"1B": 0, "3B": 0, "2B": 1, "SS": 1, "P": 1, "LF": 2, "CF": 2, "RF": 2}
POS_ERR_GROUP = {
    "C": 0, "P": 1, "1B": 1, "2B": 1, "3B": 1, "SS": 1, "LF": 2, "CF": 2, "RF": 2,
}

# Defense OUT chart, page 20, same 2d6. Groups: C, infield+P, outfield.
DEFENSE_OUT = {
    2: ("POP", "GB-DP-A", "DEEP"),
    3: ("POP", "GB-ADV", "SHORT-DP"),
    4: ("POP-FOUL", "LINE", "SHORT"),
    5: ("POP-FOUL", "GB-DP-AB", "SHORT"),
    6: ("GB-ADV", "GB-FC", "SHORT"),
    7: ("POP-FOUL", "GB-FC", "SHORT"),
    8: ("GB-FC", "GB-ADV", "DEEP"),
    9: ("POP-FOUL", "GB-DP-A", "DEEP"),
    10: ("POP", "POP", "DEEP"),
    11: ("POP", "GB-ADV", "DEEP"),
    12: ("POP", "LINE-DP-AB", "SHORT-DP"),
}

# Advanced runner chart, page 16. Low die 1-6.
# Single, runner on 1st: bases, and whether he has a choice.
ADV_SINGLE_FIRST = {
    1: (1, False), 2: (2, False), 3: (1, False),
    4: (1, True), 5: (1, False), 6: (1, False),
}
ADV_SINGLE_SECOND = {
    1: (1, False), 2: (4, False), 3: (4, False),
    4: (1, True), 5: (4, False), 6: (1, False),
}
ADV_DOUBLE_FIRST = {
    1: (2, False), 2: (2, False), 3: (4, False),
    4: (2, True), 5: (4, False), 6: (4, False),
}

# Hit location, ones digit of the percentile, page 16.
# A slash is (LHB fielder, RHB fielder).
HIT_LOCATION_SINGLE = {
    0: "RF", 1: "LF", 2: "LF", 3: "CF", 4: "CF",
    5: ("LF", "RF"), 6: "CF", 7: ("LF", "RF"), 8: ("LF", "RF"), 9: "CF",
}
HIT_LOCATION_DOUBLE = {
    0: ("RF", "LF"), 1: "RF", 2: "LF", 3: ("RF", "LF"), 4: "CF",
    5: "LF", 6: "CF", 7: ("RF", "LF"), 8: "CF", 9: ("LF", "RF"),
}

# Stealing 2nd or 3rd, page 18. Letter+arm -> column, then bands.
STEAL_COLUMN = {
    "A5": "EXCELLENT", "A4": "EXCELLENT", "A3": "EXCELLENT",
    "B5": "EXCELLENT", "B4": "EXCELLENT", "C5": "EXCELLENT",
    "A2": "VERY GOOD", "B3": "VERY GOOD", "C4": "VERY GOOD", "D5": "VERY GOOD",
    "A1": "NORMAL", "B2": "NORMAL", "C3": "NORMAL", "D4": "NORMAL", "F5": "NORMAL",
    "B1": "FAIR", "C2": "FAIR", "D3": "FAIR", "F4": "FAIR",
    "C1": "POOR", "D2": "POOR", "D1": "POOR", "F3": "POOR", "F2": "POOR", "F1": "POOR",
}
# (drop_hi, e2_hi, caught_hi). The rest through 99 is safe.
STEAL_BANDS = {
    "EXCELLENT": (2, 12, 17),
    "VERY GOOD": (2, 12, 26),
    "NORMAL": (2, 12, 42),
    "FAIR": (2, 12, 59),
    "POOR": (2, 12, 84),
}
# Stealing home uses the letter only. Page 18. (drop_hi, caught_hi).
STEAL_HOME = {"A": (9, 69), "B": (9, 79), "C": (9, 89), "D": (9, 94), "F": (9, 98)}

# Pickoff when the steal 2d6 is 12. Columns by Hold. Page 18.
# (wild_hi, caught_hi, safe_hi). The rest through 99 is a balk.
PICKOFF = {
    (1, 3): (6, 34, 95),
    (4, 5): (7, 27, 96),
    (6, 7): (8, 21, 97),
    (8, 9): (8, 16, 98),
    (10, 10): (8, 12, 98),
}

# Sacrifice bunt, page 19. (po_hi, dp_hi, lead_hi, sh_hi, miss_hi). Rest is E?.
SAC_BANDS = {
    "A": (0, 2, 6, 92, 94),
    "B": (2, 5, 10, 90, 94),
    "C": (3, 6, 15, 89, 94),
    "D": (5, 9, 24, 87, 94),
    "F": (7, 14, 33, 84, 94),
}

# Hit and run ground out, page 18. The 2d6 is a fresh roll.
# 2-3 double play, 4-10 batter out and runners advance 1, 11-12 force.

# Fatigued pitcher charts, page 21. Faces 01-99. 00 is not printed.
FATIGUE_PATIENT = {
    "SP": ((1, 67, "PATIENT"), (68, 71, "SINGLE"), (72, 79, "IN-PLAY"), (80, 99, "WHEELHOUSE")),
    "RP": ((1, 37, "PATIENT"), (38, 50, "SINGLE"), (51, 79, "IN-PLAY"), (80, 99, "WHEELHOUSE")),
}
FATIGUE_TOUGH = ((1, 54, "TOUGH"), (55, 66, "IN-PLAY"), (67, 99, "WHEELHOUSE"))

# Injury chart, page 21. Percentile bands by rating.
INJURY = {
    "Prone": ((0, 10, "ok"), (11, 15, "game"), (16, 20, "plus1"), (21, 30, "plusd6"),
              (31, 50, "plus10"), (51, 75, "plus20"), (76, 89, "plus50"), (90, 99, "season")),
    "Normal": ((0, 30, "ok"), (31, 50, "game"), (51, 65, "plus1"), (66, 88, "plusd6"), (89, 99, "plus10")),
    "Durable": ((0, 69, "ok"), (70, 84, "game"), (85, 94, "plus1"), (95, 99, "plusd6")),
    "Iron": ((0, 69, "ok"), (70, 89, "game"), (90, 99, "plus1")),
}

GROUND_OUTS = {"G1", "G2", "G3", "G4", "G5", "G6"}
FLY_OUTS = {"F7", "F8", "F9"}
LINE_OUTS = {"L4", "L6"}
POP_OUTS = {"P2", "P3", "P4", "P5", "P6"}
OUT_POS = {
    "G1": "P", "G2": "C", "G3": "1B", "G4": "2B", "G5": "3B", "G6": "SS",
    "F7": "LF", "F8": "CF", "F9": "RF",
    "L4": "2B", "L6": "SS",
    "P2": "C", "P3": "1B", "P4": "2B", "P5": "3B", "P6": "SS",
}


def defense_slot(pct):
    """Page 20. Returns (check, position) or None when the face is 00."""
    if pct == 0:
        return None
    for lo, hi, check, pos in DEFENSE_BANDS:
        if lo <= pct <= hi:
            return check, pos
    return None


def steal_result(column, pct):
    drop_hi, e2_hi, caught_hi = STEAL_BANDS[column]
    if pct <= drop_hi:
        return "DROP"
    if pct <= e2_hi:
        return "E2"
    if pct <= caught_hi:
        return "CAUGHT"
    return "SAFE"


def steal_home_result(letter, pct):
    drop_hi, caught_hi = STEAL_HOME[letter]
    if pct <= drop_hi:
        return "DROP"
    if pct <= caught_hi:
        return "CAUGHT"
    return "SAFE"


def pickoff_column(hold):
    for (lo, hi), bands in PICKOFF.items():
        if lo <= hold <= hi:
            return bands
    return None


def pickoff_result(hold, pct):
    bands = pickoff_column(hold)
    if bands is None:
        return None
    wild_hi, caught_hi, safe_hi = bands
    if pct <= wild_hi:
        return "WILD"
    if pct <= caught_hi:
        return "CAUGHT"
    if pct <= safe_hi:
        return "SAFE"
    return "BALK"


def sac_result(letter, pct):
    po_hi, dp_hi, lead_hi, sh_hi, miss_hi = SAC_BANDS[letter]
    if pct <= po_hi:
        return "PO"
    if pct <= dp_hi:
        return "DP"
    if pct <= lead_hi:
        return "LEAD"
    if pct <= sh_hi:
        return "SH"
    if pct <= miss_hi:
        return "MISS"
    return "E"


def fatigue_patient(kind, pct):
    if pct == 0:
        return None
    for lo, hi, result in FATIGUE_PATIENT[kind]:
        if lo <= pct <= hi:
            return result
    return None


def fatigue_tough(pct):
    if pct == 0:
        return None
    for lo, hi, result in FATIGUE_TOUGH:
        if lo <= pct <= hi:
            return result
    return None


def injury_result(rating, pct):
    bands = INJURY.get(rating)
    if not bands:
        return None
    for lo, hi, result in bands:
        if lo <= pct <= hi:
            return result
    return None


def hit_fielder(kind, ones, stand):
    table = HIT_LOCATION_SINGLE if kind == "1B" else HIT_LOCATION_DOUBLE
    spot = table.get(ones)
    if isinstance(spot, tuple):
        return spot[0] if stand == "L" else spot[1]
    return spot


def section_faces(hand_table):
    """Faces 1-99. The first listed result keeps a face if bands overlap."""
    faces = [None] * 100
    overlaps = []
    if not hand_table:
        return faces, overlaps
    for key in ("HR", "3B", "2B", "1B", "BB", "HBP", "SO"):
        band = hand_table.get(key)
        if not band or len(band) < 2 or band[1] is None or band[0] is None:
            continue
        lo, hi = int(band[0]), int(band[1])
        if hi < lo:
            continue
        for face in range(max(1, lo), min(99, hi) + 1):
            if faces[face] is None:
                faces[face] = key
            else:
                overlaps.append((face, faces[face], key))
    return faces, overlaps


def out_type(out_table, pct):
    if not out_table or pct == 0:
        return None
    for row in out_table:
        lo, hi = row["range"]
        if lo <= pct <= hi:
            return row["result"]
    return None


def wp_bounds(wp):
    """Page 10. Cards store '30' or '30-32'. None means no printed rating."""
    if wp is None:
        return None
    if isinstance(wp, (list, tuple)) and len(wp) == 2:
        return int(wp[0]), int(wp[1])
    text = str(wp).strip()
    if not text or text.lower() == "none":
        return None
    if "-" in text:
        left, right = text.split("-", 1)
        return int(left), int(right)
    return int(text), int(text)


def wp_hit(wp, pct):
    bounds = wp_bounds(wp)
    if bounds is None:
        return False
    lo, hi = bounds
    return lo <= pct <= hi
