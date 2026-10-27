#!/usr/bin/env python3
"""Pitcher solver v0.2: historical pitchers with special-category escalation.

1. Solve with 6 normal categories first.
2. If fit > threshold, unlock TOUGH-OUT, PATIENT-OUT.
3. Record which special was required.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pitcher_solver import optimize, evaluate_vs_hitters
from aliases import resolve

# Normal six
NORMAL_OUTCOMES = ['WHEELHOUSE', 'PATIENT', 'TOUGH', 'IN-PLAY',
                   'BALLPARK', 'DEFENSE']
# Specials (escalation)
SPECIAL_OUTCOMES = ['TOUGH-OUT', 'PATIENT-OUT']

FIT_THRESHOLD = 0.005  # v0.2: if core-six fit worse than this, try specials


def solve_historical(target, pitcher_hand='R', restarts=10, seed=0):
    """Solve with escalation. Returns (table, events, diagnostics).

    Tries SO modifiers NONE, +10, +20. The same seed is used for each
    modifier, and the modifier is applied inside the evaluation in the
    v2 direction, so the winner is the modifier that fits, not a
    second random search.
    """
    import pitcher_solver

    orig_outcomes = list(pitcher_solver.OUTCOMES)
    best_overall = None

    for mod in ['NONE', '+10', '+20']:
        pitcher_solver.OUTCOMES = list(NORMAL_OUTCOMES)
        tbl, err, diag = optimize(
            target, restarts=restarts, hand=pitcher_hand,
            seed=seed, so_modifier=mod)
        if best_overall is None or err < best_overall[1]:
            best_overall = (tbl, err, diag, mod)

    tbl, err, diag, mod = best_overall
    ev = evaluate_vs_hitters(tbl, pitcher_hand, mod)

    result = {
        'table': tbl, 'events': ev, 'fit_error': err,
        'core_six_fit': err, 'so_modifier': mod,
        'status': 'PASS' if err < FIT_THRESHOLD else 'HISTORICAL-TARGET-REVIEW',
        'diagnostics': diag,
    }

    # Escalate to specials if needed (existing logic). The winning
    # modifier stays in the evaluation.
    if err >= FIT_THRESHOLD:
        pitcher_solver.OUTCOMES = list(NORMAL_OUTCOMES) + list(SPECIAL_OUTCOMES)
        tbl2, err2, diag2 = optimize(
            target, restarts=restarts, hand=pitcher_hand,
            seed=seed + 1, so_modifier=mod)
        ev2 = evaluate_vs_hitters(tbl2, pitcher_hand, mod)
        specials_used = set(tbl2.values()) & set(SPECIAL_OUTCOMES)
        result.update({
            'table': tbl2, 'events': ev2, 'fit_error': err2,
            'with_specials': err2,
            'special_required': list(specials_used),
            'status': 'PASS — SPECIAL REQUIRED' if err2 < FIT_THRESHOLD
                      else 'HISTORICAL-TARGET-REVIEW',
        })

    pitcher_solver.OUTCOMES = orig_outcomes
    return result


if __name__ == '__main__':
    print("v0.2 historical pitcher solver loaded.")
    print(f"Fit threshold: {FIT_THRESHOLD}")
    print(f"Normal: {NORMAL_OUTCOMES}")
    print(f"Specials: {SPECIAL_OUTCOMES}")
