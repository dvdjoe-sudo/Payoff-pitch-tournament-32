#!/usr/bin/env python3
"""Card for Carlos Ruiz (PHI), who replaces J.T. Realmuto (owner, 2026-10-27).

Same method as every franchise card on the roster (build_sixth_bench_cards.py,
which builds any rostered player who has no card): the five best Phillies
seasons by one-decimal league OPS+ with PA>=300, Hitter v0.5 solver, then
card_postpass (platoon re-split, IBB as walks, jump and steal letter from
real steals, outfield arm). Fielding is then derived by
derive_hitter_fielding.py. Realmuto's PHI card is removed (his MIA card stays). Other cards,
rosters and tournament_results.json are not changed.
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_empty_team_cards as empty  # noqa: E402
import build_sixth_bench_cards as six  # noqa: E402

six.REPORT = os.path.join(ROOT, "historical-cards", "accuracy", "phi_ruiz_card.json")

if __name__ == "__main__":
    cards = json.load(open(six.CARDS, encoding="utf-8"))
    if "PHI|realmjt01" in cards:
        del cards["PHI|realmjt01"]
        empty.write_json(cards, six.CARDS)
    sys.exit(six.main())
