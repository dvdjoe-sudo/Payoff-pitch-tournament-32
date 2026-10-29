#!/usr/bin/env python3
"""Card-view parity (spec Sections 5b and 11.4): the Play
view's card renderer is a deliberate copy of bracket.js's
player-page renderer. This script extracts the observable
contract from both — section order, result-row order, fact
chip label order, and the shared label strings — and fails
if they diverge.

Run: python3 scripts/check_cardview_parity.py
Exit 1 on any divergence.
"""
import re
import sys

ROOT = __file__.rsplit('/scripts/', 1)[0]


def slice_fn(text, start_marker, end_pattern):
    i = text.index(start_marker)
    m = re.search(end_pattern, text[i + 10:])
    return text[i:i + 10 + m.start()] if m else text[i:]


def ordered(text, tokens):
    found = []
    for t in tokens:
        for m in re.finditer(re.escape(t), text):
            found.append((m.start(), t))
    found.sort()
    out = []
    for _, t in found:
        if not out or out[-1] != t:
            out.append(t)
    return out


def main():
    bracket = open(ROOT + '/js/bracket.js').read()
    play = open(ROOT + '/js/play.js').read()
    b_card = slice_fn(bracket, 'function cardSections', r'\n  function ')
    pit_at = b_card.index('if (card.card_pit) {')
    b_hit, b_pit = b_card[:pit_at], b_card[pit_at:]
    p_hit = slice_fn(play, 'function hitterCardBlock', r'\n  function ')
    p_pit = slice_fn(play, 'function pitcherCardBlock', r'\n  function ')

    sections = ['WHEELHOUSE', 'PATIENT', 'TOUGH', 'IN-PLAY']
    results = ['HR', '3B', '2B', '1B', 'BB', 'HBP', 'SO']
    hit_chips = ['Bats', 'Throws', 'Run', 'Steal', 'Sac bunt', 'DP', 'Fielding', 'Arm']
    pit_chips = ['Throws', 'Type', 'SO modifier', 'Special', 'Start', 'Relief',
                 'WP', 'DP', 'Hold', 'Pickoff', 'Inj']
    labels = ['Out table:', '2d6 section', 'vs LHP', 'vs RHP']

    checks = [
        ('section order', ordered(b_card, sections), ordered(p_hit, sections)),
        ('result order', ordered(b_card, results), ordered(p_hit, results)),
        ('hitter chip order', ordered(b_hit, hit_chips), ordered(p_hit, hit_chips)),
        ('pitcher chip order', ordered(b_pit, pit_chips), ordered(p_pit, pit_chips)),
    ]
    fails = 0
    for name, a, b in checks:
        ok = a == b
        print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else ': bracket=' + str(a) + ' play=' + str(b)))
        fails += 0 if ok else 1
    for lab in labels:
        in_b = lab in bracket
        in_p = lab in play
        ok = in_b and in_p
        print(('PASS ' if ok else 'FAIL ') + 'label ' + repr(lab) + ' in both renderers' + ('' if ok else ': bracket=' + str(in_b) + ' play=' + str(in_p)))
        fails += 0 if ok else 1
    print('CARDVIEW PARITY: ' + ('PASS' if fails == 0 else 'FAIL'))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
