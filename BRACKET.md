# Payoff Pitch Tournament 32

The bracket map for the 32-club double-elimination tournament. Seeds are in [TOURNAMENT_SEEDS.md](TOURNAMENT_SEEDS.md). Series length, home pattern, and elimination are in [TOURNAMENT_RULES.md](TOURNAMENT_RULES.md). Dated rulings are in [CHANGELOG.md](CHANGELOG.md).

The field is 32 clubs. The Athletics are Oakland and Philadelphia. The Washington franchise is the Nationals and the Expos.

Pairings after the opening round are not a fixed chart. When a stage forms, its pool is reseeded by original tournament seed and paired highest against lowest, then second-highest against second-lowest, and so on. The highest surviving winner does not play the second survivor while a lower winner is still in that pool. The losers bracket uses the same pairing. A drop-in losers stage pools the previous losers stage's winners with the clubs that just took their first loss, and that combined pool is reseeded as one.

[`tournament_results.json`](tournament_results.json) holds all 63 slots from the start: 62 series, plus the conditional reset. A stage's pairings are written into those slots when the stage forms. Until then a slot is an unfilled shell. It carries its pool and its gate, it has no pairing, and it does not accept games. [`index.html`](index.html) draws the slots from that file.

Every series is a best of 7. A club is eliminated on its second series loss. There are no byes. The home pattern is 2-2-1-1-1 with the higher seed home first.

## Status

R1-01 and R1-02 are complete. R1-03 is in progress: Boston leads Tampa Bay 2-0. The other 13 opening series are scheduled and unplayed. Every later stage is waiting on its feeders.

| Slot | Pairing | Status |
|---|---|---|
| R1-01 | #1 New York Yankees vs #32 Miami Marlins | Played. Yankees 4-0. |
| R1-02 | #2 San Francisco Giants vs #31 Washington Nationals | Played. Giants 4-1. |
| R1-03 | #3 Boston Red Sox vs #30 Tampa Bay Rays | In progress. Boston leads 2-0. |
| R1-04 | #4 Detroit Tigers vs #29 Arizona Diamondbacks | Not played |
| R1-05 | #5 St. Louis Cardinals vs #28 Colorado Rockies | Not played |
| R1-06 | #6 Chicago Cubs vs #27 Montreal Expos | Not played |
| R1-07 | #7 Atlanta Braves vs #26 San Diego Padres | Not played |
| R1-08 | #8 Pittsburgh Pirates vs #25 Toronto Blue Jays | Not played |
| R1-09 | #9 Cincinnati Reds vs #24 Texas Rangers | Not played |
| R1-10 | #10 Los Angeles Dodgers vs #23 Milwaukee Brewers | Not played |
| R1-11 | #11 Philadelphia Phillies vs #22 Oakland Athletics | Not played |
| R1-12 | #12 Minnesota Twins vs #21 New York Mets | Not played |
| R1-13 | #13 Cleveland Guardians vs #20 Los Angeles Angels | Not played |
| R1-14 | #14 Chicago White Sox vs #19 Seattle Mariners | Not played |
| R1-15 | #15 Baltimore Orioles vs #18 Kansas City Royals | Not played |
| R1-16 | #16 Houston Astros vs #17 Philadelphia Athletics | Not played |

Opening round pairings are fixed: 1 against 32 through 16 against 17, on the seed table. The series of a later stage are numbered in pairing order. The first series of a stage is the highest-against-lowest pairing.

## When a stage forms

Every series in a stage forms at the same time, and only when every series that feeds the stage is complete. The same completed results always produce the same pairings.

| Stage | Series | Pool | Gate |
|---|---|---|---|
| Opening round | R1-01 to R1-16 | Fixed 1v32 through 16v17 | Formed |
| Winners round 2 | W2-01 to W2-08 | The 16 opening-round winners | Round 1 complete |
| Losers round 1 | L1-01 to L1-08 | The 16 opening-round losers | Round 1 complete |
| Losers round 2 (drop-in) | L2-01 to L2-08 | 8 Losers Round 1 winners plus 8 Winners Round 2 losers | Losers Round 1 and Winners Round 2 complete |
| Winners round 3 | W3-01 to W3-04 | The 8 Winners Round 2 winners | Winners Round 2 complete |
| Losers round 3 | L3-01 to L3-04 | The 8 Losers Round 2 winners | Losers Round 2 complete |
| Losers round 4 (drop-in) | L4-01 to L4-04 | 4 Losers Round 3 winners plus 4 Winners Round 3 losers | Losers Round 3 and Winners Round 3 complete |
| Winners round 4 | W4-01, W4-02 | The 4 Winners Round 3 winners | Winners Round 3 complete |
| Losers round 5 | L5-01, L5-02 | The 4 Losers Round 4 winners | Losers Round 4 complete |
| Losers round 6 (drop-in) | L6-01, L6-02 | 2 Losers Round 5 winners plus 2 Winners Round 4 losers | Losers Round 5 and Winners Round 4 complete |
| Winners bracket final | W5-01 | The 2 Winners Round 4 winners | Winners Round 4 complete |
| Losers round 7 | L7-01 | The 2 Losers Round 6 winners | Losers Round 6 complete |
| Losers bracket final (drop-in) | L8-01 | Losers Round 7 winner plus the Winners Bracket Final loser | Losers Round 7 and the Winners Bracket Final complete |
| Grand final | F-01 | Winners-bracket champion vs losers-bracket champion | Both bracket finals complete |
| Reset | F-02 | The same two clubs | Only if the one-loss finalist wins F-01 |

Winners Round 2 and Losers Round 1 form together, when the opening round is complete. The loser of a losers-bracket series is eliminated. The winner of the winners-bracket final is undefeated and goes to the grand final. The loser of that final drops into the losers-bracket final with one series loss.

A club whose stage has not formed waits until the feeding round is finished. That wait is the same for every club in the pool.

## Endgame

The winners-bracket champion (no series loss) meets the losers-bracket champion (one series loss) in F-01. If the one-loss club wins F-01, both clubs have one series loss and F-02 decides the championship. If the undefeated club wins F-01, F-02 is marked not needed and the tournament is over. The champion is the last club not eliminated. Every other club finishes with two series losses. The tournament is 62 series, or 63 if the reset is played.
