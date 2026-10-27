"""Rules-accurate plate appearance simulator.

Reads a pitcher 2d6 result, then a percentile 00-99, the way the Payoff
Pitch rulebook resolves an at-bat. This module is a test harness. It does
not write cards, rosters, or game results.

What the book specifies and this simulator does
- Percentile 00 is a rare play, not an out. Rare-play rows are mostly
  injury, weather, ejection, and rating checks. They are counted and left
  out of the rate denominator. The book does not give a league-average
  resolution of those rows.
- Faces 01-99 that miss a section's printed bands are outs.
- PATIENT-OUT: a walk or hit-by-pitch from PATIENT counts. Any other
  PATIENT reading is ignored and the play is an out.
- TOUGH-OUT: a face inside the SO band is a strikeout. A face greater
  than the SO band is an out, including a face that sits in a hit band.
  A face below the SO band keeps its printed result. The printed sentence
  only redirects faces greater than the SO range.
- BALLPARK: the home park's WHEELHOUSE faces send a re-roll to the
  batter's WHEELHOUSE section. The park's IN-PLAY faces send a re-roll
  to IN-PLAY.
- DEFENSE: a percentile picks the position and whether RANGE or ERROR is
  checked, then a re-roll reads that park section. A range hit uses the
  page-20 HIT chart. The ERR chart's SINGLE+error is a reached-on-error:
  an at-bat, not a hit, and not in AVG, OBP, or SLG. A dropped foul
  restarts the at-bat.
- %roll +10 or +20 (page 39) is added to the percentile on a plain TOUGH
  result before the TOUGH section is read. If the sum is greater than 99,
  the original face is used. The shift is not applied to TOUGH-OUT. The
  book names TOUGH only. Whether TOUGH-OUT takes the same shift is
  uncertain.

What this simulator deliberately leaves out
- Fatigue. A rate comparison uses a fresh pitcher.
- Baserunning strategy, hit-and-run, infield in, steals, bunts, and wild
  pitches. Those need runners. The rate line is bases empty, so a
  fielder's choice cannot occur and a wild pitch cannot occur.
- The optional supplemental strikeout rule that starts at 50 or 90. These
  cards store +10 or +20, which is the page-39 shift, not that rule.
- /IN-PLAY/ is not on these pitcher cards. The cross-era option would read
  it as a normal IN-PLAY.

League-average opposition is not defined in the rulebook. The simulator
draws the other side uniformly from the converted cards in data/cards.json,
and draws the home park uniformly from the 12 stadium charts printed in
the rulebook. The fielder on a DEFENSE check is a neutral Range C, Error 3
(the middle of each scale). That fielder is an assumption. The book does
not name a league-average park or a league-average defender.

The tournament tracker (engines/pitcher-v2/engine_v2.py and the site
Engines page) widens the hitter's SO band by the bump. That is the
opposite of the printed +10/+20 shift. This simulator follows the book.
It does not change the tracker.
"""
from __future__ import annotations

import json
import os
import random

from charts import D6_WEIGHTS, ERR_BY_D6, HIT_BY_D6, PARKS, POS_ERR_GROUP, POS_HIT_GROUP, defense_chart

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CARDS_PATH = os.path.join(ROOT, "data", "cards.json")

CHART = defense_chart()
D6_FACES = tuple(total for total, weight in zip(range(2, 13), D6_WEIGHTS) for _ in range(weight))
RESULT_KEYS = ("HR", "3B", "2B", "1B", "BB", "HBP", "SO")

# Absolute gaps that count as outliers once they also clear sampling noise.
HITTER_TOL = {"avg": 0.025, "obp": 0.025, "slg": 0.040, "hr": 0.010, "bb": 0.015, "so": 0.025}
PITCHER_TOL = {"k": 0.020, "bb": 0.015, "hr": 0.008, "h": 0.025}
NOISE_Z = 3.5


def shift_percentile(pct, bump):
    """Page 39. 00 is left alone so the rare-play check still sees it."""
    if not bump or pct == 0:
        return pct
    adjusted = pct + bump
    if adjusted > 99:
        return pct
    return adjusted


def section_faces(hand_table):
    """Faces 1-99. Index 0 stays None (the rare-play face)."""
    faces = [None] * 100
    if not hand_table:
        return faces
    for key in RESULT_KEYS:
        band = hand_table.get(key)
        if not band or len(band) < 2:
            continue
        lo, hi = int(band[0]), int(band[1])
        if hi < lo:
            continue
        for face in range(max(1, lo), min(99, hi) + 1):
            if faces[face] is None:
                faces[face] = key
    return faces


def so_hi_of(hand_table):
    band = (hand_table or {}).get("SO")
    if not band or len(band) < 2 or band[1] < band[0]:
        return None
    return int(band[1])


def read_section(faces, pct):
    if pct == 0:
        return "RARE"
    return faces[pct] or "OUT"


def read_patient_out(faces, pct):
    event = read_section(faces, pct)
    if event in ("BB", "HBP", "RARE"):
        return event
    return "OUT"


def read_tough_out(faces, so_hi, pct):
    if pct == 0:
        return "RARE"
    event = faces[pct]
    if event == "SO":
        return "SO"
    if so_hi is not None and pct > so_hi:
        return "OUT"
    return event or "OUT"


def ballpark_target(wh_hi, pct):
    """Which batter section a BALLPARK percentile re-rolls onto."""
    if pct == 0:
        return "RARE"
    if 1 <= pct <= wh_hi:
        return "WHEELHOUSE"
    return "IN-PLAY"


def defense_event(check, pos, d6, pct, hit_hi, err_hi, run):
    """One re-rolled defense check. pct is the park percentile, 0-99."""
    if pct == 0:
        # A park-check 00 is not inside a 1-99 HIT or ERR band. The book
        # defines 00 as a rare play on the initial roll. This re-roll is
        # not that roll. Count it as an out and let the caller flag it.
        return "OUT"
    if check == "RANGE":
        if pos == "C":
            pos = "CF"
        if pct > hit_hi:
            return "OUT"
        hit, dagger = HIT_BY_D6[d6][POS_HIT_GROUP[pos]]
        if dagger and run is not None and run >= 8:
            return "3B"
        return hit
    if pct > err_hi:
        return "OUT"
    event = ERR_BY_D6[d6][POS_ERR_GROUP[pos]]
    # SINGLE+error reaches base without a hit. It is an at-bat, so it
    # lowers AVG, and it is not in the OBP or SLG numerator.
    if event == "1B":
        return "ROE"
    return event


_PARKS_1986 = None
_DEFENSE_DIST = {}
_DEFENSE_EVENTS = ("1B", "2B", "3B", "HR", "OUT", "ROE", "REROLL")


def parks_1986():
    """The 26 park charts in the official 1986 card set.

    charts.PARKS stays the 12 stadiums printed in the rulebook. This list
    is the set the hitter engine and the 1986 accuracy check average over.
    """
    global _PARKS_1986
    if _PARKS_1986 is None:
        path = os.path.join(ROOT, "historical-cards", "reference", "ballparks.json")
        _PARKS_1986 = json.load(open(path))
    return _PARKS_1986


def ballpark_wheel_share(bats, parks=None):
    """P(WHEELHOUSE | BALLPARK) from park faces 1 through wh.

    Percentile 00 is a rare play on the initial roll, so the wheel share
    is wh/99. A switch hitter stands opposite the pitcher. The solver's
    hand split is 0.28 left-handed pitching, which is the right-handed
    column on the park card.
    """
    parks = parks_1986() if parks is None else parks
    n = float(len(parks))
    mean_l = sum(int(park["wh_l"]) for park in parks) / n / 99.0
    mean_r = sum(int(park["wh_r"]) for park in parks) / n / 99.0
    if bats == "L":
        return mean_l
    if bats == "R":
        return mean_r
    return 0.28 * mean_r + 0.72 * mean_l


def _defense_pct_split(check, pos, d6, hit_hi, err_hi, run):
    """Event shares over park percentiles 0-99. Percentile 0 is an out."""
    hi = hit_hi if check == "RANGE" else err_hi
    inside = max(0, min(99, int(hi)))
    shares = {"OUT": (1 + (99 - inside)) / 100.0}
    if inside:
        event = defense_event(check, pos, d6, 1, hit_hi, err_hi, run)
        shares[event] = shares.get(event, 0.0) + inside / 100.0
    return shares


def defense_distribution(parks=None, range_grade="C", error_grade="3"):
    """P(event | DEFENSE) for a neutral fielder, averaged over the parks.

    Position faces 1-99 are equal. The 2d6 weights are the 36 outcomes.
    Park percentile 0 and a miss of the range or error band are outs.
    'low' is run below 8. 'high' turns a dagger double into a triple.
    The seven events sum to 1. Dropped fouls stay REROLL; the caller
    renormalizes those out of a completed plate appearance.
    """
    parks = parks_1986() if parks is None else parks
    error_grade = str(error_grade)
    key = (
        range_grade,
        error_grade,
        tuple(
            (
                park.get("name"),
                int(park["wh_l"]),
                int(park["wh_r"]),
                int(park["range_hit_hi"][range_grade]),
                int(park["error_hi"][error_grade]),
            )
            for park in parks
        ),
    )
    cached = _DEFENSE_DIST.get(key)
    if cached is not None:
        return cached
    counts = {}
    for face in range(1, 100):
        slot = CHART[face]
        counts[slot] = counts.get(slot, 0) + 1
    n_parks = float(len(parks))
    low = {event: 0.0 for event in _DEFENSE_EVENTS}
    high = {event: 0.0 for event in _DEFENSE_EVENTS}
    for park in parks:
        hit_hi = int(park["range_hit_hi"][range_grade])
        err_hi = int(park["error_hi"][error_grade])
        for (check, pos), npos in counts.items():
            pos_p = npos / 99.0 / n_parks
            for d6, weight in zip(range(2, 13), D6_WEIGHTS):
                d6_p = weight / 36.0
                for run, bucket in ((7, low), (8, high)):
                    split = _defense_pct_split(check, pos, d6, hit_hi, err_hi, run)
                    mass = pos_p * d6_p
                    for event, share in split.items():
                        bucket[event] += mass * share
    for bucket in (low, high):
        total = sum(bucket.values())
        if abs(total - 1.0) > 1e-9:
            raise RuntimeError("defense distribution summed to %s" % total)
    result = {"low": low, "high": high}
    _DEFENSE_DIST[key] = result
    return result


class Tally:
    __slots__ = ("pa", "ab", "h", "tb", "bb", "hbp", "so", "hr", "rare", "reroll", "park00")

    def __init__(self):
        self.pa = 0
        self.ab = 0
        self.h = 0
        self.tb = 0
        self.bb = 0
        self.hbp = 0
        self.so = 0
        self.hr = 0
        self.rare = 0
        self.reroll = 0
        self.park00 = 0

    def add(self, event):
        if event == "RARE":
            self.rare += 1
            return
        if event == "REROLL":
            self.reroll += 1
            return
        if event == "PARK00":
            self.park00 += 1
            event = "OUT"
        self.pa += 1
        if event == "BB":
            self.bb += 1
            return
        if event == "HBP":
            self.hbp += 1
            return
        self.ab += 1
        if event == "OUT":
            return
        if event == "SO":
            self.so += 1
            return
        if event == "ROE":
            return
        self.h += 1
        if event == "1B":
            self.tb += 1
        elif event == "2B":
            self.tb += 2
        elif event == "3B":
            self.tb += 3
        elif event == "HR":
            self.tb += 4
            self.hr += 1

    def rates(self):
        ab = self.ab or 1
        pa = self.pa or 1
        h, bb, hbp = self.h, self.bb, self.hbp
        return {
            "avg": h / ab,
            "obp": (h + bb + hbp) / (self.ab + bb + hbp or 1),
            "slg": self.tb / ab,
            "hr": self.hr / pa,
            "bb": bb / pa,
            "so": self.so / pa,
            "pa": self.pa,
            "ab": self.ab,
            "rare": self.rare,
            "reroll": self.reroll,
            "park00": self.park00,
        }


def _bump(modifier):
    text = str(modifier or "NONE")
    if text in ("NONE", "None", ""):
        return 0
    return int(text.replace("+", ""))


def _stand(bats, throws):
    """LHB or RHB column on the park card. A switch hitter stands opposite the pitcher."""
    if bats == "L":
        return "L"
    if bats == "R":
        return "R"
    if throws == "L":
        return "R"
    return "L"


def _hand_key(throws):
    return "vsLHP" if throws == "L" else "vsRHP"


class Batter:
    __slots__ = ("key", "name", "bats", "run", "faces", "so_hi", "source")

    def __init__(self, key, card):
        bat = card["card_bat"]
        self.key = key
        self.name = card.get("name") or key
        self.bats = bat.get("bats") or "R"
        self.run = bat.get("run")
        self.faces = {}
        self.so_hi = {}
        for hand in ("vsLHP", "vsRHP"):
            self.faces[hand] = {}
            for section, table in bat["sections"].items():
                side = table.get(hand) or {}
                self.faces[hand][section] = section_faces(side)
                if section == "TOUGH":
                    self.so_hi[hand] = so_hi_of(side)
        self.source = _hitter_source(card.get("peak_bat") or {})


class Pitcher:
    __slots__ = ("key", "name", "throws", "bump", "table", "source")

    def __init__(self, key, card):
        pit = card["card_pit"]
        self.key = key
        self.name = card.get("name") or key
        self.throws = pit.get("throws") or "R"
        self.bump = _bump(pit.get("so_modifier"))
        self.table = [pit["table_2d6"][str(total)] for total in range(2, 13)]
        self.source = _pitcher_source(card.get("peak_pit") or {})


def _num(row, *keys):
    for key in keys:
        if key in row and row[key] is not None:
            return float(row[key])
    return None


def _hitter_source(row):
    ab = _num(row, "AB")
    h = _num(row, "H")
    if not ab or h is None:
        return None
    bb = _num(row, "BB") or 0.0
    hbp = _num(row, "HBP") or 0.0
    hr = _num(row, "HR") or 0.0
    doubles = _num(row, "2B") or 0.0
    triples = _num(row, "3B") or 0.0
    so = _num(row, "SO") or 0.0
    tb = h + doubles + 2 * triples + 3 * hr
    pa = ab + bb + hbp
    if pa <= 0:
        return None
    return {
        "avg": h / ab,
        "obp": (h + bb + hbp) / pa,
        "slg": tb / ab,
        "hr": hr / pa,
        "bb": bb / pa,
        "so": so / pa,
        "pa": pa,
        "ab": ab,
    }


def _pitcher_source(row):
    bf = _num(row, "bf", "BF")
    if not bf:
        return None
    return {
        "k": (_num(row, "so", "SO") or 0.0) / bf,
        "bb": (_num(row, "bb", "BB") or 0.0) / bf,
        "hr": (_num(row, "hr", "HR") or 0.0) / bf,
        "h": (_num(row, "h", "H") or 0.0) / bf,
        "bf": bf,
    }


def load_pool(path=CARDS_PATH):
    cards = json.load(open(path))
    batters = []
    pitchers = []
    for key, card in cards.items():
        bat = card.get("card_bat") or {}
        if bat.get("sections"):
            batters.append(Batter(key, card))
        pit = card.get("card_pit") or {}
        if pit.get("table_2d6"):
            pitchers.append(Pitcher(key, card))
    return batters, pitchers


def _roll_d6(rng):
    return D6_FACES[rng.randrange(36)]


def _roll_pct(rng):
    return rng.randrange(100)


def _section_event(batter, hand, section, pct, bump):
    if section == "TOUGH" and bump:
        pct = shift_percentile(pct, bump)
    if section == "TOUGH-OUT":
        return read_tough_out(batter.faces[hand]["TOUGH"], batter.so_hi[hand], pct)
    if section == "PATIENT-OUT":
        return read_patient_out(batter.faces[hand]["PATIENT"], pct)
    return read_section(batter.faces[hand][section], pct)


def _page11_strikeout(event, pct, so_range):
    """Optional page-11 rule. An out whose original percentile is inside
    the pitcher's printed SO range is recorded as a strikeout.

    The range is the number on the card (50-xx or 90-xx). It is not
    applied unless the caller passes it. The percentile is the original
    roll, including when a later park or defense roll was also thrown.
    Whether that later roll is the one the book means is uncertain; the
    sentence says 'the percentile dice result.'
    """
    if not so_range or event != "OUT":
        return event
    lo, hi = so_range
    if lo <= pct <= hi:
        return "SO"
    return event


def resolve_outcome(rng, batter, outcome, throws, bump, parks=PARKS, range_grade="C", error_grade="3", so_range=None):
    """One bases-empty plate appearance for a known pitcher result."""
    pct = _roll_pct(rng)
    hand = _hand_key(throws)
    if outcome in ("WHEELHOUSE", "PATIENT", "TOUGH", "IN-PLAY", "PATIENT-OUT", "TOUGH-OUT"):
        event = _section_event(batter, hand, outcome, pct, bump if outcome == "TOUGH" else 0)
        return _page11_strikeout(event, pct, so_range)
    if pct == 0:
        return "RARE"
    park = parks[rng.randrange(len(parks))]
    stand = _stand(batter.bats, throws)
    if outcome == "BALLPARK":
        target = ballpark_target(park["wh_l"] if stand == "L" else park["wh_r"], pct)
        if target == "RARE":
            return "RARE"
        event = _section_event(batter, hand, target, _roll_pct(rng), 0)
        return _page11_strikeout(event, pct, so_range)
    if outcome == "DEFENSE":
        check, pos = CHART[rng.randrange(1, 100)]
        event = _finish_defense(rng, batter, park, check, pos, range_grade, error_grade)
        return _page11_strikeout(event, pct, so_range)
    if outcome == "RANGE":
        _check, pos = CHART[rng.randrange(1, 100)]
        event = _finish_defense(rng, batter, park, "RANGE", pos, range_grade, error_grade)
        return _page11_strikeout(event, pct, so_range)
    if outcome == "ERROR":
        _check, pos = CHART[rng.randrange(1, 100)]
        event = _finish_defense(rng, batter, park, "ERROR", pos, range_grade, error_grade)
        return _page11_strikeout(event, pct, so_range)
    if outcome == "/IN-PLAY/":
        # Cross-era option on page 3. These tournament cards do not use it.
        event = _section_event(batter, hand, "IN-PLAY", pct, 0)
        return _page11_strikeout(event, pct, so_range)
    if outcome == "/PATIENT/":
        event = _section_event(batter, hand, "PATIENT", pct, 0)
        return _page11_strikeout(event, pct, so_range)
    return "RARE"


def resolve_pa(rng, batter, pitcher, parks=PARKS, range_grade="C", error_grade="3", so_range=None):
    """One bases-empty plate appearance. Returns an event token."""
    outcome = pitcher.table[_roll_d6(rng) - 2]
    return resolve_outcome(
        rng, batter, outcome, pitcher.throws, pitcher.bump,
        parks, range_grade, error_grade, so_range,
    )


def _finish_defense(rng, batter, park, check, pos, range_grade, error_grade):
    d6 = _roll_d6(rng)
    pct = _roll_pct(rng)
    if pct == 0:
        # The re-roll, not the initial roll. See defense_event.
        return "PARK00"
    hit_hi = park["range_hit_hi"][range_grade]
    err_hi = park["error_hi"][error_grade]
    return defense_event(check, pos, d6, pct, hit_hi, err_hi, batter.run)


def simulate_hitter(rng, batter, pitchers, n, parks=PARKS):
    tally = Tally()
    n_pit = len(pitchers)
    guard = 0
    while tally.pa < n and guard < n * 3:
        guard += 1
        pitcher = pitchers[rng.randrange(n_pit)]
        event = resolve_pa(rng, batter, pitcher, parks)
        if event == "REROLL":
            tally.reroll += 1
            continue
        tally.add(event)
    return tally


def simulate_pitcher(rng, pitcher, batters, n, parks=PARKS):
    tally = Tally()
    n_bat = len(batters)
    guard = 0
    while tally.pa < n and guard < n * 3:
        guard += 1
        batter = batters[rng.randrange(n_bat)]
        event = resolve_pa(rng, batter, pitcher, parks)
        if event == "REROLL":
            tally.reroll += 1
            continue
        tally.add(event)
    return tally


def _se(p, n):
    if n <= 0:
        return 1.0
    p = min(1.0, max(0.0, p))
    return (p * (1.0 - p) / n) ** 0.5


# Frozen hitter-solver category frequencies (hitter_solver.PITCHER_MIX),
# renormalized onto 10,000. The book does not define this mix. The same
# DEFENSE share is resolved with the position chart and the park card.
_SOLVER_WEIGHTS = (
    ("TOUGH", 3438),
    ("IN-PLAY", 2520),
    ("PATIENT", 2293),
    ("WHEELHOUSE", 342),
    ("BALLPARK", 900),
    ("DEFENSE", 507),
)
SOLVER_OUTCOMES = tuple(name for name, weight in _SOLVER_WEIGHTS for _ in range(weight))


def _absorb(tally, event):
    if event == "REROLL":
        tally.reroll += 1
        return False
    tally.add(event)
    return True


def simulate_hitter_solver_mix(rng, batter, n, parks=PARKS):
    """Hitter versus the frozen solver's category mix. No SO shift.

    Throwing hand is the solver's 0.28 left / 0.72 right. That split is
    the solver's constant, not a figure from the rulebook. The converted
    pitcher cards are 57 left and 152 right, which is the same neighborhood.
    """
    tally = Tally()
    guard = 0
    while tally.pa < n and guard < n * 3:
        guard += 1
        throws = "L" if rng.randrange(100) < 28 else "R"
        outcome = SOLVER_OUTCOMES[rng.randrange(10000)]
        event = resolve_outcome(rng, batter, outcome, throws, 0, parks)
        _absorb(tally, event)
    return tally


def _median(values):
    ordered = sorted(values)
    mid = len(ordered) // 2
    if not ordered:
        return 0.0
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _sd(values):
    if len(values) < 2:
        return 0.0
    center = _mean(values)
    return (sum((value - center) ** 2 for value in values) / (len(values) - 1)) ** 0.5


def _residual_outliers(rows, rate_keys, tols, group_rate=None, group_key=None):
    """Cards that miss by more than the crowd, past sampling noise.

    The bar for a rate is the larger of its absolute tolerance and two
    standard deviations of the gap across cards. Pitcher strikeouts can
    be centered on the median gap inside each SO-modifier group, because
    +10 and +20 move that rate as a class.
    """
    medians = {}
    spreads = {}
    for key in rate_keys:
        gaps = [row["gaps"][key] for row in rows]
        medians[key] = _median(gaps)
        spreads[key] = _sd(gaps)
    group_medians = {}
    if group_rate and group_key:
        buckets = {}
        for row in rows:
            buckets.setdefault(row[group_key], []).append(row["gaps"][group_rate])
        group_medians = {name: _median(gaps) for name, gaps in buckets.items()}
    outliers = []
    for row in rows:
        flags = []
        for key in rate_keys:
            gap = row["gaps"][key]
            if key == group_rate and group_medians:
                center = group_medians[row[group_key]]
            else:
                center = medians[key]
            residual = gap - center
            bar = max(tols[key], 2.0 * spreads[key])
            if abs(residual) >= bar and abs(gap) >= NOISE_Z * row["se"][key]:
                flags.append({
                    "rate": key,
                    "sim": round(row["sim"][key], 4),
                    "source": round(row["source"][key], 4),
                    "gap": round(gap, 4),
                    "residual": round(residual, 4),
                })
        if flags:
            item = {"card": row["card"], "name": row["name"], "flags": flags}
            for extra in ("throws", "so_modifier"):
                if extra in row:
                    item[extra] = row[extra]
            outliers.append(item)
    outliers.sort(key=lambda item: -max(abs(flag["residual"]) for flag in item["flags"]))
    summary = {}
    for key in rate_keys:
        gaps = [row["gaps"][key] for row in rows]
        summary[key] = {
            "mean_gap": round(_mean(gaps), 4),
            "median_gap": round(medians[key], 4),
            "sd_gap": round(spreads[key], 4),
        }
    return outliers, summary


def _hitter_record(batter, tally):
    sim = tally.rates()
    source = batter.source
    keys = ("avg", "obp", "slg", "hr", "bb", "so")
    den = {"avg": sim["ab"], "obp": sim["pa"], "slg": sim["ab"], "hr": sim["pa"], "bb": sim["pa"], "so": sim["pa"]}
    return {
        "card": batter.key,
        "name": batter.name,
        "sim": {key: sim[key] for key in keys},
        "source": {key: source[key] for key in keys},
        "gaps": {key: sim[key] - source[key] for key in keys},
        "se": {key: _se(sim[key], den[key]) for key in keys},
    }


def _pitcher_record(pitcher, tally):
    pa = tally.pa or 1
    sim = {"k": tally.so / pa, "bb": tally.bb / pa, "hr": tally.hr / pa, "h": tally.h / pa}
    source = pitcher.source
    keys = ("k", "bb", "hr", "h")
    return {
        "card": pitcher.key,
        "name": pitcher.name,
        "throws": pitcher.throws,
        "so_modifier": "+%d" % pitcher.bump if pitcher.bump else "NONE",
        "sim": sim,
        "source": {key: source[key] for key in keys},
        "gaps": {key: sim[key] - source[key] for key in keys},
        "se": {key: _se(sim[key], pa) for key in keys},
    }


def _modifier_summary(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row["so_modifier"], []).append(row["gaps"]["k"])
    return {mod: {"n": len(gaps), "mean_k_gap": round(_mean(gaps), 4)} for mod, gaps in sorted(grouped.items())}


def run_report(n=10000, seed=20261027, path=CARDS_PATH, progress=None):
    """Simulate every card. Returns a JSON-ready report. Does not write files.

    Two hitter environments:
    - pool: a uniform draw of the converted pitcher cards, with each card's
      printed +10/+20 applied as the rulebook shift.
    - solver_mix: the frozen hitter solver's category frequencies and its
      0.28/0.72 hand split, with no SO shift, and with BALLPARK and DEFENSE
      resolved from the printed charts.

    An outlier is a card whose gap on a rate is at least one tolerance away
    from the median gap on that rate, and larger than sampling noise. The
    median gap itself is the systematic miss.
    """
    rng = random.Random(seed)
    batters, pitchers = load_pool(path)
    rated_batters = [b for b in batters if b.source]
    rated_pitchers = [p for p in pitchers if p.source]
    pool_rows = []
    mix_rows = []
    for index, batter in enumerate(rated_batters):
        pool_rows.append(_hitter_record(batter, simulate_hitter(rng, batter, pitchers, n)))
        mix_rows.append(_hitter_record(batter, simulate_hitter_solver_mix(rng, batter, n)))
        if progress and index % 40 == 0:
            progress("hitter", index, len(rated_batters))
    pitcher_rows = []
    for index, pitcher in enumerate(rated_pitchers):
        pitcher_rows.append(_pitcher_record(pitcher, simulate_pitcher(rng, pitcher, batters, n)))
        if progress and index % 40 == 0:
            progress("pitcher", index, len(rated_pitchers))
    pool_out, pool_sum = _residual_outliers(pool_rows, HITTER_TOL, HITTER_TOL)
    mix_out, mix_sum = _residual_outliers(mix_rows, HITTER_TOL, HITTER_TOL)
    pit_out, pit_sum = _residual_outliers(
        pitcher_rows, PITCHER_TOL, PITCHER_TOL, group_rate="k", group_key="so_modifier")
    return {
        "seed": seed,
        "pa_per_card": n,
        "hitters_rated": len(rated_batters),
        "hitters_skipped_no_line": len(batters) - len(rated_batters),
        "pitchers_rated": len(rated_pitchers),
        "pitchers_skipped_no_line": len(pitchers) - len(rated_pitchers),
        "pool_gap_summary": pool_sum,
        "solver_mix_gap_summary": mix_sum,
        "pitcher_gap_summary": pit_sum,
        "pitcher_k_gap_by_modifier": _modifier_summary(pitcher_rows),
        "hitter_outliers_vs_pitcher_pool": pool_out,
        "hitter_outliers_vs_solver_mix": mix_out,
        "pitcher_outliers": pit_out,
        "environment": {
            "pool": "uniform draw from converted cards; page-39 shift on TOUGH",
            "solver_mix": "frozen PITCHER_MIX, hand 0.28/0.72, no SO shift, real park and defense charts",
            "parks": "12 stadium charts on rulebook pages 109-110, uniform",
            "defense": "Range C, Error 3",
            "rare_play": "00 counted and excluded from rates",
            "fatigue": "not applied",
            "outlier": "residual from the median gap (pitcher K: median inside the SO-modifier group) at least max(tolerance, 2 sd), and past sampling noise",
        },
    }


def _fmt_flags(flags):
    return ", ".join(
        "%s sim %.3f src %.3f gap %+.3f resid %+.3f" % (
            flag["rate"], flag["sim"], flag["source"], flag["gap"], flag["residual"])
        for flag in flags)


def summarize(report, limit=30):
    lines = ["PA per card %d, seed %d" % (report["pa_per_card"], report["seed"])]
    lines.append("hitters %d, pitchers %d" % (report["hitters_rated"], report["pitchers_rated"]))
    lines.append("pool median gaps: " + ", ".join(
        "%s %+.3f" % (key, report["pool_gap_summary"][key]["median_gap"]) for key in HITTER_TOL))
    lines.append("solver-mix median gaps: " + ", ".join(
        "%s %+.3f" % (key, report["solver_mix_gap_summary"][key]["median_gap"]) for key in HITTER_TOL))
    lines.append("pitcher median gaps: " + ", ".join(
        "%s %+.3f" % (key, report["pitcher_gap_summary"][key]["median_gap"]) for key in PITCHER_TOL))
    lines.append("K gap by modifier: " + ", ".join(
        "%s n=%d %+.3f" % (mod, info["n"], info["mean_k_gap"])
        for mod, info in report["pitcher_k_gap_by_modifier"].items()))
    lines.append("-- hitter outliers vs pitcher pool (%d) --" % len(report["hitter_outliers_vs_pitcher_pool"]))
    for row in report["hitter_outliers_vs_pitcher_pool"][:limit]:
        lines.append("%s %s: %s" % (row["card"], row["name"], _fmt_flags(row["flags"])))
    lines.append("-- hitter outliers vs solver mix (%d) --" % len(report["hitter_outliers_vs_solver_mix"]))
    for row in report["hitter_outliers_vs_solver_mix"][:limit]:
        lines.append("%s %s: %s" % (row["card"], row["name"], _fmt_flags(row["flags"])))
    lines.append("-- pitcher outliers (%d) --" % len(report["pitcher_outliers"]))
    for row in report["pitcher_outliers"][:limit]:
        lines.append("%s %s %s %s: %s" % (row["card"], row["name"], row["throws"], row["so_modifier"], _fmt_flags(row["flags"])))
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10000

    def _progress(kind, index, total):
        print("%s %d/%d" % (kind, index, total), flush=True)

    report = run_report(n=count, progress=_progress)
    out_path = os.path.join(os.path.dirname(__file__), "outliers.json")
    with open(out_path, "w") as handle:
        json.dump(report, handle, indent=1)
        handle.write("\n")
    print(summarize(report))
    print("wrote", out_path)
