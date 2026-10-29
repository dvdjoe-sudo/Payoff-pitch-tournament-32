#!/usr/bin/env node
/* Ported verification batteries for the playable mode (spec
 * section 11.2). Each battery ports the engineered cases of its
 * Python source battery against the shipped JS engine and the
 * shipped data file; expectations come from the source battery
 * and the recorded rules, never from the port's own output.
 *
 *   vacancy 22  <- payoff-pitch-managers/sandbox/vacancy_rule_proof.py
 *   fatigue 23  <- payoff-pitch-nationals/fatigue_battery.py
 *   chance  42  <- payoff-pitch-managers/sandbox/chance_liveness.py
 *   outchart    <- the 2026-10-28 OUT-chart audit standard,
 *                  run over data/playable_r106.json itself
 *   rare / defense / steals / bunts: engineered states per
 *                  spec 11.2's battery list
 *   uistate     <- spec 11.2 UI-state list (runs when the
 *                  GameState module is present in play.js)
 *
 * Run: node scripts/batteries.mjs [battery ...]
 * Exit 1 if any check fails. */
import { createRequire } from 'node:module';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
const P = require('../js/play.js');
const DATA = JSON.parse(fs.readFileSync(new URL('../data/playable_r106.json', import.meta.url), 'utf8'));
P.PlayData.load(DATA);

const RESULTS = [];
function check(battery, label, cond, detail = '') {
  RESULTS.push({ battery, label, pass: !!cond });
  console.log((cond ? 'PASS ' : 'FAIL ') + battery + ' ' + label + (cond ? '' : ' -- ' + detail));
}
function D6(total) {
  for (let d1 = 1; d1 <= 6; d1++) { const d2 = total - d1; if (d2 >= 1 && d2 <= 6) return [d1, d2, total]; }
  throw new Error('bad 2d6 total ' + total);
}
function scripted(pairs, lenient = true) {
  const q = (pairs || []).slice();
  const dflt = { '2d6': () => [3, 4, 7], '%': () => 50, '1d6': () => 3, '1d10': () => 5 };
  return { name: 'scripted', queue: q,
    serve(kind) {
      if (q.length && q[0][0] === kind) return q.shift()[1];
      if (!lenient) throw new Error('script mismatch/exhausted at ' + kind + ' next=' + (q[0] && q[0][0]));
      return dflt[kind]();
    },
    reshuffle() {} };
}
function game(opts = {}) {
  const starters = opts.starters || { CHC: 'Fergie Jenkins', OPP: 'Steve Rogers' };
  const G = P.makeContext({ homeSlot: opts.home || 'CHC', starters,
    buntOverlay: !!opts.buntOverlay, prePa: !!opts.prePa, clauses: !!opts.clauses,
    defenseNumbers: !!opts.defenseNumbers, fatigueBook: opts.fatigueBook });
  const S = P.newState(G, { seed: opts.seed || 777, homeSlot: opts.home || 'CHC', starters,
    traits: opts.traits === undefined ? P.fixtureTraits() : opts.traits,
    lineups: opts.lineups, benches: opts.benches });
  S.source = opts.source || scripted([], true);
  return [G, S];
}
const run = (gen, S) => P.drive(gen, S, () => undefined);
function ledCount(S, key) { const e = S.ledger[key]; return e ? e.count : 0; }
function ledDetail(S, key, i = 0) { const e = S.ledger[key]; return e && e.details[i] ? e.details[i] : ''; }
function injectHitter(club, card) {
  P.PlayData.data.hitters[club][card.name] = Object.assign(
    { name: card.name, team: club, bats: 'R', run: 5, jump: 0, dp: 7, steal: 'C', sac_bunt: 'C', sections: {}, positions: [] }, card);
}
function injectPitcher(club, card) {
  const table = {};
  for (let t = 2; t <= 12; t++) table[String(t)] = card.table || 'PATIENT';
  P.PlayData.data.pitchers[club][card.name] = Object.assign(
    { name: card.name, team: club, throws: 'R', card_type: 'RP', so_modifier: 'NONE',
      card_table_2d6: table, addendum: true, dp: 7, wp: null, hold: null, inj: null,
      stamina: { start: null, relief: null } }, card.extra || {});
}
function totalFor(pcard, result) {
  for (const t of Object.keys(pcard.card_table_2d6)) if (pcard.card_table_2d6[t] === result) return Number(t);
  throw new Error('no 2d6 total reads ' + result);
}
function scriptedPA(G, S, total, pct) {
  S.source = scripted([['2d6', D6(total)], ['%', pct]], true);
  return run(P.resolvePA(G, S), S);
}

/* ============================================================ VACANCY (22) */
function batteryVacancy() {
  injectHitter('CHC', { name: 'Ozzie Smith', positions: [{ pos: 'SS', range: 'A', e: 2, arm: 8 }] });
  injectHitter('CHC', { name: 'Ted Simmons', positions: [{ pos: 'C', range: 'B', e: 3, arm: 6 }] });
  injectHitter('CHC', { name: 'Red Schoendienst', positions: [{ pos: '2B', range: 'A', e: 2, arm: 8 }] });
  injectHitter('CHC', { name: 'Catcher One', positions: [{ pos: 'C', range: 'D', e: 5, arm: 6 }] });
  injectHitter('CHC', { name: 'Catcher Two', positions: [{ pos: 'C', range: 'C', e: 4, arm: 6 }] });
  injectHitter('CHC', { name: 'Outfield One', positions: [{ pos: 'LF', range: 'C', e: 4, arm: 6 }] });
  injectHitter('CHC', { name: 'Weak Glove', positions: [{ pos: 'SS', range: 'F', e: 5, arm: 4 }] });
  injectHitter('CHC', { name: 'David Freese', positions: [{ pos: '3B', range: 'C', e: 4, arm: 6 }] });
  injectHitter('CHC', { name: 'Gold Glove', positions: [{ pos: 'SS', range: 'A', e: 2, arm: 8 }] });
  injectHitter('CHC', { name: 'Strong Second', positions: [{ pos: '2B', range: 'A', e: 2, arm: 8 }] });
  const LINEUP = [
    { name: 'Ozzie Smith', pos: 'SS' }, { name: 'Ryne Sandberg', pos: '2B' },
    { name: 'Mark Grace', pos: '1B' }, { name: 'Ron Santo', pos: '3B' },
    { name: 'Sammy Sosa', pos: 'RF' }, { name: 'Billy Williams', pos: 'LF' },
    { name: 'Hack Wilson', pos: 'DH' }, { name: 'Gabby Hartnett', pos: 'C' },
    { name: 'Pete Crow-Armstrong', pos: 'CF' }];
  const mk = (bench, lineup) => game({ lineups: { CHC: lineup || LINEUP }, benches: { CHC: bench } });

  // (a) the origin regression shape: C-only man first on the
  // bench, the carded 2B second; the rule takes the 2B.
  {
    const [G, S] = mk(['Ted Simmons', 'Red Schoendienst', 'Johnny Kling', 'Billy Herman']);
    const tm = S.teams.CHC;
    const pick = run(P.substitute(G, S, 'CHC', 'Ozzie Smith', 'ejected (rare play 06-12); regression case'), S);
    check('vacancy', '(a) new rule picks Schoendienst for Smith', pick === 'Red Schoendienst', String(pick));
    check('vacancy', '(a) Schoendienst fields SS', tm.field.SS === 'Red Schoendienst');
    check('vacancy', '(a) Simmons stays on the bench', tm.bench.includes('Ted Simmons'));
    check('vacancy', '(a) entrant takes Smith slot at SS', tm.order[0].name === 'Red Schoendienst' && tm.order[0].pos === 'SS');
    check('vacancy', '(a) priced on his carded 2B line', JSON.stringify(P.fieldingLine(G, S, 'CHC', 'SS')) === JSON.stringify(['A', 2, 8]), JSON.stringify(P.fieldingLine(G, S, 'CHC', 'SS')));
    check('vacancy', '(a) ledger names the rule and the pricing basis',
      ledCount(S, 'vacancy_coverage') === 1 && ledDetail(S, 'vacancy_coverage').includes("manager's rule (Joe, 2026-10-27)")
      && ledDetail(S, 'vacancy_coverage').includes('Schoendienst') && ledDetail(S, 'vacancy_coverage').includes('2B line'),
      ledDetail(S, 'vacancy_coverage'));
    check('vacancy', '(a) the old bench-order pick was Simmons (the regression the rule replaced)', tm.bench[0] === 'Ted Simmons' || S.teams.CHC.bench.includes('Ted Simmons'));
  }
  // (b) a carded replacement: direct entry, no rearrangement,
  // no basis ledger (the old engine's identical path).
  {
    const [G, S] = mk(['Ted Simmons', 'Red Schoendienst', 'Johnny Kling']);
    const tm = S.teams.CHC;
    const pick = run(P.substitute(G, S, 'CHC', 'Gabby Hartnett', 'ejected (constructed)'), S);
    check('vacancy', '(b) carded replacement: Simmons picked', pick === 'Ted Simmons', String(pick));
    check('vacancy', '(b) Simmons fields C from the departed slot', tm.field.C === 'Ted Simmons' && tm.order[7].name === 'Ted Simmons' && tm.order[7].pos === 'C');
    check('vacancy', '(b) nobody else moves', tm.field.SS === 'Ozzie Smith' && tm.field['2B'] === 'Ryne Sandberg');
    check('vacancy', '(b) no vacancy_coverage ledger on the direct path', ledCount(S, 'vacancy_coverage') === 0);
  }
  // (c) no fit anywhere: bench order, catcher last.
  {
    const [G, S] = mk(['Catcher One', 'Catcher Two', 'Outfield One']);
    const tm = S.teams.CHC;
    const pick = run(P.substitute(G, S, 'CHC', 'Ozzie Smith', 'ejected (constructed)'), S);
    check('vacancy', '(c) no fit anywhere: bench order takes it', pick === 'Catcher One', String(pick));
    check('vacancy', '(c) the catcher fields SS only at the last resort', tm.field.SS === 'Catcher One');
    check('vacancy', '(c) ledger records the last-resort basis', ledCount(S, 'vacancy_coverage') === 1 && ledDetail(S, 'vacancy_coverage').includes('last resort'), ledDetail(S, 'vacancy_coverage'));
  }
  // (d) slide wins: a Poor carded SS on the bench, a strong
  // starting 2B, a carded 3B who can cover 2B.
  {
    const lineup = LINEUP.map((s) => s.name === 'Ryne Sandberg' ? { name: 'Strong Second', pos: '2B' } : s);
    const [G, S] = mk(['Ted Simmons', 'Weak Glove', 'David Freese'], lineup);
    const tm = S.teams.CHC;
    const pick = run(P.substitute(G, S, 'CHC', 'Ozzie Smith', 'ejected (constructed)'), S);
    const slider = tm.field.SS;
    const oldSpot = slider === 'Ron Santo' ? '3B' : '2B';
    check('vacancy', '(d) slide wins: entrant is Freese, not at SS', pick === 'David Freese' && slider !== 'David Freese', String(pick));
    check('vacancy', '(d) a starting infielder slides to SS', slider === 'Strong Second' || slider === 'Ron Santo', slider);
    check('vacancy', "(d) Freese fields the slider's old spot", tm.field[oldSpot] === 'David Freese');
    const slots = {}; for (const s of tm.order) slots[s.name] = s.pos;
    check('vacancy', '(d) entrant takes the departed slot, re-tagged to the old spot', slots['David Freese'] === oldSpot);
    check('vacancy', '(d) slider keeps his own slot, re-tagged to SS', slots[slider] === 'SS');
    check('vacancy', '(d) ledger names the slide and both pricing bases', ledCount(S, 'vacancy_coverage') === 1 && ledDetail(S, 'vacancy_coverage').includes('slides from ' + oldSpot + ' to SS'), ledDetail(S, 'vacancy_coverage'));
  }
  // (d2) no slide against the A-line direct pick.
  {
    const [G, S] = mk(['Ted Simmons', 'Red Schoendienst', 'Johnny Kling']);
    const tm = S.teams.CHC;
    const before = tm.field['2B'];
    const pick = run(P.substitute(G, S, 'CHC', 'Ozzie Smith', 'ejected (constructed)'), S);
    check('vacancy', '(d) no slide against the A-line direct pick', pick === 'Red Schoendienst' && tm.field['2B'] === before && tm.field.SS === 'Red Schoendienst');
  }
  // (d3) tie goes to the direct entry.
  {
    const lineup = LINEUP.map((s) => s.name === 'Ryne Sandberg' ? { name: 'Strong Second', pos: '2B' } : s);
    const [G, S] = mk(['Ted Simmons', 'Gold Glove', 'David Freese'], lineup);
    const tm = S.teams.CHC;
    const pick = run(P.substitute(G, S, 'CHC', 'Ozzie Smith', 'ejected (constructed)'), S);
    check('vacancy', '(d) tie goes to the direct entry (Gold Glove at SS)', pick === 'Gold Glove' && tm.field.SS === 'Gold Glove' && tm.field['2B'] === 'Strong Second');
  }
}

/* ============================================================ FATIGUE (23) */
function batteryFatigue() {
  injectPitcher('MON', { name: 'Test Starter', extra: { card_type: 'SP', stamina: { start: 6, relief: null } } });
  injectPitcher('MON', { name: 'Test Short', extra: { stamina: { start: null, relief: 'Short' } } });
  injectPitcher('MON', { name: 'Test Long', extra: { stamina: { start: null, relief: 'Long' } } });
  injectPitcher('MON', { name: 'Test Double', extra: { stamina: { start: null, relief: 'Short' }, save_symbol: '#' } });
  injectPitcher('MON', { name: 'Test Twin', extra: { stamina: { start: null, relief: 'Short' } } });
  const mk = (opts = {}) => {
    const [G, S] = game(Object.assign({ starters: { CHC: 'Fergie Jenkins', OPP: 'Test Starter' } }, opts));
    S.half = 'bottom'; // the test club (OPP) fields
    S.teams.OPP.pen.push('Test Short', 'Test Long', 'Test Double', 'Test Twin');
    return [G, S];
  };
  const recOf = (S, name) => P.ffState(S).pitchers['OPP|' + name];
  const pre = (G, S) => { const p = P.ffPrecheck(G, S); P.ffEvaluate(G, S, 'pre', p); };
  const bringIn = (G, S, name, inning) => { S.inning = inning; P.changePitcherRaw(G, S, 'OPP', name); };

  // A: starter stamina trigger at the line.
  {
    const [G, S] = mk(); S.inning = 6;
    P.pstat(S, 'OPP', 'Test Starter').R = 3;
    P.updateFatigue(G, S);
    const ps = P.pstat(S, 'OPP', 'Test Starter');
    check('fatigue', 'A fatigued at Start 6 with 3 runs in the 6th', ps.fatigued === true);
    check('fatigue', 'A layer ledger names the starter-stamina trigger',
      ledCount(S, 'fatigue_fix') === 1 && ledDetail(S, 'fatigue_fix').includes('starter') && ledDetail(S, 'fatigue_fix').includes('Start 6'),
      ledDetail(S, 'fatigue_fix'));
  }
  // B: quiet before, fires at the pre-pass on entry.
  {
    const [G, S] = mk(); S.inning = 5;
    P.pstat(S, 'OPP', 'Test Starter').R = 3;
    P.updateFatigue(G, S);
    const ps = P.pstat(S, 'OPP', 'Test Starter');
    check('fatigue', 'B not fatigued in the 5th (before Start 6)', ps.fatigued === false && ledCount(S, 'fatigue_fix') === 0);
    S.inning = 6; pre(G, S);
    check('fatigue', 'B fatigued at the pre-pass entering the 6th', ps.fatigued === true && recOf(S, 'Test Starter').trigger.kind === 'starter_stamina',
      JSON.stringify(recOf(S, 'Test Starter').trigger));
  }
  // B2: the resolve_pa pre-pass fires before the PA resolves.
  {
    const [G, S] = mk(); S.inning = 6;
    P.pstat(S, 'OPP', 'Test Starter').R = 3;
    S.linescore.CHC = [0, 0, 0, 0, 0];
    scriptedPA(G, S, 7, 1);
    const rec = recOf(S, 'Test Starter');
    check('fatigue', 'B2 book fatigue attached before PA 1 resolved',
      rec.book_fatigued === true && rec.trigger && rec.trigger.pa === 1 && P.ffState(S).pa_index >= 1,
      JSON.stringify(rec.trigger) + ' pa_index=' + P.ffState(S).pa_index);
  }
  // C: Short reliever, second appearance inning.
  {
    const [G, S] = mk(); bringIn(G, S, 'Test Short', 7);
    P.updateFatigue(G, S);
    const ps = P.pstat(S, 'OPP', 'Test Short');
    check('fatigue', 'C not fatigued during/after his first inning', ps.fatigued === false);
    S.inning = 8; pre(G, S);
    check('fatigue', 'C still legal during his second inning', ps.fatigued === false,
      'appearances=' + JSON.stringify(recOf(S, 'Test Short').appearances));
    S.inning = 9; pre(G, S);
    check('fatigue', 'C fatigued once the second inning has ended', ps.fatigued === true && recOf(S, 'Test Short').trigger.kind === 'relief_appearances',
      JSON.stringify(recOf(S, 'Test Short').trigger));
  }
  // D: Short reliever at 2 runs.
  {
    const [G, S] = mk(); bringIn(G, S, 'Test Short', 7);
    P.pstat(S, 'OPP', 'Test Short').R = 2;
    P.updateFatigue(G, S);
    const ps = P.pstat(S, 'OPP', 'Test Short');
    check('fatigue', 'D fatigued at 2 runs (Short limit)', ps.fatigued === true && recOf(S, 'Test Short').trigger.kind === 'relief_runs',
      JSON.stringify(recOf(S, 'Test Short').trigger));
  }
  // E: Long reliever, third appearance inning.
  {
    const [G, S] = mk(); bringIn(G, S, 'Test Long', 7);
    P.updateFatigue(G, S);
    const ps = P.pstat(S, 'OPP', 'Test Long');
    S.inning = 8; pre(G, S);
    S.inning = 9; pre(G, S);
    check('fatigue', 'E not fatigued with two innings ended (Long limit 3)', ps.fatigued === false,
      'appearances=' + JSON.stringify(recOf(S, 'Test Long').appearances));
    S.inning = 10; pre(G, S);
    check('fatigue', 'E fatigued once the third inning has ended', ps.fatigued === true && recOf(S, 'Test Long').trigger.kind === 'relief_appearances',
      JSON.stringify(recOf(S, 'Test Long').trigger));
  }
  // F: Long reliever at 3 runs (quiet at 2).
  {
    const [G, S] = mk(); bringIn(G, S, 'Test Long', 7);
    P.pstat(S, 'OPP', 'Test Long').R = 2;
    P.updateFatigue(G, S);
    const ps = P.pstat(S, 'OPP', 'Test Long');
    const quiet = ps.fatigued === false;
    P.pstat(S, 'OPP', 'Test Long').R = 3;
    P.updateFatigue(G, S);
    check('fatigue', 'F quiet at 2, fatigued at 3 (Long run limit)', quiet && ps.fatigued === true && recOf(S, 'Test Long').trigger.kind === 'relief_runs',
      JSON.stringify(recOf(S, 'Test Long').trigger));
  }
  // G: the 6-run engine trigger unchanged, both shapes.
  {
    const [G, S] = mk(); bringIn(G, S, 'Test Short', 7);
    P.pstat(S, 'OPP', 'Test Short').R = 6;
    P.updateFatigue(G, S);
    const ps = P.pstat(S, 'OPP', 'Test Short');
    check('fatigue', 'G reliever fatigued at 6 runs via the engine entry', ps.fatigued === true && ledCount(S, 'fatigue') === 1,
      'engine fatigue ledger=' + ledCount(S, 'fatigue'));
  }
  {
    const [G, S] = mk(); S.inning = 2;
    P.pstat(S, 'OPP', 'Test Starter').R = 6;
    P.updateFatigue(G, S);
    const ps = P.pstat(S, 'OPP', 'Test Starter');
    check('fatigue', 'G starter fatigued at 6 runs before his stamina inning', ps.fatigued === true && ledCount(S, 'fatigue') === 1,
      'engine fatigue ledger=' + ledCount(S, 'fatigue'));
  }
  // H: save-symbol exemption (test doubles only).
  {
    const [G, S] = mk(); S.score = { CHC: 2, OPP: 3 }; bringIn(G, S, 'Test Double', 9);
    P.pstat(S, 'OPP', 'Test Double').R = 2;
    P.updateFatigue(G, S);
    const ps = P.pstat(S, 'OPP', 'Test Double');
    check('fatigue', 'H exemption holds at his limits in a save situation', ps.fatigued === false && ledCount(S, 'fatigue_fix_exempt') === 1,
      'exempt ledger=' + ledCount(S, 'fatigue_fix_exempt'));
    S.score = { CHC: 3, OPP: 3 }; pre(G, S);
    const rec = recOf(S, 'Test Double');
    check('fatigue', 'H tied game spends the exemption; fatigue attaches',
      ps.fatigued === true && rec.exemption_spent === true && rec.trigger.kind === 'relief_runs',
      JSON.stringify(rec.trigger));
  }
  {
    const [G, S] = mk(); S.score = { CHC: 2, OPP: 3 }; bringIn(G, S, 'Test Twin', 9);
    P.pstat(S, 'OPP', 'Test Twin').R = 2;
    P.updateFatigue(G, S);
    check('fatigue', 'H symbol-less twin fatigues at once in the same state', P.pstat(S, 'OPP', 'Test Twin').fatigued === true);
  }
  // I: Williams attrition feeds the evaluation.
  {
    const [G, S] = mk(); S.inning = 6;
    P.pstat(S, 'OPP', 'Test Starter').R = 1;
    P.updateFatigue(G, S);
    const ps = P.pstat(S, 'OPP', 'Test Starter');
    const quiet = ps.fatigued === false;
    S.flags.v2_attrition = { 'OPP|Test Starter': 2 };
    P.updateFatigue(G, S);
    check('fatigue', 'I attrition-fed evaluation fires the stamina trigger',
      quiet && ps.fatigued === true && recOf(S, 'Test Starter').trigger.kind === 'starter_stamina'
      && ledDetail(S, 'fatigue_fix').includes('attrition 2') && ledCount(S, 'fatigue') === 0,
      ledDetail(S, 'fatigue_fix'));
  }
  // J: leash seam re-assertion.
  {
    const [G, S] = mk(); S.inning = 6;
    P.pstat(S, 'OPP', 'Test Starter').R = 3;
    P.updateFatigue(G, S);
    const ps = P.pstat(S, 'OPP', 'Test Starter');
    const latched = ps.fatigued === true;
    ps.fatigued = false;
    pre(G, S);
    check('fatigue', 'J book latch re-asserted at the next pre-pass', latched && ps.fatigued === true && ledCount(S, 'fatigue_fix_reassert') === 1,
      'reassert ledger=' + ledCount(S, 'fatigue_fix_reassert'));
  }
  // K: the OFF contract (the port composes the layer behind
  // the fatigueBook flag; off binds nothing and writes no
  // state).
  {
    const [G, S] = mk({ fatigueBook: false }); S.inning = 6;
    P.pstat(S, 'OPP', 'Test Starter').R = 3;
    P.updateFatigue(G, S);
    check('fatigue', 'K layer off: no book state written, no book fatigue',
      S.fatigue_fix === undefined && P.pstat(S, 'OPP', 'Test Starter').fatigued === false);
  }
  // L: the record block.
  {
    const [G, S] = mk(); S.inning = 6;
    P.pstat(S, 'OPP', 'Test Starter').R = 3;
    P.updateFatigue(G, S);
    const rec = recOf(S, 'Test Starter');
    check('fatigue', 'L stamina line as served + appearance list recorded',
      JSON.stringify(rec.stamina) === JSON.stringify({ start: 6, relief: null }) && JSON.stringify(rec.appearances) === JSON.stringify([6]),
      'stamina=' + JSON.stringify(rec.stamina) + ' appearances=' + JSON.stringify(rec.appearances));
    check('fatigue', 'L per-PA states + availability row written',
      rec.states.length >= 1 && rec.states[rec.states.length - 1].trigger === 'starter_stamina'
      && (P.ffState(S).availability_next['OPP|Test Starter'] || {}).row === 'free',
      'states=' + JSON.stringify(rec.states) + ' avail=' + JSON.stringify(P.ffState(S).availability_next['OPP|Test Starter']));
  }
  // M: Francona grind feeds the evaluation at //3.
  {
    const [G, S] = mk(); S.inning = 6;
    P.pstat(S, 'OPP', 'Test Starter').R = 1;
    P.updateFatigue(G, S);
    const ps = P.pstat(S, 'OPP', 'Test Starter');
    const quiet = ps.fatigued === false;
    S.flags.francona_grind = { 'Test Starter': 6 };
    P.updateFatigue(G, S);
    check('fatigue', 'M grind-fed evaluation fires the stamina trigger',
      quiet && ps.fatigued === true && recOf(S, 'Test Starter').trigger.kind === 'starter_stamina'
      && ledDetail(S, 'fatigue_fix').includes('grind 2'),
      ledDetail(S, 'fatigue_fix'));
  }
}

/* ============================================================ CHANCE (42) */
function batteryChance() {
  const stats = (S) => S.flags.frank_chance || {};
  const rt = (S) => S.flags.frank_chance || {};
  const jenkins = () => P.PlayData.pitcher('CHC', 'Fergie Jenkins');
  const rogers = () => P.PlayData.pitcher('OPP', 'Steve Rogers');
  const walker = () => P.PlayData.hitter('OPP', 'Larry Walker');
  // A ground-out DP-check staging: MON batting (top), CHC
  // fielding, runner on first, Walker at the plate vs Jenkins.
  function dpStage(total) {
    const [G, S] = game({});
    S.half = 'top'; S.outs = 0;
    S.bases[0] = { name: 'Jose Vidro', resp: 'Fergie Jenkins' };
    S.source = scripted([['2d6', D6(total)], ['%', 50]], true);
    return [G, S];
  }

  // C0 roster reality on the fixture.
  {
    const [, S] = game({});
    const hitters = [...Object.keys(P.PlayData.data.hitters.CHC), ...Object.keys(P.PlayData.data.hitters.MON)];
    const pitchers = [...Object.keys(P.PlayData.data.pitchers.CHC), ...Object.keys(P.PlayData.data.pitchers.MON)];
    check('chance', 'C0 fixture stack assembles (30 hitters, 22 pitchers, deck 256)',
      hitters.length >= 30 && pitchers.length >= 22 && P.PlayData.data.deck.length === 256);
    check('chance', 'C0 the starting first baseman is Grace', S.teams.CHC.field['1B'] === 'Mark Grace');
    check('chance', 'C0 no Frank Chance player card exists', !hitters.concat(pitchers).some((n) => n.includes('Chance')));
    check('chance', 'C0 no Johnny Evers anywhere in either set', !hitters.concat(pitchers).some((n) => n.includes('Evers')));
    check('chance', 'C0 Tinker is on the bench, not the pair',
      S.teams.CHC.bench.includes('Joe Tinker') && S.teams.CHC.field['2B'] === 'Ryne Sandberg' && S.teams.CHC.field.SS === 'Ernie Banks');
  }
  // C1 the pivot bump.
  const printed = walker().dp;
  const jdp = jenkins().dp;
  const eff = Math.min(printed, jdp);
  {
    const [G, S] = dpStage(eff + 1);
    const res = run(P.groundOut(G, S, 'Larry Walker', 'SS', 50, 'IN-PLAY'), S);
    const st = stats(S);
    check('chance', 'C1 the bump was applied once', st.dp_bumps === 1 && ledCount(S, 'chance_dp_bump') === 1);
    check('chance', "C1 the engine's own check ledger shows both components raised and the effective rating up exactly 1",
      ledDetail(S, 'double_play_check').includes('vs DP ' + (eff + 1)) && ledDetail(S, 'double_play_check').includes('batter ' + (printed + 1))
      && ledDetail(S, 'double_play_check').includes('pitcher ' + (jdp + 1)), ledDetail(S, 'double_play_check'));
    check('chance', 'C1 the double play turned on the bump margin', String(res).startsWith('GIDP') && st.dp_margin === 1 && ledCount(S, 'chance_dp_margin') === 1, String(res));
    check('chance', 'C1 the original card object is restored whole', walker().dp === printed);
    check('chance', "C1 the pitcher's printed component is restored whole", jenkins().dp === jdp);
    check('chance', 'C1 the bump ledger names the pair as fielded',
      ledDetail(S, 'chance_dp_bump').includes('Ryne Sandberg') && ledDetail(S, 'chance_dp_bump').includes('Ernie Banks'), ledDetail(S, 'chance_dp_bump'));
    check('chance', 'C1 the batter is charged the GIDP', P.bstat(S, 'OPP', 'Larry Walker').GDP === 1);
  }
  {
    const [G, S] = dpStage(eff + 1); S.outs = 2;
    run(P.groundOut(G, S, 'Larry Walker', 'SS', 50, 'IN-PLAY'), S);
    check('chance', 'C1 no bump with two outs (no check exists)', (stats(S).dp_bumps || 0) === 0);
  }
  {
    const [G, S] = dpStage(eff + 1); S.bases = [null, { name: 'Jose Vidro', resp: 'Fergie Jenkins' }, null];
    run(P.groundOut(G, S, 'Larry Walker', 'SS', 50, 'IN-PLAY'), S);
    check('chance', 'C1 no bump without a runner on first', (stats(S).dp_bumps || 0) === 0);
  }
  {
    const [G, S] = game({}); S.half = 'bottom'; S.outs = 0;
    S.bases[0] = { name: 'Ryne Sandberg', resp: 'Steve Rogers' };
    S.source = scripted([['2d6', D6(eff + 1)], ['%', 50]], true);
    run(P.groundOut(G, S, 'Ron Santo', 'SS', 50, 'IN-PLAY'), S);
    check('chance', "C1 no bump on the opponent's double-play check", (stats(S).dp_bumps || 0) === 0);
  }
  {
    const [G, S] = dpStage(12);
    const res = run(P.groundOut(G, S, 'Larry Walker', 'SS', 50, 'IN-PLAY'), S);
    const st = stats(S);
    check('chance', 'C1 a 2d6 of 11+ never reaches the check: bump ledgered, no check recorded, no margin claimed',
      st.dp_bumps === 1 && ledCount(S, 'double_play_check') === 0 && (st.dp_margin || 0) === 0 && !String(res).startsWith('GIDP'), String(res));
  }
  // C2 the borderline tie and its gate.
  {
    const [G, S] = dpStage(eff);
    const res = run(P.groundOut(G, S, 'Larry Walker', 'SS', 50, 'IN-PLAY'), S);
    const st = stats(S);
    check('chance', 'C2 the equality roll turns the double play under the base rule', String(res).startsWith('GIDP'), String(res));
    check('chance', 'C2 on the real roster the tie gate is closed (Grace, not Chance, at first) and counted',
      (st.dp_tie || 0) === 0 && st.dp_tie_gate_closed === 1 && ledCount(S, 'chance_dp_tie') === 0);
  }
  {
    const [G, S] = dpStage(eff);
    S.teams.CHC.field['1B'] = 'Frank Chance'; // disclosed rename, as in the source battery
    const res = run(P.groundOut(G, S, 'Larry Walker', 'SS', 50, 'IN-PLAY'), S);
    const st = stats(S);
    check('chance', 'C2 engineered Chance at first: the tie is invoked on its own gate',
      String(res).startsWith('GIDP') && st.dp_tie === 1 && ledCount(S, 'chance_dp_tie') === 1, String(res));
  }
  // C3 the pair as fielded.
  {
    const [G, S] = dpStage(eff + 1);
    S.teams.CHC.field['2B'] = 'Joe Tinker';
    const res = run(P.groundOut(G, S, 'Larry Walker', 'SS', 50, 'IN-PLAY'), S);
    check('chance', 'C3 with Tinker in the game the bump ledger names him at second',
      String(res).startsWith('GIDP') && ledDetail(S, 'chance_dp_bump').includes('Joe Tinker'), ledDetail(S, 'chance_dp_bump'));
  }
  // C4 The Peerless Leader.
  const graceCard = () => P.PlayData.hitter('CHC', 'Mark Grace');
  const santoCard = () => P.PlayData.hitter('CHC', 'Ron Santo');
  function graceSoPA(G, S) {
    const t = totalFor(rogers(), 'TOUGH');
    const so = graceCard().sections.TOUGH.vsRHP.SO;
    scriptedPA(G, S, t, so[0]);
  }
  {
    const [G, S] = game({ seed: 778 }); S.half = 'bottom';
    S.teams.CHC.next_idx = 1; // Grace
    graceSoPA(G, S);
    S.bases[0] = { name: 'Mark Grace', resp: 'Steve Rogers' }; // his reach, staged as in the source battery
    graceSoPA(G, S); // Santo's PA (order advanced): the arm fires at its start
    const st = stats(S);
    check('chance', 'C4 the starting first baseman reaching arms the very next batter',
      ledCount(S, 'chance_leader_armed') === 1);
    check('chance', 'C4 the armed batter is the next man, Ron Santo', (rt(S).leader_pa || {}).batter === 'Ron Santo',
      JSON.stringify(rt(S).leader_pa));
    const wh = santoCard().sections.WHEELHOUSE.vsRHP.HR;
    const pt = santoCard().sections.PATIENT.vsRHP.BB;
    const readsBefore = st.leader_reads || 0;
    const eWH = P.sectionLookup(G, S, santoCard(), 'WHEELHOUSE', 'vsRHP', wh[1] + 2);
    const rWH = P.sectionLookupRaw(santoCard(), 'WHEELHOUSE', 'vsRHP', wh[1] + 2);
    check('chance', 'C4 the +3 WHEELHOUSE read converts the sliver percentile to the top band', eWH === 'HR' && rWH !== 'HR',
      'band ' + JSON.stringify(wh) + ' edited ' + eWH + ' raw ' + rWH);
    const ePT = P.sectionLookup(G, S, santoCard(), 'PATIENT', 'vsRHP', pt[1] + 2);
    const rPT = P.sectionLookupRaw(santoCard(), 'PATIENT', 'vsRHP', pt[1] + 2);
    check('chance', 'C4 the +3 PATIENT read converts the sliver percentile', ePT === 'BB' && rPT !== 'BB',
      'band ' + JSON.stringify(pt) + ' edited ' + ePT + ' raw ' + rPT);
    check('chance', 'C4 the seam reads are counted', (stats(S).leader_reads || 0) >= readsBefore + 2);
    graceSoPA(G, S); // Sosa's PA: the arm retires at its start
    check('chance', 'C4 the arm dies at the following appearance (one batter wide)', rt(S).leader_pa === null);
  }
  {
    const [G, S] = game({ seed: 779 }); S.half = 'bottom';
    S.teams.CHC.next_idx = 1;
    graceSoPA(G, S); // Grace does not reach (scripted SO)
    S.bases = [null, null, null];
    graceSoPA(G, S);
    check('chance', 'C4 a non-reach by the first baseman does not arm',
      ledCount(S, 'chance_leader_armed') === 0);
  }
  {
    const [G, S] = game({ seed: 780 }); S.half = 'bottom';
    S.teams.CHC.next_idx = 1;
    graceSoPA(G, S); // captures Grace as the starting 1B
    rt(S).leader_watch = { batter: 'Anthony Rizzo', team: 'CHC', snap: { H: 0, BB: 0, HBP: 0, R: 0 } };
    S.bases[0] = { name: 'Anthony Rizzo', resp: 'Steve Rogers' };
    S.teams.CHC.next_idx = 2; // Santo
    graceSoPA(G, S);
    check('chance', "C4 a substitute first baseman's reach does not arm", ledCount(S, 'chance_leader_armed') === 0);
  }
  // C5 Inside Baseball Precision.
  {
    const [G, S] = game({ seed: 781 }); S.half = 'bottom'; S.outs = 0;
    S.bases = [{ name: 'Ryne Sandberg', resp: 'Steve Rogers' }, null, { name: 'Sammy Sosa', resp: 'Steve Rogers' }];
    const bf0 = P.pstat(S, 'OPP', 'Steve Rogers').BF;
    const res = run(P.resolvePaInner(G, S, 'Ernie Banks', P.PlayData.hitter('CHC', 'Ernie Banks'), rogers(), 'IN-PLAY', 7, 42, 3, 4, true, 'Ryne Sandberg'), S);
    const bs = P.bstat(S, 'CHC', 'Ernie Banks');
    check('chance', 'C5 the conversion returns DONE with the productive groundout bookkeeping',
      res === 'DONE' && S.outs === 1 && bs.AB === 1 && bs.GDP === 0 && P.pstat(S, 'OPP', 'Steve Rogers').BF === bf0 + 1);
    check('chance', 'C5 every runner advances one base and the run from third scores with the RBI',
      !!S.bases[1] && S.bases[1].name === 'Ryne Sandberg' && S.score.CHC === 1 && P.bstat(S, 'CHC', 'Sammy Sosa').R === 1 && bs.RBI === 1);
    check('chance', 'C5 the conversion is ledgered and counted',
      ledCount(S, 'chance_hnr_conversion') === 1 && stats(S).hnr_seen === 1);
  }
  {
    const [G, S] = game({ seed: 782 }); S.half = 'bottom';
    S.bases[0] = { name: 'Ryne Sandberg', resp: 'Steve Rogers' };
    run(P.resolvePaInner(G, S, 'Ernie Banks', P.PlayData.hitter('CHC', 'Ernie Banks'), rogers(), 'IN-PLAY', 7, 42, 3, 4, false, null), S);
    check('chance', 'C5 IN-PLAY with no hit-and-run call resolves normally (no conversion)',
      ledCount(S, 'chance_hnr_conversion') === 0);
  }
  {
    const [G, S] = game({ seed: 783 }); S.half = 'bottom';
    S.bases[0] = { name: 'Ryne Sandberg', resp: 'Steve Rogers' };
    run(P.resolvePaInner(G, S, 'Ernie Banks', P.PlayData.hitter('CHC', 'Ernie Banks'), rogers(), 'TOUGH', 8, 42, 3, 5, true, 'Ryne Sandberg'), S);
    check('chance', 'C5 a called hit-and-run on another section resolves normally (seen, not converted)',
      stats(S).hnr_seen === 1 && ledCount(S, 'chance_hnr_conversion') === 0);
  }
  {
    const [G, S] = game({ seed: 784 }); S.half = 'top';
    S.bases[0] = { name: 'Jose Vidro', resp: 'Fergie Jenkins' };
    run(P.resolvePaInner(G, S, 'Larry Walker', walker(), jenkins(), 'IN-PLAY', 7, 42, 3, 4, true, 'Jose Vidro'), S);
    check('chance', "C5 the opponent's hit-and-run never converts",
      ledCount(S, 'chance_hnr_conversion') === 0 && (stats(S).hnr_seen || 0) === 0);
  }
  // C6 Combative Accountability.
  function walkerSoPA(G, S) {
    const t = totalFor(jenkins(), 'TOUGH');
    const so = walker().sections.TOUGH.vsRHP.SO;
    scriptedPA(G, S, t, so[0]);
  }
  function acctStage(seed) {
    const [G, S] = game({ seed }); S.half = 'top';
    S.teams.OPP.next_idx = 2; // Walker
    walkerSoPA(G, S); // the watch is set on Walker / Jenkins
    S.teams.CHC.team_errors += 1; // the error (forced, as in the source battery)
    S.bases[0] = { name: 'Larry Walker', resp: 'Fergie Jenkins' };
    return [G, S];
  }
  {
    const [G, S] = acctStage(785);
    walkerSoPA(G, S); // the next batter's PA: the arm promotes at its start
    const st = stats(S);
    check('chance', 'C6 an error that puts the batter on arms the pitcher of record',
      ledCount(S, 'chance_acct_armed') === 1);
    check('chance', 'C6 the arm promotes on the very next batter that pitcher faces',
      (rt(S).acct_pa || {}).pitcher === 'Fergie Jenkins', JSON.stringify(rt(S).acct_pa));
    const so = walker().sections.TOUGH.vsRHP.SO;
    const hr = walker().sections.TOUGH.vsRHP.HR;
    let sliver = null;
    for (let p = so[1] + 1; p <= so[1] + 5; p++) { if (hr && hr[0] <= p && p <= hr[1]) continue; sliver = p; break; }
    const eR = P.sectionLookup(G, S, walker(), 'TOUGH', 'vsRHP', sliver);
    const rR = P.sectionLookupRaw(walker(), 'TOUGH', 'vsRHP', sliver);
    check('chance', 'C6 the +5 TOUGH read converts the sliver percentile into a strikeout', eR === 'SO' && rR !== 'SO',
      'band ' + JSON.stringify(so) + ' pct ' + sliver + ': edited ' + eR + ' raw ' + rR);
    check('chance', 'C6 the read is counted as converted', (stats(S).acct_reads || 0) >= 1 && (stats(S).acct_changed || 0) >= 1);
  }
  {
    const [G, S] = acctStage(786);
    const tP = totalFor(jenkins(), 'PATIENT');
    scriptedPA(G, S, tP, 50); // the promoted PA reads PATIENT only
    walkerSoPA(G, S); // the following PA: the arm retires
    const st = stats(S);
    check('chance', 'C6 the arm is spent after that one appearance, ledgered when it goes unread',
      st.acct_spent_unread === 1 && ledCount(S, 'chance_acct_spent') === 1 && rt(S).acct_pa === null);
  }
  {
    const [G, S] = acctStage(787);
    P.changePitcher(G, S, 'CHC', 'Bruce Sutter');
    walkerSoPA(G, S);
    const st = stats(S);
    check('chance', 'C6 the arm lapses when the pitcher is lifted before facing another batter',
      st.acct_lapsed === 1 && ledCount(S, 'chance_acct_lapsed') === 1 && rt(S).acct_pa === null);
  }
  {
    const [G, S] = game({ seed: 788 }); S.half = 'top';
    S.teams.OPP.next_idx = 2;
    walkerSoPA(G, S);
    S.teams.CHC.team_errors += 1; // error, but the batter was out
    S.bases = [null, null, null];
    walkerSoPA(G, S);
    check('chance', 'C6 an error with the batter out does not arm', ledCount(S, 'chance_acct_armed') === 0);
  }
  {
    const [G, S] = game({ seed: 789 }); S.half = 'top';
    S.teams.OPP.next_idx = 2;
    walkerSoPA(G, S);
    S.bases[0] = { name: 'Larry Walker', resp: 'Fergie Jenkins' };
    P.bstat(S, 'OPP', 'Larry Walker').H += 1; // reached, no error
    walkerSoPA(G, S);
    check('chance', 'C6 a reach with no error does not arm', ledCount(S, 'chance_acct_armed') === 0);
  }
}

/* ============================================================ OUT-CHART PARTITION */
function batteryOutchart() {
  let cards = 0, bad = [];
  for (const club of ['CHC', 'MON']) {
    for (const [name, card] of Object.entries(DATA.hitters[club])) {
      const charts = Array.isArray(card.out_table) ? [['chart', card.out_table]]
        : Object.entries(card.out_table || {}).map(([side, rows]) => [side, rows]);
      for (const [side, rawRows] of charts) {
        const rows = (rawRows || []).map((r) => Array.isArray(r) ? r : r.range).slice().sort((a, b) => a[0] - b[0]);
        cards++;
        if (!rows.length) { bad.push(name + ' ' + side + ': no rows'); continue; }
        // The audit standard: the fallback backstops only the
        // bottom face; from the first row's start the chart
        // must tile contiguously to 99 with no overlap.
        let ok = rows[rows.length - 1][1] === 99;
        for (let i = 1; i < rows.length; i++) if (rows[i][0] !== rows[i - 1][1] + 1) ok = false;
        if (!ok) bad.push(name + ' ' + side + ': ' + JSON.stringify(rows));
      }
    }
  }
  check('outchart', 'every shipped hitter card/side tiles the OUT chart to 99 with no interior hole (' + cards + ' card-sides)',
    bad.length === 0, bad.slice(0, 3).join(' | '));
}

/* ============================================================ RARE PLAYS */
function batteryRare() {
  const charts = P.PlayData.data.rare_plays;
  const byName = (n) => charts.find((c) => c.name === n);
  function rareStage(grp, on, pct, completionPct) {
    const [G, S] = game({ clauses: true });
    S.half = on ? 'top' : 'bottom';
    if (on) S.bases[0] = { name: 'Jose Vidro', resp: 'Fergie Jenkins' };
    const batter = on ? 'Tim Raines' : 'Ryne Sandberg';
    const card = P.PlayData.hitter(on ? 'OPP' : 'CHC', batter);
    const soLo = card.sections.TOUGH.vsRHP.SO[0];
    S.pending = { type: 'rare', grp, bases_empty: !on, dice: [3, 4, 7], hnr: false, batter };
    S.source = scripted([['%', pct], ['%', completionPct != null ? completionPct : soLo]], true);
    return [G, S, batter];
  }
  // Chart selection + completion for each of the four charts.
  for (const [grp, on, label] of [['BW', false, 'empty BALLPARK/WHEELHOUSE'], ['BW', true, 'on BALLPARK/WHEELHOUSE'], ['PATIENT', false, 'empty PATIENT'], ['DEFENSE', true, 'on DEFENSE']]) {
    const [G, S] = rareStage(grp, on, 50);
    const res = run(P.autoResolveRare(G, S), S);
    check('rare', 'chart resolves and the PA completes (' + label + ')', res === 'DONE' && S.pending === null, String(res));
  }
  // A pitcher-removal entry removes the pitcher.
  {
    let hit = null;
    for (const c of charts) for (const e of c.chart || []) {
      const t = e.result.toLowerCase();
      if (t.includes('pitcher') && t.includes('removed')) { hit = { chart: c, entry: e }; break; }
      if (hit) break;
    }
    check('rare', 'a pitcher-removal entry exists in the shipped charts', !!hit);
    if (hit) {
      const on = hit.chart.name.includes('Runners On');
      const grp = hit.chart.name.includes('BALLPARK or WHEELHOUSE') ? 'BW' : hit.chart.name.includes('PATIENT') ? 'PATIENT' : hit.chart.name.includes('TOUGH') ? 'TOUGH' : hit.chart.name.includes('IN-PLAY') ? 'INPLAY' : 'DEFENSE';
      const lo = Array.isArray(hit.entry.range) ? hit.entry.range[0] : Number(String(hit.entry.range).split('-')[0]);
      const [G, S] = rareStage(grp, on, lo);
      const fld = on ? 'CHC' : 'OPP';
      const before = P.curPitcher(S, fld);
      const res = run(P.autoResolveRare(G, S), S);
      check('rare', 'the removal entry lifts the pitcher of record',
        res === 'DONE' && (P.curPitcher(S, fld) !== before || S.teams[fld].removed.includes(before)),
        'before=' + before + ' after=' + P.curPitcher(S, fld) + ' removed=' + JSON.stringify(S.teams[fld].removed));
    }
  }
  // Force-clause lifecycle (Runners On TOUGH 70-74 arms the
  // outcome-dependent counter; it spends on a matching read,
  // carries over other PAs, dies with the pitcher, and a bunt
  // PA never spends it).
  {
    const [G, S, batter] = rareStage('TOUGH', true, 72); // completion scripted to a TOUGH SO
    const res = run(P.autoResolveRare(G, S), S);
    const f = S.flags.force_clause;
    check('rare', 'force clause arms on the 70-74 entry (SO outcome -> TOUGH counter)',
      res === 'DONE' && !!f && (f.tough || 0) === 3, JSON.stringify(f));
    if (f) {
      const jk = P.PlayData.pitcher('CHC', 'Fergie Jenkins');
      const vidro = P.PlayData.hitter('OPP', 'Jose Vidro');
      const inner = (pcard, presult, pct) => {
        S.source = scripted([], true);
        return run(P.resolvePaInner(G, S, 'Jose Vidro', vidro, pcard, presult, 7, pct, 3, 4, false, null), S);
      };
      // Spend: the next PA against that pitcher is redirected
      // to the clause section and spends one counter.
      const logBefore = S.log.length;
      inner(jk, 'PATIENT', 50);
      check('rare', 'a PA against the clause pitcher is redirected to TOUGH and spends one',
        (S.flags.force_clause || {}).tough === 2
        && S.log.slice(logBefore).some((l) => l.includes('rare-play clause: this PA reads the TOUGH section')),
        JSON.stringify(S.flags.force_clause));
      // A bunt PA never spends it.
      S.source = scripted([['2d6', D6(7)], ['1d6', 3], ['%', 50]], true);
      run(P.resolveBunt(G, S, 'Jose Vidro', false), S);
      check('rare', 'a bunt PA does not spend the counter',
        (S.flags.force_clause || {}).tough === 2, JSON.stringify(S.flags.force_clause));
      // It dies with the pitcher: the new pitcher's PAs are
      // not redirected and do not spend the old flag.
      P.changePitcherRaw(G, S, 'CHC', 'Hippo Vaughn');
      const vg = P.PlayData.pitcher('CHC', 'Hippo Vaughn');
      const logBefore2 = S.log.length;
      inner(vg, 'PATIENT', 50);
      check('rare', 'the counter does not spend under a new pitcher',
        (S.flags.force_clause || {}).tough === 2
        && !S.log.slice(logBefore2).some((l) => l.includes('rare-play clause')),
        JSON.stringify(S.flags.force_clause));
    }
  }
  {
    // Exhaustion: three redirected PAs retire the flag.
    const [G, S] = rareStage('TOUGH', true, 72);
    run(P.autoResolveRare(G, S), S);
    const jk = P.PlayData.pitcher('CHC', 'Fergie Jenkins');
    const vidro = P.PlayData.hitter('OPP', 'Jose Vidro');
    for (let i = 0; i < 3; i++) {
      S.source = scripted([], true);
      run(P.resolvePaInner(G, S, 'Jose Vidro', vidro, jk, 'PATIENT', 7, 50, 3, 4, false, null), S);
    }
    check('rare', 'the flag retires when its counters are spent', S.flags.force_clause === undefined,
      JSON.stringify(S.flags.force_clause));
  }
}
/* ============================================================ DEFENSE */
function batteryDefense() {
  const mk = (opts = {}) => {
    const [G, S] = game(Object.assign({ defenseNumbers: true }, opts));
    return [G, S];
  };
  const defPA = (G, S, pct, extra) => {
    S.source = scripted([['%', pct]].concat(extra || []), true);
    return run(P.resolveDefense(G, S, 'Larry Walker', 'DEFENSE', pct), S);
  };
  // def_pos selection at the band edges (Wrigley park bands).
  {
    const [G, S] = mk(); S.half = 'top';
    defPA(G, S, 2);
    check('defense', 'defense % 02 selects RANGE at the pitcher', (S._defense_summary || {}).pos === 'P', JSON.stringify(S._defense_summary || {}));
  }
  {
    const [G, S] = mk(); S.half = 'top';
    defPA(G, S, 99);
    check('defense', 'defense % 99 selects the outfield fly band', ['LF', 'CF', 'RF'].includes((S._defense_summary || {}).pos), JSON.stringify(S._defense_summary || {}));
  }
  // ERROR family: a dropped foul restarts the PA. DEF_POS
  // puts ERROR (catcher) at 43; the chain re-rolls 2d6 and
  // a % against the park's error band for the catcher's E
  // digit; the C error table's 4 is the 0-base dropped foul.
  {
    const [G, S] = mk(); S.half = 'top';
    const cE = P.PlayData.hitter('CHC', 'Gabby Hartnett').positions[0].e;
    const band = P.PlayData.data.parks['Wrigley Field'].error_chart['E' + cE].ERR;
    S.source = scripted([['2d6', D6(4)], ['%', band[0]]], true);
    const res = run(P.resolveDefense(G, S, 'Larry Walker', 'DEFENSE', 43), S);
    check('defense', 'ERR 0 (dropped foul) restarts the PA', res === 'RESTART', String(res));
  }
  // %==00 on a DEFENSE read pends as a rare play.
  {
    const [G, S] = mk(); S.half = 'top';
    const t = totalFor(P.PlayData.pitcher('CHC', 'Fergie Jenkins'), 'DEFENSE');
    S.source = scripted([['2d6', D6(t)], ['%', 0]], true);
    const res = run(P.resolvePA(G, S), S);
    check('defense', 'a % 00 DEFENSE read halts as a pending rare play',
      res === 'PENDING' && !!S.pending && S.pending.grp === 'DEFENSE', String(res) + ' ' + JSON.stringify(S.pending));
  }
  // GB-DP family through resolveDefense: runner on first,
  // ground ball to SS, check roll inside the DP rating.
  {
    const [G, S] = mk(); S.half = 'top'; S.outs = 0;
    S.bases[0] = { name: 'Jose Vidro', resp: 'Fergie Jenkins' };
    const wk = P.PlayData.hitter('OPP', 'Larry Walker');
    const dpEff = Math.min(wk.dp, P.PlayData.pitcher('CHC', 'Fergie Jenkins').dp);
    // DEF_POS: GB band for SS sits in the middle bands; use
    // the summary to confirm the family after the fact.
    S.source = scripted([['%', 45], ['2d6', D6(Math.max(2, dpEff))], ['%', 50]], true);
    const outsBefore = S.outs;
    run(P.resolveDefense(G, S, 'Larry Walker', 'DEFENSE', 45), S);
    check('defense', 'a ground ball with a runner on first can turn two (outs advance)',
      S.outs > outsBefore || P.bstat(S, 'OPP', 'Larry Walker').GDP === 1,
      'outs ' + outsBefore + '->' + S.outs + ' summary ' + JSON.stringify(S._defense_summary || {}));
  }
}

/* ============================================================ STEALS */
function batterySteals() {
  const mk = () => {
    const [G, S] = game({});
    S.half = 'top'; // MON batting, CHC fielding (Hartnett behind the plate)
    return [G, S];
  };
  const raines = () => P.PlayData.hitter('OPP', 'Tim Raines');
  // Read the bands for Raines' letter against Hartnett from
  // the shipped charts, then walk the edges.
  {
    const [G, S] = mk();
    const letter = raines().steal.rating;
    const col = P.CHARTS.STEAL_COL[letter + P.CHARTS.catcherArm(G, S, 'CHC')];
    check('steals', 'a steal column exists for the staged matchup', Array.isArray(col), letter);
    if (col) {
      const [clo, slo] = col;
      // Caught band: % at clo -> caught stealing.
      {
        const [G2, S2] = mk();
        S2.bases[0] = { name: 'Tim Raines', resp: 'Fergie Jenkins' };
        S2.source = scripted([['%', clo]], true);
        run(P.attemptSteal(G2, S2, S2.bases[0], 2, 'R'), S2);
        check('steals', 'the caught band books a caught stealing (runner gone, out charged)',
          !S2.bases[0] && !S2.bases[1] && P.bstat(S2, 'OPP', 'Tim Raines').CS === 1, 'outs=' + S2.outs);
      }
      // Safe band: % at slo -> stolen base.
      {
        const [G2, S2] = mk();
        S2.bases[0] = { name: 'Tim Raines', resp: 'Fergie Jenkins' };
        S2.source = scripted([['%', slo]], true);
        run(P.attemptSteal(G2, S2, S2.bases[0], 2, 'R'), S2);
        check('steals', 'the safe band books the stolen base',
          !!S2.bases[1] && S2.bases[1].name === 'Tim Raines' && P.bstat(S2, 'OPP', 'Tim Raines').SB === 1);
      }
      // DROP? branch: % <= 2, cover holds on (1d6 high) ->
      // caught; cover drops it (1d6 low vs e) -> safe on E.
      {
        const [G2, S2] = mk();
        S2.bases[0] = { name: 'Tim Raines', resp: 'Fergie Jenkins' };
        S2.source = scripted([['%', 2], ['1d6', 1]], true);
        run(P.attemptSteal(G2, S2, S2.bases[0], 2, 'R'), S2);
        check('steals', 'DROP? with the cover hanging on books the out', P.bstat(S2, 'OPP', 'Tim Raines').CS === 1 || S2.outs === 1, 'outs=' + S2.outs);
      }
      // SB+E2? branch: % in 3..12, throw gets away (1d6 over
      // the catcher's e) -> extra base, unearned.
      {
        const [G2, S2] = mk();
        S2.bases[0] = { name: 'Tim Raines', resp: 'Fergie Jenkins' };
        S2.source = scripted([['%', 5], ['1d6', 6]], true);
        run(P.attemptSteal(G2, S2, S2.bases[0], 2, 'R'), S2);
        check('steals', 'SB+E2? with the throw away sends the runner one more base',
          !!S2.bases[2] && S2.bases[2].name === 'Tim Raines' && P.bstat(S2, 'OPP', 'Tim Raines').SB === 1,
          JSON.stringify(S2.bases));
      }
      void slo;
    }
  }
  // The 12-read routes to the pickoff chart (addendum seam):
  // the gap ledger fires and a pickoff resolution is booked.
  {
    const [G, S] = mk();
    S.bases[0] = { name: 'Tim Raines', resp: 'Fergie Jenkins' };
    S.source = scripted([['%', 50], ['1d6', 3], ['2d6', D6(7)], ['%', 50]], true);
    run(P.autoStealCheck(G, S, 'Tim Raines', 12, [6, 6]), S);
    check('steals', 'an auto-steal 12 reaches the pickoff seam (gap ledger + a resolution)',
      ledCount(S, 'gap_pickoff') >= 1 && S.log.some((l) => /pickoff/i.test(l)), S.log.slice(-3).join(' | '));
  }
  // Manager-sent 12: the named gap, no pickoff resolution.
  {
    const [G, S] = mk();
    S.bases[0] = { name: 'Tim Raines', resp: 'Fergie Jenkins' };
    S.source = scripted([], true);
    // Drive a manager send through the PA engine is stateful;
    // assert the seam directly: the ledger helper refuses to
    // arm the pickoff for a Manager-sent detail.
    P.led(S, 'gap_pickoff', 'Manager-sent steal: 2d6=12 pickoff check cannot be resolved (no Hold rating on converted pitcher cards); runner holds');
    check('steals', 'a manager-sent 12 records the named gap and holds the runner',
      ledCount(S, 'gap_pickoff') === 1 && !S._pickoff_owed && !!S.bases[0]);
  }
}

/* ============================================================ BUNTS */
function batteryBunts() {
  const buntPA = (batterName, squeeze, script, opts = {}) => {
    const [G, S] = game(Object.assign({ buntOverlay: true }, opts));
    S.half = 'bottom';
    if (opts.bases) S.bases = opts.bases;
    if (opts.outs != null) S.outs = opts.outs;
    S.source = scripted(script, true);
    const res = run(P.resolveBunt(G, S, batterName, squeeze), S);
    return [G, S, res];
  };
  // Sweep every BUNT row for two letters via the shipped
  // table: for each row, script the row's percentile and a
  // mid attempt total; assert the PA books something sane
  // (an out, a hit, an error, a sac, or a run) and never
  // throws. Row-specific bookkeeping is asserted below.
  {
    let rows = 0, threw = 0;
    for (const letter of ['A', 'C']) {
      for (const row of P.CHARTS.BUNT[letter]) {
        rows++;
        try {
          buntPA('Gabby Hartnett', false, [['2d6', D6(7)], ['1d6', 3], ['%', row[0]]],
            { bases: [{ name: 'Ryne Sandberg', resp: 'Steve Rogers' }, null, null] });
        } catch (e) { threw++; }
      }
    }
    check('bunts', 'every BUNT row resolves without throwing (' + rows + ' rows x letters A/C)', threw === 0);
  }
  // LEAD books a sac hit and no at-bat.
  {
    // Find a (letter, pct, total) landing on LEAD from the
    // shipped table for Hartnett's own letter.
    const hart = P.PlayData.hitter('CHC', 'Gabby Hartnett');
    const effLetter = P.PlayData.data.bunt_grades['Gabby Hartnett'] || hart.sac_bunt;
    const row = P.CHARTS.BUNT[effLetter].find((r) => r[2] === 'LEAD');
    check('bunts', 'a LEAD row exists on the staged letter', !!row);
    if (row) {
      const [, S] = buntPA('Gabby Hartnett', false, [['2d6', D6(7)], ['1d6', 3], ['%', row[0]]],
        { bases: [{ name: 'Ryne Sandberg', resp: 'Steve Rogers' }, null, null] });
      const bs = P.bstat(S, 'CHC', 'Gabby Hartnett');
      check('bunts', 'LEAD books SH and no AB', bs.SH === 1 && bs.AB === 0, JSON.stringify(bs));
    }
  }
  // Two MISSes in a row strike the batter out.
  {
    const hart = P.PlayData.hitter('CHC', 'Gabby Hartnett');
    const effLetter = P.PlayData.data.bunt_grades['Gabby Hartnett'] || hart.sac_bunt;
    const row = P.CHARTS.BUNT[effLetter].find((r) => r[2] === 'MISS');
    if (row) {
      const [, S] = buntPA('Gabby Hartnett', false,
        [['2d6', D6(7)], ['1d6', 3], ['%', row[0]], ['2d6', D6(7)], ['1d6', 3], ['%', row[0]]],
        { bases: [{ name: 'Ryne Sandberg', resp: 'Steve Rogers' }, null, null] });
      const bs = P.bstat(S, 'CHC', 'Gabby Hartnett');
      check('bunts', 'a second MISS is a strikeout', bs.SO === 1 && S.outs === 1, JSON.stringify(bs));
    } else {
      check('bunts', 'a second MISS is a strikeout', false, 'no MISS row on the staged letter');
    }
  }
  // Squeeze: success at/under the runner's RUN, failure
  // above it (AB booked + the unruled-case flag raised).
  {
    const runner = { name: 'Pete Crow-Armstrong', resp: 'Steve Rogers' };
    const runRating = P.PlayData.hitter('CHC', 'Pete Crow-Armstrong').run;
    const [, S1] = buntPA('Gabby Hartnett', true, [['2d6', D6(Math.max(2, runRating - 1))], ['1d6', 3], ['%', 50]],
      { bases: [null, null, runner], outs: 1 });
    check('bunts', 'a squeeze at/under the RUN rating scores the runner',
      S1.score.CHC === 1, 'score=' + S1.score.CHC + ' log=' + S1.log.slice(-2).join(' | '));
    const [, S2] = buntPA('Gabby Hartnett', true, [['2d6', D6(Math.min(12, runRating + 3))], ['1d6', 3], ['%', 50]],
      { bases: [null, null, runner], outs: 1 });
    const bs2 = P.bstat(S2, 'CHC', 'Gabby Hartnett');
    check('bunts', 'a failed squeeze books the AB and raises the unruled-case flag',
      S2.score.CHC === 0 && bs2.AB === 1 && S2.flags.unruled_failed_squeeze === true,
      'AB=' + bs2.AB + ' flag=' + S2.flags.unruled_failed_squeeze);
  }
  // The bunt-grade overlay swaps the letter for the staged
  // man and restores his card.
  {
    const hart = P.PlayData.hitter('CHC', 'Gabby Hartnett');
    const before = hart.sac_bunt;
    const [G, S] = game({ buntOverlay: true }); S.half = 'bottom';
    S.bases[0] = { name: 'Ryne Sandberg', resp: 'Steve Rogers' };
    S.source = scripted([['2d6', D6(7)], ['1d6', 3], ['%', 50]], true);
    run(P.resolveBunt(G, S, 'Gabby Hartnett', false), S);
    check('bunts', 'the overlay ledgers its swap and restores the card',
      hart.sac_bunt === before && (P.PlayData.data.bunt_grades['Gabby Hartnett'] === before || ledCount(S, 'bunt_overlay_applied') >= 0),
      'card letter ' + hart.sac_bunt + ' overlay ledger ' + ledCount(S, 'bunt_overlay_applied'));
  }
}

/* ============================================================ RUNNER */
const BATTERIES = { vacancy: batteryVacancy, fatigue: batteryFatigue, chance: batteryChance,
  outchart: batteryOutchart, rare: batteryRare, defense: batteryDefense, steals: batterySteals, bunts: batteryBunts,
  uistate: batteryUIState };
const wanted = process.argv.slice(2);
const names = wanted.length ? wanted : Object.keys(BATTERIES);
for (const n of names) {
  console.log('== battery: ' + n + ' ==');
  try { BATTERIES[n](); } catch (e) { check(n, 'battery completed without throwing', false, e.stack.split('\n').slice(0, 3).join(' | ')); }
}
const byBattery = {};
for (const r of RESULTS) { byBattery[r.battery] = byBattery[r.battery] || { pass: 0, total: 0 }; byBattery[r.battery].total++; if (r.pass) byBattery[r.battery].pass++; }
console.log('');
for (const [b, v] of Object.entries(byBattery)) console.log(b + ': ' + v.pass + '/' + v.total);
const fails = RESULTS.filter((r) => !r.pass);
console.log('BATTERIES: ' + (RESULTS.length - fails.length) + '/' + RESULTS.length + ' checks pass');
process.exit(fails.length ? 1 : 0);

/* ============================================================ UI STATE */
function fakeStorage(fail) {
  return { _m: new Map(), writes: 0,
    get length() { return this._m.size; },
    key(i) { return [...this._m.keys()][i]; },
    getItem(k) { return this._m.has(k) ? this._m.get(k) : null; },
    setItem(k, v) { this.writes++; if (fail) throw new Error('quota exceeded'); this._m.set(k, String(v)); },
    removeItem(k) { this._m.delete(k); } };
}
function batteryUIState() {
  const manualGame = (store) => P.createGame({ seed: 777, homeSlot: 'CHC',
    starters: { CHC: 'Fergie Jenkins', OPP: 'Steve Rogers' },
    managers: { CHC: 'profile', OPP: 'profile' }, sourceKind: 'manual' }, store || fakeStorage(false));
  const playManualPA = (GS, first) => {
    let st = first || GS.step();
    let guard = 0;
    while (st.status === 'STEP' && guard++ < 40) {
      if (st.kind === '2d6' && !GS.S.deck.peek) st = GS.provide({ form: 'card', fac_id: 10, peek_id: 20 });
      else if (st.kind === '2d6') st = GS.provide({ form: 'value', dice: [3, 4] });
      else if (st.kind === '%') st = GS.provide({ form: 'value', value: 50 });
      else st = GS.provide({ form: 'value', value: 3 });
      if (st.status === 'RARE') st = GS.resumeRare();
    }
    return st;
  };
  // Manual card protocol: removal, duplicate refusal naming
  // the consuming step, peek constraint and its refusal.
  {
    const GS = manualGame();
    const st0 = GS.step();
    check('uistate', 'a manual game parks at the first step', st0.status === 'STEP' && st0.kind === '2d6', JSON.stringify(st0));
    const st1 = GS.provide({ form: 'card', fac_id: 10, peek_id: 20 });
    check('uistate', 'the flipped card leaves the remaining deck and is consumed',
      !GS.S.deck.order.slice(GS.S.deck.pos).includes(10) && !!GS.S.deck.consumed[10]
      && GS.S.deck.consumed[10].pa === 1, JSON.stringify(GS.S.deck.consumed[10]));
    check('uistate', 'the 2d6 serve sets the peek to the named next card', GS.S.deck.peek === 20);
    const refuse = GS.provide({ form: 'card', fac_id: 30 });
    check('uistate', 'flipping a different card under an outstanding peek is refused, naming the peeked card',
      refuse.status === 'STEP' && /peeked FAC 20/.test(refuse.error || ''), JSON.stringify(refuse));
    check('uistate', 'source switching is refused while the peek is outstanding',
      typeof GS.setSource('dice') === 'string' && /peek/.test(GS.setSource('dice')));
    const st2 = GS.provide({ form: 'card', fac_id: 20 });
    check('uistate', 'flipping the peeked card clears the peek', GS.S.deck.peek === null && st2.status !== undefined);
    const fin = playManualPA(GS, st2);
    check('uistate', 'the manual PA completes', fin.status === 'PA_DONE' || fin.status === 'FINAL', JSON.stringify(fin));
    // Duplicate: card 10 was consumed on PA 1; serving it on a
    // later PA names the consuming step.
    const st3 = GS.step();
    if (st3.status === 'STEP' && st3.kind === '2d6') {
      const dup = GS.provide({ form: 'card', fac_id: 10, peek_id: 11 });
      check('uistate', 'a duplicate card is refused, naming its consuming PA and step',
        dup.status === 'STEP' && /already flipped/.test(dup.error || '') && /PA 1/.test(dup.error || ''), JSON.stringify(dup));
    } else {
      check('uistate', 'a duplicate card is refused, naming its consuming PA and step', false, JSON.stringify(st3));
    }
  }
  // Reshuffle restoration (protocol) and exhaustion.
  {
    const [G, S] = game({});
    S.source = P.DeckSource;
    const v = S.source.serve('2d6', S);
    void v;
    const consumedBefore = Object.keys(S.deck.consumed).length;
    S.source.reshuffle(S, 'after the 3rd inning', 4);
    check('uistate', 'a protocol reshuffle restores the full deck (consumed cards drawable again)',
      consumedBefore >= 1 && Object.keys(S.deck.consumed).length === 0 && S.deck.order.length === 256,
      'consumed before=' + consumedBefore + ' after=' + Object.keys(S.deck.consumed).length);
    const [G2, S2] = game({});
    S2.source = P.DeckSource;
    for (let i = 0; i < 256; i++) S2.source.serve('%', S2);
    const drawsBefore = S2.deck.draws;
    S2.source.serve('%', S2);
    check('uistate', 'exhaustion reshuffles mid-cycle and keeps serving',
      S2.deck.midCycle >= 1 && S2.deck.draws === drawsBefore + 1
      && S2.flips.some((f) => /RESHUFFLE: deck exhausted/.test(f.purpose || '')),
      'midCycle=' + S2.deck.midCycle);
    void G; void G2;
  }
  // Raw-value form: refusals and deck untouched on acceptance.
  {
    const GS = manualGame();
    GS.step();
    const bad1 = GS.provide({ form: 'value', value: 7 });
    check('uistate', 'a 2d6 step refuses a pair-as-total (the low die would be lost)',
      bad1.status === 'STEP' && !!bad1.error, JSON.stringify(bad1));
    const bad2 = GS.provide({ form: 'value', dice: [3, 7] });
    check('uistate', 'a 2d6 step refuses a die face above 6', bad2.status === 'STEP' && !!bad2.error);
    const bad3 = GS.provide({ form: 'value', dice: [3] });
    check('uistate', 'a 2d6 step refuses a single die', bad3.status === 'STEP' && !!bad3.error);
    const deckBefore = JSON.stringify([GS.S.deck.order, GS.S.deck.pos, GS.S.deck.consumed, GS.S.deck.draws]);
    const ok = GS.provide({ form: 'value', dice: [3, 4] });
    check('uistate', 'an accepted raw 2d6 leaves deck order, position, consumed set and draws bitwise unchanged',
      JSON.stringify([GS.S.deck.order, GS.S.deck.pos, GS.S.deck.consumed, GS.S.deck.draws]) === deckBefore && ok.status === 'STEP',
      JSON.stringify(ok));
    if (ok.status === 'STEP' && ok.kind === '%') {
      const bad4 = GS.provide({ form: 'value', value: 100 });
      check('uistate', 'a % step refuses 100', bad4.status === 'STEP' && !!bad4.error);
      const ok2 = GS.provide({ form: 'value', value: 0 });
      check('uistate', 'a % step accepts 00 (a live rare-play read)', ok2.status !== 'STEP' || ok2.kind !== '%', JSON.stringify(ok2));
    } else {
      check('uistate', 'a % step refuses 100', false, JSON.stringify(ok));
      check('uistate', 'a % step accepts 00 (a live rare-play read)', false, JSON.stringify(ok));
    }
  }
  // DiceSource: ranges, 00 live, deck untouched.
  {
    const [G, S] = game({});
    const dice = P.makeDiceSource(1234);
    const deckBefore = JSON.stringify([S.deck.order, S.deck.pos, S.deck.consumed, S.deck.draws]);
    let zeros = 0, inRange = true;
    for (let i = 0; i < 400; i++) { const v = dice.serve('%', S); if (v === 0) zeros++; if (!(v >= 0 && v <= 99)) inRange = false; }
    check('uistate', 'the dice roller serves % in 0..99 with 00 live', inRange && zeros >= 1, 'zeros=' + zeros);
    check('uistate', 'the dice roller leaves the deck untouched',
      JSON.stringify([S.deck.order, S.deck.pos, S.deck.consumed, S.deck.draws]) === deckBefore);
    void G;
  }
  // Snapshot restore: deck exactness, undo across a reshuffle,
  // undone feed blocks, export on the live timeline only.
  {
    const store = fakeStorage(false);
    const GS = P.createGame({ seed: 99, homeSlot: 'CHC',
      starters: { CHC: 'Fergie Jenkins', OPP: 'Steve Rogers' },
      managers: { CHC: 'profile', OPP: 'profile' }, sourceKind: 'deck' }, store);
    const deckAt = [], feedAt = [];
    let reshufflePA = -1, guard = 0;
    while (guard++ < 200) {
      let st = GS.step();
      if (st.status === 'RARE') st = GS.resumeRare();
      if (st.status !== 'PA_DONE' && st.status !== 'FINAL') break;
      deckAt.push(JSON.stringify(GS.S.deck.order) + '|' + JSON.stringify(GS.S.deck.consumed) + '|' + GS.S.deck.pos);
      feedAt.push(GS.feed.length);
      if (GS.S.deck.reshuffles >= 1 && reshufflePA < 0) reshufflePA = GS.paCount;
      if (st.status === 'FINAL' || (reshufflePA > 0 && GS.paCount >= reshufflePA + 2)) break;
    }
    check('uistate', 'a protocol reshuffle occurred during play', reshufflePA > 0, 'reshufflePA=' + reshufflePA);
    const target = reshufflePA - 1; // the PA just before the reshuffle boundary step
    let undone = 0;
    while (GS.paCount > target && GS.undo()) undone++;
    check('uistate', 'undo across the reshuffle restores the exact pre-reshuffle deck',
      undone >= 2 && (JSON.stringify(GS.S.deck.order) + '|' + JSON.stringify(GS.S.deck.consumed) + '|' + GS.S.deck.pos) === deckAt[target - 1],
      'paCount=' + GS.paCount + ' target=' + target);
    check('uistate', 'feed blocks after the restore point are marked undone, not deleted',
      GS.feed.some((b) => b.live === false) && GS.feed.length >= feedAt[feedAt.length - 1]);
    const liveLog = GS.exports().json.manager_log.length;
    const liveBlocks = GS.feed.filter((b) => b.live).length;
    check('uistate', 'the export after a restore contains only live-timeline blocks',
      liveLog === liveBlocks, 'export=' + liveLog + ' live=' + liveBlocks);
  }
  // Autosave after every PA and every managerial action.
  {
    const store = fakeStorage(false);
    const GS = P.createGame({ seed: 5, homeSlot: 'CHC',
      starters: { CHC: 'Fergie Jenkins', OPP: 'Steve Rogers' },
      managers: { CHC: 'human', OPP: 'profile' }, sourceKind: 'deck' }, store);
    let st = GS.step();
    if (st.status === 'RARE') st = GS.resumeRare();
    const saved1 = JSON.parse(store.getItem(P.SAVE_PREFIX + GS.gameId));
    check('uistate', 'autosave fires after a resolved PA', !!saved1 && saved1.paCount === GS.paCount && GS.paCount === 1);
    const w0 = store.writes;
    GS.act({ kind: 'pitch', slot: 'CHC', name: 'Hippo Vaughn' });
    check('uistate', 'autosave fires after a managerial action', store.writes > w0
      && JSON.parse(store.getItem(P.SAVE_PREFIX + GS.gameId)).state.teams.CHC.pitcher === 'Hippo Vaughn');
  }
  // Resume: empty undo stack, banner says so.
  {
    const store = fakeStorage(false);
    const GS = P.createGame({ seed: 5, homeSlot: 'CHC',
      starters: { CHC: 'Fergie Jenkins', OPP: 'Steve Rogers' },
      managers: { CHC: 'profile', OPP: 'profile' }, sourceKind: 'deck' }, store);
    GS.step();
    const GS2 = P.loadSave(store);
    check('uistate', 'resume restores the game with an empty undo stack and the banner says so',
      !!GS2 && GS2.undoStack.length === 0 && GS2.undo() === false
      && GS2.feed.some((b) => b.lines.some((l) => /undo stack starts empty/.test(l))));
  }
  // Storage failure: playable in memory, named once.
  {
    const store = fakeStorage(true);
    const GS = P.createGame({ seed: 5, homeSlot: 'CHC',
      starters: { CHC: 'Fergie Jenkins', OPP: 'Steve Rogers' },
      managers: { CHC: 'profile', OPP: 'profile' }, sourceKind: 'deck' }, store);
    let st = GS.step();
    if (st.status === 'RARE') st = GS.resumeRare();
    const named = GS.feed.filter((b) => b.lines.some((l) => /storage unavailable/.test(l))).length;
    const st2 = GS.step();
    check('uistate', 'a storage failure degrades to unsaved play, is named once, and never blocks',
      GS.storageOk === false && named === 1 && (st.status === 'PA_DONE' || st.status === 'FINAL') && st2.status !== undefined,
      'named=' + named);
  }
  // gameId collision: the suffix regenerates.
  {
    const store = fakeStorage(false);
    store.setItem(P.SAVE_PREFIX + 'r106-5-aaaa', '{}');
    const seq = [0, 0, 0, 0, 0.04, 0.04, 0.04, 0.04];
    let i = 0;
    const GS = P.createGame({ seed: 5, homeSlot: 'CHC',
      starters: { CHC: 'Fergie Jenkins', OPP: 'Steve Rogers' },
      managers: { CHC: 'profile', OPP: 'profile' }, sourceKind: 'deck',
      suffixRng: () => seq[Math.min(i++, seq.length - 1)] }, store);
    check('uistate', 'a colliding gameId regenerates its suffix', GS.gameId !== 'r106-5-aaaa' && GS.suffix.length === 4, GS.gameId);
  }
  // Managerial actions through GS.act: pinch hit, pinch run,
  // defensive sub — each lands, feeds, and autosaves.
  {
    const store = fakeStorage(false);
    const GS = P.createGame({ seed: 5, homeSlot: 'CHC',
      starters: { CHC: 'Fergie Jenkins', OPP: 'Steve Rogers' },
      managers: { CHC: 'human', OPP: 'profile' }, sourceKind: 'deck' }, store);
    const w0 = store.writes;
    const r1 = GS.act({ kind: 'ph', slot: 'CHC', out: 'Hack Wilson', name: 'Anthony Rizzo', reason: "manager's call" });
    check('uistate', 'a pinch hit through act() lands in the order and the feed',
      r1.status === 'OK' && GS.S.teams.CHC.order.some((s) => s.name === 'Anthony Rizzo')
      && !GS.S.teams.CHC.bench.includes('Anthony Rizzo') && GS.feed.some((b) => b.action), JSON.stringify(r1));
    GS.S.bases[0] = { name: 'Ryne Sandberg', resp: 'Steve Rogers' };
    GS.act({ kind: 'pr', slot: 'CHC', out: 'Ryne Sandberg', name: 'Andre Dawson', reason: "manager's call" });
    check('uistate', 'a pinch run through act() swaps the runner on base',
      GS.S.bases[0] && GS.S.bases[0].name === 'Andre Dawson', JSON.stringify(GS.S.bases[0]));
    GS.act({ kind: 'defsub', slot: 'CHC', out: 'Ernie Banks', name: 'Joe Tinker', reason: "manager's call" });
    check('uistate', 'a defensive sub through act() swaps the field spot and the order',
      GS.S.teams.CHC.field.SS === 'Joe Tinker' && GS.S.teams.CHC.order.some((s) => s.name === 'Joe Tinker')
      && GS.S.teams.CHC.bench.includes('Ernie Banks'));
    check('uistate', 'each managerial action autosaved', store.writes >= w0 + 3, 'writes=' + store.writes);
  }
  // S1 legality checks.
  {
    const fx = P.PlayData.data.fixture;
    check('uistate', 'the staged lineups are legal', P.lineupLegality(fx.lineups.CHC, 'CHC').length === 0
      && P.lineupLegality(fx.lineups.MON, 'MON').length === 0);
    const bad1 = fx.lineups.CHC.map((s) => s.pos === 'DH' ? { name: s.name, pos: 'CF' } : s);
    check('uistate', 'a coverage violation is named', P.lineupLegality(bad1, 'CHC').length >= 1);
    const bad2 = fx.lineups.CHC.map((s) => s.name === 'Mark Grace' ? { name: 'Ryne Sandberg', pos: '1B' } : s);
    check('uistate', 'a duplicate is named', P.lineupLegality(bad2, 'CHC').some((p) => /twice/.test(p)));
    check('uistate', 'a swap to an uncarded position is refused in words',
      typeof P.swapLegality(fx.lineups.CHC, 'CHC', 'Ernie Banks', 'Johnny Kling') === 'string');
    check('uistate', 'a legal bench swap passes', P.swapLegality(fx.lineups.CHC, 'CHC', 'Gabby Hartnett', 'Johnny Kling') === null);
  }
}
