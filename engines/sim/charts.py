"""Charts read from the Payoff Pitch Baseball rulebook (Sideline Strategy Games).

Pages cited are the 146-page PDF "Charts_2021_ver_09". Ballpark rows are the
12 stadium charts on pages 109-110. Portrait pages 144-145 repeat those parks
and are not entered twice. The hitter solver's frozen "26 parks" mean is a
different set; it is not these 12 charts.

Error ratings on a park chart run 5 (best, narrowest ERR band) through 1
(worst). That matches the printed sentence on page 3. Range letters run A
(best) through D and F.
"""

# 2d6 weights, totals 2 through 12. Sum is 36.
D6_WEIGHTS = (1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1)

# Defense chart, percentile faces 01-99 (page 20). 00 is not on this chart.
# (lo, hi, check, position)
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

# Re-rolled 2d6 on the HIT chart. Groups: 0 corners (1B, 3B), 1 middle
# (2B, SS, P), 2 outfield. Value is (hit, dagger). A dagger double is a
# triple when the batter's RUN rating is 8 or higher (page 20).
HIT_BY_D6 = {
    2: (("2B", False), ("1B", False), ("2B", False)),
    3: (("1B", False), ("1B", False), ("1B", False)),
    4: (("2B", False), ("1B", False), ("1B", False)),
    5: (("1B", False), ("1B", False), ("1B", False)),
    6: (("2B", False), ("1B", False), ("1B", False)),
    7: (("1B", False), ("1B", False), ("2B", False)),
    8: (("2B", False), ("1B", False), ("1B", False)),
    9: (("1B", False), ("1B", False), ("1B", False)),
    10: (("2B", False), ("1B", False), ("2B", False)),
    11: (("1B", False), ("1B", False), ("2B", False)),
    12: (("2B", True), ("1B", False), ("2B", True)),
}

# ERR chart by the same 2d6. Groups: 0 catcher, 1 pitcher and infield,
# 2 outfield. SINGLE+error counts as a single. A dropped foul restarts
# the plate appearance. Any other error is an at-bat that is not a hit.
ERR_BY_D6 = {
    2: ("OUT", "OUT", "OUT"),
    3: ("OUT", "OUT", "OUT"),
    4: ("REROLL", "OUT", "OUT"),
    5: ("OUT", "OUT", "OUT"),
    6: ("OUT", "OUT", "OUT"),
    7: ("OUT", "OUT", "1B"),
    8: ("OUT", "OUT", "1B"),
    9: ("OUT", "1B", "OUT"),
    10: ("OUT", "OUT", "1B"),
    11: ("OUT", "OUT", "OUT"),
    12: ("REROLL", "OUT", "OUT"),
}

POS_HIT_GROUP = {
    "1B": 0, "3B": 0,
    "2B": 1, "SS": 1, "P": 1,
    "LF": 2, "CF": 2, "RF": 2,
}
POS_ERR_GROUP = {
    "C": 0,
    "P": 1, "1B": 1, "2B": 1, "3B": 1, "SS": 1,
    "LF": 2, "CF": 2, "RF": 2,
}

# wh_l / wh_r: WHEELHOUSE is percentile 1 through that face; the rest of
# 01-99 is IN-PLAY. range_hit_hi / error_hi: a park check at or below the
# face is a hit (range) or an error (error rating).
PARKS = (
    {"name": "CLEVELAND STADIUM", "season": "1954 Cleveland (A)", "wh_l": 42, "wh_r": 31,
     "range_hit_hi": {"A": 23, "B": 33, "C": 42, "D": 51, "F": 61},
     "error_hi": {"5": 24, "4": 33, "3": 42, "2": 56, "1": 65}},
    {"name": "POLO GROUNDS", "season": "1954 New York (N)", "wh_l": 41, "wh_r": 41,
     "range_hit_hi": {"A": 23, "B": 32, "C": 41, "D": 50, "F": 59},
     "error_hi": {"5": 29, "4": 41, "3": 52, "2": 69, "1": 80}},
    {"name": "EBBETS FIELD", "season": "1954 Brooklyn (N)", "wh_l": 47, "wh_r": 66,
     "range_hit_hi": {"A": 24, "B": 34, "C": 43, "D": 53, "F": 63},
     "error_hi": {"5": 27, "4": 37, "3": 48, "2": 63, "1": 73}},
    {"name": "YANKEE STADIUM", "season": "1954 New York (A)", "wh_l": 48, "wh_r": 22,
     "range_hit_hi": {"A": 24, "B": 34, "C": 44, "D": 54, "F": 63},
     "error_hi": {"5": 23, "4": 32, "3": 41, "2": 54, "1": 62}},
    {"name": "MEMORIAL STADIUM", "season": "1979 Baltimore (A)", "wh_l": 62, "wh_r": 54,
     "range_hit_hi": {"A": 22, "B": 31, "C": 40, "D": 49, "F": 58},
     "error_hi": {"5": 16, "4": 26, "3": 35, "2": 50, "1": 60}},
    {"name": "OAKLAND COLISEUM", "season": "1979 Oakland (A)", "wh_l": 45, "wh_r": 40,
     "range_hit_hi": {"A": 23, "B": 32, "C": 41, "D": 50, "F": 59},
     "error_hi": {"5": 19, "4": 32, "3": 44, "2": 62, "1": 74}},
    {"name": "ATLANTA-FULTON COUNTY STADIUM", "season": "1979 Atlanta (N)", "wh_l": 74, "wh_r": 88,
     "range_hit_hi": {"A": 26, "B": 36, "C": 47, "D": 57, "F": 68},
     "error_hi": {"5": 20, "4": 33, "3": 46, "2": 65, "1": 77}},
    {"name": "THREE RIVERS STADIUM", "season": "1979 Pittsburgh (N)", "wh_l": 87, "wh_r": 83,
     "range_hit_hi": {"A": 26, "B": 36, "C": 47, "D": 57, "F": 68},
     "error_hi": {"5": 16, "4": 26, "3": 36, "2": 51, "1": 61}},
    {"name": "ASTRODOME", "season": "1986 Houston (N)", "wh_l": 33, "wh_r": 46,
     "range_hit_hi": {"A": 27, "B": 36, "C": 47, "D": 58, "F": 68},
     "error_hi": {"5": 28, "4": 35, "3": 41, "2": 51, "1": 58}},
    {"name": "SHEA STADIUM", "season": "1986 New York (N)", "wh_l": 55, "wh_r": 48,
     "range_hit_hi": {"A": 25, "B": 35, "C": 45, "D": 51, "F": 59},
     "error_hi": {"5": 34, "4": 46, "3": 56, "2": 63, "1": 71}},
    {"name": "FENWAY PARK", "season": "1986 Boston (A)", "wh_l": 28, "wh_r": 46,
     "range_hit_hi": {"A": 31, "B": 44, "C": 57, "D": 67, "F": 80},
     "error_hi": {"5": 22, "4": 32, "3": 42, "2": 48, "1": 55}},
    {"name": "ANAHEIM STADIUM", "season": "1986 California (A)", "wh_l": 59, "wh_r": 54,
     "range_hit_hi": {"A": 23, "B": 35, "C": 43, "D": 53, "F": 63},
     "error_hi": {"5": 24, "4": 33, "3": 43, "2": 54, "1": 58}},
)


def defense_chart():
    """Percentile 1-99 -> (check, position). Index 0 is unused."""
    chart = [None] * 100
    for lo, hi, check, pos in DEFENSE_BANDS:
        for face in range(lo, hi + 1):
            chart[face] = (check, pos)
    return chart
