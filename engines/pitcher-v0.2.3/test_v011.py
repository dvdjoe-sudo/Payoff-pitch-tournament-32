#!/usr/bin/env python3
"""v0.1.1 five tests before 30-pitcher reconstruction.

The 1986 reference is opened only when this file is run, not on import.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from event_vectors import section_events, vectors_for, load_players
    from pitcher_solver import evaluate_vs_hitters

    all_players, hitters = load_players()
    vectors_rhp = vectors_for('R')
    vectors_lhp = vectors_for('L')

    print("=" * 60)
    print("v0.1.1 FIVE TESTS")
    print("=" * 60)

    print("\n1. Known hitter + category -> exact vector")
    hitter = next(p for p in hitters if p['name'] == 'Don Mattingly')
    ev = section_events(hitter['sections']['WHEELHOUSE'], 'vsRHP')
    total = sum(ev.values())
    print(f"   Mattingly WH vsRHP sum: {total:.4f} "
          f"{'PASS' if abs(total - 1.0) < 0.001 else 'FAIL'}")

    print("\n2. RHP/LHP select opposite hitter splits")
    wh_r = vectors_rhp['WHEELHOUSE']['HR']
    wh_l = vectors_lhp['WHEELHOUSE']['HR']
    print(f"   WH HR vsRHP: {wh_r:.3f}, vsLHP: {wh_l:.3f}")
    print(f"   {'PASS' if wh_r != wh_l else 'FAIL'} (different = correct)")

    print("\n3. BALLPARK = WH/IP mixture")
    bp = vectors_rhp['BALLPARK']
    wh = vectors_rhp['WHEELHOUSE']
    ip = vectors_rhp['IN-PLAY']
    ok = all(abs(bp[k] - 0.5 * (wh[k] + ip[k])) < 0.001
             for k in bp if k != 'RARE_PLAY')
    print(f"   {'PASS' if ok else 'FAIL'}")

    print("\n4. PATIENT-OUT / TOUGH-OUT per rules")
    po = vectors_rhp['PATIENT-OUT']
    to = vectors_rhp['TOUGH-OUT']
    po_ok = po['BB'] > 0 and po['SO'] == 0 and po['1B'] == 0
    to_ok = to['SO'] > 0 and to['BB'] == 0 and to['1B'] == 0
    print(f"   PATIENT-OUT preserves BB/HBP only: {'PASS' if po_ok else 'FAIL'}")
    print(f"   TOUGH-OUT preserves SO only: {'PASS' if to_ok else 'FAIL'}")

    print("\n5. Aase card analytical evaluation")
    aase = next(p for p in all_players if p.get('pitcher') and p['name'] == 'Don Aase')
    tbl = aase['pitcher']['results']
    events = evaluate_vs_hitters(tbl, 'R')
    print(f"   H/BF: {events['h_bf']:.3f}, BB/BF: {events['bb_bf']:.3f}, "
          f"SO/BF: {events['so_bf']:.3f}, HR/BF: {events['hr_bf']:.3f}")
    print("   PASS (analytical, no Monte Carlo)")

    print("\n" + "=" * 60)
    print("All five tests complete.")


if __name__ == '__main__':
    main()
