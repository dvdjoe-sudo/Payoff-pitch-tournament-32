#!/usr/bin/env python3
"""pitcher_grammar_generator.py -- the new-generation PITCHER card
table generator. Standalone extraction from the workshop build
scripts of 2026-10-28 (build_pilot_cards.py's smoothed_fit and
pitcher table generator, built on pitcher_blind_test.py's
population, share, and decile machinery), made for the tournament
site's Engines page download. The extraction is faithful: same fit,
same greedy face assignment, same constants.

HOW THE GRAMMAR WORKS (the system the real 1986 cards were built
with, recovered by the 2026-10-27 system analysis): each section of
the 2d6 dice table is priced off its own rate. TOUGH share follows
the strikeout rate, PATIENT share the walk rate, WHEELHOUSE and the
stadium channel (BALLPARK) the home-run rate, DEFENSE is a token of
about one face dealt at the role median, and IN-PLAY takes whatever
faces remain. The fit is a set of decile ladders: pitchers grouped
in rate deciles, each bucket carrying the median section share of
its members, then smoothed (each bucket blended half itself, a
quarter each neighbor; edges three-quarters self, one quarter the
one neighbor). A generated card carries no supplemental strikeout
bump: the table itself does the work.

DATA INPUT: this file fits itself at import from
pitchers_1986.json, the parse of all 484 printed pitcher cards of
the official 1986 Payoff Pitch set, which must sit beside this
file (the tournament repository carries a copy next to it under
engines/). The production population is the 424 of those cards
with 60 or more batters faced (the same population the workshop
blind test used); the fit uses the whole population, train and
test recombined, exactly as the 2026-10-28 production build did.
Rates on a printed card are per batter faced, with BF approximated
as outs + hits + walks off the printed line, the workshop's
standing convention.

Rates fed to generate_table() are era-normalized per-BF rates:
{'so': ..., 'bb': ..., 'hr': ...} for the pitcher's prime window,
plus whether he is a starter (the DEFENSE token differs by role).
Output is a dice table: {total-as-string: section} for totals 2-12.

VALIDATION ANCHOR: Ubaldo Jimenez (era-normalized SO .1983,
BB .0999, HR .0124 per BF, starter) generates exactly:
2 DEFENSE, 3 IN-PLAY, 4 TOUGH, 5 TOUGH, 6 PATIENT, 7 TOUGH,
8 PATIENT, 9 TOUGH, 10 BALLPARK, 11 IN-PLAY, 12 DEFENSE.
The __main__ block checks that line when the file is run directly.

Blind-test standing (workshop, 2026-10-27/28): fit on a train
split and generated blind for 128 held-out 1986 pitchers, the
generated tables sat as close to the men's real rates as the
designers' own printed cards did (per-BF error vs real rates:
hits .052 generated vs .055 printed, walks .008 vs .012,
strikeouts .033 vs .035, home runs .008 vs .009; panel OPS error
.039 with zero bias after smoothing).
"""
import json, os, statistics as st
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

FACE_W = {t: 6 - abs(t - 7) for t in range(2, 13)}
D6W = {t: (6 - abs(t - 7)) / 36.0 for t in range(2, 13)}
SECS = ('TOUGH', 'PATIENT', 'IN-PLAY', 'BALLPARK', 'DEFENSE', 'WHEELHOUSE')
DRIVER = {'TOUGH': 'so', 'PATIENT': 'bb', 'WHEELHOUSE': 'hr', 'BALLPARK': 'hr'}


def _outs(ip_str):
    ip = float(ip_str)
    return int(ip) * 3 + round((ip - int(ip)) * 10)


def rates_of(card):
    """Per-BF rates off a printed 1986 card's stat line."""
    s = card['stats']
    o = _outs(s['IP'])
    h, bb, so, hr = (float(s[k]) for k in ('H', 'BB', 'SO', 'HR'))
    bf = o + h + bb
    return {'bf': bf, 'h': h / bf, 'bb': bb / bf, 'so': so / bf, 'hr': hr / bf,
            'ip': o / 3.0, 'sp': int(s.get('GS', 0)) >= 10}


def shares_of(table):
    """Dice-weighted share of all rolls per section."""
    sh = defaultdict(float)
    for t, res in table.items():
        base = res.replace('-OUT', '').strip('/')
        sh[base] += D6W[int(t)]
    return {k: sh.get(k, 0.0) for k in SECS}


def decile_table(rows, rate_key, share_key):
    rows = sorted(rows, key=lambda x: x[0][rate_key])
    n = len(rows)
    buckets = []
    for i in range(10):
        chunk = rows[i * n // 10:(i + 1) * n // 10]
        buckets.append({'hi': chunk[-1][0][rate_key],
                        'share': st.median([x[1][share_key] for x in chunk])})
    return buckets


def bucket_share(buckets, v):
    for b in buckets:
        if v <= b['hi']:
            return b['share']
    return buckets[-1]['share']


def smoothed_fit(rows_shares, rate_key, share_key):
    """Decile ladder with each bucket blended toward its neighbors."""
    buckets = decile_table(rows_shares, rate_key, share_key)
    med = [b['share'] for b in buckets]
    out = []
    for i, b in enumerate(buckets):
        if i == 0:
            s = 0.75 * med[0] + 0.25 * med[1]
        elif i == len(med) - 1:
            s = 0.25 * med[-2] + 0.75 * med[-1]
        else:
            s = 0.25 * med[i - 1] + 0.50 * med[i] + 0.25 * med[i + 1]
        out.append({'hi': b['hi'], 'share': s})
    return out


def load_population(path=None):
    """The 424 printed 1986 cards with BF >= 60, as (card, rates)."""
    path = path or os.path.join(HERE, 'pitchers_1986.json')
    pop = []
    for c in json.load(open(path)):
        r = rates_of(c)
        if r['bf'] >= 60:
            pop.append((c, r))
    return pop


class PitcherGrammar:
    """The production fit: smoothed ladders over the whole
    population, role DEFENSE medians, and per-section placement
    habits (totals ranked by how often the real cards put the
    section there)."""

    def __init__(self, pop):
        tsh = [(r, shares_of(c['table'])) for c, r in pop]
        self.fit = {sec: smoothed_fit(tsh, rate, sec)
                    for sec, rate in DRIVER.items()}
        self.def_sp = st.median([s['DEFENSE'] for r, s in tsh if r['sp']])
        self.def_rp = st.median([s['DEFENSE'] for r, s in tsh if not r['sp']])
        self.pref = {}
        for sec in SECS:
            freq = defaultdict(int)
            for c, r in pop:
                for t, res in c['table'].items():
                    if res.replace('-OUT', '').strip('/') == sec:
                        freq[int(t)] += 1
            self.pref[sec] = sorted(range(2, 13),
                                    key=lambda t: (-freq.get(t, 0), t))

    def generate_table(self, rates, is_sp):
        """rates: {'so': .., 'bb': .., 'hr': ..} era-normalized per
        BF. Returns {total-as-string: section} for totals 2-12."""
        target = {sec: bucket_share(self.fit[sec], rates[rate]) * 36
                  for sec, rate in DRIVER.items()}
        target['DEFENSE'] = (self.def_sp if is_sp else self.def_rp) * 36
        used = sum(target.values())
        if used > 34.0:
            target['TOUGH'] = max(4.0, target['TOUGH'] - (used - 34.0))
        table, taken = {}, set()
        for sec in ('WHEELHOUSE', 'BALLPARK', 'DEFENSE', 'PATIENT', 'TOUGH'):
            cur = 0.0
            for t in self.pref[sec]:
                if t in taken:
                    continue
                w = FACE_W[t]
                if abs(cur + w - target[sec]) < abs(cur - target[sec]):
                    table[str(t)] = sec
                    taken.add(t)
                    cur += w
                if cur >= target[sec]:
                    break
        for t in range(2, 13):
            if t not in taken:
                table[str(t)] = 'IN-PLAY'
        return table


def build():
    return PitcherGrammar(load_population())


if __name__ == '__main__':
    g = build()
    jimenez = g.generate_table({'so': 0.1983, 'bb': 0.0999, 'hr': 0.0124}, True)
    expected = {'2': 'DEFENSE', '3': 'IN-PLAY', '4': 'TOUGH', '5': 'TOUGH',
                '6': 'PATIENT', '7': 'TOUGH', '8': 'PATIENT', '9': 'TOUGH',
                '10': 'BALLPARK', '11': 'IN-PLAY', '12': 'DEFENSE'}
    print('Jimenez generated:', dict(sorted(jimenez.items(), key=lambda kv: int(kv[0]))))
    assert jimenez == expected, 'MISMATCH against the workshop anchor table'
    print('ANCHOR OK: reproduces the workshop Jimenez table exactly.')
