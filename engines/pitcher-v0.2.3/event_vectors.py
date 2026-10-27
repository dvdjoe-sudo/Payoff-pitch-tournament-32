#!/usr/bin/env python3
"""v0.1.1 exact category-to-event engine.

Precomputes event vectors for each pitcher category against the frozen
596-hitter 1986 environment. No Monte Carlo in the optimizer.
"""
import json, os

HIST = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(os.path.dirname(HIST), 'historical-cards', 'reference')

with open(os.path.join(REF, 'cards_1986.json')) as f:
    ALL = json.load(f)['players']
HITTERS = [p for p in ALL if not p.get('pitcher')]

with open(os.path.join(REF, 'ballparks.json')) as f:
    PARKS = json.load(f)

# Map section outcomes to events
# Each section has ranges like {'HR': [1,5], '2B': [6,10], ...}
# Anything not in a range is OUT


def section_events(section, hand):
    """Compute event probabilities for a hitter section.
    Returns dict: 1B, 2B, 3B, HR, BB, HBP, SO, OUT (probabilities sum to 1.0).
    Percentile 00 (100) is RARE_PLAY, tracked separately.
    """
    tbl = section.get(hand, {})
    events = {'1B': 0, '2B': 0, '3B': 0, 'HR': 0, 'BB': 0,
              'HBP': 0, 'SO': 0, 'OUT': 0, 'RARE_PLAY': 0}
    covered = 0
    for outcome, rng in tbl.items():
        if not rng or len(rng) < 2:
            continue
        w = (rng[1] - rng[0] + 1) / 100.0  # 1-100 scale (00=100)
        covered += w
        # Map outcome names to events
        if outcome in ('1B', '2B', '3B', 'HR', 'BB', 'HBP', 'SO'):
            events[outcome] += w
        elif outcome == 'RARE':
            events['RARE_PLAY'] += w
        # OUT, etc. go to OUT bucket via remainder
    events['OUT'] = max(0, 1.0 - covered - events['RARE_PLAY'])
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
    # PATIENT-OUT: preserves BB/HBP, else OUT
    po = vectors['PATIENT'].copy()
    po_out = po['BB'] + po['HBP']
    vectors['PATIENT-OUT'] = {
        '1B': 0, '2B': 0, '3B': 0, 'HR': 0,
        'BB': po['BB'], 'HBP': po['HBP'], 'SO': 0,
        'OUT': 1.0 - po_out, 'RARE_PLAY': 0,
    }
    # TOUGH-OUT: preserves SO, else OUT
    to = vectors['TOUGH'].copy()
    vectors['TOUGH-OUT'] = {
        '1B': 0, '2B': 0, '3B': 0, 'HR': 0, 'BB': 0, 'HBP': 0,
        'SO': to['SO'], 'OUT': 1.0 - to['SO'], 'RARE_PLAY': 0,
    }
    # BALLPARK: mixture of WHEELHOUSE and IN-PLAY vectors
    # v0.1.1: use 50/50 as placeholder; v0.2 will use actual park cards
    # Actually, per Joe: use park's WH/IP probability. For now, neutral.
    wh = vectors['WHEELHOUSE']
    ip = vectors['IN-PLAY']
    vectors['BALLPARK'] = {k: 0.5 * wh[k] + 0.5 * ip[k] for k in wh}
    # DEFENSE: league-average defensive outcome (placeholder v0.1.1)
    # Per rules: routes through defensive check. Use fixed vector.
    vectors['DEFENSE'] = {
        '1B': 0.25, '2B': 0.02, '3B': 0.005, 'HR': 0, 'BB': 0,
        'HBP': 0, 'SO': 0, 'OUT': 0.725, 'RARE_PLAY': 0,
    }
    return vectors


# Precompute for both hands
VECTORS_RHP = build_category_vectors('R')
VECTORS_LHP = build_category_vectors('L')

print("v0.1.1 event vectors built.")
print(f"\nWHEELHOUSE vs RHP: {VECTORS_RHP['WHEELHOUSE']}")
print(f"\nTOUGH vs RHP: {VECTORS_RHP['TOUGH']}")
print(f"\nPATIENT-OUT vs RHP: {VECTORS_RHP['PATIENT-OUT']}")


if __name__ == '__main__':
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
