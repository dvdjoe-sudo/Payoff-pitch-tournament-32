#!/usr/bin/env python3
"""Solver fixes that do not need the 1986 reference files."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from calibration import apply_so_modifier
from pitcher_solver import evaluate_vs_hitters, optimize


def base_vector():
    return {
        '1B': 0.20, '2B': 0.05, '3B': 0.01, 'HR': 0.02,
        'BB': 0.0, 'HBP': 0.0, 'SO': 0.30, 'OUT': 0.42, 'RARE_PLAY': 0.0,
    }


def vectors():
    tough = base_vector()
    other = {
        '1B': 0.10, '2B': 0.02, '3B': 0.0, 'HR': 0.01,
        'BB': 0.08, 'HBP': 0.01, 'SO': 0.05, 'OUT': 0.73, 'RARE_PLAY': 0.0,
    }
    names = ('WHEELHOUSE', 'PATIENT', 'TOUGH', 'IN-PLAY', 'BALLPARK',
             'DEFENSE', 'PATIENT-OUT', 'TOUGH-OUT')
    return {name: dict(tough if name.startswith('TOUGH') else other) for name in names}


def test_so_modifier_increases_strikeouts():
    raw = base_vector()
    bumped = apply_so_modifier(raw, '+10')
    assert bumped['SO'] > raw['SO']
    assert apply_so_modifier(raw, 'NONE')['SO'] == raw['SO']
    assert abs(sum(bumped[k] for k in bumped if k != 'RARE_PLAY') - 1) < 1e-9


def test_optimize_is_seeded_and_uses_hand():
    target = {'so_bf': 0.20, 'bb_bf': 0.08, 'hr_bf': 0.02}
    seen = []

    def fake(hand):
        seen.append(hand)
        return vectors()

    import event_vectors
    event_vectors.vectors_for = fake
    first = optimize(target, restarts=2, iters=3, hand='L', seed=11)
    second = optimize(target, restarts=2, iters=3, hand='L', seed=11)
    third = optimize(target, restarts=2, iters=3, hand='R', seed=12)
    assert first[0] == second[0]
    assert seen and set(seen) >= {'L', 'R'}
    # The modifier changes the TOUGH strikeout rate the search sees.
    plain = evaluate_vs_hitters(
        {'2': 'TOUGH', '3': 'TOUGH', '4': 'TOUGH', '5': 'TOUGH',
         '6': 'TOUGH', '7': 'TOUGH', '8': 'TOUGH', '9': 'TOUGH',
         '10': 'TOUGH', '11': 'TOUGH', '12': 'TOUGH'},
        'L', 'NONE', vectors())
    wide = evaluate_vs_hitters(
        {'2': 'TOUGH', '3': 'TOUGH', '4': 'TOUGH', '5': 'TOUGH',
         '6': 'TOUGH', '7': 'TOUGH', '8': 'TOUGH', '9': 'TOUGH',
         '10': 'TOUGH', '11': 'TOUGH', '12': 'TOUGH'},
        'L', '+20', vectors())
    assert wide['so_bf'] > plain['so_bf']
    assert third[0]


if __name__ == '__main__':
    test_so_modifier_increases_strikeouts()
    test_optimize_is_seeded_and_uses_hand()
    print('pitcher solver tests passed')
