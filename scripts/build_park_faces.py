#!/usr/bin/env python3
"""Build ballpark card face images for the two playable parks from
Joe's 1986 set PDF (ballpark sheets, pp137-140; both targets are on
p137).

Geometry (measured 2026-10-29 from a 200-dpi render of p137 by
scanning for runs of non-gutter pixels; the sheet's gutter color is
(197,217,240) and the cards tile it 4x2):
  columns x: [2.9,195.1] [200.9,393.1] [398.9,591.1] [596.9,789.1]
  rows    y: [1.8,303.5] [308.5,608.6]
Wrigley Field is column 2, row 1; Stade Olympique is column 2,
row 2.

Each card's name and its four BALLPARK ranges (LHB/RHB x
WHEELHOUSE/IN-PLAY) are read back from the PDF text layer inside
its crop cell and checked against the app's park data
(data/playable_r106.json) before the image is written. Any
mismatch aborts the build.

Run with the pdf venv python (PyMuPDF):
  ~/workspace/tools/pdfvenv/bin/python scripts/build_park_faces.py
Output: PNGs staged in /tmp/park_png; convert to the shipped WebP
names with system python3 (PIL):
  python3 -c "from PIL import Image; import sys; \
    [Image.open(a).save(b, quality=88) for a, b in \
     [('.../wrigley-field.png', 'assets/parks/wrigley-field.webp'), \
      ('.../stade-olympique.png', 'assets/parks/stade-olympique.webp')]]"
"""
import json
import re
import sys

import fitz

PDF = '/home/hatch/workspace/user/files/1986_PDF_LR_US_3_dhn0.pdf'
APPDATA = '/home/hatch/workspace/pp-t32-cards/data/playable_r106.json'
STAGE = '/tmp/park_png'
DPI = 200
PAGE = 137  # 1-indexed

COLS = [(2.9, 195.1), (200.9, 393.1), (398.9, 591.1), (596.9, 789.1)]
ROWS = [(1.8, 303.5), (308.5, 608.6)]

# park name -> (column index, row index, output slug)
TARGETS = {
    'Wrigley Field': (1, 0, 'wrigley-field'),
    'Stade Olympique': (1, 1, 'stade-olympique'),
}

RANGE_RE = re.compile(
    r'(\d+)\s*-\s*(\d+)\s+WHEELHOUSE\s+(\d+)\s*-\s*(\d+)\s+'
    r'(\d+)\s*-\s*(\d+)\s+IN-PLAY\s+(\d+)\s*-\s*(\d+)')


def face_numbers(page, cell):
    """Read (name_ok, LHB WH, RHB WH, LHB IP, RHB IP) from the cell."""
    text = page.get_text('text', clip=cell)
    flat = ' '.join(text.split())
    m = RANGE_RE.search(flat)
    if not m:
        return None
    g = [int(x) for x in m.groups()]
    return flat, (g[0], g[1]), (g[2], g[3]), (g[4], g[5]), (g[6], g[7])


def main():
    import os
    os.makedirs(STAGE, exist_ok=True)
    parks = json.load(open(APPDATA))['parks']
    doc = fitz.open(PDF)
    page = doc[PAGE - 1]
    problems = []
    staged = []
    for name, (ci, ri, slug) in TARGETS.items():
        cell = fitz.Rect(COLS[ci][0], ROWS[ri][0], COLS[ci][1], ROWS[ri][1])
        got = face_numbers(page, cell)
        if got is None:
            problems.append(f'{name}: BALLPARK ranges unreadable in cell')
            continue
        flat, lwh, rwh, lip, rip = got
        if name.upper() not in flat:
            problems.append(f'{name}: name not on the face in this cell')
            continue
        chart = parks[name]['ballpark_chart']
        want = (tuple(chart['LHB']['WHEELHOUSE']), tuple(chart['RHB']['WHEELHOUSE']),
                tuple(chart['LHB']['IN-PLAY']), tuple(chart['RHB']['IN-PLAY']))
        if (lwh, rwh, lip, rip) != want:
            problems.append(f'{name}: face {(lwh, rwh, lip, rip)} != app {want}')
            continue
        pix = page.get_pixmap(dpi=DPI, clip=cell)
        out = f'{STAGE}/{slug}.png'
        pix.save(out)
        staged.append(out)
        print(f'{name}: verified vs app data, staged {out} ({pix.width}x{pix.height})')
    if problems:
        print('VERIFICATION FAILED:')
        for p in problems:
            print(' ', p)
        sys.exit(1)
    print(f'all {len(staged)} park faces verified and staged')


if __name__ == '__main__':
    main()
