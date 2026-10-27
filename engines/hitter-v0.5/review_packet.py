#!/usr/bin/env python3
"""v0.5 review packet: compact human-readable summary for flagged cards.

Usage: python3 review_packet.py
Reads output/architecture_limited.csv and generates output/review_packet.txt
with target vs card event rates, primary constraint, and best legal tradeoff
for each flagged player.
"""
import csv, json, os, sys

HIST = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HIST, 'output')
sys.path.insert(0, os.path.join(HIST, 'engine'))
from hitter_solver import expected, event_targets


def make_packet():
    arch_path = os.path.join(OUT, 'architecture_limited.csv')
    if not os.path.exists(arch_path):
        print("No architecture_limited.csv found.")
        return
    with open(arch_path) as f:
        rows = list(csv.DictReader(f))
    lines = []
    lines.append("=" * 60)
    lines.append("ARCHITECTURE-LIMITED REVIEW PACKET")
    lines.append(f"{len(rows)} players need review")
    lines.append("=" * 60)
    for r in rows:
        card = json.load(open(r['file']))
        audit = card.get('audit', {})
        # reconstruct targets from audit input
        inp = audit.get('input_row', {})
        lines.append("")
        lines.append(f"{r['name'].upper()}")
        lines.append(f"Primary issue: {r['primary_issue']}")
        lines.append(f"Fit error: {r['fit_error']}  "
                     f"Best possible: {r['best_possible']}")
        lines.append(f"Reason: {r['reason']}")
        lines.append(f"Solver version: {audit.get('solver_version', '?')}  "
                     f"Built: {audit.get('built_utc', '?')}")
        lines.append(f"IBB treatment: {audit.get('ibb_treatment', '?')}")
        lines.append(f"Card file: {r['file']}")
        lines.append("-" * 40)
    out = os.path.join(OUT, 'review_packet.txt')
    with open(out, 'w') as f:
        f.write('\n'.join(lines))
    print(f"Review packet written: {out} ({len(rows)} players)")


if __name__ == '__main__':
    make_packet()
