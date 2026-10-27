#!/usr/bin/env python3
"""v0.1.1 exact category-to-event engine.

Precomputes event vectors for each pitcher category against the frozen
596-hitter 1986 environment. No Monte Carlo in the optimizer.
"""
import json, os

HIST = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(os.path.dirname(HIST), 'historical-cards', 'reference')

ALL = None
HITTERS = None
PARKS = None

# Map section outcomes to events
# Each section has ranges like {'HR': [1,5], '2B': [6,10], ...}
# Anything not in a range is OUT


def section_events(section, hand):
    """Event probabilities for one hitter section. The 100 faces are 00-99.

    Face 00 is a rare play (rulebook p.4), not an out. Each printed face
    from 01-99 has probability 1/100. A face in that span that misses every
    result band is an out. Probabilities sum to 1.0 when the bands do not
    overlap and stay inside 01-99.
    """
    tbl = section.get(hand, {})
    events = {'1B': 0, '2B': 0, '3B': 0, 'HR': 0, 'BB': 0,
              'HBP': 0, 'SO': 0, 'OUT': 0, 'RARE_PLAY': 0}
    covered_faces = 0
    for outcome, rng in tbl.items():
        if not rng or len(rng) < 2 or rng[1] < rng[0]:
            continue
        faces = int(rng[1]) - int(rng[0]) + 1
        covered_faces += faces
        share = faces / 100.0
        if outcome in ('1B', '2B', '3B', 'HR', 'BB', 'HBP', 'SO'):
            events[outcome] += share
        elif outcome == 'RARE':
            events['RARE_PLAY'] += share
    events['RARE_PLAY'] += 0.01
    events['OUT'] = max(0, 99 - covered_faces) / 100.0
    return events


def build_category_vectors(pitcher_hand='R'):
    """Build event vectors for each pitcher category.
    pitcher_hand: 'R' (vsRHP) or 'L' (vsLHP).
    Returns dict: category -> event probs (averaged over hitter population).
    """
    hand_key = 'vsRHP' if pitcher_hand == 'R' else 'vsLHP'
    # Categories map to hitter sections
    cat_to_sec = {
        'WHEELHOUSE': 'WHEELHOUSE',
        'PATIENT': 'PATIENT',
        'TOUGH': 'TOUGH',
        'IN-PLAY': 'IN-PLAY',
    }
    vectors = {}
    for cat, sec in cat_to_sec.items():
        agg = {'1B': 0, '2B': 0, '3B': 0, 'HR': 0, 'BB': 0,
               'HBP': 0, 'SO': 0, 'OUT': 0, 'RARE_PLAY': 0}
        n = 0
        for h in HITTERS:
            if sec not in h.get('sections', {}):
                continue
            ev = section_events(h['sections'][sec], hand_key)
            for k in agg:
                agg[k] += ev[k]
            n += 1
        if n > 0:
            for k in agg:
                agg[k] /= n
        vectors[cat] = agg
    # Special categories
    # PATIENT-OUT (rulebook p.2): BB and HBP count. Every other PATIENT
    # face is an out. Face 00 stays a rare play.
    po = vectors['PATIENT']
    po_keep = po['BB'] + po['HBP']
    vectors['PATIENT-OUT'] = {
        '1B': 0, '2B': 0, '3B': 0, 'HR': 0,
        'BB': po['BB'], 'HBP': po['HBP'], 'SO': 0,
        'OUT': max(0.0, 1.0 - po_keep - po['RARE_PLAY']),
        'RARE_PLAY': po['RARE_PLAY'],
    }
    # TOUGH-OUT: a face in the SO band is a strikeout. The book sends every
    # face above that band to the out section, so hits in this vector are
    # removed. Face 00 stays a rare play.
    to = vectors['TOUGH']
    vectors['TOUGH-OUT'] = {
        '1B': 0, '2B': 0, '3B': 0, 'HR': 0, 'BB': 0, 'HBP': 0,
        'SO': to['SO'],
        'OUT': max(0.0, 1.0 - to['SO'] - to['RARE_PLAY']),
        'RARE_PLAY': to['RARE_PLAY'],
    }
    # BALLPARK and DEFENSE below are the frozen solver placeholders.
    # The rulebook reads BALLPARK off the home park chart (not a 50/50
    # mix) and reads DEFENSE off the position chart plus that park's
    # range or error band (not a 25% single). engines/sim uses the
    # printed charts. These two vectors stay as the v0.2.3 fit saw them,
    # because the 1986 reference files are not in this repo and the
    # converted cards were not rebuilt.
    wh = vectors['WHEELHOUSE']
    ip = vectors['IN-PLAY']
    vectors['BALLPARK'] = {k: 0.5 * wh[k] + 0.5 * ip[k] for k in wh}
    vectors['DEFENSE'] = {
        '1B': 0.25, '2B': 0.02, '3B': 0.005, 'HR': 0, 'BB': 0,
        'HBP': 0, 'SO': 0, 'OUT': 0.725, 'RARE_PLAY': 0,
    }
    return vectors


# The 1986 cards are loaded on first use. Importing this module does
# not open them and does not print. section_events gives face 00 to
# RARE_PLAY and divides each 01-99 face by 100.
_VECTORS = {}
_PLAYERS = None


def load_players():
    """Return (all players, hitters). Opens the 1986 reference once."""
    global ALL, HITTERS, _PLAYERS
    if _PLAYERS is None:
        with open(os.path.join(REF, 'cards_1986.json')) as f:
            ALL = json.load(f)['players']
        HITTERS = [p for p in ALL if not p.get('pitcher')]
        with open(os.path.join(REF, 'ballparks.json')) as f:
            global PARKS
            PARKS = json.load(f)
        _PLAYERS = (ALL, HITTERS)
    return _PLAYERS


def vectors_for(pitcher_hand='R'):
    key = 'R' if pitcher_hand == 'R' else 'L'
    if key not in _VECTORS:
        load_players()
        _VECTORS[key] = build_category_vectors(key)
    return _VECTORS[key]


def get_vectors():
    return vectors_for('R'), vectors_for('L')


if __name__ == '__main__':
    VECTORS_RHP = vectors_for('R')
    VECTORS_LHP = vectors_for('L')
    print("v0.1.1 event vectors built.")
    print(f"\nWHEELHOUSE vs RHP: {VECTORS_RHP['WHEELHOUSE']}")
    print(f"\nTOUGH vs RHP: {VECTORS_RHP['TOUGH']}")
    print(f"\nPATIENT-OUT vs RHP: {VECTORS_RHP['PATIENT-OUT']}")

    # Test 1: known hitter + category produces exact vector
    h = next(p for p in HITTERS if p['name'] == 'Don Mattingly')
    ev = section_events(h['sections']['WHEELHOUSE'], 'vsRHP')
    print(f"\nTest 1 - Mattingly WHEELHOUSE vsRHP: {ev}")
    print(f"  Sum: {sum(ev.values()):.4f} (should be 1.0)")

    # Test 5: Don Aase analytical vs structure
    from pitcher_solver import table_to_probs, D6_W
    aase = next(p for p in ALL if p.get('pitcher') and p['name'] == 'Don Aase')
    tbl = aase['pitcher']['results']
    print(f"\nTest 5 - Aase table loaded: {len(tbl)} slots")
