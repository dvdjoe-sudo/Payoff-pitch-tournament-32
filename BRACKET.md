# APBA Top 32 Tournament: Bracket Map

Joe's direction (2026-10-23): "Go to 32 teams." The two merged
franchises split into their city teams (Athletics into Oakland
and Philadelphia; Washington into Washington and Montreal),
and the field is 32. On top of that structure, Joe's reseeding
rule (2026-10-23) governs every pairing beyond the opening
round: "winners should play next lowest rank winner left so
not a 1 vs 2 in 2nd round; 2nd round winners should reseed 1
vs lowest rank winner and so on; and same with loser bracket,
best rank loser vs lowest rank loser."

So there is no fixed chart of named feeders anymore. This file
is the stage map: it fixes the double-elimination structure
(how many stages, how many series in each, what pool feeds
each stage, and when a stage may form), and the writer
(tournament_results.py) pairs each stage's pool by reseeding
when the stage forms. The results file holds all 63 slots
from the start (62 series, plus the conditional reset).

Standing format rules, unchanged: every matchup is a
best-of-7 series; a team is eliminated when it loses its
second series; no byes; home pattern 2-2-1-1-1 with the
higher seed home first in every series (TOURNAMENT_RULES.md).

## The reseeding rule

At every stage of both brackets, the teams entering the stage
form a pool. The pool is reseeded by original tournament seed
and paired highest vs lowest, second-highest vs
second-lowest, and so on. The stage's series are numbered in
pairing order: the first series of a stage is the
highest-vs-lowest pairing.

- Winners bracket: the #1 seed plays the lowest-seeded
  surviving winner, never the #2 seed while any lower winner
  is alive. Every later winners stage reseeds the same way.
- Losers bracket: the best-ranked loser in the pool plays
  the lowest-ranked loser, and so on down the pool.
- A drop-in losers stage pools the previous losers stage's
  winners together with the corresponding winners stage's
  losers (the teams that just took their first loss), and
  the combined pool is reseeded as one.

## When a stage forms (the gating rule)

A stage's series form only when every series feeding that
stage is complete, and all of a stage's series form at once:

- Winners Round 2 and Losers Round 1 form when all 16
  opening series are complete.
- Each later winners stage forms when the previous winners
  stage is complete.
- Each survivor-only losers stage forms when the previous
  losers stage is complete.
- Each drop-in losers stage forms when the previous losers
  stage AND the corresponding winners stage are complete.
- The Grand Final forms when the Winners Bracket Final and
  the Losers Bracket Final are both complete.

Until its stage forms, a slot sits in the results file as an
unfilled shell carrying its reseeding basis (its pool and its
gate), and unfilled shells refuse game recording. Formation
is deterministic and idempotent: the same completed results
always produce the same pairings.

Endgame: the winners-bracket champion (undefeated) meets the
losers-bracket champion (one loss) in the Grand Final (F-01).
If the one-loss team wins it, the other team then has one
loss too, so the Reset (F-02) decides the championship; if
the undefeated team wins the final, F-02 is marked
not-needed. The champion is the last team not eliminated;
every other team finishes with exactly two series losses.
Unlike the old fixed chart, a team whose stage has not formed
yet waits for the feeding round to finish; that wait is the
price of reseeding, and it is the same for every team in the
pool.

## Round 1: Opening Round (fixed slots, already in the results file)

Seeded straight, 1v32 through 16v17, on the corrected
seed table (TOURNAMENT_SEEDS.md, Joe's reset of
2026-10-24 as amended by Joe the same day: six
Joe-placed pins, Yankees #1, Philadelphia #17 (moved
from #14 in the amendment), Oakland #22, Montreal #27,
Washington #31, Miami #32; the other 26 teams by Full
26 Index). Only R1-01 is
played: Yankees 4-0 over the Marlins, standing exactly as
recorded. The other 15 series are unplayed shells with
the pairings below. The Round 1 series played under the
old table (Giants over Expos, Red Sox over Philadelphia)
were voided by the same ruling and are archived in
superseded_r1_02_r1_03_seed_reset_2026-10-24.json.

| Slot | Pairing |
|---|---|
| R1-01 | #1 New York Yankees vs #32 Miami Marlins (played, Yankees 4-0) |
| R1-02 | #2 San Francisco Giants vs #31 Washington Nationals |
| R1-03 | #3 Boston Red Sox vs #30 Tampa Bay Rays |
| R1-04 | #4 Detroit Tigers vs #29 Arizona Diamondbacks |
| R1-05 | #5 St. Louis Cardinals vs #28 Colorado Rockies |
| R1-06 | #6 Chicago Cubs vs #27 Montreal Expos |
| R1-07 | #7 Atlanta Braves vs #26 San Diego Padres |
| R1-08 | #8 Pittsburgh Pirates vs #25 Toronto Blue Jays |
| R1-09 | #9 Cincinnati Reds vs #24 Texas Rangers |
| R1-10 | #10 Los Angeles Dodgers vs #23 Milwaukee Brewers |
| R1-11 | #11 Philadelphia Phillies vs #22 Oakland Athletics |
| R1-12 | #12 Minnesota Twins vs #21 New York Mets |
| R1-13 | #13 Cleveland Guardians vs #20 Los Angeles Angels |
| R1-14 | #14 Chicago White Sox vs #19 Seattle Mariners |
| R1-15 | #15 Baltimore Orioles vs #18 Kansas City Royals |
| R1-16 | #16 Houston Astros vs #17 Philadelphia Athletics |

## Winners Bracket Round 2 (8 series: W2-01 to W2-08)

Pool: the 16 opening-round winners. Gate: Round 1 complete.
Reseeded high vs low: the #1 seed meets the lowest-seeded
Round 1 winner, the #2 seed the second-lowest, and so on.
Forms at the same moment as Losers Round 1.

## Losers Bracket Round 1 (8 series: L1-01 to L1-08)

Pool: the 16 opening-round losers. Gate: Round 1 complete.
Reseeded high vs low: the best-ranked loser meets the
lowest-ranked loser. The loser of each series is eliminated
(second loss).

## Losers Bracket Round 2 (8 series: L2-01 to L2-08, drop-in)

Pool: the 8 Losers Round 1 winners plus the 8 Winners Round
2 losers dropping in with their first loss. Gate: Losers
Round 1 and Winners Round 2 both complete. The combined pool
is reseeded high vs low.

## Winners Bracket Round 3 (4 series: W3-01 to W3-04)

Pool: the 8 Winners Round 2 winners. Gate: Winners Round 2
complete. Reseeded high vs low.

## Losers Bracket Round 3 (4 series: L3-01 to L3-04)

Pool: the 8 Losers Round 2 winners. Gate: Losers Round 2
complete. Reseeded high vs low.

## Losers Bracket Round 4 (4 series: L4-01 to L4-04, drop-in)

Pool: the 4 Losers Round 3 winners plus the 4 Winners Round
3 losers dropping in. Gate: Losers Round 3 and Winners Round
3 both complete. The combined pool is reseeded high vs low.

## Winners Bracket Round 4 (2 series: W4-01, W4-02)

Pool: the 4 Winners Round 3 winners. Gate: Winners Round 3
complete. Reseeded high vs low.

## Losers Bracket Round 5 (2 series: L5-01, L5-02)

Pool: the 4 Losers Round 4 winners. Gate: Losers Round 4
complete. Reseeded high vs low.

## Losers Bracket Round 6 (2 series: L6-01, L6-02, drop-in)

Pool: the 2 Losers Round 5 winners plus the 2 Winners Round
4 losers dropping in. Gate: Losers Round 5 and Winners Round
4 both complete. The combined pool is reseeded high vs low.

## Winners Bracket Final (1 series: W5-01)

Pool: the 2 Winners Round 4 winners. Gate: Winners Round 4
complete. The winner is the winners-bracket champion
(undefeated); the loser drops into the Losers Bracket Final
with one loss.

## Losers Bracket Round 7 (1 series: L7-01)

Pool: the 2 Losers Round 6 winners. Gate: Losers Round 6
complete.

## Losers Bracket Final (1 series: L8-01, drop-in)

Pool: the Losers Round 7 winner plus the loser of the
Winners Bracket Final dropping in. Gate: Losers Round 7 and
the Winners Bracket Final both complete. The winner is the
losers-bracket champion (one loss); the loser is eliminated.

## Grand Final (1 series: F-01)

Pool: the winners-bracket champion (undefeated) vs the
losers-bracket champion (one loss). Gate: both bracket
finals complete.

## Grand Final, Reset Series (1 series: F-02, conditional)

The same two teams as the Grand Final, played only if the
one-loss finalist won F-01. If the undefeated finalist won
F-01, F-02 is marked not-needed and the tournament is over.

## Verification (2026-10-23, reseeding)

(Historical: this verification ran under the 2026-10-23
seed table, superseded 2026-10-24; the seed numbers in
its examples are the old table's. The reseeding mechanics
it proves are unchanged.)

The reseeding formation was fast-forwarded in scratch copies
of the live results file (conversion_work/verify_reseed.py),
starting from the real file with R1-01 and R1-02 complete.
After every completed series the script recomputed each
stage's pool independently and asserted the pairings match
the reseeded high-vs-low order exactly, and that no stage
held pairings before all its feeders completed:

- Favorites path (higher seed wins every series): champion
  (Yankees, undefeated) in exactly 62 series, F-02
  not-needed. Winners Round 2 opens NYY (#1) vs BAL (#16),
  the lowest-seeded Round 1 winner; the #2 seed draws #15.
- Mixed path (underdogs win opening series R1-03 through
  R1-16, favorites after that, and the one-loss finalist
  wins the Grand Final): the reset fills and a champion is
  decided in exactly 63 series. Winners Round 2 opens
  NYY (#1) vs PHA (#30), the lowest-seeded Round 1 winner;
  Losers Round 1 opens BOS (#3), the best-ranked loser, vs
  MIA (#32), the lowest-ranked loser.
- On both paths: every non-champion finishes eliminated at
  exactly two series losses, no team ever occupies two live
  series, drop-in stages pool survivors plus drop-ins
  correctly, and the played record (R1-01, R1-02, all 9 game
  records) is untouched. The migration that reverted W2-01
  and L1-01 to shells (conversion_work/migrate_reseed.py)
  proved the same with deep-equality diff guards on the
  games array, both played series records, and all 32 team
  records.
