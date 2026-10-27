#!/usr/bin/env python3
"""v0.2.2: 1986 calibration + supplemental SO modifier.

1. Calibration: printed_card_rate = a + b * actual_1986_rate
2. Supplemental SO: NONE, +10, +20 on TOUGH
3. Full pipeline: raw -> era-norm -> 1986-equiv -> calibration -> solver target
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from translation import era_normalize, BASELINE_1986

# Calibration coefficients (fit from 324 pitchers, BF-weighted, 2026-10-08)
# printed = a + b * actual
CALIBRATION = {
    'h_bf': {'a': 0.1268, 'b': 0.3976},   # R² 0.367 - WEAK, diagnostic only
    'bb_bf': {'a': 0.0008, 'b': 0.9041},  # R² 0.747
    'so_bf': {'a': 0.0124, 'b': 1.0353},  # R² 0.875 - STRONG
    'hr_bf': {'a': 0.0034, 'b': 0.6989},  # R² 0.660
}

def apply_calibration(rates):
    """Map 1986-equivalent rates to printed-card target space."""
    out = {}
    for k in ['h_bf', 'bb_bf', 'so_bf', 'hr_bf']:
        a, b = CALIBRATION[k]['a'], CALIBRATION[k]['b']
        out[k] = a + b * rates[k]
    out['hbp_bf'] = rates.get('hbp_bf', BASELINE_1986['hbp_bf'])
    return out


def full_pipeline(pitcher_rates, career_mid_year):
    """Raw -> era-norm -> 1986-equiv -> calibration -> solver target."""
    # Step 1: era normalization
    era_norm = era_normalize(pitcher_rates, career_mid_year)
    # Step 2: 1986 printed-card calibration
    target = apply_calibration(era_norm)
    return {
        'raw': pitcher_rates,
        'era_normalized': era_norm,
        'solver_target': target,
    }


# Supplemental SO modifier
# When +10/+20 is active, TOUGH section's SO range expands
SO_MODIFIERS = {
    'NONE': 0,
    '+10': 10,
    '+20': 20,
}

def apply_so_modifier(vector, modifier):
    """Adjust the TOUGH vector the way the tournament's v2 tracker reads a bump.

    The printed rulebook (ratings addendum) does something else. A card
    marked %roll +10 or +20 adds that amount to the percentile on a TOUGH
    result, and if the sum is greater than 99 the original face is used.
    Strikeout bands sit at the low end of TOUGH, so that shift produces
    fewer strikeouts. engines/sim/pa_sim.py follows the printed shift.

    This function follows engines/pitcher-v2/engine_v2.py, which is what
    the converted tournament cards were fit to play: the SO band widens by
    `bump` faces and strikeouts go up. It is the tracker rule. It is not
    the rulebook rule. The gain depends on where each hitter's SO band
    ends. This population vector moves bump/99 of the non-SO mass into SO.
    """
    v = dict(vector)
    bump = SO_MODIFIERS.get(modifier, 0)
    if not bump:
        return v
    non = [key for key in v if key not in ('SO', 'RARE_PLAY')]
    pool = sum(v.get(key, 0.0) for key in non)
    take = min(pool, bump / 99.0)
    if pool <= 0 or take <= 0:
        return v
    keep = (pool - take) / pool
    for key in non:
        v[key] = v.get(key, 0.0) * keep
    v['SO'] = v.get('SO', 0.0) + take
    return v


if __name__ == '__main__':
    print("v0.2.2 framework loaded.")
    print(f"Calibration (placeholder): {CALIBRATION}")
    # Test pipeline
    pedro = {'h_bf': 0.195, 'bb_bf': 0.067, 'so_bf': 0.277, 'hr_bf': 0.021}
    result = full_pipeline(pedro, 2000)
    print(f"\nPedro raw: {result['raw']}")
    print(f"Pedro era-norm: {result['era_normalized']}")
    print(f"Pedro solver target: {result['solver_target']}")
