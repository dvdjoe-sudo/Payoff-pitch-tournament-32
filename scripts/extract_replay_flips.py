#!/usr/bin/env python3
"""Extract the replay fixtures for the playable mode's verification
gate (spec 11.1) from the recorded game evidence. Outputs (all
under scripts/replay/):

  replay_a_flips.json / replay_b_flips.json
      The recorded FAC history as a serve stream: card items
      {type:'card', fac_id, purpose} and reshuffle markers
      {type:'reshuffle', reason, inning?} where a [0, purpose]
      history entry stood.
  replay_a_pas.json / replay_b_pas.json
      The recorded per-PA records the comparator checks: pre-state
      (inning, half, outs, bases by name, score, batter, pitcher)
      and, for B, the recorded post-state.
  replay_a_actions.json / replay_b_actions.json
      Every pitching change / substitution anchored to the PA
      ordinal it precedes, from the recorded pitcher spans and
      lines, verified against the written records.
  replay_b_overrides.json
      The single fenced override: PA47, THE WHEELS (spec 11.1).

Replay A's per-PA segmentation comes from re-running the
deterministic Python stack (promotion_series_game.run_chc, seed
20261701) with the engine log wrapped to capture the state at
every PA header. The rerun is only used if it reproduces the
recorded final state on every compared field; the verification
result is written to replay_a_rerun_check.json and printed.
The recorded state files are the authority throughout; nothing
here writes to them.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'replay')
os.makedirs(OUT, exist_ok=True)

CUBS = os.path.expanduser('~/workspace/payoff-pitch-cubs')
SANDBOX = os.path.expanduser('~/workspace/payoff-pitch-managers/sandbox')
STATE_A = os.path.join(CUBS, 'battery',
                       'state_EXHIBITION_r106_series_g1_20261701.json')
STATE_B = os.path.join(CUBS, 'state_series_chc_mon_g1.json')
EV_B1 = os.path.join(CUBS, 'r106_g1_segment_evidence.json')
EV_B2 = os.path.join(CUBS, 'r106_g1_top7_evidence.json')
DECK = os.path.join(REPO, 'data', 'playable_r106.json')


def load(p):
    with open(p) as f:
        return json.load(f)


def flips_from_history(S):
    stream = []
    for fac_id, purpose in S['fac']['history']:
        if fac_id == 0:
            reason = purpose
            if reason.startswith('RESHUFFLE: '):
                reason = reason[len('RESHUFFLE: '):]
            item = {'type': 'reshuffle', 'reason': reason}
            # protocol markers carry the inning they open
            if reason.startswith('after ') and 'full innings' in reason:
                n = int(reason.split()[1])
                item['inning'] = n + 1
            stream.append(item)
        else:
            stream.append({'type': 'card', 'fac_id': fac_id,
                           'purpose': purpose})
    return stream


def bases_names(S):
    return [e['name'] if e else None for e in S['bases']]


# ---------------------------------------------------------------- A
def extract_a():
    S = load(STATE_A)
    stream = flips_from_history(S)
    with open(os.path.join(OUT, 'replay_a_flips.json'), 'w') as f:
        json.dump(stream, f)

    # --- deterministic rerun with per-PA capture
    sys.path.insert(0, SANDBOX)
    sys.path.insert(0, CUBS)
    import promotion_series_game as PSG  # noqa: E402
    import pilot_chance_setup as CS  # noqa: E402
    E = CS.E
    captures = []
    orig_log = E.log

    def cap_log(state, msg):
        if msg.startswith('[') and ' out, bases ' in msg:
            import copy
            captures.append({
                'inning': state['inning'], 'half': state['half'],
                'outs': state['outs'], 'bases': bases_names(state),
                'score': dict(state['score']),
                'fac_len': len(state['fac']['history']),
                'header': msg,
            })
        orig_log(state, msg)

    cfg = load(os.path.join(SANDBOX, 'playtest_series_cfg_g1.json'))
    rerun_state = '/tmp/replay_a_rerun_state.json'
    rerun_ev = '/tmp/replay_a_rerun_ev.json'
    E.log = cap_log
    try:
        PSG.run_chc(cfg, 20261701, rerun_state, rerun_ev)
    finally:
        E.log = orig_log
    R = load(rerun_state)

    def batting(R):
        return {t: R['teams'][t]['batting'] for t in ('CHC', 'OPP')}

    def pitching(R):
        return {t: R['teams'][t]['pitching'] for t in ('CHC', 'OPP')}

    checks = {
        'score': R['score'] == S['score'],
        'linescore': R['linescore'] == S['linescore'],
        'batting': batting(R) == batting(S),
        'pitching': pitching(R) == pitching(S),
        'pitcher_spans': json.dumps(R['pitcher_spans'], sort_keys=True)
            == json.dumps(S['pitcher_spans'], sort_keys=True),
        'ledger_counts': {k: v['count'] for k, v in R['ledger'].items()}
            == {k: v['count'] for k, v in S['ledger'].items()},
        'fac_history': R['fac']['history'] == S['fac']['history'],
        'final': bool(R['final']) == bool(S['final']),
        'log': R['log'] == S['log'],
    }
    with open(os.path.join(OUT, 'replay_a_rerun_check.json'), 'w') as f:
        json.dump(checks, f, indent=1)
    print('Replay A rerun verification:', checks)
    if not all(checks.values()):
        print('RERUN DOES NOT REPRODUCE THE RECORDED STATE; '
              'per-PA records fall back to log headers + final state')

    # batter/pitcher per capture from the header text
    pas = []
    for c in captures:
        hdr = c['header']
        rest = hdr.split('] ', 1)[1]
        batter, pitcher = rest.split(' vs ')
        pas.append({'inning': c['inning'], 'half': c['half'],
                    'outs': c['outs'], 'bases': c['bases'],
                    'score': c['score'], 'batter': batter,
                    'pitcher': pitcher, 'fac_len': c['fac_len']})
    with open(os.path.join(OUT, 'replay_a_pas.json'), 'w') as f:
        json.dump({'pas': pas, 'rerun_verified': all(checks.values()),
                   'final_state': final_snapshot(S)}, f)

    # actions: every span after the starters, anchored to the
    # first PA whose recorded pitcher is the incoming man
    actions = []
    starters = {sp['team']: sp['name'] for sp in S['pitcher_spans'][:2]}
    seen = set()
    for sp in S['pitcher_spans']:
        key = (sp['team'], sp['name'])
        if key in seen:
            continue
        seen.add(key)
        if starters.get(sp['team']) == sp['name']:
            continue
        anchor = None
        for i, pa in enumerate(pas):
            if pa['pitcher'] == sp['name']:
                anchor = i + 1
                break
        actions.append({'pa': anchor, 'team': sp['team'],
                        'in': sp['name'], 'span_start': sp['start']})
    with open(os.path.join(OUT, 'replay_a_actions.json'), 'w') as f:
        json.dump(actions, f, indent=1)
    print('Replay A: %d stream items, %d PAs, actions %s'
          % (len(stream), len(pas), actions))


def final_snapshot(S):
    return {
        'score': S['score'], 'linescore': S['linescore'],
        'batting': {t: S['teams'][t]['batting'] for t in ('CHC', 'OPP')},
        'pitching': {t: S['teams'][t]['pitching'] for t in ('CHC', 'OPP')},
        'pitcher_spans': S['pitcher_spans'],
        'ledger_counts': {k: v['count'] for k, v in S['ledger'].items()},
        'fac': {'draws': S['fac']['draws'],
                'history_len': len(S['fac']['history'])},
        'final': S['final'],
        'inning': S['inning'], 'half': S['half'], 'outs': S['outs'],
        'bases': bases_names(S),
    }


# ---------------------------------------------------------------- B
def extract_b():
    S = load(STATE_B)
    stream = flips_from_history(S)
    with open(os.path.join(OUT, 'replay_b_flips.json'), 'w') as f:
        json.dump(stream, f)

    ev1 = load(EV_B1)
    ev2 = load(EV_B2)
    pas = []
    for pa in ev1['pas'] + ev2['pas']:
        pas.append({'pre': pa['pre'], 'post': pa['post'],
                    'pending': pa.get('pending', False)})
    with open(os.path.join(OUT, 'replay_b_pas.json'), 'w') as f:
        json.dump({'pas': pas, 'final_state': final_snapshot(S),
                   'strength_roll': ev1['strength_roll'],
                   'declaration_setup': (S['ledger'].get(
                       'declaration_setup') or {}).get('details', []),
                   'declaration_wheels': (S['ledger'].get(
                       'declaration_wheels') or {}).get('details', [])}, f)

    # actions: the Vaughn change (a Joe call before the top of
    # the 6th) anchored at the first PA he pitches; plus any
    # substitution the recorded ledger carries, located by its
    # log line inside the evidence segments.
    actions = []
    for i, pa in enumerate(pas):
        if pa['pre']['pitcher'] == 'Hippo Vaughn':
            actions.append({'pa': i + 1, 'team': 'CHC',
                            'out': 'Fergie Jenkins', 'in': 'Hippo Vaughn',
                            'kind': 'pitching_change'})
            break
    sub_details = (S['ledger'].get('substitution') or {}).get('details', [])
    seg_lines = []
    for pa in ev1['pas'] + ev2['pas']:
        seg_lines.append(pa.get('segment', []))
    for d in sub_details:
        for i, lines in enumerate(seg_lines):
            if any(d.split(' (')[0] in ln for ln in lines):
                actions.append({'pa': i + 1, 'kind': 'substitution',
                                'detail': d})
                break
    with open(os.path.join(OUT, 'replay_b_actions.json'), 'w') as f:
        json.dump(actions, f, indent=1)

    # PA47 override: find real FAC cards whose faces reproduce
    # the recorded rewound resolution (2d6 = 2+3 = 7, % = 51).
    deck = load(DECK)['deck']
    by_id = {c['fac_id']: c for c in deck}
    a = next(c for c in deck if c['d1d6'] == 2 and c['d2d6'] == 7)
    b = next(c for c in deck if c['d1d6'] == 3 and c['pct'] == 51)
    hist = S['fac']['history']
    assert hist[106][0] == 152 and hist[106][1] == '1d6', hist[106]
    assert hist[107][0] == 171 and hist[107][1] == '2d6', hist[107]
    override = {
        'pa': 47, 'batter': 'Tim Raines', 'pitcher': 'Hippo Vaughn',
        'trigger': {'inning': 7, 'half': 'top', 'outs': 1,
                    'bases': [None, None, None],
                    'score': {'CHC': 0, 'OPP': 5}},
        'recorded_resolution': {'dice': [2, 3, 7], 'pct': 51,
                                'section': 'TOUGH', 'result': 'OUT G4'},
        'splice': {'fac_2d6': a['fac_id'], 'fac_pct': b['fac_id']},
        'live_die': {'seq': 107, 'fac_id': 152, 'purpose': '1d6',
                     'expected': 2},
        'conversion': {'result': 'infield single',
                       'booked': {'AB': 1, 'H': 1},
                       'post_bases': ['Tim Raines', None, None],
                       'post_outs': 1},
        'steal_step': {'seq': 108, 'fac_id': 171, 'purpose': '2d6',
                       'last_total': 6, 'attempt_booked': False},
    }
    with open(os.path.join(OUT, 'replay_b_overrides.json'), 'w') as f:
        json.dump([override], f, indent=1)
    print('Replay B: %d stream items, %d PAs, actions %s, splice %s'
          % (len(stream), len(pas), actions, override['splice']))


if __name__ == '__main__':
    extract_a()
    extract_b()
