#!/usr/bin/env python3
"""Make a Payoff Pitch batter card from a stat line.

Usage: python3 make_card.py player.csv
  player.csv has Joe's standard header + one data row.

Output: ~/workspace/custom-cards/<slug>/<slug>-card.json

Method: section-specific comps from the 596 digitized 1986 cards, then an
analytical coordinate-descent tuner aligns the card's expected AVG/OBP/SLG/
BB%/SO%/HR%/HBP% and the 1B/2B/3B rates with the stat line. Doubles and
triples keep the comp cards' section mix. DEFENSE is the rulebook position
roll against a neutral fielder and the 1986 park charts, not an automatic
out. A reached-on-error is an at-bat and not a hit. No hand tuning.
"""
import csv, json, os, re, sys, copy

HOME = os.path.expanduser('~')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
REF = os.path.join(ROOT, 'historical-cards', 'reference')
APP = os.environ.get('PP_CARDS_1986_DIR', '')
CC = os.environ.get('PP_CUSTOM_CARDS_DIR', HOME + '/workspace/custom-cards')
_REFERENCE = None


def reference():
    """Load the 1986 comp cards and profiles on first use.

    The files live at historical-cards/reference/. PP_CARDS_1986 and
    PP_CARD_PROFILES override the file paths. PP_CARDS_1986_DIR still
    selects a directory whose data/cards_1986.json is the card file.
    Importing this module does not open the files.
    """
    global _REFERENCE
    if _REFERENCE is None:
        cards_path = os.environ.get('PP_CARDS_1986')
        profiles_path = os.environ.get('PP_CARD_PROFILES')
        if not cards_path:
            if APP:
                cards_path = os.path.join(APP, 'data', 'cards_1986.json')
            else:
                cards_path = os.path.join(REF, 'cards_1986.json')
        if not profiles_path:
            profiles_path = os.path.join(REF, 'card_profiles.json')
        cards = json.load(open(cards_path))['players']
        profiles = json.load(open(profiles_path))
        _REFERENCE = {
            'cards': cards,
            'by_name': {p['name']: p for p in cards},
            'profiles': profiles,
        }
    return _REFERENCE

# ---- section model ----
# BALLPARK resolves through the official 1986 park cards (wh/99). DEFO is
# resolved by pa_sim.defense_distribution, not counted as an automatic out.
PITCHER_MIX = {'TOUGH': 0.3429, 'IN-PLAY': 0.2514, 'PATIENT': 0.2287,
               'WHEELHOUSE': 0.0341, 'BALLPARK': 0.0898, 'DEFO': 0.0506}
CANON = {
    'WHEELHOUSE': ['HR', '2B', '3B', '1B'],
    'PATIENT': ['BB', '2B', '3B', '1B', 'HBP'],
    'TOUGH': ['SO', '2B', '3B', '1B'],
    'IN-PLAY': ['2B', '3B', '1B'],
}
ORDER = ('HR', 'SO', 'BB', 'HBP', '3B', '2B', '1B')
# Hits that appear in more than one section. Their face mix is taken from
# the comp cards and held fixed while the tuner changes only the total.
SHAPED = ('1B', '2B', '3B')
MIN_COMP_PA = 300
# Floors keep a near-zero triple rate from vanishing into the 1e-4
# denominator, and from being free when the term is absent.
RATE_FLOOR = {'1bp': 0.02, '2bp': 0.02, '3bp': 0.008}

TEAMS = {
    'Baltimore Orioles': 'BAL', 'Boston Red Sox': 'BOS', 'California Angels': 'CAL',
    'Chicago White Sox': 'CWS', 'Cleveland Indians': 'CLE', 'Detroit Tigers': 'DET',
    'Kansas City Royals': 'KC', 'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN',
    'New York Yankees': 'NYY', 'Oakland Athletics': 'OAK', 'Seattle Mariners': 'SEA',
    'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR',
    'Atlanta Braves': 'ATL', 'Chicago Cubs': 'CHC', 'Cincinnati Reds': 'CIN',
    'Houston Astros': 'HOU', 'Los Angeles Dodgers': 'LAD', 'Montreal Expos': 'MON',
    'New York Mets': 'NYM', 'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT',
    'San Diego Padres': 'SD', 'San Francisco Giants': 'SF', 'St. Louis Cardinals': 'STL',
}

FIELDING_MAP = {  # text -> (range, E)
    'elite': ('A', 1), 'great': ('A', 2), 'excellent': ('A', 2),
    'above average': ('B', 3), 'slightly above average': ('B', 3),
    'average': ('C', 4), 'below average': ('D', 5), 'poor': ('F', 5),
}
ARM_MAP = {'strong': 8, 'above average': 7, 'average': 6,
           'below average': 5, 'weak': 4}


def parse_name(raw):
    m = re.match(r"^(.*?)\s*'([^']+)'\s*(.*)$", raw)
    if m:
        name = (m.group(1) + ' ' + m.group(3)).strip()
        return re.sub(r'\s+', ' ', name), m.group(2)
    m = re.match(r'^(.*?)\s*"([^"]+)"\s*(.*)$', raw)
    if m:
        name = (m.group(1) + ' ' + m.group(3)).strip()
        return re.sub(r'\s+', ' ', name), m.group(2)
    return raw.strip(), None


def _sim():
    """Import the plate-appearance module without opening it at import time."""
    try:
        import pa_sim
    except ImportError:
        sim_dir = os.path.join(ROOT, 'engines', 'sim')
        if sim_dir not in sys.path:
            sys.path.insert(0, sim_dir)
        import pa_sim
    return pa_sim


def section_probs(bats):
    """Four section probabilities plus DEFO.

    BALLPARK is folded into WHEELHOUSE and IN-PLAY with the 1986 park
    cards. DEFO stays in the dict so a caller can see it. prescale reads
    only the four sections. expected() pops DEFO and resolves it.
    """
    p = dict(PITCHER_MIX)
    bp = p.pop('BALLPARK')
    wh = _sim().ballpark_wheel_share(bats)
    p['WHEELHOUSE'] += bp * wh
    p['IN-PLAY'] += bp * (1 - wh)
    return p


def width(tbl, key):
    r = tbl.get(key)
    return (r[1] - r[0] + 1) if r else 0


def comp_distance(p, t):
    return (((p['avg']-t['avg'])*3)**2 + ((p['obp']-t['obp'])*3)**2 +
            ((p['slg']-t['slg'])*2)**2 + ((p['bbp']-t['bbp'])*4)**2 +
            ((p['sop']-t['sop'])*3)**2 + ((p['hrp']-t['hrp'])*8)**2)


def plate_appearances(card):
    """AB+BB across the two pitcher hands. The 1986 card does not print HBP."""
    total = 0
    for side in ('L', 'R'):
        stats = (card.get('stats_split') or {}).get(side) or {}
        total += int(stats.get('AB') or 0) + int(stats.get('BB') or 0)
    return total


def select_comps(tgt, n=8, exclude=None):
    """Section comps. exclude is a set of profile names left out of the pool.

    A held-out accuracy check passes the player's own card here so the
    rebuild cannot copy that card.

    Comps need a real sample. The eight highest home-run rates in the
    1986 set are mostly cups of coffee, and their wheelhouses are not a
    usable shape. Wheel comps are qualified cards with a similar home-run
    rate. Patient comps are qualified cards with a similar walk rate.
    """
    profiles = reference()['profiles']
    by_name = reference()['by_name']
    if exclude:
        skip = set(exclude)
        profiles = [p for p in profiles if p['name'] not in skip]
    qualified = [p for p in profiles
                 if plate_appearances(by_name.get(p['name']) or {}) >= MIN_COMP_PA]
    pool = qualified if len(qualified) >= n else profiles

    def closest(key):
        return [p['name'] for p in sorted(pool, key=key)[:n]]

    wh = closest(lambda p: (abs(p['hrp'] - tgt['hrp']), comp_distance(p, tgt)))
    pat = closest(lambda p: (abs(p['bbp'] - tgt['bbp']), comp_distance(p, tgt)))
    contact = closest(lambda p: (comp_distance(p, tgt),))
    return {'WHEELHOUSE': wh, 'PATIENT': pat,
            'TOUGH': contact, 'IN-PLAY': contact}


def build_initial(comps):
    by_name = reference()['by_name']
    widths = {}
    for sec, keys in CANON.items():
        cards = [by_name[n] for n in comps[sec]]
        for hand in ('vsLHP', 'vsRHP'):
            for k in keys:
                # v0.5 fix: skip cards missing this section/hand
                vals = []
                for c in cards:
                    try:
                        vals.append(width(c['sections'][sec][hand], k))
                    except KeyError:
                        continue
                widths[(sec, hand, k)] = round(sum(vals) / len(vals)) if vals else 0
    return widths


def shape_shares(widths):
    """Fraction of each shaped outcome's faces sitting in each section and hand."""
    shares = {}
    for outcome in SHAPED:
        cells = [key for key in widths if key[2] == outcome]
        total = sum(max(0, widths[key]) for key in cells)
        for key in cells:
            shares[key] = (max(0, widths[key]) / total) if total else 0.0
    return shares


def project_shaped(widths, shares):
    """Put 1B, 2B, and 3B back on the comp face mix.

    The total of each outcome is kept. Which section holds those faces is
    not. A restart that dumps 15 triples into one hand is pulled back onto
    the sections where the comp cards actually printed that outcome.
    """
    if not shares:
        return dict(widths)
    projected = dict(widths)
    for outcome in SHAPED:
        cells = [key for key in shares if key[2] == outcome]
        if not cells:
            continue
        total = sum(max(0, projected.get(key, 0)) for key in cells)
        if sum(shares[key] for key in cells) <= 0:
            for key in cells:
                projected[key] = 0
            continue
        raw = {key: total * shares[key] for key in cells}
        assigned = {key: int(raw[key]) for key in cells}
        leftover = int(round(total)) - sum(assigned.values())
        order = sorted(cells, key=lambda key: (raw[key] - assigned[key], shares[key]),
                       reverse=True)
        index = 0
        while leftover > 0 and order:
            assigned[order[index % len(order)]] += 1
            leftover -= 1
            index += 1
        for key in cells:
            projected[key] = assigned[key]
    return projected


def _with_fallback_share(shares, outcome, target_rate):
    """If every comp printed none of an outcome the player actually had,
    allow it on IN-PLAY. The book does not name a section for that case.
    """
    cells = [key for key in shares if key[2] == outcome]
    if target_rate < 0.004 or sum(shares[key] for key in cells) > 0:
        return shares
    for hand in ('vsLHP', 'vsRHP'):
        key = ('IN-PLAY', hand, outcome)
        if key in shares:
            shares[key] = 0.5
    return shares


def prescale(widths, tgt, bats):
    """Set absolute widths directly from target rates.

    BB/HBP/SO/HR live in exactly one section each, so their widths are
    solved directly. Hits are distributed across sections proportionally
    to the comp-implied widths, with the 2B:3B ratio taken from comps and
    1B solved from AVG/SLG. This replaces hand-tuned scale factors.
    """
    p = section_probs(bats)
    W = dict(widths)

    def avg_width(sec, key):
        return (W[(sec, 'vsLHP', key)] + W[(sec, 'vsRHP', key)]) / 2

    def set_width(sec, key, target_avg):
        cur = avg_width(sec, key)
        if cur > 0:
            f = target_avg / cur
            for h in ('vsLHP', 'vsRHP'):
                W[(sec, h, key)] = max(0, round(W[(sec, h, key)] * f))

    # single-section keys: solve directly
    set_width('PATIENT', 'BB', tgt['bbp'] / p['PATIENT'] * 99)
    set_width('PATIENT', 'HBP', tgt['hbpp'] / p['PATIENT'] * 99)
    set_width('TOUGH', 'SO', tgt['sop'] / p['TOUGH'] * 99)
    set_width('WHEELHOUSE', 'HR', tgt['hrp'] / p['WHEELHOUSE'] * 99)

    # hits: solve per-PA totals from AVG/SLG, keep comp 2B:3B ratio
    p_ab = 1 - tgt['bbp'] - tgt['hbpp']          # P(AB) per PA
    h_pa = tgt['avg'] * p_ab
    iso_pa = (tgt['slg'] - tgt['avg']) * p_ab    # 2B + 2*3B + 3*HR per PA
    r = 0.0
    d2 = sum(W[('WHEELHOUSE', h, '2B')] + W[('PATIENT', h, '2B')] +
             W[('TOUGH', h, '2B')] + W[('IN-PLAY', h, '2B')]
             for h in ('vsLHP', 'vsRHP'))
    d3 = sum(W[('WHEELHOUSE', h, '3B')] + W[('PATIENT', h, '3B')] +
             W[('TOUGH', h, '3B')] + W[('IN-PLAY', h, '3B')]
             for h in ('vsLHP', 'vsRHP'))
    if d2 > 0:
        r = d3 / d2
    xbh2 = (iso_pa - 3 * tgt['hrp']) / (1 + 2 * r)   # 2B per PA
    xbh2 = max(0.002, xbh2)
    t3 = max(0.0, xbh2 * r)                           # 3B per PA
    s1 = max(0.005, h_pa - xbh2 - t3 - tgt['hrp'])     # 1B per PA
    for key, need_pa in (('2B', xbh2), ('3B', t3), ('1B', s1)):
        # distribute across sections proportional to comp widths
        tot = 0.0
        contrib = {}
        for sec in CANON:
            if key not in CANON[sec]:
                continue
            for h in ('vsLHP', 'vsRHP'):
                c = W[(sec, h, key)] / 99 * p[sec] * (0.28 if h == 'vsLHP' else 0.72)
                contrib[(sec, h)] = c
                tot += c
        if tot > 0:
            for (sec, h), c in contrib.items():
                W[(sec, h, key)] = max(0, round(need_pa * (c / tot) / p[sec] /
                                                (0.28 if h == 'vsLHP' else 0.72) * 99))
    return W


def hole_faces(table):
    """Faces 1-99 that no result band claims. Inverted and out-of-range
    bands claim nothing; repack drops them before this runs."""
    claimed = set()
    for key in ('HR', '3B', '2B', '1B', 'BB', 'HBP', 'SO'):
        rng = (table or {}).get(key)
        if not rng:
            continue
        lo, hi = int(rng[0]), int(rng[1])
        if lo > hi or lo < 1 or hi > 99:
            continue
        claimed.update(range(lo, hi + 1))
    return [face for face in range(1, 100) if face not in claimed]


def _label_for_face(face, template):
    for row in template or []:
        rng = row.get('range')
        if not rng or len(rng) < 2:
            continue
        lo, hi = int(rng[0]), int(rng[1])
        if lo <= face <= hi:
            return row.get('result') or 'P4'
    # Uncertain which out type a hole should print when the comp chart
    # does not cover that face. P4 is the fallback the repaired cards
    # already use for an uncovered out.
    return 'P4'


def rows_from_faces(faces, template):
    """Merge consecutive hole faces that share a label."""
    rows = []
    for face in faces:
        label = _label_for_face(face, template)
        if rows and rows[-1]['result'] == label and rows[-1]['range'][1] == face - 1:
            rows[-1]['range'][1] = face
        else:
            rows.append({'range': [face, face], 'result': label})
    return rows


def widths_from_sections(sections):
    widths = {}
    for sec, keys in CANON.items():
        for hand in ('vsLHP', 'vsRHP'):
            table = (sections.get(sec) or {}).get(hand) or {}
            for key in keys:
                rng = table.get(key)
                if rng and int(rng[0]) <= int(rng[1]):
                    widths[(sec, hand, key)] = int(rng[1]) - int(rng[0]) + 1
                else:
                    widths[(sec, hand, key)] = 0
    return widths


def repack_sections(sections):
    """Pack every hand from face 1 using the current band widths.

    A neighborhood edit that moves one endpoint can overlap the next
    band or run past 99. Widths are kept; lay_out places them in
    canonical order and clips the hand at 99.
    """
    return lay_out(widths_from_sections(sections))


def out_tables_from_holes(sections, template):
    """Build an out table from the faces each hand did not claim.

    Hands on one card do not share a hole set, so one shared table
    cannot equal every hand's holes. out_by_hand is the strict table
    for each hand. The shared out_table covers the union. A face that
    is a result on one hand and a hole on another remains in the
    shared table. Uncertain: that printed overlap is what the
    resolved reading ignores, giving the result band the face.
    """
    per = {}
    union = set()
    for sec in CANON:
        per[sec] = {}
        for hand in ('vsLHP', 'vsRHP'):
            holes = hole_faces(sections[sec][hand])
            per[sec][hand] = rows_from_faces(holes, template)
            union.update(holes)
    return per, rows_from_faces(sorted(union), template)


def lay_out(widths):
    sections = {}
    for sec, keys in CANON.items():
        for hand in ('vsLHP', 'vsRHP'):
            lo, table = 1, {}
            for k in keys:
                wd = max(0, widths[(sec, hand, k)])
                if wd > 0 and lo <= 99:
                    hi = min(lo + wd - 1, 99)
                    table[k] = [lo, hi]
                    lo = hi + 1
                else:
                    table[k] = None
            sections.setdefault(sec, {})[hand] = table
    return sections


def expected(sections, bats, run=None):
    """Completed-PA rates. run >= 8 turns a dagger double into a triple.

    DEFENSE uses a neutral Range C, Error 3 fielder and the 1986 parks.
    A reached-on-error adds an at-bat and not a hit. A dropped foul is
    removed from the denominator. Section and BALLPARK face 00 stay rare
    and are already outside this /99 model. A defense park-00 is an out
    inside the plate appearance.
    """
    p_sec = section_probs(bats)
    defo = p_sec.pop('DEFO', 0.0)
    ph = {'vsLHP': 0.28, 'vsRHP': 0.72}
    acc = {k: 0.0 for k in ('BB', 'HBP', 'SO', 'HR', '3B', '2B', '1B', 'AB')}
    for sec, ps in p_sec.items():
        for hand, h in ph.items():
            tbl = sections[sec][hand]
            w = {k: ((tbl[k][1]-tbl[k][0]+1)/99) if tbl.get(k) else 0.0
                 for k in ('BB', 'HBP', 'SO', 'HR', '3B', '2B', '1B')}
            f = ps * h
            for k in w:
                acc[k] += f * w[k]
            acc['AB'] += f * (w['SO']+w['HR']+w['3B']+w['2B']+w['1B'])
            acc['AB'] += f * max(0.0, 1 - sum(w.values()))
    dist = _sim().defense_distribution()
    side = dist['high'] if run is not None and run >= 8 else dist['low']
    p_reroll = defo * side.get('REROLL', 0.0)
    for event, share in side.items():
        if event == 'REROLL':
            continue
        mass = defo * share
        if event in ('OUT', 'ROE'):
            acc['AB'] += mass
        elif event in acc:
            acc[event] += mass
            acc['AB'] += mass
    scale = 1.0 / (1.0 - p_reroll) if p_reroll < 1.0 else 1.0
    for key in acc:
        acc[key] *= scale
    h = acc['HR']+acc['3B']+acc['2B']+acc['1B']
    pa = acc['AB']+acc['BB']+acc['HBP']
    return {'avg': h/acc['AB'], 'obp': (h+acc['BB']+acc['HBP'])/pa,
            'slg': (h+acc['2B']+2*acc['3B']+3*acc['HR'])/acc['AB'],
            'bbp': acc['BB']/pa, 'sop': acc['SO']/pa, 'hrp': acc['HR']/pa,
            'hbpp': acc['HBP']/pa,
            '1bp': acc['1B']/pa, '2bp': acc['2B']/pa, '3bp': acc['3B']/pa}


def event_targets(row):
    """Target event rates (per PA) from a CSV row. IBB excluded from BB."""
    g = lambda k: float(row[k] or 0)
    h, bb, ibb = g('H'), g('BB'), g('IBB')
    pa = g('PA') - ibb  # the card has no IBB plate appearance
    ubb = bb - ibb
    d2, d3, hr = g('2B'), g('3B'), g('HR')
    s1 = h - d2 - d3 - hr
    return {'1bp': s1/pa, '2bp': d2/pa, '3bp': d3/pa, 'hrp': hr/pa,
            'bbp': ubb/pa, 'hbpp': g('HBP')/pa, 'sop': g('SO')/pa}


def diagnose(exp, tgt_events, tgt_slash):
    """v0.2 event-level diagnostic. Returns (report_lines, primary_issue)."""
    lines = []
    lines.append("TARGET      GENERATED      DELTA")
    for lbl, k in [('AVG', 'avg'), ('OBP', 'obp'), ('SLG', 'slg')]:
        d = exp[k] - tgt_slash[k]
        lines.append(f"{lbl} {tgt_slash[k]:.3f}    {exp[k]:.3f}           "
                     f"{d:+.3f}")
    lines.append("")
    ev = [('1B', '1bp'), ('2B', '2bp'), ('3B', '3bp'), ('HR', 'hrp'),
          ('BB', 'bbp'), ('HBP', 'hbpp'), ('SO', 'sop')]
    max_drift, primary = 0, None
    for lbl, k in ev:
        t = tgt_events[k]
        e = exp[k]
        d = (e - t) * 100  # percentage points
        lines.append(f"{lbl:3s} {t*100:6.2f}%  {e*100:6.2f}%         "
                     f"{d:+.2f}pp")
        if abs(d) > max_drift:
            max_drift, primary = abs(d), lbl
    issue = f"{primary} drift ({max_drift:.2f}pp)" if primary else "none"
    return lines, issue


def err(exp, tgt):
    total = 0.0
    for key, target in tgt.items():
        if key not in exp:
            continue
        floor = RATE_FLOOR.get(key, 1e-4)
        total += ((exp[key] - target) / max(abs(target), floor)) ** 2
    return total


def irreducible_error(build_fn, tgt, bats, restarts=3, run=None):
    """Best error from independent tuner restarts.

    build_fn(seed=) owns its own RNG. The returned error is a probe,
    not a copy of the card already chosen. classify_review uses the
    gap between the shipped card and this probe.
    """
    best_err, best_secs = float('inf'), None
    for i in range(restarts):
        _widths, secs = build_fn(seed=i)
        e = err(expected(secs, bats, run), tgt)
        if e < best_err:
            best_err, best_secs = e, secs
    return best_err, best_secs


def classify_review(fit_ok, actual_err, best_err):
    """Two-tier review: SOLVER vs ARCHITECTURE-LIMITED.

    A shipped card that matches the probe and still misses tolerance
    is architecture-limited. A shipped card at least 50% worse than
    the probe is a solver miss. Tiny absolute errors stay
    architecture-limited even when the ratio is large. A missing
    probe is a solver review, not a silent pass.
    """
    if fit_ok:
        return 'PASS', 'within tolerance'
    if best_err is None:
        return 'SOLVER-REVIEW', (
            'No independent probe of the best legal card. '
            'Manual inspection recommended.')
    if actual_err + 1e-12 < best_err:
        best_err = actual_err
    if best_err < 0.003 and actual_err < 0.005:
        return 'ARCHITECTURE-LIMITED', (
            'Format cannot simultaneously reproduce all target event rates. '
            'Solver found the best legal card.')
    if best_err > 0:
        gap = (actual_err - best_err) / best_err
    else:
        gap = actual_err - best_err
    if gap >= 0.50:
        return 'SOLVER-REVIEW', (
            'Optimizer may not have found the best legal card. '
            'Manual inspection recommended.')
    return 'ARCHITECTURE-LIMITED', (
        'Format cannot simultaneously reproduce all target event rates. '
        'Solver found the best legal card.')


TUNE_CELLS = [
    [('PATIENT', 'BB')], [('WHEELHOUSE', 'HR')],
    [('IN-PLAY', '1B')], [('IN-PLAY', '2B')], [('IN-PLAY', '3B')],
    [('TOUGH', '1B')], [('TOUGH', '2B')], [('TOUGH', '3B')], [('TOUGH', 'SO')],
    [('PATIENT', '1B')], [('PATIENT', '2B')], [('PATIENT', '3B')], [('PATIENT', 'HBP')],
    [('WHEELHOUSE', '1B')], [('WHEELHOUSE', '2B')], [('WHEELHOUSE', '3B')],
]


def tune(widths, tgt, bats, shares=None, run=None):
    W = project_shaped(widths, shares) if shares else dict(widths)
    best = err(expected(lay_out(W), bats, run), tgt)
    step = 8
    while step >= 1:
        improved = True
        while improved:
            improved = False
            for cell in TUNE_CELLS:
                keys = [(s, h, k) for (s, k) in cell
                        for h in ('vsLHP', 'vsRHP')]
                for delta in (-step, step):
                    W2 = dict(W)
                    for key in keys:
                        W2[key] = max(0, W2.get(key, 0) + delta)
                    if shares:
                        W2 = project_shaped(W2, shares)
                    e = err(expected(lay_out(W2), bats, run), tgt)
                    if e < best - 1e-10:
                        best, W, improved = e, W2, True
                        break
        step //= 2
    return lay_out(W), best


def ratings(row):
    pos = row['Position'].strip().upper()
    frange, fe = FIELDING_MAP.get(row['Fielding'].strip().lower(), ('C', 4))
    arm = ARM_MAP.get(row['Arm'].strip().lower(), 6)
    sb, cs = int(row['SB'] or 0), int(row['CS'] or 0)
    if sb == 0:
        steal = {'jump': None, 'jump_mod': None, 'rating': 'F'}
    else:
        rate = sb / (sb + cs) if (sb + cs) else 0
        jump = 2 if sb <= 5 else 3 if sb <= 15 else 4 if sb <= 30 else 5
        rating = 'B' if rate >= 0.85 else 'C' if rate >= 0.75 else 'D' if rate >= 0.65 else 'F'
        steal = {'jump': jump, 'jump_mod': None, 'rating': rating}
    run = max(1, min(10, 5 + int(row['3B'] or 0)//3 + sb//20))
    return {'positions': [{'pos': pos, 'range': frange, 'e': fe, 'arm': arm}],
            'dp': 7, 'steal': steal, 'run': run, 'sac_bunt': 'F'}


def fit_report(exp, tgt):
    """Per-stat errors and PASS/REVIEW based on absolute tolerances."""
    # (label, exp_key, scale_to_points, tolerance_in_points)
    specs = [('avg', 'avg', 1000, 3), ('obp', 'obp', 1000, 5),
             ('slg', 'slg', 1000, 8), ('bbp', 'bbp', 100, 0.3),
             ('sop', 'sop', 100, 0.3), ('hrp', 'hrp', 100, 0.15),
             ('hbpp', 'hbpp', 100, 0.15)]
    errs, ok = {}, True
    for label, k, scale, tol in specs:
        e = (exp[k] - tgt[k]) * scale
        errs[label] = e
        if abs(e) > tol:
            ok = False
    # fit %: 100 = perfect, 90 = at tolerance edge, lower = worse
    worst = max(abs(errs[l]) / tol for l, _, _, tol in specs)
    fit = max(0, min(100, 100 - 10 * worst))
    status = 'PASS' if ok else 'REVIEW'
    lines = [f"  {l} error: {errs[l]:+.2f}" for l, _, _, _ in specs]
    return lines, fit, status


def build_one(row, exclude=None, run=None):
    """Build a card from a CSV row. Returns (card, exp, tgt, best_comp).

    exclude keeps those profile names out of the comp pool and out of
    the out-table template pick.
    """
    if row['Position'].strip().upper() == 'P':
        return None
    name, nickname = parse_name(row['Name'])
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    g = lambda k: float(row[k] or 0)
    h, bb, ibb, hbp = g('H'), g('BB'), g('IBB'), g('HBP')
    ubb = bb - ibb  # unintentional walks only; IBB is a gameplay decision
    # The card has no IBB plate appearance, so rates are per PA without
    # IBB. Dividing by full PA turned each IBB into an out (Bonds -.045 AVG).
    pa, ab = g('PA') - ibb, g('AB')
    so, hr = g('SO'), g('HR')
    doubles, triples = g('2B'), g('3B')
    tb = h + doubles + 2*triples + 3*hr
    singles = h - doubles - triples - hr
    tgt = {'avg': h/ab, 'obp': (h+ubb+hbp)/pa, 'slg': tb/ab,
           'bbp': ubb/pa, 'sop': so/pa, 'hrp': hr/pa, 'hbpp': hbp/pa,
           '1bp': singles/pa, '2bp': doubles/pa, '3bp': triples/pa}
    bats = row['Bats'].strip().upper()[0]
    if run is None:
        run = ratings(row)['run']
    comps = select_comps(tgt, exclude=exclude)
    # v0.4: multi-start optimization (10 restarts). Each restart has its
    # own Random so the process-wide RNG is left alone and a rerun with
    # the same seeds reproduces the starts.
    import random
    raw_widths = build_initial(comps)
    shares = shape_shares(raw_widths)
    _with_fallback_share(shares, '2B', tgt['2bp'])
    _with_fallback_share(shares, '3B', tgt['3bp'])
    base_widths = prescale(raw_widths, tgt, bats)

    def jitter(seed):
        rng = random.Random(seed)
        out = {}
        for key, value in base_widths.items():
            # Shaped outcomes stay on the comp mix. Jittering them by 15
            # faces is what parked a triple band where the comps had none,
            # and the old tuner had no 3B cell with which to remove it.
            if key[2] in SHAPED:
                out[key] = value
            else:
                out[key] = max(0, value + rng.randint(-15, 15))
        return out

    starts = []
    starts.append(('heuristic', dict(base_widths)))
    # rate-derived: scale widths by target event rates, then restore the mix
    rd = project_shaped({k: max(0, int(v * 0.9)) for k, v in base_widths.items()},
                        shares)
    starts.append(('rate-derived', rd))
    # 8 randomized legal seeds
    for i in range(8):
        starts.append((f'random-{i}', jitter(1000 + i)))
    best_err, best_secs, best_idx, init_err = float('inf'), None, -1, None
    for idx, (label, w0) in enumerate(starts):
        secs, e = tune(dict(w0), tgt, bats, shares, run)
        if idx == 0:
            init_err = e
        if e < best_err:
            best_err, best_secs, best_idx = e, secs, idx
    # Neighborhood search changes one width, then repacks the hand from
    # face 1. Shaped outcomes are projected back onto the comp mix before
    # the hand is scored, so a one-face edit cannot move triples into a
    # section the comps left empty.
    improved = True
    while improved:
        improved = False
        cur_widths = widths_from_sections(best_secs)
        for key, w in list(cur_widths.items()):
            if w <= 0 and key[2] not in SHAPED:
                continue
            for delta in (-2, -1, 1, 2):
                nw = max(0, w + delta)
                if nw == w:
                    continue
                w2 = dict(cur_widths)
                w2[key] = nw
                w2 = project_shaped(w2, shares)
                if w2 == cur_widths:
                    continue
                s2 = lay_out(w2)
                e2 = err(expected(s2, bats, run), tgt)
                if e2 < best_err - 1e-10:
                    best_err, best_secs, improved = e2, s2, True
                    break
            if improved:
                break
    sections = repack_sections(best_secs)
    search_err = err(expected(sections, bats, run), tgt)

    def probe(seed=0):
        rw = jitter(2000 + seed)
        secs, _e = tune(dict(rw), tgt, bats, shares)
        return rw, repack_sections(secs)

    probe_err, probe_secs = irreducible_error(probe, tgt, bats, restarts=3, run=run)
    if probe_secs is not None and probe_err < search_err:
        sections = probe_secs
        best_err = probe_err
    else:
        best_err = search_err
    exp = expected(sections, bats, run)
    actual_err = err(exp, tgt)
    # v0.4 diagnostics
    init_label = starts[0][0]
    best_label = starts[best_idx][0]
    improvement = ((init_err - best_err) / init_err * 100) if init_err > 0 else 0
    opt_status = 'UNSTABLE INITIALIZATION' if improvement > 50 else 'STABLE'
    r = ratings(row)
    ref = reference()
    pool = ref['profiles']
    if exclude:
        skip = set(exclude)
        pool = [p for p in pool if p['name'] not in skip]
    best_comp = min(pool, key=lambda p: comp_distance(p, tgt))['name']
    template = (ref['by_name'].get(best_comp) or {}).get('out_table') or []
    out_by_hand, out_table = out_tables_from_holes(sections, template)
    # v0.5: audit trail
    import datetime
    audit = {
        'solver_version': '0.7',
        'built_utc': datetime.datetime.utcnow().isoformat() + 'Z',
        'input_row': {k: row[k] for k in row},
        'ibb_treatment': f"BB={g('BB'):.0f} IBB={g('IBB'):.0f} "
                         f"uBB={ubb:.0f} target_bbp={tgt['bbp']:.4f}",
        'winning_seed': best_label,
        'restart_index': best_idx,
        'objective_score': round(actual_err, 6),
        'best_possible_score': round(min(search_err, probe_err), 6),
        'neighborhood_search': 'exhaustive ±1,±2 then repack',
        'optimizer_status': opt_status,
    }
    card = {
        'name': name, 'nickname': nickname,
        'team': TEAMS.get(row['Team'].strip(), row['Team'].strip()),
        'bats': bats, 'throws': row['Throws'].strip().upper()[0] or None,
        'fictional': True,
        'based_on': 'Auto build (make_card.py): section comps + analytical tune',
        'stat_line': {k: row[k] for k in row},
        'positions': r['positions'], 'sections': sections,
        'out_table': out_table,
        'out_by_hand': out_by_hand,
        'dp': r['dp'], 'steal': r['steal'], 'run': r['run'],
        'sac_bunt': r['sac_bunt'], 'pitcher': None,
        'audit': audit,
    }
    return card, exp, tgt, best_comp, slug, actual_err, best_err, {
        'init_err': init_err, 'best_idx': best_idx, 'best_label': best_label,
        'improvement': improvement, 'opt_status': opt_status,
    }


def main(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    results = []
    for row in rows:
        built = build_one(row)
        if built is None:
            print(f"SKIP {row['Name']} (pitchers not supported yet)")
            continue
        card, exp, tgt, best_comp, slug, actual_err, best_err, diag = built
        outdir = os.path.join(CC, slug)
        os.makedirs(outdir, exist_ok=True)
        out = os.path.join(outdir, slug + '-card.json')
        json.dump(card, open(out, 'w'), indent=1)
        lines, fit, old_status = fit_report(exp, tgt)
        # Two-tier review: SOLVER vs ARCHITECTURE-LIMITED
        fit_ok = (old_status == 'PASS')
        status, reason = classify_review(fit_ok, actual_err, best_err)
        print(f"\n{card['name'].upper()}")
        # v0.2 event-level diagnostic
        ev_tgt = event_targets(row)
        dlines, issue = diagnose(exp, ev_tgt, tgt)
        print('\n'.join(dlines))
        print(f"\nQA STATUS: {status}")
        if status != 'PASS':
            print(f"Reason: {reason}")
        print(f"Primary issue: {issue}")
        print(f"Fit error: {actual_err:.4f}  Best possible: {best_err:.4f}")
        # v0.4 optimizer diagnostics
        print(f"Initial fit error: {diag['init_err']:.4f}")
        print(f"Best restart: {diag['best_label']} "
              f"({diag['best_idx']+1} of 10)")
        print(f"Improvement: {diag['improvement']:.1f}%")
        print(f"Optimizer status: {diag['opt_status']}")
        print(f"Manual review: {'RECOMMENDED' if status != 'PASS' else 'not needed'}")
        results.append({'name': card['name'], 'fit': round(fit, 1),
                        'status': status, 'primary_issue': issue,
                        'fit_error': round(actual_err, 4),
                        'best_possible': round(best_err, 4),
                        'opt_status': diag['opt_status'],
                        'improvement': round(diag['improvement'], 1),
                        'file': out})
    # validation CSV
    if results:
        with open(os.path.join(CC, 'validation_results.csv'), 'w',
                  newline='') as f:
            w = csv.DictWriter(
                f, fieldnames=['name', 'fit', 'status', 'primary_issue',
                               'fit_error', 'best_possible', 'opt_status',
                               'improvement', 'file'])
            w.writeheader()
            w.writerows(results)
        print(f"\n{len(results)} cards, validation_results.csv written")


if __name__ == '__main__':
    main(sys.argv[1])
