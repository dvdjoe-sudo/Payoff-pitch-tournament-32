#!/usr/bin/env python3
"""A game-import refresh must not replace repaired card bodies."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_cards as bc


def test_refresh_keeps_windows_and_dice():
    cards = {
        "BOS|willite01": {
            "id": "willite01",
            "name": "Ted Williams",
            "team": "BOS",
            "spots": [{"group": "lineup", "kind": "hitter", "pos": "LF", "slot": 3}],
            "peak_bat": {"window_years": [1941, 1942, 1946, 1955, 1957], "HR": 1},
            "card_bat": {"sections": {"WHEELHOUSE": {"vsLHP": {"HR": [1, 55]}}}},
            "card_pit": None,
            "tournament": None,
        }
    }
    archive = {
        "games": [{
            "id": "R1-03-G1",
            "batting": [{
                "team": "BOS", "name": "Ted Williams", "player_id": "willite01",
                "ab": 4, "r": 1, "h": 2, "doubles": 0, "triples": 0, "hr": 1,
                "rbi": 1, "bb": 1, "k": 1, "hbp": 0, "sb": 0, "cs": 0,
                "sac": 0, "sf": 0, "gidp": 0, "ci": 0,
            }],
            "pitching": [],
            "wls": {},
        }]
    }
    changed = bc.refresh_tournament_lines(cards, archive)
    card = cards["BOS|willite01"]
    assert changed == 1
    assert card["peak_bat"]["window_years"] == [1941, 1942, 1946, 1955, 1957]
    assert card["card_bat"]["sections"]["WHEELHOUSE"]["vsLHP"]["HR"] == [1, 55]
    assert card["tournament"]["games"] == ["R1-03-G1"]
    assert card["tournament"]["batting"]["hr"] == 1
    again = bc.refresh_tournament_lines(cards, archive)
    assert again == 0


if __name__ == "__main__":
    test_refresh_keeps_windows_and_dice()
    print("preserve-cards test passed")
