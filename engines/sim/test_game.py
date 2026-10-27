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
    assert report["score"] == {"TOR": 0, "BOS": 4}
    assert report["innings"] == 9
    assert report["postponed"] is False
    assert report["pitching"]["BOS|martipe02"]["outs"] == 27
    assert report["pitching"]["TOR|stiebda01"]["outs"] == 21
    assert any("Fast Action Cards replace the dice" in line for line in report["log"])
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
    who = runner("thief", 8)
    found.bases = [who, None, None]
    found._resolve_steal(0, "A", who)
    assert found.bases[0]["id"] == "thief"
    assert any("does not say how to turn 6, 7, or 8" in gap for gap in found.gaps)


if __name__ == "__main__":
    chart_faces()
    basic_running_and_walks()
    double_play_fly_and_bunt()
    steal_defense_and_pitch_quality()
    hit_and_run_advanced_and_infield()
    roster_rules_and_extra_innings()
    fac_deck_and_scripted_plays()
    sample_game_stays_out_of_the_tournament()
    print("game tests passed")
