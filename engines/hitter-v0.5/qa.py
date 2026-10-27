#!/usr/bin/env python3
"""QA warnings for generated hitter cards.

Flags cards that are statistically fine but structurally suspicious.
These go to Joe for review; they are not auto-rejected.
"""
import json, sys


def qa_warnings(card, exp, tgt, row):
    w = []
    secs = card['sections']

    # 1. Extreme ranges: any single outcome covering 90+ of a section
    for sec in ('WHEELHOUSE', 'PATIENT', 'TOUGH', 'IN-PLAY'):
        for hand in ('vsLHP', 'vsRHP'):
            for outcome, rng in secs[sec][hand].items():
                if rng and (rng[1] - rng[0] + 1) >= 90:
                    w.append(f"Extreme range: {sec} {hand} {outcome} "
                             f"{rng[0]}-{rng[1]} covers 90+ points")

    # 2. Empty sections: a section with no hit outcomes at all
    for sec in ('WHEELHOUSE', 'IN-PLAY'):
        for hand in ('vsLHP', 'vsRHP'):
            hits = [o for o in ('HR', '2B', '3B', '1B')
                    if secs[sec][hand].get(o)]
            if not hits:
                w.append(f"Empty section: {sec} {hand} has no hit outcomes")

    # 3. Reverse platoon: check if vsLHP expected AVG+SLG wildly exceeds vsRHP
    # (or vice versa) beyond what the input suggests
    # (detailed check needs per-hand targets; flag if TOUGH SO differs by 20+)
    for sec in ('TOUGH',):
        lhp_so = secs[sec]['vsLHP'].get('SO')
        rhp_so = secs[sec]['vsRHP'].get('SO')
        if lhp_so and rhp_so:
            lw = lhp_so[1] - lhp_so[0] + 1
            rw = rhp_so[1] - rhp_so[0] + 1
            if abs(lw - rw) >= 20:
                w.append(f"Large platoon gap: {sec} SO width LHP={lw} "
                         f"vs RHP={rw} (20+ point difference)")

    # 4. Small-sample input: PA < 300
    try:
        pa = float(row.get('PA') or 0)
        if pa < 300:
            w.append(f"Small sample: only {pa:.0f} PA in source data")
    except (ValueError, TypeError):
        pass

    # 5. IBB-heavy: IBB > 25% of BB means card OBP understates real OBP
    try:
        bb = float(row.get('BB') or 0)
        ibb = float(row.get('IBB') or 0)
        if bb > 0 and ibb / bb > 0.25:
            w.append(f"IBB-heavy: {ibb:.0f} of {bb:.0f} walks ({ibb/bb:.0%}) "
                     f"were intentional; card targets unintentional rate only")
    except (ValueError, TypeError, ZeroDivisionError):
        pass

    # 6. Fit drift: any single stat off by more than 2x tolerance
    tols = {'avg': 0.003, 'obp': 0.005, 'slg': 0.008, 'bbp': 0.003,
            'sop': 0.003, 'hrp': 0.0015, 'hbpp': 0.0015}
    for k, tol in tols.items():
        if abs(exp[k] - tgt[k]) > 2 * tol:
            w.append(f"Fit drift: {k} off by "
                     f"{(exp[k]-tgt[k])*(1000 if k in ('avg','obp','slg') else 100):+.2f} "
                     f"(>2x tolerance)")

    return w


if __name__ == '__main__':
    # usage: qa.py <card.json>  (reads stat_line from card for row data)
    card = json.load(open(sys.argv[1]))
    # exp/tgt would come from solver; stub for standalone use
    print("QA module loaded. Call qa_warnings(card, exp, tgt, row).")
