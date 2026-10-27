#!/usr/bin/env python3
"""v0.2 historical pitcher stress test: 24 pitchers."""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from historical_solver import solve_historical

HIST = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_stress(csv_path):
    from calibration import full_pipeline
    from career_spans import get_mid_year
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    results = []
    for r in rows:
        name = r['Name']
        throws = r['Throws']
        hand = 'R' if throws == 'R' else 'L'
        bf = float(r['BF'])
        # Raw career rates
        raw = {
            'h_bf': float(r['H']) / bf,
            'hr_bf': float(r['HR']) / bf,
            'bb_bf': float(r['BB']) / bf,
            'so_bf': float(r['SO']) / bf,
            'hbp_bf': float(r['HBP']) / bf,
        }
        # v0.2.3: actual career span for era normalization
        mid_year = get_mid_year(name)
        pipeline = full_pipeline(raw, mid_year)
        full_target = pipeline['solver_target']
        # v0.2.3: THREE PRIMARY ONLY (SO/BB/HR). H/BF diagnostic, zero weight.
        target = {
            'so_bf': full_target['so_bf'],
            'bb_bf': full_target['bb_bf'],
            'hr_bf': full_target['hr_bf'],
        }
        # Keep H for diagnostic reporting
        h_target = full_target['h_bf']
        print(f"\n{name} ({throws}, {mid_year})...")
        res = solve_historical(target, hand, restarts=10)
        ev = res['events']
        print(f"  SO/BF: {target['so_bf']:.3f} -> {ev['so_bf']:.3f}")
        print(f"  BB/BF: {target['bb_bf']:.3f} -> {ev['bb_bf']:.3f}")
        print(f"  HR/BF: {target['hr_bf']:.3f} -> {ev['hr_bf']:.3f}")
        print(f"  H/BF (diag): {h_target:.3f} -> {ev['h_bf']:.3f}")
        print(f"  SO modifier: {res.get('so_modifier', 'NONE')}")
        print(f"  Status: {res['status']}")
        # Audit trail
        era_avg = __import__('translation').get_era_avg(mid_year)
        results.append({
            'name': name, 'throws': throws,
            'career_span': f"{__import__('career_spans').CAREER_SPANS.get(name, ('?','?'))[0]}-{__import__('career_spans').CAREER_SPANS.get(name, ('?','?'))[1]}",
            'mid_year': mid_year,
            'raw_so': round(raw['so_bf'], 4),
            'era_league_so': round(era_avg['so_bf'], 4),
            'norm_so': round(pipeline['era_normalized']['so_bf'], 4),
            'target_so': round(target['so_bf'], 4),
            'gen_so': round(ev['so_bf'], 4),
            'fit_error': round(res['fit_error'], 4),
            'so_modifier': res.get('so_modifier', 'NONE'),
            'status': res['status'],
        })
    out = os.path.join(HIST, 'output', 'pitcher_stress_v02.csv')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys())
        w.writeheader()
        w.writerows(results)
    # Summary
    n_pass = sum(1 for r in results if 'PASS' in r['status'])
    n_arch = sum(1 for r in results if 'ARCHITECTURE' in r['status'])
    n_solver = sum(1 for r in results if r['status'] == 'SOLVER-REVIEW')
    print(f"\n{len(results)} pitchers: {n_pass} PASS, {n_arch} ARCH, {n_solver} SOLVER-REVIEW")

if __name__ == '__main__':
    run_stress(sys.argv[1])
