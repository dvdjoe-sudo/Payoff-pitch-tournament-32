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

# Load 1986 data
with open(os.path.join(REF, 'cards_1986.json')) as f:
    ALL = json.load(f)['players']
HITTERS_1986 = [p for p in ALL if not p.get('pitcher')]
PITCHERS_1986 = [p for p in ALL if p.get('pitcher')]

print(f"Loaded: {len(HITTERS_1986)} hitters, {len(PITCHERS_1986)} pitchers (1986)")


def table_to_probs(table):
    """Convert 2d6 table (dict 2-12 -> outcome) to outcome probabilities."""
    probs = {o: 0.0 for o in OUTCOMES}
    for roll, outcome in table.items():
        probs[outcome] += D6_W[int(roll)] / D6_TOTAL
    return probs


def evaluate_vs_hitters(table, pitcher_hand='R'):
    """Evaluate 2d6 table against 1986 hitter population using exact vectors.
    No Monte Carlo. Sum of (2d6_weight * category_event_vector).
    """
    from event_vectors import VECTORS_RHP, VECTORS_LHP
    vecs = VECTORS_RHP if pitcher_hand == 'R' else VECTORS_LHP
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


def random_table():
    """Generate random legal 2d6 table."""
    return {str(r): random.choice(OUTCOMES) for r in range(2, 13)}


def neighbor(table):
    """Single-slot mutation."""
    t = dict(table)
    r = str(random.randint(2, 12))
    t[r] = random.choice([o for o in OUTCOMES if o != t[r]])
    return t


def optimize(target, restarts=10, iters=500):
    """Multi-start local search. Returns (best_table, best_err, diagnostics)."""
    best_err, best_table = float('inf'), None
    init_err = None
    best_restart = -1
    for i in range(restarts):
        tbl = random_table()
        e = err(evaluate_vs_hitters(tbl), target)
        if i == 0:
            init_err = e
        # hill climb
        for _ in range(iters):
            nt = neighbor(tbl)
            ne = err(evaluate_vs_hitters(nt), target)
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
    aase = next(p for p in PITCHERS_1986 if p['name'] == 'Don Aase')
    actual = aase['pitcher']['results']
    print(f"\nDon Aase actual 1986 table: {actual}")
    print(f"Outcome probs: {table_to_probs(actual)}")
