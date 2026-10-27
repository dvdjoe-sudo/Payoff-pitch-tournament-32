#!/usr/bin/env python3
"""v0.2.3 PRODUCTION: Run all 160 historical pitchers."""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from historical_solver import solve_historical
from calibration import full_pipeline, apply_calibration
from translation import get_era_avg

INPUT = '../input/production_pitchers_160.csv'
OUTPUT = '../output/production_v023.csv'

def main():
    rows = list(csv.DictReader(open(INPUT)))
    print(f"Production run: {len(rows)} pitchers")
    results = []
    for i, r in enumerate(rows, 1):
        name = r['Name']
        throws = r['Throws']
        hand = 'R' if throws == 'R' else 'L'
        bf = float(r['BF'])
        if bf < 100:
            print(f"[{i}/{len(rows)}] {name}: SKIP (BF {bf} < 100)")
            continue
        # Career span for era normalization
        try:
            start = int(r['CareerStart'])
            end = int(r['CareerEnd']) if r['CareerEnd'] else 2026
            mid = (start + end) // 2
        except:
            mid = 2000
        # Raw rates
        raw = {
            'h_bf': float(r['H']) / bf,
            'hr_bf': float(r['HR']) / bf,
            'bb_bf': float(r['BB']) / bf,
            'so_bf': float(r['SO']) / bf,
            'hbp_bf': float(r['HBP']) / bf,
        }
        # v0.2.3 pipeline
        pipeline = full_pipeline(raw, mid)
        full_target = pipeline['solver_target']
        target = {
            'so_bf': full_target['so_bf'],
            'bb_bf': full_target['bb_bf'],
            'hr_bf': full_target['hr_bf'],
        }
        print(f"[{i}/{len(rows)}] {name} ({mid})...", flush=True)
        res = solve_historical(target, hand, restarts=10)
        ev = res['events']
        # Determine primary constraint for ARCHITECTURE-LIMITED
        status = res['status']
        constraint = ''
        if 'ARCHITECTURE' in status or 'HISTORICAL' in status:
            # Find which of SO/BB/HR missed most
            errs = {
                'SO': abs(target['so_bf'] - ev['so_bf']),
                'BB': abs(target['bb_bf'] - ev['bb_bf']),
                'HR': abs(target['hr_bf'] - ev['hr_bf']),
            }
            worst = max(errs, key=errs.get)
            # Check for interactions
            sorted_errs = sorted(errs.items(), key=lambda x: -x[1])
            if sorted_errs[1][1] > 0.01:  # Second worst also significant
                constraint = f"{sorted_errs[0][0]} + {sorted_errs[1][0]} interaction"
            else:
                constraint = worst
        results.append({
            'name': name, 'throws': throws,
            'career_start': start, 'career_end': end,
            'fit_error': round(res['fit_error'], 4),
            'so_modifier': res.get('so_modifier', 'NONE'),
            'primary_constraint': constraint,
            'status': status,
        })
        print(f"  -> {status} (err {res['fit_error']:.4f}, SOmod {res.get('so_modifier')})")

    # Write output
    with open(OUTPUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys())
        w.writeheader()
        w.writerows(results)

    # Summary
    from collections import Counter
    c = Counter(r['status'] for r in results)
    print(f"\n{'='*50}")
    print(f"PRODUCTION COMPLETE: {len(results)} pitchers")
    for k, v in sorted(c.items()):
        print(f"  {k}: {v}")
    print(f"{'='*50}")

if __name__ == '__main__':
    main()
