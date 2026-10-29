#!/usr/bin/env python3
"""CI gate for data/playable_r106.json (spec Section 11.4).

The full build (scripts/build_playable_data.py) reads the
governing set homes, which live outside this repo and stay
read-only, so a clean CI runner cannot rebuild the file.
What CI can do — and what this script does — is verify the
committed file against the in-repo record: every fixture
hitter's batting surface must equal data/cards.json's
card_bat for that player (the Section 3 cross-check, with
positions compared by sequence only, per the build note),
the deck must be the full 256 unique faces in range, and
the fixture must partition cleanly over the shipped
rosters. A stale or hand-edited playable file fails here.

Run: python3 scripts/verify_playable_data.py
Exit 1 on any failure.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def canon(v):
    return json.dumps(v, sort_keys=True)


def main():
    fails = []

    def fail(msg):
        fails.append(msg)

    data = json.load(open(os.path.join(REPO, 'data', 'playable_r106.json')))
    cj = json.load(open(os.path.join(REPO, 'data', 'cards.json')))
    by_name = {}
    for key, rec in cj.items():
        club = key.split('|')[0]
        if club in ('CHC', 'MON'):
            by_name[(club, rec['name'])] = rec['card_bat']

    SHARED = ('sections', 'out_table', 'run', 'steal',
              'sac_bunt', 'dp', 'bats', 'throws')
    for club in ('CHC', 'MON'):
        hitters = data['hitters'][club]
        pitchers = data['pitchers'][club]
        if len(hitters) != 15:
            fail(f'{club}: {len(hitters)} hitters shipped, expected 15')
        if len(pitchers) != 11:
            fail(f'{club}: {len(pitchers)} pitchers shipped, expected 11')
        for nm, pit in pitchers.items():
            if pit.get('addendum') is not True:
                fail(f'{club}: pitcher {nm} addendum not merged')
        for nm, card in hitters.items():
            rec = by_name.get((club, nm))
            if rec is None:
                fail(f'{club}: {nm} missing from data/cards.json')
                continue
            for f in SHARED:
                if canon(card.get(f)) != canon(rec.get(f)):
                    fail(f'{club}: {nm} field {f} differs from data/cards.json card_bat')
            eng_pos = [p['pos'] for p in card.get('positions') or []]
            app_pos = [p['pos'] for p in rec.get('positions') or []]
            if eng_pos != app_pos:
                fail(f'{club}: {nm} position sequence differs from cards.json')

    deck = data['deck']
    ids = [c['fac_id'] for c in deck]
    if len(deck) != 256 or sorted(ids) != list(range(1, 257)):
        fail('deck is not the 256 unique FAC ids 1..256')
    for c in deck:
        if not (2 <= c['d2d6'] <= 12 and 0 <= c['pct'] <= 99 and 1 <= c['d1d6'] <= 6):
            fail(f"FAC {c['fac_id']} face out of range")
            break

    fx = data['fixture']
    for club in ('CHC', 'MON'):
        lu = fx['lineups'][club]
        if len(lu) != 9:
            fail(f'{club}: lineup has {len(lu)} slots, expected 9')
        for slot in lu:
            if slot['name'] not in data['hitters'][club]:
                fail(f"{club}: lineup name {slot['name']} not in shipped hitters")
        for nm in fx['benches'][club]:
            if nm not in data['hitters'][club]:
                fail(f'{club}: bench name {nm} not in shipped hitters')
        for nm in fx['pens'][club] + fx['rotations'][club]:
            if nm not in data['pitchers'][club]:
                fail(f'{club}: pitcher {nm} not in shipped pitchers')
        park = fx['clubs'][club]['park']
        if park not in data['parks']:
            fail(f'{club}: park {park} not in shipped parks')
    if len(data['rare_plays']) != 24:
        fail(f"rare_plays has {len(data['rare_plays'])} entries, expected 24")

    for msg in fails:
        print('FAIL', msg)
    print('VERIFY PLAYABLE DATA: ' + ('PASS' if not fails else f'FAIL ({len(fails)})'))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
