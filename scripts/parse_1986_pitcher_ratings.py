#!/usr/bin/env python3
"""Read the printed pitcher ratings from the official 1986 card-set PDF.

parse_1986_cards.py reads the 2d6 table and the Start number. This reads
the rest of the right-hand column on every pitcher card exactly as
printed: BATTING, FIELDING (range, error), FATIGUE (Start/Relief and any
save symbol), HOLD, INJURY, DP, and WP. Output:
historical-cards/reference/pitcher_ratings_1986.json. Nothing is derived.
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import parse_1986_cards as P  # noqa: E402
import pymupdf  # noqa: E402

PDF = os.environ.get("PP_1986_PDF", P.DEFAULT_PDF)
OUT = os.path.join(ROOT, "historical-cards", "reference", "pitcher_ratings_1986.json")
LABELS = ["BATTING", "FIELDING", "FATIGUE", "HOLD", "INJURY", "DP", "WP", "SO"]


def main():
    doc = pymupdf.open(PDF)
    out = []
    for i, page in enumerate(doc):
        if i == 0:
            continue
        for x0, x1 in zip(P.COLS, P.COLS[1:]):
            for y0, y1 in zip(P.ROWS, P.ROWS[1:]):
                words = P._cell_words(page, x0, x1, y0, y1)
                if len(words) < 8 or not P._is_pitcher(words) or P._is_hitter(words):
                    continue
                base = P._parse_pitcher(P._lines(words))
                fat = [w for w in words if w[4] == "FATIGUE"]
                if not fat:
                    continue
                left = fat[0][0] - 3
                so_y = max(w[1] for w in words if w[4] == "SO" and w[0] >= left)
                right = sorted([w for w in words if w[0] >= left and w[1] < so_y + 12 and "\u00a9" not in w[4]],
                               key=lambda w: (round(w[1]), w[0]))
                vals, cur = {}, None
                for w in right:
                    if w[4] in LABELS:
                        cur = w[4]
                        vals[cur] = []
                    elif cur:
                        vals[cur].append(w[4])
                printed = {k.lower(): " ".join(v) for k, v in vals.items() if k != "SO"}
                printed["wp"] = printed.get("wp", "").replace(" ", "")
                out.append({"name": base["name"], "team": base["team"], "partial": base["partial"],
                            "throws": base["throws"], "stats": base["stats"], "printed": printed,
                            "source_page": i + 1})
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump({"source": "1986 Payoff Pitch season PDF, pitcher card right column as printed",
                   "pitchers": out}, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    print(len(out), "pitcher cards")


if __name__ == "__main__":
    main()
