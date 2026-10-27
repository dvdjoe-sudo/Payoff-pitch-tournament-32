"""Rulebook checks for the plate-appearance simulator. No card files are written."""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from charts import DEFENSE_BANDS, PARKS, defense_chart
from pa_sim import (
    CHART,
    D6_FACES,
    Tally,
    ballpark_target,
    ballpark_wheel_share,
    defense_distribution,
    defense_event,
    parks_1986,
    read_patient_out,
    read_section,
    read_tough_out,
    resolve_pa,
    section_faces,
    shift_percentile,
    simulate_hitter,
    Pitcher,
    Batter,
)


def hodges_tough():
    """Page 4. Cuellar TOUGH, percentile 65, Hodges misses 1-61 and is out."""
    faces = section_faces({"SO": [1, 47], "2B": [48, 49], "3B": [50, 50], "1B": [51, 61]})
    assert read_section(faces, 65) == "OUT"
    assert read_section(faces, 47) == "SO"
    assert read_section(faces, 51) == "1B"
    assert read_section(faces, 0) == "RARE"


def shift_matches_page_39():
    assert shift_percentile(86, 20) == 86
    assert shift_percentile(50, 20) == 70
    assert shift_percentile(35, 10) == 45
    assert shift_percentile(0, 20) == 0
    faces = section_faces({"SO": [1, 40], "1B": [41, 55]})
    # 35 is a strikeout. After +10 it is 45, a single. The shift makes fewer strikeouts.
    assert read_section(faces, 35) == "SO"
    assert read_section(faces, shift_percentile(35, 10)) == "1B"


def patient_out_keeps_only_walks():
    faces = section_faces({"BB": [1, 20], "1B": [21, 40], "HBP": [41, 45]})
    assert read_patient_out(faces, 10) == "BB"
    assert read_patient_out(faces, 30) == "OUT"
    assert read_patient_out(faces, 43) == "HBP"
    assert read_patient_out(faces, 80) == "OUT"
    assert read_patient_out(faces, 0) == "RARE"


def tough_out_blocks_hits_above_the_strikeout_band():
    faces = section_faces({"1B": [1, 9], "SO": [10, 40], "2B": [41, 50]})
    assert read_tough_out(faces, 40, 25) == "SO"
    assert read_tough_out(faces, 40, 45) == "OUT"
    assert read_tough_out(faces, 40, 5) == "1B"
    assert read_tough_out(faces, 40, 0) == "RARE"


def ballpark_uses_the_park_split():
    assert ballpark_target(30, 20) == "WHEELHOUSE"
    assert ballpark_target(30, 31) == "IN-PLAY"
    assert ballpark_target(30, 0) == "RARE"


def defense_chart_covers_01_through_99():
    chart = defense_chart()
    assert chart[0] is None
    assert all(chart[face] is not None for face in range(1, 100))
    covered = sum(hi - lo + 1 for lo, hi, _check, _pos in DEFENSE_BANDS)
    assert covered == 99


def defense_is_not_an_automatic_out():
    # Range C that hits on every face, 2d6 = 3, first base: a single.
    assert defense_event("RANGE", "1B", 3, 50, 99, 0, 5) == "1B"
    # A missed range check is an out.
    assert defense_event("RANGE", "1B", 3, 50, 10, 99, 5) == "OUT"
    # SINGLE+error on the outfield, 2d6 = 7, is a reached-on-error, not a hit.
    assert defense_event("ERROR", "LF", 7, 20, 0, 40, 5) == "ROE"
    # A plain error is an at-bat that is not a hit.
    assert defense_event("ERROR", "SS", 5, 20, 0, 40, 5) == "OUT"
    # RANGE against the catcher is read at CF. 2d6 = 2 is a double in the outfield.
    assert defense_event("RANGE", "C", 2, 10, 99, 0, 5) == "2B"
    # Dagger double, run 8, becomes a triple.
    assert defense_event("RANGE", "LF", 12, 10, 99, 0, 8) == "3B"
    assert defense_event("RANGE", "LF", 12, 10, 99, 0, 7) == "2B"


def reached_on_error_is_not_a_hit():
    tally = Tally()
    tally.add("ROE")
    tally.add("1B")
    rates = tally.rates()
    assert tally.ab == 2 and tally.h == 1 and tally.tb == 1
    assert rates["avg"] == 0.5
    assert rates["obp"] == 0.5
    assert rates["slg"] == 0.5


def ballpark_share_uses_the_1986_charts():
    parks = parks_1986()
    assert len(parks) == 26
    mean_l = sum(park["wh_l"] for park in parks) / len(parks) / 99.0
    mean_r = sum(park["wh_r"] for park in parks) / len(parks) / 99.0
    assert abs(ballpark_wheel_share("L", parks) - mean_l) < 1e-12
    assert abs(ballpark_wheel_share("R", parks) - mean_r) < 1e-12
    switch = 0.28 * mean_r + 0.72 * mean_l
    assert abs(ballpark_wheel_share("S", parks) - switch) < 1e-12
    assert len(PARKS) == 12


def defense_distribution_matches_monte_carlo():
    parks = parks_1986()
    dist = defense_distribution(parks)
    assert abs(sum(dist["low"].values()) - 1.0) < 1e-9
    assert abs(sum(dist["high"].values()) - 1.0) < 1e-9
    assert dist["low"]["ROE"] > 0.01
    assert dist["low"]["REROLL"] > 0
    assert dist["high"]["3B"] > dist["low"]["3B"]
    rng = random.Random(7)
    n = 40000
    counts = {}
    for _ in range(n):
        park = parks[rng.randrange(len(parks))]
        check, pos = CHART[rng.randrange(1, 100)]
        d6 = D6_FACES[rng.randrange(36)]
        pct = rng.randrange(100)
        if pct == 0:
            event = "OUT"
        else:
            event = defense_event(
                check, pos, d6, pct,
                park["range_hit_hi"]["C"], park["error_hi"]["3"], 5,
            )
        counts[event] = counts.get(event, 0) + 1
    for event, share in dist["low"].items():
        got = counts.get(event, 0) / n
        assert abs(got - share) < 0.012, (event, got, share)


def parks_are_the_twelve_printed_charts():
    assert len(PARKS) == 12
    astrodome = next(park for park in PARKS if park["name"] == "ASTRODOME")
    assert astrodome["wh_l"] == 33 and astrodome["wh_r"] == 46
    assert astrodome["range_hit_hi"]["C"] == 47
    assert astrodome["error_hi"]["5"] < astrodome["error_hi"]["1"]


def synthetic_card_runs():
    """A walk-heavy patient band versus a patient-only pitcher draws walks."""
    card_b = {
        "name": "Synthetic",
        "card_bat": {
            "bats": "R",
            "run": 6,
            "sections": {
                "WHEELHOUSE": {"vsRHP": {"HR": [1, 10]}, "vsLHP": {"HR": [1, 10]}},
                "PATIENT": {"vsRHP": {"BB": [1, 80]}, "vsLHP": {"BB": [1, 80]}},
                "TOUGH": {"vsRHP": {"SO": [1, 50]}, "vsLHP": {"SO": [1, 50]}},
                "IN-PLAY": {"vsRHP": {"1B": [1, 20]}, "vsLHP": {"1B": [1, 20]}},
            },
        },
        "peak_bat": {"AB": 400, "H": 100, "2B": 20, "3B": 2, "HR": 10, "BB": 40, "HBP": 4, "SO": 80},
    }
    card_p = {
        "name": "Synthetic P",
        "card_pit": {
            "throws": "R",
            "so_modifier": "NONE",
            "table_2d6": {str(n): "PATIENT" for n in range(2, 13)},
        },
        "peak_pit": {"bf": 600, "h": 150, "hr": 15, "bb": 40, "so": 120},
    }
    batter = Batter("SYN|bat", card_b)
    pitcher = Pitcher("SYN|pit", card_p)
    tally = simulate_hitter(random.Random(1), batter, [pitcher], 2000)
    rates = tally.rates()
    assert rates["bb"] > 0.70
    assert tally.rare > 0
    # 00 is excluded, so the walk rate is about 80/99, not 80/100, and it is not an out.
    assert rates["so"] == 0


def tough_shift_changes_a_live_pa():
    card_b = {
        "name": "Synthetic",
        "card_bat": {
            "bats": "R",
            "run": 5,
            "sections": {
                "WHEELHOUSE": {"vsRHP": {}, "vsLHP": {}},
                "PATIENT": {"vsRHP": {}, "vsLHP": {}},
                "TOUGH": {"vsRHP": {"SO": [1, 40], "1B": [41, 60]}, "vsLHP": {"SO": [1, 40]}},
                "IN-PLAY": {"vsRHP": {}, "vsLHP": {}},
            },
        },
    }
    batter = Batter("SYN|bat", card_b)
    base = {"name": "P", "card_pit": {"throws": "R", "so_modifier": "NONE",
                                      "table_2d6": {str(n): "TOUGH" for n in range(2, 13)}}}
    bumped = {"name": "P", "card_pit": {"throws": "R", "so_modifier": "+20",
                                        "table_2d6": {str(n): "TOUGH" for n in range(2, 13)}}}
    plain = simulate_hitter(random.Random(2), batter, [Pitcher("a", base)], 4000)
    wide = simulate_hitter(random.Random(2), batter, [Pitcher("b", bumped)], 4000)
    assert wide.so < plain.so


def resolve_uses_the_printed_table():
    card_b = {
        "name": "Synthetic",
        "card_bat": {
            "bats": "L",
            "run": 4,
            "sections": {
                "WHEELHOUSE": {"vsRHP": {"HR": [1, 99]}, "vsLHP": {"HR": [1, 99]}},
                "PATIENT": {"vsRHP": {}, "vsLHP": {}},
                "TOUGH": {"vsRHP": {}, "vsLHP": {}},
                "IN-PLAY": {"vsRHP": {}, "vsLHP": {}},
            },
        },
    }
    card_p = {"name": "P", "card_pit": {"throws": "R", "so_modifier": "NONE",
                                        "table_2d6": {str(n): "WHEELHOUSE" for n in range(2, 13)}}}
    event = resolve_pa(random.Random(3), Batter("b", card_b), Pitcher("p", card_p))
    assert event in ("HR", "RARE")


if __name__ == "__main__":
    hodges_tough()
    shift_matches_page_39()
    patient_out_keeps_only_walks()
    tough_out_blocks_hits_above_the_strikeout_band()
    ballpark_uses_the_park_split()
    defense_chart_covers_01_through_99()
    defense_is_not_an_automatic_out()
    reached_on_error_is_not_a_hit()
    ballpark_share_uses_the_1986_charts()
    defense_distribution_matches_monte_carlo()
    parks_are_the_twelve_printed_charts()
    synthetic_card_runs()
    tough_shift_changes_a_live_pa()
    resolve_uses_the_printed_table()
    print("pa sim tests passed")
