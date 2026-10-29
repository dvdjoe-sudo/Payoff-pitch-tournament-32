/* Payoff Pitch — Playable Mode, Phase 1 (R1-06 fixture: Chicago vs Montreal).
 *
 * A function-by-function port of the governed Python reference stack:
 * the Cubs v2 engine (pitcher_output_v2/engine_v2.py), the FAC deck as
 * dice surface (sim/fac.py install semantics), the pitcher addendum
 * (sim/addendum.py), the fatigue fix (fatigue_fix.py), the traits2
 * Williams package re-pointed to the guest slot (McGraw pinned off),
 * Frank Chance (traits_chance.py), the bunt-grade overlay and the
 * driver loop of chance_setup.py / series_chc_mon_setup_g1.py.
 * traits5 (the Martinez library layer) is installed-but-inert in this
 * fixture — no Martinez assignment exists, so its wrappers delegate;
 * the port carries the delegation points only.
 *
 * Exhibition only. Nothing in this file writes tournament_results.json
 * or any official record; exports are downloads in the player's hand.
 *
 * The Engine is a generator core: it runs until it needs a value,
 * yields the pending step ({step:'2d6'|'%'|'1d6'|'1d10'}) or a
 * decision request, and resumes when the driver serves it. The same
 * shipped code runs headlessly under Node (see the export guard at
 * the bottom) for the replay gate and the rule batteries.
 */
(function (global) {
'use strict';

/* ---------------------------------------------------------- utils */
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function shuffleInPlace(arr, rand) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    const t = arr[i]; arr[i] = arr[j]; arr[j] = t;
  }
  return arr;
}
function deepCopy(o) { return JSON.parse(JSON.stringify(o)); }
function pad2(n) { return (n < 10 ? '0' : '') + n; }
function has(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }

/* ------------------------------------------------------- PlayData */
const PlayData = {
  data: null,
  load(data) {
    this.data = data;
    this.assertBuild();
    this.deckById = {};
    for (const c of data.deck) this.deckById[c.fac_id] = c;
    return this;
  },
  /* The Section 3 build assertions, re-checked client-side on load. */
  assertBuild() {
    const d = this.data, bad = (m) => { throw new Error('playable data: ' + m); };
    if (!d || !d.fixture) bad('no fixture block');
    for (const club of ['CHC', 'MON']) {
      if (Object.keys(d.hitters[club]).length !== 15) bad(club + ' hitters != 15');
      if (Object.keys(d.pitchers[club]).length !== 11) bad(club + ' pitchers != 11');
      for (const nm of Object.keys(d.pitchers[club])) {
        const p = d.pitchers[club][nm];
        if (p.addendum !== true) bad(club + ' ' + nm + ' missing merged addendum');
        for (let t = 2; t <= 12; t++) if (!has(p.card_table_2d6, String(t))) bad(club + ' ' + nm + ' 2d6 table missing ' + t);
      }
    }
    if (d.deck.length !== 256) bad('deck != 256');
    const ids = new Set(d.deck.map((c) => c.fac_id));
    if (ids.size !== 256) bad('deck ids not unique');
    if (d.rare_plays.length !== 24) bad('rare plays != 24');
    if (!d.parks['Wrigley Field'] || !d.parks['Stade Olympique']) bad('park missing');
  },
  clubOf(slot) { return slot === 'CHC' ? 'CHC' : 'MON'; },
  hitter(slot, name) { return this.data.hitters[this.clubOf(slot)][name]; },
  pitcher(slot, name) { return this.data.pitchers[this.clubOf(slot)][name]; },
  park(name) { return this.data.parks[name]; },
};

/* ---------------------------------------------------- roll sources */
/* A source serves one step at a time through serve(kind, S).
 * It returns the value in engine shape: '2d6' -> [d1, d2, total],
 * '%' -> 0..99, '1d6' -> 1..6, '1d10' -> 0..9. Every served value is
 * recorded into S.flips by the source with its purpose and tag.
 * Deck state lives on S.deck: {order (full cycle order), pos,
 * consumed {facId: {pa, step, source}}, peek (manual 2d6 peek owed),
 * draws, reshuffles, midCycle, reshuffleDone}. */

function deckNextRand(S) {
  // The deck's own shuffle stream (the web game's seed, not Python's
  // Mersenne stream). State is a single uint32 on S.deck so snapshots
  // and autosaves carry it exactly.
  let a = (S.deck.rngState || 0) | 0;
  a = (a + 0x6D2B79F5) | 0;
  S.deck.rngState = a;
  let t = Math.imul(a ^ (a >>> 15), 1 | a);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function deckShuffle(S) {
  const order = [];
  for (let i = 1; i <= 256; i++) order.push(i);
  for (let i = order.length - 1; i > 0; i--) {
    const j = Math.floor(deckNextRand(S) * (i + 1));
    const t = order[i]; order[i] = order[j]; order[j] = t;
  }
  S.deck.order = order;
  S.deck.pos = 0;
  S.deck.consumed = {};
}
function deckNew(S, seed) {
  S.deck = { seed: seed, order: [], pos: 0, consumed: {}, peek: null,
             draws: 0, reshuffles: 0, midCycle: 0, reshuffleDone: [],
             rngState: seed | 0 };
  deckShuffle(S);
}
function deckReshuffle(S, reason) {
  deckShuffle(S);
  S.deck.peek = null;
  S.deck.reshuffles += 1;
  S.flips.push({ fac_id: 0, purpose: 'RESHUFFLE: ' + reason, source: 'deck' });
}
function deckDrawCard(S, purpose, tag) {
  if (S.deck.pos >= S.deck.order.length) {
    deckShuffle(S);
    S.deck.midCycle += 1;
    S.flips.push({ fac_id: 0, purpose: 'RESHUFFLE: deck exhausted mid-cycle', source: tag });
  }
  const fid = S.deck.order[S.deck.pos];
  S.deck.pos += 1;
  S.deck.draws += 1;
  S.deck.consumed[fid] = { source: tag };
  S.flips.push({ fac_id: fid, purpose: purpose, source: tag });
  return PlayData.deckById[fid];
}
function deckPeekCard(S) {
  if (S.deck.pos >= S.deck.order.length) {
    deckShuffle(S);
    S.deck.midCycle += 1;
    S.flips.push({ fac_id: 0, purpose: 'RESHUFFLE: deck exhausted mid-cycle', source: 'deck' });
  }
  return PlayData.deckById[S.deck.order[S.deck.pos]];
}

const DeckSource = {
  name: 'deck',
  reshuffle(S, reason, inn) {
    deckReshuffle(S, reason);
    if (!S.deck.reshuffleDone.includes(inn)) S.deck.reshuffleDone.push(inn);
  },
  serve(kind, S) {
    if (kind === '2d6') {
      const c = deckDrawCard(S, '2d6', 'deck');
      const pk = deckPeekCard(S);
      return [c.d1d6, pk.d1d6, c.d2d6];
    }
    if (kind === '%') return deckDrawCard(S, '%', 'deck').pct;
    if (kind === '1d6') return deckDrawCard(S, '1d6', 'deck').d1d6;
    if (kind === '1d10') return deckDrawCard(S, '1d10', 'deck').pct % 10;
    throw new Error('DeckSource: bad step ' + kind);
  },
};

function makeDiceSource(seed) {
  const rand = mulberry32(seed == null ? 987654321 : seed);
  return {
    name: 'dice',
    reshuffle(S, reason, inn) {
      if (!S.deck.reshuffleDone.includes(inn)) S.deck.reshuffleDone.push(inn);
      S.flips.push({ fac_id: null, purpose: 'RESHUFFLE: ' + reason, source: 'dice' });
    },
    serve(kind, S) {
      if (kind === '2d6') {
        const a = 1 + Math.floor(rand() * 6), b = 1 + Math.floor(rand() * 6);
        S.flips.push({ fac_id: null, purpose: '2d6', source: 'dice', dice: [a, b] });
        return [a, b, a + b];
      }
      if (kind === '%') {
        const v = Math.floor(rand() * 100);
        S.flips.push({ fac_id: null, purpose: '%', source: 'dice', value: v });
        return v;
      }
      if (kind === '1d6') {
        const v = 1 + Math.floor(rand() * 6);
        S.flips.push({ fac_id: null, purpose: '1d6', source: 'dice', value: v });
        return v;
      }
      if (kind === '1d10') {
        const v = Math.floor(rand() * 10);
        S.flips.push({ fac_id: null, purpose: '1d10', source: 'dice', value: v });
        return v;
      }
      throw new Error('DiceSource: bad step ' + kind);
    },
  };
}

/* ManualSource: values come from the driver (UI or battery script)
 * through provide(). Card form runs against the virtual deck state
 * exactly as Section 5.2 specifies; raw-value form touches no deck. */
function makeManualSource() {
  return {
    name: 'manual',
    pendingProvide: null,
    reshuffle(S, reason, inn) {
      deckReshuffle(S, reason);
      if (!S.deck.reshuffleDone.includes(inn)) S.deck.reshuffleDone.push(inn);
    },
    provide(v) { this.pendingProvide = v; },
    serve(kind, S) {
      const v = this.pendingProvide;
      this.pendingProvide = null;
      if (v == null) throw new Error('ManualSource: no value provided for step ' + kind);
      if (v.form === 'value') {
        // validate against the pending step's type and range only
        if (kind === '2d6') {
          if (!Array.isArray(v.dice) || v.dice.length !== 2 ||
              v.dice.some((d) => !Number.isInteger(d) || d < 1 || d > 6)) {
            throw new Error('a 2d6 step takes two die faces, each 1-6 (entered as the pair, so the low die is preserved)');
          }
          S.flips.push({ fac_id: null, purpose: '2d6', source: 'manual-value', dice: v.dice.slice() });
          return [v.dice[0], v.dice[1], v.dice[0] + v.dice[1]];
        }
        const ranges = { '%': [0, 99], '1d6': [1, 6], '1d10': [0, 9] };
        const r = ranges[kind];
        if (!r || !Number.isInteger(v.value) || v.value < r[0] || v.value > r[1]) {
          throw new Error('value out of range for a ' + kind + ' step');
        }
        S.flips.push({ fac_id: null, purpose: kind, source: 'manual-value', value: v.value });
        return v.value;
      }
      // card form
      const fid = v.fac_id;
      if (!Number.isInteger(fid) || fid < 1 || fid > 256) {
        throw new Error('a FAC card id is an integer 1-256');
      }
      if (S.deck.peek && S.deck.peek !== fid) {
        throw new Error('the 2d6 pair peeked FAC ' + S.deck.peek + '; flip it next, or undo the PA');
      }
      if (has(S.deck.consumed, fid)) {
        const c = S.deck.consumed[fid];
        throw new Error('FAC ' + fid + ' already flipped this cycle' +
          (c.pa != null ? ', PA ' + c.pa + (c.stepLabel ? ', ' + c.stepLabel : '') : ''));
      }
      const idx = S.deck.order.indexOf(fid, S.deck.pos);
      if (idx < 0) throw new Error('FAC ' + fid + ' is not in the remaining deck');
      S.deck.order.splice(idx, 1);
      S.deck.consumed[fid] = { source: 'manual-card', pa: v.pa != null ? v.pa : null, stepLabel: v.stepLabel || null };
      S.deck.draws += 1;
      const card = PlayData.deckById[fid];
      if (kind === '2d6') {
        if (!Number.isInteger(v.peek_id) || v.peek_id < 1 || v.peek_id > 256) {
          throw new Error('a manual 2d6 step also needs the peek: the id of the top card of your deck');
        }
        if (v.peek_id === fid) throw new Error('the peek is the next card, not the flipped card itself');
        if (has(S.deck.consumed, v.peek_id)) throw new Error('peeked FAC ' + v.peek_id + ' was already flipped this cycle');
        const pk = PlayData.deckById[v.peek_id];
        S.deck.peek = v.peek_id;
        S.flips.push({ fac_id: fid, purpose: '2d6', source: 'manual-card', peek_fac_id: v.peek_id });
        return [card.d1d6, pk.d1d6, card.d2d6];
      }
      if (S.deck.peek === fid) S.deck.peek = null;
      S.flips.push({ fac_id: fid, purpose: kind, source: 'manual-card' });
      if (kind === '%') return card.pct;
      if (kind === '1d6') return card.d1d6;
      if (kind === '1d10') return card.pct % 10;
      throw new Error('ManualSource: bad step ' + kind);
    },
  };
}

/* ReplaySource: serves a recorded flip stream (extraction output).
 * Stream items: {type:'card', fac_id, purpose} in order, with
 * {type:'reshuffle', reason} markers at their stream positions.
 * Bypasses the manual-entry refusals by design (spec 11.1). */
function makeReplaySource(stream) {
  return {
    name: 'replay',
    stream: stream,
    i: 0,
    log: [],   // {pa, step, purpose, fac_id} per consumed value
    paIndex: 0,
    stepIndex: 0,
    exhausted() {
      let j = this.i;
      while (j < this.stream.length && this.stream[j].type === 'reshuffle') j++;
      return j >= this.stream.length;
    },
    _take(S) {
      while (this.i < this.stream.length && this.stream[this.i].type === 'reshuffle') {
        const r = this.stream[this.i++];
        S.flips.push({ fac_id: 0, purpose: 'RESHUFFLE: ' + r.reason, source: 'replay' });
        if (r.inning != null && !S.deck.reshuffleDone.includes(r.inning)) S.deck.reshuffleDone.push(r.inning);
      }
      if (this.i >= this.stream.length) {
        const e = new Error('replay stream exhausted');
        e.streamExhausted = true;
        throw e;
      }
      return this.stream[this.i++];
    },
    _peekItem() {
      let j = this.i;
      while (j < this.stream.length && this.stream[j].type === 'reshuffle') j++;
      return j < this.stream.length ? this.stream[j] : null;
    },
    serve(kind, S) {
      const item = this._take(S);
      if (item.purpose !== kind) {
        const e = new Error('replay divergence: engine asked for ' + kind +
          ' but the recorded stream has ' + item.purpose + ' (FAC ' + item.fac_id + ') at stream position ' + (this.i - 1));
        e.replayDivergence = { purposeExpected: item.purpose, purposeActual: kind, fac_id: item.fac_id };
        throw e;
      }
      const card = PlayData.deckById[item.fac_id];
      S.flips.push({ fac_id: item.fac_id, purpose: kind, source: 'replay' });
      this.log.push({ pa: this.paIndex, step: this.stepIndex, purpose: kind, fac_id: item.fac_id });
      this.stepIndex += 1;
      if (kind === '2d6') {
        const pk = this._peekItem();
        const pkCard = pk ? PlayData.deckById[pk.fac_id] : card;
        return [card.d1d6, pkCard.d1d6, card.d2d6];
      }
      if (kind === '%') return card.pct;
      if (kind === '1d6') return card.d1d6;
      if (kind === '1d10') return card.pct % 10;
      throw new Error('ReplaySource: bad step ' + kind);
    },
  };
}

/* ============================================================ Engine */
/* G (game context) carries what Python keeps in module globals:
 * { starters {CHC, OPP}, penRole {CHC, OPP}, allPenNames Set,
 *   park (the venue park entry), buntOverlay bool, clauses bool,
 *   prePa bool, human {CHC: bool, OPP: bool} }.
 * Team slots are 'CHC' and 'OPP' exactly as in the Python state;
 * 'OPP' is Montreal in this fixture. */

const DEF_POS = [[2, 'RANGE', 'P'], [6, 'RANGE', '1B'], [12, 'RANGE', '2B'],
  [16, 'RANGE', '3B'], [22, 'RANGE', 'SS'], [26, 'RANGE', 'LF'],
  [31, 'RANGE', 'CF'], [35, 'RANGE', 'RF'], [42, 'ERROR', 'P'],
  [43, 'ERROR', 'C'], [50, 'ERROR', '1B'], [61, 'ERROR', '2B'],
  [75, 'ERROR', '3B'], [90, 'ERROR', 'SS'], [93, 'ERROR', 'LF'],
  [96, 'ERROR', 'CF'], [99, 'ERROR', 'RF']];
function defPos(pct) {
  let lo = 1;
  for (const [hi, chk, pos] of DEF_POS) {
    if (lo <= pct && pct <= hi) return [chk, pos];
    lo = hi + 1;
  }
  return ['ERROR', 'RF'];
}
const HIT_G = { '1B': 'A', '3B': 'A', '2B': 'B', 'SS': 'B', 'P': 'B', 'LF': 'C', 'CF': 'C', 'RF': 'C', 'C': 'B' };
const DEF_HIT = {
  A: { 2: ['2B', 3], 3: ['1B', 2], 4: ['2B', 2], 5: ['1B', 1], 6: ['2B', 2], 7: ['1B', 1], 8: ['2B', 2], 9: ['1B', 1], 10: ['2B', 2], 11: ['1B', 2], 12: ['2B+', 3] },
  B: { 2: ['1B', 2], 3: ['1B', 1], 4: ['1B', 1], 5: ['1B', 1], 6: ['1B', 1], 7: ['1B', 2], 8: ['1B', 1], 9: ['1B', 1], 10: ['1B', 1], 11: ['1B', 2], 12: ['1B', 2] },
  C: { 2: ['2B', 3], 3: ['1B', 2], 4: ['1B', 2], 5: ['1B', 2], 6: ['1B', 2], 7: ['2B', 2], 8: ['1B', 2], 9: ['1B', 2], 10: ['2B', 3], 11: ['2B', 3], 12: ['2B+', 3] },
};
const DEF_ERR = {
  C: { 2: 2, 3: 2, 4: 0, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1, 12: 0 },
  INF: { 2: 2, 3: 1, 4: 2, 5: 1, 6: 1, 7: 1, 8: 1, 9: -1, 10: 1, 11: 1, 12: 2 },
  OF: { 2: 2, 3: 3, 4: 1, 5: 1, 6: 2, 7: -1, 8: -1, 9: 1, 10: -1, 11: 1, 12: 2 },
};
const DEF_OUT = {
  C: { 2: 'Popout', 3: 'Popout', 4: 'PopoutF', 5: 'PopoutF', 6: 'GB+adv', 7: 'PopoutF', 8: 'GB-fc', 9: 'PopoutF', 10: 'Popout', 11: 'Popout', 12: 'Popout' },
  INF: { 2: 'GB-DP-A', 3: 'GB+adv', 4: 'Lineout', 5: 'GB-DP-AB', 6: 'GB-fc', 7: 'GB-fc', 8: 'GB+adv', 9: 'GB-DP-A', 10: 'Popout', 11: 'GB+adv', 12: 'Lineout-DP' },
  OF: { 2: 'DeepFly', 3: 'ShortFlyDP', 4: 'ShortFly', 5: 'ShortFly', 6: 'ShortFly', 7: 'ShortFly', 8: 'DeepFly', 9: 'DeepFly', 10: 'DeepFly', 11: 'DeepFly', 12: 'ShortFlyDP' },
};
const STEAL_COL = {};
for (const c of ['A5', 'A4', 'A3', 'B5', 'B4', 'C5']) STEAL_COL[c] = [13, 17];
for (const c of ['A2', 'B3', 'C4', 'D5']) STEAL_COL[c] = [13, 26];
for (const c of ['A1', 'B2', 'C3', 'D4', 'F5']) STEAL_COL[c] = [13, 42];
for (const c of ['B1', 'C2', 'D3', 'F4']) STEAL_COL[c] = [13, 59];
for (const c of ['C1', 'D2', 'D1', 'F3', 'F2', 'F1']) STEAL_COL[c] = [13, 84];
const STEAL_HOME = { A: [10, 69], B: [10, 79], C: [10, 89], D: [10, 94], F: [10, 98] };
const BUNT = {
  A: [[0, 0, 'PO'], [1, 2, 'DP'], [3, 6, 'LEAD'], [7, 92, 'SH'], [93, 94, 'MISS'], [95, 99, 'E?']],
  B: [[0, 2, 'PO'], [3, 5, 'DP'], [6, 10, 'LEAD'], [11, 90, 'SH'], [91, 94, 'MISS'], [95, 99, 'E?']],
  C: [[0, 3, 'PO'], [4, 6, 'DP'], [7, 15, 'LEAD'], [16, 89, 'SH'], [90, 94, 'MISS'], [95, 99, 'E?']],
  D: [[0, 5, 'PO'], [6, 9, 'DP'], [10, 24, 'LEAD'], [25, 87, 'SH'], [88, 94, 'MISS'], [95, 99, 'E?']],
  F: [[0, 7, 'PO'], [8, 14, 'DP'], [15, 33, 'LEAD'], [34, 84, 'SH'], [85, 94, 'MISS'], [95, 99, 'E?']],
};
const ADV_1B_FROM1 = { 1: [1, false], 2: [2, false], 3: [1, false], 4: [1, true], 5: [1, false], 6: [1, false] };
const ADV_1B_FROM2 = { 1: [1, false], 2: [99, false], 3: [99, false], 4: [1, true], 5: [99, false], 6: [1, false] };
const ADV_2B_FROM1 = { 1: [2, false], 2: [2, false], 3: [99, false], 4: [2, true], 5: [99, false], 6: [99, false] };
const HITLOC_1B = { 0: 'RF', 1: 'LF', 2: 'LF', 3: 'CF', 4: 'CF', 5: null, 6: 'CF', 7: null, 8: null, 9: 'CF' };
const HITLOC_1B_LHB = { 5: 'RF', 7: 'RF', 8: 'LF' };
const HITLOC_1B_RHB = { 5: 'LF', 7: 'LF', 8: 'RF' };
const HITLOC_2B = { 0: null, 1: 'RF', 2: 'LF', 3: null, 4: 'CF', 5: 'LF', 6: 'CF', 7: null, 8: 'CF', 9: null };
const HITLOC_2B_LHB = { 0: 'RF', 3: 'RF', 7: 'RF', 9: 'LF' };
const HITLOC_2B_RHB = { 0: 'LF', 3: 'LF', 7: 'LF', 9: 'RF' };
const EMERGENCY_TABLE = { '2': 'TOUGH', '3': 'TOUGH', '4': 'TOUGH', '5': 'IN-PLAY', '6': 'IN-PLAY', '7': 'PATIENT', '8': 'PATIENT', '9': 'IN-PLAY', '10': 'WHEELHOUSE', '11': 'BALLPARK', '12': 'DEFENSE' };
const TEAMNAME = { CHC: 'Chicago', OPP: 'Montreal' };

/* ---- the roll surface. Every random input in the engine is one of
 * these four generators; each yields exactly one step. rollpct also
 * carries the addendum's wild-pitch arm (Section 6.1.16): the arm is
 * set by the resolvePA chain and popped by the PA's first % read. */
function* roll2d6(G, S) { const v = yield { step: '2d6' }; return v; }
function* roll1d6(G, S) { const v = yield { step: '1d6' }; return v; }
function* roll1d10(G, S) { const v = yield { step: '1d10' }; return v; }
function* rollpct(G, S) {
  const armed = !!S._add_wp_armed;
  if (armed) S._add_wp_armed = false;
  let v = yield { step: '%' };
  if (armed && S.bases.some(Boolean)) {
    const wp = pitcherCard(G, S, fldTeam(S), curPitcher(S)).wp;
    if (wpInRange(v, wp)) {
      applyWP(G, S, 1);
      const v2 = yield { step: '%' };
      if (wpInRange(v2, wp)) applyWP(G, S, 2);
      return v2;
    }
  }
  return v;
}
function wpInRange(pct, wp) {
  if (wp == null) return false;
  if (Array.isArray(wp)) return wp[0] <= pct && pct <= wp[1];
  if (typeof wp === 'string') {
    if (wp.includes('-')) {
      const parts = wp.split('-');
      return parseInt(parts[0], 10) <= pct && pct <= parseInt(parts[1], 10);
    }
    return pct === parseInt(wp, 10);
  }
  return pct === wp;
}

/* ------------------------------------------------------------ state */
function blankBstat() {
  return { PA: 0, AB: 0, H: 0, '2B': 0, '3B': 0, HR: 0, R: 0, RBI: 0, BB: 0, HBP: 0, SO: 0, SB: 0, CS: 0, GDP: 0, SH: 0 };
}
function blankPstat() {
  return { outs: 0, H: 0, R: 0, ER: 0, BB: 0, SO: 0, HR: 0, BF: 0, innings_seen: [], fatigued: false, entered_inning: null };
}
function newState(G, cfg) {
  const fx = PlayData.data.fixture;
  const S = { inning: 1, half: 'top', outs: 0, bases: [null, null, null],
    score: { CHC: 0, OPP: 0 }, linescore: { CHC: [], OPP: [] }, log: [], ledger: {},
    pending: null, final: null, flags: {}, woudouts: 0, steal_checked: {},
    jump1_used: {}, hr_log: [], notes: [], run_events: [], errors_by_pos: [],
    def_outs: { CHC: 0, OPP: 0 }, pitcher_spans: [], pa_count: 0,
    home: cfg.homeSlot, flips: [], fc_count: {}, declarations: null,
    traits: cfg.traits, outs_needed: 3 };
  S.teams = {};
  for (const slot of ['CHC', 'OPP']) {
    const club = PlayData.clubOf(slot);
    const lineup = (cfg.lineups && cfg.lineups[club]) || fx.lineups[club];
    const bench = (cfg.benches && cfg.benches[club]) || fx.benches[club];
    const order = lineup.map((s) => ({ name: s.name, pos: s.pos, in_game: true }));
    const field = {};
    for (const s of lineup) if (s.pos !== 'DH') field[s.pos] = s.name;
    const starter = cfg.starters[slot];
    field.P = starter;
    S.teams[slot] = { order: order, next_idx: 0, bench: bench.slice(),
      pen: fx.pens[club].slice(), field: field, pitcher: starter, removed: [],
      batting: {}, pitching: {}, team_errors: 0 };
    S.teams[slot].pitching[starter] = blankPstat();
  }
  // init_spans: both starters, entered_inning 1
  for (const slot of ['CHC', 'OPP']) {
    S.pitcher_spans.push({ team: slot, name: cfg.starters[slot],
      start: [1, slot === 'OPP' ? 'top' : 'bottom', 0], end: null });
    pstat(S, slot, cfg.starters[slot]).entered_inning = 1;
  }
  deckNew(S, cfg.seed);
  return S;
}
function T(S, team) { return S.teams[team]; }
function batTeam(S) { return S.half === 'top' ? (S.home === 'CHC' ? 'OPP' : 'CHC') : S.home; }
function fldTeam(S) { return S.half === 'top' ? S.home : (S.home === 'CHC' ? 'OPP' : 'CHC'); }
function elog(S, msg) { S.log.push(msg); }
function led(S, key, detail) {
  const e = S.ledger[key] || (S.ledger[key] = { count: 0, details: [] });
  e.count += 1;
  if (detail) e.details.push(detail);
  // addendum pickoff interception (Section 6.1.17): the auto-steal
  // site's gap_pickoff is resolved on the pickoff chart; the
  // manager-sent site's is not (its detail starts 'Manager-sent').
  if (key === 'gap_pickoff' && !(detail || '').startsWith('Manager-sent')) {
    S._pickoff_owed = true;
  }
}
function bstat(S, team, name) {
  const b = T(S, team).batting;
  if (!b[name]) b[name] = blankBstat();
  return b[name];
}
function pstat(S, team, name) {
  const p = T(S, team).pitching;
  if (!p[name]) p[name] = blankPstat();
  return p[name];
}
function curPitcher(S) { const ft = fldTeam(S); return T(S, ft).pitcher; }
function pitcherCard(G, S, team, name) {
  if (name === 'EMERGENCY') {
    return { name: 'EMERGENCY', throws: 'R', card_table_2d6: EMERGENCY_TABLE, so_modifier: 'NONE', card_type: 'RP' };
  }
  return PlayData.pitcher(team, name);
}
function hcard(G, name, team) { return PlayData.hitter(team, name); }
function fielderCard(G, S, fteam, pos) {
  const name = T(S, fteam).field[pos];
  if (name == null || pos === 'P') return [null, name];
  return [hcard(G, name, fteam), name];
}
function fieldingLine(G, S, fteam, pos) {
  if (pos === 'P') {
    led(S, 'gap_pitcher_fielding', 'DEFENSE check on P resolved on the Average line (C/E4): converted pitcher cards carry no fielding line');
    return ['C', 4, 6];
  }
  const [card] = fielderCard(G, S, fteam, pos);
  const p = card.positions[0];
  return [p.range, p.e, p.arm];
}
function catcherArm(G, S, fteam) {
  const [card] = fielderCard(G, S, fteam, 'C');
  const arm = card.positions[0].arm;
  return { 8: 1, 7: 2, 6: 3, 5: 4, 4: 5 }[arm];
}

/* --------------------------------------------------- scoring helpers */
function runnerAt(S, base) { const e = S.bases[base - 1]; return e ? e.name : null; }
function scoreRun(S, bteam, entry, rbiTo, unearned) {
  S.score[bteam] += 1;
  S.linescore[bteam][S.linescore[bteam].length - 1] += 1;
  bstat(S, bteam, entry.name).R += 1;
  const fteam = bteam === 'OPP' ? 'CHC' : 'OPP';
  const ps = pstat(S, fteam, entry.resp);
  ps.R += 1;
  if (!unearned && S.woudouts < 3) ps.ER += 1;
  if (rbiTo) bstat(S, bteam, rbiTo).RBI += 1;
  S.run_events.push({ inning: S.inning, half: S.half, team: bteam, resp: entry.resp, score: Object.assign({}, S.score) });
}
function applyPlay(S, batterName, batterDest, runnerDest, opts) {
  opts = opts || {};
  const rbiTo = opts.rbiTo || null, rbiRuns0 = opts.rbiRuns || 0;
  const unearnedRunners = opts.unearnedRunners || [];
  const bteam = batTeam(S);
  const cur = curPitcher(S);
  const old = S.bases.slice();
  const newbases = [null, null, null];
  const scored = [];
  let rbiLeft = rbiRuns0;
  for (const base of [3, 2, 1]) {
    const e = old[base - 1];
    if (!e) continue;
    const dest = runnerDest[base];
    if (dest === 0) continue;
    if (dest >= 4) {
      const un = unearnedRunners.includes(e.name);
      scoreRun(S, bteam, e, rbiLeft > 0 ? rbiTo : null, un);
      if (rbiLeft > 0) rbiLeft -= 1;
      scored.push(e.name);
    } else {
      newbases[dest - 1] = e;
    }
  }
  if (batterDest && batterDest >= 4) {
    const e = { name: batterName, resp: cur };
    scoreRun(S, bteam, e, rbiLeft > 0 ? rbiTo : null, false);
    scored.push(batterName);
  } else if (batterDest) {
    newbases[batterDest - 1] = { name: batterName, resp: cur };
  }
  S.bases = newbases;
  if (opts.error) chargeError(S, fldTeam(S), opts.error);
  if (opts.pb) S.woudouts += 1;
  return scored;
}
function chargeError(S, fteam, pos) {
  T(S, fteam).team_errors += 1;
  S.errors_by_pos.push([fteam, pos]);
  S.woudouts += 1;
}
function basesStr(S) { return S.bases.map((x) => (x ? '1' : '-')).join(''); }

/* ----------------------------------------------------------- lookups */
const PRIO = ['HR', 'SO', 'BB', 'HBP', '3B', '2B', '1B'];
function sectionLookupRaw(card, section, hand, pct) {
  const sec = card.sections[section][hand];
  for (const k of PRIO) {
    const r = sec[k];
    if (r && r[0] <= pct && pct <= r[1]) return k;
  }
  return null;
}
function v2BandPct(card, hand, pct, bump) {
  const so = card.sections.TOUGH[hand].SO;
  if (!so) return null;
  if (so[1] < pct && pct <= so[1] + bump) return so[1];
  return null;
}
function outLookup(S, card, pct, batterName, section) {
  const rows = card.out_table;
  for (const row of rows) {
    if (row.range[0] <= pct && pct <= row.range[1]) return row.result;
  }
  const above = rows.filter((r) => r.range[0] > pct);
  const pick = above.length ? above.reduce((a, b) => (a.range[0] <= b.range[0] ? a : b)) : rows[rows.length - 1];
  led(S, 'card_out_hole', batterName + ' ' + section + ' roll ' + pad2(pct) + ' falls in a printed hole on the converted card; out taken from nearest OUT row ' + JSON.stringify(pick.range) + ' (' + pick.result + ')');
  return pick.result;
}
function ballparkSection(G, batterBats, pct) {
  const side = batterBats === 'L' ? 'LHB' : 'RHB';
  const ch = G.park.ballpark_chart[side];
  if (ch.WHEELHOUSE[0] <= pct && pct <= ch.WHEELHOUSE[1]) return 'WHEELHOUSE';
  return 'IN-PLAY';
}

/* ---------------------------------------------------- coach's choice */
function* coachsChoice(G, S, runnerName, runRating, fpos, fteam, leadFromBase) {
  const [frng, fe, farm] = fieldingLine(G, S, fteam, fpos);
  const total = (yield* roll2d6(G, S))[2];
  if (total <= runRating && total <= farm) return [true, false];
  if (total > runRating && total > farm) return [false, true];
  const pct = yield* rollpct(G, S);
  if (pct <= 10) { // DROP?
    const d = yield* roll1d6(G, S);
    if (pct === 0) led(S, 'gap_injury_check', "Coach's Choice DROP? rolled 00: injury check on the fielder receiving the throw cannot be performed (no injury ratings on converted cards)");
    return [d > fe, false];
  }
  if (pct <= 45) return [false, true]; // OUT
  if (pct <= 55) { // WILD?
    const d = yield* roll1d6(G, S);
    if (pct === 55) led(S, 'gap_injury_check', "Coach's Choice WILD? rolled 55: injury check on the outfielder cannot be performed (no injury ratings on converted cards)");
    return [true, null];
  }
  const d = yield* roll1d6(G, S); // SAFE; 1-3 others advance on the throw
  return [true, d <= 3];
}
/* The automated go/stay (the default policy). For the human club the
 * choice is Joe's (Section 7.1): a decision yield replaces the roll,
 * and no 2d6 is consumed. */
function* decideAttempt(G, S, runnerEntry, fromBase) {
  const bteam = batTeam(S);
  if (G.human[bteam]) {
    const ans = yield { decision: { kind: 'send_hold', runner: runnerEntry.name, from: fromBase, to: fromBase + 1 } };
    return !!(ans && ans.go);
  }
  const rn = hcard(G, runnerEntry.name, bteam).run;
  return (yield* roll2d6(G, S))[2] < rn;
}

/* ------------------------------------------------- hit advancement */
function hitLocation(pct, hitType, bats) {
  const d = pct % 10;
  if (hitType === '1B') {
    const m = bats === 'L' ? HITLOC_1B_LHB : HITLOC_1B_RHB;
    return m[d] !== undefined && m[d] !== null ? m[d] : HITLOC_1B[d];
  }
  const m = bats === 'L' ? HITLOC_2B_LHB : HITLOC_2B_RHB;
  return m[d] !== undefined && m[d] !== null ? m[d] : HITLOC_2B[d];
}
function* resolveHit(G, S, batterName, hitType, section, pct, lowD6) {
  const bteam = batTeam(S), fteam = fldTeam(S);
  const bs = bstat(S, bteam, batterName);
  bs.AB += 1; bs.H += 1;
  if (hitType === '2B' || hitType === '3B' || hitType === 'HR') bs[hitType] += 1;
  const ps = pstat(S, fteam, curPitcher(S));
  ps.H += 1;
  if (hitType === 'HR') ps.HR += 1;
  const old = S.bases.slice();
  if (hitType === 'HR') {
    const nRuns = old.filter(Boolean).length + 1;
    applyPlay(S, batterName, 4, { 1: 4, 2: 4, 3: 4 }, { rbiTo: batterName, rbiRuns: nRuns });
    S.hr_log.push(batterName + ' HR (' + S.inning + (S.half === 'top' ? 'T' : 'B') + ')');
    led(S, 'home_run', batterName + ' off ' + curPitcher(S) + ' in the ' + S.inning);
    return batterName + ' homers';
  }
  if (hitType === '3B') {
    const nRuns = old.filter(Boolean).length;
    applyPlay(S, batterName, 3, { 1: 4, 2: 4, 3: 4 }, { rbiTo: batterName, rbiRuns: nRuns });
    return batterName + ' triples, ' + nRuns + ' run(s) score';
  }
  const low = lowD6;
  const twoOuts = S.outs === 2;
  const fpos = hitLocation(pct, hitType, hcard(G, batterName, bteam).bats);
  const dest = {};
  const notes = [];
  if (old[2]) dest[3] = 4;
  let bd;
  if (hitType === '2B') {
    if (old[1]) dest[2] = 4;
    if (old[0]) {
      const e = old[0];
      const rn = hcard(G, e.name, bteam).run;
      if (twoOuts && rn >= 6) dest[1] = 4;
      else {
        const [adv, choice] = ADV_2B_FROM1[low];
        dest[1] = adv === 99 ? 4 : 3;
        if (choice) notes.push(['choice', 1, e, fpos]);
      }
    }
    bd = 2;
  } else {
    if (old[1]) {
      const e = old[1];
      const rn = hcard(G, e.name, bteam).run;
      if (twoOuts && rn >= 6) dest[2] = 4;
      else {
        const [adv, choice] = ADV_1B_FROM2[low];
        dest[2] = adv === 99 ? 4 : 3;
        if (choice) notes.push(['choice', 2, e, fpos]);
      }
    }
    if (old[0]) {
      const e = old[0];
      const rn = hcard(G, e.name, bteam).run;
      if (twoOuts && rn >= 6) dest[1] = 3;
      else {
        const [adv, choice] = ADV_1B_FROM1[low];
        dest[1] = 1 + adv;
        if (choice) notes.push(['choice', 1, e, fpos]);
      }
    }
    bd = 1;
  }
  if (section === 'PATIENT' && old[0] && !old[1] && dest[1] === 2 &&
      !notes.some((n) => n[0] === 'choice' && n[1] === 1)) {
    notes.push(['patient_option', 1, old[0], fpos]);
  }
  const scoredBefore = S.score[bteam];
  applyPlay(S, batterName, bd, dest, { rbiTo: batterName, rbiRuns: 99 });
  void scoredBefore;
  for (const [kind, fromBase, e, fp] of notes) {
    const rnName = e.name;
    let curBase = null;
    S.bases.forEach((ent, i) => { if (ent && ent.name === rnName) curBase = i + 1; });
    if (curBase === null || S.outs >= 3) continue;
    if (kind === 'patient_option') {
      led(S, 'coachs_choice', 'PATIENT hit: lead runner ' + rnName + ' has the extra-base option');
    }
    if (!(yield* decideAttempt(G, S, e, fromBase))) {
      elog(S, '  ' + rnName + ' holds (choice declined by the 2d6 check)');
      continue;
    }
    const target = curBase + 1;
    const [safe, othersAdv] = yield* coachsChoice(G, S, rnName, hcard(G, rnName, bteam).run, fp, fteam, curBase);
    led(S, 'coachs_choice', rnName + ' attempts extra base from ' + curBase + ' vs ' + fp + ' arm: ' + (safe ? 'safe' : 'OUT'));
    const rd = { 1: 0, 2: 0, 3: 0 };
    S.bases.forEach((ent, i) => { if (ent) rd[i + 1] = i + 1; });
    if (safe) {
      rd[curBase] = target;
      if (othersAdv) {
        S.bases.forEach((ent, i) => { if (ent && ent.name !== rnName && rd[i + 1] < 4) rd[i + 1] = rd[i + 1] + 1; });
      }
      applyPlay(S, batterName, 0, rd, {});
    } else {
      rd[curBase] = 0;
      if (othersAdv) {
        S.bases.forEach((ent, i) => { if (ent && ent.name !== rnName && rd[i + 1] < 4) rd[i + 1] = rd[i + 1] + 1; });
      }
      applyPlay(S, batterName, 0, rd, {});
      S.outs += 1;
      S.def_outs[fteam] += 1;
      elog(S, '  ' + rnName + ' thrown out going to ' + target);
    }
  }
  return batterName + ' ' + (hitType === '1B' ? 'singles' : 'doubles') + ' (' + fpos + ' fields it)';
}

/* --------------------------------------------------------- out plays */
function* playAtHome(G, S, runnerEntry, runAdj) {
  const rn = hcard(G, runnerEntry.name, batTeam(S)).run + (runAdj || 0);
  const total = (yield* roll2d6(G, S))[2];
  if (total > rn) return false;
  if (total < rn) return true;
  const pct = yield* rollpct(G, S);
  if (pct <= 49) {
    const d = yield* roll1d6(G, S);
    const [ccard] = fielderCard(G, S, fldTeam(S), 'C');
    if (d > ccard.positions[0].e) {
      chargeError(S, fldTeam(S), 'C');
      elog(S, '  catcher drops the ball (E2) on the play at home');
    }
    return true;
  }
  return false;
}
function* infieldInChart(G, S, batterName) {
  const bteam = batTeam(S), fteam = fldTeam(S);
  const total = (yield* roll2d6(G, S))[2];
  const old = S.bases.slice();
  const loaded = old.every(Boolean);
  if (total <= 5) {
    if (loaded) {
      applyPlay(S, batterName, 0, { 1: 2, 2: 3, 3: 0 }, {});
      S.outs += 2; S.def_outs[fteam] += 2;
      elog(S, '  infield in: runner on 3rd out at home, batter out at 1st (DP)');
    } else {
      const rd = {};
      for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = { 1: 2, 2: 2, 3: 3 }[b];
      applyPlay(S, batterName, 0, rd, {});
      S.outs += 1; S.def_outs[fteam] += 1;
      elog(S, '  infield in: batter out, runners hold/advance per chart');
    }
    return true;
  }
  if (total <= 8) {
    if (loaded) {
      const d10 = yield* roll1d10(G, S);
      const batterOut = d10 > hcard(G, batterName, bteam).run;
      applyPlay(S, batterName, batterOut ? 0 : 1, { 1: 2, 2: 3, 3: 0 }, {});
      S.outs += batterOut ? 2 : 1; S.def_outs[fteam] += batterOut ? 2 : 1;
      elog(S, '  infield in: runner on 3rd out at home' + (batterOut ? ', batter out too (DP)' : ', batter safe'));
    } else {
      const rd = {};
      for (const b of [1, 2]) if (old[b - 1]) rd[b] = b + 1;
      rd[3] = 0;
      applyPlay(S, batterName, 1, rd, {});
      S.outs += 1; S.def_outs[fteam] += 1;
      elog(S, '  infield in: runner on 3rd out at home, batter safe');
    }
    return true;
  }
  if (total <= 10) {
    const rd = {};
    for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = b + 1;
    applyPlay(S, batterName, 1, rd, { rbiTo: batterName, rbiRuns: old[2] ? 1 : 0 });
    elog(S, '  ball sneaks past the drawn-in infield: single');
    bstat(S, bteam, batterName).H += 1;
    pstat(S, fteam, curPitcher(S)).H += 1;
    return true;
  }
  const rd = {};
  for (const b of [1, 2]) if (old[b - 1]) rd[b] = b + 1;
  const safe = yield* playAtHome(G, S, old[2], 0);
  rd[3] = safe ? 4 : 0;
  applyPlay(S, batterName, 1, rd, { rbiTo: batterName, rbiRuns: safe ? 1 : 0 });
  S.outs += safe ? 0 : 1; S.def_outs[fteam] += safe ? 0 : 1;
  elog(S, '  infield in: runner breaks for home and is ' + (safe ? 'safe' : 'out'));
  return true;
}
/* The addendum's ground_out (book p6): the engine's function with the
 * DP check on the LOWER of the batter's printed DP and the pitcher's
 * addendum DP. Chance's Tinker-to-Evers-to-Chance wrapper sits over
 * this (groundOut, below). */
function* groundOutAdd(G, S, batterName, pos, pct, pitcherResult) {
  const bteam = batTeam(S), fteam = fldTeam(S);
  const bs = bstat(S, bteam, batterName);
  bs.AB += 1;
  const old = S.bases.slice();
  if (S.outs === 2) {
    S.outs += 1; S.def_outs[fteam] += 1;
    return 'ground out ' + pos;
  }
  const inn = S.inning;
  const diff = S.score[fteam] - S.score[bteam];
  const infieldIn = !!old[2] && S.outs < 2 && inn >= 7 && diff <= 2 && diff >= -1;
  if (old[2] && S.outs < 2 && ['1B', '2B', '3B', 'SS', 'P', 'C'].includes(pos) && infieldIn) {
    led(S, 'infield_in', fteam + ' infield in, runner on 3rd, ' + S.outs + ' out(s), inning ' + inn);
    if (yield* infieldInChart(G, S, batterName)) return 'ground out ' + pos + ' (infield in)';
  }
  if (old[0] && S.outs < 2) {
    const total = (yield* roll2d6(G, S))[2];
    if (total >= 11) {
      const rd = {};
      for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = b + 1;
      applyPlay(S, batterName, 0, rd, { rbiTo: batterName, rbiRuns: old[2] ? 1 : 0 });
      S.outs += 1; S.def_outs[fteam] += 1;
      elog(S, "  fielder's only play is to 1st; batter out, runners advance");
      return 'ground out ' + pos;
    }
    const batterDp = hcard(G, batterName, bteam).dp;
    const pname = curPitcher(S);
    const pcardNow = pitcherCard(G, S, fteam, pname);
    const pitcherDp = pname === 'EMERGENCY' ? null : (pcardNow.dp != null ? pcardNow.dp : null);
    const dpRating = pitcherDp !== null ? Math.min(batterDp, pitcherDp) : batterDp;
    led(S, 'double_play_check', '2d6=' + total + ' vs DP ' + dpRating + ' (lower of batter ' + batterDp + ' and pitcher ' + pitcherDp + ', book p6, addendum)');
    const ends5 = (pct % 10 === 5);
    if (total <= dpRating) {
      if (old[1] && ['3B', 'SS', 'P'].includes(pos) && ends5) {
        applyPlay(S, batterName, 0, old[2] ? { 1: 2, 2: 0, 3: 4 } : { 1: 2, 2: 0 }, { rbiTo: null });
        elog(S, '  DP: runner from 2nd forced at 3rd, batter out at 1st');
      } else {
        const rd = { 1: 0 };
        if (old[1]) rd[2] = 3;
        if (old[2]) rd[3] = 4;
        applyPlay(S, batterName, 0, rd, {});
        elog(S, '  double play turned');
      }
      bs.GDP += 1;
      S.outs += 2; S.def_outs[fteam] += 2;
      led(S, 'double_play', batterName + ' GIDP to ' + pos);
      return 'GIDP ' + pos;
    }
    if (old[1] && ['SS', '3B'].includes(pos) && ends5) {
      const rd = { 1: 2, 2: 0 };
      if (old[2]) rd[3] = 4;
      applyPlay(S, batterName, 1, rd, {});
      elog(S, '  FC: runner from 2nd out advancing to 3rd, batter safe');
    } else {
      const rd = { 1: 0 };
      if (old[1]) rd[2] = 3;
      if (old[2]) rd[3] = 4;
      applyPlay(S, batterName, 1, rd, {});
      elog(S, "  fielder's choice: runner out at 2nd, batter safe");
    }
    S.outs += 1; S.def_outs[fteam] += 1;
    return "fielder's choice " + pos;
  }
  if (pos === 'P' && (old[1] || old[2])) {
    S.outs += 1; S.def_outs[fteam] += 1;
    elog(S, '  pitcher looks back the lead runner, throws to 1st: batter out, runners hold');
    return 'ground out P';
  }
  const rd = {};
  if (old[2]) {
    if (pos === '2B' || pos === 'SS') {
      const full = {};
      for (const b of [1, 2]) if (old[b - 1]) full[b] = b;
      full[3] = 4;
      applyPlay(S, batterName, 0, full, { rbiTo: batterName, rbiRuns: 1 });
      S.outs += 1; S.def_outs[fteam] += 1;
      elog(S, '  batter out at 1st, runner on 3rd scores on the throw');
      return 'ground out ' + pos + ', run scores';
    }
    if (yield* decideAttempt(G, S, old[2], 3)) {
      const safe = yield* playAtHome(G, S, old[2], -1);
      rd[3] = safe ? 4 : 0;
      const full = {};
      for (const b of [1, 2, 3]) if (old[b - 1]) full[b] = b === 3 ? rd[3] : b;
      // (the Python 'extra' branch here is unreachable: old[1] and not old[2] is false in this block)
      applyPlay(S, batterName, 0, full, { rbiTo: batterName, rbiRuns: safe ? 1 : 0 });
      S.outs += safe ? 1 : 2; S.def_outs[fteam] += safe ? 1 : 2;
      elog(S, '  runner from 3rd ' + (safe ? 'scores' : 'is out at home') + ' on the ground ball to ' + pos);
      return 'ground out ' + pos;
    }
    rd[3] = 3;
  }
  if (old[1]) {
    if (old[2]) rd[2] = 2;
    else if (pos === '1B' || pos === '2B') rd[2] = 3;
    else if (hcard(G, old[1].name, bteam).run >= 7) rd[2] = 3;
    else rd[2] = 2;
  }
  if (old[0]) rd[1] = 1;
  applyPlay(S, batterName, 0, rd, {});
  S.outs += 1; S.def_outs[fteam] += 1;
  return 'ground out ' + pos;
}
function* flyOut(G, S, batterName, pos, pitcherResult) {
  const bteam = batTeam(S), fteam = fldTeam(S);
  bstat(S, bteam, batterName).AB += 1;
  const old = S.bases.slice();
  const deep = ['WHEELHOUSE', 'PATIENT', 'PATIENT-OUT'].includes(pitcherResult);
  const rd = {};
  let scored = 0;
  if (S.outs === 2) {
    const hold = {};
    for (const b of [1, 2, 3]) if (old[b - 1]) hold[b] = b;
    applyPlay(S, batterName, 0, hold, {});
    S.outs += 1; S.def_outs[fteam] += 1;
    return 'fly out ' + pos;
  }
  if (old[2]) {
    const e = old[2];
    let rn = hcard(G, e.name, bteam).run;
    if (pitcherResult === 'TOUGH') rn -= 2;
    if (deep) { rd[3] = 4; scored = 1; }
    else if (rn >= 7) { rd[3] = 4; scored = 1; }
    else {
      if (yield* decideAttempt(G, S, e, 3)) {
        const [safe] = yield* coachsChoice(G, S, e.name, rn, pos, fteam, 3);
        rd[3] = safe ? 4 : 0;
        scored = safe ? 1 : 0;
        if (!safe) {
          S.outs += 1; S.def_outs[fteam] += 1;
          elog(S, '  ' + e.name + ' thrown out at home trying to tag');
        }
      } else rd[3] = 3;
    }
  }
  if (old[1]) {
    const e = old[1];
    let rn = hcard(G, e.name, bteam).run;
    if (pitcherResult === 'TOUGH') rn -= 2;
    if (deep) {
      if (pos === 'RF') rd[2] = 3;
      else if (pos === 'CF') {
        if (rn >= 7) rd[2] = 3;
        else if (yield* decideAttempt(G, S, e, 2)) {
          const [safe] = yield* coachsChoice(G, S, e.name, rn, pos, fteam, 2);
          rd[2] = safe ? 3 : 0;
          if (!safe) { S.outs += 1; S.def_outs[fteam] += 1; }
        }
      } else if (pos === 'LF') {
        const rn2 = rn - 2;
        if ((yield* roll2d6(G, S))[2] < rn2) {
          const [safe] = yield* coachsChoice(G, S, e.name, rn2, pos, fteam, 2);
          rd[2] = safe ? 3 : 0;
          if (!safe) { S.outs += 1; S.def_outs[fteam] += 1; }
        }
      }
      if (!(2 in rd)) rd[2] = 2;
    } else {
      if ((pos === 'CF' || pos === 'RF') && rn >= 7) rd[2] = 3;
      else rd[2] = 2;
    }
  }
  if (old[0]) rd[1] = 1;
  applyPlay(S, batterName, 0, rd, { rbiTo: batterName, rbiRuns: scored });
  if (scored) {
    const bs = bstat(S, bteam, batterName);
    bs.AB -= 1;
    bs.SF = (bs.SF || 0) + 1;
  }
  S.outs += 1; S.def_outs[fteam] += 1;
  return 'fly out ' + pos + (scored ? ', run tags and scores' : '');
}
function* resolveOutCode(G, S, batterName, code, pitcherResult, pct) {
  const posmap = { '1': 'P', '2': 'C', '3': '1B', '4': '2B', '5': '3B', '6': 'SS', '7': 'LF', '8': 'CF', '9': 'RF' };
  const kind = code[0], pos = posmap[code[1]];
  if (kind === 'P' || kind === 'L') {
    bstat(S, batTeam(S), batterName).AB += 1;
    S.outs += 1; S.def_outs[fldTeam(S)] += 1;
    return (kind === 'P' ? 'pop out' : 'line out') + ' ' + pos + ', runners hold';
  }
  if (kind === 'F') return yield* flyOut(G, S, batterName, pos, pitcherResult);
  return yield* groundOut(G, S, batterName, pos, pct, pitcherResult);
}

/* ------------------------------------------------------ defense chain */
/* The G1 stack's defense-numbers wrapper (logging only): one
 * ledger entry per defense resolution, carrying the numbers the
 * chain used. Installed in the G1 stack and in app play
 * (G.defenseNumbers); absent from the Replay A stack. */
function* resolveDefense(G, S, batterName, pitcherResult, initPct) {
  const flipsBefore = S.flips.length;
  const out = yield* resolveDefenseCore(G, S, batterName, pitcherResult, initPct);
  if (G.defenseNumbers && S._defense_summary) {
    const d = S._defense_summary;
    const chain = S.flips.slice(flipsBefore).map((f, i) => '#' + (flipsBefore + i + 1) + ' FAC ' + f.fac_id + ' (' + f.purpose + ')').join('; ');
    const inside = d.bandLo <= d.npct && d.npct <= d.bandHi;
    led(S, 'defense_numbers', 'DEFENSE NUMBERS: init %=' + pad2(initPct) + ' lands in DEF_POS band ' + d.posLo + '-' + d.posHi + ' (' + d.chk + ' on ' + d.pos + '); ' + d.chk + ' check on ' + d.pos + ' (' + d.fielder + '), carded range ' + d.frng + ', error E' + d.fe + ', arm ' + d.farm + '; ' + G.park.name.replace(' Field', '') + ' ' + d.chk + ' band for that grade: ' + pad2(d.bandLo) + '-' + pad2(d.bandHi) + '; chain flips: ' + chain + '; re-roll 2d6=' + d.n2 + ' %=' + pad2(d.npct) + ': ' + pad2(d.npct) + ' is ' + (inside ? 'INSIDE' : 'OUTSIDE') + ' the band (reads ' + d.reads + '); chain outcome ' + out);
  }
  return out;
}
function* resolveDefenseCore(G, S, batterName, pitcherResult, initPct) {
  const bteam = batTeam(S), fteam = fldTeam(S);
  let [chk, pos] = defPos(Math.max(1, initPct));
  if (pitcherResult === 'ERROR') chk = 'ERROR';
  else if (pitcherResult === 'RANGE') { chk = 'RANGE'; if (pos === 'C') pos = 'CF'; }
  const [frng, fe, farm] = fieldingLine(G, S, fteam, pos);
  const n2 = (yield* roll2d6(G, S))[2];
  const npct = yield* rollpct(G, S);
  led(S, 'defense_chain', pitcherResult + ': ' + chk + ' check on ' + pos + ' (' + frng + '/E' + fe + '), re-roll 2d6=' + n2 + ' %=' + pad2(npct));
  let outcome;
  if (chk === 'RANGE') {
    const ch = G.park.range_chart[frng];
    outcome = (ch.HIT[0] <= npct && npct <= ch.HIT[1]) ? 'HIT' : 'OUT';
  } else {
    const ch = G.park.error_chart['E' + fe];
    outcome = (ch.ERR[0] <= npct && npct <= ch.ERR[1]) ? 'ERR' : 'OUT';
  }
  {
    let lo = 1, posLo = 1, posHi = 99;
    for (const [hi] of DEF_POS) { if (initPct <= hi) { posLo = lo; posHi = hi; break; } lo = hi + 1; }
    void posLo;
    const band = chk === 'RANGE' ? G.park.range_chart[frng].HIT : G.park.error_chart['E' + fe].ERR;
    S._defense_summary = { chk: chk, pos: pos, frng: frng, fe: fe, farm: farm,
      fielder: T(S, fteam).field[pos], posLo: lo, posHi: posHi, bandLo: band[0], bandHi: band[1],
      n2: n2, npct: npct, reads: outcome };
  }
  const bs = bstat(S, bteam, batterName);
  const old = S.bases.slice();
  if (outcome === 'HIT') {
    const grp = HIT_G[pos];
    let [htype, rbases] = DEF_HIT[grp][n2];
    if (htype === '2B+') {
      htype = hcard(G, batterName, bteam).run >= 8 ? '3B' : '2B';
    }
    bs.AB += 1; bs.H += 1;
    if (htype === '2B' || htype === '3B') bs[htype] += 1;
    pstat(S, fteam, curPitcher(S)).H += 1;
    const rd = {};
    for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = Math.min(4, b + rbases);
    const nRuns = Object.values(rd).filter((d) => d >= 4).length;
    applyPlay(S, batterName, { '1B': 1, '2B': 2, '3B': 3 }[htype], rd, { rbiTo: batterName, rbiRuns: nRuns });
    elog(S, '  DEFENSE: ball gets by/through ' + pos + ': ' + batterName + ' with a ' + htype + ', runners advance ' + rbases);
    return 'REACH';
  }
  if (outcome === 'ERR') {
    const grp = pos === 'C' ? 'C' : (['LF', 'CF', 'RF'].includes(pos) ? 'OF' : 'INF');
    const ev = DEF_ERR[grp][n2];
    if (ev === 0) {
      elog(S, '  DEFENSE: dropped foul ball, at-bat restarts');
      led(S, 'dropped_foul', pos + ' drops a foul ball');
      return 'RESTART';
    }
    bs.AB += 1;
    if (ev === -1) {
      bs.H += 1;
      pstat(S, fteam, curPitcher(S)).H += 1;
      const rd = {};
      for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = Math.min(4, b + 1);
      const nRuns = Object.values(rd).filter((d) => d >= 4).length;
      applyPlay(S, batterName, 1, rd, { rbiTo: batterName, rbiRuns: nRuns });
      const rd2 = {};
      const scorers = [];
      S.bases.forEach((e, i) => { if (e) { rd2[i + 1] = Math.min(4, i + 2); if (rd2[i + 1] >= 4) scorers.push(e.name); } });
      applyPlay(S, batterName, 0, rd2, { unearnedRunners: scorers });
      chargeError(S, fteam, pos);
      elog(S, '  DEFENSE: single plus error on ' + pos);
      led(S, 'defense_error', 'SINGLE + error charged to ' + pos);
      return 'REACH';
    }
    const rd = {};
    for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = Math.min(4, b + ev);
    const un = old.filter((e, i) => e && rd[i + 1] >= 4).map((e) => e.name);
    applyPlay(S, batterName, Math.min(3, ev), rd, { unearnedRunners: un, error: pos });
    elog(S, '  DEFENSE: ' + ev + '-base error on ' + pos + ', batter reaches');
    led(S, 'defense_error', ev + '-base error charged to ' + pos);
    return 'REACH';
  }
  const grp = pos === 'C' ? 'C' : (['LF', 'CF', 'RF'].includes(pos) ? 'OF' : 'INF');
  const kind = DEF_OUT[grp][n2];
  bs.AB += 1;
  elog(S, '  DEFENSE: ' + pos + ' converts it: ' + kind);
  led(S, 'defense_out', kind + ' at ' + pos);
  if (kind === 'Popout' || kind === 'PopoutF' || kind === 'Lineout') {
    S.outs += 1; S.def_outs[fteam] += 1;
    return 'OUT';
  }
  if (kind === 'Lineout-DP') {
    S.outs += 1; S.def_outs[fteam] += 1;
    if ((frng === 'A' || frng === 'B') && old.some(Boolean)) {
      const lead = Math.max(...[1, 2, 3].filter((b) => old[b - 1]));
      const rd = {};
      for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = b;
      rd[lead] = 0;
      applyPlay(S, batterName, 0, rd, {});
      S.outs += 1; S.def_outs[fteam] += 1;
      elog(S, '  line drive DP: closest runner doubled off');
    }
    return 'OUT';
  }
  if (kind === 'GB+adv') {
    const rd = {};
    for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = Math.min(4, b + 1);
    applyPlay(S, batterName, 0, rd, { rbiTo: batterName, rbiRuns: old[2] ? 1 : 0 });
    S.outs += 1; S.def_outs[fteam] += 1;
    return 'OUT';
  }
  if (kind === 'GB-fc') {
    const occ = [1, 2, 3].filter((b) => old[b - 1]);
    const forced = occ.includes(1) ? 1 : null; // the '2 in occ and False' branch is dead in the source, kept dead
    if (forced) {
      const rd = {};
      for (const b of occ) rd[b] = b === forced ? 0 : b + 1;
      applyPlay(S, batterName, 1, rd, {});
      elog(S, '  GB-fc: lead runner forced out, batter safe');
    } else {
      elog(S, '  GB-fc with no force: batter out at 1st');
    }
    S.outs += 1; S.def_outs[fteam] += 1;
    return 'OUT';
  }
  if (kind === 'GB-DP-A' || kind === 'GB-DP-AB') {
    if (old[0]) {
      const rd = {};
      for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = b;
      rd[1] = 0;
      applyPlay(S, batterName, 0, rd, {});
      S.outs += 1; S.def_outs[fteam] += 1;
      const good = frng === 'A' || (kind === 'GB-DP-AB' && frng === 'B');
      if (good && S.outs < 3) {
        S.outs += 1; S.def_outs[fteam] += 1;
        elog(S, '  GB-DP completed: batter out at 1st too');
        led(S, 'double_play', 'defense-chart DP at ' + pos);
      } else {
        if (!S.bases[0]) S.bases[0] = { name: batterName, resp: curPitcher(S) };
        elog(S, '  GB-DP: runner out at 2nd, batter beats the throw');
      }
      return 'OUT';
    }
    S.outs += 1; S.def_outs[fteam] += 1;
    return 'OUT';
  }
  if (kind === 'ShortFly') {
    S.outs += 1; S.def_outs[fteam] += 1;
    if (old[2] && S.outs < 3) {
      const e = old[2];
      const rn = hcard(G, e.name, bteam).run - 2;
      const [safe] = yield* coachsChoice(G, S, e.name, rn, pos, fteam, 3);
      const rd = {};
      for (const b of [1, 2]) if (old[b - 1]) rd[b] = b;
      rd[3] = safe ? 4 : 0;
      applyPlay(S, batterName, 0, rd, { rbiTo: batterName, rbiRuns: safe ? 1 : 0 });
      if (safe) { bs.AB -= 1; bs.SF = (bs.SF || 0) + 1; }
      if (!safe) { S.outs += 1; S.def_outs[fteam] += 1; }
      elog(S, '  short fly: runner on 3rd ' + (safe ? 'scores' : 'thrown out at home'));
      led(S, 'coachs_choice', 'tag attempt on short fly: ' + (safe ? 'safe' : 'out'));
    }
    return 'OUT';
  }
  if (kind === 'ShortFlyDP') {
    S.outs += 1; S.def_outs[fteam] += 1;
    if (farm <= 5 && old.some(Boolean) && S.outs < 3) {
      const lead = Math.max(...[1, 2, 3].filter((b) => old[b - 1]));
      const rd = {};
      for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = b;
      rd[lead] = 0;
      applyPlay(S, batterName, 0, rd, {});
      S.outs += 1; S.def_outs[fteam] += 1;
      elog(S, '  short fly DP: lead runner thrown out by the outfielder (arm <= 5)');
      led(S, 'double_play', 'short fly DP');
    }
    return 'OUT';
  }
  if (kind === 'DeepFly') {
    S.outs += 1; S.def_outs[fteam] += 1;
    const rd = {};
    for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = b;
    let rbi = 0;
    for (const b of [3, 2]) {
      if (old[b - 1]) {
        const e = old[b - 1];
        const rn = hcard(G, e.name, bteam).run;
        if (rn >= 6) { rd[b] = b + 1; if (b === 3) rbi = 1; }
        else if (yield* decideAttempt(G, S, e, b)) {
          const [safe] = yield* coachsChoice(G, S, e.name, rn, pos, fteam, b);
          rd[b] = safe ? b + 1 : 0;
          if (safe && b === 3) rbi = 1;
          if (!safe) { S.outs += 1; S.def_outs[fteam] += 1; }
        }
      }
    }
    applyPlay(S, batterName, 0, rd, { rbiTo: batterName, rbiRuns: rbi });
    if (rbi) { bs.AB -= 1; bs.SF = (bs.SF || 0) + 1; }
    return 'OUT';
  }
  S.outs += 1; S.def_outs[fteam] += 1;
  return 'OUT';
}

/* ------------------------------------------------------------ stealing */
function* attemptSteal(G, S, runnerEntry, target, nextBatterBats) {
  const bteam = batTeam(S), fteam = fldTeam(S);
  const name = runnerEntry.name;
  const card = hcard(G, name, bteam);
  const letter = card.steal.rating;
  const fromBase = S.bases.findIndex((e) => e && e.name === name) + 1;
  let clo, slo, combo;
  if (target === 4) { [clo, slo] = STEAL_HOME[letter]; combo = letter + ' (home)'; }
  else { const arm = catcherArm(G, S, fteam); combo = letter + arm; [clo, slo] = STEAL_COL[combo]; }
  const pct = yield* rollpct(G, S);
  const bs = bstat(S, bteam, name);
  led(S, 'steal_attempt', name + ' attempts ' + target + ' (' + combo + '), %=' + pad2(pct));
  if (pct <= 2) { // DROP?
    let cover;
    if (target === 2) cover = nextBatterBats === 'L' ? 'SS' : '2B';
    else if (target === 3) cover = '3B';
    else cover = 'C';
    const [, ce] = fieldingLine(G, S, fteam, cover);
    const d = yield* roll1d6(G, S);
    if (d > ce) {
      chargeError(S, fteam, cover);
      S.bases[fromBase - 1] = null;
      S.bases[target - 1] = runnerEntry;
      bs.SB += 1;
      elog(S, '  DROP?: ' + cover + ' drops the throw (E), ' + name + ' safe at ' + target);
      return 'safe';
    }
    bs.CS += 1;
    S.bases[fromBase - 1] = null;
    S.outs += 1; S.def_outs[fteam] += 1;
    elog(S, '  DROP?: ' + cover + ' hangs on, ' + name + ' is OUT');
    return 'caught';
  }
  if (pct <= 12) { // SB+E2?
    bs.SB += 1;
    S.bases[fromBase - 1] = null;
    if (target >= 4) {
      scoreRun(S, bteam, runnerEntry, null, false);
      elog(S, '  SB+E2?: ' + name + ' steals home');
      return 'safe';
    }
    S.bases[target - 1] = runnerEntry;
    const [ccard] = fielderCard(G, S, fteam, 'C');
    const d = yield* roll1d6(G, S);
    if (d > ccard.positions[0].e) {
      chargeError(S, fteam, 'C');
      const rd = {};
      const scorers = [];
      S.bases.forEach((e, i) => { if (e) { rd[i + 1] = Math.min(4, i + 2); if (rd[i + 1] >= 4) scorers.push(e.name); } });
      applyPlay(S, name, 0, rd, { unearnedRunners: scorers });
      elog(S, '  SB+E2?: throw sails into the outfield (E2), runners advance');
    } else {
      elog(S, '  SB+E2?: ' + name + ' safe at ' + target + ', throw on target but late');
    }
    return 'safe';
  }
  if (clo <= pct && pct < slo) {
    bs.CS += 1;
    S.bases[fromBase - 1] = null;
    S.outs += 1; S.def_outs[fteam] += 1;
    elog(S, '  caught stealing: ' + name + ' out at ' + target);
    return 'caught';
  }
  bs.SB += 1;
  S.bases[fromBase - 1] = null;
  if (target >= 4) scoreRun(S, bteam, runnerEntry, null, false);
  else S.bases[target - 1] = runnerEntry;
  elog(S, '  ' + name + ' steals ' + target + ' safely');
  return 'safe';
}
function* autoStealCheck(G, S, batterName, lastTotal, lastDice) {
  if (S.outs >= 3 || S.final) return;
  let ent = null, base = null;
  S.bases.forEach((e, i) => { if (e && e.name === batterName) { ent = e; base = i + 1; } });
  if (!ent || base === 3) return;
  const target = base + 1;
  if (S.bases[target - 1] !== null) return;
  if (S.outs === 2 && S.bases[2] !== null) {
    elog(S, '  auto-steal: ' + batterName + ' has the jump but is held (2 outs, runner on 3rd)');
    led(S, 'steal_held', batterName + ' held with 2 outs and a runner on 3rd');
    return;
  }
  const card = hcard(G, batterName, batTeam(S));
  const jump = card.steal.jump;
  if (jump === null || jump === undefined) return;
  const key = batTeam(S) + ':' + batterName;
  let effJump = jump;
  if (card.steal.jump_mod === '+') effJump = !(key in S.steal_checked) ? jump + 1 : jump;
  if (card.steal.jump_mod === '-') effJump = !(key in S.steal_checked) ? jump - 1 : jump;
  if (jump === 1) {
    if (key in S.jump1_used) return;
    effJump = 2;
    S.jump1_used[key] = true;
  }
  S.steal_checked[key] = true;
  if (lastTotal === 12) {
    led(S, 'gap_pickoff', "Auto-steal jump check rolled 12: Pick Off chart needs the pitcher's Hold rating, which the converted cards do not carry; no pickoff attempted");
    if (S._pickoff_owed) { // the addendum intercepts this site, synchronously
      S._pickoff_owed = false;
      yield* resolvePickoff(G, S);
    }
    return;
  }
  if (lastTotal <= effJump) {
    if (target === 3 && lastDice[0] !== lastDice[1]) {
      elog(S, '  auto-steal: ' + batterName + ' would go but stealing 3rd needs doubles on the 2d6');
      return;
    }
    const tm = T(S, batTeam(S));
    const nxt = tm.order[tm.next_idx].name;
    const nbats = hcard(G, nxt, batTeam(S)).bats;
    yield* attemptSteal(G, S, ent, target, nbats);
  }
}

/* ------------------------------------------- addendum: WP / pickoff */
function applyWP(G, S, n) {
  const bteam = batTeam(S);
  const pname = curPitcher(S);
  led(S, 'addendum_wild_pitch', pname + ' wild pitch #' + n + ' of the PA (addendum WP rating, book p10); runners advance one base');
  elog(S, '  WILD PITCH by ' + pname + ' (book p10, addendum WP rating): all runners advance one base');
  const ps = pstat(S, fldTeam(S), pname);
  ps.WP = (ps.WP || 0) + 1;
  const old = S.bases.slice();
  if (old[2]) scoreRun(S, bteam, old[2], null, false);
  S.bases = [null, old[0], old[1]];
}
const PICKOFF_CHART = { '1-3': [6, 7, 34, 95, 96], '4-5': [7, 8, 27, 96, 97], '6-7': [8, 9, 21, 97, 98], '8-9': [8, 9, 16, 98, 99], '10': [8, 9, 12, 98, 99] };
function holdBand(hold) {
  if (hold <= 3) return '1-3';
  if (hold <= 5) return '4-5';
  if (hold <= 7) return '6-7';
  if (hold <= 9) return '8-9';
  return '10';
}
function pickoffRunner(S) {
  for (const b of [2, 1]) {
    const e = S.bases[b - 1];
    if (e && ((b === 2 && S.bases[2] === null) || (b === 1 && S.bases[1] === null))) return [b, e];
  }
  for (const b of [2, 1]) if (S.bases[b - 1]) return [b, S.bases[b - 1]];
  return [null, null];
}
function* resolvePickoff(G, S) {
  const fteam = fldTeam(S), bteam = batTeam(S);
  const pname = curPitcher(S);
  const pcardNow = pitcherCard(G, S, fteam, pname);
  const hold = pname === 'EMERGENCY' || pcardNow.hold == null ? 7 : pcardNow.hold;
  const band = holdBand(hold);
  const [wildHi, cLo, cHi, sHi, balkLo] = PICKOFF_CHART[band];
  void sHi;
  const [base, ent] = pickoffRunner(S);
  if (!ent) return null;
  const pct = yield* rollpct(G, S);
  const who = ent.name + ' (on ' + base + ') vs ' + pname + ' (Hold ' + hold + ', band ' + band + '), %=' + pad2(pct);
  if (pct <= wildHi) {
    const [, pe] = fieldingLine(G, S, fteam, 'P');
    const d = yield* roll1d6(G, S);
    if (d <= pe) {
      led(S, 'addendum_pickoff', "WILD? " + who + ": 1d6=" + d + " <= pitcher's E " + pe + '; throw on target but late, runner back safely');
      elog(S, '  PICK OFF WILD?: throw is on target but late; ' + ent.name + ' back safely');
      return 'wild_on_target';
    }
    const [a, b] = yield* roll2d6(G, S);
    const errPos = (a === 3 || b === 3) ? '1B' : 'P';
    const adv = a === b ? 2 : 1;
    chargeError(S, fteam, errPos);
    const rd = {};
    S.bases.forEach((e, i) => { if (e) rd[i + 1] = Math.min(4, i + 1 + adv); });
    applyPlay(S, ent.name, 0, rd, {});
    led(S, 'addendum_pickoff', 'WILD? ' + who + ': 1d6=' + d + ' > E ' + pe + '; throw gets past the base (E' + errPos + '), runners advance ' + adv);
    elog(S, '  PICK OFF WILD?: throw gets away (error, ' + errPos + '); all runners advance ' + adv + ' base(s)');
    return 'wild_error';
  }
  if (cLo <= pct && pct <= cHi) {
    S.bases[base - 1] = null;
    S.outs += 1; S.def_outs[fteam] += 1;
    const bs = bstat(S, bteam, ent.name);
    bs.PO = (bs.PO || 0) + 1;
    led(S, 'addendum_pickoff', 'CAUGHT: ' + who);
    elog(S, '  PICKED OFF: ' + ent.name + ' is caught off ' + base + ' by ' + pname + ' (book p18)');
    return 'caught';
  }
  if (pct >= balkLo) {
    const rd = {};
    S.bases.forEach((e, i) => { if (e) rd[i + 1] = Math.min(4, i + 2); });
    applyPlay(S, ent.name, 0, rd, {});
    led(S, 'addendum_pickoff', 'BALK: ' + who);
    elog(S, '  BALK on ' + pname + ' during the pickoff move (book p18); all runners advance one base');
    return 'balk';
  }
  led(S, 'addendum_pickoff', 'SAFE: ' + who + '; runner back safely, no steal attempt');
  elog(S, '  pickoff move on ' + ent.name + ': he gets back safely (book p18)');
  return 'safe';
}
const INJURY_CHART = {
  Prone: [[10, 'ok'], [15, 'game'], [20, 'g1'], [30, 'g1d6'], [50, 'g10'], [75, 'g20'], [89, 'g50'], [99, 'season']],
  Normal: [[30, 'ok'], [50, 'game'], [65, 'g1'], [88, 'g1d6'], [99, 'g10']],
  Durable: [[69, 'ok'], [84, 'game'], [94, 'g1'], [99, 'g1d6']],
  Iron: [[69, 'ok'], [89, 'game'], [99, 'g1']],
};
const INJURY_TEXT = { ok: 'player okay, no injury', game: 'injured, remainder of the game', g1: 'injured, remainder of the game + 1 game', g1d6: 'injured, remainder of the game + 1d6 games', g10: 'injured, remainder of the game + 10 games', g20: 'injured, remainder of the game + 20 games', g50: 'injured, remainder of the game + 50 games', season: 'injured, remainder of the season' };
function* injuryCheck(G, S, name, team, cause) {
  const pcardNow = name === 'EMERGENCY' ? null : pitcherCard(G, S, team, name);
  if (!pcardNow || pcardNow.inj == null) {
    led(S, 'gap_injury_check', 'addendum: injury check on ' + name + ' (' + cause + ') cannot be performed; no Inj rating in the addendum for him');
    return null;
  }
  const grade = pcardNow.inj;
  const pct = yield* rollpct(G, S);
  const outcome = INJURY_CHART[grade].find(([hi]) => pct <= hi)[1];
  let games = null;
  if (outcome === 'g1d6') games = yield* roll1d6(G, S);
  else if (outcome === 'g1') games = 1;
  else if (['g10', 'g20', 'g50'].includes(outcome)) games = parseInt(outcome.slice(1), 10);
  const result = { player: name, team: team, grade: grade, pct: pct, outcome: outcome, games_missed: games, cause: cause, removed_from_game: outcome !== 'ok' };
  led(S, 'addendum_injury_check', name + ' (' + grade + ') injury check (' + cause + '): %=' + pad2(pct) + ' -> ' + INJURY_TEXT[outcome] + (games ? ' (' + games + ' additional games)' : ''));
  elog(S, '  INJURY CHECK on ' + name + ' (' + cause + '): ' + INJURY_TEXT[outcome] + ' (Inj ' + grade + ', %=' + pad2(pct) + ')');
  (S.addendum_injuries || (S.addendum_injuries = [])).push(result);
  if (outcome !== 'ok') {
    const tm = T(S, team);
    if (!tm.removed.includes(name)) tm.removed.push(name);
    for (const slot of tm.order) if (slot.name === name) slot.in_game = false;
    if (tm.field.P === name) {
      S.flags.addendum_pitcher_injured_out = { team: team, name: name, outcome: outcome };
      led(S, 'addendum_injury_removal', name + ' is removed injured (' + cause + '); the replacement is a managerial decision above this layer');
      elog(S, '  ' + name + ' is removed from the game (injury). A replacement must be named by the decision layer.');
    }
  }
  return result;
}

/* --------------------------------------------------------------- bunts */
const BUNT_FIELDER = { 1: 'P', 4: 'P', 2: 'C', 6: 'C', 3: '1B', 5: '3B' };
function* resolveBuntBody(G, S, batterName, squeeze) {
  const bteam = batTeam(S), fteam = fldTeam(S);
  const card = hcard(G, batterName, bteam);
  const letter = squeeze ? 'D' : card.sac_bunt;
  const bs = bstat(S, bteam, batterName);
  pstat(S, fteam, curPitcher(S)).BF += 1;
  led(S, 'sac_bunt_attempt', batterName + ' bunts (' + (squeeze ? 'squeeze, column D' : 'letter ' + letter) + ')');
  let misses = 0;
  while (true) {
    const [, , tot2] = yield* roll2d6(G, S);
    const fdie = yield* roll1d6(G, S);
    const fpos = BUNT_FIELDER[fdie];
    const pct = yield* rollpct(G, S);
    let res = BUNT[letter].find((x) => x[0] <= pct && pct <= x[1])[2];
    elog(S, '  bunt: fielder ' + fpos + ', %=' + pad2(pct) + ' -> ' + res);
    const old = S.bases.slice();
    if (res === 'MISS') {
      misses += 1;
      if (misses >= 2) {
        bs.AB += 1; bs.SO += 1;
        pstat(S, fteam, curPitcher(S)).SO += 1;
        S.outs += 1; S.def_outs[fteam] += 1;
        elog(S, '  second MISS: batter strikes out');
        return;
      }
      elog(S, '  MISS: batter misses the pitch, bunt stays on');
      continue;
    }
    if (res === 'PO') {
      bs.AB += 1;
      if (squeeze && old[2]) {
        const rd = {};
        for (const b of [1, 2]) if (old[b - 1]) rd[b] = b;
        rd[3] = 0;
        applyPlay(S, batterName, 0, rd, {});
        S.outs += 2; S.def_outs[fteam] += 2;
        elog(S, '  bunt popped out; runner on 3rd also out (squeeze DP)');
      } else {
        S.outs += 1; S.def_outs[fteam] += 1;
        elog(S, '  bunt popped out, runners hold');
      }
      return;
    }
    if (res === 'DP') {
      if (old[0]) {
        bs.AB += 1;
        const rd = {};
        for (const b of [2, 3]) if (old[b - 1]) rd[b] = b + 1;
        rd[1] = 0;
        applyPlay(S, batterName, 0, rd, {});
        bs.GDP += 1;
        S.outs += 2; S.def_outs[fteam] += 2;
        elog(S, '  bunt DP: lead runner and batter out');
        return;
      }
      res = 'LEAD';
    }
    if (res === 'LEAD') {
      bs.SH += 1;
      const lead = Math.max(...[1, 2, 3].filter((b) => old[b - 1]));
      const rd = {};
      for (const b of [1, 2, 3]) if (old[b - 1] && b !== lead) rd[b] = b + 1;
      rd[lead] = 0;
      applyPlay(S, batterName, 1, rd, {});
      S.outs += 1; S.def_outs[fteam] += 1;
      elog(S, '  bunt: lead runner thrown out, batter safe');
      return;
    }
    if (res === 'E?') {
      const [, fe] = fieldingLine(G, S, fteam, fpos);
      const d = yield* roll1d6(G, S);
      if (d > fe) {
        bs.AB += 1;
        const rd = {};
        for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = Math.min(4, b + 1);
        const un = old.filter((e, i) => e && rd[i + 1] >= 4).map((e) => e.name);
        applyPlay(S, batterName, 1, rd, { unearnedRunners: un, error: fpos });
        elog(S, '  bunt: error on ' + fpos + ', batter safe, runners advance');
        led(S, 'defense_error', 'bunt error charged to ' + fpos);
        return;
      }
      res = 'SH';
    }
    if (res === 'SH') {
      if (squeeze && old[2]) {
        const rn = hcard(G, old[2].name, bteam).run;
        if (tot2 <= rn) {
          const rd = {};
          for (const b of [1, 2]) if (old[b - 1]) rd[b] = b + 1;
          rd[3] = 4;
          applyPlay(S, batterName, 1, rd, { rbiTo: batterName, rbiRuns: 1 });
          bs.SH += 1;
          elog(S, '  squeeze works: runner scores, batter safe at 1st');
          return;
        }
        // The failed squeeze: booked as an at-bat by the engines
        // today; Joe has not ruled on it (spec 6.1.10 named seam).
        bs.AB += 1;
        S.flags.unruled_failed_squeeze = true;
        const rd = {};
        for (const b of [1, 2]) if (old[b - 1]) rd[b] = b + 1;
        rd[3] = 0;
        applyPlay(S, batterName, 1, rd, {});
        S.outs += 1; S.def_outs[fteam] += 1;
        elog(S, '  squeeze: runner out at home (LEAD result), batter safe [unruled case: booked as an at-bat, as the engines book it]');
        return;
      }
      bs.SH += 1;
      const rd = {};
      for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = b + 1;
      applyPlay(S, batterName, 0, rd, { rbiTo: batterName, rbiRuns: old[2] ? 1 : 0 });
      S.outs += 1; S.def_outs[fteam] += 1;
      elog(S, '  sacrifice works: batter out at 1st, runners advance');
      return;
    }
  }
}
/* The G1 stack's bunt-grade overlay (Joe, 2026-10-25): while a bunt
 * resolves, the batter's sac_bunt is temporarily his official grade
 * where bunt_grades.json carries one. Installed in the G1 stack and
 * in app play; NOT installed in the Replay A stack. */
function* resolveBunt(G, S, batterName, squeeze) {
  if (!squeeze && G.buntOverlay) {
    const bteam = batTeam(S);
    const card = hcard(G, batterName, bteam);
    const grade = PlayData.data.bunt_grades[batterName];
    if (grade && grade !== card.sac_bunt) {
      const printed = card.sac_bunt;
      card.sac_bunt = grade;
      led(S, 'bunt_overlay_applied', batterName + ': bunt grade ' + grade + ' by the official printed grade (bunt_grades.json) (governing card prints ' + printed + ')');
      try {
        yield* resolveBuntBody(G, S, batterName, squeeze);
      } finally {
        card.sac_bunt = printed;
      }
      return;
    }
  }
  yield* resolveBuntBody(G, S, batterName, squeeze);
}

/* ============================================================
 * PART 4: pitching management, substitution, the layered
 * wrappers (fatigue book, Williams traits, Chance), the PA
 * body, and the game driver.
 * ========================================================== */
function currentBatter(S) {
  const tm = T(S, batTeam(S));
  const slot = tm.order[tm.next_idx];
  return [slot.name, tm.next_idx];
}
function advanceOrder(S) {
  const tm = T(S, batTeam(S));
  tm.next_idx = (tm.next_idx + 1) % tm.order.length;
}
function applyWalk(G, S, batterName, kind) {
  const bteam = batTeam(S), fteam = fldTeam(S);
  const bs = bstat(S, bteam, batterName);
  const ps = pstat(S, fteam, curPitcher(S));
  if (kind === 'BB') { bs.BB += 1; ps.BB += 1; }
  else { bs.HBP += 1; ps.HBP = (ps.HBP || 0) + 1; }
  const old = S.bases.slice();
  const rd = {};
  if (old[0]) {
    rd[1] = 2;
    if (old[1]) {
      rd[2] = 3;
      if (old[2]) rd[3] = 4;
    }
  }
  if (old[1] && !old[0]) rd[2] = 2;
  if (old[2] && !(old[0] && old[1])) rd[3] = 3;
  applyPlay(S, batterName, 1, rd, { rbiTo: batterName, rbiRuns: (old[0] && old[1] && old[2]) ? 1 : 0 });
  elog(S, '  ' + batterName + (kind === 'BB' ? ' walks' : ' is hit by a pitch'));
}
function* applySo(G, S, batterName, hnrRunner) {
  const bteam = batTeam(S), fteam = fldTeam(S);
  const bs = bstat(S, bteam, batterName);
  bs.AB += 1; bs.SO += 1;
  const ps = pstat(S, fteam, curPitcher(S));
  ps.SO += 1;
  S.outs += 1; S.def_outs[fteam] += 1;
  elog(S, '  ' + batterName + ' strikes out');
  if (hnrRunner != null && S.outs < 3) {
    let ent = null;
    for (const e of S.bases) if (e && e.name === hnrRunner) ent = e;
    if (ent !== null) {
      elog(S, '  hit and run: the lead runner must attempt to steal');
      yield* attemptSteal(G, S, ent, 2, hcard(G, batterName, bteam).bats);
    }
  }
}
function hnrHit(G, S, batterName, hitType, pct) {
  const bteam = batTeam(S), fteam = fldTeam(S);
  const bs = bstat(S, bteam, batterName);
  bs.AB += 1; bs.H += 1;
  if (hitType === '2B' || hitType === '3B' || hitType === 'HR') bs[hitType] += 1;
  pstat(S, fteam, curPitcher(S)).H += 1;
  const old = S.bases.slice();
  if (hitType === '1B') {
    const fpos = hitLocation(pct, '1B', hcard(G, batterName, bteam).bats);
    const farm = fieldingLine(G, S, fteam, fpos)[2];
    const rd = {};
    if (old[2]) rd[3] = 4;
    if (old[1]) rd[2] = 4;
    if (old[0]) {
      const rn = hcard(G, old[0].name, bteam).run;
      rd[1] = (rn >= 7 && farm >= 8) ? 4 : 3;
    }
    const nRuns = Object.values(rd).filter((d) => d >= 4).length;
    applyPlay(S, batterName, 1, rd, { rbiTo: batterName, rbiRuns: nRuns });
  } else if (hitType === '2B') {
    const rd = {};
    for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = 4;
    applyPlay(S, batterName, 2, rd, { rbiTo: batterName, rbiRuns: Object.values(rd).filter((d) => d >= 4).length });
  } else {
    const rd = {};
    for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = 4;
    applyPlay(S, batterName, hitType === '3B' ? 3 : 4, rd, { rbiTo: batterName, rbiRuns: old.filter(Boolean).length + (hitType === 'HR' ? 1 : 0) });
  }
  elog(S, '  hit and run: ' + batterName + ' with a ' + hitType + ', runners take the extra base');
}
function* hnrGroundOut(G, S, batterName) {
  const bteam = batTeam(S), fteam = fldTeam(S);
  bstat(S, bteam, batterName).AB += 1;
  const old = S.bases.slice();
  const total = (yield* roll2d6(G, S))[2];
  led(S, 'hit_and_run', 'ground ball on the hit and run, chart roll ' + total);
  if (total <= 3) {
    const rd = {};
    for (const b of [2, 3]) if (old[b - 1]) rd[b] = b;
    rd[1] = 0;
    applyPlay(S, batterName, 0, rd, {});
    S.outs += 2; S.def_outs[fteam] += 2;
    elog(S, '  hit and run ground ball: DOUBLE PLAY');
  } else if (total <= 10) {
    const rd = {};
    for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = Math.min(4, b + 1);
    applyPlay(S, batterName, 0, rd, { rbiTo: batterName, rbiRuns: old[2] ? 1 : 0 });
    S.outs += 1; S.def_outs[fteam] += 1;
    elog(S, '  hit and run: batter out at 1st, runners advance');
  } else {
    const rd = {};
    for (const b of [2, 3]) if (old[b - 1]) rd[b] = b + 1;
    rd[1] = 0;
    applyPlay(S, batterName, 1, rd, {});
    S.outs += 1; S.def_outs[fteam] += 1;
    elog(S, '  hit and run: runner forced at 2nd, batter safe');
  }
}

/* ------------------------------------------------- pitching changes */
function pickReliever(G, S, fteam, want) {
  const tm = T(S, fteam);
  for (const name of tm.pen) {
    if (G.penRole[fteam][name] === want) return name;
  }
  return tm.pen.length ? tm.pen[0] : 'EMERGENCY';
}
function changePitcherRaw(G, S, fteam, newName) {
  const tm = T(S, fteam);
  const old = tm.pitcher;
  for (const sp of S.pitcher_spans) {
    if (sp.team === fteam && sp.name === old && sp.end === null) {
      sp.end = [S.inning, S.half, S.def_outs[fteam]];
    }
  }
  tm.pitcher = newName;
  tm.field.P = newName;
  const i = tm.pen.indexOf(newName);
  if (i >= 0) tm.pen.splice(i, 1);
  const ps = pstat(S, fteam, newName);
  ps.entered_inning = S.inning;
  S.pitcher_spans.push({ team: fteam, name: newName, start: [S.inning, S.half, S.def_outs[fteam]], end: null });
  elog(S, 'Pitching change (' + TEAMNAME[fteam] + '): ' + newName + ' replaces ' + old);
}
/* traits2's change_pitcher wrapper: the Fireman entry can
 * displace a policy pick (never the closer branch's shape), and
 * an armed fireman lifted unused expires. McGraw's ace branch is
 * dead in this fixture (his club is not in it). traits5 delegates. */
function changePitcher(G, S, fteam, want) {
  const fl = S.flags;
  const outgoing = T(S, fteam).pitcher;
  let pick = pickReliever(G, S, fteam, want);
  if (masterOn(S)) {
    if (fl.v2_fireman_armed && fl.v2_fireman_armed === outgoing) {
      led(S, 'v2_fireman_arm_expired', outgoing + ' is lifted before his first WHEELHOUSE read; the Fireman arm expires unused');
      fl.v2_fireman_armed = null;
    }
    const closerShape = (() => {
      if (S.inning < 9 || outgoing !== G.starters[fteam]) return false;
      const lead = S.score[fteam] - S.score[batTeam(S)];
      if (!(lead >= 1 && lead <= 3)) return false;
      let realOuts = null;
      for (const sp of S.pitcher_spans) {
        if (sp.team === fteam && sp.name === outgoing && sp.end === null) realOuts = S.def_outs[fteam] - sp.start[2];
      }
      return realOuts !== null && realOuts >= 21;
    })();
    if (!closerShape && fteam === 'OPP') {
      const midInning = fl.v2_half_seen === S.inning + ':' + S.half;
      const risp = !!(S.bases[1] || S.bases[2]);
      if (midInning && risp && S.inning >= 6) {
        led(S, 'v2_fireman_opportunity', 'Dick Williams considers the Fireman with runners in scoring position in the ' + S.inning + 'th');
        const diff = S.score[fteam] - S.score[batTeam(S)];
        if (!fl.v2_fireman_used && diff >= -3 && diff <= 3) {
          let cand = null;
          for (const role of ROLE_PRIORITY) {
            for (const name of T(S, fteam).pen) {
              if (G.penRole[fteam][name] === role) { cand = name; break; }
            }
            if (cand) break;
          }
          if (cand && cand !== outgoing) {
            fl.v2_fireman_used = true;
            fl.v2_fireman_armed = cand;
            led(S, 'v2_fireman_entry', cand + ' enters as the Fireman (first WHEELHOUSE read against him converts to PATIENT)');
            elog(S, '  Dick Williams goes to his Fireman: ' + cand);
            pick = cand;
          }
        }
      }
    }
  }
  if (pick !== outgoing) changePitcherRaw(G, S, fteam, pick);
  return pick;
}
function maybeHook(G, S) {
  const fteam = fldTeam(S);
  const tm = T(S, fteam);
  const cur = tm.pitcher;
  if (cur === 'EMERGENCY') return;
  const ps = pstat(S, fteam, cur);
  const inn = S.inning;
  const bteam = batTeam(S);
  const lead = S.score[fteam] - S.score[bteam];
  const runsThisInning = S.run_events.filter((ev) => ev.inning === inn && ev.half === S.half && ev.resp === cur).length;
  const isStarter = ps.entered_inning === 1 && !G.allPenNames.has(cur);
  let hook = false, want = null;
  if (isStarter) {
    if (ps.R >= 6 && ps.fatigued) { hook = true; want = inn >= 7 ? 'setup' : 'long'; }
    else if (inn >= 6 && ps.R >= 4) { hook = true; want = inn <= 6 ? 'long' : 'setup'; }
    else if (inn >= 5 && runsThisInning >= 3) { hook = true; want = 'long'; }
    else if (inn >= 9 && lead > 0 && lead <= 3 && ps.outs >= 21) { hook = true; want = 'closer'; }
  } else {
    if (ps.R >= 3) { hook = true; want = 'setup'; }
    else if (inn >= 9 && lead > 0 && lead <= 3 && G.penRole[fteam][cur] !== 'closer') { hook = true; want = 'closer'; }
  }
  if (hook && tm.pen.length) {
    const nw = pickReliever(G, S, fteam, want);
    if (nw !== cur) changePitcher(G, S, fteam, want);
  }
}
function removePitcher(G, S, fteam, reason) {
  const tm = T(S, fteam);
  const cur = tm.pitcher;
  tm.removed.push(cur);
  const nw = pickReliever(G, S, fteam, S.inning >= 7 ? 'setup' : 'long');
  changePitcherRaw(G, S, fteam, nw);
  elog(S, '  ' + cur + ' removed (' + reason + ')');
  led(S, 'pitcher_removed', cur + ': ' + reason);
}
function engineUpdateFatigue(G, S) {
  const fteam = fldTeam(S);
  const cur = curPitcher(S);
  const ps = pstat(S, fteam, cur);
  if (ps.R >= 6 && !ps.fatigued) {
    ps.fatigued = true;
    led(S, 'fatigue', cur + ' is fatigued under the universal 6-run rule (no Start stamina rating on converted cards)');
    elog(S, '  ' + cur + ' has allowed 6 runs and is fatigued (Fatigued Pitcher Adjustments apply)');
  }
}
const FAT_SP_PATIENT = [[67, 'PATIENT'], [71, 'SINGLE'], [79, 'IN-PLAY'], [99, 'WHEELHOUSE']];
const FAT_RP_PATIENT = [[37, 'PATIENT'], [50, 'SINGLE'], [79, 'IN-PLAY'], [99, 'WHEELHOUSE']];
const FAT_TOUGH = [[54, 'TOUGH'], [66, 'IN-PLAY'], [99, 'WHEELHOUSE']];
function fatiguedSection(kind, pct, isSp) {
  const table = kind === 'PATIENT' ? (isSp ? FAT_SP_PATIENT : FAT_RP_PATIENT) : FAT_TOUGH;
  for (const [hi, sec] of table) if (pct <= hi) return sec;
  return 'WHEELHOUSE';
}

/* ------------------------------------------------------ substitution */
const VAC_AREA = { '1B': 'IF', '2B': 'IF', '3B': 'IF', 'SS': 'IF', 'LF': 'OF', 'CF': 'OF', 'RF': 'OF', 'C': 'C', 'P': 'P' };
const VAC_RANGE_RANK = { A: 0, B: 1, C: 2, D: 3, F: 4 };
function vacLine(card, spot) {
  for (const p of card.positions) if (p.pos === spot) return p;
  return card.positions[0];
}
function vacKey(line) { return [VAC_RANGE_RANK[line.range] != null ? VAC_RANGE_RANK[line.range] : 2, line.e, -line.arm]; }
function vacCmp(a, b) { for (let i = 0; i < 3; i++) { if (a[i] !== b[i]) return a[i] - b[i]; } return 0; }
function vacPair(ka, kb) { return vacCmp(ka, kb) >= 0 ? [ka, kb] : [kb, ka]; }
function vacPairCmp(pa, pb) { const c = vacCmp(pa[0], pb[0]); return c !== 0 ? c : vacCmp(pa[1], pb[1]); }
function vacDescribe(line) { return 'range ' + line.range + ', E ' + line.e + ', arm ' + line.arm; }
function vacFitPick(benchCards, spot) {
  for (const [name, card] of benchCards) {
    if (card.positions.some((p) => p.pos === spot)) return [name, 1];
  }
  const area = VAC_AREA[spot];
  if (area) {
    let best = null;
    benchCards.forEach(([name, card], i) => {
      if (card.positions.some((p) => VAC_AREA[p.pos] === area)) {
        const k = vacKey(vacLine(card, spot));
        if (best === null || vacCmp(k, best[0]) < 0) best = [k, i, name];
      }
    });
    if (best !== null) return [best[2], 2];
  }
  return [null, null];
}
/* Joe's vacancy rule (2026-10-27), ported whole. A generator only
 * because a human club's forced coverage stops for the manager's
 * pick (spec 7.1); with no human club it never yields. */
function* substitute(G, S, team, outName, reason) {
  const tm = T(S, team);
  const slot = tm.order.find((s) => s.name === outName) || null;
  let pos = null;
  for (const p of Object.keys(tm.field)) if (tm.field[p] === outName) pos = p;
  const wantPos = slot ? slot.pos : pos;
  const spot = pos || wantPos;
  let pick = null, slide = null, basis = null;
  if (spot && spot !== 'DH' && tm.bench.length) {
    const benchCards = tm.bench.map((b) => [b, hcard(G, b, team)]);
    const [fp, tier] = vacFitPick(benchCards, spot);
    pick = fp;
    if (pick !== null && tier === 2) {
      const pline = vacLine(hcard(G, pick, team), spot);
      basis = "manager's rule (Joe, 2026-10-27): no bench card carries " + spot + '; ' + pick + ' is the best ' +
        (VAC_AREA[spot] === 'IF' ? 'infield' : 'outfield') + ' fit and covers ' + spot + ' priced on his carded ' +
        hcard(G, pick, team).positions[0].pos + ' line (' + vacDescribe(pline) + '); bench order does not govern';
    }
    if (pos && (VAC_AREA[spot] === 'IF' || VAC_AREA[spot] === 'OF')) {
      const area = VAC_AREA[spot];
      let bestSlide = null;
      for (const oldSpot of Object.keys(tm.field)) {
        const starter = tm.field[oldSpot];
        if (starter === outName || oldSpot === spot) continue;
        if (VAC_AREA[oldSpot] !== area) continue;
        const [sub2] = vacFitPick(benchCards, oldSpot);
        if (sub2 === null) continue;
        const scard = hcard(G, starter, team);
        const pair = vacPair(vacKey(vacLine(scard, spot)), vacKey(vacLine(hcard(G, sub2, team), oldSpot)));
        if (pick !== null) {
          const direct = vacPair(vacKey(vacLine(hcard(G, pick, team), spot)), vacKey(vacLine(scard, oldSpot)));
          if (vacPairCmp(pair, direct) >= 0) continue;
        }
        if (bestSlide === null || vacPairCmp(pair, bestSlide[0]) < 0) bestSlide = [pair, starter, oldSpot, sub2];
      }
      if (bestSlide !== null) {
        const [, starter, oldSpot, sub2] = bestSlide;
        const scard = hcard(G, starter, team);
        basis = "manager's rule (Joe, 2026-10-27): " + starter + ' slides from ' + oldSpot + ' to ' + spot +
          ' priced on his carded ' + scard.positions[0].pos + ' line (' + vacDescribe(vacLine(scard, spot)) + ') and ' +
          sub2 + ' covers ' + oldSpot + ' priced on his carded ' + hcard(G, sub2, team).positions[0].pos + ' line (' +
          vacDescribe(vacLine(hcard(G, sub2, team), oldSpot)) + '); the two spots together are stronger than ' +
          pick + ' covering ' + spot + ' directly';
        slide = [starter, oldSpot];
        pick = sub2;
      }
    }
  }
  if (pick === null && tm.bench.length) {
    pick = tm.bench[0];
    if (spot && spot !== 'DH') {
      const pline = vacLine(hcard(G, pick, team), spot);
      basis = "manager's rule (Joe, 2026-10-27): no carded or same-area fit for " + spot + ' on the bench; bench order, the last resort: ' +
        pick + ' covers ' + spot + ' priced on his carded ' + hcard(G, pick, team).positions[0].pos + ' line (' + vacDescribe(pline) + ')';
    }
  }
  if (pick === null) {
    elog(S, '  !! no substitute available for ' + outName);
    return null;
  }
  if (G.human[team]) {
    const ans = yield { decision: { kind: 'coverage', team: team, out: outName, spot: spot, pick: pick, slide: slide, basis: basis, bench: tm.bench.slice(), reason: reason } };
    if (ans && ans.pick && ans.pick !== pick && tm.bench.includes(ans.pick)) {
      pick = ans.pick;
      slide = null;
      basis = 'your call: ' + pick + ' covers ' + spot + ' (the machinery had ' + (basis ? 'a fit pick' : 'bench order') + ')';
      led(S, 'vacancy_coverage', basis);
    }
  }
  tm.bench.splice(tm.bench.indexOf(pick), 1);
  tm.removed.push(outName);
  if (slot) slot.name = pick;
  if (slide) {
    const [starter, oldSpot] = slide;
    tm.field[spot] = starter;
    tm.field[oldSpot] = pick;
    if (slot) slot.pos = oldSpot;
    const sslot = tm.order.find((s) => s.name === starter);
    if (sslot) sslot.pos = spot;
  } else if (pos) {
    tm.field[pos] = pick;
  }
  if (slide) {
    elog(S, '  substitution (' + TEAMNAME[team] + '): ' + pick + ' replaces ' + outName + '; ' + slide[0] + ' slides from ' + slide[1] + ' to ' + spot + ' (' + reason + ')');
  } else {
    elog(S, '  substitution (' + TEAMNAME[team] + '): ' + pick + ' replaces ' + outName + ' (' + reason + ')');
  }
  led(S, 'substitution', pick + ' for ' + outName + ' (' + reason + ')');
  if (basis) led(S, 'vacancy_coverage', basis);
  return pick;
}

/* ------------------------------------------- fatigue book (fatigue_fix) */
function ffState(S) {
  if (!S.fatigue_fix) {
    S.fatigue_fix = { version: 1, date: null, pa_index: 0, run_events_seen: 0,
      chart_count_seen: 0, pitchers: {}, adjustments: [], availability_next: {} };
  }
  return S.fatigue_fix;
}
function ffIsStarter(G, S, team, name) {
  if (G.starters[team] === name) return true;
  for (const sp of S.pitcher_spans) {
    if (sp.team === team) return sp.name === name;
  }
  const ps = S.teams[team].pitching[name];
  return !!(ps && ps.entered_inning === 1);
}
function ffSymbolOf(card) {
  if (!card) return null;
  return card.save_symbol || card.symbol ||
    (Array.isArray(card.symbols) ? card.symbols[0] : card.symbols) || null;
}
function ffRecord(G, S, team, name) {
  const ff = ffState(S);
  const key = team + '|' + name;
  if (!ff.pitchers[key]) {
    const card = name === 'EMERGENCY' ? null : pitcherCard(G, S, team, name);
    const st = card && card.stamina && typeof card.stamina === 'object' ? card.stamina : null;
    ff.pitchers[key] = { team: team, name: name,
      stamina: st ? { start: st.start != null ? st.start : null, relief: st.relief != null ? st.relief : null } : null,
      symbol: ffSymbolOf(card), is_starter: ffIsStarter(G, S, team, name),
      appearances: [], timeline: [], states: [], book_fatigued: false,
      trigger: null, exempt_active: false, exempt_noted: false, exemption_spent: false };
  }
  return ff.pitchers[key];
}
function ffPhantom(S, team, name) {
  const fl = S.flags || {};
  const attr = (fl.v2_attrition || {})[team + '|' + name] || 0;
  const grind = Math.floor(((fl.francona_grind || {})[name] || 0) / 3);
  return [attr, grind, attr + grind];
}
function ffPrecheck(G, S) {
  const ff = ffState(S);
  const fteam = fldTeam(S);
  const cur = curPitcher(S);
  while (ff.run_events_seen < S.run_events.length) {
    const ev = S.run_events[ff.run_events_seen];
    const evTeam = ev.team === 'CHC' ? 'OPP' : 'CHC';
    const rec = ffRecord(G, S, evTeam, ev.resp);
    rec.timeline.push({ pa: ff.pa_index, inning: ev.inning, half: ev.half,
      charged_to: ev.resp, runs_after: pstat(S, evTeam, ev.resp).R });
    ff.run_events_seen += 1;
  }
  const pre = { fteam: fteam, cur: cur, rec: null, suppressed: false, lead: 0, sit: false };
  if (cur === 'EMERGENCY') return pre;
  const rec = ffRecord(G, S, fteam, cur);
  pre.rec = rec;
  if (!rec.appearances.includes(S.inning)) rec.appearances.push(S.inning);
  const lead = S.score[fteam] - S.score[fteam === 'CHC' ? 'OPP' : 'CHC'];
  const sit = S.inning >= 9 && lead >= 1 && lead <= 3;
  pre.lead = lead; pre.sit = sit;
  if (rec.symbol && !rec.is_starter && sit && !rec.exemption_spent) {
    pre.suppressed = true;
    rec.exempt_active = true;
  } else if (rec.exempt_active && !rec.exemption_spent && S.inning >= 9 && lead <= 0) {
    rec.exemption_spent = true;
    const msg = cur + ": the game is tied or the lead is lost; the save-symbol exemption is spent and the book's fatigue rules apply from here (2024 rulebook pp11, 39)";
    led(S, 'fatigue_fix', msg);
    elog(S, '  FATIGUE (book): ' + msg);
  }
  return pre;
}
const FF_RELIEF_LIMITS = { Short: [2, 2], Long: [3, 3] };
function ffTriggers(G, S, pre) {
  const fteam = pre.fteam, cur = pre.cur, rec = pre.rec;
  const ps = pstat(S, fteam, cur);
  const [attr, grind, ph] = ffPhantom(S, fteam, cur);
  const eff = ps.R + ph;
  const evalNote = ph ? 'evaluation runs ' + eff + ' = ' + ps.R + ' charged + ' + ph + ' trait evaluation runs (attrition ' + attr + ', grind ' + grind + ')' : eff + ' runs allowed';
  const out = [];
  const stam = rec.stamina || {};
  if (rec.is_starter) {
    const start = stam.start;
    if (start !== null && start !== undefined && S.inning >= start && eff >= 3) {
      out.push(['starter_stamina', cur + " is fatigued under the book's starter-stamina rule: Start " + start + ' reached (inning ' + S.inning + ') with ' + evalNote + ', 3 or more (2024 rulebook p10)']);
    }
  } else {
    const rel = stam.relief;
    if (FF_RELIEF_LIMITS[rel]) {
      const [limI, limR] = FF_RELIEF_LIMITS[rel];
      const ended = rec.appearances.filter((i) => i < S.inning).length;
      if (ended >= limI) {
        out.push(['relief_appearances', cur + " is fatigued under the book's relief rule: a " + rel + ' reliever whose appeared innings are ' + JSON.stringify(rec.appearances) + '; ' + ended + ' of them have ended, reaching the ' + limI + '-inning limit as the last of them ended (2024 rulebook p11)']);
      }
      if (eff >= limR) {
        out.push(['relief_runs', cur + " is fatigued under the book's relief rule: a " + rel + ' reliever at ' + evalNote + ', the ' + limR + '-run limit (2024 rulebook p11)']);
      }
    }
  }
  if (eff >= 6) {
    out.push(['universal_runs', cur + ' is fatigued at ' + evalNote + ': the universal 6-run line (2024 rulebook p10)']);
  }
  return out;
}
function ffMirror(G, S) {
  const ff = ffState(S);
  const rows = (S.ledger.fatigue_chart || { details: [] }).details;
  if (rows.length > ff.chart_count_seen) {
    for (const d of rows.slice(ff.chart_count_seen)) {
      ff.adjustments.push({ pa: ff.pa_index, detail: d });
    }
    ff.chart_count_seen = rows.length;
  }
}
function ffAvailability(G, S) {
  const ff = ffState(S);
  const rows = {};
  for (const sp of S.pitcher_spans) {
    const end = sp.end ? sp.end[2] : S.def_outs[sp.team];
    const outs = end - sp.start[2];
    const row = outs < 6 ? 'free' : (outs <= 8 ? 'available next game, capped at 3 outs' : 'unavailable next game');
    rows[sp.team + '|' + sp.name] = { outs: outs, row: row };
  }
  ff.availability_next = rows;
}
function ffEvaluate(G, S, phase, pre) {
  const ff = ffState(S);
  const cur = pre.cur, rec = pre.rec;
  if (cur === 'EMERGENCY' || rec === null) return;
  const ps = pstat(S, pre.fteam, cur);
  const trigs = ffTriggers(G, S, pre);
  if (pre.suppressed) {
    if (trigs.length && !rec.exempt_noted) {
      rec.exempt_noted = true;
      const msg = cur + ' carries a save symbol (' + rec.symbol + ') and is in a save situation (inning ' + S.inning + ', lead ' + pre.lead + "): the book's exemption holds and fatigue does not attach, although a book trigger is met (" + trigs[0][0] + ') (2024 rulebook pp11, 39)';
      led(S, 'fatigue_fix_exempt', msg);
      elog(S, '  FATIGUE (book, exemption): ' + msg);
    }
  } else {
    if (trigs.length && !rec.book_fatigued) {
      const [kind, detail] = trigs[0];
      rec.book_fatigued = true;
      rec.trigger = { kind: kind, detail: detail, pa: ff.pa_index, inning: S.inning, half: S.half };
      const wasSet = !!ps.fatigued;
      if (!wasSet) ps.fatigued = true;
      led(S, 'fatigue_fix', detail + (wasSet && kind !== 'universal_runs' ? ' (the flag was already set by the wrapped chain; the book trigger attaches on the same evaluation)' : ''));
      elog(S, '  FATIGUE (book): ' + detail);
    } else if (rec.book_fatigued && !ps.fatigued) {
      ps.fatigued = true;
      const msg = cur + ': book fatigue (' + rec.trigger.kind + ') re-asserted after an external clearance of the flag';
      led(S, 'fatigue_fix_reassert', msg);
      elog(S, '  FATIGUE (book): ' + msg);
    }
  }
  if (phase === 'post') {
    rec.states.push({ pa: ff.pa_index, inning: S.inning, half: S.half,
      fatigued: !!ps.fatigued, book_fatigued: rec.book_fatigued,
      trigger: rec.trigger ? rec.trigger.kind : null,
      save_situation: pre.sit, lead: pre.lead, symbol_exempt: pre.suppressed });
    ffMirror(G, S);
    ffAvailability(G, S);
  }
}

/* --------------------------------------------- Williams traits (traits2) */
function masterOn(S) { return !!(S.traits && S.traits.on && S.traits.v2); }
const ROLE_PRIORITY = ['closer', 'setup', 'mid', 'long'];
const FAST_RUN = 10, SLOW_RUN = 7;
function diffFor(S, team) { const other = team === 'CHC' ? 'OPP' : 'CHC'; return S.score[team] - S.score[other]; }
function armShift(S, source) {
  const fl = S.flags;
  if (fl.v2_shift_live) {
    led(S, 'v2_late_sub_shift', 'shift refreshed by ' + source + ' while already live; still a single +3');
  } else if (fl.v2_shift_pending) {
    led(S, 'v2_late_sub_shift', 'shift refresh from ' + source + ': already armed, still a single +3');
  } else {
    led(S, 'v2_late_sub_shift', 'defensive shift armed by ' + source + ': the next Montreal PA after the sub reads PATIENT shifted +3 (Williams) late-inning sub shift');
  }
  fl.v2_shift_pending = true;
}
function pinchHit(S, team, outName, pick, reason) {
  const tm = T(S, team);
  tm.bench.splice(tm.bench.indexOf(pick), 1);
  tm.removed.push(outName);
  for (const slot of tm.order) {
    if (slot.name === outName) {
      slot.name = pick;
      for (const p of Object.keys(tm.field)) if (tm.field[p] === outName) tm.field[p] = pick;
      break;
    }
  }
  elog(S, '  pinch hitter (' + TEAMNAME[team] + '): ' + pick + ' bats for ' + outName + ' (' + reason + ')');
  led(S, 'substitution', pick + ' for ' + outName + ' (' + reason + ')');
}
function pinchRun(S, team, outName, pick, reason) {
  const tm = T(S, team);
  tm.bench.splice(tm.bench.indexOf(pick), 1);
  tm.removed.push(outName);
  for (let i = 0; i < 3; i++) {
    if (S.bases[i] && S.bases[i].name === outName) S.bases[i] = { name: pick, resp: S.bases[i].resp };
  }
  for (const slot of tm.order) {
    if (slot.name === outName) {
      slot.name = pick;
      for (const p of Object.keys(tm.field)) if (tm.field[p] === outName) tm.field[p] = pick;
      break;
    }
  }
  elog(S, '  pinch runner (' + TEAMNAME[team] + '): ' + pick + ' runs for ' + outName + ' (' + reason + ')');
  led(S, 'substitution', pick + ' runs for ' + outName + ' (' + reason + ')');
}
function* williamsDefenseCheck(G, S) {
  const fl = S.flags;
  const key = S.inning + ':' + S.half;
  if (fl.v2_last_half_key === key) return;
  fl.v2_last_half_key = key;
  if (fldTeam(S) !== 'OPP' || S.inning < 8 || fl.v2_defsub_done) return;
  const d = diffFor(S, 'OPP');
  if (!(d >= 1 && d <= 3)) return;
  const tm = T(S, 'OPP');
  let cand = null, candPos = null;
  for (const n of tm.bench) {
    const card = hcard(G, n, 'OPP');
    const p0 = card.positions[0];
    const inc = tm.field[p0.pos];
    if (!inc || inc === n) continue;
    const iline = vacLine(hcard(G, inc, 'OPP'), p0.pos);
    if (p0.range === 'A' && iline.range !== 'A') { cand = n; candPos = p0.pos; break; }
  }
  if (!cand) return;
  const inc = tm.field[candPos];
  led(S, 'v2_late_sub_opportunity', 'Dick Williams weighs a defensive replacement: ' + cand + ' (range A at ' + candPos + ') for ' + inc + ' in the ' + S.inning + 'th, Montreal up ' + d);
  const pick = yield* substitute(G, S, 'OPP', inc, 'defensive replacement (Dick Williams)');
  if (pick === cand) {
    fl.v2_defsub_done = true;
    armShift(S, 'defensive replacement by ' + cand + ' at ' + candPos);
    led(S, 'v2_late_sub_defense', cand + ' in at ' + candPos + ' for ' + inc + ' (Williams defensive replacement)');
  }
}
function williamsDecisions(G, S) {
  const fl = S.flags;
  const tm = T(S, 'OPP');
  const fteam = fldTeam(S);
  const pitcherName = curPitcher(S);
  const pcardNow = pitcherCard(G, S, fteam, pitcherName);
  const throws = pcardNow.throws;
  const [batterName] = currentBatter(S);
  const bcard = hcard(G, batterName, 'OPP');
  if (S.inning >= 7 && (bcard.bats === 'L' || bcard.bats === 'R') && bcard.bats === throws) {
    const want = throws === 'R' ? 'L' : 'R';
    led(S, 'v2_attrition_opportunity', batterName + ' (' + bcard.bats + 'HB) vs ' + pitcherName + ' (' + throws + 'HP), ' + S.inning + 'th inning: strict platoon disadvantage');
    const cand = tm.bench.find((n) => hcard(G, n, 'OPP').bats === want) || null;
    if (cand) {
      pinchHit(S, 'OPP', batterName, cand, 'Williams platoon pinch hit (Strategic Attrition)');
      const key = fteam + '|' + pitcherName;
      const att = fl.v2_attrition || (fl.v2_attrition = {});
      att[key] = (att[key] || 0) + 1;
      led(S, 'v2_attrition', cand + ' pinch hits for ' + batterName + ': ' + pitcherName + ' is rattled, attrition ' + att[key] + ' (his 6-run fatigue line now sits at ' + (6 - att[key]) + ' runs allowed)');
      elog(S, "  Strategic Attrition: " + pitcherName + "'s remaining stamina drops by one batter-equivalent (attrition " + att[key] + ' toward the fatigue line)');
    } else {
      led(S, 'v2_attrition_nomove', 'no ' + want + 'HB bench bat remains; no pinch hit');
    }
  }
  if (S.inning >= 8 && [-2, -1, 0, 1].includes(diffFor(S, 'OPP'))) {
    let slow = null;
    for (const base of [3, 2, 1]) {
      const e = S.bases[base - 1];
      if (e && (hcard(G, e.name, 'OPP').run || 0) <= SLOW_RUN) {
        if (slow === null || base > slow[0]) slow = [base, e];
      }
    }
    if (slow) {
      const [base, e] = slow;
      led(S, 'v2_late_sub_opportunity', e.name + ' (RUN ' + hcard(G, e.name, 'OPP').run + ') on ' + base + 'B, ' + S.inning + 'th inning');
      const cand = tm.bench.find((n) => (hcard(G, n, 'OPP').run || 0) >= FAST_RUN) || null;
      if (cand) {
        const oldName = e.name;
        pinchRun(S, 'OPP', oldName, cand, 'Williams late-inning pinch run (fast runner)');
        armShift(S, 'pinch run by ' + cand + ' (RUN ' + FAST_RUN + ') for ' + oldName);
        led(S, 'v2_late_sub_pr', cand + ' runs for ' + oldName + ' at ' + base + 'B');
      } else {
        led(S, 'v2_late_sub_nomove', 'no RUN-10 bench runner remains; no sub made');
      }
    }
  }
}
/* traits2's pre_pa: the driver hook (Replay B and app play;
 * Replay A's driver never called it, spec 11.1). */
function* prePa(G, S) {
  if (S.pending || S.final) return;
  const fl = S.flags;
  fl.v2_pa_serial = (fl.v2_pa_serial || 0) + 1;
  fl.v2_half_seen = S.inning + ':' + S.half;
  const ph = fl.v2_ph;
  if (ph && ph.serial !== fl.v2_pa_serial && !ph.applied) {
    if (fl.v2_cur_section === 'TOUGH') {
      led(S, 'v2_mr_opportunity', 'the manufactured-runs window closed unread (the PA read TOUGH)');
    }
    fl.v2_ph = null;
  }
  if (fl.v2_shift_live && !fl.v2_shift_pending && !fl.v2_shift_applied) {
    led(S, 'v2_late_sub_shift_expired', 'the sub shift lapsed unread after one full PA');
    fl.v2_shift_live = false;
  }
  fl.v2_shift_live = false;
  fl.v2_shift_applied = false;
  fl.v2_cur_section = null;
  fl.v2_ph_tough = false;
  if (!masterOn(S)) return;
  yield* williamsDefenseCheck(G, S);
  if (batTeam(S) === 'OPP') williamsDecisions(G, S);
}

/* ------------------------------------------------ Chance (traits_chance) */
function chanceAsg(S) {
  return S.traits && S.traits.on ? (S.traits.frank_chance || null) : null;
}
function chanceRt(S) {
  const fl = S.flags;
  if (!fl.frank_chance) {
    fl.frank_chance = { leader_reads: 0, leader_changed: 0, acct_reads: 0, acct_changed: 0,
      dp_bumps: 0, dp_margin: 0, dp_tie: 0, dp_tie_gate_closed: 0, hnr_seen: 0,
      hnr_slash_seen: 0, starter_1b: null, leader_watch: null, leader_pa: null,
      leader_unread: 0, acct_watch: null, acct_armed: null, acct_pa: null,
      acct_spent_unread: 0, acct_lapsed: 0 };
  }
  return fl.frank_chance;
}
function statSnap(S, team, name) {
  const bs = T(S, team).batting[name];
  const snap = {};
  for (const k of ['H', 'BB', 'HBP', 'R']) snap[k] = bs ? (bs[k] || 0) : 0;
  return snap;
}
function reachedSince(S, team, name, snap) {
  if (S.bases.some((e) => e && e.name === name)) return true;
  const bs = T(S, team).batting[name];
  if (!bs) return false;
  return ['H', 'BB', 'HBP', 'R'].some((k) => (bs[k] || 0) > (snap[k] || 0));
}
function chanceLeaderCycle(G, S) {
  const rt = chanceRt(S);
  const team = chanceAsg(S).team;
  const tm = T(S, team);
  if (rt.starter_1b === null && tm.field['1B']) rt.starter_1b = tm.field['1B'];
  const w = rt.leader_watch;
  rt.leader_pa = null;
  if (w && w.batter === rt.starter_1b && w.batter !== currentBatter(S)[0] && reachedSince(S, w.team, w.batter, w.snap)) {
    const batter = currentBatter(S)[0];
    rt.leader_pa = { batter: batter, serial: S.pa_count + 1 };
    led(S, 'chance_leader_armed', 'Frank Chance reached and the lineup turned over: ' + batter + "'s PATIENT and WHEELHOUSE sections read with the leader bonus (+3 on the result band, Chance trait)");
  }
  const [batter] = currentBatter(S);
  rt.leader_watch = { batter: batter, team: team, snap: statSnap(S, team, batter) };
}
function chanceAcctCycle(G, S) {
  const rt = chanceRt(S);
  const team = chanceAsg(S).team;
  const w = rt.acct_watch;
  rt.acct_pa = null;
  if (w) {
    const errorsNow = T(S, team).team_errors;
    if (errorsNow > w.errors && reachedSince(S, w.bteam, w.batter, w.snap)) {
      rt.acct_armed = { pitcher: w.pitcher };
      led(S, 'chance_acct_armed', 'an error behind ' + w.pitcher + ' let ' + w.batter + ' reach: the pitcher is owed one (Accountability, Chance trait)');
    }
  }
  if (rt.acct_armed) {
    if (curPitcher(S) === rt.acct_armed.pitcher) {
      rt.acct_pa = { pitcher: rt.acct_armed.pitcher, serial: S.pa_count + 1 };
      rt.acct_armed = null;
    } else {
      rt.acct_lapsed += 1;
      led(S, 'chance_acct_lapsed', 'the owed chance lapses: ' + rt.acct_armed.pitcher + ' is no longer pitching');
      rt.acct_armed = null;
    }
  }
  const [batter] = currentBatter(S);
  rt.acct_watch = { pitcher: curPitcher(S), batter: batter, bteam: batTeam(S),
    errors: T(S, team).team_errors, snap: statSnap(S, batTeam(S), batter) };
}
function bandEdit(card, section, hand, prioList, n) {
  const sec = (card.sections[section] || {})[hand];
  if (!sec) return [null, null];
  for (const k of prioList) {
    const r = sec[k];
    if (r && r[1] >= r[0]) {
      const s2 = {};
      for (const kk of Object.keys(sec)) s2[kk] = sec[kk] ? [sec[kk][0], sec[kk][1]] : null;
      s2[k] = [r[0], Math.min(99, r[1] + n)];
      const c2 = Object.assign({}, card, { sections: Object.assign({}, card.sections, { [section]: Object.assign({}, card.sections[section], { [hand]: s2 }) }) });
      return [c2, k];
    }
  }
  return [null, null];
}
const SECTION_PRIO = ['HR', 'SO', 'BB', 'HBP', '3B', '2B', '1B'];
function editedRead(G, S, card, section, hand, pct, kind) {
  const rt = chanceRt(S);
  let edited, band, n;
  if (kind === 'leader') { [edited, band] = bandEdit(card, section, hand, SECTION_PRIO, 3); n = 3; }
  else { [edited, band] = bandEdit(card, section, hand, ['SO'], 5); n = 5; }
  if (!edited) return null;
  const raw = sectionLookupTraits2(G, S, card, section, hand, pct);
  const ed = sectionLookupTraits2(G, S, edited, section, hand, pct);
  const changed = ed !== raw;
  if (kind === 'leader') {
    rt.leader_reads += 1;
    if (changed) rt.leader_changed += 1;
    led(S, 'chance_leader_read', 'leader read on ' + card.name + "'s " + section + ': band ' + band + ' widened +' + n + ' for this read; %=' + pad2(pct) + ' raw=' + raw + ' edited=' + ed + (changed ? ' (result changed)' : ''));
  } else {
    rt.acct_reads += 1;
    if (changed) rt.acct_changed += 1;
    led(S, 'chance_acct_read', 'accountability read vs ' + card.name + "'s TOUGH: SO band widened +5 for this read; %=" + pad2(pct) + ' raw=' + raw + ' edited=' + ed + (changed ? ' (result changed)' : ''));
  }
  return [ed, changed];
}
/* The composed section lookup: Chance's edits over traits2's
 * shift over the raw engine read. */
function sectionLookup(G, S, card, section, hand, pct) {
  const asg = chanceAsg(S);
  if (asg && !S.final) {
    const rt = chanceRt(S);
    const lp = rt.leader_pa, ap = rt.acct_pa;
    if (lp && (section === 'PATIENT' || section === 'WHEELHOUSE') && batTeam(S) === asg.team && card.name === lp.batter) {
      const r = editedRead(G, S, card, section, hand, pct, 'leader');
      if (r !== null) return r[0];
    }
    if (ap && section === 'TOUGH' && fldTeam(S) === asg.team && curPitcher(S) === ap.pitcher) {
      const r = editedRead(G, S, card, section, hand, pct, 'acct');
      if (r !== null) return r[0];
    }
  }
  return sectionLookupTraits2(G, S, card, section, hand, pct);
}
function sectionLookupTraits2(G, S, card, section, hand, pct) {
  if (S && masterOn(S)) {
    const fl = S.flags;
    fl.v2_cur_section = section;
    if (fl.v2_shift_live && section === 'PATIENT' && batTeam(S) === 'OPP' && !fl.v2_shift_applied) {
      if (pct + 3 <= 99) {
        fl.v2_shift_applied = true;
        led(S, 'v2_late_sub_shift', 'PATIENT read shifted +3 by the late-inning sub (Williams): %=' + pad2(pct) + ' read at ' + pad2(pct + 3));
        pct = pct + 3;
      }
    }
  }
  return sectionLookupRaw(card, section, hand, pct);
}
/* Chance's ground_out wrapper (Tinker to Evers to Chance) over
 * the addendum's ground_out. */
function* groundOut(G, S, batterName, pos, pct, pitcherResult) {
  const asg = chanceAsg(S);
  const qualifies = asg && fldTeam(S) === asg.team && !!S.bases[0] && S.outs < 2;
  if (!qualifies) {
    return yield* groundOutAdd(G, S, batterName, pos, pct, pitcherResult);
  }
  const rt = chanceRt(S);
  if (rt.starter_1b === null) { const ct = S.teams[asg.team]; if (ct && ct.field['1B']) rt.starter_1b = ct.field['1B']; }
  const pname = curPitcher(S);
  const pcardNow = pitcherCard(G, S, fldTeam(S), pname);
  const pitcherDp = pname === 'EMERGENCY' ? null : (pcardNow.dp != null ? pcardNow.dp : null);
  const bcard = hcard(G, batterName, batTeam(S));
  const eff = pitcherDp !== null ? Math.min(bcard.dp, pitcherDp) : bcard.dp;
  const before = (S.ledger.double_play_check || { details: [] }).details.length;
  const oldBatterDp = bcard.dp;
  let oldPitcherDp;
  bcard.dp = eff + 1;
  if (pname !== 'EMERGENCY' && pcardNow.dp != null) { oldPitcherDp = pcardNow.dp; pcardNow.dp = eff + 1; }
  rt.dp_bumps += 1;
  led(S, 'chance_dp_bump', 'Tinker to Evers to Chance: the double-play combination is set (' + S.teams[fldTeam(S)].field['2B'] + ' at 2B, ' + S.teams[fldTeam(S)].field.SS + ' at SS); the DP check reads one higher (' + eff + ' -> ' + (eff + 1) + ')');
  let result;
  const bsBefore = bstat(S, batTeam(S), batterName).GDP;
  try {
    result = yield* groundOutAdd(G, S, batterName, pos, pct, pitcherResult);
  } finally {
    bcard.dp = oldBatterDp;
    if (oldPitcherDp !== undefined) pcardNow.dp = oldPitcherDp;
  }
  const bs = bstat(S, batTeam(S), batterName);
  if (bs.GDP > bsBefore) {
    const details = (S.ledger.double_play_check || { details: [] }).details;
    if (details.length > before) {
      const m = /2d6=(\d+)/.exec(details[details.length - 1]);
      if (m) {
        const total = parseInt(m[1], 10);
        if (total === eff + 1) {
          rt.dp_margin += 1;
          led(S, 'chance_dp_margin', 'the DP turned exactly on the Chance bump (2d6=' + total + ' = effective DP ' + eff + ' + 1)');
        } else if (total === eff) {
          if (rt.starter_1b === 'Frank Chance') {
            rt.dp_tie += 1;
            led(S, 'chance_dp_tie', 'the DP check tied the unbumped rating (2d6=' + total + ' = DP ' + eff + ') and Chance himself holds the bag: the double play is completed');
          } else {
            rt.dp_tie_gate_closed += 1;
          }
        }
      }
    }
  }
  return result;
}

/* ------------------------------------------------------- PA resolution */
function* resolvePaInner(G, S, batterName, bcard, pcard, presult, total, pct, d1, d2, hnr, hnrRunner) {
  // Chance's Inside Baseball Precision intercepts H&R IN-PLAY reads.
  const asg = chanceAsg(S);
  if (asg && hnr && batTeam(S) === asg.team) {
    const rt = chanceRt(S);
    rt.hnr_seen += 1;
    if (presult === 'IN-PLAY') {
      const bteam = batTeam(S), fteam = fldTeam(S);
      pstat(S, fteam, curPitcher(S)).BF += 1;
      const bs = bstat(S, bteam, batterName);
      bs.AB += 1;
      const old = S.bases.slice();
      const rd = {};
      for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = Math.min(4, b + 1);
      applyPlay(S, batterName, 0, rd, { rbiTo: batterName, rbiRuns: old[2] ? 1 : 0 });
      S.outs += 1; S.def_outs[fteam] += 1;
      rt.hnr_conversions = (rt.hnr_conversions || 0) + 1;
      led(S, 'chance_hnr_conversion', 'Inside Baseball Precision: the IN-PLAY read on the hit and run becomes the chart outcome (batter out at 1st, every runner advances one base' + (old[2] ? ', the run scores' : '') + '); the percentile is discarded unread');
      elog(S, '  Inside Baseball Precision (Chance): batter out at 1st, runners advance one base on the hit and run');
      return 'DONE';
    }
    if (presult === '/IN-PLAY/' || presult === 'IN-PLAY [SINGLE]') rt.hnr_slash_seen += 1;
  }
  return yield* resolvePaInnerBody(G, S, batterName, bcard, pcard, presult, total, pct, d1, d2, hnr, hnrRunner);
}
function* resolvePaInnerBody(G, S, batterName, bcard, pcard, presult, total, pct, d1, d2, hnr, hnrRunner) {
  const bteam = batTeam(S), fteam = fldTeam(S);
  const pitcherName = curPitcher(S);
  const ps = pstat(S, fteam, pitcherName);
  const hand = pcard.throws === 'L' ? 'vsLHP' : 'vsRHP';
  const lowD6 = Math.min(d1, d2);
  const fatigued = ps.fatigued;
  const isSp = pitcherName === G.starters[fteam];
  let effPct = pct;
  if ((presult === 'TOUGH' || presult === 'TOUGH-OUT') && pcard.so_modifier != null && pcard.so_modifier !== 'NONE') {
    const bump = parseInt(String(pcard.so_modifier).replace('+', ''), 10);
    const conv = v2BandPct(bcard, hand, pct, bump);
    if (conv !== null) {
      effPct = conv;
      led(S, 'pct_band_v2', pitcherName + ' v2 bump +' + bump + ': TOUGH %=' + pad2(pct) + ' within ' + bump + ' above the SO band -> strikeout read at ' + pad2(effPct));
    }
  }
  elog(S, '  dice 2d6=' + total + ' (' + d1 + '+' + d2 + ') %=' + pad2(pct) + ' -> ' + presult);
  // Rare-force clauses (spec 6.1.8): a live clause for this
  // pitcher replaces the table dispatch with the forced section.
  if (G.clauses) {
    const forced = spendForceClause(S, pitcherName);
    if (forced) {
      elog(S, '  rare-play clause: this PA reads the ' + forced + ' section (clause live against ' + pitcherName + ')');
      if (forced === 'IN-PLAY') return yield* finishSection(G, S, batterName, bcard, 'IN-PLAY', effPct, lowD6, presult, hnr, hnrRunner);
      return yield* finishSection(G, S, batterName, bcard, forced, effPct, lowD6, presult, hnr, hnrRunner);
    }
  }
  if (hnr && (presult === 'PATIENT' || presult === 'PATIENT-OUT')) {
    const pct2 = yield* rollpct(G, S);
    led(S, 'hit_and_run', 'PATIENT on the hit and run = foul ball; re-roll %=' + pad2(pct2) + ' on IN-PLAY');
    elog(S, '  hit and run: PATIENT is a foul ball, re-roll %=' + pad2(pct2) + ' on IN-PLAY');
    return yield* finishSection(G, S, batterName, bcard, 'IN-PLAY', pct2, lowD6, presult, hnr, hnrRunner);
  }
  let section = null;
  if (fatigued && presult === 'BALLPARK') {
    section = 'WHEELHOUSE';
    led(S, 'fatigue_chart', 'fatigued ' + pitcherName + ': BALLPARK read directly on WHEELHOUSE');
  } else if (fatigued && (presult === 'PATIENT' || presult === 'PATIENT-OUT')) {
    section = fatiguedSection('PATIENT', pct, isSp);
    led(S, 'fatigue_chart', 'fatigued ' + pitcherName + ': PATIENT %=' + pad2(pct) + ' read as ' + section);
  } else if (fatigued && (presult === 'TOUGH' || presult === 'TOUGH-OUT')) {
    section = fatiguedSection('TOUGH', pct, isSp);
    led(S, 'fatigue_chart', 'fatigued ' + pitcherName + ': TOUGH %=' + pad2(pct) + ' read as ' + section);
  }
  if (section === 'SINGLE') {
    ps.BF += 1;
    elog(S, '  fatigued pitcher chart: batter singles');
    const desc = yield* resolveHit(G, S, batterName, '1B', 'PATIENT', pct, lowD6);
    elog(S, '  ' + desc);
    return 'DONE';
  }
  if (section !== null) {
    return yield* finishSection(G, S, batterName, bcard, section, section === 'TOUGH' ? effPct : pct, lowD6, presult, hnr, hnrRunner);
  }
  if (presult === 'WHEELHOUSE') return yield* finishSection(G, S, batterName, bcard, 'WHEELHOUSE', effPct, lowD6, presult, hnr, hnrRunner);
  if (presult === 'PATIENT') return yield* finishSection(G, S, batterName, bcard, 'PATIENT', effPct, lowD6, presult, hnr, hnrRunner);
  if (presult === 'PATIENT-OUT') {
    const r = sectionLookup(G, S, bcard, 'PATIENT', hand, effPct);
    ps.BF += 1;
    if (r === 'BB' || r === 'HBP') { applyWalk(G, S, batterName, r); return 'DONE'; }
    const code = outLookup(S, bcard, effPct, batterName, 'OUT (PATIENT-OUT)');
    elog(S, '  PATIENT-OUT: not a walk, OUT section -> ' + code);
    led(S, 'patient_out', batterName + ': ' + code);
    return yield* finishOutCode(G, S, batterName, code, presult, effPct, hnr, hnrRunner);
  }
  if (presult === 'TOUGH') return yield* finishSection(G, S, batterName, bcard, 'TOUGH', effPct, lowD6, presult, hnr, hnrRunner);
  if (presult === 'TOUGH-OUT') {
    const r = sectionLookup(G, S, bcard, 'TOUGH', hand, effPct);
    ps.BF += 1;
    if (r === 'SO') { yield* applySo(G, S, batterName, hnrRunner); return 'DONE'; }
    const code = outLookup(S, bcard, effPct, batterName, 'OUT (TOUGH-OUT)');
    elog(S, '  TOUGH-OUT: OUT section -> ' + code);
    led(S, 'tough_out', batterName + ': ' + code);
    return yield* finishOutCode(G, S, batterName, code, presult, effPct, hnr, hnrRunner);
  }
  if (presult === 'IN-PLAY') return yield* finishSection(G, S, batterName, bcard, 'IN-PLAY', effPct, lowD6, presult, hnr, hnrRunner);
  if (presult === '/IN-PLAY/') {
    if (ps.entered_inning === S.inning) {
      return yield* finishSection(G, S, batterName, bcard, 'IN-PLAY', effPct, lowD6, presult, hnr, hnrRunner);
    }
    ps.BF += 1;
    const code = outLookup(S, bcard, effPct, batterName, 'OUT (/IN-PLAY/ auto out)');
    led(S, 'slash_in_play', pitcherName + ' in his 2nd+ inning: /IN-PLAY/ is an automatic out; the converted table prints no out code, so the batter OUT section supplies ' + code);
    elog(S, '  /IN-PLAY/ automatic out -> ' + code);
    return yield* finishOutCode(G, S, batterName, code, presult, effPct, hnr, hnrRunner);
  }
  if (presult === 'IN-PLAY [SINGLE]') {
    const r = sectionLookup(G, S, bcard, 'IN-PLAY', hand, effPct);
    if (r === '1B' || r === '2B' || r === '3B') {
      return yield* finishSection(G, S, batterName, bcard, 'IN-PLAY', effPct, lowD6, presult, hnr, hnrRunner);
    }
    ps.BF += 1;
    if (!isSp || ps.H > 0) {
      elog(S, '  IN-PLAY [SINGLE]: out result converts to a single');
      const desc = yield* resolveHit(G, S, batterName, '1B', 'IN-PLAY', effPct, lowD6);
      elog(S, '  ' + desc);
      return 'DONE';
    }
    const code = outLookup(S, bcard, effPct, batterName, 'OUT ([SINGLE], no hit allowed yet)');
    return yield* finishOutCode(G, S, batterName, code, presult, effPct, hnr, hnrRunner);
  }
  if (presult === 'BALLPARK') {
    const bp = ballparkSection(G, bcard.bats, pct);
    const pct2 = yield* rollpct(G, S);
    led(S, 'ballpark', 'BALLPARK at ' + G.park.name + ': ' + (bcard.bats === 'L' ? 'L' : 'R') + 'HB %=' + pad2(pct) + ' -> ' + bp + '; re-roll %=' + pad2(pct2));
    elog(S, '  BALLPARK (' + G.park.name + ', ' + bcard.bats + 'HB): ' + bp + ', re-roll %=' + pad2(pct2));
    if (bp === 'WHEELHOUSE' && hnr) return yield* hnrWheel(G, S, batterName, bcard, lowD6, presult, hnrRunner);
    return yield* finishSection(G, S, batterName, bcard, bp, pct2, lowD6, presult, hnr, hnrRunner);
  }
  if (presult === 'DEFENSE' || presult === 'ERROR' || presult === 'RANGE') {
    ps.BF += 1;
    const out = yield* resolveDefense(G, S, batterName, presult, pct);
    if (out === 'RESTART') { ps.BF -= 1; return 'RESTART'; }
    return 'DONE';
  }
  throw new Error('unknown pitcher result ' + presult);
}
function* hnrWheel(G, S, batterName, bcard, lowD6, presult, hnrRunner) {
  const bteam = batTeam(S);
  yield* roll2d6(G, S);
  const pct2 = yield* rollpct(G, S);
  const ps = pstat(S, fldTeam(S), curPitcher(S));
  if ([0, 11, 22, 33, 44, 55, 66, 77, 88, 99].includes(pct2)) {
    elog(S, '  hit and run WHEELHOUSE re-roll: doubles %=' + pad2(pct2) + ', resolve as normal');
    return yield* finishSection(G, S, batterName, bcard, 'WHEELHOUSE', pct2, lowD6, presult, false, null);
  }
  ps.BF += 1;
  if (pct2 <= 49) {
    const old = S.bases.slice();
    const rd = {};
    for (const b of [1, 2, 3]) if (old[b - 1]) rd[b] = Math.min(4, b + 2);
    const bs = bstat(S, bteam, batterName);
    bs.AB += 1; bs.H += 1;
    pstat(S, fldTeam(S), curPitcher(S)).H += 1;
    applyPlay(S, batterName, 1, rd, { rbiTo: batterName, rbiRuns: Object.values(rd).filter((d) => d >= 4).length });
    elog(S, '  hit and run WHEELHOUSE re-roll %=' + pad2(pct2) + ': single, runners advance 2');
    return 'DONE';
  }
  const code = outLookup(S, bcard, pct2, batterName, 'OUT (H&R wheel)');
  elog(S, '  hit and run WHEELHOUSE re-roll %=' + pad2(pct2) + ': out -> ' + code);
  return yield* finishOutCode(G, S, batterName, code, presult, pct2, false, null);
}
function* finishSection(G, S, batterName, bcard, section, pct, lowD6, presult, hnr, hnrRunner) {
  // traits2's Fireman conversion sits on this seam.
  if (section === 'WHEELHOUSE' && masterOn(S) && S.flags.v2_fireman_armed && S.flags.v2_fireman_armed === curPitcher(S)) {
    S.flags.v2_fireman_armed = null;
    led(S, 'v2_fireman_conversion', 'the first WHEELHOUSE read against the Fireman converts to PATIENT (Williams)');
    elog(S, '  Fireman: the WHEELHOUSE read converts to PATIENT');
    section = 'PATIENT';
  }
  const fteam = fldTeam(S);
  const pcardNow = pitcherCard(G, S, fteam, curPitcher(S));
  const hand = pcardNow.throws === 'L' ? 'vsLHP' : 'vsRHP';
  const ps = pstat(S, fteam, curPitcher(S));
  if (section === 'WHEELHOUSE' && hnr) {
    return yield* hnrWheel(G, S, batterName, bcard, lowD6, presult, hnrRunner);
  }
  const r = sectionLookup(G, S, bcard, section, hand, pct);
  ps.BF += 1;
  if (r === null || r === undefined) {
    const code = outLookup(S, bcard, pct, batterName, section);
    elog(S, '  ' + section + ' %=' + pad2(pct) + ' above the ranges -> OUT ' + code);
    return yield* finishOutCode(G, S, batterName, code, presult, pct, hnr, hnrRunner);
  }
  elog(S, '  ' + section + ' %=' + pad2(pct) + ' -> ' + r);
  if (r === 'HR' || r === '1B' || r === '2B' || r === '3B') {
    if (hnr) hnrHit(G, S, batterName, r, pct);
    else {
      const desc = yield* resolveHit(G, S, batterName, r, section, pct, lowD6);
      elog(S, '  ' + desc);
    }
    return 'DONE';
  }
  if (r === 'BB' || r === 'HBP') { applyWalk(G, S, batterName, r); return 'DONE'; }
  if (r === 'SO') { yield* applySo(G, S, batterName, hnrRunner); return 'DONE'; }
  return 'DONE';
}
function* finishOutCode(G, S, batterName, code, presult, pct, hnr, hnrRunner) {
  const bteam = batTeam(S), fteam = fldTeam(S);
  const kind = code[0];
  if (hnr && kind === 'G') { yield* hnrGroundOut(G, S, batterName); return 'DONE'; }
  const desc = yield* resolveOutCode(G, S, batterName, code, presult, pct);
  elog(S, '  ' + desc);
  if (hnr && kind === 'L' && S.outs < 3 && S.bases.some(Boolean)) {
    const lead = Math.max(...[1, 2, 3].filter((b) => S.bases[b - 1]));
    const rd = {};
    for (const b of [1, 2, 3]) if (S.bases[b - 1]) rd[b] = b;
    const nm = S.bases[lead - 1].name;
    rd[lead] = 0;
    applyPlay(S, batterName, 0, rd, {});
    S.outs += 1; S.def_outs[fteam] += 1;
    elog(S, '  hit and run: line out doubles off ' + nm);
    led(S, 'hit_and_run', 'line out turned into a double play');
  }
  if (hnr && kind === 'F' && (code[1] === '8' || code[1] === '9')) {
    let ent = null;
    for (const e of S.bases) if (e && e.name === hnrRunner) ent = e;
    if (ent !== null) {
      const baseNow = S.bases.findIndex((e) => e && e.name === hnrRunner) + 1;
      if (baseNow > 1) {
        const [dd1, dd2] = yield* roll2d6(G, S);
        const d10 = yield* roll1d10(G, S);
        if (dd1 === dd2 && d10 > hcard(G, hnrRunner, bteam).run) {
          const rd = {};
          for (const b of [1, 2, 3]) if (S.bases[b - 1]) rd[b] = b;
          rd[baseNow] = 0;
          applyPlay(S, batterName, 0, rd, {});
          S.outs += 1; S.def_outs[fteam] += 1;
          elog(S, '  hit and run: ' + hnrRunner + ' thrown out returning to 1st');
          led(S, 'hit_and_run', 'runner thrown out returning on F8/F9');
        }
      }
    }
  }
  return 'DONE';
}

/* The engine's resolve_pa body. Manager blocks: for a profile
 * club the Python conditions apply whole; for a human club the
 * SITUATION gates the offer and the call itself is a decision
 * (spec 7.1). The hit-and-run usage cap (4) stays a hard gate. */
function* engineResolvePA(G, S) {
  if (S.pending) return 'PENDING';
  const bteam = batTeam(S), fteam = fldTeam(S);
  const tm = T(S, bteam);
  const [batterName, slotIdx] = currentBatter(S);
  const bcard = hcard(G, batterName, bteam);
  const pitcherName = curPitcher(S);
  const pcard = pitcherCard(G, S, fteam, pitcherName);
  const old = S.bases.slice();
  const inn = S.inning;
  const diff = S.score[bteam] - S.score[fteam];
  elog(S, '[' + inn + (S.half === 'top' ? 'T' : 'B') + ' ' + S.outs + ' out, bases ' + basesStr(S) + '] ' + batterName + ' vs ' + pitcherName);
  const human = !!G.human[bteam];
  // ---- manager: squeeze
  const squeezeSit = !!old[2] && S.outs === 1;
  const squeezePol = inn >= 8 && (diff === -1 || diff === 0) && slotIdx >= 6;
  if (squeezeSit && (squeezePol || human)) {
    let go = squeezePol;
    if (human && !squeezePol) {
      const ans = yield { decision: { kind: 'manager_call', call: 'squeeze', batter: batterName, slot: slotIdx } };
      go = !!(ans && ans.go);
    } else if (human && squeezePol) {
      const ans = yield { decision: { kind: 'manager_call', call: 'squeeze', batter: batterName, slot: slotIdx, policy: true } };
      go = ans ? !!ans.go : true;
    }
    if (go) {
      yield* resolveBunt(G, S, batterName, true);
      advanceOrder(S);
      return 'DONE';
    }
  }
  // ---- manager: sacrifice
  const sacSit = (old[0] || old[1]) && !(old[2] && !old[0] && !old[1]) && S.outs <= 1;
  const sacPol = slotIdx >= 6 && !(inn >= 7 && diff <= -4) &&
    ((old[0] && slotIdx >= 6) || (old[1] && S.outs === 0 && slotIdx >= 7));
  if (sacSit && (sacPol || human)) {
    let go = sacPol;
    if (human) {
      const ans = yield { decision: { kind: 'manager_call', call: 'sac', batter: batterName, slot: slotIdx, policy: sacPol } };
      go = ans ? !!ans.go : sacPol;
    }
    if (go) {
      yield* resolveBunt(G, S, batterName, false);
      advanceOrder(S);
      return 'DONE';
    }
  }
  // ---- manager: send the runner
  const sendSit = !!old[0] && !old[1] && S.outs === 2;
  let sendPol = false;
  if (sendSit) {
    const rc = hcard(G, old[0].name, bteam);
    sendPol = slotIdx >= 7 && !!rc.steal.jump && rc.steal.jump >= 4 && (rc.steal.rating === 'B' || rc.steal.rating === 'C');
  }
  if (sendSit && (sendPol || human)) {
    let go = sendPol;
    if (human) {
      const ans = yield { decision: { kind: 'manager_call', call: 'send', runner: old[0].name, batter: batterName, slot: slotIdx, policy: sendPol } };
      go = ans ? !!ans.go : sendPol;
    }
    if (go) {
      const [, , tot] = yield* roll2d6(G, S);
      if (tot === 12) {
        led(S, 'gap_pickoff', 'Manager-sent steal: 2d6=12 pickoff check cannot be resolved (no Hold rating on converted pitcher cards); runner holds');
      } else {
        led(S, 'manager_steal_send', old[0].name + ' sent with 2 outs, ' + batterName + ' at the plate');
        yield* attemptSteal(G, S, old[0], 2, bcard.bats);
        if (S.outs >= 3) return 'DONE';
      }
    }
  }
  // ---- hit and run call
  let hnr = false;
  const hnrSit = !!old[0] && S.outs <= 1;
  let hnrPol = false;
  if (hnrSit) {
    const rc = hcard(G, old[0].name, bteam);
    const used = (S.ledger.hit_and_run || { count: 0 }).count;
    hnrPol = [5, 6, 7, 8].includes(slotIdx) && !!rc.steal.jump && rc.steal.jump >= 4 && used < 4;
  }
  if (hnrSit && (hnrPol || human)) {
    let go = hnrPol;
    if (human) {
      const used = (S.ledger.hit_and_run || { count: 0 }).count;
      if (used < 4) {
        const ans = yield { decision: { kind: 'manager_call', call: 'hnr', runner: old[0].name, batter: batterName, slot: slotIdx, policy: hnrPol } };
        go = ans ? !!ans.go : hnrPol;
      } else go = false;
    }
    if (go) {
      hnr = true;
      led(S, 'hit_and_run', 'hit and run called: ' + old[0].name + ' on 1st, ' + batterName + ' hitting');
      elog(S, '  hit and run is on');
    }
  }
  const hnrRunner = hnr && old[0] ? old[0].name : null;
  let restarts = 0;
  while (true) {
    const [d1, d2, total] = yield* roll2d6(G, S);
    const pct = yield* rollpct(G, S);
    const presult = pcard.card_table_2d6[String(total)];
    if (pct === 0) {
      const grp = { BALLPARK: 'BW', WHEELHOUSE: 'BW', PATIENT: 'PATIENT', 'PATIENT-OUT': 'PATIENT',
        TOUGH: 'TOUGH', 'TOUGH-OUT': 'TOUGH', 'IN-PLAY': 'INPLAY', '/IN-PLAY/': 'INPLAY',
        'IN-PLAY [SINGLE]': 'INPLAY', DEFENSE: 'DEFENSE', ERROR: 'DEFENSE', RANGE: 'DEFENSE' }[presult];
      S.pending = { type: 'rare', grp: grp, bases_empty: !S.bases.some(Boolean),
        pitcher_result: presult, batter: batterName, slot_idx: slotIdx, dice: [d1, d2, total],
        inning: inn, half: S.half, outs: S.outs, hnr: hnr };
      led(S, 'rare_play_trigger', 'initial % = 00, pitcher result ' + presult + ', bases ' + (S.bases.some(Boolean) ? 'occupied' : 'empty'));
      return 'PENDING';
    }
    const res = yield* resolvePaInner(G, S, batterName, bcard, pcard, presult, total, pct, d1, d2, hnr, hnrRunner);
    if (res === 'RESTART') {
      restarts += 1;
      if (restarts > 3) {
        elog(S, '  repeated dropped fouls; at-bat resolved as a foul ball, PA continues no further (logged)');
        led(S, 'dropped_foul', 'restart cap reached');
        advanceOrder(S);
        return 'DONE';
      }
      continue;
    }
    advanceOrder(S);
    if (S.bases.some((e) => e && e.name === batterName) && S.outs < 3) {
      yield* autoStealCheck(G, S, batterName, total, [d1, d2]);
    }
    return 'DONE';
  }
}
/* The composed resolve_pa: Chance's cycles, then traits2's
 * dispatcher (shift arming + post bookkeeping), then the fatigue
 * book's pre-pass, the addendum's WP arm, and the engine body. */
function* resolvePA(G, S) {
  const asg = chanceAsg(S);
  if (asg && !S.pending) {
    const rt = chanceRt(S);
    if (rt.leader_pa) rt.leader_unread += 1;
    if (rt.acct_pa) {
      rt.acct_spent_unread += 1;
      led(S, 'chance_acct_spent', 'the owed strikeout chance was spent on a PA that never read TOUGH');
    }
    rt.leader_pa = null;
    rt.acct_pa = null;
    if (batTeam(S) === asg.team) chanceLeaderCycle(G, S);
    if (fldTeam(S) === asg.team) chanceAcctCycle(G, S);
  }
  if (S.pending) return 'PENDING';
  const fl = S.flags;
  if (masterOn(S) && fl.v2_shift_pending && batTeam(S) === 'OPP') {
    fl.v2_shift_pending = false;
    fl.v2_shift_live = true;
    fl.v2_shift_applied = false;
  }
  let res;
  if (!S.pending && G.fatigueBook !== false) {
    const ff = ffState(S);
    ff.pa_index += 1;
    const pre = ffPrecheck(G, S);
    ffEvaluate(G, S, 'pre', pre);
    void pre;
  }
  S._add_wp_armed = true;
  try {
    res = yield* engineResolvePA(G, S);
  } finally {
    delete S._add_wp_armed;
  }
  if (res !== 'PENDING') {
    if (fl.v2_shift_live) {
      if (!fl.v2_shift_applied) led(S, 'v2_late_sub_shift_expired', 'the late-inning sub shift went unread this PA');
      fl.v2_shift_live = false;
      fl.v2_shift_applied = false;
    }
  }
  return res;
}
/* The composed update_fatigue: the book's precheck, the engine's
 * 6-run rule inside the book's post pass, then Williams'
 * attrition. Called by the driver after every PA. */
function traits2Attrition(G, S) {
  if (masterOn(S)) {
    const fteam = fldTeam(S);
    const cur = curPitcher(S);
    const att = (S.flags.v2_attrition || {})[fteam + '|' + cur] || 0;
    const ps = pstat(S, fteam, cur);
    if (att && !ps.fatigued && ps.R + att >= 6) {
      ps.fatigued = true;
      led(S, 'v2_attrition_fatigue', cur + ' is fatigued: ' + ps.R + ' runs allowed plus attrition ' + att + ' reaches the 6-run line (Williams Strategic Attrition)');
      elog(S, '  ' + cur + ' is fatigued (runs plus Williams attrition reach the line)');
    }
  }
}
function updateFatigue(G, S) {
  if (G.fatigueBook === false) { engineUpdateFatigue(G, S); traits2Attrition(G, S); return; }
  const pre = ffPrecheck(G, S);
  if (!pre.suppressed) engineUpdateFatigue(G, S);
  ffEvaluate(G, S, 'post', pre);
  traits2Attrition(G, S);
}

/* ------------------------------------------------------------ driver */
function enforceCloser(G, S) {
  if (S.inning < 9 || S.final) return;
  const fteam = fldTeam(S);
  const tm = T(S, fteam);
  const lead = S.score[fteam] - S.score[batTeam(S)];
  if (!(lead >= 1 && lead <= 3)) return;
  const cur = tm.pitcher;
  const ps = pstat(S, fteam, cur);
  if (ps.entered_inning !== 1 || tm.pen.includes(cur)) return;
  let realOuts = null;
  for (const sp of S.pitcher_spans) {
    if (sp.team === fteam && sp.name === cur && sp.end === null) realOuts = S.def_outs[fteam] - sp.start[2];
  }
  if (realOuts === null || realOuts < 21) return;
  if (!tm.pen.length) return;
  const pick = pickReliever(G, S, fteam, 'closer');
  if (pick === cur) return;
  changePitcher(G, S, fteam, 'closer');
  led(S, 'closer_branch_enforced', 'governing closer rule from Game 2 (Joe, 2026-10-23): ' + pick + ' in for ' + cur + ' in the ' + S.inning + 'th, lead ' + lead + ', ' + realOuts + ' outs recorded');
}
function maybeReshuffle(G, S) {
  const inn = S.inning;
  if (inn >= 4 && (inn - 1) % 3 === 0 && !S.deck.reshuffleDone.includes(inn)) {
    if (S.source && S.source.reshuffle) S.source.reshuffle(S, 'after ' + (inn - 1) + ' full innings (printed protocol)', inn);
  }
}
function closeCheck(G, S) {
  const need = S.outs_needed || 3;
  const home = S.home, away = home === 'CHC' ? 'OPP' : 'CHC';
  if (S.half === 'bottom' && S.inning >= 9 && S.score[home] > S.score[away]) {
    S.final = { reason: 'walk-off / home lead in bottom 9th+' };
    return true;
  }
  if (S.outs >= need) {
    const justHalf = S.half, justInn = S.inning;
    S.last_def_pitcher = curPitcher(S);
    S.outs = 0;
    S.bases = [null, null, null];
    S.woudouts = 0;
    if (justHalf === 'top') {
      S.half = 'bottom';
      if (justInn >= 9 && S.score[home] > S.score[away]) {
        S.final = { reason: 'home leads after top 9th+' };
        return true;
      }
    } else {
      S.half = 'top';
      S.inning += 1;
      if (justInn >= 9 && S.score[home] !== S.score[away]) {
        S.final = { reason: 'game over after ' + justInn + ' innings' };
        return true;
      }
    }
    return false;
  }
  return false;
}
const RARE_CHART_NAME = {
  'empty|BW': 'Rare Plays: Bases Empty, BALLPARK or WHEELHOUSE',
  'empty|PATIENT': 'Rare Plays: Bases Empty, PATIENT',
  'empty|TOUGH': 'Rare Plays: Bases Empty, TOUGH',
  'empty|INPLAY': 'Rare Plays: Bases Empty, IN-PLAY',
  'empty|DEFENSE': 'Rare Plays: Bases Empty, DEFENSE',
  'on|BW': 'Rare Plays: Runners On, BALLPARK or WHEELHOUSE',
  'on|PATIENT': 'Rare Plays: Runners On, PATIENT',
  'on|TOUGH': 'Rare Plays: Runners On, TOUGH',
  'on|INPLAY': 'Rare Plays: Runners On, IN-PLAY',
  'on|DEFENSE': 'Rare Plays: Runners On, DEFENSE',
};
function spendForceClause(S, pitcherName) {
  const f = S.flags.force_clause;
  if (!f || f.pitcher !== pitcherName) return null;
  if (f.tough_until_hit) return 'TOUGH';
  for (const [key, sec] of [['wheelhouse', 'WHEELHOUSE'], ['tough', 'TOUGH'], ['inplay', 'IN-PLAY']]) {
    if (f[key] > 0) {
      f[key] -= 1;
      if (f.wheelhouse <= 0 && f.tough <= 0 && f.inplay <= 0 && !f.tough_until_hit) delete S.flags.force_clause;
      return sec;
    }
  }
  return null;
}
/* Rare resolution, the governed stack's auto_resolve: flip the
 * chart matching base state and section family at a fresh
 * percentile; a pitcher-removal entry takes him out (and checks
 * injury where its text orders one); the PA then completes on
 * its own section at a further fresh percentile. The printed
 * force clauses are the governed-vs-hand seam (spec 6.1.8):
 * with clauses on (app play), the Runners On TOUGH 70-74 entry
 * arms the outcome-dependent next-three flags; entries whose
 * condition is a SO/9 the converted cards do not carry (45-54,
 * 55-59) ledger the gap, as the recorded hand-resolutions did.
 * With clauses off (both replays, the distribution run) no
 * flags are set, matching the recorded environments. */
function* autoResolveRare(G, S) {
  const pend = S.pending;
  const chartName = RARE_CHART_NAME[(pend.bases_empty ? 'empty' : 'on') + '|' + pend.grp];
  const chart = PlayData.data.rare_plays.find((p) => p.name === chartName).chart;
  const flip = yield* rollpct(G, S);
  const ent = chart.find((e) => {
    const r = e.range;
    if (Array.isArray(r)) return r[0] <= flip && flip <= r[1];
    const parts = String(r).split('-');
    return parseInt(parts[0], 10) <= flip && flip <= parseInt(parts[1], 10);
  });
  const fteam = fldTeam(S);
  const pname = curPitcher(S);
  const batterName = pend.batter;
  const bsBefore = Object.assign({}, bstat(S, batTeam(S), batterName));
  elog(S, '  RARE PLAY (' + chartName + '): flip %=' + pad2(flip) + ' -> [' + (Array.isArray(ent.range) ? ent.range.join('-') : ent.range) + '] ' + ent.result);
  const text = ent.result.toLowerCase();
  if (text.includes('pitcher') && text.includes('removed') && (text.includes('may not return') || text.includes('must be removed'))) {
    T(S, fteam).removed.push(pname);
    removePitcher(G, S, fteam, 'rare play');
    if (text.includes('injur')) yield* injuryCheck(G, S, pname, fteam, 'rare play');
  } else {
    led(S, 'bulk_auto_resolve', 'auto-resolved rare play on ' + chartName + ': flip ' + flip + ' -> ' + (Array.isArray(ent.range) ? ent.range.join('-') : ent.range));
  }
  S.pending = null;
  const section = { INPLAY: 'IN-PLAY', BW: 'BALLPARK' }[pend.grp] || pend.grp;
  let bd1, bd2, btot;
  if (pend.dice) { [bd1, bd2, btot] = pend.dice; }
  else { const r = yield* roll2d6(G, S); [bd1, bd2, btot] = r; }
  let restarts = 0;
  let finalRes = 'DONE';
  while (true) {
    const pct = yield* rollpct(G, S);
    const bcard = hcard(G, batterName, batTeam(S));
    const res = yield* resolvePaInner(G, S, batterName, bcard, pitcherCard(G, S, fteam, curPitcher(S)), section, btot, pct, bd1, bd2, false, null);
    if (res === 'RESTART') {
      restarts += 1;
      if (restarts > 3) {
        led(S, 'dropped_foul', 'auto-resolve: restart cap reached');
        break;
      }
      continue;
    }
    finalRes = res;
    break;
  }
  /* The governed stack's completion does NOT advance the batting
   * order (chance_setup._complete_pa_on_section): the same batter
   * leads off the next inning after a rare-ended half. Recorded
   * behavior, ported as-is (Replay A PA73 -> PA77 is the proof
   * case: Grace lines out to end the 8th on a rare completion and
   * leads off the 9th). */
  if (S.bases.some((e) => e && e.name === batterName) && S.outs < 3) {
    yield* autoStealCheck(G, S, batterName, btot, [bd1, bd2]);
  }
  if (G.clauses) {
    const rng = Array.isArray(ent.range) ? ent.range.join('-') : String(ent.range);
    if (chartName === 'Rare Plays: Runners On, TOUGH' && rng === '70-74') {
      const bsAfter = bstat(S, batTeam(S), batterName);
      const f = { pitcher: pname, wheelhouse: 0, tough: 0, inplay: 0, tough_until_hit: false };
      if ((bsAfter.SO || 0) > (bsBefore.SO || 0)) f.tough = 3;
      else if ((bsAfter.H || 0) > (bsBefore.H || 0)) f.wheelhouse = 3;
      else f.inplay = 3;
      S.flags.force_clause = f;
      led(S, 'force_clause', 'Runners On TOUGH 70-74: the next three batters ' + pname + ' faces read the ' + (f.tough ? 'TOUGH' : f.wheelhouse ? 'WHEELHOUSE' : 'IN-PLAY') + ' section (printed clause, spec 6.1.8)');
    } else if (chartName === 'Rare Plays: Runners On, TOUGH' && (rng === '45-54' || rng === '55-59')) {
      led(S, 'gap_so9_clause', 'rare entry ' + rng + ' turns on a SO/9 the converted cards do not carry; its force clause is not applied (the recorded hand-resolutions logged the same gap)');
    }
  }
  return finalRes;
}
/* One full driver step: closer rule, protocol reshuffle, the
 * pre-PA traits hook (governed mode), one PA including its
 * pending-rare resolution. Yields step/decision objects from the
 * layers below. Returns 'PA_DONE', 'FINAL', or 'PENDING_RARE'
 * (app play stops at a rare so the feed can be read first). */
function* gameStep(G, S, opts) {
  opts = opts || {};
  if (opts.beforePA) opts.beforePA(S);
  enforceCloser(G, S);
  maybeReshuffle(G, S);
  const bt = batTeam(S);
  while (S.linescore[bt].length < S.inning) S.linescore[bt].push(0);
  if (G.prePa) yield* prePa(G, S);
  let res = yield* resolvePA(G, S);
  let guard = 0;
  while (res === 'PENDING') {
    if (opts.stopAtRare) yield { pause: 'rare' };
    yield* autoResolveRare(G, S);
    res = S.pending ? (yield* resolvePA(G, S)) : 'DONE';
    guard += 1;
    if (guard > 6) break;
  }
  if (opts.afterPA) yield* opts.afterPA(S);
  // a force clause keyed to a lifted pitcher dies with his outing
  if (G.clauses && S.flags.force_clause && S.flags.force_clause.pitcher !== curPitcher(S)) {
    delete S.flags.force_clause;
  }
  updateFatigue(G, S);
  if (S.outs < 3) maybeHook(G, S);
  if (closeCheck(G, S)) return 'FINAL';
  return 'PA_DONE';
}
function* runGame(G, S, opts) {
  let steps = 0;
  while (!S.final && steps < 1200) {
    const r = yield* gameStep(G, S, opts);
    if (r === 'PENDING_RARE') return 'PENDING_RARE';
    steps += 1;
  }
  return S.final ? 'FINAL' : 'STEP_CAP';
}

/* ============================================================
 * PART 5a: game context, the step driver, audits, decisions,
 * snapshots. (UI modules follow in Part 5b.)
 * ========================================================== */
function makeContext(cfg) {
  const fx = PlayData.data.fixture;
  const homeClub = cfg.homeSlot === 'CHC' ? 'CHC' : 'MON';
  return {
    starters: cfg.starters,
    penRole: { CHC: fx.pen_roles.CHC, OPP: fx.pen_roles.MON },
    allPenNames: new Set([...fx.pens.CHC, ...fx.pens.MON]),
    park: PlayData.data.parks[fx.clubs[homeClub].park],
    fatigueBook: cfg.fatigueBook !== false,
    buntOverlay: !!cfg.buntOverlay,
    defenseNumbers: !!cfg.defenseNumbers,
    clauses: !!cfg.clauses,
    prePa: !!cfg.prePa,
    human: cfg.human || { CHC: false, OPP: false },
  };
}
/* The recorded traits block for this fixture (spec 3): Chance
 * manages Chicago, Williams manages Montreal, traits5 inert. */
function fixtureTraits() {
  return { on: true, version: 5, v2: true, elimination: [], governed: true,
    frank_chance: { manager: 'Frank Chance', team: 'CHC', club: 'CHC', profile: 'profiles/frank-chance.md' },
    williams: { manager: 'Dick Williams', team: 'OPP', club: 'MON', package: 'late-game v2' } };
}
/* Drive a generator to completion: steps are served by the
 * state's source; decisions go to the decide callback (null in
 * auto play, where the engine's policy defaults apply). */
function drive(gen, S, decide) {
  let r = gen.next();
  while (!r.done) {
    const y = r.value;
    if (y && y.step) r = gen.next(S.source.serve(y.step, S));
    else if (y && y.decision) r = gen.next(decide ? decide(y.decision, S) : undefined);
    else r = gen.next();
  }
  return r.value;
}
/* The Section 10 S5 audit equalities, run by the end screen,
 * the export, and the test batteries. Returns a list of
 * {check, ok, detail}; the port never adjusts a number to pass. */
function auditGame(G, S) {
  const out = [];
  const clubs = ['CHC', 'OPP'];
  const sum = (obj, k) => Object.values(obj).reduce((a, b) => a + (b[k] || 0), 0);
  for (const t of clubs) {
    const o = t === 'CHC' ? 'OPP' : 'CHC';
    const ls = S.linescore[t].reduce((a, b) => a + b, 0);
    out.push({ check: t + ' score == linescore sum', ok: S.score[t] === ls, detail: S.score[t] + ' vs ' + ls });
    const bR = sum(S.teams[t].batting, 'R');
    out.push({ check: t + ' batting R == score', ok: bR === S.score[t], detail: bR + ' vs ' + S.score[t] });
    for (const k of ['H', 'BB', 'SO']) {
      const b = sum(S.teams[t].batting, k), p = sum(S.teams[o].pitching, k);
      out.push({ check: t + ' batting ' + k + ' == opposing pitching', ok: b === p, detail: b + ' vs ' + p });
    }
    let pa = 0;
    for (const bs of Object.values(S.teams[t].batting)) pa += bs.AB + bs.BB + (bs.HBP || 0) + (bs.SH || 0) + (bs.SF || 0);
    const bf = sum(S.teams[o].pitching, 'BF');
    out.push({ check: t + ' PA == opposing BF', ok: pa === bf, detail: pa + ' vs ' + bf });
    let spanOuts = 0;
    for (const sp of S.pitcher_spans) {
      if (sp.team !== t) continue;
      spanOuts += (sp.end ? sp.end[2] : S.def_outs[t]) - sp.start[2];
    }
    out.push({ check: t + ' span outs == defensive outs', ok: spanOuts === S.def_outs[t], detail: spanOuts + ' vs ' + S.def_outs[t] });
  }
  return out;
}
/* W/L/SV derivation, ported from the table game's audit module:
 * go-ahead-for-good from the run events and spans; the save by
 * the house entry-state standard (entered with a lead of 1-3,
 * or pitched 3+ innings to finish). Labeled derived. */
function deriveDecisions(S) {
  const winner = S.score.CHC >= S.score.OPP ? 'CHC' : 'OPP';
  const loser = winner === 'CHC' ? 'OPP' : 'CHC';
  const evs = S.run_events;
  let gtg = null;
  for (let i = 0; i < evs.length; i++) {
    if (evs[i].score[winner] > evs[i].score[loser] &&
        evs.slice(i).every((e2) => e2.score[winner] > e2.score[loser])) { gtg = i; break; }
  }
  let wp = null, lp = null, save = null;
  if (gtg !== null) {
    const ev = evs[gtg];
    const key = (ih) => [ih[0], ih[1] === 'top' ? 0 : 1];
    const keyCmp = (a, b) => a[0] - b[0] || a[1] - b[1];
    const pitcherAt = (team, inn, half) => {
      const target = key([inn, half]);
      for (const sp of S.pitcher_spans) {
        if (sp.team !== team) continue;
        const start = key(sp.start.slice(0, 2));
        const end = sp.end ? key(sp.end.slice(0, 2)) : [99, 1];
        if (keyCmp(start, target) <= 0 && keyCmp(target, end) <= 0) return sp.name;
      }
      return null;
    };
    wp = pitcherAt(winner, ev.inning, ev.half);
    lp = pitcherAt(loser, ev.inning, ev.half);
    const wspans = S.pitcher_spans.filter((sp) => sp.team === winner);
    if (wspans.length) {
      const lastSp = wspans[wspans.length - 1];
      if (lastSp.name !== wp) {
        const outsPitched = S.def_outs[winner] - lastSp.start[2];
        const startKey = key(lastSp.start.slice(0, 2));
        let sc = { CHC: 0, OPP: 0 };
        for (const e2 of evs) {
          if (keyCmp(key([e2.inning, e2.half]), startKey) <= 0) sc = Object.assign({}, e2.score);
        }
        const entryLead = sc[winner] - sc[loser];
        if ((entryLead >= 1 && entryLead <= 3) || outsPitched >= 9) save = lastSp.name;
      }
    }
  }
  return { winner: winner, W: wp, L: lp, SV: save,
    basis: 'derived from run events and pitcher spans (go-ahead-for-good); save by the house entry-state standard' };
}
/* Snapshots for undo (spec 5.4): the whole state minus the
 * source object; deck state rides inside S.deck. Feed entries
 * after the snapshot point are marked undone, never deleted. */
function snapshotState(S) {
  const c = deepCopy(S);
  return c;
}
function restoreState(S, snap) {
  const keepSource = S.source;
  for (const k of Object.keys(S)) delete S[k];
  Object.assign(S, deepCopy(snap));
  S.source = keepSource;
}

/* ================================================================
 * Part 5b: Profiles / GameState / Feed / Export (spec sections
 * 5.3-5.4, 7, 9, 10). Headless-safe: the UI at the bottom of the
 * file is the only DOM consumer. GameState owns the timeline:
 * snapshots at PA boundaries and managerial actions, the feed
 * blocks (live/undone), the autosave, and the seal on export.
 * ================================================================ */
const SAVE_PREFIX = 'pp-play-r106-';
const SUFFIX_CHARS = 'abcdefghjkmnpqrstuvwxyz23456789';
function makeSuffix(rng) {
  let s = '';
  for (let i = 0; i < 4; i++) s += SUFFIX_CHARS[Math.floor(rng() * SUFFIX_CHARS.length)];
  return s;
}
/* S1 lineup legality (a)-(c): coverage exactly once, fielders
 * only at printed positions (DH any hitter), no duplicates,
 * all rostered. Returns a list of violated-rule strings. */
function lineupLegality(lineup, club) {
  const problems = [];
  const roster = PlayData.data.hitters[club];
  const need = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH'];
  if (!Array.isArray(lineup) || lineup.length !== 9) return ['the lineup must name nine men'];
  const seen = new Set(), covered = new Set();
  for (const slot of lineup) {
    if (!roster[slot.name]) { problems.push(slot.name + ' is not rostered for ' + club); continue; }
    if (seen.has(slot.name)) problems.push(slot.name + ' appears twice');
    seen.add(slot.name);
    if (!need.includes(slot.pos)) { problems.push(slot.pos + ' is not a lineup position'); continue; }
    if (covered.has(slot.pos)) problems.push(slot.pos + ' is covered twice');
    covered.add(slot.pos);
    if (slot.pos !== 'DH') {
      const carded = (roster[slot.name].positions || []).some((p) => p.pos === slot.pos);
      if (!carded) problems.push(slot.name + ' is not carded at ' + slot.pos);
    }
  }
  for (const p of need) if (!covered.has(p)) problems.push(p + ' is not covered');
  return problems;
}
/* S1 (e): a bench swap is legal when the incoming man is
 * carded at the outgoing man's position (any hitter for DH). */
function swapLegality(lineup, club, outName, inName) {
  const slot = lineup.find((s) => s.name === outName);
  if (!slot) return outName + ' is not in the lineup';
  if (lineup.some((s) => s.name === inName)) return inName + ' is already in the lineup';
  const card = PlayData.data.hitters[club][inName];
  if (!card) return inName + ' is not rostered for ' + club;
  if (slot.pos === 'DH') return null;
  return (card.positions || []).some((p) => p.pos === slot.pos) ? null
    : inName + ' is not carded at ' + slot.pos;
}

function createGame(cfg, storage) {
  const fx = PlayData.data.fixture;
  const seed = cfg.seed;
  const rng = cfg.suffixRng || Math.random;
  let suffix = cfg.suffix || makeSuffix(rng);
  let gameId = 'r106-' + seed + '-' + suffix;
  if (storage) {
    let guard = 0;
    while (storage.getItem(SAVE_PREFIX + gameId) && guard++ < 50) {
      suffix = makeSuffix(rng); gameId = 'r106-' + seed + '-' + suffix;
    }
  }
  const managers = cfg.managers;
  const G = makeContext({ homeSlot: cfg.homeSlot, starters: cfg.starters,
    buntOverlay: true, prePa: true, clauses: true, defenseNumbers: true,
    human: { CHC: managers.CHC === 'human', OPP: managers.OPP === 'human' } });
  const S = newState(G, { seed, homeSlot: cfg.homeSlot, starters: cfg.starters,
    traits: fixtureTraits(), lineups: cfg.lineups, benches: cfg.benches });
  const sources = {
    deck: DeckSource,
    dice: makeDiceSource((seed ^ 0x9e3779b9) >>> 0),
    manual: makeManualSource(),
  };
  const GS = {
    G, S, cfg: { seed, homeSlot: cfg.homeSlot, starters: cfg.starters,
      lineups: cfg.lineups || null, benches: cfg.benches || null, managers },
    gameId, suffix, seed,
    exportId: 'EXHIBITION-CHC-MON-' + seed + '-' + suffix,
    sources, sourceKind: cfg.sourceKind || 'deck',
    feed: [], undoStack: [], paCount: 0, undoCount: 0,
    gen: null, logMark: 0, pendingStep: null, pendingDecision: null,
    sealed: false, storageOk: true, storageWarned: false, finished: false,
    setupBlock: { fixture: fx.id, label: fx.label, home: cfg.homeSlot,
      venue: fx.clubs[cfg.homeSlot === 'CHC' ? 'CHC' : 'MON'].park,
      starters: cfg.starters, closers: fx.closers, managers,
      diceMode: cfg.sourceKind || 'deck', seed },
  };
  S.source = sources[GS.sourceKind];
  GS._storage = storage || null;

  GS.setSource = function (kind) {
    if (S.deck.peek) return 'a manual 2d6 peek is outstanding (FAC ' + S.deck.peek + '); flip it or undo the PA before switching';
    if (!sources[kind]) return 'unknown source ' + kind;
    GS.sourceKind = kind; S.source = sources[kind];
    GS.setupBlock.diceMode = kind;
    return null;
  };
  GS._snapshot = function () {
    GS.undoStack.push({ snap: snapshotState(S), feedLen: GS.feed.length, paCount: GS.paCount });
    if (GS.undoStack.length > 200) GS.undoStack.shift();
  };
  GS._feedBlock = function (action) {
    const lines = S.log.slice(GS.logMark);
    GS.logMark = S.log.length;
    if (lines.length) GS.feed.push({ pa: GS.paCount, lines, live: true, action: !!action });
  };
  GS.save = function () {
    if (!GS._storage) return;
    try {
      const payload = { version: 1, gameId: GS.gameId, cfg: GS.cfg, sourceKind: GS.sourceKind,
        state: snapshotState(S), feed: GS.feed, paCount: GS.paCount, undoCount: GS.undoCount,
        setupBlock: GS.setupBlock, finished: GS.finished };
      delete payload.state.source;
      GS._storage.setItem(SAVE_PREFIX + GS.gameId, JSON.stringify(payload));
      GS.storageOk = true;
    } catch (e) {
      GS.storageOk = false;
      if (!GS.storageWarned) {
        GS.storageWarned = true;
        GS.feed.push({ pa: GS.paCount, lines: ['Saved indicator: storage unavailable — this game is being kept in memory only (' + (e && e.message ? e.message : 'write failed') + ').'], live: true, action: true });
      }
    }
  };
  GS._decisionClub = function (dec) {
    if (dec.kind === 'coverage') return dec.team;
    return batTeam(S);
  };
  GS._pump = function (answer) { return GS._pumpFrom(GS.gen.next(answer)); };
  GS._pumpFrom = function (r0) {
    let r = r0;
    let guard = 0;
    while (!r.done) {
      const y = r.value;
      if (y && y.step) {
        let v;
        try { v = S.source.serve(y.step, S); }
        catch (e) {
          if (GS.sourceKind === 'manual') { GS.pendingStep = y.step; return { status: 'STEP', kind: y.step, error: e.message }; }
          throw e;
        }
        r = GS.gen.next(v);
      } else if (y && y.decision) {
        const club = GS._decisionClub(y.decision);
        if (GS.cfg.managers[club] === 'human') {
          GS.pendingDecision = y.decision;
          return { status: 'DECISION', decision: y.decision };
        }
        r = GS.gen.next(undefined);
      } else if (y && y.pause === 'rare') {
        return { status: 'RARE' };
      } else {
        r = GS.gen.next();
      }
      if (++guard > 20000) throw new Error('game pump guard tripped');
    }
    const res = r.value;
    GS.gen = null;
    GS.paCount += 1;
    GS._feedBlock(false);
    if (res === 'FINAL') GS.finished = true;
    GS.save();
    return { status: res };
  };
  /* Play one plate appearance (or resume a parked one). */
  GS.step = function () {
    if (GS.sealed) return { status: 'SEALED' };
    if (GS.finished) return { status: 'FINAL' };
    if (!GS.gen) {
      GS._snapshot();
      GS.logMark = S.log.length;
      GS.gen = gameStep(G, S, { stopAtRare: true });
    }
    return GS._pump(undefined);
  };
  GS.answer = function (ans) {
    GS.pendingDecision = null;
    return GS._pump(ans);
  };
  GS.resumeRare = function () { return GS._pump(undefined); };
  GS.provide = function (input) {
    if (!GS.pendingStep) return { status: 'NO_STEP' };
    const kind = GS.pendingStep;
    GS.manualProvide(input);
    let v;
    try { v = S.source.serve(kind, S); }
    catch (e) { return { status: 'STEP', kind, error: e.message }; }
    GS.pendingStep = null;
    return GS._pumpFrom(GS.gen.next(v));
  };
  GS.manualProvide = function (input) {
    const src = sources.manual;
    const v = Object.assign({}, input);
    if (v.form === 'card') { v.pa = GS.paCount + 1; v.stepLabel = GS.pendingStep; }
    src.provide(v);
  };
  /* Managerial actions between plate appearances. Each is a
   * snapshot point and an autosave point. */
  GS.act = function (action, decide) {
    if (GS.sealed || GS.finished || GS.gen) return { status: 'BUSY' };
    GS._snapshot();
    GS.logMark = S.log.length;
    if (action.kind === 'pitch') {
      changePitcher(G, S, action.slot, action.name);
    } else if (action.kind === 'ph') {
      pinchHit(S, action.slot, action.out, action.name, action.reason || 'pinch hit');
    } else if (action.kind === 'pr') {
      pinchRun(S, action.slot, action.out, action.name, action.reason || 'pinch run');
    } else if (action.kind === 'sub') {
      drive(substitute(G, S, action.slot, action.out, action.reason || 'substitution'), S, decide);
    } else if (action.kind === 'defsub') {
      const tm = T(S, action.slot);
      const slotE = tm.order.find((s) => s.name === action.out);
      const pos = slotE ? slotE.pos : null;
      tm.bench.splice(tm.bench.indexOf(action.name), 1);
      tm.bench.push(action.out);
      tm.removed.push(action.out);
      if (slotE) slotE.name = action.name;
      if (pos && pos !== 'DH' && tm.field[pos] === action.out) tm.field[pos] = action.name;
      elog(S, '  substitution (' + TEAMNAME[action.slot] + '): ' + action.name + ' replaces ' + action.out + ' (defensive substitution, manager\'s call)');
      led(S, 'substitution', action.name + ' for ' + action.out + ' (defensive substitution)');
    } else {
      GS.undoStack.pop();
      return { status: 'UNKNOWN_ACTION' };
    }
    GS._feedBlock(true);
    GS.save();
    return { status: 'OK' };
  };
  GS.undo = function () {
    if (GS.sealed || !GS.undoStack.length) return false;
    const flipsBefore = S.flips.length;
    const consumedIds = S.flips.slice(GS.undoStack[GS.undoStack.length - 1].snap.flips.length)
      .map((f) => f.fac_id).filter((x) => x);
    const u = GS.undoStack.pop();
    restoreState(S, u.snap);
    S.source = sources[GS.sourceKind];
    for (let i = u.feedLen; i < GS.feed.length; i++) GS.feed[i].live = false;
    GS.paCount = u.paCount;
    GS.gen = null; GS.pendingStep = null; GS.pendingDecision = null;
    GS.finished = false;
    GS.undoCount += 1;
    const note = ['Undo: back to the end of PA ' + GS.paCount + '.'];
    if (GS.sourceKind === 'manual' && consumedIds.length) {
      note.push('Undo: return FAC ' + consumedIds.join(', FAC ') + ' to your deck; they are back in this cycle and may be flipped again.');
    } else if (consumedIds.length) {
      note.push('The ' + consumedIds.length + ' card(s) drawn in the undone span are restored to the deck.');
    }
    void flipsBefore;
    GS.feed.push({ pa: GS.paCount, lines: note, live: true, action: true });
    GS.logMark = S.log.length;
    GS.save();
    return true;
  };
  GS.audit = function () { return auditGame(G, S); };
  GS.decisions = function () { return deriveDecisions(S); };
  GS.exports = function () { return buildExports(GS); };
  GS.seal = function () {
    GS.sealed = true;
    if (GS._storage) { try { GS._storage.removeItem(SAVE_PREFIX + GS.gameId); } catch (e) { /* gone either way */ } }
  };
  return GS;
}
/* Resume support (S6): peek at the one saved game, if any. */
function peekSave(storage) {
  if (!storage) return null;
  try {
    for (let i = 0; i < storage.length; i++) {
      const k = storage.key(i);
      if (k && k.startsWith(SAVE_PREFIX)) {
        const p = JSON.parse(storage.getItem(k));
        const st = p.state;
        return { gameId: p.gameId, finished: !!p.finished,
          label: PlayData.data.fixture.label,
          inning: st.inning, half: st.half,
          score: st.score, paCount: p.paCount };
      }
    }
  } catch (e) { return null; }
  return null;
}
function loadSave(storage) {
  const peek = peekSave(storage);
  if (!peek) return null;
  const p = JSON.parse(storage.getItem(SAVE_PREFIX + peek.gameId));
  const GS = createGame(Object.assign({}, p.cfg, { suffix: p.gameId.split('-').pop() }), storage);
  restoreState(GS.S, p.state);
  GS.S.source = GS.sources[p.sourceKind || 'deck'];
  GS.sourceKind = p.sourceKind || 'deck';
  GS.feed = p.feed || [];
  GS.paCount = p.paCount || 0;
  GS.undoCount = p.undoCount || 0;
  GS.finished = !!p.finished;
  GS.setupBlock = p.setupBlock || GS.setupBlock;
  GS.logMark = GS.S.log.length;
  GS.feed.push({ pa: GS.paCount, lines: ['Resumed. The undo stack starts empty: nothing before this point can be undone.'], live: true, action: true });
  return GS;
}
function discardSave(storage) {
  const peek = peekSave(storage);
  if (peek) storage.removeItem(SAVE_PREFIX + peek.gameId);
  return peek;
}

/* ---------------------------------------------------------- exports */
function ipText(outs) { return Math.floor(outs / 3) + '.' + (outs % 3); }
function batLineRow(name, bs) {
  const pa = (bs.AB || 0) + (bs.BB || 0) + (bs.HBP || 0) + (bs.SH || 0) + (bs.SF || 0);
  return [name, pa, bs.AB || 0, bs.R || 0, bs.H || 0, bs['2B'] || 0, bs['3B'] || 0, bs.HR || 0,
    bs.RBI || 0, bs.BB || 0, bs.HBP || 0, bs.SO || 0, bs.SB || 0, bs.CS || 0, bs.GDP || 0];
}
function buildExports(GS) {
  const S = GS.S, fx = PlayData.data.fixture;
  const audit = auditGame(GS.G, S);
  const auditBad = audit.filter((a) => !a.ok);
  const dec = deriveDecisions(S);
  const clubName = (slot) => fx.clubs[PlayData.clubOf(slot)].name;
  const away = GS.cfg.homeSlot === 'CHC' ? 'OPP' : 'CHC';
  const home = GS.cfg.homeSlot;
  const today = new Date().toISOString().slice(0, 10);
  const md = [];
  md.push('# Exhibition Game: ' + clubName(away) + ' at ' + clubName(home));
  md.push('');
  md.push('**Game ID:** ' + GS.exportId);
  md.push('**Date:** ' + today);
  md.push('**Seed:** ' + GS.seed);
  md.push('**Game recap:** R1-06 fixture, exhibition. ' + clubName(home) + ' ' + S.score[home] + ', ' + clubName(away) + ' ' + S.score[away] + '.');
  md.push('**Series state after this game:** Exhibition, not a tournament game.');
  md.push('');
  const innings = Math.max(S.linescore[away].length, S.linescore[home].length, 9);
  const head = ['| ', ''];
  for (let i = 1; i <= innings; i++) head.push(String(i));
  head.push('R', 'H', 'E');
  md.push('| ' + head.slice(1).join(' | ') + ' |');
  md.push('|' + '---|'.repeat(innings + 4));
  for (const slot of [away, home]) {
    const cells = [fx.clubs[PlayData.clubOf(slot)].short];
    for (let i = 0; i < innings; i++) cells.push(String(S.linescore[slot][i] != null ? S.linescore[slot][i] : ''));
    const hTotal = Object.values(S.teams[slot].batting).reduce((a, b) => a + (b.H || 0), 0);
    cells.push(String(S.score[slot]), String(hTotal), String(S.teams[slot].team_errors));
    md.push('| ' + cells.join(' | ') + ' |');
  }
  md.push('');
  const decLine = [];
  if (dec.W) decLine.push('W: ' + dec.W + ' (' + clubName(dec.winner) + ')');
  if (dec.L) decLine.push('L: ' + dec.L + ' (' + clubName(dec.winner === 'CHC' ? 'OPP' : 'CHC') + ')');
  if (dec.SV) decLine.push('SV: ' + dec.SV + ' (' + clubName(dec.winner) + ')');
  md.push(decLine.length ? decLine.join(' · ') : 'Decisions: none recorded.');
  for (const slot of [away, home]) {
    md.push('');
    md.push('## ' + clubName(slot) + ' batting');
    md.push('');
    md.push('| Player | PA | AB | R | H | 2B | 3B | HR | RBI | BB | HBP | SO | SB | CS | GDP |');
    md.push('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|');
    const tm = S.teams[slot];
    const orderNames = [];
    for (const s of tm.order) if (!orderNames.includes(s.name)) orderNames.push(s.name);
    for (const nm of Object.keys(tm.batting)) if (!orderNames.includes(nm)) orderNames.push(nm);
    const tot = blankBstat();
    for (const nm of orderNames) {
      const bs = tm.batting[nm]; if (!bs) continue;
      md.push('| ' + batLineRow(nm, bs).join(' | ') + ' |');
      for (const k of Object.keys(tot)) tot[k] = (tot[k] || 0) + (bs[k] || 0);
    }
    md.push('| **Team** | ' + batLineRow('', tot).slice(1).join(' | ') + ' |');
    md.push('');
    md.push('## ' + clubName(slot) + ' pitching');
    md.push('');
    md.push('| Pitcher | IP | BF | H | R | ER | BB | SO |');
    md.push('|---|---|---|---|---|---|---|---|');
    for (const sp of S.pitcher_spans.filter((x) => x.team === slot)) {
      const ps = tm.pitching[sp.name]; if (!ps) continue;
      const outs = (sp.end ? sp.end[2] : S.def_outs[slot]) - sp.start[2];
      md.push('| ' + [sp.name, ipText(outs), ps.BF || 0, ps.H || 0, ps.R || 0, ps.ER || 0, ps.BB || 0, ps.SO || 0].join(' | ') + ' |');
    }
  }
  md.push('');
  md.push('Exhibition. This game is not in the tournament record. Adoption is Joe\'s ruling, outside the app.');
  if (auditBad.length) {
    md.push('');
    md.push('AUDIT: FAILED — ' + auditBad.map((a) => a.check + ' (' + a.detail + ')').join('; '));
    md.push('This export failed an internal audit check and is not adoption-ready.');
  }
  const governance = {
    audit: audit.map((a) => ({ check: a.check, ok: a.ok, detail: a.detail })),
    ledger: S.ledger,
    fatigue: S.fatigue_fix || null,
    spans: S.pitcher_spans,
    undo_count: GS.undoCount,
    fac: { draws: S.deck.draws, reshuffles: S.deck.reshuffles, mid_cycle: S.deck.midCycle },
    setup: GS.setupBlock,
  };
  const json = {
    id: GS.exportId, series: 'EXHIBITION', fixture: fx.id, seed: GS.seed,
    date: today, home: PlayData.clubOf(home), away: PlayData.clubOf(away),
    venue: GS.setupBlock.venue,
    score: { [PlayData.clubOf(away)]: S.score[away], [PlayData.clubOf(home)]: S.score[home] },
    linescore: { [PlayData.clubOf(away)]: S.linescore[away], [PlayData.clubOf(home)]: S.linescore[home] },
    decisions: dec,
    batting: { [PlayData.clubOf(away)]: S.teams[away].batting, [PlayData.clubOf(home)]: S.teams[home].batting },
    pitching: { [PlayData.clubOf(away)]: S.teams[away].pitching, [PlayData.clubOf(home)]: S.teams[home].pitching },
    rolls: S.flips,
    manager_log: GS.feed.filter((b) => b.live).map((b) => ({ pa: b.pa, action: !!b.action, lines: b.lines })),
    governance,
  };
  return { markdown: md.join('\n'), json, audit };
}


/* ============================================================
 * Part 5b (browser UI): PlayUI — Screens S0-S6 of spec Section 8.
 * Browser only; the Node export path above never touches it.
 * The card renderer below is a deliberate copy of bracket.js's
 * player-page renderer (cardSections and its helpers), adapted
 * to the playable data file: the pitcher carries
 * card_table_2d6 and merged scalar wp/dp/hold/inj. The parity
 * script (scripts/check_cardview_parity.py) fails the build if
 * the two renderers' orders or labels drift apart.
 * ========================================================== */
if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  const PUI = {};
  window.PlayUI = PUI;

  function el(tag, attrs) {
    const node = document.createElement(tag);
    const children = Array.prototype.slice.call(arguments, 2);
    if (attrs) {
      Object.keys(attrs).forEach(function (key) {
        const value = attrs[key];
        if (value == null || value === false) return;
        if (key === 'class') node.className = value;
        else if (key === 'text') node.textContent = value;
        else node.setAttribute(key, value === true ? '' : value);
      });
    }
    children.forEach(function (child) {
      if (child == null || child === false) return;
      node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
    });
    return node;
  }
  function bandText(band) { return band ? band[0] + '-' + band[1] : '—'; }
  function factChip(label, value, wide) {
    const text = value == null ? '—' : String(value);
    return el('span', { class: 'card-chip' + (wide || text.length > 18 ? ' wide' : '') },
      el('span', { class: 'card-k', text: label }),
      el('span', { class: 'card-v', text: text }));
  }
  function factRow(chips) {
    const kept = chips.filter(Boolean);
    if (!kept.length) return null;
    const row = el('div', { class: 'card-facts' });
    kept.forEach(function (chip) { row.appendChild(chip); });
    return row;
  }
  function bandHead(full, short, numeric) {
    return el('th', { class: numeric ? 'num' : null, scope: 'col' },
      el('span', { class: 'wide-label', text: full }),
      el('span', { class: 'phone-label', text: short }));
  }
  function cardBandTable(rows) {
    const wrap = el('div', { class: 'table-wrap card-band' });
    const t = el('table');
    t.appendChild(el('colgroup', null,
      el('col', { class: 'band-result' }), el('col', { class: 'band-num' }), el('col', { class: 'band-num' })));
    const head = el('tr');
    head.appendChild(bandHead('Result', 'Result', false));
    head.appendChild(bandHead('vs LHP', 'vs L', true));
    head.appendChild(bandHead('vs RHP', 'vs R', true));
    t.appendChild(el('thead', null, head));
    const body = el('tbody');
    rows.forEach(function (row) {
      const tr = el('tr');
      tr.appendChild(el('td', { text: row[0] }));
      tr.appendChild(el('td', { class: 'num', text: row[1] }));
      tr.appendChild(el('td', { class: 'num', text: row[2] }));
      body.appendChild(tr);
    });
    t.appendChild(body);
    wrap.appendChild(t);
    return wrap;
  }
  function fieldingLine(positions) {
    const list = el('div', { class: 'fielding-line' });
    positions.forEach(function (spot) {
      const row = el('div', { class: 'field-row' });
      row.appendChild(el('span', { class: 'field-pos', text: spot.pos || '' }));
      if (spot.range != null && spot.range !== '') row.appendChild(factChip('Range', spot.range));
      if (spot.e != null && spot.e !== '') row.appendChild(factChip('E', spot.e));
      if (spot.arm != null && spot.arm !== '') row.appendChild(factChip('Arm', spot.arm));
      list.appendChild(row);
    });
    return list;
  }
  function diceGrid(table) {
    const grid = el('div', { class: 'dice-grid' });
    ['2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'].forEach(function (total) {
      const text = table[total] || '—';
      grid.appendChild(el('div', { class: 'dice-cell' + (text.length > 12 ? ' wide' : '') },
        el('span', { class: 'card-k', text: total }),
        el('span', { class: 'card-v', text: text })));
    });
    return grid;
  }
  function hitterCardBlock(bat) {
    const block = el('section', { class: 'payoff-card' });
    block.appendChild(el('h4', { text: 'Hitter card' }));
    const bits = [];
    if (bat.bats) bits.push(factChip('Bats', bat.bats));
    if (bat.throws) bits.push(factChip('Throws', bat.throws));
    if (bat.run != null) bits.push(factChip('Run', bat.run));
    if (bat.steal) bits.push(factChip('Steal', bat.steal.rating + (bat.steal.jump != null ? ', jump ' + bat.steal.jump : '')));
    if (bat.sac_bunt) bits.push(factChip('Sac bunt', bat.sac_bunt));
    if (bat.dp != null) bits.push(factChip('DP', bat.dp));
    if (bat.fielding) bits.push(factChip('Fielding', bat.fielding));
    if (bat.arm) bits.push(factChip('Arm', bat.arm));
    const facts = factRow(bits);
    if (facts) block.appendChild(facts);
    if (bat.positions && bat.positions.length) block.appendChild(fieldingLine(bat.positions));
    ['WHEELHOUSE', 'PATIENT', 'TOUGH', 'IN-PLAY'].forEach(function (name) {
      const section = bat.sections && bat.sections[name];
      if (!section) return;
      block.appendChild(el('p', { class: 'meta', text: name + ' (percentile bands)' }));
      const rows = ['HR', '3B', '2B', '1B', 'BB', 'HBP', 'SO'].filter(function (result) {
        return (section.vsLHP && section.vsLHP[result]) || (section.vsRHP && section.vsRHP[result]);
      }).map(function (result) {
        return [result, bandText(section.vsLHP && section.vsLHP[result]), bandText(section.vsRHP && section.vsRHP[result])];
      });
      if (rows.length) block.appendChild(cardBandTable(rows));
    });
    if (bat.out_table && bat.out_table.length) {
      block.appendChild(el('p', { class: 'note', text: 'Out table: ' + bat.out_table.map(function (row) {
        return row.range[0] + '-' + row.range[1] + ' ' + row.result;
      }).join(' · ') }));
    }
    return block;
  }
  function pitcherCardBlock(pit) {
    const block = el('section', { class: 'payoff-card' });
    block.appendChild(el('h4', { text: 'Pitcher card' }));
    const pbits = [];
    if (pit.throws) pbits.push(factChip('Throws', pit.throws));
    if (pit.card_type) pbits.push(factChip('Type', pit.card_type));
    if (pit.so_modifier) pbits.push(factChip('SO modifier', pit.so_modifier));
    const special = pit.special && pit.special.length ? pit.special : pit.special_required;
    if (special && special.length) pbits.push(factChip('Special', Array.isArray(special) ? special.join(', ') : String(special), true));
    if (pit.stamina) {
      if (pit.stamina.start != null) pbits.push(factChip('Start', pit.stamina.start));
      if (pit.stamina.relief) pbits.push(factChip('Relief', pit.stamina.relief));
    }
    [['wp', 'WP'], ['dp', 'DP'], ['hold', 'Hold'], ['pickoff', 'Pickoff'], ['inj', 'Inj']].forEach(function (pair) {
      let value = pit[pair[0]];
      if (value == null && pit.addendum) value = pit.addendum[pair[0]];
      if (value != null && value !== '') pbits.push(factChip(pair[1], value));
    });
    const pfacts = factRow(pbits);
    if (pfacts) block.appendChild(pfacts);
    if (pit.card_table_2d6) {
      block.appendChild(el('p', { class: 'meta', text: '2d6 section' }));
      block.appendChild(diceGrid(pit.card_table_2d6));
    }
    return block;
  }
  function parkCardBlock(park) {
    const block = el('section', { class: 'payoff-card' });
    block.appendChild(el('h4', { text: park.name }));
    block.appendChild(el('p', { class: 'meta', text: 'BALLPARK (percentile bands)' }));
    const order = [];
    ['L', 'R'].forEach(function (side) {
      (park.ballpark_chart[side] || []).forEach(function (row) { if (!order.includes(row.result)) order.push(row.result); });
    });
    const rows = order.map(function (result) {
      const l = (park.ballpark_chart.L || []).find(function (r) { return r.result === result; });
      const r = (park.ballpark_chart.R || []).find(function (r) { return r.result === result; });
      return [result, l ? l.range[0] + '-' + l.range[1] : '—', r ? r.range[0] + '-' + r.range[1] : '—'];
    });
    block.appendChild(cardBandTable(rows));
    return block;
  }

  // -- storage (never throws) --------------------------------
  const store = {
    get length() { try { return window.localStorage.length; } catch (e) { return 0; } },
    key(i) { try { return window.localStorage.key(i); } catch (e) { return null; } },
    getItem(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } },
    setItem(k, v) { window.localStorage.setItem(k, v); },
    removeItem(k) { try { window.localStorage.removeItem(k); } catch (e) { /* gone is fine */ } },
  };

  const UI = { GS: null, setup: null, cardTab: 'batter', rarePending: false,
    stepError: null, modal: null, confirmDiscard: false, lastPitcher: null, view: null,
    feedOpen: false,
    _flash: null, _flashSeenPa: 0, _shownCards: null, _parkedDecision: false };
  PUI.UI = UI;
  const fx = () => PlayData.data.fixture;
  const slotOfClub = (club) => club === 'CHC' ? 'CHC' : 'OPP';
  const clubOfSlot = (slot) => slot === 'CHC' ? 'CHC' : 'MON';
  const clubName = (club) => fx().clubs[club].name;
  const clubShort = (club) => fx().clubs[club].short;

  function freshSetup() {
    const f = fx();
    return {
      homeClub: f.home_default,
      starters: { CHC: f.default_starters.CHC, MON: f.default_starters.MON },
      lineups: { CHC: deepCopy(f.lineups.CHC), MON: deepCopy(f.lineups.MON) },
      benches: { CHC: f.benches.CHC.slice(), MON: f.benches.MON.slice() },
      managers: { CHC: null, MON: null },
      sourceKind: 'deck',
      seed: Math.floor(100000 + Math.random() * 900000),
    };
  }

  function button(label, onClick, opts) {
    const b = el('button', { type: 'button', class: 'play-btn' + ((opts && opts.cls) ? ' ' + opts.cls : '') });
    b.textContent = label;
    if (opts && opts.disabled) b.disabled = true;
    if (onClick) b.addEventListener('click', onClick);
    return b;
  }

  // -- S6 resume banner + S1 setup ----------------------------
  function renderSetup(view) {
    UI.view = view;
    view.replaceChildren();
    const page = el('article', { class: 'panel play-page' });
    const save = peekSave(store);
    if (save && !save.finished) {
      const banner = el('section', { class: 'play-banner' });
      banner.appendChild(el('h3', { text: 'A saved game is waiting' }));
      banner.appendChild(el('p', { text: save.label + ' — ' + (save.half === 'top' ? 'Top' : 'Bottom') + ' ' + save.inning
        + ', Chicago ' + save.score.CHC + ', Montreal ' + save.score.OPP + ', after PA ' + save.paCount + '.' }));
      if (UI.confirmDiscard) {
        banner.appendChild(el('p', { class: 'note', text: 'Discarding deletes the app\'s only copy of this game, and if it was never exported, it is gone for good.' }));
        banner.appendChild(button('Delete the saved game', () => { discardSave(store); UI.confirmDiscard = false; renderSetup(view); }, { cls: 'danger' }));
        banner.appendChild(button('Keep it', () => { UI.confirmDiscard = false; renderSetup(view); }));
      } else {
        banner.appendChild(button('Resume the saved game', () => {
          const GS = loadSave(store);
          if (GS) { UI.GS = GS; UI.rarePending = false; renderGame(view); }
        }));
        banner.appendChild(button('Discard it', () => { UI.confirmDiscard = true; renderSetup(view); }));
      }
      page.appendChild(banner);
    } else if (save && save.finished) {
      const banner = el('section', { class: 'play-banner' });
      banner.appendChild(el('h3', { text: 'A finished game is saved' }));
      banner.appendChild(el('p', { text: save.label + ' — final, Chicago ' + save.score.CHC + ', Montreal ' + save.score.OPP + '. It is not resumable; open it to export it, then clear it.' }));
      banner.appendChild(button('Open it for export', () => {
        const GS = loadSave(store);
        if (GS) { UI.GS = GS; renderGame(view); }
      }));
      banner.appendChild(button('Clear it', () => { discardSave(store); renderSetup(view); }));
      page.appendChild(banner);
    }

    const S = UI.setup || (UI.setup = freshSetup());
    const f = fx();
    page.appendChild(el('h2', { text: 'Play the game' }));
    page.appendChild(el('p', { class: 'note', text: f.label + '. Exhibition: this game is not in the tournament record, and nothing here writes to it.' }));

    // Home club + park card
    page.appendChild(el('h3', { text: 'Home club' }));
    const homeRow = el('div', { class: 'play-toggle-row' });
    ['CHC', 'MON'].forEach(function (club) {
      const b = button(clubName(club) + ' (' + f.clubs[club].park + ')', () => { S.homeClub = club; renderSetup(view); },
        { cls: S.homeClub === club ? 'on' : '' });
      homeRow.appendChild(b);
    });
    page.appendChild(homeRow);
    page.appendChild(parkCardBlock(PlayData.data.parks[f.clubs[S.homeClub].park]));

    // Starters
    page.appendChild(el('h3', { text: 'Starting pitchers' }));
    ['CHC', 'MON'].forEach(function (club) {
      const lab = el('label', { class: 'play-field', text: clubName(club) + ' ' });
      const sel = el('select');
      f.rotations[club].forEach(function (name) {
        const o = el('option', { value: name, text: name });
        if (S.starters[club] === name) o.selected = true;
        sel.appendChild(o);
      });
      sel.addEventListener('change', () => { S.starters[club] = sel.value; });
      lab.appendChild(sel);
      page.appendChild(lab);
    });

    // Lineups
    const problems = { CHC: [], MON: [] };
    ['CHC', 'MON'].forEach(function (club) {
      page.appendChild(el('h3', { text: clubName(club) + ' lineup' }));
      const list = el('div', { class: 'play-lineup' });
      S.lineups[club].forEach(function (slotEntry, i) {
        const row = el('div', { class: 'play-lu-row' });
        row.appendChild(el('span', { class: 'play-lu-n', text: String(i + 1) }));
        row.appendChild(el('span', { class: 'play-lu-name', text: slotEntry.name }));
        row.appendChild(el('span', { class: 'play-lu-pos', text: slotEntry.pos }));
        row.appendChild(button('↑', () => { if (i > 0) { const t = S.lineups[club][i - 1]; S.lineups[club][i - 1] = S.lineups[club][i]; S.lineups[club][i] = t; renderSetup(view); } }, { disabled: i === 0 }));
        row.appendChild(button('↓', () => { if (i < 8) { const t = S.lineups[club][i + 1]; S.lineups[club][i + 1] = S.lineups[club][i]; S.lineups[club][i] = t; renderSetup(view); } }, { disabled: i === 8 }));
        row.appendChild(button('Swap', () => openSetupSwap(view, club, i)));
        list.appendChild(row);
      });
      page.appendChild(list);
      page.appendChild(el('p', { class: 'note', text: 'Bench: ' + S.benches[club].join(', ') }));
      problems[club] = lineupLegality(S.lineups[club], club);
      problems[club].forEach(function (p) { page.appendChild(el('p', { class: 'play-problem', text: clubShort(club) + ': ' + p })); });
      page.appendChild(button('Restore the staged lineup', () => {
        S.lineups[club] = deepCopy(f.lineups[club]); S.benches[club] = f.benches[club].slice(); renderSetup(view);
      }));
    });

    // Managers
    page.appendChild(el('h3', { text: 'Managers' }));
    ['CHC', 'MON'].forEach(function (club) {
      const profile = f.clubs[club].manager;
      const row = el('div', { class: 'play-toggle-row' });
      row.appendChild(el('span', { class: 'play-lu-name', text: clubName(club) + ': ' }));
      row.appendChild(button('You manage', () => { S.managers[club] = 'human'; renderSetup(view); }, { cls: S.managers[club] === 'human' ? 'on' : '' }));
      row.appendChild(button(profile + ' (profile)', () => { S.managers[club] = 'profile'; renderSetup(view); }, { cls: S.managers[club] === 'profile' ? 'on' : '' }));
      page.appendChild(row);
    });

    // Dice source
    page.appendChild(el('h3', { text: 'Dice and cards' }));
    const srcRow = el('div', { class: 'play-toggle-row' });
    [['deck', 'FAC deck'], ['dice', 'Dice roller'], ['manual', 'Manual entry']].forEach(function (pair) {
      srcRow.appendChild(button(pair[1], () => { S.sourceKind = pair[0]; renderSetup(view); }, { cls: S.sourceKind === pair[0] ? 'on' : '' }));
    });
    page.appendChild(srcRow);
    page.appendChild(el('p', { class: 'note', text: 'Declarations are not part of Phase 1 play. They arrive in a later phase.' }));

    // Seed + start
    const seedLab = el('label', { class: 'play-field', text: 'Seed ' });
    const seedIn = el('input', { type: 'number', value: String(S.seed) });
    seedIn.addEventListener('change', () => { const v = parseInt(seedIn.value, 10); if (Number.isFinite(v)) S.seed = v; });
    seedLab.appendChild(seedIn);
    page.appendChild(seedLab);
    const legal = problems.CHC.length === 0 && problems.MON.length === 0;
    const managed = S.managers.CHC && S.managers.MON;
    const start = button('Start the game', () => {
      const GS = createGame({
        seed: S.seed, homeSlot: slotOfClub(S.homeClub),
        starters: { CHC: S.starters.CHC, OPP: S.starters.MON },
        lineups: S.lineups, benches: S.benches,
        managers: { CHC: S.managers.CHC, OPP: S.managers.MON },
        sourceKind: S.sourceKind,
      }, store);
      UI.GS = GS; UI.rarePending = false; UI.setup = null;
      renderGame(view);
    }, { disabled: !(legal && managed), cls: 'primary' });
    page.appendChild(start);
    if (!managed) page.appendChild(el('p', { class: 'note', text: 'Pick a manager for both clubs to start.' }));
    view.appendChild(page);
  }

  function openSetupSwap(view, club, idx) {
    const S = UI.setup;
    const out = S.lineups[club][idx];
    openModal(view, 'Swap for ' + out.name + ' (' + out.pos + ')', (body, close) => {
      S.benches[club].forEach(function (cand) {
        const err = swapLegality(S.lineups[club], club, out.name, cand);
        const row = el('div', { class: 'play-modal-row' });
        row.appendChild(el('span', { class: 'play-lu-name', text: cand }));
        if (err) row.appendChild(el('span', { class: 'play-problem', text: err }));
        else row.appendChild(button('Bring in', () => {
          S.lineups[club][idx] = { name: cand, pos: out.pos };
          S.benches[club] = S.benches[club].filter((n) => n !== cand).concat([out.name]);
          close(); renderSetup(view);
        }));
        body.appendChild(row);
      });
    });
  }

  function openModal(view, title, build) {
    closeModal();
    const overlay = el('div', { class: 'play-modal-overlay' });
    const box = el('div', { class: 'play-modal' });
    box.appendChild(el('h3', { text: title }));
    const body = el('div', { class: 'play-modal-body' });
    box.appendChild(body);
    const close = () => closeModal();
    box.appendChild(button('Cancel', close));
    overlay.appendChild(box);
    document.body.appendChild(overlay);
    UI.modal = overlay;
    build(body, close);
  }
  function closeModal() { if (UI.modal) { UI.modal.remove(); UI.modal = null; } }
  PUI.renderSetup = renderSetup;
  PUI._openModal = openModal;
  PUI._el = el;
  PUI._button = button;
  PUI._blocks = { hitterCardBlock, pitcherCardBlock, parkCardBlock };
  PUI._store = store;
  PUI._clubOfSlot = clubOfSlot;

  // -- S2 game screen -----------------------------------------
  const runnerName = (entry) => entry == null ? null : (entry.name || entry[0]);
  function ffFat(S, name) {
    if (!S.fatigue_fix) return false;
    const recs = S.fatigue_fix.pitchers || {};
    for (const k of Object.keys(recs)) { const r = recs[k]; if ((k === name || (r && r.name === name)) && r && r.book_fatigued) return true; }
    return false;
  }
  function linescoreTable(S, full) {
    const innings = Math.max(9, S.linescore.CHC.length, S.linescore.OPP.length);
    const away = S.home === 'CHC' ? 'OPP' : 'CHC';
    const head = [''];
    for (let i = 1; i <= innings; i++) head.push(String(i));
    head.push('R', 'H', 'E');
    const rows = [away, S.home].map(function (slot) {
      const club = clubOfSlot(slot);
      const cells = [clubShort(club)];
      let r = 0;
      for (let i = 0; i < innings; i++) { const v = S.linescore[slot][i]; cells.push(v == null ? '' : String(v)); if (v) r += v; }
      let h = 0;
      Object.values(S.teams[slot].batting).forEach((bs) => { h += bs.H || 0; });
      cells.push(String(S.score[slot]), String(h), String(S.teams[slot].team_errors || 0));
      void r;
      return cells;
    });
    const wrap = el('div', { class: 'table-wrap' });
    const t = el('table', { class: 'play-linescore' });
    const hr = el('tr');
    head.forEach((h) => hr.appendChild(el('th', { text: h })));
    t.appendChild(el('thead', null, hr));
    const body = el('tbody');
    rows.forEach(function (cells) {
      const tr = el('tr');
      cells.forEach((c, i) => tr.appendChild(el('td', { class: i === 0 ? 'play-ls-club' : 'num', text: c })));
      body.appendChild(tr);
    });
    t.appendChild(body);
    wrap.appendChild(t);
    void full;
    return wrap;
  }
  function flipText(f) {
    if (!f) return 'No flips yet.';
    if (f.purpose && f.purpose.indexOf('RESHUFFLE') === 0) return f.purpose;
    if (f.fac_id) {
      const card = PlayData.deckById[f.fac_id];
      if (card) return 'FAC ' + f.fac_id + ' — page ' + card.page + ' · 2d6 ' + card.d2d6 + ' · % ' + pad2(card.pct) + ' · 1d6 ' + card.d1d6 + (card.wp ? ' · WP face' : '') + '  (' + f.purpose + ')';
      return 'FAC ' + f.fac_id + ' (' + f.purpose + ')';
    }
    if (f.dice) return 'Rolled 2d6: ' + f.dice[0] + ' + ' + f.dice[1] + ' = ' + (f.dice[0] + f.dice[1]) + '  (' + f.purpose + ')';
    if (f.value != null) return 'Rolled ' + f.purpose + ': ' + f.value;
    return f.purpose || '';
  }
  function feedBlock(b) {
    const d = el('div', { class: 'play-feed-block' + (b.live ? '' : ' undone') });
    d.appendChild(el('div', { class: 'play-feed-head', text: (b.action ? 'Managerial action' : 'PA ' + b.pa) + (b.live ? '' : ' — undone') }));
    b.lines.forEach((l) => d.appendChild(el('div', { class: 'play-feed-line', text: l })));
    return d;
  }
  function renderGame(view) {
    UI.view = view;
    if (UI._flash) cancelFlash();
    const GS = UI.GS, S = GS.S, G = GS.G;
    UI._parkedDecision = !!GS.pendingDecision;
    if (UI._flashSeenPa > GS.paCount) UI._flashSeenPa = GS.paCount;
    if (GS.finished) { renderOver(view); return; }
    view.replaceChildren();
    const page = el('article', { class: 'panel play-page' });
    // Scorebug
    const bat = batTeam(S), fld = fldTeam(S);
    const bug = el('div', { class: 'play-scorebug' });
    bug.appendChild(el('span', { class: 'play-bug-state', text: (S.half === 'top' ? 'Top' : 'Bottom') + ' ' + S.inning + ' · ' + S.outs + (S.outs === 1 ? ' out' : ' outs') }));
    bug.appendChild(el('span', { class: 'play-bug-score', text: clubShort('CHC') + ' ' + S.score.CHC + ' — ' + S.score.OPP + ' ' + clubShort('MON') }));
    bug.appendChild(el('span', { class: 'play-bug-save', text: GS.sealed ? 'Sealed' : (GS.storageOk ? 'Saved — after PA ' + GS.paCount : 'Unsaved — storage unavailable') }));
    page.appendChild(bug);
    page.appendChild(linescoreTable(S));
    // Diamond
    const dia = el('div', { class: 'play-diamond' });
    const baseNames = [2, 1, 3].map((b) => runnerName(S.bases[b - 1]));
    dia.appendChild(el('div', { class: 'play-base b2', text: baseNames[0] ? '◆ ' + baseNames[0] : '◇' }));
    dia.appendChild(el('div', { class: 'play-base b1', text: baseNames[1] ? '◆ ' + baseNames[1] : '◇' }));
    dia.appendChild(el('div', { class: 'play-base b3', text: baseNames[2] ? '◆ ' + baseNames[2] : '◇' }));
    dia.appendChild(el('div', { class: 'play-home', text: currentBatter(S)[0] + ' batting · ' + curPitcher(S) + ' pitching' }));
    page.appendChild(dia);
    // Matchup cards
    const pitcherNow = curPitcher(S);
    if (UI.lastPitcher && UI.lastPitcher !== pitcherNow) UI.cardTab = 'pitcher';
    UI.lastPitcher = pitcherNow;
    const tabRow = el('div', { class: 'play-toggle-row play-card-tabs' });
    tabRow.appendChild(button('Batter', () => { UI.cardTab = 'batter'; renderGame(view); }, { cls: UI.cardTab === 'batter' ? 'on' : '' }));
    tabRow.appendChild(button('Pitcher', () => { UI.cardTab = 'pitcher'; renderGame(view); }, { cls: UI.cardTab === 'pitcher' ? 'on' : '' }));
    // Layout: the game column, with the play feed in a collapsible
    // side panel so the two cards get the room.
    const layout = el('div', { class: 'play-layout' });
    const mainCol = el('div', { class: 'play-main' });
    layout.appendChild(mainCol);
    page.appendChild(layout);
    mainCol.appendChild(tabRow);
    const cards = el('div', { class: 'play-cards show-' + UI.cardTab });
    const batCardData = hcard(G, currentBatter(S)[0], bat);
    const bCard = hitterCardBlock(batCardData);
    bCard.classList.add('play-card-batter');
    const pitCardData = pitcherCard(G, S, fld, pitcherNow);
    const pCard = pitcherCardBlock(pitCardData);
    pCard.classList.add('play-card-pitcher');
    UI._shownCards = { bat: batCardData, pit: pitCardData };
    cards.appendChild(bCard);
    cards.appendChild(pCard);
    mainCol.appendChild(cards);
    // Roll panel
    const roll = el('section', { class: 'play-roll' });
    roll.appendChild(el('h3', { text: 'Dice and cards' }));
    const srcRow = el('div', { class: 'play-toggle-row' });
    [['deck', 'FAC deck'], ['dice', 'Dice roller'], ['manual', 'Manual entry']].forEach(function (pair) {
      srcRow.appendChild(button(pair[1], () => {
        const err = GS.setSource(pair[0]);
        UI.stepError = err || null;
        renderGame(view);
      }, { cls: GS.sourceKind === pair[0] ? 'on' : '' }));
    });
    roll.appendChild(srcRow);
    roll.appendChild(el('p', { class: 'play-lastflip', text: flipText(S.flips[S.flips.length - 1]) }));
    if (GS.pendingStep) roll.appendChild(manualForm(GS));
    if (UI.stepError) roll.appendChild(el('p', { class: 'play-problem', text: UI.stepError }));
    mainCol.appendChild(roll);
    // Decision / advance bar
    mainCol.appendChild(actionBar(view));
    // Play feed: a collapsible side panel. Collapsed by default so
    // the cards own the screen; the feed's blocks and live updates
    // are unchanged when it is open.
    const feedPanel = el('aside', { class: 'play-feed-panel' + (UI.feedOpen ? ' open' : '') });
    const feedBar = el('div', { class: 'play-feed-bar' });
    feedBar.appendChild(el('span', { class: 'play-feed-title', text: 'Play feed' }));
    feedBar.appendChild(button(UI.feedOpen ? 'Hide' : 'Show', () => {
      UI.feedOpen = !UI.feedOpen;
      renderGame(view);
    }, { cls: 'play-feed-toggle' }));
    feedPanel.appendChild(feedBar);
    let feedList = null;
    if (UI.feedOpen) {
      feedList = el('div', { class: 'play-feed-list' });
      GS.feed.forEach((b) => feedList.appendChild(feedBlock(b)));
      feedPanel.appendChild(feedList);
    }
    layout.appendChild(feedPanel);
    // Bench and bullpen panels
    mainCol.appendChild(rosterPanels(GS));
    view.appendChild(page);
    if (feedList) feedList.scrollTop = feedList.scrollHeight;
    void G;
  }
  function manualForm(GS) {
    const kind = GS.pendingStep;
    const S = GS.S;
    const box = el('div', { class: 'play-manual' });
    const label = kind === '2d6' ? 'Next step: 2d6' : kind === '%' ? 'Next step: percentile (%)' : kind === '1d6' ? 'Next step: 1d6' : 'Next step: 1d10';
    box.appendChild(el('p', { class: 'play-manual-label', text: label }));
    const modeRow = el('div', { class: 'play-toggle-row' });
    const form = { mode: 'card' };
    const cardBtn = button('FAC card', () => { form.mode = 'card'; cardBtn.classList.add('on'); valBtn.classList.remove('on'); cardBox.style.display = ''; valBox.style.display = 'none'; }, { cls: 'on' });
    const valBtn = button('Raw value', () => { form.mode = 'value'; valBtn.classList.add('on'); cardBtn.classList.remove('on'); valBox.style.display = ''; cardBox.style.display = 'none'; });
    modeRow.appendChild(cardBtn); modeRow.appendChild(valBtn);
    box.appendChild(modeRow);
    const cardBox = el('div');
    const valBox = el('div');
    valBox.style.display = 'none';
    let facIn, peekIn, d1In, d2In, vIn;
    if (S.deck.peek != null && S.deck.peek !== undefined) {
      cardBox.appendChild(el('p', { class: 'note', text: 'Flip FAC ' + S.deck.peek + ' — it is the peeked card and must be flipped next.' }));
      facIn = el('input', { type: 'number', value: String(S.deck.peek) });
    } else {
      facIn = el('input', { type: 'number', placeholder: 'FAC id (1-256)' });
    }
    cardBox.appendChild(el('label', { text: 'Card ' }, facIn));
    if (kind === '2d6' && !(S.deck.peek != null && S.deck.peek !== undefined)) {
      peekIn = el('input', { type: 'number', placeholder: 'Next card id (peek)' });
      cardBox.appendChild(el('label', { text: ' Peek ' }, peekIn));
    }
    if (kind === '2d6') {
      d1In = el('input', { type: 'number', placeholder: 'Die 1' });
      d2In = el('input', { type: 'number', placeholder: 'Die 2' });
      valBox.appendChild(el('label', { text: 'Dice ' }, d1In, d2In));
    } else {
      vIn = el('input', { type: 'number', placeholder: kind === '%' ? '0-99' : kind === '1d6' ? '1-6' : '0-9' });
      valBox.appendChild(el('label', { text: 'Value ' }, vIn));
    }
    box.appendChild(cardBox);
    box.appendChild(valBox);
    box.appendChild(button('Serve it', () => {
      let input;
      if (form.mode === 'card') {
        input = { form: 'card', fac_id: parseInt(facIn.value, 10) };
        if (peekIn) input.peek_id = parseInt(peekIn.value, 10);
      } else if (kind === '2d6') {
        input = { form: 'value', dice: [parseInt(d1In.value, 10), parseInt(d2In.value, 10)] };
      } else {
        input = { form: 'value', value: parseInt(vIn.value, 10) };
      }
      const st = GS.provide(input);
      afterPump(st);
    }, { cls: 'primary' }));
    return box;
  }
  function afterPump(st) {
    const wasParked = UI.rarePending || UI._parkedDecision;
    UI.rarePending = !!(st && st.status === 'RARE');
    if (st && st.status === 'STEP') UI.stepError = st.error || null; else UI.stepError = null;
    const wasFlashing = !!UI._flash;
    if (wasFlashing) cancelFlash();
    const completed = !!(st && UI.GS && (st.status === 'PA_DONE' || st.status === 'FINAL') &&
      UI.GS.paCount > UI._flashSeenPa);
    if (completed) {
      UI._flashSeenPa = UI.GS.paCount;
      // The flash decorates the cards still on screen, which are the
      // resolved PA's pair until the next render. It is skipped when
      // a flash is already running (the screen is a PA behind) and
      // when this pump resumed a parked rare play or decision (the
      // parked control is still on screen and must retire at once).
      if (!wasFlashing && !wasParked) {
        const data = flashDataForLastPa();
        if (data && startFlash(data)) return;
      }
    }
    renderGame(UI.view);
  }

  /* ---- Per-at-bat card highlight (display only) ----
   * When a plate appearance completes, flash first the pitcher's
   * 2d6 cell that was rolled, then the batter's section and the
   * exact band row the percentile landed in (or the OUT row the
   * read fell to). Everything is read back from the resolution
   * lines the engine already wrote into the PA's feed block and
   * checked against the cards still on screen; any mismatch and
   * the flash is downgraded or skipped, never wrong. No engine
   * state, resolution order, or recorded data is touched. */

  function findByClass(root, cls) {
    let hit = null;
    (function walk(n) {
      if (hit || !n) return;
      if (n.classList && n.classList.contains(cls)) { hit = n; return; }
      const kids = n.children || [];
      for (let i = 0; i < kids.length && !hit; i++) walk(kids[i]);
    })(root);
    return hit;
  }

  function cancelFlash() {
    if (!UI._flash) return;
    UI._flash.timers.forEach(clearTimeout);
    UI._flash = null;
  }

  // Pure mirror of the engine's outLookup pick (which also writes
  // a ledger line, so it cannot be called from the display layer).
  function outPick(card, pct) {
    const rows = (card && card.out_table) || [];
    for (const row of rows) if (row.range[0] <= pct && pct <= row.range[1]) return row;
    const above = rows.filter((r) => r.range[0] > pct);
    if (above.length) return above.reduce((a, b) => (a.range[0] <= b.range[0] ? a : b));
    return rows[rows.length - 1] || null;
  }

  function flashDataForLastPa() {
    const GS = UI.GS, shown = UI._shownCards;
    if (!GS || !shown || !shown.bat || !shown.pit) return null;
    let block = null;
    for (let i = GS.feed.length - 1; i >= 0; i--) {
      if (GS.feed[i].live && !GS.feed[i].action) { block = GS.feed[i]; break; }
    }
    if (!block) return null;
    const lines = block.lines || [];
    let di = -1, total = 0, dpct = 0, presult = '';
    for (let i = lines.length - 1; i >= 0; i--) {
      const m = /^ {2}dice 2d6=(\d+) \(\d+\+\d+\) %=(\d+) -> (.+?)\s*$/.exec(lines[i]);
      if (m) { di = i; total = +m[1]; dpct = +m[2]; presult = m[3]; break; }
    }
    if (di < 0) return null;
    let read = null, effPct = null;
    for (let i = di + 1; i < lines.length; i++) {
      const L = lines[i];
      let m = /strikeout read at (\d+)\s*$/.exec(L);
      if (m) { effPct = +m[1]; continue; }
      m = /^ {2}(WHEELHOUSE|PATIENT|TOUGH|IN-PLAY) %=(\d+) -> ([A-Z0-9]+)\s*$/.exec(L);
      if (m) { read = { section: m[1], pct: +m[2], result: m[3], out: false }; continue; }
      m = /^ {2}(WHEELHOUSE|PATIENT|TOUGH|IN-PLAY) %=(\d+) above the ranges -> OUT ([A-Z0-9]+)\s*$/.exec(L);
      if (m) { read = { section: m[1], pct: +m[2], out: true, code: m[3] }; continue; }
      m = /^ {2}(PATIENT-OUT|TOUGH-OUT): .*OUT section -> ([A-Z0-9]+)\s*$/.exec(L);
      if (m) read = { section: m[1] === 'PATIENT-OUT' ? 'PATIENT' : 'TOUGH', pct: effPct != null ? effPct : dpct, out: true, code: m[2] };
    }
    // The pitcher cell must agree with the card still on screen.
    const table = shown.pit.card_table_2d6;
    if (!table || table[String(total)] !== presult) return null;
    // Verify the batter read against the shown card; a read that
    // does not check out (an edited or shifted percentile) drops
    // to a pitcher-only flash rather than lighting the wrong row.
    if (read && !read.out) {
      const hand = shown.pit.throws === 'L' ? 'vsLHP' : 'vsRHP';
      const sec = shown.bat.sections && shown.bat.sections[read.section];
      const bands = sec && sec[hand];
      let hit = null;
      if (bands) Object.keys(bands).forEach((k) => {
        const b = bands[k];
        if (b && b[0] <= read.pct && read.pct <= b[1]) hit = k;
      });
      if (hit !== read.result) read = null;
    } else if (read && read.out) {
      const pick = outPick(shown.bat, read.pct);
      if (!pick || pick.result !== read.code) read = null;
      else read.pick = pick;
    }
    return { total, presult, read };
  }

  function startFlash(data) {
    const view = UI.view;
    const pCard = findByClass(view, 'play-card-pitcher');
    const grid = pCard && findByClass(pCard, 'dice-grid');
    if (!grid) return false;
    let cell = null;
    for (let i = 0; i < grid.children.length; i++) {
      const k = findByClass(grid.children[i], 'card-k');
      if (k && k.textContent.trim() === String(data.total)) { cell = grid.children[i]; break; }
    }
    if (!cell) return false;
    UI._flash = { timers: [] };
    cell.classList.add('hl-flash');
    setCardsTab('pitcher');
    // Each step holds about a second: the at-bat gets its moment,
    // and the game still only advances when the player says so.
    UI._flash.timers.push(setTimeout(() => {
      if (!UI._flash) return;
      cell.classList.remove('hl-flash');
      let wait = 250;
      if (data.read && decorateBatter(data.read)) { setCardsTab('batter'); wait = 1000; }
      UI._flash.timers.push(setTimeout(() => {
        if (!UI._flash) return;
        UI._flash = null;
        renderGame(UI.view);
      }, wait));
    }, 1000));
    return true;
  }

  function setCardsTab(which) {
    const cards = findByClass(UI.view, 'play-cards');
    if (cards) cards.className = 'play-cards show-' + which;
    const tabs = findByClass(UI.view, 'play-card-tabs');
    if (tabs) for (let i = 0; i < tabs.children.length; i++) {
      const b = tabs.children[i];
      const on = (which === 'batter' && b.textContent.trim() === 'Batter') ||
        (which === 'pitcher' && b.textContent.trim() === 'Pitcher');
      if (on) b.classList.add('on'); else b.classList.remove('on');
    }
  }

  function decorateBatter(read) {
    const bCard = findByClass(UI.view, 'play-card-batter');
    if (!bCard) return false;
    const kids = bCard.children || [];
    if (!read.out) {
      for (let i = 0; i < kids.length; i++) {
        const n = kids[i];
        if (n.classList && n.classList.contains('meta') && n.textContent.indexOf(read.section + ' ') === 0) {
          const table = kids[i + 1];
          if (!table) return false;
          const rows = [];
          (function walk(x) {
            if (x.tagName === 'TR') rows.push(x);
            (x.children || []).forEach(walk);
          })(table);
          for (const tr of rows) {
            const td = (tr.children || [])[0];
            if (td && td.textContent.trim() === read.result) {
              n.classList.add('hl-meta');
              tr.classList.add('hl-flash');
              return true;
            }
          }
          return false;
        }
      }
      return false;
    }
    // OUT read: repaint the out-table note with the landed row lit.
    if (!read.pick) return false;
    for (let i = 0; i < kids.length; i++) {
      const n = kids[i];
      if (n.classList && n.classList.contains('note') && n.textContent.indexOf('Out table: ') === 0) {
        const segs = n.textContent.slice('Out table: '.length).split(' · ');
        const target = read.pick.range[0] + '-' + read.pick.range[1] + ' ' + read.pick.result;
        if (segs.indexOf(target) < 0) return false;
        n.textContent = '';
        n.appendChild(document.createTextNode('Out table: '));
        segs.forEach((s, j) => {
          if (j) n.appendChild(document.createTextNode(' · '));
          const sp = el('span', { text: s });
          if (s === target) sp.classList.add('hl-out');
          n.appendChild(sp);
        });
        for (let j = 0; j < kids.length; j++) {
          const mm = kids[j];
          if (mm.classList && mm.classList.contains('meta') && read.section &&
            mm.textContent.indexOf(read.section + ' ') === 0) mm.classList.add('hl-meta');
        }
        return true;
      }
    }
    return false;
  }
  function decisionPanel(view) {
    const GS = UI.GS;
    const dec = GS.pendingDecision;
    const box = el('section', { class: 'play-decision' });
    if (dec.kind === 'manager_call') {
      const labels = {
        squeeze: ['Squeeze play: ' + dec.batter + ' bunts, the runner breaks home.', 'Squeeze', 'Swing away'],
        sac: ['Sacrifice: ' + dec.batter + ' lays it down?', 'Lay it down', 'Swing away'],
        send: ['Send ' + (dec.runner || 'the runner') + ' on the pitch?', 'Send him', 'Hold him'],
        hnr: ['Hit-and-run with ' + dec.batter + ' at the plate?', 'Put it on', 'Leave it off'],
      };
      const L = labels[dec.call] || ['Manager call: ' + dec.call, 'Go', 'Hold'];
      box.appendChild(el('p', { class: 'play-decision-q', text: L[0] }));
      if (dec.policy !== undefined) box.appendChild(el('p', { class: 'note', text: 'Profile policy would ' + (dec.policy ? 'go.' : 'hold.') }));
      box.appendChild(button(L[1], () => afterPump(GS.answer({ go: true })), { cls: 'primary' }));
      box.appendChild(button(L[2], () => afterPump(GS.answer({ go: false }))));
    } else if (dec.kind === 'send_hold') {
      box.appendChild(el('p', { class: 'play-decision-q', text: 'Third base coach: ' + dec.runner + ' rounds ' + (dec.from === 1 ? 'second' : 'first') + ' — send him to ' + (dec.to === 3 ? 'third' : 'second') + '?' }));
      box.appendChild(button('Send', () => afterPump(GS.answer({ go: true })), { cls: 'primary' }));
      box.appendChild(button('Hold', () => afterPump(GS.answer({ go: false }))));
    } else if (dec.kind === 'coverage') {
      box.appendChild(el('p', { class: 'play-decision-q', text: dec.out + ' is out of the game. The fit pick for ' + dec.spot + ' is ' + dec.pick + ' — ' + (dec.reason || '') }));
      const row = el('div', { class: 'play-modal-row' });
      row.appendChild(el('span', { class: 'play-lu-name', text: dec.pick + ' (fit pick)' }));
      row.appendChild(button('Confirm', () => afterPump(GS.answer({ pick: dec.pick })), { cls: 'primary' }));
      box.appendChild(row);
      (dec.bench || []).filter((n) => n !== dec.pick).forEach(function (cand) {
        const r = el('div', { class: 'play-modal-row' });
        r.appendChild(el('span', { class: 'play-lu-name', text: cand }));
        r.appendChild(button('Pick him instead', () => afterPump(GS.answer({ pick: cand }))));
        box.appendChild(r);
      });
    } else {
      box.appendChild(el('p', { text: 'Decision: ' + dec.kind }));
      box.appendChild(button('Go with the policy', () => afterPump(GS.answer(undefined)), { cls: 'primary' }));
    }
    return box;
  }
  function actionBar(view) {
    const GS = UI.GS, S = GS.S;
    const bar = el('section', { class: 'play-actions' });
    if (GS.pendingDecision) { bar.appendChild(decisionPanel(view)); return bar; }
    if (UI.rarePending) {
      bar.appendChild(el('p', { class: 'play-decision-q', text: 'A rare play is on the table. The feed above has the trigger; the chart resolves it.' }));
      bar.appendChild(button('Resolve rare play', () => afterPump(GS.resumeRare()), { cls: 'primary' }));
      return bar;
    }
    if (GS.pendingStep) {
      bar.appendChild(el('p', { class: 'note', text: 'Waiting on the manual entry above.' }));
      return bar;
    }
    bar.appendChild(button('Play plate appearance', () => afterPump(GS.step()), { cls: 'primary' }));
    // Managerial actions for human clubs, between PAs.
    const bat = batTeam(S), fld = fldTeam(S);
    if (GS.cfg.managers[bat] === 'human') {
      bar.appendChild(button('Pinch hit', () => openPickTwo(view, bat, 'ph')));
      const runners = S.bases.map(runnerName).filter(Boolean);
      if (runners.length) bar.appendChild(button('Pinch run', () => openPickTwo(view, bat, 'pr')));
    }
    if (GS.cfg.managers[fld] === 'human') {
      bar.appendChild(button('Pitching change', () => openPitchModal(view, fld)));
      bar.appendChild(button('Defensive sub', () => openPickTwo(view, fld, 'defsub')));
    }
    bar.appendChild(button('Undo', () => { if (GS.undo()) { UI.rarePending = false; renderGame(view); } },
      { disabled: GS.undoStack.length === 0 || GS.sealed }));
    if (GS.sealed) bar.appendChild(el('span', { class: 'note', text: 'Exported — this game is sealed.' }));
    return bar;
  }
  function rosterPanels(GS) {
    const S = GS.S;
    const wrap = el('div', { class: 'play-rosters' });
    ['CHC', 'OPP'].forEach(function (slot) {
      const club = clubOfSlot(slot);
      const tm = S.teams[slot];
      const sec = el('section', { class: 'play-roster' });
      sec.appendChild(el('h3', { text: clubName(club) }));
      sec.appendChild(el('p', { class: 'play-roster-h', text: 'Bench' }));
      const bl = el('ul', { class: 'play-roster-list' });
      if (!tm.bench.length) bl.appendChild(el('li', { text: 'Empty — everyone is in or gone.' }));
      tm.bench.forEach((n) => bl.appendChild(el('li', { text: n })));
      sec.appendChild(bl);
      if (tm.removed.length) sec.appendChild(el('p', { class: 'note', text: 'Out of the game: ' + tm.removed.join(', ') }));
      sec.appendChild(el('p', { class: 'play-roster-h', text: 'Bullpen' }));
      const pl = el('ul', { class: 'play-roster-list' });
      const entered = Object.keys(tm.pitching);
      const all = entered.concat(tm.pen.filter((n) => !entered.includes(n)));
      all.forEach(function (n) {
        const ps = tm.pitching[n];
        const role = (GS.G.penRole[slot] || {})[n] || '';
        let state = 'available';
        if (tm.pitcher === n) state = 'in now';
        else if (!tm.pen.includes(n)) state = 'done';
        const fat = ps && (ps.fatigued || ffFat(GS.S, n)) ? ' · fatigued' : '';
        pl.appendChild(el('li', { text: n + (role ? ' (' + role + ')' : '') + ' — ' + state + (ps ? ', ' + ipText(ps.outs) + ' IP' : '') + fat }));
      });
      sec.appendChild(pl);
      wrap.appendChild(sec);
    });
    return wrap;
  }
  function openPickTwo(view, slot, kind) {
    const GS = UI.GS, S = GS.S;
    const tm = S.teams[slot];
    const titles = { ph: 'Pinch hit', pr: 'Pinch run', defsub: 'Defensive substitution' };
    openModal(view, titles[kind], (body, close) => {
      body.appendChild(el('p', { class: 'note', text: 'First the man coming in, then the man he replaces.' }));
      tm.bench.forEach(function (cand) {
        const row = el('div', { class: 'play-modal-row' });
        const card = hcard(GS.G, cand, slot);
        row.appendChild(el('span', { class: 'play-lu-name', text: cand + ' — Bats ' + (card.bats || '?') + ', Run ' + (card.run != null ? card.run : '?') }));
        row.appendChild(button('In', () => {
          body.replaceChildren();
          body.appendChild(el('p', { class: 'note', text: cand + ' comes in for…' }));
          let targets;
          if (kind === 'pr') targets = S.bases.map(runnerName).filter(Boolean);
          else targets = tm.order.map((s) => s.name);
          targets.forEach(function (out) {
            const r2 = el('div', { class: 'play-modal-row' });
            r2.appendChild(el('span', { class: 'play-lu-name', text: out }));
            if (kind === 'defsub') {
              const lineupNow = tm.order.map((s) => ({ name: s.name, pos: s.pos }));
              const err = swapLegality(lineupNow, clubOfSlot(slot), out, cand);
              if (err) { r2.appendChild(el('span', { class: 'play-problem', text: err })); body.appendChild(r2); return; }
            }
            r2.appendChild(button('Replace', () => {
              GS.act({ kind: kind, slot: slot, out: out, name: cand, reason: "manager's call" });
              close(); renderGame(view);
            }));
            body.appendChild(r2);
          });
        }));
        body.appendChild(row);
      });
    });
  }
  function openPitchModal(view, slot) {
    const GS = UI.GS, S = GS.S, G = GS.G;
    const tm = S.teams[slot];
    const cur = tm.pitcher;
    const ps = pstat(S, slot, cur);
    openModal(view, 'Pitching change — ' + clubName(clubOfSlot(slot)), (body, close) => {
      body.appendChild(el('p', { text: 'Now pitching: ' + cur + ' — ' + ipText(ps.outs) + ' IP, ' + ps.H + ' H, ' + ps.R + ' R (' + ps.ER + ' ER), ' + ps.BB + ' BB, ' + ps.SO + ' SO'
        + ((ps.fatigued || ffFat(S, cur)) ? ' — fatigued.' : '.') }));
      // Policy banner: the closer shape and the live hook.
      const lead = S.score[slot] - S.score[batTeam(S)];
      let span = null;
      for (const sp of S.pitcher_spans) if (sp.team === slot && sp.name === cur && !sp.end) span = sp;
      const spanOuts = span ? S.def_outs[slot] - span.start[2] : ps.outs;
      if (S.inning >= 9 && lead >= 1 && lead <= 3 && ps.entered_inning === 1 && spanOuts >= 21) {
        const closer = tm.pen.find((n) => (G.penRole[slot] || {})[n] === 'closer');
        if (closer) body.appendChild(el('p', { class: 'play-banner-line', text: 'Closer branch: ' + closer + ' is the indicated arm.' }));
      } else if (ps.fatigued) {
        body.appendChild(el('p', { class: 'play-banner-line', text: 'The hook policy is live on ' + cur + ' (fatigued). Left alone, the machinery may lift him between PAs.' }));
      }
      body.appendChild(el('p', { class: 'note', text: 'The house hard rule keeps pitchers who have not appeared in this game off the starter list: only the bullpen is offered.' }));
      tm.pen.forEach(function (name) {
        const p2 = pstat(S, slot, name);
        const row = el('div', { class: 'play-modal-row' });
        row.appendChild(el('span', { class: 'play-lu-name', text: name + ' (' + ((G.penRole[slot] || {})[name] || 'pen') + ') — ' + ipText(p2.outs) + ' IP today' }));
        row.appendChild(button('Bring in', () => {
          GS.act({ kind: 'pitch', slot: slot, name: name });
          close(); renderGame(view);
        }));
        body.appendChild(row);
      });
    });
  }

  // -- S5 game over -------------------------------------------
  function boxTables(GS) {
    const S = GS.S;
    const wrap = el('div');
    ['CHC', 'OPP'].forEach(function (slot) {
      const club = clubOfSlot(slot);
      wrap.appendChild(el('h3', { text: clubName(club) + ' batting' }));
      const t = el('table');
      const hr = el('tr');
      ['Player', 'PA', 'AB', 'R', 'H', '2B', '3B', 'HR', 'RBI', 'BB', 'HBP', 'SO', 'SB', 'CS', 'GDP'].forEach((h) => hr.appendChild(el('th', { text: h })));
      t.appendChild(el('thead', null, hr));
      const body = el('tbody');
      const tot = blankBstat();
      Object.entries(S.teams[slot].batting).forEach(function ([name, bs]) {
        body.appendChild(el('tr', null, ...batLineRow(name, bs).map((c, i) => el('td', { class: i ? 'num' : null, text: String(c) }))));
        for (const k of Object.keys(tot)) tot[k] += bs[k] || 0;
      });
      body.appendChild(el('tr', null, ...batLineRow('Team', tot).map((c, i) => el('td', { class: i ? 'num' : null, text: String(c) }))));
      t.appendChild(body);
      wrap.appendChild(el('div', { class: 'table-wrap' }, t));
      wrap.appendChild(el('h3', { text: clubName(club) + ' pitching' }));
      const pt = el('table');
      const ph = el('tr');
      ['Pitcher', 'IP', 'BF', 'H', 'R', 'ER', 'BB', 'SO'].forEach((h) => ph.appendChild(el('th', { text: h })));
      pt.appendChild(el('thead', null, ph));
      const pb = el('tbody');
      S.pitcher_spans.filter((sp) => sp.team === slot).forEach(function (sp) {
        const p2 = S.teams[slot].pitching[sp.name];
        if (!p2) return;
        const outs = sp.end ? sp.end[2] - sp.start[2] : S.def_outs[slot] - sp.start[2];
        pb.appendChild(el('tr', null, ...[sp.name, ipText(outs), p2.BF, p2.H, p2.R, p2.ER, p2.BB, p2.SO].map((c, i) => el('td', { class: i ? 'num' : null, text: String(c) }))));
      });
      pt.appendChild(pb);
      wrap.appendChild(el('div', { class: 'table-wrap' }, pt));
    });
    return wrap;
  }
  function download(name, text, type) {
    const blob = new Blob([text], { type: type });
    const a = el('a', { href: URL.createObjectURL(blob), download: name });
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 400);
  }
  function renderOver(view) {
    UI.view = view;
    const GS = UI.GS, S = GS.S;
    view.replaceChildren();
    const page = el('article', { class: 'panel play-page' });
    page.appendChild(el('h2', { text: 'Final — ' + clubName('CHC') + ' ' + S.score.CHC + ', ' + clubName('MON') + ' ' + S.score.OPP }));
    page.appendChild(linescoreTable(S, true));
    const dec = GS.decisions();
    const decBits = [];
    if (dec.W) decBits.push('W: ' + dec.W);
    if (dec.L) decBits.push('L: ' + dec.L);
    if (dec.SV) decBits.push('SV: ' + dec.SV);
    if (decBits.length) page.appendChild(el('p', { class: 'play-decisions-line', text: decBits.join(' · ') }));
    page.appendChild(boxTables(GS));
    const audit = GS.audit();
    const bad = audit.filter((a) => !a.ok);
    page.appendChild(el('p', { class: bad.length ? 'play-problem' : 'note',
      text: bad.length ? 'AUDIT: FAILED — ' + bad.map((a) => a.check + ' (' + a.detail + ')').join('; ') : 'Internal audit: every Section 10 equality passes.' }));
    const f = fx();
    page.appendChild(el('p', { class: 'note', text: 'Record: seed ' + GS.seed + ' · dice mode ' + GS.sourceKind + ' · FAC draws ' + S.deck.draws
      + ' · reshuffles ' + S.deck.reshuffles + ' · undos ' + GS.undoCount + ' · venue ' + f.clubs[UI.GS.cfg.homeSlot === 'CHC' ? 'CHC' : 'MON'].park
      + ' · managers: Chicago ' + (GS.cfg.managers.CHC === 'human' ? 'you' : f.clubs.CHC.manager) + ', Montreal ' + (GS.cfg.managers.OPP === 'human' ? 'you' : f.clubs.MON.manager) + '.' }));
    page.appendChild(el('p', { class: 'play-notice', text: 'Exhibition. This game is not in the tournament record. Adoption is Joe\'s ruling, outside the app.' }));
    if (GS.sealed) {
      page.appendChild(el('p', { class: 'note', text: 'Exported and sealed. The autosave is cleared; undo is closed.' }));
    } else {
      const ex = GS.exports();
      page.appendChild(button('Download the box score (.md)', () => { download(GS.exportId + '.md', ex.markdown, 'text/markdown'); GS.seal(); renderOver(view); }));
      page.appendChild(button('Download the detail file (.json)', () => { download(GS.exportId + '.json', JSON.stringify(ex.json, null, 1), 'application/json'); GS.seal(); renderOver(view); }));
      page.appendChild(button('Copy the box score', () => {
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(ex.markdown);
        GS.seal(); renderOver(view);
      }));
      if (GS.undoStack.length) page.appendChild(button('Step back in (undo the last PA)', () => { if (GS.undo()) { UI.rarePending = false; renderGame(view); } }));
    }
    page.appendChild(button('Play again', () => { UI.GS = null; UI.setup = null; renderSetup(view); }));
    const back = el('a', { href: '#/bracket', class: 'play-btn', text: 'Back to bracket' });
    page.appendChild(back);
    view.appendChild(page);
  }

  // -- Entry ---------------------------------------------------
  PUI.renderPlay = function (view) {
    document.querySelectorAll('.views a').forEach(function (link) {
      const on = link.getAttribute('data-view') === 'play';
      if (on) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
    });
    if (!PlayData.data) {
      view.replaceChildren(el('p', { text: 'Loading the playable fixture…' }));
      fetch('data/playable_r106.json').then((r) => r.json()).then((j) => {
        PlayData.load(j);
        PUI.renderPlay(view);
      }).catch((e) => {
        view.replaceChildren(el('p', { class: 'play-problem', text: 'The playable data file did not load: ' + e.message }));
      });
      return;
    }
    if (UI.GS) renderGame(view);
    else renderSetup(view);
  };
  // Leaving the play route retires any pending card flash, so its
  // timers can never repaint over the page navigated to.
  if (typeof window.addEventListener === 'function') {
    window.addEventListener('hashchange', () => { if (UI._flash) cancelFlash(); });
  }
}

/* Node export guard: the headless verification gate (replay
 * driver, batteries, distribution) loads the engine from here.
 * In the browser this file runs as a plain script and the guard
 * is inert. */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { PlayData, makeContext, fixtureTraits, newState, drive,
    gameStep, runGame, resolvePA, resolvePaInner, autoResolveRare, prePa, updateFatigue,
    ffPrecheck, ffEvaluate, ffState, sectionLookupRaw, fieldingLine,
    createGame, loadSave, peekSave, discardSave, lineupLegality, swapLegality, makeSuffix, SAVE_PREFIX,
    CHARTS: { STEAL_COL, STEAL_HOME, BUNT, DEF_POS, HIT_G, DEF_HIT, DEF_ERR, DEF_OUT, catcherArm },
    maybeHook, enforceCloser, closeCheck, changePitcher, changePitcherRaw,
    pickReliever, removePitcher, substitute, pinchHit, pinchRun,
    resolveBunt, attemptSteal, autoStealCheck, resolveDefense, groundOut,
    groundOutAdd, resolvePickoff, injuryCheck, sectionLookup, outLookup,
    auditGame, deriveDecisions, snapshotState, restoreState,
    DeckSource, makeDiceSource, makeManualSource, makeReplaySource,
    batTeam, fldTeam, curPitcher, bstat, pstat, hcard, pitcherCard,
    basesStr, led, elog };
}

})(typeof window !== 'undefined' ? window : globalThis);
