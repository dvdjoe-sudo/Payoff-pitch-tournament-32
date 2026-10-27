#!/usr/bin/env python3
"""Put set-file outfield arms on the rulebook direction.

Rulebook page 8: outfield Arm "ranges from 3 to 10 with 3 being the best and
10 the worst". The engine agrees (the runner is safe on 2d6 <= ARM, page 16)
and so do the printed 1986 cards (Barfield RF 6 / CF 4, Parker RF 8).
The converted set files tied the arm to the word grade the other way round:
Elite and Great 8, middle grades 6, Poor 4. This mirrors those set-file
outfield arms inside the set's own 4-8 band (arm -> 12 - arm: 8 -> 4,
4 -> 8, 6 stays). Catchers, infield rows, Derived cards and everything
else are unchanged.
"""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CARDS = os.path.join(ROOT, "data", "cards.json")
SET_WORDS = {"Elite", "Great", "Above Average", "Average", "Below Average", "Poor"}
OF = {"LF", "CF", "RF", "OF"}
MARK = "rulebook p8: 3 best, 10 worst (set-file OF arm mirrored)"


def main():
    cards = json.load(open(CARDS, encoding="utf-8"))
    changed = []
    for key, card in cards.items():
        bat = card.get("card_bat") or {}
        if bat.get("fielding") not in SET_WORDS or bat.get("of_arm_scale"):
            continue
        rows = [r for r in bat.get("positions") or [] if r.get("pos") in OF and isinstance(r.get("arm"), int)]
        if not rows:
            continue
        before = [r["arm"] for r in rows]
        for r in rows:
            r["arm"] = 12 - r["arm"]
        bat["of_arm_scale"] = MARK
        changed.append((key, bat["fielding"], before, [r["arm"] for r in rows]))
    with open(CARDS, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(cards, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    for row in changed:
        print(*row)
    moved = sum(1 for r in changed if r[2] != r[3])
    print("cards marked:", len(changed), "arms changed:", moved)


if __name__ == "__main__":
    main()
