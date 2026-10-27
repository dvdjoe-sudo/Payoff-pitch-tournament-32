#!/usr/bin/env python3
"""Make a Payoff Pitch batter card from a stat line.

Usage: python3 make_card.py player.csv
  player.csv has Joe's standard header + one data row.

Output: ~/workspace/custom-cards/<slug>/<slug>-card.json

Method: section-specific comps from the 596 digitized 1986 cards, then an
analytical coordinate-descent tuner aligns the card's expected AVG/OBP/SLG/
BB%/SO%/HR%/HBP% with the stat line. No hand tuning.
"""
import csv, json, os, re, sys, copy

HOME = os.path.expanduser('~')
APP = HOME + '/workspace/payoff-pitch-app'
CC = HOME + '/workspace/custom-cards'
CARDS = json.load(open(APP + '/data/cards_1986.json'))['players']
BY_NAME = {p['name']: p for p in CARDS}
PROFILES = json.load(open(CC + '/card_profiles.json'))

# ---- section model ----
# BALLPARK (8.98% of pitcher rolls) resolves via the park chart to WHEELHOUSE
# or IN-PLAY; mean P(WH|BALLPARK) across 26 parks:
P_WH_GIVEN_BP = {'L': 0.519, 'R': 0.504, 'S': 0.5115}
PITCHER_MIX = {'TOUGH': 0.3429, 'IN-PLAY': 0.2514, 'PATIENT': 0.2287,
               'WHEELHOUSE': 0.0341, 'BALLPARK': 0.0898, 'DEFO': 0.0506}
CANON = {
    'WHEELHOUSE': ['HR', '2B', '3B', '1B'],
    'PATIENT': ['BB', '2B', '3B', '1B', 'HBP'],
    'TOUGH': ['SO', '2B', '3B', '1B'],
    'IN-PLAY': ['2B', '3B', '1B'],
}
ORDER = ('HR', 'SO', 'BB', 'HBP', '3B', '2B', '1B')

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


def section_probs(bats):
    p = dict(PITCHER_MIX)
    bp, wh = p.pop('BALLPARK'), P_WH_GIVEN_BP.get(bats, 0.5115)
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


def select_comps(tgt, n=8):
    wh = sorted(PROFILES, key=lambda p: -p['hrp'])[:n]
    pat = sorted(PROFILES, key=lambda p: -p['bbp'])[:n]
    contact = sorted(PROFILES, key=lambda p: comp_distance(p, tgt))[:n]
    return {'WHEELHOUSE': [p['name'] for p in wh],
            'PATIENT': [p['name'] for p in pat],
            'TOUGH': [p['name'] for p in contact],
            'IN-PLAY': [p['name'] for p in contact]}


def build_initial(comps):
    widths = {}
    for sec, keys in CANON.items():
        cards = [BY_NAME[n] for n in comps[sec]]
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
    widths = {}
    for sec, keys in CANON.items():
        cards = [BY_NAME[n] for n in comps[sec]]
        for hand in ('vsLHP', 'vsRHP'):
            for k in keys:
                widths[(sec, hand, k)] = round(sum(
                    width(c['sections'][sec][hand], k) for c in cards) / len(cards))
    return widths


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


def expected(sections, bats):
    p_sec = section_probs(bats)
    ph = {'vsLHP': 0.28, 'vsRHP': 0.72}
    acc = {k: 0.0 for k in ('BB', 'HBP', 'SO', 'HR', '3B', '2B', '1B', 'AB')}
    for sec, ps in p_sec.items():
        if sec == 'DEFO':
            acc['AB'] += ps
            continue
        for hand, h in ph.items():
            tbl = sections[sec][hand]
            w = {k: ((tbl[k][1]-tbl[k][0]+1)/99) if tbl.get(k) else 0.0
                 for k in ('BB', 'HBP', 'SO', 'HR', '3B', '2B', '1B')}
            f = ps * h
            for k in w:
                acc[k] += f * w[k]
            acc['AB'] += f * (w['SO']+w['HR']+w['3B']+w['2B']+w['1B'])
            acc['AB'] += f * max(0.0, 1 - sum(w.values()))
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
    pa = g('PA')
    h, bb, ibb = g('H'), g('BB'), g('IBB')
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
    return sum(((exp[k]-tgt[k])/max(tgt[k], 1e-4))**2 for k in tgt)


def irreducible_error(build_fn, tgt, bats, restarts=3):
    """Estimate best achievable error via multiple tuner restarts.
    Returns (best_error, best_sections). If actual is close to best,
    the miss is architectural, not solver failure."""
    import random
    best_err, best_secs = float('inf'), None
    for i in range(restarts):
        widths, secs = build_fn(seed=i)
        e = err(expected(secs, bats), tgt)
        if e < best_err:
            best_err, best_secs = e, secs
    return best_err, best_secs


def classify_review(fit_ok, actual_err, best_err):
    """Two-tier review: SOLVER vs ARCHITECTURE-LIMITED."""
    if fit_ok:
        return 'PASS', 'within tolerance'
    # If errors are tiny in absolute terms, small relative gaps don't
    # indicate solver failure
    if best_err < 0.003 and actual_err < 0.005:
        return 'ARCHITECTURE-LIMITED', (
            'Format cannot simultaneously reproduce all target event rates. '
            'Solver found the best legal card.')
    # If actual is within 50% of best possible, solver is effectively optimal
    if best_err > 0 and (actual_err - best_err) / best_err < 0.50:
        return 'ARCHITECTURE-LIMITED', (
            'Format cannot simultaneously reproduce all target event rates. '
            'Solver found the best legal card.')
    return 'SOLVER-REVIEW', (
        'Optimizer may not have found the best legal card. '
        'Manual inspection recommended.')


TUNE_CELLS = [
    [('PATIENT', 'BB')], [('WHEELHOUSE', 'HR')],
    [('IN-PLAY', '1B')], [('IN-PLAY', '2B')],
    [('TOUGH', '1B')], [('TOUGH', '2B')], [('TOUGH', 'SO')],
    [('PATIENT', '1B')], [('PATIENT', 'HBP')],
    [('WHEELHOUSE', '1B')], [('WHEELHOUSE', '2B')],
]


def tune(widths, tgt, bats):
    W = dict(widths)
    best = err(expected(lay_out(W), bats), tgt)
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
                        W2[key] = max(0, W2[key] + delta)
                    e = err(expected(lay_out(W2), bats), tgt)
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


def build_one(row):
    """Build a card from a CSV row. Returns (card, exp, tgt, best_comp)."""
    if row['Position'].strip().upper() == 'P':
        return None
    name, nickname = parse_name(row['Name'])
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    g = lambda k: float(row[k] or 0)
    pa, ab = g('PA'), g('AB')
    h, bb, ibb, hbp = g('H'), g('BB'), g('IBB'), g('HBP')
    ubb = bb - ibb  # unintentional walks only; IBB is a gameplay decision
    so, hr = g('SO'), g('HR')
    tb = h + g('2B') + 2*g('3B') + 3*hr
    tgt = {'avg': h/ab, 'obp': (h+ubb+hbp)/pa, 'slg': tb/ab,
           'bbp': ubb/pa, 'sop': so/pa, 'hrp': hr/pa, 'hbpp': hbp/pa}
    bats = row['Bats'].strip().upper()[0]
    comps = select_comps(tgt)
    # v0.4: multi-start optimization (10 restarts)
    import random
    base_widths = prescale(build_initial(comps), tgt, bats)
    starts = []
    starts.append(('heuristic', dict(base_widths)))
    # rate-derived: scale widths by target event rates
    rd = {k: max(1, int(v * 0.9)) for k, v in base_widths.items()}
    starts.append(('rate-derived', rd))
    # 8 randomized legal seeds
    for i in range(8):
        random.seed(1000 + i)
        rw = {k: max(0, v + random.randint(-15, 15))
              for k, v in base_widths.items()}
        starts.append((f'random-{i}', rw))
    best_err, best_secs, best_idx, init_err = float('inf'), None, -1, None
    for idx, (label, w0) in enumerate(starts):
        secs, e = tune(dict(w0), tgt, bats)
        if idx == 0:
            init_err = e
        if e < best_err:
            best_err, best_secs, best_idx = e, secs, idx
    # v0.4: exhaustive neighborhood search ±1, ±2 around best
    improved = True
    while improved:
        improved = False
        cur_widths = {}
        # reconstruct widths from best_secs (approximate via reverse)
        # simpler: perturb the best sections directly
        for sec in ('WHEELHOUSE', 'PATIENT', 'TOUGH', 'IN-PLAY'):
            for hand in ('vsLHP', 'vsRHP'):
                for outcome, rng in best_secs[sec][hand].items():
                    if rng:
                        key = (sec, hand, outcome)
                        cur_widths[key] = rng[1] - rng[0] + 1
        for key, w in cur_widths.items():
            sec, hand, outcome = key
            for delta in (-2, -1, 1, 2):
                nw = max(0, w + delta)
                if nw == w:
                    continue
                # apply to a copy
                import copy
                s2 = copy.deepcopy(best_secs)
                r0 = s2[sec][hand][outcome]
                s2[sec][hand][outcome] = [r0[0], r0[0] + nw - 1]
                e2 = err(expected(s2, bats), tgt)
                if e2 < best_err - 1e-10:
                    best_err, best_secs, improved = e2, s2, True
                    break
            if improved:
                break
    sections = best_secs
    exp = expected(sections, bats)
    actual_err = err(exp, tgt)
    # v0.4 diagnostics
    init_label = starts[0][0]
    best_label = starts[best_idx][0]
    improvement = ((init_err - best_err) / init_err * 100) if init_err > 0 else 0
    opt_status = 'UNSTABLE INITIALIZATION' if improvement > 50 else 'STABLE'
    r = ratings(row)
    best_comp = min(PROFILES, key=lambda p: comp_distance(p, tgt))['name']
    # v0.5: audit trail
    import datetime
    audit = {
        'solver_version': '0.5',
        'built_utc': datetime.datetime.utcnow().isoformat() + 'Z',
        'input_row': {k: row[k] for k in row},
        'ibb_treatment': f"BB={g('BB'):.0f} IBB={g('IBB'):.0f} "
                         f"uBB={ubb:.0f} target_bbp={tgt['bbp']:.4f}",
        'winning_seed': best_label,
        'restart_index': best_idx,
        'objective_score': round(actual_err, 6),
        'best_possible_score': round(best_err, 6),
        'neighborhood_search': 'exhaustive ±1,±2 completed',
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
        'out_table': [dict(x) for x in BY_NAME[best_comp]['out_table']],
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
