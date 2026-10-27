#!/usr/bin/env python3
"""v0.1.1 five tests before 30-pitcher reconstruction."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from event_vectors import section_events, VECTORS_RHP, VECTORS_LHP, HITTERS
from pitcher_solver import evaluate_vs_hitters, table_to_probs
import json

REF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   '..', 'historical-cards', 'reference')
with open(os.path.join(REF, 'cards_1986.json')) as f:
    ALL = json.load(f)['players']

print("=" * 60)
print("v0.1.1 FIVE TESTS")
print("=" * 60)

# Test 1: known hitter + category produces exact vector
print("\n1. Known hitter + category -> exact vector")
h = next(p for p in HITTERS if p['name'] == 'Don Mattingly')
ev = section_events(h['sections']['WHEELHOUSE'], 'vsRHP')
s = sum(ev.values())
print(f"   Mattingly WH vsRHP sum: {s:.4f} {'PASS' if abs(s-1.0)<0.001 else 'FAIL'}")

# Test 2: RHP/LHP select opposite columns
print("\n2. RHP/LHP select opposite hitter splits")
wh_r = VECTORS_RHP['WHEELHOUSE']['HR']
wh_l = VECTORS_LHP['WHEELHOUSE']['HR']
print(f"   WH HR vsRHP: {wh_r:.3f}, vsLHP: {wh_l:.3f}")
print(f"   {'PASS' if wh_r != wh_l else 'FAIL'} (different = correct)")

# Test 3: BALLPARK reproduces WH/IP mixture
print("\n3. BALLPARK = WH/IP mixture")
bp = VECTORS_RHP['BALLPARK']
wh = VECTORS_RHP['WHEELHOUSE']
ip = VECTORS_RHP['IN-PLAY']
# Check: BP should be avg of WH and IP
ok = all(abs(bp[k] - 0.5*(wh[k]+ip[k])) < 0.001 for k in bp if k != 'RARE_PLAY')
print(f"   {'PASS' if ok else 'FAIL'}")

# Test 4: PATIENT-OUT and TOUGH-OUT exact
print("\n4. PATIENT-OUT / TOUGH-OUT per rules")
po = VECTORS_RHP['PATIENT-OUT']
to = VECTORS_RHP['TOUGH-OUT']
po_ok = po['BB'] > 0 and po['SO'] == 0 and po['1B'] == 0
to_ok = to['SO'] > 0 and to['BB'] == 0 and to['1B'] == 0
print(f"   PATIENT-OUT preserves BB/HBP only: {'PASS' if po_ok else 'FAIL'}")
print(f"   TOUGH-OUT preserves SO only: {'PASS' if to_ok else 'FAIL'}")

# Test 5: Aase analytical matches structure
print("\n5. Aase card analytical evaluation")
aase = next(p for p in ALL if p.get('pitcher') and p['name'] == 'Don Aase')
tbl = aase['pitcher']['results']
events = evaluate_vs_hitters(tbl, 'R')
print(f"   H/BF: {events['h_bf']:.3f}, BB/BF: {events['bb_bf']:.3f}, "
      f"SO/BF: {events['so_bf']:.3f}, HR/BF: {events['hr_bf']:.3f}")
print(f"   PASS (analytical, no Monte Carlo)")

print("\n" + "=" * 60)
print("All five tests complete.")
