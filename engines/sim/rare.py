"""Rare-play cells transcribed from rulebook pages 22-30.

A 00 on the first percentile is a rare play (page 4). The simulator
re-rolls the percentile and looks up the cell. Cells listed here are
the ones whose baseball result is stated in a single way. A cell that
is not listed is a gap: the log quotes that the chart was not
transcribed, and the at-bat is rolled again. Replaying is not in the
book. It only lets a test game finish.

Stateful sentences (the strike zone changes for the rest of the game,
extra outs, rain postponements, suspensions) are flagged even when a
result for this at-bat is applied. Those lasting effects are not all
modeled.
"""
from __future__ import annotations

# (bases_empty, section, lo, hi, event, note)
# section is the pitcher result family: WHEEL, PATIENT, TOUGH, IN-PLAY, DEFENSE.
CELLS = (
    (True, "WHEEL", 0, 5, "NO_PLAY", "Pitcher must leave. Check him for injury. Page 22."),
    (True, "WHEEL", 6, 13, "CATCHER_FOUL", "Foul ball hits the catcher. Check him for injury. The at-bat is not given a result. Page 22."),
    (True, "WHEEL", 14, 16, "RUN6_OUT_OR_1B", "Line drive off the pitcher. RUN 6 or less is out; 7 or more is a single. Check the pitcher. Page 22."),
    (True, "WHEEL", 17, 26, "OUT_REMOVE", "Groundout to SS. Batter must leave. Check him for injury. Page 22."),
    (True, "WHEEL", 27, 56, "WEATHER", "Rain or a roof power outage. 1d6: 1-2 no effect, 3-4 both pitchers leave, 5-6 postponed if the game is official. Page 22."),
    (True, "WHEEL", 57, 66, "RUN5_1B_OR_2B_OUT3", "Misplayed liner to right. RUN 5 or less is a single. RUN 6 or more reaches second and is out at third. Page 22."),
    (True, "WHEEL", 67, 76, "HR_UNLESS_CF_A", "Deep drive. CF range A is an out. Otherwise a home run. Page 22."),
    (True, "WHEEL", 77, 79, "OUT", "Fair grounder down the line. Batter does not run and is thrown out by the RF. Page 22."),
    (True, "WHEEL", 80, 86, "OUT_UNLESS_NOT_LF_A", "Sinking liner. LF range A is an out. Otherwise a single, runners advance 1. Page 22."),
    (True, "WHEEL", 87, 91, "2B", "Ground-rule double, or a double when the ball hits a bird. Page 22."),
    (True, "WHEEL", 92, 96, "OUT", "Single to right, then the batter is tagged out in a rundown. Page 22."),
    (True, "WHEEL", 97, 99, "OUT", "Batter does not run and is thrown out 7-4-3. Page 22."),
    (True, "PATIENT", 0, 5, "NO_PLAY", "Pitcher must leave. Check him for injury. Page 22."),
    (True, "PATIENT", 6, 12, "BB", "Walk. Catcher is ejected. Page 22."),
    (True, "PATIENT", 13, 24, "BB", "Walk. Pitcher is ejected. Page 22."),
    (True, "PATIENT", 25, 30, "SO", "Strikeout. Batter is ejected. Page 22."),
    (True, "PATIENT", 31, 46, "HBP", "Hit by pitch. A later hit by pitch can eject the pitcher. That later effect is not modeled. Page 22."),
    (True, "PATIENT", 47, 68, "HBP", "Hit by pitch and a mound charge. The suspension is not applied beyond this game. Page 22."),
    (True, "TOUGH", 0, 5, "SO", "Strikeout while checking a swing. Check the batter for injury. Page 23."),
    (True, "TOUGH", 6, 12, "SO", "Strikeout. Batter is ejected. Page 23."),
    (True, "TOUGH", 45, 64, "SO_DROP", "Strikeout, ball gets past the catcher. 2d6 versus RUN decides if the batter is safe. Page 23."),
    (True, "IN-PLAY", 6, 11, "1B", "Ball off the pitcher's leg. Single. Check the pitcher. Page 24."),
    (True, "DEFENSE", 94, 96, "REROLL", "Dropped foul. Restart the at-bat. Page 26."),
    (True, "DEFENSE", 97, 99, "REROLL", "Foul ball. Restart the at-bat. Check the first baseman. Page 26."),
    (False, "WHEEL", 70, 79, "1B", "Lost in the sun or the lights. Single, and runners advance 2. Page 27."),
)


def family(pitcher_result):
    text = pitcher_result or ""
    if "WHEEL" in text or text == "BALLPARK":
        return "WHEEL"
    if "PATIENT" in text:
        return "PATIENT"
    if "TOUGH" in text:
        return "TOUGH"
    if "IN-PLAY" in text or text == "INPLAY":
        return "IN-PLAY"
    if text in {"DEFENSE", "RANGE", "ERROR"}:
        return "DEFENSE"
    return "WHEEL"


def lookup(bases_empty, pitcher_result, pct):
    fam = family(pitcher_result)
    for empty, section, lo, hi, event, note in CELLS:
        if empty == bases_empty and section == fam and lo <= pct <= hi:
            return {"event": event, "note": note, "coded": True, "section": fam}
    return {
        "event": "UNCODED",
        "note": (
            "Rare-play cell is not transcribed. Pages 22-30. "
            "Section %s, percentile %02d, bases %s. The at-bat is rolled again, which the book does not say to do."
            % (fam, pct, "empty" if bases_empty else "occupied")
        ),
        "coded": False,
        "section": fam,
    }
