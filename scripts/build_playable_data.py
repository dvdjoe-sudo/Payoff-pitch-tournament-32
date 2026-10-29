#!/usr/bin/env python3
"""Build data/playable_r106.json for the playable mode (Phase 1).

Rule (PLAYABLE_MODE_SPEC.md Section 3): serialize what the reference
engines themselves load. This script assembles the Cubs stack exactly
the way series_chc_mon_setup_g1.py does (through chance_setup, with
Montreal injected as the guest and its addendum merged into the home
cache), then dumps the loaded HITTERS / PITCHERS objects -- pitchers
through the addendum-merging pitcher_card the engine itself serves --
never the files they were loaded from. data/cards.json is used only
as the cross-check surface the spec names.

Assertions fail the build; nothing here warns. Output is
deterministic (sorted keys, fixed separators): same inputs, same
bytes, so the CI generated-files gate can diff it.

Run from the pinned pipeline venv:
  ~/workspace/tools/pp-t32-venv/bin/python scripts/build_playable_data.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SANDBOX = os.path.expanduser('~/workspace/payoff-pitch-managers/sandbox')
CHC_DIR = os.path.expanduser('~/workspace/payoff-pitch-cubs')
APP_DATA = os.path.expanduser('~/workspace/payoff-pitch-app/data')
FAC_DECK = os.path.expanduser(
    '~/workspace/payoff-pitch-alltime-teams/fac/fac_deck.json')
OUT = os.path.join(REPO, 'data', 'playable_r106.json')

sys.path.insert(0, SANDBOX)
sys.path.insert(0, CHC_DIR)

import series_chc_mon_setup_g1 as G1  # noqa: E402  (assembles the stack)

E = G1.E
CS = G1.CS

# Fixture configuration (spec Section 4; staged in the G1 setup and
# printed in PP_R1_06_G1.md). Rotation chairs in rotation order.
ROTATIONS = {
    'CHC': ['Fergie Jenkins', 'Mordecai Brown', 'Rick Reuschel',
            'Pete Alexander', 'Carlos Zambrano'],
    'MON': ['Steve Rogers', 'Pedro Martinez', 'Dennis Martinez',
            'Bryn Smith', 'Javier Vazquez'],
}
SLOT_OF = {'CHC': 'CHC', 'MON': 'OPP'}   # engine slot per club


def fail(msg):
    raise SystemExit(f'build_playable_data: FAIL: {msg}')


def names_of(entries):
    """Lineup constants are (name, pos) pairs; bench constants are
    bare names in the v2 modules and pairs in the v1 module."""
    out = []
    for e in entries:
        out.append(e[0] if isinstance(e, (list, tuple)) else e)
    return out


def lineup_of(entries):
    return [{'name': e[0], 'pos': e[1]} for e in entries]


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))


def main():
    S = CS.base_state(20261401, {'CHC': G1.CHC_SP, 'OPP': G1.MON_SP})

    lineups = {'CHC': lineup_of(E.CHC_LINEUP), 'MON': lineup_of(E.OPP_LINEUP)}
    benches = {'CHC': names_of(E.CHC_BENCH), 'MON': names_of(E.OPP_BENCH)}
    pens = {'CHC': list(G1.CHC_PEN_NAMES), 'MON': list(G1.MON_PEN_NAMES)}
    pen_roles = {'CHC': dict(E.PEN_ROLE['CHC']),
                 'MON': dict(E.PEN_ROLE['OPP'])}

    hitters, pitchers = {}, {}
    addendum_counts = {}
    for club in ('CHC', 'MON'):
        slot = SLOT_OF[club]
        hnames = [s['name'] for s in lineups[club]] + benches[club]
        if len(hnames) != 15 or len(set(hnames)) != 15:
            fail(f'{club}: expected 15 distinct rostered hitters, '
                 f'got {len(hnames)}')
        hitters[club] = {}
        for nm in hnames:
            card = E.HITTERS.get((nm, slot))
            if card is None:
                fail(f'{club}: staged hitter {nm} has no loaded card')
            hitters[club][nm] = card
        pnames = ROTATIONS[club] + pens[club]
        if len(pnames) != 11 or len(set(pnames)) != 11:
            fail(f'{club}: expected 11 distinct rostered pitchers, '
                 f'got {len(pnames)}')
        pitchers[club] = {}
        n_add = 0
        for nm in pnames:
            if (nm, slot) not in E.PITCHERS:
                fail(f'{club}: rostered pitcher {nm} has no loaded card')
            merged = E.pitcher_card(S, slot, nm)
            table = merged.get('card_table_2d6') or {}
            missing = [str(t) for t in range(2, 13) if str(t) not in table]
            if missing:
                fail(f'{club}: {nm} 2d6 table missing totals {missing}')
            if merged.get('addendum') is True and all(
                    k in merged for k in ('wp', 'hold', 'dp', 'inj',
                                          'stamina')):
                n_add += 1
            pitchers[club][nm] = merged
        addendum_counts[club] = n_add
    if addendum_counts != {'CHC': 11, 'MON': 11}:
        fail(f'merged addendum counts {addendum_counts}, expected 11/11 '
             '(a short guest count is the silent merge failure)')

    # ---- cross-check: hitter bodies vs data/cards.json card_bat
    cj = json.load(open(os.path.join(REPO, 'data', 'cards.json')))
    by_name = {}
    for key, rec in cj.items():
        club = key.split('|')[0]
        if club in ('CHC', 'MON'):
            by_name[(club, rec['name'])] = rec['card_bat']
    SHARED = ('sections', 'out_table', 'run', 'steal',
              'sac_bunt', 'dp', 'bats', 'throws')
    for club in ('CHC', 'MON'):
        for nm, card in hitters[club].items():
            rec = by_name.get((club, nm))
            if rec is None:
                fail(f'{club}: {nm} missing from data/cards.json')
            for f in SHARED:
                if canon(card.get(f)) != canon(rec.get(f)):
                    fail(f'{club}: {nm} field {f} differs between the '
                         f'loaded engine object and data/cards.json')
            # positions: cards.json carries the app pipeline's display
            # transformation of the fielding lines (build_cards.py:
            # rulebook_error_scale, rulebook_of_arm, and
            # derive_hitter_fielding), so range/e/arm are not expected
            # to byte-agree; the position sequence itself must. The
            # shipped fielding lines are the loaded governing ones
            # (spec Section 3 build note, 2026-10-28).
            eng_pos = [p['pos'] for p in card.get('positions') or []]
            app_pos = [p['pos'] for p in rec.get('positions') or []]
            if eng_pos != app_pos:
                fail(f'{club}: {nm} position sequence differs: '
                     f'{eng_pos} vs cards.json {app_pos}')

    # ---- FAC deck faces (the dice surface only; spec Section 3)
    raw_deck = json.load(open(FAC_DECK))
    deck = []
    seen = set()
    for c in raw_deck:
        fid = c['fac_id']
        if fid in seen:
            fail(f'FAC id {fid} appears twice')
        seen.add(fid)
        deck.append({'fac_id': fid, 'page': c['page'], 'd2d6': c['d2d6'],
                     'pct': c['pct'], 'd1d6': c['d1d6'],
                     'wp': bool(c['wp'])})
    if seen != set(range(1, 257)):
        fail('FAC deck ids are not exactly 1..256')
    deck.sort(key=lambda c: c['fac_id'])

    # ---- rare plays, as the engine loaded them
    rare = E.RARE
    if len(rare) != 24:
        fail(f'expected 24 rare plays, engine loaded {len(rare)}')

    # ---- parks by name
    parks_all = json.load(open(os.path.join(
        APP_DATA, 'ballparks.json')))['ballparks']
    parks = {}
    for name in ('Wrigley Field', 'Stade Olympique'):
        hit = [b for b in parks_all if b['name'] == name]
        if len(hit) != 1:
            fail(f'park {name!r} found {len(hit)} times')
        parks[name] = hit[0]
    if canon(parks['Wrigley Field']) != canon(E.FENWAY):
        fail('Wrigley entry differs from the park the engine loaded')

    # ---- bunt grades for rostered hitters (the G1 overlay source)
    grades_all = G1.bunt_overlay()
    bunt_grades = {}
    for club in ('CHC', 'MON'):
        for nm in hitters[club]:
            if nm in grades_all:
                bunt_grades[nm] = grades_all[nm]

    # ---- staged lineups pass S1 legality (a)-(c) as shipped
    POS9 = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH']
    for club in ('CHC', 'MON'):
        nine = lineups[club]
        if sorted(s['pos'] for s in nine) != sorted(POS9):
            fail(f'{club}: staged nine do not cover the nine positions')
        if len({s['name'] for s in nine}) != 9:
            fail(f'{club}: staged nine contain a duplicate')
        for s in nine:
            if s['pos'] == 'DH':
                continue
            carded = [p['pos'] for p in hitters[club][s['name']]['positions']]
            if s['pos'] not in carded:
                fail(f"{club}: {s['name']} staged at {s['pos']} but "
                     f"carded at {carded}")

    data = {
        'fixture': {
            'id': 'R1-06',
            'label': 'R1-06 fixture, exhibition',
            'clubs': {
                'CHC': {'name': 'Chicago Cubs', 'short': 'Chicago',
                        'manager': 'Frank Chance',
                        'park': 'Wrigley Field'},
                'MON': {'name': 'Montreal Expos', 'short': 'Montreal',
                        'manager': 'Dick Williams',
                        'park': 'Stade Olympique'},
            },
            'home_default': 'CHC',
            'lineups': lineups,
            'benches': benches,
            'pens': pens,
            'pen_roles': pen_roles,
            'rotations': ROTATIONS,
            'default_starters': {'CHC': G1.CHC_SP, 'MON': G1.MON_SP},
            'closers': {'CHC': G1.CHC_CLOSER, 'MON': G1.MON_CLOSER},
        },
        'hitters': hitters,
        'pitchers': pitchers,
        'deck': deck,
        'rare_plays': rare,
        'parks': parks,
        'bunt_grades': bunt_grades,
    }
    text = json.dumps(data, sort_keys=True, separators=(',', ':')) + '\n'
    with open(OUT, 'w') as f:
        f.write(text)
    print(f'build_playable_data: wrote {OUT} '
          f'({len(text)} bytes; addendum merged CHC '
          f'{addendum_counts["CHC"]}/11, MON {addendum_counts["MON"]}/11; '
          f'bunt grades for {len(bunt_grades)} rostered hitters)')


if __name__ == '__main__':
    main()
