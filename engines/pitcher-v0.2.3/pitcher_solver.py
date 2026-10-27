#!/usr/bin/env python3
"""Pitcher card solver v0.1: generate legal 2d6 tables from target rates.

Calibrates against frozen 1986 hitter population.
Multi-start optimization from day one.
"""
import json, os, sys, random, itertools

HIST = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(os.path.dirname(HIST), 'historical-cards', 'reference')

# 2d6 weights
D6_W = {2:1, 3:2, 4:3, 5:4, 6:5, 7:6, 8:5, 9:4, 10:3, 11:2, 12:1}
D6_TOTAL = 36

# Legal outcomes per slot
OUTCOMES = ['WHEELHOUSE', 'PATIENT', 'TOUGH', 'IN-PLAY', 'BALLPARK', 'DEFENSE']

# The 1986 reference is opened on first use, not at import.
ALL = None
HITTERS_1986 = None
PITCHERS_1986 = None


def load_1986():
    global ALL, HITTERS_1986, PITCHERS_1986
    if ALL is None:
        with open(os.path.join(REF, 'cards_1986.json')) as f:
            ALL = json.load(f)['players']
        HITTERS_1986 = [p for p in ALL if not p.get('pitcher')]
        PITCHERS_1986 = [p for p in ALL if p.get('pitcher')]
    return ALL, HITTERS_1986, PITCHERS_1986


def table_to_probs(table):
    """Convert 2d6 table (dict 2-12 -> outcome) to outcome probabilities."""
    probs = {o: 0.0 for o in OUTCOMES}
    for roll, outcome in table.items():
        probs[outcome] += D6_W[int(roll)] / D6_TOTAL
    return probs


def _vectors_with_modifier(vecs, so_modifier):
    """Copy the category vectors and apply the v2 SO bump to TOUGH."""
    from calibration import apply_so_modifier
    out = dict(vecs)
    for key in ('TOUGH', 'TOUGH-OUT'):
        if key in out:
            out[key] = apply_so_modifier(out[key], so_modifier)
    return out


def evaluate_vs_hitters(table, pitcher_hand='R', so_modifier='NONE', vectors=None):
    """Evaluate 2d6 table against 1986 hitter population using exact vectors.
    No Monte Carlo. Sum of (2d6_weight * category_event_vector).

    pitcher_hand selects the vsRHP or vsLHP hitter vectors. so_modifier
    is the v2 band bump (NONE, +10, +20), applied before the events
    are scored. Pass vectors to score without opening the 1986 files.
    """
    if vectors is None:
        from event_vectors import vectors_for
        vectors = vectors_for(pitcher_hand)
    vecs = _vectors_with_modifier(vectors, so_modifier)
    total = {'1B': 0, '2B': 0, '3B': 0, 'HR': 0, 'BB': 0,
             'HBP': 0, 'SO': 0, 'OUT': 0, 'RARE_PLAY': 0}
    for roll_str, outcome in table.items():
        w = D6_W[int(roll_str)] / D6_TOTAL
        v = vecs.get(outcome, vecs['IN-PLAY'])  # fallback
        for k in total:
            total[k] += w * v[k]
    # Convert to BF rates (exclude RARE_PLAY from denominator for now)
    bf = 1.0 - total['RARE_PLAY']
    return {
        'h_bf': (total['1B'] + total['2B'] + total['3B'] + total['HR']) / bf,
        'bb_bf': total['BB'] / bf,
        'so_bf': total['SO'] / bf,
        'hr_bf': total['HR'] / bf,
        'hbp_bf': total['HBP'] / bf,
    }


def err(events, target):
    """Squared relative error."""
    return sum(((events[k] - target[k]) / max(target[k], 1e-4)) ** 2
               for k in target)


def random_table(rng):
    """Generate random legal 2d6 table from a seeded RNG."""
    return {str(r): rng.choice(OUTCOMES) for r in range(2, 13)}


def neighbor(table, rng):
    """Single-slot mutation."""
    t = dict(table)
    r = str(rng.randint(2, 12))
    t[r] = rng.choice([o for o in OUTCOMES if o != t[r]])
    return t


def optimize(target, restarts=10, iters=500, hand='R', seed=0,
             so_modifier='NONE', vectors=None):
    """Multi-start local search. Returns (best_table, best_err, diagnostics).

    hand is the pitcher's throwing hand and selects the hitter vectors.
    seed makes the search reproducible. so_modifier is applied inside
    every evaluation, in the v2 direction.
    """
    rng = random.Random(seed)
    best_err, best_table = float('inf'), None
    init_err = None
    best_restart = -1
    for i in range(restarts):
        tbl = random_table(rng)
        e = err(evaluate_vs_hitters(tbl, hand, so_modifier, vectors), target)
        if i == 0:
            init_err = e
        # hill climb
        for _ in range(iters):
            nt = neighbor(tbl, rng)
            ne = err(evaluate_vs_hitters(nt, hand, so_modifier, vectors), target)
            if ne < e:
                tbl, e = nt, ne
        if e < best_err:
            best_err, best_table, best_restart = e, tbl, i
    improvement = ((init_err - best_err) / init_err * 100) if init_err else 0
    return best_table, best_err, {
        'init_err': init_err, 'best_restart': best_restart,
        'improvement': improvement,
        'opt_status': 'UNSTABLE' if improvement > 50 else 'STABLE',
    }


if __name__ == '__main__':
    # v0.1 smoke test: reconstruct Don Aase's table
    _all, _hitters, pitchers = load_1986()
    print(f"Loaded: {len(_hitters)} hitters, {len(pitchers)} pitchers (1986)")
    aase = next(p for p in pitchers if p['name'] == 'Don Aase')
    actual = aase['pitcher']['results']
    print(f"\nDon Aase actual 1986 table: {actual}")
    print(f"Outcome probs: {table_to_probs(actual)}")
