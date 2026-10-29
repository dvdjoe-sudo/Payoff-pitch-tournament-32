#!/usr/bin/env node
/* Distribution check (spec 11.3): 200 auto games on the
 * port, compared against the disclosed reference conditions
 * of PLAYTEST_VOLUME.md (60 best-of-7 series, 311 games):
 * Chicago 5.80 runs/game, Montreal 3.98, Chicago win share
 * 70%. Pass bands: +-0.50 runs, +-7 points of win share.
 *
 * Conditions set to the reference's own environment, read
 * off its evidence: the volume driver was the
 * promotion_series_game stack (Replay A's driver), which
 * never calls Williams' pre_pa (the volume book records zero
 * bench plate appearances in 622 team-games, which pre_pa
 * would have produced), carries no bunt-grade overlay and
 * no force clauses, and auto-resolves rares in bulk. The
 * port runs the same flags: prePa off, buntOverlay off,
 * clauses off. Staged lineups, DeckSource serves every
 * step, fresh seed per game, starters rotate by chair,
 * venues alternate (odd Wrigley, even Stade Olympique).
 * Disclosed difference, per the spec: the reference rested
 * relievers inside each series (Rest Chart); the port's
 * relievers are never rest-limited (fresher-bullpen end).
 *
 * Run: node scripts/distribution.mjs [games]
 * Exit 1 if any figure lands outside its band or any game
 * fails the Section 10 audit equalities. */
import { createRequire } from 'node:module';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
const P = require('../js/play.js');
P.PlayData.load(JSON.parse(fs.readFileSync(new URL('../data/playable_r106.json', import.meta.url), 'utf8')));

const N = Number(process.argv[2] || 200);
const fx = P.PlayData.data.fixture;
let chcRuns = 0, monRuns = 0, chcWins = 0, auditFails = 0, pas = 0, finals = 0;
const t0 = Date.now();
for (let i = 1; i <= N; i++) {
  const homeSlot = i % 2 === 1 ? 'CHC' : 'OPP';
  const chair = (i - 1) % 5;
  const starters = { CHC: fx.rotations.CHC[chair], OPP: fx.rotations.MON[chair] };
  const G = P.makeContext({ homeSlot, starters, buntOverlay: false, prePa: false, clauses: false, defenseNumbers: false });
  const S = P.newState(G, { seed: 20263000 + i, homeSlot, starters, traits: P.fixtureTraits() });
  S.source = P.DeckSource;
  const res = P.drive(P.runGame(G, S), S, () => undefined);
  if (res !== 'FINAL') { console.log('game ' + i + ': did not finish (' + res + ')'); auditFails++; continue; }
  finals++;
  chcRuns += S.score.CHC; monRuns += S.score.OPP;
  if (S.score.CHC > S.score.OPP) chcWins++;
  pas += S.flips.length;
  const bad = P.auditGame(G, S).filter((a) => !a.ok);
  if (bad.length) { auditFails++; console.log('game ' + i + ': audit failures ' + JSON.stringify(bad)); }
}
const chcAvg = chcRuns / N, monAvg = monRuns / N, winShare = chcWins / N;
console.log('games: ' + N + ' (' + finals + ' finished), ' + (Date.now() - t0) + 'ms');
console.log('Chicago runs/game: ' + chcAvg.toFixed(2) + '  (reference 5.80, band 5.30-6.30)');
console.log('Montreal runs/game: ' + monAvg.toFixed(2) + '  (reference 3.98, band 3.48-4.48)');
console.log('Chicago win share: ' + (winShare * 100).toFixed(1) + '%  (reference 70%, band 63-77%)');
console.log('audit failures: ' + auditFails);
const ok = finals === N && auditFails === 0
  && chcAvg >= 5.30 && chcAvg <= 6.30 && monAvg >= 3.48 && monAvg <= 4.48
  && winShare >= 0.63 && winShare <= 0.77;
console.log(ok ? 'DISTRIBUTION: PASS' : 'DISTRIBUTION: FAIL');
process.exit(ok ? 0 : 1);
