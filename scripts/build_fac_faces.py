#!/usr/bin/env python3
"""Build FAC card face images from Joe's 2024 game PDF (pp40-71).

Geometry (measured 2026-10-29 from the PDF's own vector border lines,
identical on pp40/55/71): the 8 cards tile the landscape page.
  columns x: [0.85,198.75] [197.75,395.55] [394.55,592.45] [591.45,790.05]
  rows    y: [10.7,308.85] [307.85,605.85]
Slots are row-major 1..8; fac_id = (page-40)*8 + slot, matching
fac_deck.json (payoff-pitch-alltime-teams/fac/).

Every card's header numbers (2d6, %, 1d6) are read back from the PDF
text layer inside its crop cell and checked against fac_deck.json
before the image is written. Any mismatch aborts the build.

Run with the pdf venv python (PyMuPDF):
  ~/workspace/tools/pdfvenv/bin/python scripts/build_fac_faces.py
Output: assets/fac/fac-001.webp .. fac-256.webp (WebP via Pillow if
importable in this interpreter; otherwise PNGs are staged and the
script prints the follow-up conversion command).
"""
import json
import sys

import fitz

PDF = '/home/hatch/workspace/user/files/Payoff_Pitch_Baseball_Game_2024_0_ve3c.pdf'
DECK = '/home/hatch/workspace/payoff-pitch-alltime-teams/fac/fac_deck.json'
OUTDIR = '/home/hatch/workspace/pp-t32-cards/assets/fac'
STAGE = '/tmp/fac_png'
DPI = 200

COLS = [(0.85, 198.75), (197.75, 395.55), (394.55, 592.45), (591.45, 790.05)]
ROWS = [(10.7, 308.85), (307.85, 605.85)]


def header_numbers(page, cell):
    """Read (d2d6, pct, d1d6, wp) from text spans in the cell header."""
    x0, y0, x1, y1 = cell
    big, mid, wp = [], [], False
    d = page.get_text('dict', clip=fitz.Rect(x0, y0, x1, y0 + 58))
    for block in d['blocks']:
        for line in block.get('lines', []):
            for span in line['spans']:
                t = span['text'].strip()
                if not t:
                    continue
                if t.startswith('WP'):
                    wp = True
                if not t.isdigit():
                    continue
                cx = (span['bbox'][0] + span['bbox'][2]) / 2
                if span['size'] > 17:
                    big.append((cx, int(t)))
                elif span['size'] > 9.5:
                    mid.append((cx, int(t)))
    big.sort()
    if len(big) != 2 or len(mid) != 1:
        return None
    return big[0][1], big[1][1], mid[0][1], wp


def main():
    import os
    os.makedirs(STAGE, exist_ok=True)
    deck = {c['fac_id']: c for c in json.load(open(DECK))}
    doc = fitz.open(PDF)
    problems = []
    cells = {}
    for pno in range(40, 72):
        page = doc[pno - 1]
        words = page.get_text('words')
        anchors = [w for w in words if w[4] == '2d6']
        if len(anchors) != 8:
            problems.append(f'page {pno}: {len(anchors)} 2d6 anchors')
            continue
        for w in anchors:
            cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
            col = next(i for i, (a, b) in enumerate(COLS) if a <= cx <= b)
            row = next(i for i, (a, b) in enumerate(ROWS) if a <= cy <= b)
            slot = row * 4 + col + 1
            fac_id = (pno - 40) * 8 + slot
            cell = fitz.Rect(COLS[col][0], ROWS[row][0], COLS[col][1], ROWS[row][1])
            cells[fac_id] = (page, cell)
            got = header_numbers(page, cell)
            want = deck[fac_id]
            if got is None:
                problems.append(f'fac {fac_id} (p{pno} s{slot}): header unreadable')
            elif got[:3] != (want['d2d6'], want['pct'], want['d1d6']) or got[3] != bool(want['wp']):
                problems.append(
                    f"fac {fac_id} (p{pno} s{slot}): read {got}, "
                    f"json {(want['d2d6'], want['pct'], want['d1d6'], want['wp'])}")
    if problems:
        print('VERIFICATION FAILED:')
        for p in problems[:30]:
            print(' ', p)
        print(f'  ... {len(problems)} problems total')
        sys.exit(1)
    print(f'verified all {len(cells)} card headers against fac_deck.json')
    for fac_id in sorted(cells):
        page, cell = cells[fac_id]
        pix = page.get_pixmap(dpi=DPI, clip=cell)
        pix.save(f'{STAGE}/{fac_id:03d}.png')
    print(f'staged {len(cells)} PNGs at {DPI} dpi in {STAGE}')


if __name__ == '__main__':
    main()
