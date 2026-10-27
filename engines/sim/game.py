"""One Payoff Pitch game from the rulebook.

This does not read or write tournament_results.json. A lineup is taken
from data/rosters.json and the cards from data/cards.json. Rolls are
logged. Where the book offers a choice, the choice is a toggle and the
log names it. Where the book does not say, the log says so.

The default draw is the Fast Action Card deck printed on rulebook pages
40-71 (fac=True). The 1986 season card PDF has no FAC sheets. Running
then uses the card's SINGLE and DOUBLE lines (pages 13-14). fac=False
keeps the dice. Basic running is pages 5-6 and 16. Advanced running is
running="advanced".
"""
from __future__ import annotations

import json
import os
import random

from book import (
    ADV_DOUBLE_FIRST,
    ADV_SINGLE_FIRST,
    ADV_SINGLE_SECOND,
    DEFENSE_OUT,
    ERR_BY_D6,
    FATIGUE_PATIENT,
    FLY_OUTS,
    GROUND_OUTS,
    HIT_BY_D6,
    LINE_OUTS,
    OUT_POS,
    POP_OUTS,
    POS_ERR_GROUP,
    POS_HIT_GROUP,
    STEAL_COLUMN,
    defense_slot,
    fatigue_patient,
    fatigue_tough,
    hit_fielder,
    injury_result,
    out_type,
    pickoff_result,
    sac_result,
    section_faces,
    steal_result,
    wp_hit,
)
from charts import PARKS
from fac import (
    WP_READING,
    Deck,
    FacRolls,
    parse_err_cell,
    parse_hit_cell,
    parse_out_cell,
    parse_runner_line,
)
from rare import lookup as rare_lookup

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Home park is the 1986 card in historical-cards/reference/ballparks.json
# when that stadium is also one of the 12 charts printed in the rulebook.
# Fenway's faces match charts.PARKS. A club with no 1986 park card is refused.
HOME_PARK = {
    "ATL": "ATLANTA-FULTON COUNTY STADIUM",
    "BAL": "MEMORIAL STADIUM",
    "BOS": "FENWAY PARK",
    "CHC": "WRIGLEY FIELD",
    "CIN": "RIVERFRONT STADIUM",
    "CLE": "CLEVELAND STADIUM",
    "CWS": "COMISKEY PARK",
    "DET": "TIGER STADIUM",
    "HOU": "ASTRODOME",
    "KC": "ROYALS STADIUM",
    "LAA": "ANAHEIM STADIUM",
    "LAD": "DODGER STADIUM",
    "MIL": "COUNTY STADIUM",
    "MIN": "HUBERT H HUMPHREY METRODOME",
    "MON": "STADE OLYMPIQUE",
    "NYM": "SHEA STADIUM",
    "NYY": "YANKEE STADIUM",
    "OAK": "OAKLAND COLISEUM",
    "PHI": "VETERANS STADIUM",
    "PIT": "THREE RIVERS STADIUM",
    "SD": "JACK MURPHY STADIUM",
    "SEA": "KINGDOME",
    "SF": "CANDLESTICK PARK",
    "STL": "BUSCH STADIUM",
    "TEX": "ARLINGTON STADIUM",
    "TOR": "EXHIBITION STADIUM",
    # No 1986 card exists for these clubs; the 2024 Season PDF park cards are used.
    "ARI": "CHASE FIELD",
    "COL": "COORS FIELD",
    "MIA": "LOANDEPOT PARK",
    "TB": "TROPICANA FIELD",
    "WSH": "NATIONALS PARK",
}


class Dice:
    def __init__(self, rng):
        self.rng = rng
        self.trace = []

    def d6(self):
        value = self.rng.randint(1, 6)
        self.trace.append("d6=%d" % value)
        return value

    def d10(self):
        value = self.rng.randint(0, 9)
        self.trace.append("d10=%d" % value)
        return value

    def pair(self):
        one, two = self.d6(), self.d6()
        return one, two, one + two

    def pct(self):
        tens, ones = self.d10(), self.d10()
        value = tens * 10 + ones
        self.trace.append("pct=%02d" % value)
        return value

    def take(self):
        done = self.trace
        self.trace = []
        return done


def _hand_key(throws):
    return "vsLHP" if throws == "L" else "vsRHP"


def _stand(bats, throws):
    if bats == "L":
        return "L"
    if bats == "R":
        return "R"
    return "R" if throws == "L" else "L"


def _player(roster_row, card):
    bat = (card or {}).get("card_bat") or {}
    pit = (card or {}).get("card_pit") or {}
    return {
        "id": roster_row["id"],
        "name": roster_row["name"],
        "pos": roster_row["pos"],
        "slot": roster_row["slot"],
        "group": roster_row["group"],
        "bats": bat.get("bats") or "R",
        "bat": bat,
        "pit": pit,
        "run": bat.get("run"),
        "steal": bat.get("steal") or {},
        "dp": bat.get("dp"),
        "sac": bat.get("sac_bunt"),
        # Pitcher cards carry their own FIELDING line (card_pit.fielding, the
        # 1986 pitcher-card range/error); a batting card's positions come first.
        "positions": bat.get("positions") or pit.get("fielding") or [],
        "fielding_label": bat.get("fielding"),
        "out_table": bat.get("out_table") or [],
        "sections": bat.get("sections") or {},
        "throws": pit.get("throws"),
        "table": pit.get("table_2d6") or {},
        "special": set(pit.get("special") or []),
        "stamina": pit.get("stamina") or {},
        "addendum": pit.get("addendum") or {},
        "so_modifier": pit.get("so_modifier") or "NONE",
        "so_band": pit.get("so_band"),
        "removed": False,
    }


def load_club(code, rosters=None, cards=None):
    if rosters is None:
        rosters = json.load(open(os.path.join(ROOT, "data", "rosters.json")))
    if cards is None:
        cards = json.load(open(os.path.join(ROOT, "data", "cards.json")))
    roster = rosters[code]
    people = []
    for row in roster["players"]:
        card = cards.get("%s|%s" % (code, row["id"]))
        if card is None:
            raise SystemExit("no card for %s %s" % (code, row["id"]))
        people.append(_player(row, card))
    return {
        "code": code,
        "name": roster["name"],
        "people": people,
        "lineup": [p for p in people if p["group"] == "lineup"],
        "rotation": [p for p in people if p["group"] == "rotation"],
        "bullpen": [p for p in people if p["group"] == "bullpen"],
        "bench": [p for p in people if p["group"] == "bench"],
    }


# No official park card exists for these clubs. A labelled stand-in is used
# and every game log names it as a stand-in.
STAND_IN_PARK = {
    "PHA": ("VETERANS STADIUM", "Stand-in: no Shibe Park / Connie Mack Stadium card exists in the 1986 or 2024 sets; the 1986 Philadelphia (N) Veterans Stadium card is used."),
}


def park_for(code):
    if code in STAND_IN_PARK and code not in HOME_PARK:
        base_name, note = STAND_IN_PARK[code]
        HOME_PARK[code] = base_name
        try:
            park = park_for(code)
        finally:
            del HOME_PARK[code]
        if park is None:
            return None
        park = dict(park)
        park["season"] = "%s (STAND-IN for %s)" % (park.get("season", ""), code)
        park["stand_in"] = note
        return park
    name = HOME_PARK.get(code)
    if not name:
        return None
    for park in PARKS:
        if park["name"] == name:
            return park
    # 1986 cards first; ballparks_2024.json holds the 2024 Season PDF cards
    # for clubs that have no 1986 park (ARI, COL, MIA, TB, WSH).
    for fname in ("ballparks.json", "ballparks_2024.json"):
        path = os.path.join(ROOT, "historical-cards", "reference", fname)
        for park in json.load(open(path)):
            if park["name"] == name:
                return park
    return None


class Game:
    def __init__(self, home, away, seed=1, **opts):
        self.home = home
        self.away = away
        self.rng = random.Random(seed)
        self.plain = Dice(self.rng)
        self.seed = seed
        passed_running = "running" in opts
        self.opts = {
            "fac": True,
            "running": "basic",
            "steal": "auto",
            "bunt_policy": True,
            "hit_and_run": True,
            "infield_in": True,
            "supplemental_so": True,  # page 11 optional rule, owner choice 2026-10-27
            "tough_shift": True,
            "slash_in_play": "normal",
            "zero_hr": False,
            # Usage, not a rule (owner choice 2026-10-27): "manager" pulls a
            # fatigued or struggling starter, lets him go his Start rating, and
            # uses the closer in a save spot. "book" keeps the old behaviour
            # (a reliever only after a starter tires, at the end of a half).
            "bullpen": "manager",
        }
        self.opts.update(opts)
        if self.opts["fac"]:
            self.deck = Deck(self.rng)
            self.dice = FacRolls(self.deck)
            if not passed_running:
                self.opts["running"] = "fac"
        else:
            self.deck = None
            self.dice = self.plain
        self.fac_result_card = None
        self.wp_seen = 0
        self.wp_fired = 0
        self.wp_miss = 0
        self.wp_empty = 0
        self.wp_no_rating = 0
        self.wp_unmarked = 0
        self._wp_reroll_gap_said = False
        self._in_wild_reroll = False
        if self.deck:
            self.deck.on_draw = self._on_fac_draw
        self.park = park_for(home["code"])
        if self.park is None:
            raise SystemExit("no ballpark card for " + home["code"])
        self.log = []
        self.gaps = []
        self.inning = 1
        self.half = "top"
        self.outs = 0
        self.bases = [None, None, None]
        self.score = {away["code"]: 0, home["code"]: 0}
        self.order_index = {away["code"]: 0, home["code"]: 0}
        self.batting = away
        self.fielding = home
        self.pitcher = {}
        self.defense = {}
        self.box = {}
        self.pitch_box = {}
        self.notes = []
        self._resp = {}        # runner id -> pitcher box key responsible for him
        self._ue = set()       # runner ids who reached on an error (their run is unearned)
        self._half_err = 0     # errors this half (earned-run reconstruction)
        self._pa = None        # the plate appearance in progress (RBI)
        self._no_rbi = 0       # >0 inside a steal, pickoff or wild pitch
        self._entries = []     # pitcher appearances for W/L/S/H
        self._lead_runs = []   # (scoring team, run number, W candidate key, responsible key)
        self._scorer_wraps()
        self.hr_called = {away["code"]: False, home["code"]: False}
        self.over = False
        self.postponed = False
        self.jump_seen = set()
        self.jump_closed = set()
        self._patient_out = False
        self._tough_out = False
        for club in (home, away):
            self._start_pitcher(club)
            self._align(club)

    def say(self, text):
        self.log.append(text)

    def gap(self, text):
        if text not in self.gaps:
            self.gaps.append(text)
        self.say("GAP: " + text)

    def _start_pitcher(self, club):
        arm = club["rotation"][0]
        self.pitcher[club["code"]] = {
            "player": arm,
            "runs": 0,
            "innings": set(),
            "outs": 0,
            "fatigued": False,
            "batters": 0,
        }
        self._enter(club["code"], arm)
        start = (arm["stamina"] or {}).get("start")
        if start is None:
            self.gap(
                "%s has no Start stamina. Pages 10-11 cannot say when he tires."
                % arm["name"]
            )

    def _align(self, field_club):
        """One fielder per position. A second player at a position does not field."""
        taken = {}
        dh = []
        for batter in field_club["lineup"]:
            pos = batter["pos"]
            if pos == "DH":
                dh.append(batter)
                continue
            if pos in taken:
                dh.append(batter)
                self.gap(
                    "%s is listed at %s and so is %s. The rulebook does not say who fields. %s does not field."
                    % (batter["name"], pos, taken[pos]["name"], batter["name"])
                )
                continue
            taken[pos] = batter
        self.defense[field_club["code"]] = taken
        self.dh_names = getattr(self, "dh_names", {})
        self.dh_names[field_club["code"]] = [p["name"] for p in dh]

    def _side(self):
        return self.batting if self.half == "top" else self.fielding

    def play(self):
        self.say(
            "%s at %s. Park %s (%s). Seed %s. Running %s."
            % (
                self.away["name"], self.home["name"], self.park["name"],
                self.park.get("season", ""), self.seed, self.opts["running"],
            )
        )
        if self.park.get("stand_in"):
            self.say(self.park["stand_in"])
            self.gap(self.park["stand_in"])
        self.say(
            "The rulebook never defines a designated hitter. Any lineup hitter may be the DH and the pitcher does not bat, because these rosters list nine hitters."
        )
        self.say(
            "No card stores the page 11 save symbol (#, †, or +). That relief exception is not applied."
        )
        self.say(
            "No card stores the page 39 dagger after the steal letter. A catcher arm of 1 or 2 is not rewritten to 3."
        )
        if self.deck:
            self.say(
                "Fast Action Cards replace the dice (pages 12-15). The deck is the 256 cards on rulebook pages 40-71. The 1986 season card PDF has no FAC sheets."
            )
            self.gap(WP_READING)
            self.gap(
                "Three cards say to use the previous card's 1d6 (1-3 out, check the runner; 4-6 safe, check the fielder). Their HOME line is only a position letter, so it is not read as a play."
            )
            self.gap(
                "Every card has a HOME line. Pages 12-15 do not say when to read it. A play at home uses the page 19 chart, and the next card supplies the 2d6 and the percentile."
            )
        else:
            self.gap(
                "This game uses dice. Fast Action Cards are the other official method (pages 12-15). Pass fac=True to draw the deck."
            )
        while self.inning <= 30:
            for half, batting, fielding in (
                ("top", self.away, self.home),
                ("bottom", self.home, self.away),
            ):
                if half == "bottom" and self.inning >= 9 and self.score[self.home["code"]] > self.score[self.away["code"]]:
                    self.say("Home leads after %d. The bottom is not played." % self.inning)
                    break
                self.half = half
                self.batting = batting
                self.fielding = fielding
                self.outs = 0
                self.bases = [None, None, None]
                self.say("— %s %d. %s bats. %s pitches. Score %s %d, %s %d." % (
                    half, self.inning, batting["code"],
                    self.pitcher[fielding["code"]]["player"]["name"],
                    self.away["code"], self.score[self.away["code"]],
                    self.home["code"], self.score[self.home["code"]],
                ))
                self._half()
                if self.over:
                    break
            if self.over:
                break
            if self.inning >= 9 and self.score[self.home["code"]] != self.score[self.away["code"]]:
                break
            if self.inning >= 9 and self.score[self.home["code"]] == self.score[self.away["code"]]:
                self.gap(
                    "The book never says how a tie after nine is finished. Play continues one inning at a time until one side leads after a full inning. No runner is placed on second."
                )
            if self.inning >= 30 and self.score[self.home["code"]] == self.score[self.away["code"]]:
                self.gap("Safety stop at 30 innings. The book does not set a limit.")
                break
            if self.deck and self.inning % 3 == 0:
                reason = "Recommended reshuffle after three full innings (page 12). Inning %d is complete." % self.inning
                self.deck.reshuffle(reason)
                self.say(reason)
                self.deck.take()
            self.inning += 1
        if self.postponed:
            self.say("Postponed. The line is not a finished game.")
        if self.deck:
            self.say(
                "WP? drawn %d. Fired %d. Missed the rating %d. Bases empty %d. No WP rating %d. Page-10 wild pitches on a card with no WP? mark %d."
                % (
                    self.wp_seen, self.wp_fired, self.wp_miss,
                    self.wp_empty, self.wp_no_rating, self.wp_unmarked,
                )
            )
        self.say("Final %s %d, %s %d." % (
            self.away["code"], self.score[self.away["code"]],
            self.home["code"], self.score[self.home["code"]],
        ))
        return self.report()

    def _half(self):
        self._ue.clear()
        self._resp.clear()
        self._half_err = 0
        while self.outs < 3:
            self._substitute_removed()
            self._maybe_change_pitcher(before_batter=True)
            self._plate()
        state = self.pitcher[self.fielding["code"]]
        state["innings"].add(self.inning)
        self._mark_fatigue(state, end_of_half=True)
        self._maybe_change_pitcher(before_batter=False)

    def _plate(self):
        batter = self.batting["lineup"][self.order_index[self.batting["code"]] % 9]
        outer = self._pa
        self._pa = {"batter": batter, "rbi": [], "outs0": self.outs, "log0": len(self.log), "on_error": False}
        self._resp[batter["id"]] = self._pkey()
        self._ue.discard(batter["id"])
        try:
            self._plate_inner()
        finally:
            pa, self._pa = self._pa, outer
            self._settle_rbi(pa)

    def _plate_inner(self):
        club = self.batting
        idx = self.order_index[club["code"]] % 9
        batter = club["lineup"][idx]
        self.order_index[club["code"]] += 1
        state = self.pitcher[self.fielding["code"]]
        pitcher = state["player"]
        state["batters"] += 1
        state["innings"].add(self.inning)
        self._pitch_line(bf=1)
        self._mark_fatigue(state, end_of_half=False)
        if self.opts["steal"] == "hold":
            self._hold_steal()
            if self.outs >= 3:
                return
        situation = self._situation()
        self.say("%s (%s) vs %s. %s." % (batter["name"], batter["pos"], pitcher["name"], situation))
        if self._try_bunt(batter, pitcher):
            return
        if self.deck:
            self._plate_fac(batter, pitcher)
            return
        one, two, total = self.dice.pair()
        pct = self.dice.pct()
        rolls = self.dice.take()
        result = str(pitcher["table"].get(str(total), "IN-PLAY"))
        self.say("Roll %s. 2d6 %s -> %s." % (", ".join(rolls), self._fmt(one, two, total), result))
        pct = self._wild_pitch(pitcher, pct)
        if pct == 0:
            self._rare(batter, pitcher, result, one, two)
            return
        reading = self._pitch_reading(batter, pitcher, result, pct)
        if self.opts["hit_and_run"] and self._want_hit_and_run(batter):
            self._hit_and_run(batter, pitcher, reading, pct, one, two, total)
            return
        self._apply_reading(batter, pitcher, reading, pct, one, two, total, False)

    def _plate_fac(self, batter, pitcher):
        """One card for the pitcher 2d6, then a card for the percentile. Page 13."""
        card = self.deck.draw("pitch")
        total = card["d6_2"]
        result = str(pitcher["table"].get(str(total), "IN-PLAY"))
        self.say("FAC pitch. 2d6=%s -> %s. Rolls %s." % (total, result, ", ".join(self.deck.take())))
        one = two = None
        fatigued = self.pitcher[self.fielding["code"]]["fatigued"]
        needs_pct = result not in {"BALLPARK", "DEFENSE", "RANGE", "ERROR"} or (
            result == "BALLPARK" and fatigued
        )
        pct = None
        if needs_pct:
            pct_card = self.deck.draw("batter")
            pct = pct_card["pct"]
            self.fac_result_card = pct_card
            self.say(
                "FAC percentile %02d. This card's 2d6 is %s. Rolls %s."
                % (pct, pct_card["d6_2"], ", ".join(self.deck.take()))
            )
            pct = self._wild_pitch(pitcher, pct)
            if pct == 0:
                self._rare(batter, pitcher, result, one, two)
                return
        reading = self._pitch_reading(batter, pitcher, result, pct)
        if self.opts["hit_and_run"] and self._want_hit_and_run(batter):
            self._hit_and_run(batter, pitcher, reading, pct, one, two, total)
            return
        self._apply_reading(batter, pitcher, reading, pct, one, two, total, False)

    def _restart_at_bat(self):
        """The at-bat starts over (dropped foul, rare-play replay, delay).
        The same batter comes up again, so the first try is not a batter faced."""
        self.order_index[self.batting["code"]] -= 1
        state = self.pitcher.get(self.fielding["code"])
        if state:
            state["batters"] -= 1
        self._pitch_line(bf=-1)

    def _fmt(self, one, two, total):
        if one is None:
            return "2d6=%s" % total
        return "%d+%d=%d" % (one, two, total)

    def _is_doubles(self, one, two, why):
        if one is not None:
            return one == two
        left, right = self.plain.d6(), self.plain.d6()
        self.gap(
            "%s needs doubles. A Fast Action Card prints the 2d6 total and not the two dice (pages 12-13). Two dice are rolled for that check. Page 15 allows dice with the deck."
            % why
        )
        self.say("Doubles check %d and %d. Rolls %s." % (left, right, ", ".join(self.plain.take())))
        return left == right

    def _low_die(self, one, two):
        if one is not None:
            return min(one, two)
        left, right = self.plain.d6(), self.plain.d6()
        self.gap(
            "Advanced running uses the lower die (page 16). A Fast Action Card prints only the 2d6 total. Two dice are rolled for that die. Page 15 allows it."
        )
        self.say("Low die from %d and %d. Rolls %s." % (left, right, ", ".join(self.plain.take())))
        return min(left, right)

    def _situation(self):
        names = []
        for base, label in ((0, "1st"), (1, "2nd"), (2, "3rd")):
            if self.bases[base]:
                names.append(self.bases[base]["name"] + " on " + label)
        occupied = ", ".join(names) if names else "bases empty"
        return "%d out, %s" % (self.outs, occupied)

    def _mark_fatigue(self, state, end_of_half):
        player = state["player"]
        stamina = player["stamina"] or {}
        runs = state["runs"]
        if runs >= 6 and not state["fatigued"]:
            state["fatigued"] = True
            self.say("%s has allowed %d runs and is fatigued (page 10)." % (player["name"], runs))
            return
        start = stamina.get("start")
        relief = stamina.get("relief")
        if start and self.inning >= int(start) and runs >= 3 and not state["fatigued"]:
            state["fatigued"] = True
            self.say(
                "%s reached inning %s of his Start rating with %d runs and is fatigued (pages 10-11)."
                % (player["name"], start, runs)
            )
        if relief == "Short" and not state["fatigued"]:
            if runs >= 2:
                state["fatigued"] = True
                self.say("%s (Short relief) has allowed 2 runs and is fatigued (page 11)." % player["name"])
            elif end_of_half and len(state["innings"]) >= 2:
                state["fatigued"] = True
                self.say("%s (Short relief) has finished a second inning and is fatigued (page 11)." % player["name"])
        if relief == "Long" and not state["fatigued"]:
            if runs >= 3:
                state["fatigued"] = True
                self.say("%s (Long relief) has allowed 3 runs and is fatigued (page 11)." % player["name"])
            elif end_of_half and len(state["innings"]) >= 3:
                state["fatigued"] = True
                self.say("%s (Long relief) has finished a third inning and is fatigued (page 11)." % player["name"])

    def _maybe_change_pitcher(self, before_batter):
        """Usage is not a rule. The book says a tired pitcher uses the fatigue card and may stay."""
        state = self.pitcher[self.fielding["code"]]
        player = state["player"]
        stamina = player["stamina"] or {}
        relief = stamina.get("relief")
        remove = False
        reason = ""
        if not before_batter and relief == "Short" and len(state["innings"]) >= 1 and state["outs"] >= 3:
            remove = True
            reason = "Short relief has finished an inning. Page 11 says that is the normal outing. Removing him is a usage choice."
        if not before_batter and relief == "Long" and len(state["innings"]) >= 3:
            remove = True
            reason = "Long relief has pitched 3 innings. Page 11 says 1-3 is the normal outing."
        if not before_batter and state["fatigued"] and stamina.get("start"):
            remove = True
            reason = "Starter is fatigued at the end of a half-inning. The book lets him stay on the fatigue card. This game brings in a reliever."
        if player["removed"]:
            remove = True
            reason = "The pitcher was removed by a play."
        if not remove:
            why = self._usage_reason(before_batter)
            if why:
                remove, reason = True, why
        if not before_batter and self._no_more_batters():
            return
        code = self.fielding["code"]
        pending = getattr(self, "_pending_change", {})
        self._pending_change = pending
        if not remove and before_batter and code in pending:
            remove, reason = True, pending[code]
        if not remove:
            return
        if not before_batter:
            # Decided at the end of the half. The reliever is brought in when
            # his side next takes the field, so a game that ends first does
            # not give him an appearance with no batter faced.
            pending[code] = reason
            return
        pending.pop(code, None)
        # A pitcher who has left cannot come back in the same game.
        self._pitched = getattr(self, "_pitched", {})
        gone = self._pitched.setdefault(code, set())
        gone.add(player["id"])
        pen = [p for p in self.fielding["bullpen"] if not p["removed"] and p["id"] not in gone]
        if not pen:
            self.gap("%s stays in. The bullpen has no remaining arm. The book does not name a replacement." % player["name"])
            return
        nxt = self._pick_reliever(pen)
        if (nxt["stamina"] or {}).get("relief") is None and (nxt["stamina"] or {}).get("start") is None:
            self.gap("%s has no relief stamina. He enters anyway. Pages 10-11 do not say when he tires." % nxt["name"])
        self.pitcher[self.fielding["code"]] = {
            "player": nxt, "runs": 0, "innings": set(), "outs": 0, "fatigued": False, "batters": 0,
        }
        self._pitch_line()
        self._enter(self.fielding["code"], nxt)
        self.say("Pitching change: %s replaces %s. %s" % (nxt["name"], player["name"], reason))

    # ---- official scoring (owner ruling 2026-10-27) ----------------------
    def _pkey(self, code=None):
        code = code or self.fielding["code"]
        state = self.pitcher.get(code)
        return code + "|" + state["player"]["id"] if state else None

    def _scorer_wraps(self):
        """Runs that score inside a steal, pickoff, wild pitch or balk are
        not batted in (rule 9.04(b))."""
        for name in ("_wild_pitch", "_wild_reroll", "_resolve_steal", "_auto_steal", "_hold_steal",
                     "_pickoff_runner", "_pickoff", "_fac_steal_error", "_fac_steal_drop"):
            orig = getattr(self, name, None)
            if orig is None:
                continue

            def wrap(*a, _o=orig, **k):
                self._no_rbi += 1
                try:
                    return _o(*a, **k)
                finally:
                    self._no_rbi -= 1
            setattr(self, name, wrap)

    def _run_scores(self, runner):
        """One run: score, the current pitcher's fatigue count (pages 10-11
        count runs while he pitches), the responsible pitcher's R and ER
        (rules 9.16), and the batter's RBI (rule 9.04)."""
        code = self.batting["code"]
        self.score[code] += 1
        self.pitcher[self.fielding["code"]]["runs"] += 1
        self._line_id(code, runner["id"], r=1)
        resp = self._resp.pop(runner["id"], None) or self._pkey()
        # Earned unless the runner reached on an error, or the inning would
        # already have ended had the errors been outs (rule 9.16(a)).
        earned = runner["id"] not in self._ue and self.outs + self._half_err < 3
        self._ue.discard(runner["id"])
        row = self.pitch_box.get(resp)
        if row is None:  # a runner placed by a rule (no pitcher put him on)
            resp = self._pkey()
            self._pitch_line(r=1, er=1 if earned else 0)
        else:
            row["r"] += 1
            row["er"] += 1 if earned else 0
        if self._pa is not None and not self._no_rbi:
            self._pa["rbi"].append(runner["id"])
        fld = self.fielding["code"]
        # every run; the winner's run number (loser's final + 1) is the one
        # that put them ahead for good (rule 9.17)
        self._lead_runs.append((code, self.score[code], self._pkey(code), resp))
        if self._entries:
            cur = self._entries[-1] if self._entries[-1]["code"] == fld else None
            for e in reversed(self._entries):
                if e["code"] == fld:
                    cur = e
                    break
            if cur and cur["save_spot"] and self.score[code] >= self.score[fld]:
                cur["blown"] = True

    def _settle_rbi(self, pa):
        """No RBI when the batter reached on an error or grounded into a
        double play (rule 9.04(b)); otherwise every run in the play counts."""
        if not pa:
            return
        text = " ".join(self.log[pa["log0"]:]).lower()
        dp = "double play" in text and self.outs - pa["outs0"] >= 2 if self.outs < 3 else "double play" in text
        if pa["on_error"] or dp:
            return
        n = len(pa["rbi"])
        if n:
            self._line(pa["batter"], rbi=n)

    def _enter(self, code, player):
        fld_lead = self.score[code] - self.score[self.away["code"] if code == self.home["code"] else self.home["code"]]
        on = sum(1 for b in self.bases if b) if code == self.fielding["code"] else 0
        # rule 9.19: lead of 3 or less, or the tying run on base, at bat or on deck
        spot = len(self._entries) > 0 and fld_lead >= 1 and (fld_lead <= 3 or fld_lead <= on + 2)
        self._entries.append({"code": code, "key": code + "|" + player["id"], "lead": fld_lead,
                              "save_spot": spot, "blown": False, "inning": self.inning})

    def _decisions(self):
        """W, L, S and holds by rule 9.17-9.19, from the run that put the
        winner ahead for good."""
        a, h = self.away["code"], self.home["code"]
        if self.score[a] == self.score[h]:
            return {}
        win, lose = (a, h) if self.score[a] > self.score[h] else (h, a)
        go = [r for r in self._lead_runs if r[0] == win and r[1] == self.score[lose] + 1]
        if not go:
            return {}
        _team, _n, wkey, lkey = go[-1]
        wins = [e for e in self._entries if e["code"] == win]
        starter = wins[0]["key"]
        if wkey == starter and self.pitch_box.get(starter, {}).get("outs", 0) < 15 and len(wins) > 1:
            # starter short of 5 innings: the most effective reliever
            rel = [e["key"] for e in wins[1:]]
            wkey = max(rel, key=lambda k: (self.pitch_box[k]["outs"] - 3 * self.pitch_box[k]["r"]))
        out = {"W": wkey, "L": lkey, "S": None, "H": []}
        last = wins[-1]
        if last["key"] != wkey and not last["blown"]:
            outs = self.pitch_box.get(last["key"], {}).get("outs", 0)
            if (last["save_spot"] and (outs >= 3 or last["lead"] < 3)) or outs >= 9:
                out["S"] = last["key"]
        for e in wins[1:-1]:
            if e["save_spot"] and not e["blown"] and e["key"] != wkey and self.pitch_box.get(e["key"], {}).get("outs", 0) >= 1:
                out["H"].append(e["key"])
        return out

    # ---- bullpen usage --------------------------------------------------
    def _usage_reason(self, before_batter):
        if self.opts.get("bullpen") != "manager":
            return None
        code = self.fielding["code"]
        state = self.pitcher[code]
        player = state["player"]
        stamina = player["stamina"] or {}
        starter = bool(self._entries) and [e for e in self._entries if e["code"] == code][0]["key"] == self._pkey()
        if not starter:
            return None
        if before_batter:
            if state["fatigued"]:
                return "Manager: the starter is fatigued (pages 10-11), so he is pulled before the next batter."
            if state["runs"] >= 5:
                return "Manager: the starter has allowed %d runs and is pulled." % state["runs"]
            return None
        nxt = self.inning + 1
        done = len(state["innings"])
        start = stamina.get("start") or 0
        lead = self.score[code] - self.score[self.batting["code"]]
        if start and done >= start and not (lead > 0 and state["runs"] <= 1 and done < 9):
            return "Manager: the starter has gone his Start rating (%s innings)." % start
        if nxt >= 9 and 1 <= lead <= 3 and done >= 7:
            return "Manager: save situation in inning %d; the closer comes in." % nxt
        return None

    def _pick_reliever(self, pen):
        code = self.fielding["code"]
        lead = self.score[code] - self.score[self.batting["code"]]
        late = self.inning >= 7
        short = [p for p in pen if (p["stamina"] or {}).get("relief") == "Short"]
        long_ = [p for p in pen if (p["stamina"] or {}).get("relief") == "Long"]
        if self.opts.get("bullpen") == "manager":
            if late and -1 <= lead <= 3 and short:
                return short[0]            # closer / setup, in roster order
            if not late and long_:
                return long_[0]
            if short:
                return short[-1]           # low-leverage: last man
        return pen[0]

    INFIELD = {"1B", "2B", "3B", "SS"}
    OUTFIELD = {"LF", "CF", "RF", "OF"}

    def _bench_choice(self, club, pos):
        """Same position first, then the same side of the field, then anyone.
        The book names no replacement rule; this is a usage choice."""
        used = self._used_bench.setdefault(club["code"], set())
        bench = [p for p in club["bench"] if not p["removed"] and p["id"] not in used]
        if not bench:
            return None

        def plays(player, group):
            spots = {player.get("pos")} | {r.get("pos") for r in player.get("positions") or []}
            return bool(spots & group)

        if pos and pos != "DH":
            for group in ({pos}, self.INFIELD if pos in self.INFIELD else
                          self.OUTFIELD if pos in self.OUTFIELD else {pos}):
                for player in bench:
                    if plays(player, group):
                        return player
            # A catcher must be replaced; anyone else catches if no C is left.
        return bench[0]

    def _substitute_removed(self):
        """An injured or removed player leaves for the rest of this game only.
        Each game loads its clubs fresh, so he is back the next game.
        Batters come off the bench; pitchers come from the bullpen
        (_maybe_change_pitcher)."""
        self._used_bench = getattr(self, "_used_bench", {})
        for club in (self.batting, self.fielding):
            changed = False
            for i, player in enumerate(club["lineup"]):
                if not player["removed"]:
                    continue
                pos = player["pos"]
                sub = self._bench_choice(club, pos)
                if sub is None:
                    if not player.get("_no_sub_noted"):
                        player["_no_sub_noted"] = True
                        self.gap("%s cannot be replaced. The bench is used up. He stays in." % player["name"])
                    continue
                self._used_bench[club["code"]].add(sub["id"])
                self.box.setdefault(club["code"] + "|" + sub["id"], _empty_line(sub))
                sub["pos"] = pos
                sub["slot"] = player["slot"]
                club["lineup"][i] = sub
                for b, runner in enumerate(self.bases):
                    if runner is player:
                        self.bases[b] = sub
                changed = True
                self.say("Substitution: %s replaces %s (%s) for the rest of this game." % (
                    sub["name"], player["name"], pos))
            if changed:
                self._align(club)

    def _no_more_batters(self):
        if self.half == "top" and self.inning >= 9 and self.score[self.home["code"]] > self.score[self.away["code"]]:
            return True
        if self.half == "bottom" and self.inning >= 9 and self.score[self.home["code"]] != self.score[self.away["code"]]:
            return True
        return False

    def _try_bunt(self, batter, pitcher):
        """Auto bunt needs the 2d6 numbers on the card (page 9). These cards store only the letter."""
        if not self.opts["bunt_policy"]:
            return False
        if self.outs >= 2 or self.bases[0] is None:
            return False
        if self.bases[2] is not None:
            return False
        # Declared sacrifice by the 8 or 9 hitter with a runner on first only.
        # That moment is not in the book. The chart is.
        if batter["slot"] < 8:
            return False
        letter = batter["sac"]
        if letter not in {"A", "B", "C", "D", "F"}:
            self.gap("%s has no bunt letter. A declared bunt cannot be read." % batter["name"])
            return False
        self.say(
            "Sacrifice bunt called (usage choice, page 9 option 1). %s bunt letter %s. The card has no auto-bunt 2d6 numbers, so option 2 cannot fire."
            % (batter["name"], letter)
        )
        self._bunt(batter, letter, squeeze=False)
        return True

    def _bunt(self, batter, letter, squeeze):
        if squeeze:
            letter = "D"
            self.say("Squeeze uses column D regardless of the batter's letter (page 19).")
        if self.deck:
            card = self.deck.draw("bunt")
            result = (card.get("sac") or {}).get(letter)
            fielder_die = card["d6_1"]
            rolls = self.deck.take()
            if result is None:
                self.gap("This FAC has no sac result for letter %s. The bunt is not given a result." % letter)
                return
            fielder = {1: "P", 2: "C", 3: "1B", 4: "P", 5: "3B", 6: "C"}[fielder_die]
            self.say("FAC bunt %s -> %s. 1d6=%s names the fielder (pages 13-14 and 19). Rolls %s." % (
                letter, result, fielder_die, ", ".join(rolls)))
        else:
            fielder_die = self.dice.d6()
            pct = self.dice.pct()
            rolls = self.dice.take()
            fielder = {1: "P", 2: "C", 3: "1B", 4: "P", 5: "3B", 6: "C"}[fielder_die]
            result = sac_result(letter, pct)
            self.say("Bunt roll %s. Fielder %s (page 19 1d6 key). Chart %s." % (", ".join(rolls), fielder, result))
        # The page 19 chart and the FAC print the error result as "E?".
        if result == "E?":
            result = "E"
        if result == "MISS":
            self.say("First miss. Page 19 says the second miss is a strikeout. The bunt is rolled again.")
            if self.deck:
                again = self.deck.draw("bunt-again")
                result = (again.get("sac") or {}).get(letter)
                self.say("Second bunt card -> %s. Rolls %s." % (result, ", ".join(self.deck.take())))
                if result is None:
                    self.gap("The second bunt card has no result for %s. It is not a second miss." % letter)
                    return
            else:
                pct = self.dice.pct()
                result = sac_result(letter, pct)
                self.say("Second bunt percentile %02d -> %s. Rolls %s." % (pct, result, ", ".join(self.dice.take())))
            if result == "E?":
                result = "E"
            if result == "MISS":
                self._record_out(batter, "SO", "Second bunt miss is a strikeout (page 19).")
                return
        if result == "PO":
            self._record_out(batter, "PO", "Bunt pops out. Runners hold (page 19).")
            return
        if result == "DP":
            if self.bases[0] is not None and self.outs < 2:
                self._out_runner(0, "lead runner out on the bunt")
                self._record_out(batter, "BUNT-DP", "Batter out. Double play (page 19).")
            else:
                result = "LEAD"
        if result == "LEAD":
            self._lead_out_batter_safe(batter, "Bunt LEAD (page 19).")
            return
        if result == "SH":
            self._runners_advance(1)
            self._record_out(batter, "SH", "Sacrifice. Batter out, runners advance 1 (page 19).")
            return
        if result == "E":
            defender = self._fielder(fielder)
            err = self._error_of(defender)
            die = self.dice.d6()
            self.say("Error check 1d6=%d against %s error %s. Rolls %s." % (
                die, defender["name"] if defender else fielder, err, ", ".join(self.dice.take())))
            if err is None:
                self.gap("The bunt error check needs the fielder's error rating (page 19). It is missing, so the chart's handled result (SH) is used and no error is invented.")
                self._runners_advance(1)
                self._record_out(batter, "SH", "Bunt error rating missing. Recorded as SH.")
            elif die > err:
                self._reach(batter, 1, 1, "Bunt error. Batter safe, runners advance 1 (page 19).", hit=False, error=True)
            else:
                self._runners_advance(1)
                self._record_out(batter, "SH", "Fielder handles the bunt. Treated as SH (page 19).")

    def _on_fac_draw(self, card, purpose):
        """A drawn WP? card that is not the at-bat percentile. Page 10."""
        if not card.get("wp"):
            return
        if purpose == "batter":
            return
        if purpose == "pct" and self._in_wild_reroll:
            return
        pitcher = self.pitcher[self.fielding["code"]]["player"]
        if self._wp_classify(card, pitcher) != "hit":
            return
        self._runners_advance(1)
        if self._wp_reroll_gap_said:
            return
        self._wp_reroll_gap_said = True
        self.gap(
            "Page 10 re-rolls the percentile after a wild pitch so that roll can resolve the at-bat. This WP? card was drawn for %s, not as that at-bat percentile, so no new at-bat percentile is drawn. The card is still used for %s. Uncertain."
            % (purpose, purpose)
        )

    def _marked_wp_card(self, pct):
        card = self.deck.last if self.deck else None
        if not card or not card.get("wp") or card.get("pct") != pct:
            return None
        return card

    def _wp_classify(self, card, pitcher, second=False):
        """Count one WP? card. Does not move runners. Page 10."""
        self.wp_seen += 1
        pct = card["pct"]
        where = "p%d r%d c%d" % (card["page"], card["row"], card["col"])
        wp = (pitcher.get("addendum") or {}).get("wp")
        if not any(self.bases):
            self.wp_empty += 1
            self.say(
                "FAC %s WP? percentile %02d. Bases are empty, so page 10 does not call a wild pitch."
                % (where, pct)
            )
            return "empty"
        if not wp:
            self.wp_no_rating += 1
            self.say(
                "FAC %s WP? percentile %02d. %s has no WP rating. Page 10 says a wild pitch then comes only from the Rare Play charts."
                % (where, pct, pitcher["name"])
            )
            return "no-rating"
        if not wp_hit(wp, pct):
            self.wp_miss += 1
            self.say(
                "FAC %s WP? percentile %02d is outside %s's WP rating %s. No wild pitch (page 10)."
                % (where, pct, pitcher["name"], wp)
            )
            return "miss"
        self.wp_fired += 1
        which = "Second wild pitch" if second else "Wild pitch"
        self.say(
            "FAC %s WP? percentile %02d is inside %s's WP rating %s. %s. Runners advance 1 (page 10)."
            % (where, pct, pitcher["name"], wp, which)
        )
        return "hit"

    def _wild_pitch(self, pitcher, pct):
        """Return the percentile that resolves the at-bat. Page 10."""
        marked = self._marked_wp_card(pct)
        if marked:
            if self._wp_classify(marked, pitcher) != "hit":
                return pct
            self._runners_advance(1)
            if self.outs >= 3:
                return pct
            return self._wild_reroll(pitcher)
        if not any(self.bases):
            return pct
        wp = (pitcher["addendum"] or {}).get("wp")
        if not wp or not wp_hit(wp, pct):
            return pct
        self.wp_unmarked += 1
        self.say("Wild pitch on percentile %02d. Rating %s. Runners advance 1 (page 10)." % (pct, wp))
        self._runners_advance(1)
        if self.outs >= 3:
            return pct
        return self._wild_reroll(pitcher)

    def _wild_reroll(self, pitcher):
        """Page 10. The re-roll resolves the at-bat. A second hit advances again."""
        self._in_wild_reroll = True
        try:
            pct = self.dice.pct()
        finally:
            self._in_wild_reroll = False
        rolls = ", ".join(self.dice.take())
        if self.deck:
            self.fac_result_card = self.deck.last
        self.say("Wild-pitch re-roll percentile %02d. Rolls %s." % (pct, rolls))
        wp = (pitcher["addendum"] or {}).get("wp")
        marked = self._marked_wp_card(pct)
        kind = None
        if marked and any(self.bases):
            kind = self._wp_classify(marked, pitcher, second=True)
        elif marked:
            self.wp_seen += 1
            self.wp_empty += 1
            self.say(
                "FAC p%d r%d c%d WP? on the wild-pitch re-roll. Bases are empty, so the mark does not add a wild pitch (page 10)."
                % (marked["page"], marked["row"], marked["col"])
            )
        if wp_hit(wp, pct):
            if kind != "hit":
                if not marked:
                    self.wp_unmarked += 1
                self.say("Second wild pitch. Runners advance 1 more. This same roll resolves the at-bat (page 10).")
            self._runners_advance(1)
        elif kind is None:
            self.say("The re-roll is outside the wild-pitch range. Runners hold. This roll resolves the at-bat (page 10).")
        else:
            self.say("This same roll resolves the at-bat (page 10).")
        return pct

    def _want_hit_and_run(self, batter):
        if self.bases[0] is None or self.bases[2] is not None or self.outs >= 2:
            return False
        # One call when the runner is on first and there is one out. Not a rule.
        return self.outs == 1 and batter["slot"] in (2, 6)

    def _hit_and_run(self, batter, pitcher, reading, pct, one, two, total):
        self.say("Hit and run called (optional, page 10). The moment it is called is a usage choice.")
        self.say(reading["text"])
        section = self._hit_and_run_section(batter, pitcher, reading, pct)
        if section == "WHEELHOUSE":
            a, b, fresh = self.dice.pair()
            new_pct = self.dice.pct()
            self.say("Wheelhouse during a hit and run. Re-roll %s, percentile %02d. Rolls %s." % (
                self._fmt(a, b, fresh), new_pct, ", ".join(self.dice.take())))
            if self._is_doubles(a, b, "A hit-and-run wheelhouse"):
                self.say("Doubles. The wheelhouse is read as normal (page 10).")
                if new_pct == 0:
                    self._rare(batter, pitcher, "WHEELHOUSE", a, b)
                    return
                self._read_batter(batter, pitcher, "WHEELHOUSE", new_pct, a, b, True)
            elif new_pct == 0 or new_pct <= 49:
                if new_pct == 0:
                    self.gap("Hit and run wheelhouse re-roll is 00. Page 10 puts 00-49 on a single and does not mention a rare play. Recorded as that single.")
                self._hit_and_run_single(batter, pitcher, new_pct, "Hit and run wheelhouse single (page 10).")
            else:
                kind = out_type(batter["out_table"], new_pct) or "OUT"
                self.say("Hit and run wheelhouse out. Out section %s." % kind)
                self._apply_out(batter, kind, pitcher, True, "IN-PLAY", new_pct)
            return
        if section == "PATIENT":
            self.say("Hit and run PATIENT is a foul. Re-roll on IN-PLAY (page 18).")
            new_pct = self.dice.pct()
            self.say("IN-PLAY percentile %02d. Rolls %s." % (new_pct, ", ".join(self.dice.take())))
            if new_pct == 0:
                self._rare(batter, pitcher, "IN-PLAY", one, two)
                return
            self._read_batter(batter, pitcher, "IN-PLAY", new_pct, one, two, True)
            return
        self._apply_reading(batter, pitcher, reading, pct, one, two, total, True, announced=True)

    def _hit_and_run_section(self, batter, pitcher, reading, pct):
        event = reading["event"]
        if event == "PARK":
            target = self._ballpark_section(batter, pitcher, pct)
            self.say("BALLPARK during a hit and run is %s before the wheelhouse rule (page 10)." % target)
            return target
        if event == "PATIENT-OUT":
            self.gap("Hit and run names PATIENT as a foul (page 18). It does not name PATIENT-OUT. This game uses the PATIENT foul.")
            return "PATIENT"
        if reading.get("section") == "PATIENT":
            return "PATIENT"
        if reading.get("section") == "WHEELHOUSE" or event == "READ" and reading.get("section") == "WHEELHOUSE":
            return "WHEELHOUSE"
        return reading.get("section")

    def _apply_reading(self, batter, pitcher, reading, pct, one, two, total, hit_and_run, announced=False):
        if not announced:
            self.say(reading["text"])
        event = reading["event"]
        if event == "RARE":
            self._rare(batter, pitcher, reading.get("section") or "WHEELHOUSE", one, two)
            return
        if event == "DEFENSE":
            self._defense(batter, pitcher, reading, hit_and_run, pct)
            return
        if event == "SINGLE":
            advance = reading.get("advance_as") or "PATIENT"
            self._finish_event(batter, pitcher, "1B", advance, pct, one, two, hit_and_run)
            return
        if event == "PARK":
            if pct is None and self.deck:
                park_card = self.deck.draw("park")
                pct = park_card["pct"]
                self.say("FAC ballpark percentile %02d. Rolls %s. (page 13)" % (pct, ", ".join(self.deck.take())))
            section = self._ballpark_section(batter, pitcher, pct)
            new_pct = self.dice.pct()
            if self.deck:
                self.fac_result_card = self.deck.last
            self.say("Re-roll percentile %02d onto %s. Rolls %s. Page 2 names the percentile. Page 9 says re-roll the dice." % (
                new_pct, section, ", ".join(self.dice.take())))
            self.gap(
                "BALLPARK tells the reader to re-roll the dice (page 9) and to re-roll the percentile (page 2). This game re-rolls the percentile and keeps the 2d6."
            )
            if new_pct == 0:
                self._rare(batter, pitcher, section, one, two)
                return
            self._read_batter(batter, pitcher, section, new_pct, one, two, hit_and_run, section)
            return
        if event == "REROLL":
            new_pct = self.dice.pct()
            self.say("Re-roll percentile %02d onto %s. Rolls %s." % (
                new_pct, reading["section"], ", ".join(self.dice.take())))
            if new_pct == 0:
                self._rare(batter, pitcher, reading["section"], one, two)
                return
            self._read_batter(
                batter, pitcher, reading["section"], new_pct, one, two, hit_and_run,
                reading.get("advance_as") or reading["section"],
            )
            return
        if event == "PATIENT-OUT":
            self._patient_out = True
            self._read_batter(batter, pitcher, "PATIENT", pct, one, two, hit_and_run)
            self._patient_out = False
            return
        if event == "TOUGH-OUT":
            self._tough_out = True
            self._read_batter(batter, pitcher, "TOUGH", pct, one, two, hit_and_run)
            self._tough_out = False
            return
        if event == "OUT-SECTION":
            kind = out_type(batter["out_table"], pct)
            if kind is None:
                printed = reading.get("printed_out")
                if not printed:
                    self.gap(
                        "The /IN-PLAY/ face is outside the OUT section. Page 3 says to use the out printed beside the pitcher result. These cards do not store that out."
                    )
                    printed = "OUT"
                kind = printed
            self._apply_out(batter, kind, pitcher, hit_and_run, "IN-PLAY", pct)
            return
        if event == "AUTO-OUT":
            kind = reading.get("printed_out") or "OUT"
            if kind == "OUT":
                self.gap(
                    "Page 3 makes a later-inning /IN-PLAY/ the printed out. These cards do not store that out code. Recorded as an out."
                )
            self._apply_out(batter, kind, pitcher, hit_and_run, "IN-PLAY", pct)
            return
        self._read_batter(
            batter, pitcher, reading["section"], pct, one, two, hit_and_run,
            reading.get("advance_as") or reading["section"],
        )

    def _ballpark_section(self, batter, pitcher, pct):
        if pct is None and self.deck:
            park_card = self.deck.draw("park")
            pct = park_card["pct"]
            self.say("FAC ballpark percentile %02d. Rolls %s. (page 13)" % (pct, ", ".join(self.deck.take())))
        stand = _stand(batter["bats"], pitcher["throws"] or "R")
        wh = self.park["wh_l"] if stand == "L" else self.park["wh_r"]
        self.say("BALLPARK. %s bats %s. %s wheelhouse runs through %s (page 9)." % (
            batter["name"], stand, self.park["name"], wh))
        if pct == 0:
            return "RARE"
        if 1 <= pct <= int(wh):
            return "WHEELHOUSE"
        return "IN-PLAY"

    def _pitch_reading(self, batter, pitcher, result, pct):
        fatigued = self.pitcher[self.fielding["code"]]["fatigued"]
        special = set(pitcher["special"])
        original = result
        if fatigued and result in {"PATIENT-OUT", "/PATIENT/"}:
            result = "PATIENT"
            self.say("Fatigue ignores %s and reads PATIENT (page 21)." % original)
        elif fatigued and result == "TOUGH-OUT":
            result = "TOUGH"
            self.say("Fatigue ignores TOUGH-OUT and reads TOUGH (page 21).")
        elif fatigued and "IN-PLAY" in result and result != "IN-PLAY":
            result = "IN-PLAY"
            self.say("Fatigue ignores the slash and reads IN-PLAY (page 21).")
        if result == "BALLPARK":
            if fatigued:
                return {"event": "READ", "section": "WHEELHOUSE", "advance_as": "WHEELHOUSE",
                        "text": "Fatigued BALLPARK is read on WHEELHOUSE with this percentile (page 21)."}
            return {"event": "PARK", "text": "BALLPARK. The home chart is checked (page 9)."}
        if result in {"DEFENSE", "RANGE", "ERROR"}:
            return {"event": "DEFENSE", "mode": result, "text": "%s. The defense chart uses this percentile, then all four dice are re-rolled (pages 2 and 20)." % result}
        if "IN-PLAY" in result and result != "IN-PLAY":
            return self._slash_in_play(pitcher, result)
        section = result
        advance_as = result
        if fatigued and result in {"PATIENT", "TOUGH"}:
            kind = "RP" if (pitcher["stamina"] or {}).get("relief") else "SP"
            mapped = fatigue_patient(kind, pct) if result == "PATIENT" else fatigue_tough(pct)
            if mapped is None:
                self.gap("Fatigue chart has no face %02d. The original %s result is kept." % (pct, result))
            else:
                self.say("Fatigue chart reads %s as %s (page 21, %s)." % (result, mapped, kind))
                if mapped == "SINGLE":
                    return {
                        "event": "SINGLE",
                        "advance_as": result,
                        "text": "Fatigue chart single. Runner advancement follows the original %s result (page 21)." % result,
                    }
                section = mapped
                advance_as = result
        plain = original if not fatigued else result
        if not fatigued and (plain == "PATIENT-OUT" or ("PATIENT-OUT" in special and plain == "PATIENT")):
            return {"event": "PATIENT-OUT", "section": "PATIENT", "text": "PATIENT-OUT (page 2). Walks and hit by pitches count. Anything else is the OUT section."}
        if not fatigued and (plain == "TOUGH-OUT" or ("TOUGH-OUT" in special and plain == "TOUGH")):
            return {"event": "TOUGH-OUT", "section": "TOUGH", "text": "TOUGH-OUT (page 2). A face above the strikeout band is an out."}
        return {"event": "READ", "section": section, "advance_as": advance_as,
                "text": "Read the batter's %s section (page 4)." % section}

    def _slash_in_play(self, pitcher, result):
        mode = self.opts["slash_in_play"]
        first = len(self.pitcher[self.fielding["code"]]["innings"]) <= 1 and self.pitcher[self.fielding["code"]]["batters"] <= 1
        self.say("/IN-PLAY/ (page 3). Toggle %s." % mode)
        if mode == "normal" or (mode == "first_inning" and first):
            return {"event": "READ", "section": "IN-PLAY", "text": "Read as a normal IN-PLAY (page 3 option)."}
        if mode == "out_section":
            return {"event": "OUT-SECTION", "text": "Use the batter OUT section, and the printed out only if the face is outside it (page 3)."}
        return {"event": "AUTO-OUT", "text": "Second or later inning. The printed out is automatic (page 3)."}

    def _read_batter(self, batter, pitcher, section, pct, one, two, hit_and_run, advance_as=None):
        advance_as = advance_as or section
        if section == "SINGLE":
            self._finish_event(batter, pitcher, "1B", advance_as if advance_as != "SINGLE" else "PATIENT", pct, one, two, hit_and_run)
            return
        if section == "RARE":
            self._rare(batter, pitcher, "WHEELHOUSE", one, two)
            return
        throws = pitcher["throws"] or "R"
        hand = _hand_key(throws)
        table = ((batter["sections"].get(section) or {}).get(hand)) or {}
        if self.opts["tough_shift"] and section == "TOUGH" and not self._tough_out:
            bump = _bump(pitcher["so_modifier"])
            if bump and pct != 0:
                adjusted = pct + bump
                if adjusted > 99:
                    self.say("Page 39 +%d would be %d, over 99, so percentile %02d stands." % (bump, adjusted, pct))
                else:
                    self.say("Page 39 +%d moves percentile %02d to %02d on TOUGH." % (bump, pct, adjusted))
                    pct = adjusted
        elif self._tough_out and _bump(pitcher["so_modifier"]):
            self.gap("Page 39 adds +10 or +20 on TOUGH. It does not name TOUGH-OUT. The shift is not applied.")
        faces, overlaps = section_faces(table)
        if overlaps:
            self.gap("%s %s bands overlap. The first listed result is kept." % (batter["name"], section))
        if pct == 0 and self.opts["zero_hr"] and _hr_blank(table):
            self._zero_hr(batter, pitcher, section, one, two)
            return
        event = "RARE" if pct == 0 else (faces[pct] or "OUT")
        if self._patient_out and section == "PATIENT" and event not in {"BB", "HBP", "RARE"}:
            event = "OUT"
        if self._tough_out and section == "TOUGH":
            so_hi = _so_hi(table)
            if event == "SO" or event == "RARE":
                pass
            elif so_hi is not None and pct > so_hi:
                event = "OUT"
            elif event != "SO":
                # A face below the strikeout band keeps its printed result.
                pass
        if event == "RARE":
            self._rare(batter, pitcher, section, one, two)
            return
        if event == "OUT":
            kind = out_type(batter["out_table"], pct)
            if kind is None:
                if self._patient_out:
                    self.gap("PATIENT-OUT face %02d is outside %s's OUT section. Page 2 says to use the out provided with the pitcher result. These cards do not store that out." % (pct, batter["name"]))
                else:
                    self.gap("Percentile %02d is outside %s's hitting and out ranges. Recorded as an out. The book does not name the out." % (pct, batter["name"]))
                kind = "OUT"
            if self._supplemental_strikeout(pitcher, pct):
                kind = "SO"
                band = pitcher.get("so_band")
                self.say("Optional page 11 strikeout range %02d-%02d replaces the out. The range is an estimate, not printed on the card." % (band[0], band[1]))
            self.say("%s section percentile %02d is an out: %s." % (section, pct, kind))
            self._apply_out(batter, kind, pitcher, hit_and_run, section, pct)
            return
        self.say("%s section percentile %02d is %s." % (section, pct, event))
        if hit_and_run and event == "BB":
            self.gap("A hit and run cannot be a walk (page 10). The book does not say what the walk becomes. This roll is re-read on IN-PLAY.")
            new_pct = self.dice.pct()
            self.say("IN-PLAY percentile %02d. Rolls %s." % (new_pct, ", ".join(self.dice.take())))
            self._read_batter(batter, pitcher, "IN-PLAY", new_pct, one, two, False)
            return
        self._finish_event(batter, pitcher, event, advance_as, pct, one, two, hit_and_run)

    def _zero_hr(self, batter, pitcher, section, one, two):
        new_pct = self.dice.pct()
        self.say("Optional page 39 rule. HR range is blank or 0 and the percentile was 00. Re-roll %02d." % new_pct)
        self.dice.take()
        if new_pct % 11 == 0:
            self.say("Doubles. Home run (page 39).")
            self._finish_event(batter, pitcher, "HR", section, new_pct, one, two, False)
            return
        self.say("Not doubles. The rare-play chart is used (page 39).")
        self._rare(batter, pitcher, section, one, two)

    def _finish_event(self, batter, pitcher, event, section, pct, one, two, hit_and_run):
        if event in {"BB", "HBP"}:
            self._walk(batter, event)
            return
        if event == "SO":
            self._record_out(batter, "SO", "Strikeout. Runners hold (page 5).")
            if hit_and_run:
                self.say("Hit and run: the lead runner must steal (page 10).")
                self._steal_lead(must=True)
            return
        if hit_and_run and event == "1B":
            self._hit_and_run_single(batter, pitcher, pct, "Hit and run single (page 18).")
            return
        if hit_and_run and event == "2B":
            self._reach(batter, 2, 4, "Hit and run double. Runners score (page 18).", hit=True)
            return
        bases = {"1B": 1, "2B": 2, "3B": 3, "HR": 4}[event]
        if self.opts["running"] == "fac" and self.deck and event in {"1B", "2B"} and any(self.bases):
            self._fac_running(batter, event)
            return
        if self.opts["running"] == "advanced" and event in {"1B", "2B"} and any(self.bases):
            self._advanced_hit(batter, event, one, two, pct)
            return
        runner_bases = bases
        if self.opts["running"] == "basic":
            auto_extra = (self.outs == 2 or section == "WHEELHOUSE") and event in {"1B", "2B"}
            if auto_extra:
                runner_bases = bases + 1
                self.say("Basic running: two outs or wheelhouse, runners take one extra base (pages 5-6).")
                if section == "PATIENT":
                    self.gap(
                        "A PATIENT hit with two outs is named by both the two-out extra base and the patient choice (page 6). This game uses the two-out extra base and does not add another attempt."
                    )
            elif section == "PATIENT" and event in {"1B", "2B"} and any(self.bases):
                self._patient_extra(batter, event, pct)
                return
        elif self.opts["running"] == "fac":
            pass
        elif self.opts["running"] not in {"basic", "advanced"}:
            self.gap("Running option %s is not a printed dice chart. Basic advancement is used." % self.opts["running"])
        self._reach(batter, bases, runner_bases, "%s." % event, hit=True)

    def _hit_and_run_single(self, batter, pitcher, pct, text):
        stand = _stand(batter["bats"], pitcher["throws"] or "R")
        pos = hit_fielder("1B", pct % 10, stand)
        arm = self._arm_of(self._fielder(pos))
        runner = self.bases[0]
        bases = 2
        if runner and (runner.get("run") or 0) >= 7:
            if arm is None:
                self.gap("Hit and run: a runner rated 7 or higher scores from first when the outfield arm is 8 or higher (page 18). %s has no arm. He stops at third." % pos)
            elif arm >= 8:
                bases = 3
                self.say("Hit and run: RUN 7 or higher scores from first. %s arm %s is 8 or higher (page 18)." % (pos, arm))
            else:
                self.say("Hit and run: RUN 7 or higher stops at third. %s arm %s is better than 8 (page 18)." % (pos, arm))
        else:
            self.say("Hit and run: runners take two on a single (page 18).")
        self._reach(batter, 1, bases, text, hit=True)

    def _fac_running(self, batter, event):
        """Preferred advancement: the next card's SINGLE or DOUBLE lines. Pages 13-14."""
        card = self.deck.draw("advance")
        block = card["single"] if event == "1B" else card["double"]
        self.say(
            "FAC %s. %s. %s. 1d6=%s on this card. Rolls %s. (pages 13-14)"
            % (
                "single" if event == "1B" else "double",
                block.get("location"),
                "; ".join(block.get("lines") or []) or "no extra runner line",
                card["d6_1"],
                ", ".join(self.deck.take()),
            )
        )
        default = 1 if event == "1B" else 2
        moves = {}
        for base in (0, 1, 2):
            if self.bases[base]:
                moves[base] = default
        choice = False
        for line in block.get("lines") or []:
            parsed = parse_runner_line(line)
            if parsed is None:
                self.gap("Runner line is not encoded: %s. That runner keeps %d base(s)." % (line, default))
                continue
            who, count, plus = parsed
            if plus:
                choice = True
            if who == "first" and 0 in moves:
                moves[0] = count
            elif who == "second" and 1 in moves:
                moves[1] = count
            elif who in {"all", "score"}:
                for base in list(moves):
                    moves[base] = 3 if who == "score" else count
        automatic = set()
        for base in list(moves):
            runner = self.bases[base]
            run = runner["run"] or 0
            if self.outs >= 2 and run >= 6:
                moves[base] = 2 if event == "1B" else 3
                automatic.add(base)
                self.say("%s RUN %s with two outs takes the automatic extra base (page 14)." % (runner["name"], run))
        lead = max(moves) if moves else None
        lead_id = self.bases[lead]["id"] if lead is not None else None
        for base in (2, 1, 0):
            if base in moves and self.bases[base] is not None:
                self._advance_runner_n(base, moves[base], "FAC")
        if choice and lead_id and lead not in automatic and self.outs < 3:
            now = self._find_runner(lead_id)
            runner = self.bases[now] if now is not None else None
            if runner is not None:
                run = runner["run"] or 0
                self.say(
                    "+? compares RUN %s to 1d6=%s on this card. He tries when RUN is higher (page 13). The next card's 1d6 is allowed and is not used."
                    % (run, card["d6_1"])
                )
                if run > card["d6_1"]:
                    pos = self._fac_fielder(batter, block.get("location"))
                    self._extra_base(now, pos)
        batter_bases = 1 if event == "1B" else 2
        self._reach(batter, batter_bases, 0, "%s." % event, hit=True, hold_lead=True)

    def _fac_fielder(self, batter, location):
        text = location or ""
        if "/" in text:
            left, right = [part.strip() for part in text.split("/", 1)]
            stand = _stand(batter["bats"], self.pitcher[self.fielding["code"]]["player"]["throws"] or "R")
            chosen = left if stand == "L" else right
            self.say("Split location %s. A %s batter is fielded by %s (page 13)." % (text, stand, chosen))
            for pos in ("LF", "CF", "RF", "1B", "2B", "3B", "SS", "P", "C"):
                if pos in chosen:
                    return pos
        for pos in ("LF", "CF", "RF"):
            if pos in text:
                return pos
        self.gap("The FAC location does not name an outfielder (%s). The extra-base chart needs an arm, so the lead runner holds the stated base." % text)
        return None

    def _advanced_hit(self, batter, event, one, two, pct):
        low = self._low_die(one, two)
        self.say("Advanced running uses the low die %d (page 16)." % low)
        planned = []
        for base in (2, 1, 0):
            runner = self.bases[base]
            if runner is None:
                continue
            count, choice = self._advanced_move(base, event, low, runner)
            planned.append((base, count, choice, runner))
        # Move the lead runner first so a trail runner can follow onto a vacated base.
        for base, count, choice, runner in planned:
            if self.bases[base] is None or self.outs >= 3:
                continue
            self._advance_runner_n(base, count, "advanced chart")
            if choice and self.outs < 3:
                now = self._find_runner(runner["id"])
                if now is not None:
                    pos = hit_fielder(event, pct % 10, _stand(batter["bats"], "R"))
                    self.say("%s may try for one more base (page 16)." % runner["name"])
                    self._extra_base(now, pos)
        if self.outs < 3:
            self._reach(batter, 1 if event == "1B" else 2, 0, "%s." % event, hit=True)

    def _advanced_move(self, base, event, low, runner):
        run = runner.get("run") or 0
        if self.outs == 2:
            if run >= 6:
                return (2 if event == "1B" else 4), False
            self.say("%s is rated %s. With two outs he has a choice (page 16)." % (runner["name"], run))
            return (1 if event == "1B" else 2), True
        if event == "1B" and base == 0:
            return ADV_SINGLE_FIRST[low]
        if event == "1B" and base == 1:
            return ADV_SINGLE_SECOND[low]
        if event == "2B" and base == 0:
            return ADV_DOUBLE_FIRST[low]
        self.gap(
            "The advanced chart has no column for a %s with the runner on %s. He takes the same number of bases as the hit."
            % (event, _base_name(base))
        )
        return (1 if event == "1B" else 2), False

    def _advance_runner_n(self, base, n, text):
        if n <= 0 or self.bases[base] is None:
            return
        runner = self.bases[base]
        self.bases[base] = None
        dest = base + n
        if dest >= 3:
            self._run_scores(runner)
            self.say("%s scores from %s (%s)." % (runner["name"], _base_name(base), text))
        else:
            if self.bases[dest] is not None:
                self.gap("Advanced advancement would put two runners on %s. The trail runner holds. The book does not say how to break the tie." % _base_name(dest))
                self.bases[base] = runner
                return
            self.bases[dest] = runner
            self.say("%s to %s (%s)." % (runner["name"], _base_name(dest), text))

    def _find_runner(self, pid):
        for base, runner in enumerate(self.bases):
            if runner and runner["id"] == pid:
                return base
        return None

    def _patient_extra(self, batter, event, pct):
        """Lead runner may try for one more base. Page 6 and the page 16 chart."""
        stand = _stand(batter["bats"], "R")
        fielder_pos = hit_fielder(event, pct % 10, stand)
        self._reach(batter, 1 if event == "1B" else 2, 1 if event == "1B" else 2,
                    "PATIENT %s. Basic advance, then the lead runner may try for one more (page 6)." % event,
                    hit=True, hold_lead=True)
        if self.outs >= 3:
            return
        lead = self._lead_base()
        if lead is None:
            return
        runner = self.bases[lead]
        total = self.dice.pair()[2]
        self.say(
            "Coach's choice for %s. 2d6=%d against RUN %s. The book says he goes when the roll is less than RUN. Rolls %s."
            % (runner["name"], total, runner["run"], ", ".join(self.dice.take()))
        )
        if runner["run"] is None or total >= runner["run"]:
            self.say("He holds.")
            return
        self._extra_base(lead, fielder_pos)

    def _apply_out(self, batter, kind, pitcher, hit_and_run, section="IN-PLAY", pct=0):
        if hit_and_run and kind in LINE_OUTS:
            self.say("Hit and run lineout is a double play. The closest runner is doubled off (page 18).")
            self.gap("Page 18 says the closest runner is doubled off on a hit-and-run lineout. It does not say how to measure closest. The lead runner is used.")
            self._double_off_lead()
            self._record_out(batter, kind, "Lineout.")
            return
        if hit_and_run and kind in GROUND_OUTS and self.bases[0] is not None and self.outs < 2:
            a, b, total = self.dice.pair()
            self.say("Hit and run groundout chart. 2d6 %s. Rolls %s." % (self._fmt(a, b, total), ", ".join(self.dice.take())))
            if total <= 3:
                self._out_runner(0, "forced at second")
                self._record_out(batter, kind, "Hit and run double play (page 18).")
            elif total <= 10:
                self._runners_advance(1)
                self._record_out(batter, kind, "Hit and run: batter out, runners advance 1 (page 18).")
            else:
                self._out_runner(0, "forced at second")
                self._reach(batter, 1, 0, "Hit and run: runner forced, batter safe (page 18).", hit=False)
            return
        if kind in POP_OUTS or kind in LINE_OUTS or kind == "OUT":
            self._record_out(batter, kind, "%s. Runners hold (pages 5 and 17)." % kind)
            return
        if kind in FLY_OUTS:
            self._fly(batter, kind, section, pct, hit_and_run)
            return
        if kind in GROUND_OUTS:
            self._ground(batter, kind, pitcher, pct)
            return
        self._record_out(batter, kind, "Out %s. No advancement rule is printed for this code." % kind)

    def _fly(self, batter, kind, section, pct, hit_and_run=False):
        """Page 17 fly outs. A fly that is the third out does not score a runner."""
        pos = OUT_POS.get(kind, "CF")
        deep = section in {"WHEELHOUSE", "PATIENT"}
        self.say("Fly %s to %s. The pitcher result is %s for the out chart (page 17)." % (kind, pos, "deep" if deep else "ordinary"))
        if self.outs >= 2:
            self._record_out(batter, kind, "Third out on the catch. A runner does not score after the third out.")
            self.gap("Page 17 says a runner on third scores on a deep fly and does not mention the third out. This game does not count that run.")
            return
        scored_from_third = False
        if deep:
            if self.bases[2]:
                self._score_runner(2, "scores from third on a deep fly (page 17)")
                scored_from_third = True
            if kind == "F9" and self.bases[1]:
                self._move_runner(1, 2, "second to third on F9")
            elif kind == "F8" and self.bases[1]:
                runner = self.bases[1]
                if (runner["run"] or 0) >= 7:
                    self._move_runner(1, 2, "RUN 7 or higher, second to third on F8")
                else:
                    self.say("%s may try for third. The book reduces RUN by 2. That attempt is the coach's chart." % runner["name"])
                    self._maybe_send(1, "CF", run_cut=2)
            elif kind == "F7" and self.bases[1]:
                self.say("F7: the runner on second may try, with RUN reduced by 2 (page 17).")
                self._maybe_send(1, "LF", run_cut=2)
        else:
            if self.bases[2]:
                runner = self.bases[2]
                run = runner["run"] or 0
                if section == "TOUGH":
                    run = max(0, run - 2)
                    self.say("TOUGH fly: RUN reduced by 2 before the attempt (page 17).")
                if run >= 7:
                    self._score_runner(2, "RUN 7 or higher scores from third")
                    scored_from_third = True
                else:
                    self.say("%s may try to score from third (page 17)." % runner["name"])
                    before = self.score[self.batting["code"]]
                    self._maybe_send(2, pos, run_cut=2 if section == "TOUGH" else 0)
                    if self.score[self.batting["code"]] > before:
                        scored_from_third = True
            if kind in {"F8", "F9"} and self.bases[1]:
                runner = self.bases[1]
                if (runner["run"] or 0) >= 7:
                    self._move_runner(1, 2, "RUN 7 or higher, second to third on %s" % kind)
        self.outs += 1
        self.pitcher[self.fielding["code"]]["outs"] += 1
        self._pitch_line(outs=1)
        if scored_from_third:
            self._charge_out(batter, "SF")
            self.say("%s is a sacrifice fly. It is not an at-bat." % kind)
        else:
            self._charge_out(batter, kind)
        if hit_and_run and kind in {"F8", "F9"} and self.outs < 3:
            self._hit_and_run_fly_back(kind)

    def _hit_and_run_fly_back(self, kind):
        runner = self.bases[0]
        if runner is None:
            return
        a, b, total = self.dice.pair()
        face = self.dice.d10()
        self.say("Hit and run %s with a runner still on first. 2d6 %s, 1d10=%d. Rolls %s. (page 18)" % (
            kind, self._fmt(a, b, total), face, ", ".join(self.dice.take())))
        self.gap("Page 18's hit-and-run fly check says 1d10. This game reads it as 0-9. It does not say whether 0 is 10.")
        if self._is_doubles(a, b, "The hit-and-run fly check") and face > (runner.get("run") or 0):
            self._out_runner(0, "thrown out going back to first")

    def _maybe_send(self, base, pos, run_cut=0):
        runner = self.bases[base] if 0 <= base <= 2 else None
        if runner is None or self.outs >= 3:
            return
        run = max(0, (runner.get("run") or 0) - run_cut)
        total = self.dice.pair()[2]
        self.say("Send %s? 2d6=%d against RUN %s. He goes when the roll is less than RUN (page 16). Rolls %s." % (
            runner["name"], total, run, ", ".join(self.dice.take())))
        if total >= run:
            self.say("He holds.")
            return
        self._extra_base(base, pos, run_cut=run_cut)

    def _ground(self, batter, kind, pitcher, pct):
        pos = OUT_POS.get(kind, "2B")
        runner_first = self.bases[0] is not None and self.outs < 2
        if self.opts["infield_in"] and self.bases[2] and self.outs < 2 and self._infield_in_now() and pos in {"1B", "2B", "3B", "SS"}:
            self.say("Infield in was declared before the pitch (page 7). The moment is a usage choice.")
            self._infield_in(batter, pos)
            return
        if not runner_first:
            self._ground_no_force(batter, kind, pos)
            return
        bat_dp = batter["dp"]
        pit_dp = pitcher["addendum"].get("dp")
        if bat_dp is None and pit_dp is None:
            self.gap("Neither the batter nor the pitcher has a DP rating. The double-play check cannot be read. The batter is out and the runners hold.")
            self._record_out(batter, kind, "Groundout. No DP rating.")
            return
        if bat_dp is None:
            self.gap("%s has no DP rating. The pitcher's DP %s is used alone. Page 6 says to use the lower of the two." % (batter["name"], pit_dp))
            rating = int(pit_dp)
        elif pit_dp is None:
            self.gap("%s has no DP rating. The batter's DP %s is used alone. Page 6 says to use the lower of the two." % (pitcher["name"], bat_dp))
            rating = int(bat_dp)
        else:
            rating = min(int(bat_dp), int(pit_dp))
        a, b, total = self.dice.pair()
        ones = pct % 10
        self.say("Double-play check. Lower DP %s. 2d6 %s. At-bat percentile %02d. Rolls %s. (pages 6 and 17)" % (
            rating, self._fmt(a, b, total), pct, ", ".join(self.dice.take())))
        if kind == "G3":
            if ones >= 3:
                self.say("The percentile ends in %d. The first baseman is unassisted (page 17)." % ones)
            else:
                self.say("The percentile ends in %d. The first baseman throws to the pitcher covering first (page 17)." % ones)
        if total <= rating and self.bases[0] and self.bases[1] and pos in {"3B", "SS", "P"} and ones == 5:
            self.say("Percentile ends in 5. The runner from second is out at third and the batter is out at first (page 17).")
            self.gap("That double-play exception does not say what the runner on first does, or whether a runner on third scores. They hold.")
            self._out_runner(1, "forced out at third")
            if self.outs < 3:
                self._record_out(batter, kind, "Batter out at first.")
            return
        if total <= rating:
            if pos == "SS" and ones == 6:
                self.say("Percentile ends in 6. The shortstop steps on second and throws to first (page 17).")
            self.say("Double play.")
            self._out_runner(0, "forced at second")
            if self.outs < 3:
                self._runners_advance(1)
                self._record_out(batter, kind, "Batter out at first. Other runners advance 1 (page 17).")
            return
        if total >= 11:
            self._runners_advance(1)
            self._record_out(batter, kind, "2d6 is 11 or 12. Batter out, runners advance 1 (page 6).")
            return
        if self.bases[1] and pos in {"SS", "3B"} and ones == 5:
            self.say("Percentile ends in 5. The runner on second is out advancing to third. The batter is safe (page 17).")
            self._out_runner(1, "out advancing to third")
            if self.outs < 3:
                self._runners_advance(1)
                self._reach(batter, 1, 0, "Batter safe at first.", hit=False)
            return
        self._out_runner(0, "forced at second")
        if self.outs < 3:
            self._runners_advance(1)
            self._reach(batter, 1, 0, "Fielder's choice. Batter safe at first (page 6).", hit=False)

    def _ground_no_force(self, batter, kind, pos):
        if pos == "P" and (self.bases[1] or self.bases[2]):
            self._record_out(batter, kind, "Pitcher looks the runner back and throws to first. Runners hold (page 17).")
            return
        if self.bases[2] and pos in {"2B", "SS"} and self.outs < 2:
            self._score_runner(2, "scores from third on a grounder to %s (page 17)" % pos)
        elif self.bases[2] and pos in {"1B", "3B"} and self.outs < 2:
            self.say("Runner on third has a choice on a grounder to %s. RUN is reduced by 1 (page 17)." % pos)
            self._maybe_send(2, pos, run_cut=1)
        if self.bases[2] is None and self.bases[1] and pos in {"1B", "2B"} and self.outs < 2:
            self._move_runner(1, 2, "second to third on a grounder to %s (page 17)" % pos)
        elif self.bases[2] is None and self.bases[1] and pos in {"SS", "3B"} and self.outs < 2:
            runner = self.bases[1]
            if (runner["run"] or 0) >= 7:
                self._move_runner(1, 2, "RUN 7 or higher takes third on the throw (page 17)")
        self._record_out(batter, kind, "Groundout %s (page 17)." % kind)

    def _infield_in_now(self):
        if self.inning < 7:
            return False
        diff = self.score[self.fielding["code"]] - self.score[self.batting["code"]]
        return abs(diff) <= 1

    def _infield_in(self, batter, pos):
        a, b, total = self.dice.pair()
        pct = self.dice.pct()
        self.say("Infield-in chart re-roll %s, percentile %02d. Rolls %s. (page 19)" % (
            self._fmt(a, b, total), pct, ", ".join(self.dice.take())))
        loaded = all(base is not None for base in self.bases)
        if total <= 5:
            if loaded:
                self._out_runner(2, "out at home")
                if self.outs < 3:
                    self._runners_advance(1)
                    self._record_out(batter, "GI", "Bases loaded, 2-5. Runner out at home, batter out. Double play (page 19).")
            else:
                if self.bases[0]:
                    self._move_runner(0, 1, "runner on first advances")
                self._record_out(batter, "GI", "Infield in 2-5. Batter out, other runners hold (page 19).")
            return
        if total <= 8:
            if loaded:
                face = self.dice.d10()
                self.say("Bases loaded. 1d10=%d against batter RUN %s. Rolls %s. (page 19)" % (
                    face, batter["run"], ", ".join(self.dice.take())))
                self.gap("The infield-in chart says 1d10. This game reads it as 0-9, the same faces as a percentile ones die (page 13). It does not say whether a 0 is a 10.")
                if batter["run"] is None or face > (batter["run"] or 0):
                    self._out_runner(2, "out at home")
                    if self.outs < 3:
                        self._runners_advance(1)
                        self._record_out(batter, "GI", "1d10 is higher than RUN. Batter out. Double play (page 19).")
                    return
            self._out_runner(2, "out at home")
            if self.outs < 3:
                self._runners_advance(1)
                self._reach(batter, 1, 0, "Infield in 6-8. Batter safe (page 19).", hit=False)
            return
        if total <= 10:
            self._reach(batter, 1, 1, "Infield in 9-10. Single through the drawn-in infield (page 19).", hit=True)
            return
        self.say("Infield in 11-12. Play at home (page 19).")
        self._play_at_home(batter)

    def _play_at_home(self, batter):
        if self.bases[2] is None:
            self._reach(batter, 1, 1, "No runner on third. Batter safe, runners advance 1.", hit=False)
            return
        runner = self.bases[2]
        a, b, total = self.dice.pair()
        pct = self.dice.pct()
        run = runner["run"] or 0
        self.say("Play at home. 2d6=%d, percentile %02d, RUN %s. Rolls %s." % (
            total, pct, run, ", ".join(self.dice.take())))
        if total > run:
            self._out_runner(2, "out at home")
        elif total < run:
            self._score_runner(2, "safe at home")
        else:
            if pct <= 49:
                die = self.dice.d6()
                catcher = self._fielder("C")
                err = self._error_of(catcher)
                self.say("Tie at home, percentile %02d. 1d6=%d against the catcher's error %s. Rolls %s." % (
                    pct, die, err, ", ".join(self.dice.take())))
                if err is not None and die > err:
                    self._line_field(self.fielding["code"], e=1)
                    self.say("The catcher drops the ball. The runner is safe (page 19).")
                else:
                    self.say("The catcher holds the ball. The runner still beats the throw (page 19).")
                self._score_runner(2, "safe at home")
            else:
                self._out_runner(2, "out at home on 50-99")
        if pct == 0:
            self._injury(self._fielder("C") or {}, "Normal")
        if pct == 99:
            person = self._person(self.batting, runner["id"])
            if person:
                self._injury(person, "Normal")
        self._runners_advance(1)
        if self.outs < 3:
            self._reach(batter, 1, 0, "Batter safe at first on the play at home (page 19).", hit=False)

    def _defense(self, batter, pitcher, reading, hit_and_run, pct):
        if self.deck:
            self._defense_fac(batter, pitcher, reading)
            return
        mode = reading.get("mode", "DEFENSE")
        slot = defense_slot(pct)
        self.say("Defense chart uses the at-bat percentile %02d (page 20)." % pct)
        if slot is None:
            self._rare(batter, pitcher, mode, 0, 0)
            return
        check, pos = slot
        if mode == "RANGE":
            check = "RANGE"
            if pos == "C":
                pos = "CF"
                self.say("RANGE selected the catcher. Page 2 says to use CF.")
        elif mode == "ERROR":
            check = "ERROR"
        self.say("Chart says %s at %s (page 20)." % (check, pos))
        a, b, total = self.dice.pair()
        park_pct = self.dice.pct()
        self.say("Re-roll all four dice (page 20): %s, percentile %02d. Rolls %s." % (
            self._fmt(a, b, total), park_pct, ", ".join(self.dice.take())))
        fielder = self._fielder(pos)
        if check == "RANGE":
            grade = self._range_of(fielder)
            hi = (self.park["range_hit_hi"] or {}).get(grade or "")
            if hi is None:
                self.gap("No range grade for %s. The park check cannot be read. Recorded as an out." % pos)
                self._record_out(batter, "DEF", "Defense out, missing range.")
                return
            self.say("Park range %s hits through %s at %s." % (grade, hi, self.park["name"]))
            if park_pct == 0 or park_pct > hi:
                self._defense_out(batter, pos, total)
                return
            hit, bases, dagger = HIT_BY_D6[total][POS_HIT_GROUP[pos]]
            if dagger and (batter["run"] or 0) >= 8 and hit == "2B":
                hit, bases = "3B", 3
                self.say("Dagger double becomes a triple. RUN is 8 or higher (page 20).")
            self._reach(batter, {"1B": 1, "2B": 2, "3B": 3}[hit], bases,
                        "Range hit %s. Runners advance %d (page 20 stars)." % (hit, bases), hit=True)
            return
        err = self._error_of(fielder)
        hi = (self.park["error_hi"] or {}).get(str(err) if err is not None else "")
        if hi is None:
            self.gap("No error number for %s. The park check cannot be read. Recorded as an out." % pos)
            self._record_out(batter, "DEF", "Defense out, missing error.")
            return
        self.say("Park error %s is an error through %s." % (err, hi))
        if park_pct == 0 or park_pct > hi:
            self._defense_out(batter, pos, total)
            return
        group = POS_ERR_GROUP[pos]
        outcome = ERR_BY_D6[total][group]
        if outcome == "FOUL":
            self.say("Dropped foul. The at-bat restarts (page 20).")
            self._restart_at_bat()
            return
        if outcome == "SINGLE+":
            self.say("SINGLE+error is a hit, and the runners take one extra base (page 20). The rate harness does not play it this way.")
            self._reach(batter, 1, 2, "Single plus an error.", hit=True, error=True)
            return
        self._reach(batter, int(outcome), int(outcome),
                    "%d-base error (page 20). The batter reaches on the error, which is not a hit." % int(outcome),
                    hit=False, error=True)

    def _defense_fac(self, batter, pitcher, reading):
        """DEFENSE draws the card's fielding line, then a park percentile, then the HIT/ERR/OUT row. Page 13."""
        mode = reading.get("mode", "DEFENSE")
        card = self.deck.draw("defense")
        info = card.get("defense") or {}
        self.say("FAC defense. %s. Rolls %s. (page 13)" % (info.get("text"), ", ".join(self.deck.take())))
        if info.get("check") == "RARE":
            self.say("DEF RARE PLAY. The next card names the fielder. The card after that is the rare-play percentile (page 13).")
            fielder_card = self.deck.draw("rare-fielder")
            named = fielder_card.get("defense") or {}
            self.say("Rare-play fielder card: %s. Rolls %s." % (named.get("text"), ", ".join(self.deck.take())))
            if named.get("check") == "RARE" or not named.get("pos"):
                self.gap("The card drawn for the rare-play fielder does not name a position. The at-bat is replayed. The book does not say to replay it.")
                self._restart_at_bat()
                return
            pct_card = self.deck.draw("rare-pct")
            self.say("Defense rare-play percentile %02d. Rolls %s." % (pct_card["pct"], ", ".join(self.deck.take())))
            self._rare(batter, pitcher, "DEFENSE", None, None, pct=pct_card["pct"])
            return
        check = info.get("check")
        pos = info.get("pos")
        if check not in {"RANGE", "ERROR"} or pos is None:
            self.gap("This FAC defense section could not be read (%s). Recorded as an out." % info.get("text"))
            self._record_out(batter, "DEF", "Unreadable defense card.")
            return
        if mode == "RANGE" and check != "RANGE":
            self.gap("The pitcher card says RANGE. The FAC says %s. The position comes from the card and the check is RANGE (page 2)." % check)
            check = "RANGE"
        elif mode == "ERROR" and check != "ERROR":
            self.gap("The pitcher card says ERROR. The FAC says %s. The position comes from the card and the check is ERROR." % check)
            check = "ERROR"
        if check == "RANGE" and pos == "C":
            pos = "CF"
            self.say("RANGE selected the catcher. Page 2 says to use CF.")
        park_card = self.deck.draw("park")
        park_pct = park_card["pct"]
        self.say("Park check percentile %02d. Rolls %s." % (park_pct, ", ".join(self.deck.take())))
        fielder = self._fielder(pos)
        if check == "RANGE":
            grade = self._range_of(fielder)
            hi = (self.park["range_hit_hi"] or {}).get(grade or "")
            if hi is None:
                self.gap("No range grade for %s. The park check cannot be read. Recorded as an out." % pos)
                self._record_out(batter, "DEF", "Defense out, missing range.")
                return
            self.say("Park range %s hits through %s at %s." % (grade, hi, self.park["name"]))
            band = "OUT" if park_pct == 0 or park_pct > hi else "HIT"
        else:
            err = self._error_of(fielder)
            hi = (self.park["error_hi"] or {}).get(str(err) if err is not None else "")
            if hi is None:
                self.gap("No error number for %s. The park check cannot be read. Recorded as an out." % pos)
                self._record_out(batter, "DEF", "Defense out, missing error.")
                return
            self.say("Park error %s is an error through %s." % (err, hi))
            band = "OUT" if park_pct == 0 or park_pct > hi else "ERR"
        self.say("Park check is %s. Symbols on the park card are ignored (page 13)." % band)
        played = self.deck.draw("defense-play")
        self.fac_result_card = played
        self.say("FAC %s row. Rolls %s." % (band, ", ".join(self.deck.take())))
        if band == "OUT":
            group = 0 if pos == "C" else 2 if pos in {"LF", "CF", "RF"} else 1
            text = (played.get("out") or [None, None, None])[group]
            kind = parse_out_cell(text) if text else None
            if kind is None:
                self.gap("OUT cell %s is not a printed result. Recorded as an out." % text)
                self._record_out(batter, "DEF", "Unreadable OUT cell.")
                return
            self._defense_out(batter, pos, None, kind)
            return
        if band == "ERR":
            group = POS_ERR_GROUP[pos]
            text = (played.get("err") or [None, None, None])[group]
            outcome = parse_err_cell(text) if text else None
            if outcome is None:
                self.gap("ERR cell %s is not a printed result. Recorded as an out." % text)
                self._record_out(batter, "DEF", "Unreadable ERR cell.")
                return
            if outcome == "FOUL":
                self.say("Dropped foul. The at-bat restarts (page 20).")
                self._restart_at_bat()
                return
            if outcome == "SINGLE+":
                self.say("SINGLE+error is a hit, and the runners take one extra base (page 20). The FAC error cell states that advance, so a SINGLE card is not also drawn.")
                self._reach(batter, 1, 2, "Single plus an error.", hit=True, error=True)
                return
            self._reach(
                batter, int(outcome), int(outcome),
                "%d-base error (page 20). The batter reaches on the error, which is not a hit." % int(outcome),
                hit=False, error=True,
            )
            return
        group = POS_HIT_GROUP[pos]
        text = (played.get("hit") or [None, None, None])[group]
        cell = parse_hit_cell(text) if text else None
        if cell is None:
            self.gap("HIT cell %s is not a printed result. Recorded as an out." % text)
            self._record_out(batter, "DEF", "Unreadable HIT cell.")
            return
        hit = cell["result"]
        bases = cell["bases"]
        if cell["dagger"] and (batter["run"] or 0) >= 8 and hit == "2B":
            hit, bases = "3B", 3
            self.say("Dagger double becomes a triple. RUN is 8 or higher (page 20).")
        if self.opts["running"] == "fac" and hit in {"1B", "2B"} and any(self.bases):
            self.say("HIT cell %s. The star advance is not used. The next card's %s section is the preferred advance (pages 13-14)." % (text, "SINGLE" if hit == "1B" else "DOUBLE"))
            self._fac_running(batter, hit)
            return
        self._reach(
            batter, {"1B": 1, "2B": 2, "3B": 3}[hit], bases,
            "Range hit %s from the FAC. Runners advance %d (the printed stars)." % (hit, bases),
            hit=True,
        )

    def _defense_out(self, batter, pos, total, kind=None):
        if kind is None:
            if pos in {"LF", "CF", "RF"}:
                group = 2
            elif pos == "C":
                group = 0
            else:
                group = 1
            kind = DEFENSE_OUT[total][group]
            self.say("Park check is OUT. Chart %s (page 20)." % kind)
        else:
            self.say("FAC OUT cell %s (page 20)." % kind)
        fielder = self._fielder(pos)
        if kind in {"POP", "POP-FOUL", "LINE"}:
            self._record_out(batter, kind, "Defense out. Runners hold.")
            return
        if kind == "GB-ADV":
            self._runners_advance(1)
            self._record_out(batter, kind, "Batter out. Runners advance 1.")
            return
        if kind == "GB-FC":
            if self.bases[0] is not None and self.outs < 2:
                self._out_runner(0, "forced")
                self._runners_advance(1)
                self._reach(batter, 1, 0, "Lead runner out, batter safe.", hit=False)
            else:
                self._record_out(batter, kind, "Nobody to force. Batter out.")
            return
        if kind in {"GB-DP-A", "GB-DP-AB"}:
            letters = {"A"} if kind.endswith("-A") else {"A", "B"}
            grade = self._range_of(fielder)
            if self.bases[0] is not None and self.outs < 2 and grade in letters:
                self._out_runner(0, "forced at second")
                self.gap("The defense OUT chart does not say whether other runners advance on a double play. They hold.")
                self._record_out(batter, kind, "Range %s matches. Double play (page 20)." % grade)
            elif self.bases[0] is not None and self.outs < 2:
                self._out_runner(0, "forced at second")
                self._reach(batter, 1, 0, "Range does not match. Batter safe (page 20).", hit=False)
            else:
                self._record_out(batter, kind, "No runner on first. Batter out.")
            return
        if kind == "LINE-DP-AB":
            grade = self._range_of(fielder)
            self._record_out(batter, kind, "Lineout.")
            self.gap("The defense lineout double play says the closest runner. It does not say how to measure closest. The lead runner is used.")
            if grade in {"A", "B"} and self.outs < 3:
                self._double_off_lead()
            return
        if kind == "DEEP":
            self._record_out(batter, kind, "Deep fly.")
            if self.outs >= 3:
                return
            for base in (2, 1):
                runner = self.bases[base]
                if runner is None:
                    continue
                if (runner["run"] or 0) >= 6:
                    if base == 2:
                        self._score_runner(2, "RUN 6 or higher tags on a deep fly")
                    else:
                        self._move_runner(1, 2, "RUN 6 or higher tags to third")
                else:
                    self.say("%s may try to tag. RUN is under 6 (page 20)." % runner["name"])
                    self._maybe_send(base, pos)
            return
        if kind == "SHORT":
            self._record_out(batter, kind, "Short fly. Runners hold. A runner on third may try with RUN reduced by 2 (page 20).")
            if self.bases[2] and self.outs < 3:
                self._maybe_send(2, pos, run_cut=2)
            return
        if kind == "SHORT-DP":
            arm = self._arm_of(fielder)
            self._record_out(batter, kind, "Short fly.")
            if arm is not None and arm <= 5 and self.outs < 3:
                self.say("Outfield arm %s is 5 or better. The lead runner is out (page 20). Lower numbers are the better arm (page 8)." % arm)
                self._double_off_lead()
            return
        self._record_out(batter, kind, "Defense out.")

    def _rare(self, batter, pitcher, result, one, two, pct=None):
        if pct is None:
            pct = self.dice.pct()
            self.say("Percentile 00. Rare play. Re-roll percentile %02d. Rolls %s. (page 4)" % (pct, ", ".join(self.dice.take())))
        else:
            self.say("Rare-play chart percentile %02d (page 13)." % pct)
        cell = rare_lookup(not any(self.bases), result, pct)
        self.say(cell["note"])
        if not cell["coded"]:
            self.gap(cell["note"])
            self._restart_at_bat()
            return
        event = cell["event"]
        if event == "NO_PLAY":
            self._injury(pitcher, "Normal")
            pitcher["removed"] = True
            self._restart_at_bat()
            return
        if event == "CATCHER_FOUL":
            catcher = self._fielder("C")
            if catcher:
                self._injury(catcher, "Normal")
            else:
                self.gap("The foul ball hits the catcher (page 22). Nobody is playing catcher, so the injury check cannot be read.")
            self._restart_at_bat()
            return
        if event == "OUT_REMOVE":
            self._record_out(batter, "RARE", cell["note"])
            self._injury(batter, "Normal")
            batter["removed"] = True
            return
        if event == "RUN5_1B_OR_2B_OUT3":
            if (batter["run"] or 0) <= 5:
                self._reach(batter, 1, 1, "RUN 5 or less. Single (page 22).", hit=True)
            else:
                self.say("RUN 6 or more reaches second, then is thrown out at third (page 22).")
                # _record_out charges the at-bat.
                self._line(batter, h=1, tb=2)
                self._record_out(batter, "RARE", "Out at third.")
            return
        if event == "REROLL":
            self._restart_at_bat()
            return
        if event == "WEATHER":
            die = self.dice.d6()
            self.say("Weather 1d6=%d. Rolls %s." % (die, ", ".join(self.dice.take())))
            if die >= 5:
                official = self.inning >= 6
                self.say(
                    "Game postponed%s (page 22). The rest of the game is not played."
                    % (" and official" if official else ", and not official")
                )
                self.postponed = True
                self.over = True
                self.outs = 3
            elif die >= 3:
                pitcher["removed"] = True
                other = self.pitcher[self.batting["code"]]["player"]
                other["removed"] = True
                self.say("Both pitchers must leave after the delay (page 22).")
            self._restart_at_bat()
            return
        if event == "RUN6_OUT_OR_1B":
            if (batter["run"] or 0) <= 6:
                self._record_out(batter, "RARE", cell["note"])
            else:
                self._reach(batter, 1, 1, cell["note"], hit=True)
            return
        if event == "HR_UNLESS_CF_A":
            cf = self._fielder("CF")
            if self._range_of(cf) == "A":
                self._record_out(batter, "RARE", "CF range A takes the home run away.")
            else:
                self._reach(batter, 4, 4, "Home run.", hit=True)
            return
        if event == "OUT_UNLESS_NOT_LF_A":
            lf = self._fielder("LF")
            if self._range_of(lf) == "A":
                self._record_out(batter, "RARE", "LF range A, batter out.")
            else:
                self._reach(batter, 1, 1, "Single.", hit=True)
            return
        if event == "SO_DROP":
            total = self.dice.pair()[2]
            self.say("Dropped third strike check 2d6=%d against RUN %s." % (total, batter["run"]))
            self.dice.take()
            if batter["run"] is not None and total <= batter["run"]:
                self._reach(batter, 1, 1, "Safe at first on the drop. Still a strikeout, and the side needs four outs. The extra out is not added; that lasting effect is unmodeled.", hit=False)
                self.gap("Page 23 gives the batting team an extra out on this drop. This game does not change the number of outs in the inning.")
                # _reach already charged the at-bat; add only the strikeout.
                self._line(batter, so=1)
            else:
                self._record_out(batter, "SO", "Strikeout, catcher throws him out.")
            return
        if event in {"BB", "HBP"}:
            self._walk(batter, event)
            return
        if event == "SO":
            self._record_out(batter, "SO", cell["note"])
            return
        if event == "OUT":
            self._record_out(batter, "RARE", cell["note"])
            return
        if event == "1B":
            self._reach(batter, 1, 1, cell["note"], hit=True)
            return
        if event == "2B":
            self._reach(batter, 2, 2, cell["note"], hit=True)
            return
        self.gap("Rare event %s has no applier." % event)
        self._restart_at_bat()

    def _injury(self, player, default):
        rating = None
        if player:
            rating = (player.get("addendum") or {}).get("inj")
            if not rating and player.get("bat"):
                rating = player["bat"].get("inj")
        if rating not in {"Prone", "Normal", "Durable", "Iron"}:
            name = player.get("name") if player else "The player"
            self.gap("%s has no injury rating. The page 21 check is skipped. A Normal rating is not assumed." % name)
            return
        pct = self.dice.pct()
        result = injury_result(rating, pct)
        self.say("Injury check %s (%s) percentile %02d -> %s (page 21)." % (player["name"], rating, pct, result))
        self.dice.take()
        if result and result != "ok":
            player["removed"] = True
            self.say("%s is injured and leaves." % player["name"])

    # --- bases and box ---

    def _reach(self, batter, batter_bases, runner_bases, text, hit, error=False, hold_lead=False):
        if self.outs >= 3:
            # A runner made the third out on the play (e.g. trying for an
            # extra base). The batter still has his at-bat and his hit.
            if hit:
                bases = min(batter_bases, 4)
                self._line(batter, ab=1, h=1, hr=1 if bases == 4 else 0, tb=bases)
                self.say("%s The inning ended on the bases; the batter is credited with the hit." % text)
            else:
                self._line(batter, ab=1)
                if error:
                    self._line_field(self.fielding["code"], e=1)
            return
        self.say(text)
        if batter_bases >= 4:
            self._runners_advance(4)
            self._score_batter(batter, hit)
            self._line(batter, ab=1, h=1, hr=1, tb=4)
            return
        if not hold_lead:
            self._runners_advance(runner_bases)
        self._place(batter, batter_bases)
        self._line(batter, ab=1, h=1 if hit else 0, tb=batter_bases if hit else 0)
        if error and not hit:
            self._ue.add(batter["id"])
            if self._pa is not None:
                self._pa["on_error"] = True
            self._line_field(self.fielding["code"], e=1)
        self._after_reach(batter)

    def _walk(self, batter, event):
        self.say("%s. Forced runners advance (page 5)." % event)
        self._force_one()
        self._place(batter, 1)
        if event == "BB":
            self._line(batter, bb=1)
        else:
            self._line(batter, hbp=1)
        self._after_reach(batter)

    def _record_out(self, batter, kind, text):
        self.say(text)
        if self.outs >= 3:
            return
        self.outs += 1
        self._charge_out(batter, kind)
        state = self.pitcher[self.fielding["code"]]
        state["outs"] += 1
        self._pitch_line(outs=1)

    def _charge_out(self, batter, kind):
        so = 1 if kind == "SO" else 0
        ab = 0 if kind in {"SH", "SF"} else 1
        self._line(batter, ab=ab, so=so, sf=1 if kind == "SF" else 0, sh=1 if kind == "SH" else 0)
        if kind == "SF":
            self._count_sac_fly(batter, kind)

    def _count_sac_fly(self, batter, kind):
        return

    def _charge_so(self, batter):
        self._line(batter, ab=1, so=1)

    def _score_batter(self, batter, hit):
        self._resp.setdefault(batter["id"], self._pkey())
        self._run_scores(batter)
        self.say("%s scores." % batter["name"])

    def _runners_advance(self, n):
        if n <= 0 or self.outs >= 3:
            return
        for base in (2, 1, 0):
            if self.bases[base] is None:
                continue
            dest = base + n
            runner = self.bases[base]
            self.bases[base] = None
            if dest >= 3:
                self._run_scores(runner)
                self.say("%s scores from %s." % (runner["name"], _base_name(base)))
            else:
                self.bases[dest] = runner
                self.say("%s to %s." % (runner["name"], _base_name(dest)))

    def _force_one(self):
        # Advance only runners who are forced, from the lead forced base backward.
        forced = [False, False, False]
        if self.bases[0]:
            forced[0] = True
            if self.bases[1]:
                forced[1] = True
                if self.bases[2]:
                    forced[2] = True
        for base in (2, 1, 0):
            if not forced[base] or self.bases[base] is None:
                continue
            runner = self.bases[base]
            self.bases[base] = None
            if base == 2:
                self._run_scores(runner)
                self.say("%s scores on the force." % runner["name"])
            else:
                self.bases[base + 1] = runner
                self.say("%s forced to %s." % (runner["name"], _base_name(base + 1)))

    def _place(self, batter, bases):
        dest = bases - 1
        if dest >= 3:
            self._score_batter(batter, True)
            return
        self.bases[dest] = {"id": batter["id"], "name": batter["name"], "run": batter["run"], "steal": batter["steal"]}
        self.say("%s to %s." % (batter["name"], _base_name(dest)))

    def _out_runner(self, base, text):
        runner = self.bases[base]
        if runner is None or self.outs >= 3:
            return
        self.bases[base] = None
        self.outs += 1
        self.pitcher[self.fielding["code"]]["outs"] += 1
        self._pitch_line(outs=1)
        self.say("%s is %s. %d out." % (runner["name"], text, self.outs))

    def _score_runner(self, base, text):
        runner = self.bases[base]
        if runner is None or self.outs >= 3:
            return
        self.bases[base] = None
        self._run_scores(runner)
        self.say("%s %s." % (runner["name"], text))

    def _move_runner(self, src, dest, text):
        runner = self.bases[src]
        if runner is None or self.bases[dest] is not None or self.outs >= 3:
            return
        self.bases[src] = None
        self.bases[dest] = runner
        self.say("%s %s." % (runner["name"], text))

    def _lead_base(self):
        for base in (2, 1, 0):
            if self.bases[base]:
                return base
        return None

    def _double_off_lead(self):
        lead = self._lead_base()
        if lead is None:
            return
        self._out_runner(lead, "doubled off")

    def _lead_out_batter_safe(self, batter, text):
        lead = self._lead_base()
        if lead is not None:
            self._out_runner(lead, "thrown out")
        if self.outs < 3:
            self._runners_advance(1)
            self._reach(batter, 1, 0, text, hit=False)

    def _after_reach(self, batter):
        if self.outs >= 3:
            return
        if self.opts["steal"] == "off":
            return
        # The runner who just reached, if the next base is open. Page 7 option 2.
        for base in (1, 0):
            runner = self.bases[base]
            if runner and runner["id"] == batter["id"] and self.bases[base + 1] is None:
                self._auto_steal(base, batter)
                return

    def _auto_steal(self, base, batter):
        steal = batter["steal"] or {}
        jump = steal.get("jump")
        letter = steal.get("rating")
        if batter["id"] in self.jump_closed:
            self.say("%s used a Jump of 1 earlier. Page 39 says he is not checked again." % batter["name"])
            return
        if not jump or not letter:
            self.say("%s has no jump rating. Page 7 says he does not auto-steal." % batter["name"])
            return
        jump = self._jump_this_time(batter, jump, steal.get("jump_mod"))
        if jump is None:
            return
        if self.deck:
            card = self.fac_result_card
            if card is None:
                card = self.deck.draw("auto-steal")
                self.deck.take()
                self.gap("Auto steal had no result card saved. A new card's 2d6 is used. Page 13 allows drawing the next card.")
            else:
                self.say("Auto steal uses 2d6=%s on the card that resolved the play (page 13)." % card["d6_2"])
            a, b, total = None, None, card["d6_2"]
        else:
            # Use a fresh 2d6. The book says "compare the 2d6 total" and does not say it is a new roll.
            self.gap("Auto steal compares a 2d6 to Jump (page 7). It does not say whether that is the at-bat's 2d6 or a new roll. This game rolls a new 2d6.")
            a, b, total = self.dice.pair()
            self.say("Auto-steal check %s against jump %s. Rolls %s." % (self._fmt(a, b, total), jump, ", ".join(self.dice.take())))
        if self.deck:
            self.say("Auto-steal check 2d6=%s against jump %s." % (total, jump))
        if total == 12:
            self._pickoff(batter)
            return
        if base == 1 and not self._is_doubles(a, b, "Stealing third"):
            self.say("Stealing third needs doubles (page 7). He does not go.")
            return
        if total > jump:
            self.say("No steal.")
            return
        self._resolve_steal(base, letter, batter)

    def _jump_this_time(self, batter, jump, mod):
        first = batter["id"] not in self.jump_seen
        if first:
            self.jump_seen.add(batter["id"])
            if jump == 1:
                self.jump_closed.add(batter["id"])
                self.say("%s has Jump 1. Page 39 uses 2 this time and does not check him again." % batter["name"])
                return 2
            if mod == "+":
                self.say("Jump + applies the first time %s reaches with a steal chance (pages 8 and 39). Jump is %s." % (batter["name"], jump + 1))
                return jump + 1
            if mod == "-":
                adjusted = max(1, jump - 1)
                self.say("Jump - applies the first time %s reaches with a steal chance (pages 8 and 39). Jump is %s." % (batter["name"], adjusted))
                return adjusted
        return jump

    def _hold_steal(self):
        """Page 7 option 3. Not the default. A fresh 2d6 is a choice the book does not require."""
        self.gap("Hold stealing rolls four dice and compares the 2d6 to Hold (page 7). It does not say this roll is separate from the at-bat. This game rolls a new 2d6 before the pitch.")
        lead = None
        for base in (1, 0):
            if self.bases[base] and (base == 1 or self.bases[1] is None) and (base == 0 or self.bases[2] is None):
                if self.bases[base + 1] is None:
                    lead = base
                    break
        if lead is None:
            return
        runner = self.bases[lead]
        hold = self.pitcher[self.fielding["code"]]["player"]["addendum"].get("hold")
        if hold is None:
            self.gap("Hold stealing needs the pitcher's Hold rating (page 7). This pitcher has none. The runner stays.")
            return
        a, b, total = self.dice.pair()
        self.say("Hold steal check %s against Hold %s. Rolls %s." % (self._fmt(a, b, total), hold, ", ".join(self.dice.take())))
        if total == 12:
            self._pickoff_runner(lead)
            return
        letter = (runner.get("steal") or {}).get("rating")
        if lead == 1 and not self._is_doubles(a, b, "Stealing third"):
            self.say("Stealing third needs doubles (page 7). He does not go.")
            return
        if total <= int(hold):
            if not letter:
                self.gap("The runner has no steal letter. The Hold steal cannot be read.")
                return
            self._resolve_steal(lead, letter, runner)
            return
        self.say("The jump is not good enough. He does not steal (page 7).")

    def _steal_lead(self, must):
        lead = self._lead_base()
        if lead is None or self.bases[min(lead + 1, 2)] is not None and lead < 2:
            return
        runner = self.bases[lead]
        letter = (runner.get("steal") or {}).get("rating")
        if not letter:
            self.gap("The lead runner has no steal letter. The required steal cannot be read.")
            return
        self._resolve_steal(lead, letter, runner)

    def _resolve_steal(self, base, letter, runner):
        catcher = self._fielder("C")
        arm = self._arm_of(catcher)
        if arm is None or not 1 <= int(arm) <= 5:
            self.gap(
                "Catcher arm is %s. Page 8 rates a catcher from 1 to 5, 1 the best. Roster catcher arms were re-rated onto that scale from caught-stealing rates (see engines/sim/catcher_arm_rerate.json). An arm outside 1-5 is not on the steal chart, so the runner holds."
                % arm
            )
            return
        column = STEAL_COLUMN.get("%s%s" % (letter, int(arm)))
        if column is None:
            self.gap("No stealing column for %s%s." % (letter, arm))
            return
        if self.deck:
            previous = self.deck.last
            card = self.deck.draw("steal")
            self.say(
                "FAC steal. %s%s is %s. Rolls %s. (pages 13-14)"
                % (letter, int(arm), column, ", ".join(self.deck.take()))
            )
            special = (card.get("steal") or {}).get("special")
            if special:
                die = previous["d6_1"] if previous else None
                self.say("Printed instruction: %s" % special)
                if die is None:
                    self.gap("The card says to use the previous card's 1d6. No previous card was drawn. The steal is not given a result.")
                    return
                self.say("Previous card 1d6=%s. 1-3 is out and the runner is checked. 4-6 is safe and the fielder is checked." % die)
                if die <= 3:
                    self._out_runner(base, "caught stealing")
                    self._line_id(self.batting["code"], runner["id"], cs=1)
                    person = self._person(self.batting, runner["id"]) or runner
                    self._injury(person, "Normal")
                else:
                    self._move_runner(base, base + 1, "steals")
                    self._line_id(self.batting["code"], runner["id"], sb=1)
                    self._injury(self._fielder("C") or {}, "Normal")
                return
            outcome = (card.get("steal") or {}).get("grades", {}).get(column)
            if outcome == "Safe":
                self._move_runner(base, base + 1, "steals")
                self._line_id(self.batting["code"], runner["id"], sb=1)
            elif outcome == "Out":
                self._out_runner(base, "caught stealing")
                self._line_id(self.batting["code"], runner["id"], cs=1)
            elif outcome == "SB+E2?":
                self._fac_steal_error(base, runner, card)
            elif outcome == "Drop?":
                self._fac_steal_drop(base, runner, card)
            else:
                self.gap("This FAC has no stealing result for %s. The runner holds." % column)
            return
        pct = self.dice.pct()
        result = steal_result(column, pct)
        self.say("Steal %s vs arm %s is %s. Percentile %02d -> %s. Rolls %s. (page 18)" % (
            letter, arm, column, pct, result, ", ".join(self.dice.take())))
        if result == "SAFE":
            self._move_runner(base, base + 1, "steals")
            self._line_id(self.batting["code"], runner["id"], sb=1)
        elif result == "CAUGHT":
            self._out_runner(base, "caught stealing")
            self._line_id(self.batting["code"], runner["id"], cs=1)
        elif result == "E2":
            self._move_runner(base, base + 1, "safe, throw sails (page 18)")
            self._line_id(self.batting["code"], runner["id"], sb=1)
            self._line_field(self.fielding["code"], e=1)
            self._runners_advance(1)
        else:
            self.say("DROP on the steal chart. 1d6 against the fielder's error (page 18).")
            cover = "SS" if _stand(runner.get("bats", "R"), "R") == "L" else "2B"
            # The key says SS covers for a LHB and 2B for a RHB. The batter's hand is the one that matters.
            self.gap("The steal DROP fielder depends on the batter's hand (page 18). The runner's hand was used when the batter had already reached. That may be the wrong hand.")
            fielder = self._fielder(cover)
            die = self.dice.d6()
            err = self._error_of(fielder)
            self.say("1d6=%d, %s error %s." % (die, cover, err))
            self.dice.take()
            if err is None or die > err:
                self._move_runner(base, base + 1, "safe, ball dropped")
                self._line_id(self.batting["code"], runner["id"], sb=1)
                self._line_field(self.fielding["code"], e=1)
            else:
                self._out_runner(base, "caught, fielder holds the ball")
                self._line_id(self.batting["code"], runner["id"], cs=1)

    def _fac_steal_error(self, base, runner, card):
        """SB+E2? on the card. The runner is safe. 1d6 against the catcher's error decides the wild throw. Page 18."""
        self._move_runner(base, base + 1, "safe")
        self._line_id(self.batting["code"], runner["id"], sb=1)
        die = card["d6_1"]
        catcher = self._fielder("C")
        err = self._error_of(catcher)
        self.say("SB+E2? uses 1d6=%s on this card against the catcher's error %s (page 18)." % (die, err))
        if err is None or die > err:
            self.say("The throw sails. Runners advance 1.")
            self._line_field(self.fielding["code"], e=1)
            self._runners_advance(1)
        else:
            self.say("The throw is late and on target. No extra base.")

    def _fac_steal_drop(self, base, runner, card):
        """Drop? on the card. 1d6 on this card against the covering fielder. Page 18."""
        cover = "SS" if _stand(runner.get("bats", "R"), "R") == "L" else "2B"
        self.gap("The steal DROP fielder depends on the batter's hand (page 18). The runner's hand was used when the batter had already reached. That may be the wrong hand.")
        fielder = self._fielder(cover)
        die = card["d6_1"]
        err = self._error_of(fielder)
        self.say("Drop? 1d6=%s on this card, %s error %s (page 18)." % (die, cover, err))
        if err is None or die > err:
            self._move_runner(base, base + 1, "safe, ball dropped")
            self._line_id(self.batting["code"], runner["id"], sb=1)
            self._line_field(self.fielding["code"], e=1)
        else:
            self._out_runner(base, "caught, fielder holds the ball")
            self._line_id(self.batting["code"], runner["id"], cs=1)

    def _pickoff_runner(self, base):
        runner = self.bases[base]
        if runner is None:
            return
        hold = self.pitcher[self.fielding["code"]]["player"]["addendum"].get("hold")
        if hold is None:
            self.gap("2d6 is 12. The pickoff chart needs a Hold rating (page 8). This pitcher has none. The runner stays.")
            return
        pct = self.dice.pct()
        result = pickoff_result(int(hold), pct)
        self.say("Pickoff. Hold %s, percentile %02d -> %s (page 18)." % (hold, pct, result))
        self.dice.take()
        if result == "CAUGHT":
            self._out_runner(base, "picked off")
            self._line_id(self.batting["code"], runner["id"], po=1)
        elif result == "BALK":
            self.say("Balk. Runners advance 1 (page 18).")
            self._runners_advance(1)
        elif result == "WILD":
            self.say("The pickoff throw is wild. The chart's error detail is applied as one base.")
            self.gap("A wild pickoff throw has a second error roll on page 18. This game advances every runner one base and does not assign the error.")
            self._runners_advance(1)
        else:
            self.say("The pickoff throw is late. The runner is safe.")

    def _pickoff(self, batter):
        hold = self.pitcher[self.fielding["code"]]["player"]["addendum"].get("hold")
        if hold is None:
            self.gap("2d6 is 12. The pickoff chart needs a Hold rating (page 8). This pitcher has none. The runner stays.")
            return
        pct = self.dice.pct()
        result = pickoff_result(int(hold), pct)
        self.say("Pickoff. Hold %s, percentile %02d -> %s (page 18)." % (hold, pct, result))
        self.dice.take()
        if result == "CAUGHT":
            base = next((b for b in (0, 1, 2) if self.bases[b] and self.bases[b]["id"] == batter["id"]), None)
            if base is None:
                base = self._lead_base()
            if base is not None:
                picked = self.bases[base]
                self._out_runner(base, "picked off")
                # A pickoff is not a caught stealing unless he was running.
                # The auto-steal pickoff fires before the jump check, so it is
                # scored as a pickoff (po), not cs.
                self._line_id(self.batting["code"], picked["id"], po=1)
        elif result == "BALK":
            self.say("Balk. Runners advance 1 (page 18).")
            self._runners_advance(1)
        elif result == "WILD":
            self.say("Pickoff throw is wild. Runner is safe and the chart's error detail is applied as one base.")
            self._runners_advance(1)
        else:
            self.say("Pickoff throw is late. Runner is safe.")

    def _extra_base(self, base, pos, run_cut=0):
        runner = self.bases[base]
        if runner is None or self.outs >= 3:
            return
        fielder = self._fielder(pos) if pos else None
        arm = self._arm_of(fielder) if fielder else None
        run = runner["run"] if runner["run"] is not None else 0
        run = max(0, run - run_cut)
        if arm is None:
            self.gap("No outfield arm at %s. The extra-base chart needs RUN and ARM (page 16). He holds." % pos)
            return
        a, b, total = self.dice.pair()
        self.say("Extra base. 2d6=%d, RUN %s, ARM %s. Rolls %s." % (total, run, arm, ", ".join(self.dice.take())))
        if total <= run and total <= arm:
            self._advance_one(base, "safe. The roll is within both ratings (page 16).")
            return
        if total > run and total > arm:
            self._out_runner(base, "out trying for the extra base")
            self._runners_advance(1)
            return
        pct = self.dice.pct()
        self.say("Split ratings. Percentile %02d. Rolls %s." % (pct, ", ".join(self.dice.take())))
        if pct <= 10:
            die = self.dice.d6()
            err = self._error_of(fielder)
            self.dice.take()
            if err is None or die > err:
                self._advance_one(base, "ball dropped")
                self._line_field(self.fielding["code"], e=1)
            else:
                self._out_runner(base, "fielder holds on")
        elif pct <= 45:
            self._out_runner(base, "thrown out")
            self._runners_advance(1)
        elif pct <= 55:
            self._advance_one(base, "wild throw, safe")
        else:
            self._advance_one(base, "safe")

    def _advance_one(self, base, text):
        runner = self.bases[base]
        if runner is None:
            return
        if base == 2:
            self._score_runner(2, text)
        else:
            self._move_runner(base, base + 1, text)

    def _fielder(self, pos):
        if pos == "P":
            return self.pitcher[self.fielding["code"]]["player"]
        found = self.defense.get(self.fielding["code"], {}).get(pos)
        if found is None:
            self.gap("Nobody is playing %s. The roster does not fill that position." % pos)
        return found

    def _grade_row(self, fielder, pos):
        if fielder is None:
            return None
        for row in fielder["positions"]:
            if row.get("pos") == pos or (pos == "P" and row.get("pos") in {"P", "SP", "RP"}):
                return row
        if fielder["positions"]:
            return fielder["positions"][0]
        return None

    def _range_of(self, fielder):
        if fielder is None:
            return None
        if not fielder["positions"]:
            self.gap("%s has no fielding line. Range is not invented." % fielder["name"])
            return None
        row = fielder["positions"][0]
        if row.get("range") == "C" and row.get("e") == 4 and fielder.get("fielding_label") == "Average":
            self.gap("%s fielding is the engine Average default (range C, error 4), not a printed rating." % fielder["name"])
        return row.get("range")

    def _error_of(self, fielder):
        if fielder is None:
            return None
        if not fielder["positions"]:
            if fielder is self.pitcher[self.fielding["code"]]["player"]:
                self.gap("%s has no fielding line on the pitcher card. Error and range checks against him have no rating." % fielder["name"])
            return None
        row = fielder["positions"][0]
        if row.get("range") == "C" and row.get("e") == 4 and fielder.get("fielding_label") == "Average":
            self.gap("%s fielding is the engine Average default (range C, error 4), not a printed rating." % fielder["name"])
        return row.get("e")

    def _arm_of(self, fielder):
        if fielder is None or not fielder["positions"]:
            return None
        return fielder["positions"][0].get("arm")

    def _supplemental_strikeout(self, pitcher, pct):
        if not self.opts["supplemental_so"]:
            return False
        band = pitcher.get("so_band")
        if not band:
            # Page 11: only "some pitchers" carry the band. No band, no change.
            return False
        return band[0] <= pct <= band[1]

    def _person(self, club, pid):
        for player in club["people"]:
            if player["id"] == pid:
                return player
        return None

    def _pitch_line(self, **add):
        state = self.pitcher.get(self.fielding["code"])
        if not state:
            return
        player = state["player"]
        row = self.pitch_box.setdefault(self.fielding["code"] + "|" + player["id"], _empty_pitch(player["name"]))
        for key, amount in add.items():
            row[key] = row.get(key, 0) + amount

    def _line(self, batter, **add):
        row = self.box.setdefault(self.batting["code"] + "|" + batter["id"], _empty_line(batter))
        for key, amount in add.items():
            row[key] = row.get(key, 0) + amount
        charge = {k: add[k] for k in ("h", "bb", "so", "hr", "hbp") if add.get(k)}
        if charge:
            self._pitch_line(**charge)

    def _line_id(self, code, pid, **add):
        row = self.box.setdefault(code + "|" + pid, {"id": pid, "name": pid, "ab": 0, "r": 0, "h": 0, "hr": 0, "rbi": 0, "bb": 0, "so": 0, "hbp": 0, "sb": 0, "cs": 0, "po": 0, "sf": 0, "sh": 0, "tb": 0})
        for key, amount in add.items():
            row[key] = row.get(key, 0) + amount

    def _line_field(self, code, e=0):
        self.box.setdefault(code + "|field", {"e": 0})
        self.box[code + "|field"]["e"] += e
        if code == self.fielding["code"]:
            self._half_err += e

    def report(self):
        return {
            "away": self.away["code"],
            "home": self.home["code"],
            "score": dict(self.score),
            "innings": self.inning if self.inning < 90 else self.inning,
            "seed": self.seed,
            "park": self.park["name"],
            "park_stand_in": self.park.get("stand_in"),
            "log": self.log,
            "gaps": self.gaps,
            "box": self.box,
            "pitching": self.pitch_box,
            "decisions": self._decisions(),
            "options": self.opts,
            "postponed": self.postponed,
            "wp": {
                "seen": self.wp_seen,
                "fired": self.wp_fired,
                "miss": self.wp_miss,
                "empty": self.wp_empty,
                "no_rating": self.wp_no_rating,
                "unmarked": self.wp_unmarked,
            },
        }


def _empty_pitch(name):
    return {"name": name, "outs": 0, "bf": 0, "h": 0, "r": 0, "er": 0, "bb": 0, "so": 0, "hr": 0, "hbp": 0}


def _empty_line(batter):
    return {
        "id": batter["id"], "name": batter["name"], "pos": batter["pos"],
        "ab": 0, "r": 0, "h": 0, "hr": 0, "rbi": 0, "bb": 0, "so": 0,
        "hbp": 0, "sb": 0, "cs": 0, "po": 0, "sf": 0, "sh": 0, "tb": 0,
    }


def _base_name(base):
    return ("first", "second", "third")[base]


def _bump(modifier):
    text = str(modifier or "NONE")
    if text in {"NONE", "None", ""}:
        return 0
    return int(text.replace("+", ""))


def _so_hi(table):
    band = (table or {}).get("SO")
    if not band or len(band) < 2 or band[1] is None:
        return None
    return int(band[1])


def _hr_blank(table):
    band = (table or {}).get("HR")
    if not band:
        return True
    if isinstance(band, (int, float)):
        return int(band) == 0
    if len(band) < 2 or band[0] is None or band[1] is None:
        return True
    return int(band[0]) == 0 and int(band[1]) == 0


def play(home_code, away_code, seed=1, **opts):
    home = load_club(home_code)
    away = load_club(away_code)
    game = Game(home, away, seed=seed, **opts)
    # Fix the unused helper's stand by binding the real batter inside _read_batter.
    return game.play()


def render(report):
    lines = list(report["log"])
    lines.append("")
    lines.append("Pitching")
    for key, row in sorted(report.get("pitching", {}).items()):
        outs = row.get("outs") or 0
        lines.append("%s %s IP %d.%d H %s R %s ER %s BB %s SO %s HR %s BF %s" % (
            key, row.get("name"), outs // 3, outs % 3, row.get("h", 0), row.get("r"), row.get("er", 0),
            row.get("bb", 0), row.get("so", 0), row.get("hr", 0), row.get("bf")))
    dec = report.get("decisions") or {}
    if dec:
        lines.append("W %s  L %s  S %s  H %s" % (dec.get("W"), dec.get("L"), dec.get("S") or "-",
                                                  ", ".join(dec.get("H") or []) or "-"))
    lines.append("")
    lines.append("Box")
    for key, row in sorted(report["box"].items()):
        if key.endswith("|field"):
            lines.append("%s errors %s" % (key, row.get("e")))
            continue
        lines.append(
            "%s %s AB %s R %s H %s HR %s RBI %s BB %s SO %s SB %s CS %s"
            % (key, row.get("name"), row.get("ab"), row.get("r"), row.get("h"),
               row.get("hr"), row.get("rbi"), row.get("bb"), row.get("so"), row.get("sb"), row.get("cs"))
        )
    if report["gaps"]:
        lines.append("")
        lines.append("Gaps named during the game")
        for gap in report["gaps"]:
            lines.append("- " + gap)
    return "\n".join(lines) + "\n"
