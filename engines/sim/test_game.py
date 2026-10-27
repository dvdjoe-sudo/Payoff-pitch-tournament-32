"""Checks for one full Payoff Pitch game. Nothing here writes a played game."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from book import sac_result, steal_home_result, steal_result, wp_hit
from game import Game, load_club, play


class Bag:
    def __init__(self, rolls):
        self.rolls = list(rolls)

    def randint(self, lo, hi):
        if not self.rolls:
            raise AssertionError("scripted dice ran out")
        value = self.rolls.pop(0)
        if not lo <= value <= hi:
            raise AssertionError("roll %s is outside %s-%s" % (value, lo, hi))
        return value


def game():
    found = Game(load_club("BOS"), load_club("TOR"), seed=1, steal="off", fac=False)
    found.dice.rng = Bag([])
    return found


def feed(found, rolls):
    found.dice.rng = Bag(rolls)


def runner(pid, run=6):
    return {"id": pid, "name": pid, "run": run, "steal": {"jump": 4, "rating": "A", "jump_mod": None}}


def arm(found, code, pos, number):
    fielder = found.defense[code][pos]
    fielder["positions"][0]["arm"] = number
    return fielder


def chart_faces():
    assert steal_result("EXCELLENT", 0) == "DROP"
    assert steal_result("EXCELLENT", 12) == "E2"
    assert steal_result("EXCELLENT", 17) == "CAUGHT"
    assert steal_result("EXCELLENT", 18) == "SAFE"
    assert steal_result("POOR", 84) == "CAUGHT"
    assert steal_result("POOR", 85) == "SAFE"
    assert steal_home_result("A", 9) == "DROP"
    assert steal_home_result("A", 69) == "CAUGHT"
    assert steal_home_result("A", 70) == "SAFE"
    assert steal_home_result("F", 98) == "CAUGHT"
    assert steal_home_result("F", 99) == "SAFE"
    assert sac_result("A", 0) == "PO"
    assert sac_result("A", 2) == "DP"
    assert sac_result("A", 6) == "LEAD"
    assert sac_result("A", 20) == "SH"
    assert sac_result("A", 93) == "MISS"
    assert sac_result("A", 99) == "E"
    assert wp_hit("30-32", 31) is True
    assert wp_hit("30-32", 29) is False
    assert wp_hit("30", 30) is True
    assert wp_hit("30", 31) is False
    assert wp_hit(None, 30) is False


def basic_running_and_walks():
    found = game()
    batter = found.away["lineup"][0]
    found.bases = [None, runner("second", 8), None]
    found.outs = 0
    found._finish_event(batter, found.pitcher["BOS"]["player"], "1B", "IN-PLAY", 11, 3, 4, False)
    assert found.bases[0]["id"] == batter["id"]
    assert found.bases[2]["id"] == "second"
    assert found.score["TOR"] == 0

    found = game()
    batter = found.away["lineup"][0]
    found.bases = [None, runner("second", 8), None]
    found.outs = 2
    found._finish_event(batter, found.pitcher["BOS"]["player"], "1B", "IN-PLAY", 11, 3, 4, False)
    assert found.score["TOR"] == 1
    assert found.bases[0]["id"] == batter["id"]

    found = game()
    batter = found.away["lineup"][0]
    found.bases = [runner("first"), runner("second"), None]
    found._walk(batter, "BB")
    assert found.bases[0]["id"] == batter["id"]
    assert found.bases[1]["id"] == "first"
    assert found.bases[2]["id"] == "second"
    assert found.score["TOR"] == 0
    assert found.box["TOR|" + batter["id"]]["ab"] == 0
    assert found.box["TOR|" + batter["id"]]["bb"] == 1


def double_play_fly_and_bunt():
    found = game()
    batter = found.away["lineup"][0]
    batter["dp"] = 12
    pitcher = found.pitcher["BOS"]["player"]
    pitcher["addendum"]["dp"] = 12
    found.bases = [runner("first"), runner("second"), None]
    found.outs = 0
    feed(found, [1, 1])
    found._ground(batter, "G6", pitcher, 15)
    assert found.outs == 2
    assert found.bases[0]["id"] == "first"
    assert found.bases[1] is None
    assert any("does not say what the runner on first does" in gap for gap in found.gaps)

    found = game()
    batter = found.away["lineup"][0]
    batter["dp"] = 6
    pitcher = found.pitcher["BOS"]["player"]
    pitcher["addendum"]["dp"] = 6
    found.bases = [runner("first"), None, None]
    feed(found, [6, 4])
    found._ground(batter, "G4", pitcher, 14)
    assert found.outs == 1
    assert found.bases[0]["id"] == batter["id"]

    found = game()
    batter = found.away["lineup"][0]
    batter["dp"] = 6
    pitcher = found.pitcher["BOS"]["player"]
    pitcher["addendum"]["dp"] = 6
    found.bases = [runner("first"), None, None]
    feed(found, [6, 6])
    found._ground(batter, "G4", pitcher, 14)
    assert found.outs == 1
    assert found.bases[1]["id"] == "first"
    assert found.bases[0] is None

    found = game()
    batter = found.away["lineup"][0]
    found.outs = 2
    found.bases = [None, None, runner("third")]
    found._fly(batter, "F8", "WHEELHOUSE", 10)
    assert found.outs == 3
    assert found.score["TOR"] == 0

    found = game()
    batter = found.away["lineup"][0]
    found.outs = 0
    found.bases = [None, None, runner("third")]
    found._fly(batter, "F8", "WHEELHOUSE", 10)
    assert found.score["TOR"] == 1
    row = found.box["TOR|" + batter["id"]]
    assert row["sf"] == 1 and row["ab"] == 0

    found = game()
    batter = found.away["lineup"][7]
    found.bases = [runner("first"), None, None]
    feed(found, [1, 2, 0])
    found._bunt(batter, "A", False)
    assert found.outs == 1
    assert found.bases[1]["id"] == "first"
    assert found.box["TOR|" + batter["id"]]["sh"] == 1
    assert found.box["TOR|" + batter["id"]]["ab"] == 0


def steal_defense_and_pitch_quality():
    found = game()
    arm(found, "BOS", "C", 3)
    who = runner("thief", 8)
    found.bases = [who, None, None]
    feed(found, [5, 0])
    found._resolve_steal(0, "A", who)
    assert found.bases[1]["id"] == "thief"
    assert found.box["TOR|thief"]["sb"] == 1

    found = game()
    arm(found, "BOS", "C", 3)
    who = runner("thief", 8)
    found.bases = [who, None, None]
    feed(found, [1, 5])
    found._resolve_steal(0, "A", who)
    assert found.outs == 1
    assert found.box["TOR|thief"]["cs"] == 1

    found = game()
    arm(found, "BOS", "C", 6)  # out of page-8 1-5: hold path
    who = runner("thief", 8)
    found.bases = [who, None, None]
    feed(found, [1, 1])
    found._auto_steal(0, {"id": "thief", "name": "thief", "steal": {"jump": 5, "rating": "A"}})
    assert found.bases[0]["id"] == "thief"
    assert any("Catcher arm is" in gap for gap in found.gaps)

    found = game()
    batter = found.away["lineup"][0]
    # Percentile 97 is an error by the right fielder. 2d6 of 7 is SINGLE+error for an outfielder.
    feed(found, [3, 4, 1, 0])
    found._defense(batter, found.pitcher["BOS"]["player"], {"mode": "DEFENSE"}, False, 97)
    row = found.box["TOR|" + batter["id"]]
    assert row["h"] == 1 and row["ab"] == 1
    assert any("SINGLE+error is a hit" in line for line in found.log)

    found = game()
    batter = found.away["lineup"][0]
    pitcher = found.pitcher["BOS"]["player"]
    found.pitcher["BOS"]["fatigued"] = True
    reading = found._pitch_reading(batter, pitcher, "PATIENT", 68)
    assert reading["event"] == "SINGLE"
    assert reading["advance_as"] == "PATIENT"
    reading = found._pitch_reading(batter, pitcher, "BALLPARK", 10)
    assert reading["section"] == "WHEELHOUSE"

    found = game()
    batter = found.away["lineup"][0]
    batter["sections"] = {
        "PATIENT": {"vsRHP": {"BB": [1, 10], "1B": [11, 40]}},
        "TOUGH": {"vsRHP": {"SO": [1, 20], "1B": [21, 40]}},
        "IN-PLAY": {"vsRHP": {"1B": [1, 40]}},
        "WHEELHOUSE": {"vsRHP": {"1B": [1, 40]}},
    }
    batter["out_table"] = [{"range": [1, 99], "result": "G6"}]
    pitcher = found.pitcher["BOS"]["player"]
    pitcher["throws"] = "R"
    pitcher["so_modifier"] = "+20"
    pitcher["special"] = ["PATIENT-OUT", "TOUGH-OUT"]
    found._patient_out = True
    found._read_batter(batter, pitcher, "PATIENT", 25, 3, 4, False)
    found._patient_out = False
    assert found.outs == 1
    assert found.box["TOR|" + batter["id"]]["h"] == 0
    found._patient_out = True
    found._read_batter(batter, pitcher, "PATIENT", 5, 3, 4, False)
    found._patient_out = False
    assert found.box["TOR|" + batter["id"]]["bb"] == 1
    found._tough_out = True
    found._read_batter(batter, pitcher, "TOUGH", 15, 3, 4, False)
    found._tough_out = False
    assert found.box["TOR|" + batter["id"]]["so"] == 1
    assert not any("moves percentile" in line for line in found.log)

    found = game()
    batter = found.away["lineup"][0]
    feed(found, [1, 0])
    found._apply_reading(
        batter, found.pitcher["BOS"]["player"],
        {"event": "PARK", "text": "BALLPARK."}, 10, 2, 2, 4, False,
    )
    assert any("onto WHEELHOUSE" in line for line in found.log)
    found = game()
    batter = found.away["lineup"][0]
    feed(found, [8, 0])
    found._apply_reading(
        batter, found.pitcher["BOS"]["player"],
        {"event": "PARK", "text": "BALLPARK."}, 80, 2, 2, 4, False,
    )
    assert any("onto IN-PLAY" in line for line in found.log)


def hit_and_run_advanced_and_infield():
    found = game()
    batter = found.away["lineup"][0]
    found.bases = [runner("first"), None, None]
    found._apply_out(batter, "L4", found.pitcher["BOS"]["player"], True, "IN-PLAY", 10)
    assert found.outs == 2

    found = game()
    found.opts["running"] = "advanced"
    batter = found.away["lineup"][0]
    found.bases = [runner("first", 7), runner("second", 7), None]
    found._advanced_hit(batter, "1B", 3, 4, 12)
    assert found.score["TOR"] == 1
    assert found.bases[1]["id"] == "first"
    assert found.bases[0]["id"] == batter["id"]

    found = game()
    batter = found.away["lineup"][0]
    found.inning = 8
    found.outs = 0
    found.score["BOS"] = 1
    found.score["TOR"] = 1
    found.bases = [runner("first"), None, runner("third")]
    feed(found, [1, 1, 0, 0])
    found._infield_in(batter, "SS")
    assert found.outs == 1
    assert found.score["TOR"] == 1
    assert found.bases[1]["id"] == "first"


def roster_rules_and_extra_innings():
    found = game()
    assert found.defense["BOS"]["1B"]["id"] == "ortizda01"
    assert "foxxji01" not in {player["id"] for player in found.defense["BOS"].values()}
    assert found.defense["TOR"]["DH"] if False else "bautijo02" not in {
        player["id"] for player in found.defense["TOR"].values()
    }
    lineup_ids = [player["id"] for player in found.home["lineup"]]
    assert found.pitcher["BOS"]["player"]["id"] not in lineup_ids
    assert len(found.home["lineup"]) == 9
    assert len(found.away["lineup"]) == 9

    found = game()

    def instant_half():
        found.outs = 3
        if found.inning == 10 and found.half == "bottom":
            found.score[found.home["code"]] += 1

    found._half = instant_half
    report = found.play()
    assert report["score"]["BOS"] == 1
    assert report["score"]["TOR"] == 0
    assert report["innings"] == 10
    assert any("never says how a tie after nine" in gap for gap in report["gaps"])
    assert any("No runner is placed on second" in gap for gap in report["gaps"])


def sample_game_stays_out_of_the_tournament():
    report = play("BOS", "TOR", seed=1)
    assert report["score"] == {"TOR": 1, "BOS": 9}
    assert report["innings"] == 9
    assert report["postponed"] is False
    assert report["pitching"]["BOS|martipe02"]["outs"] == 27
    assert report["pitching"]["TOR|stiebda01"]["outs"] == 14
    assert report["decisions"]["W"] == "BOS|martipe02" and report["decisions"]["L"] == "TOR|stiebda01"
    assert report["wp"] == {
        "seen": 19, "fired": 2, "miss": 8, "empty": 8, "no_rating": 1, "unmarked": 0,
    }
    assert any("Fast Action Cards replace the dice" in line for line in report["log"])
    assert any("WP? drawn 19. Fired 2." in line for line in report["log"])
    # Catcher arms are on the page-8 1-5 scale, so steals resolve.
    # Seed 1 has no steal attempt since the v0.3 pitcher tables; seed 4 does.
    assert any("FAC steal." in line for line in play("BOS", "TOR", seed=4)["log"])
    blob = subprocess.check_output(["git", "hash-object", "tournament_results.json"], cwd=ROOT, text=True).strip()
    assert blob == "c355ca75cf71d179e8d2fa4c01a8d8756d5e58c4"
    diff = subprocess.check_output(["git", "diff", "--", "sw.js"], cwd=ROOT, text=True)
    assert diff == ""


def fac_deck_and_scripted_plays():
    from fac import load_deck
    cards = load_deck()
    assert len(cards) == 256
    assert sum(1 for card in cards if card["wp"]) == 26
    specials = [card for card in cards if card["steal"]["special"]]
    assert len(specials) == 3
    assert all(card["home"] in {"C", "P"} for card in specials)
    assert all(card["defense"]["check"] == "RARE" for card in specials)
    flagged = [card for card in cards if card["uncertain"]]
    assert len(flagged) == 29

    found = Game(load_club("BOS"), load_club("TOR"), seed=1, steal="off", running="fac")
    found.deck.order = [0]
    found.deck.pos = 0
    batter = found.away["lineup"][0]
    found.bases = [None, runner("second", 4), None]
    found.outs = 2
    found._fac_running(batter, "1B")
    assert found.score["TOR"] == 0
    assert found.bases[2]["id"] == "second"
    assert found.bases[0]["id"] == batter["id"]

    found = Game(load_club("BOS"), load_club("TOR"), seed=1, steal="off", running="fac")
    found.deck.order = [0]
    found.deck.pos = 0
    arm(found, "BOS", "C", 3)
    who = runner("thief", 8)
    who["steal"] = {"jump": 4, "rating": "A", "jump_mod": None}
    found.bases = [who, None, None]
    found._resolve_steal(0, "A", who)
    assert found.bases[1]["id"] == "thief"

    found = Game(load_club("BOS"), load_club("TOR"), seed=1, steal="off", running="fac")
    found.deck.order = [0]
    found.deck.pos = 0
    batter = found.away["lineup"][7]
    found.bases = [runner("first"), None, None]
    found._bunt(batter, "A", False)
    assert found.outs == 1
    assert found.bases[1]["id"] == "first"
    assert found.box["TOR|" + batter["id"]]["sh"] == 1

    found = Game(load_club("BOS"), load_club("TOR"), seed=1, steal="off", running="fac")
    arm(found, "BOS", "C", 6)  # out of page-8 1-5: hold path
    who = runner("thief", 8)
    found.bases = [who, None, None]
    found._resolve_steal(0, "A", who)
    assert found.bases[0]["id"] == "thief"
    assert any("outside 1-5 is not on the steal chart" in gap for gap in found.gaps)


def _fac_index(cards, page, row, col):
    for index, card in enumerate(cards):
        if card["page"] == page and card["row"] == row and card["col"] == col:
            return index
    raise AssertionError("no card p%s r%s c%s" % (page, row, col))


def wp_mark_uses_the_page_10_rating():
    from fac import WP_READING, load_deck
    cards = load_deck()
    marked = [card for card in cards if card["wp"]]
    assert len(marked) == 26
    assert all(WP_READING in card["uncertain"] for card in marked)
    assert all(30 <= card["pct"] <= 39 for card in marked)
    hit = _fac_index(cards, 49, 0, 0)
    assert cards[hit]["wp"] is True and cards[hit]["pct"] == 30
    miss = _fac_index(cards, 43, 1, 3)
    assert cards[miss]["wp"] is True and cards[miss]["pct"] == 36
    other = next(
        index for index, card in enumerate(cards)
        if not card["wp"] and card["pct"] not in range(30, 33) and card["pct"] != 0
    )
    pedro = lambda found: found.pitcher["BOS"]["player"]

    found = Game(load_club("BOS"), load_club("TOR"), seed=1, steal="off", running="fac")
    found.deck.order = [hit]
    found.deck.pos = 0
    found.bases = [runner("first"), None, None]
    found.deck.draw("advance")
    assert found.bases[1]["id"] == "first"
    assert found.bases[0] is None
    assert found.score["TOR"] == 0
    assert found.wp_fired == 1 and found.wp_seen == 1
    assert found.deck.pos == 1
    assert any("Page 10 re-rolls the percentile" in gap for gap in found.gaps)

    found = Game(load_club("BOS"), load_club("TOR"), seed=1, steal="off", running="fac")
    found.deck.order = [hit]
    found.deck.pos = 0
    found.deck.draw("advance")
    assert found.bases == [None, None, None]
    assert found.wp_empty == 1 and found.wp_fired == 0
    assert any("Bases are empty" in line for line in found.log)

    found = Game(load_club("BOS"), load_club("TOR"), seed=1, steal="off", running="fac")
    found.deck.order = [miss]
    found.deck.pos = 0
    found.bases = [runner("first"), None, None]
    found.deck.draw("steal")
    assert found.wp_miss == 1 and found.wp_fired == 0
    assert found.bases[0]["id"] == "first"

    found = Game(load_club("BOS"), load_club("TOR"), seed=1, steal="off", running="fac")
    original = pedro(found)
    clone = dict(original)
    clone["addendum"] = dict(original.get("addendum") or {})
    clone["addendum"]["wp"] = None
    found.pitcher["BOS"]["player"] = clone
    found.deck.order = [hit]
    found.deck.pos = 0
    found.bases = [runner("first"), None, None]
    found.deck.draw("bunt")
    assert found.wp_no_rating == 1 and found.wp_fired == 0
    assert found.bases[0]["id"] == "first"
    assert any("Rare Play charts" in line for line in found.log)

    found = Game(load_club("BOS"), load_club("TOR"), seed=1, steal="off", running="fac")
    found.deck.order = [hit, other]
    found.deck.pos = 0
    found.bases = [runner("first"), None, None]
    card = found.deck.draw("batter")
    assert found.wp_seen == 0
    pct = found._wild_pitch(pedro(found), card["pct"])
    assert pct == cards[other]["pct"]
    assert found.bases[1]["id"] == "first"
    assert found.wp_fired == 1 and found.wp_seen == 1
    assert found.deck.pos == 2
    assert any("Wild-pitch re-roll" in line for line in found.log)

    both = [index for index, card in enumerate(cards) if card["wp"] and card["pct"] == 30]
    assert len(both) >= 2
    found = Game(load_club("BOS"), load_club("TOR"), seed=1, steal="off", running="fac")
    found.deck.order = both[:2]
    found.deck.pos = 0
    found.bases = [runner("first"), None, None]
    card = found.deck.draw("batter")
    found._wild_pitch(pedro(found), card["pct"])
    assert found.bases[2]["id"] == "first"
    assert found.score["TOR"] == 0
    assert found.wp_fired == 2

    assert not any(not card["wp"] and 30 <= card["pct"] <= 39 for card in cards)
    found = game()
    found.bases = [runner("first"), None, None]
    feed(found, [4, 4])
    pct = found._wild_pitch(found.pitcher["BOS"]["player"], 30)
    assert pct == 44
    assert found.wp_fired == 0 and found.wp_unmarked == 1
    assert found.bases[1]["id"] == "first"


class FixedDice:
    def __init__(self, die=6, pair=(1, 1)):
        self.die, self.two = die, pair

    def d6(self):
        return self.die

    def pair(self):
        return self.two[0], self.two[1], sum(self.two)

    def pct(self):
        return 50

    def take(self):
        return []


def injury_substitution_is_for_one_game():
    """An injured or removed player leaves for the rest of that game only."""
    found = game()
    tor = found.away
    found.batting, found.fielding = found.away, found.home
    hurt = next(p for p in tor["lineup"] if p["pos"] not in ("DH", "C"))
    pos, slot = hurt["pos"], tor["lineup"].index(hurt)
    hurt["removed"] = True
    found.bases = [hurt, None, None]
    found._substitute_removed()
    sub = tor["lineup"][slot]
    assert sub is not hurt and sub in tor["bench"]
    assert sub["pos"] == pos and found.bases[0] is sub
    spots = {sub.get("pos")} | {r.get("pos") for r in sub.get("positions") or []}
    bench_at_pos = [p for p in tor["bench"] if pos in {r.get("pos") for r in p.get("positions") or []}]
    if bench_at_pos:
        assert pos in spots
    assert found.defense["TOR"][pos] is sub
    assert any("Substitution: %s replaces %s" % (sub["name"], hurt["name"]) in line for line in found.log)
    # A removed pitcher goes to the bullpen; a pitcher who has left never returns.
    found.batting, found.fielding = found.away, found.home
    starter = found.pitcher["BOS"]["player"]
    starter["removed"] = True
    found._maybe_change_pitcher(before_batter=True)
    first = found.pitcher["BOS"]["player"]
    assert first is not starter and first in found.home["bullpen"]
    found._pending_change = {"BOS": "usage"}
    found._maybe_change_pitcher(before_batter=True)
    second = found.pitcher["BOS"]["player"]
    assert second not in (starter, first)
    # The next game loads the clubs fresh: everyone is back.
    again = game()
    assert not any(p["removed"] for p in again.away["people"])
    assert hurt["id"] in [p["id"] for p in again.away["lineup"]]
    assert again.pitcher["BOS"]["player"]["id"] == starter["id"]


def stress_test_box_score_fixes():
    """Bugs the 1000+ game stress run found (scripts/stress_sim.py)."""
    import game as engine
    # A restarted at-bat is not a batter faced.
    found = game()
    found.order_index["TOR"] = 3
    found.pitcher["BOS"]["batters"] = 1
    found._pitch_line(bf=1)
    found._restart_at_bat()
    assert found.order_index["TOR"] == 2
    assert found.pitcher["BOS"]["batters"] == 0
    assert found.pitch_box["BOS|martipe02"]["bf"] == 0

    # The FAC prints the bunt error result as "E?" (pages 14 and 19).
    found = Game(load_club("BOS"), load_club("TOR"), seed=1, steal="off", fac=True)
    found.deck.draw = lambda purpose: {"sac": {"F": "E?"}, "d6_1": 3, "d6_2": 7, "pct": 50}
    found.deck.take = lambda: []
    found.dice = FixedDice(die=6)
    batter = found.away["lineup"][0]
    found.bases = [runner("first"), None, None]
    found._bunt(batter, "F", False)
    line = found.box["TOR|" + batter["id"]]
    assert line["ab"] == 1 and line["h"] == 0
    assert found.bases[0]["id"] == batter["id"] and found.bases[1]["id"] == "first"
    assert found.box["BOS|field"]["e"] == 1

    # Safe on a dropped third strike is one at-bat and one strikeout.
    saved = engine.rare_lookup
    try:
        found = game()
        found.dice = FixedDice(pair=(1, 1))
        batter = found.away["lineup"][0]
        batter["run"] = 5
        engine.rare_lookup = lambda empty, result, pct: {"coded": True, "event": "SO_DROP", "note": "drop"}
        found._rare(batter, found.pitcher["BOS"]["player"], "TOUGH", None, None, pct=50)
        line = found.box["TOR|" + batter["id"]]
        assert (line["ab"], line["so"]) == (1, 1)
        # RUN 6+ doubles and is out at third: one at-bat, one hit, one out.
        found = game()
        batter = found.away["lineup"][1]
        batter["run"] = 7
        engine.rare_lookup = lambda empty, result, pct: {"coded": True, "event": "RUN5_1B_OR_2B_OUT3", "note": "liner"}
        found._rare(batter, found.pitcher["BOS"]["player"], "TOUGH", None, None, pct=50)
        line = found.box["TOR|" + batter["id"]]
        assert (line["ab"], line["h"], line["tb"], found.outs) == (1, 1, 2, 1)
    finally:
        engine.rare_lookup = saved

    # A runner thrown out for the third out: the batter keeps his hit.
    found = game()
    batter = found.away["lineup"][0]
    found.outs = 3
    found._reach(batter, 1, 0, "Single.", hit=True, hold_lead=True)
    line = found.box["TOR|" + batter["id"]]
    assert (line["ab"], line["h"], line["tb"]) == (1, 1, 1)

    # A starter tired at the end of a half is replaced when his side next
    # takes the field, not before a game that may already be over.
    found = game()
    found.pitcher["BOS"]["fatigued"] = True
    found._maybe_change_pitcher(before_batter=False)
    assert found.pitcher["BOS"]["player"]["id"] == "martipe02"
    found._maybe_change_pitcher(before_batter=True)
    assert found.pitcher["BOS"]["player"]["id"] != "martipe02"


def supplemental_strikeout_is_on_by_default():
    """Page 11 optional rule: on by default (owner choice), off by option.
    Only a pitcher with an so_band is affected, and only on a batter-card out."""
    found = game()
    assert found.opts["supplemental_so"] is True
    pitcher = {"so_band": [50, 61]}
    assert found._supplemental_strikeout(pitcher, 50)
    assert found._supplemental_strikeout(pitcher, 61)
    assert not found._supplemental_strikeout(pitcher, 62)
    assert not found._supplemental_strikeout(pitcher, 49)
    assert not found._supplemental_strikeout({"so_band": None}, 55)
    off = Game(load_club("BOS"), load_club("TOR"), seed=1, steal="off", fac=False, supplemental_so=False)
    assert not off._supplemental_strikeout(pitcher, 55)


def official_scoring_and_bullpen():
    """RBI (9.04), responsible pitcher and earned runs (9.16), W/L/S (9.17-9.19),
    manager bullpen usage. Owner ruling 2026-10-27."""
    def pa_for(found, batter):
        return {"batter": batter, "rbi": [], "outs0": found.outs, "log0": len(found.log), "on_error": False}

    # A run on a hit is batted in; a run on a double play or an error is not.
    for text, on_error, want in (("Single.", False, 1), ("Double play.", False, 0), ("Error.", True, 0)):
        found = game()
        batter, runner = found.away["lineup"][0], found.away["lineup"][5]
        found.bases[2] = runner
        found._resp[runner["id"]] = found._pkey()
        found._pa = pa_for(found, batter)
        found._pa["on_error"] = on_error
        found.say(text)
        if text == "Double play.":
            found.outs += 2
        found._score_runner(2, "scores")
        pa, found._pa = found._pa, None
        found._settle_rbi(pa)
        assert found.box.get("TOR|" + batter["id"], {}).get("rbi", 0) == want, text

    # A run on a wild pitch or steal is not batted in.
    found = game()
    batter, runner = found.away["lineup"][0], found.away["lineup"][5]
    found.bases[2] = runner
    found._pa = pa_for(found, batter)
    found._no_rbi += 1
    found._score_runner(2, "scores on the wild pitch")
    found._no_rbi -= 1
    assert found._pa["rbi"] == []

    # An inherited runner's run is charged to the pitcher who put him on.
    found = game()
    starter = found._pkey()
    runner = found.away["lineup"][3]
    found.bases[1] = runner
    found._resp[runner["id"]] = starter
    found._pitch_line()
    found.pitcher["BOS"]["fatigued"] = True
    found._maybe_change_pitcher(before_batter=True)
    reliever = found._pkey()
    assert reliever != starter
    found._pitch_line()
    found._runners_advance(2)
    assert found.pitch_box[starter]["r"] == 1 and found.pitch_box[starter]["er"] == 1
    assert found.pitch_box[reliever]["r"] == 0

    # Earned runs: a runner who reached on an error, or a run after the
    # inning would have ended without the errors, is unearned.
    found = game()
    runner = found.away["lineup"][3]
    found._pitch_line()
    found.bases[2] = runner
    found._ue.add(runner["id"])
    found._score_runner(2, "scores")
    row = found.pitch_box[found._pkey()]
    assert (row["r"], row["er"]) == (1, 0)
    found.bases[2] = found.away["lineup"][4]
    found.outs, found._half_err = 2, 1
    found._score_runner(2, "scores")
    assert (row["r"], row["er"]) == (2, 0)

    # The book option keeps a fatigued starter until the end of the half.
    found = Game(load_club("BOS"), load_club("TOR"), seed=1, steal="off", fac=False, bullpen="book")
    found.pitcher["BOS"]["fatigued"] = True
    found._maybe_change_pitcher(before_batter=True)
    assert found.pitcher["BOS"]["player"]["id"] == "martipe02"

    # Whole games: the box adds up and the decisions are on the right sides.
    for seed in range(1, 41):
        r = play("CHC", "MON", seed=seed)
        if r["postponed"]:
            continue
        for side, other in (("CHC", "MON"), ("MON", "CHC")):
            pit = [v for k, v in r["pitching"].items() if k.startswith(side + "|")]
            bat = [v for k, v in r["box"].items() if k.startswith(other + "|") and not k.endswith("|field")]
            assert sum(p["r"] for p in pit) == r["score"][other], seed
            assert sum(p["er"] for p in pit) <= sum(p["r"] for p in pit)
            assert sum(p["h"] for p in pit) == sum(b["h"] for b in bat), seed
            assert sum(p["hr"] for p in pit) == sum(b["hr"] for b in bat), seed
            assert sum(b["rbi"] for b in bat) <= r["score"][other], seed
        d = r["decisions"]
        win = max(r["score"], key=r["score"].get)
        assert d["W"].startswith(win + "|") and not d["L"].startswith(win + "|"), seed
        assert d["S"] is None or (d["S"].startswith(win + "|") and d["S"] != d["W"]), seed
        assert d["W"] in r["pitching"] and d["L"] in r["pitching"]


if __name__ == "__main__":
    official_scoring_and_bullpen()
    supplemental_strikeout_is_on_by_default()
    chart_faces()
    basic_running_and_walks()
    double_play_fly_and_bunt()
    steal_defense_and_pitch_quality()
    hit_and_run_advanced_and_infield()
    roster_rules_and_extra_innings()
    fac_deck_and_scripted_plays()
    wp_mark_uses_the_page_10_rating()
    sample_game_stays_out_of_the_tournament()
    stress_test_box_score_fixes()
    injury_substitution_is_for_one_game()
    print("game tests passed")
