#!/usr/bin/env python3
"""v0.1.1 pitcher reconstruction: 30 pitchers, actual vs generated."""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from event_vectors import VECTORS_RHP, VECTORS_LHP
from pitcher_solver import evaluate_vs_hitters, optimize, table_to_probs, D6_W

HIST = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(os.path.dirname(HIST), 'historical-cards', 'reference')
with open(os.path.join(REF, 'cards_1986.json')) as f:
    ALL = json.load(f)['players']
PITCHERS = {p['name']: p for p in ALL if p.get('pitcher')}


def run_reconstruction(csv_path):
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    results = []
    for r in rows:
        name = r['pitcher']
        throws = r['throws']
        hand = 'R' if throws == 'R' else 'L'
        if name not in PITCHERS:
            print(f"{name}: NOT FOUND in 1986 set")
            continue
        actual_card = PITCHERS[name]['pitcher']['results']
        # Target: actual card's event vector
        target = evaluate_vs_hitters(actual_card, hand)
        # Optimize to reconstruct
        gen_table, best_err, diag = optimize(target, restarts=10, iters=300)
        gen_events = evaluate_vs_hitters(gen_table, hand)
        # Compare
        print(f"\n{name} ({throws})")
        print(f"  Actual H/BF: {target['h_bf']:.3f} -> Gen: {gen_events['h_bf']:.3f}")
        print(f"  Actual BB/BF: {target['bb_bf']:.3f} -> Gen: {gen_events['bb_bf']:.3f}")
        print(f"  Actual SO/BF: {target['so_bf']:.3f} -> Gen: {gen_events['so_bf']:.3f}")
        print(f"  Actual HR/BF: {target['hr_bf']:.3f} -> Gen: {gen_events['hr_bf']:.3f}")
        print(f"  Fit error: {best_err:.4f}, Improvement: {diag['improvement']:.1f}%")
        results.append({
            'name': name, 'fit_error': round(best_err, 4),
            'h_bf_actual': round(target['h_bf'], 3),
            'h_bf_gen': round(gen_events['h_bf'], 3),
            'bb_bf_actual': round(target['bb_bf'], 3),
            'bb_bf_gen': round(gen_events['bb_bf'], 3),
            'so_bf_actual': round(target['so_bf'], 3),
            'so_bf_gen': round(gen_events['so_bf'], 3),
            'hr_bf_actual': round(target['hr_bf'], 3),
            'hr_bf_gen': round(gen_events['hr_bf'], 3),
        })
    # Write results
    out = os.path.join(HIST, 'output', 'reconstruction_v011.csv')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys())
        w.writeheader()
        w.writerows(results)
    print(f"\n{len(results)} pitchers reconstructed. Results: {out}")


if __name__ == '__main__':
    run_reconstruction(sys.argv[1])
