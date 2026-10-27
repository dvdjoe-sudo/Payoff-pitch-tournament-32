"""card_version=2 resolution path for the Historical Cards library.

The library has no game engine of its own; this module is the v2
resolution semantics for library pitcher cards, exactly as fitted and
gated in the 2026-10-24 v2 build (see ../V2_PITCHER_REPORT.md).

The one change from v1 semantics — the v2 bump rule:
  On a TOUGH or TOUGH-OUT read, a percentile landing within `bump`
  points above the top of the hitter's printed TOUGH SO range is also
  a strikeout: the band reads [lo, hi + bump]. The percentile itself
  is never shifted. (v1 shifted the percentile up by the bump, which
  pushed reads past hitters' bottom-loaded SO bands and collapsed
  implied strikeout rates.) The conversion set grows monotonically
  with the bump for every hitter.

Environment for implied rates: the pooled Release 1.0 library hitter
cards (184, engine v0.5) enumerated exactly (percentile 1..99 x 2d6).
DEFENSE branch = the frozen v0.2.3 solver's constant vector
(event_vectors.py); BALLPARK = the event-vector construction (50/50
WHEELHOUSE / IN-PLAY mixture) over the pool. No v1 file is read for
writing anywhere; the frozen engines are untouched.
"""
import json, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.expanduser('~/workspace')
HITTER_CARDS_DIR = os.path.join(WS, 'historical-cards', 'output', 'cards')
D6W = {t: (6 - abs(t - 7)) / 36.0 for t in range(2, 13)}
PRIO = ('HR', 'SO', 'BB', 'HBP', '3B', '2B', '1B')
DEFENSE_VECTOR = {'1B': 0.25, '2B': 0.02, '3B': 0.005, 'HR': 0.0,
                  'BB': 0.0, 'HBP': 0.0, 'SO': 0.0, 'OUT': 0.725}

def load_pitchers():
    return json.load(open(os.path.join(HERE, 'pitchers_v2.json')))

def load_hitters():
    import glob
    master = json.load(open(os.path.join(WS, 'historical_cards_master.json')))
    names = [c['player'] for c in master['cards'] if c['engine_version'] == 'v0.5']
    by_name = {}
    for f in glob.glob(os.path.join(HITTER_CARDS_DIR, '*.json')):
        c = json.load(open(f))
        by_name[c['name']] = c
    return [by_name[n] for n in names]

def section_lookup(card, section, hand, pct):
    sec = card['sections'][section][hand]
    for k in PRIO:
        r = sec.get(k)
        if r and r[0] <= pct <= r[1]:
            return k
    return None

def v2_band_pct(card, hand, pct, bump):
    """The v2 bump rule: returns a percentile inside the printed SO
    band when `pct` lands within `bump` points above its top, else
    None. Mirrors pitcher_output_v2/engine_v2.py of the converted sets."""
    so = card['sections']['TOUGH'][hand].get('SO')
    if not so:
        return None
    if so[1] < pct <= so[1] + bump:
        return so[1]
    return None

def bump_of(pcard):
    m = str(pcard.get('so_modifier'))
    return 0 if m in ('None', 'NONE') else int(m.replace('+', ''))

def tough_read(card, hand, pct, bump):
    """Resolve one TOUGH percentile under v2 semantics."""
    if v2_band_pct(card, hand, pct, bump) is not None:
        return 'SO'
    return section_lookup(card, 'TOUGH', hand, pct)

def pair_implied(hcard, pcard):
    """Exact PA outcome distribution of one hitter vs one v2 pitcher."""
    hand = 'vsLHP' if pcard['throws'] == 'L' else 'vsRHP'
    bump = bump_of(pcard)
    def dist(sec, tough_mode=None):
        d = defaultdict(float)
        for pct in range(1, 100):
            if tough_mode == 'v2':
                r = tough_read(hcard, hand, pct, bump)
            elif tough_mode == 'out':
                r0 = tough_read(hcard, hand, pct, bump)
                r = 'SO' if r0 == 'SO' else 'OUT'
            else:
                r = section_lookup(hcard, sec, hand, pct)
            d[r if r else 'OUT'] += 1 / 99.0
        return d
    vec = {'WHEELHOUSE': dist('WHEELHOUSE'), 'PATIENT': dist('PATIENT'),
           'IN-PLAY': dist('IN-PLAY'), 'TOUGH': dist('TOUGH', 'v2'),
           'TOUGH-OUT': dist('TOUGH', 'out')}
    po = defaultdict(float)
    for k, v in vec['PATIENT'].items():
        po[k if k in ('BB', 'HBP') else 'OUT'] += v
    vec['PATIENT-OUT'] = po
    bp = defaultdict(float)
    for k, v in vec['WHEELHOUSE'].items():
        bp[k] += 0.5 * v
    for k, v in vec['IN-PLAY'].items():
        bp[k] += 0.5 * v
    vec['BALLPARK'] = bp
    vec['DEFENSE'] = defaultdict(float, DEFENSE_VECTOR)
    total = defaultdict(float)
    for t, wt in D6W.items():
        for k, v in vec[pcard['card_table_2d6'][str(t)]].items():
            total[k] += wt * v
    return dict(total)

def rates(dist):
    n = sum(dist.values())
    g = lambda k: dist.get(k, 0.0)
    h = g('1B') + g('2B') + g('3B') + g('HR')
    return {'SO%': g('SO') / n, 'BB%': g('BB') / n, 'H%': h / n,
            'HR%': g('HR') / n, 'HBP%': g('HBP') / n}
