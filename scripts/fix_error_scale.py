#!/usr/bin/env python3
"""Put set-file hitter error ratings on the rulebook direction.

Rulebook page 2: "The 'E' rating is the batter's Error rating with 1 being
the worst and 5 the best." The park chart agrees (error 5 has the smallest
error band) and so do the printed 1986 cards (Ozzie Smith SS A 4).
The converted set files stored the digit the other way round, tied to the
word grade: Elite A/1, Great A/2, Above Average B/3, Average C/4,
Below Average D/5, Poor F/5. The engine reads the digit as printed, so an
Elite fielder drew the largest error band. This flips e -> 6 - e on every
card whose fielding still comes from a set file (label is a set-file word
and the card is not marked error_scale). Range, arm, label and everything
else stay. Cards derived from stats (label "Derived") and the engine
Average default (range C, error 4) are already on the rulebook direction.
"""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CARDS = os.path.join(ROOT, "data", "cards.json")
SET_WORDS = {"Elite", "Great", "Above Average", "Average", "Below Average", "Poor"}
MARK = "rulebook p2: 1 worst, 5 best (set-file digit flipped)"


def needs_flip(bat):
    if bat.get("fielding") not in SET_WORDS or bat.get("error_scale"):
        return False
    rows = bat.get("positions") or []
    # The engine Average default is not a set-file rating.
    if bat.get("fielding") == "Average" and all(r.get("range") == "C" and r.get("e") == 4 for r in rows):
        return False
    return bool(rows)


def main():
    cards = json.load(open(CARDS, encoding="utf-8"))
    changed = []
    for key, card in cards.items():
        bat = card.get("card_bat") or {}
        if not needs_flip(bat):
            continue
        before = [r.get("e") for r in bat["positions"]]
        for r in bat["positions"]:
            if isinstance(r.get("e"), int):
                r["e"] = 6 - r["e"]
        bat["error_scale"] = MARK
        changed.append((key, bat["fielding"], before, [r.get("e") for r in bat["positions"]]))
    with open(CARDS, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(cards, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    for row in changed:
        print(*row)
    print("cards flipped:", len(changed), "position rows:", sum(len(r[2]) for r in changed))


if __name__ == "__main__":
    main()
