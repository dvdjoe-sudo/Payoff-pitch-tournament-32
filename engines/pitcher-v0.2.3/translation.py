#!/usr/bin/env python3
"""v0.2.1 historical translation layer.

1. 1986 baseline rates (from printed cards)
2. Era normalization: translate historical performance relative to league
3. Supplemental SO modifier (+10/+20 on TOUGH)
4. Updated QA: PASS / HISTORICAL-TARGET-REVIEW / SOLVER-REVIEW /
   ARCHITECTURE-LIMITED / DATA-REVIEW
"""
# 1986 baseline from 484 printed cards (vs RHP)
BASELINE_1986 = {
    'h_bf': 0.2217,
    'bb_bf': 0.0872,
    'so_bf': 0.1593,
    'hr_bf': 0.0204,
    'hbp_bf': 0.0053,
}

# Approximate historical league averages by era (for era normalization)
# Format: (start_year, end_year, h_bf, bb_bf, so_bf, hr_bf)
ERA_LEAGUE_AVGS = [
    (1901, 1919, 0.250, 0.080, 0.080, 0.005),  # Deadball
    (1920, 1941, 0.280, 0.090, 0.080, 0.015),  # Live ball early
    (1942, 1962, 0.260, 0.095, 0.110, 0.020),  # Post-war
    (1963, 1976, 0.235, 0.085, 0.140, 0.018),  # Low offense
    (1977, 1992, 0.255, 0.085, 0.130, 0.022),  # DH era
    (1993, 2009, 0.265, 0.085, 0.160, 0.028),  # Expansion/high offense
    (2010, 2026, 0.245, 0.080, 0.200, 0.030),  # Modern strikeout era
]


def get_era_avg(year):
    """Get league average rates for a given year."""
    for start, end, h, bb, so, hr in ERA_LEAGUE_AVGS:
        if start <= year <= end:
            return {'h_bf': h, 'bb_bf': bb, 'so_bf': so, 'hr_bf': hr}
    return {'h_bf': 0.25, 'bb_bf': 0.085, 'so_bf': 0.13, 'hr_bf': 0.02}


def era_normalize(pitcher_rates, career_mid_year, damping=0.7):
    """Translate historical rates to 1986 environment.
    
    normalized = 1986_baseline * (pitcher_rate / era_league_rate) ^ damping
    
    Damping prevents over-translation of extreme early-era values.
    """
    era_avg = get_era_avg(career_mid_year)
    normalized = {}
    for k in ['h_bf', 'bb_bf', 'so_bf', 'hr_bf']:
        if era_avg[k] > 0 and pitcher_rates[k] > 0:
            ratio = pitcher_rates[k] / era_avg[k]
            # Apply damping: ratio^damping
            damped_ratio = ratio ** damping
            normalized[k] = BASELINE_1986[k] * damped_ratio
        else:
            normalized[k] = BASELINE_1986[k]
    # HBP: use raw (less era-dependent)
    normalized['hbp_bf'] = pitcher_rates.get('hbp_bf', BASELINE_1986['hbp_bf'])
    return normalized


# QA statuses v0.2.1
QA_PASS = 'PASS'
QA_HISTORICAL_TARGET = 'HISTORICAL-TARGET-REVIEW'
QA_SOLVER = 'SOLVER-REVIEW'
QA_ARCHITECTURE = 'ARCHITECTURE-LIMITED'
QA_DATA = 'DATA-REVIEW'


def classify_v021(fit_ok, has_era_norm, has_calibration, has_so_mod,
                  search_exhausted):
    """v0.2.1 QA: ARCHITECTURE-LIMITED only after all 4 conditions."""
    if fit_ok:
        return QA_PASS, 'within tolerance'
    if not (has_era_norm and has_calibration and has_so_mod and search_exhausted):
        return QA_HISTORICAL_TARGET, (
            'Target translation incomplete. Requires: era normalization, '
            '1986 calibration, supplemental SO modifier, exhaustive search.')
    return QA_ARCHITECTURE, (
        'Format cannot reproduce era-normalized target. Best legal card found.')


if __name__ == '__main__':
    print("v0.2.1 translation layer loaded.")
    print(f"1986 baseline: {BASELINE_1986}")
    # Example: Pedro Martinez (career ~1992-2009, mid ~2000)
    pedro_raw = {'h_bf': 0.195, 'bb_bf': 0.067, 'so_bf': 0.277, 'hr_bf': 0.021}
    pedro_norm = era_normalize(pedro_raw, 2000)
    print(f"\nPedro raw: {pedro_raw}")
    print(f"Pedro normalized: {pedro_norm}")
