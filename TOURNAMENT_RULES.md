# Payoff Pitch Tournament 32 — Rules

Standing rules for every series in this tournament. Adopted 2026-10-22. Dated rulings are in [CHANGELOG.md](CHANGELOG.md). Where this file and an earlier series note disagree, this file governs.

Seeds are only in [TOURNAMENT_SEEDS.md](TOURNAMENT_SEEDS.md). The bracket map is [BRACKET.md](BRACKET.md). Rosters are [ROSTERS.md](ROSTERS.md). The game record is [tournament_results.json](tournament_results.json) and the files in [games/](games/). The shape of those files is [SCHEMA.md](SCHEMA.md).

## Rosters

Every club carries 26 men: a nine-man lineup, a five-man bench, a five-man rotation, and a seven-man bullpen, from Joe's all-time roster graphics. [ROSTERS.md](ROSTERS.md) is the roster record for all 32 clubs. Owner cards are on file for 25 clubs, including the Philadelphia Athletics. The note that a missing graphic left a roster TODO is closed. A club that has played and has no owner card still lists only the players who have appeared.

A pitcher carded in a swing or long role is a bullpen arm, not a starter. On the recorded Yankees and Marlins rosters those arms are Reynolds and Burnett. Section 2 does not bar them from pitching in relief.

The pre-tournament Yankees–Marlins exhibition used different lineups and pitcher pools. It is not the template. Tournament games use the rosters in [ROSTERS.md](ROSTERS.md).

## 1. Foundation

Play resolution, symbols, grades, and the manager's menu, as adopted for this tournament.

### Boards

Play resolution uses the APBA Basic Game boards, Version 23 (the 2012–2020 printing; Version 24 made no play-result changes). A cell's value is its latest documented change in the APBA Handbook Part 5 change catalogue, carried forward. Coverage as audited: 1,065 of 2,352 cells established (45.3 percent). Any cell the catalogue could not establish is model-filled: it resolves on the project's card plus log5 model. Nothing resolves on an unlabeled fallback.

### Master Game symbols

Master Game symbols are assigned to every card by the Master Game Instructions' old-card procedures and are permanent: steal allowance letters and steal success numbers, catcher Th and PB ratings, arm ratings, pitcher MF, and QR ratings. They are never recomputed between games. The symbol tables are not in this repository. The assignments that were written up covered the Yankees and Marlins cards.

### Pitcher grades during a game

Pitcher grades move during a game by three sources, applied together:

- The Master Game Instructions Pitcher Fatigue Table (the QR rows, which govern relievers).
- The Starting Pitcher Fatigue Rating Chart for starters.
- The SCBL 2021 amendments Rules 26 to 29. Rule 24 is the grade order. Rule 26 is starter advancement on consecutive scoreless innings, capped at straight A. Rule 27 is starter reductions. Rule 28a: six runs allowed drops a pitcher to grade D for the game. Rules 28b to 28d are reliever outs-based reductions, floor C. Rule 29 is the mid-inning entry grade bump against the first same-side batter.

The starter fatigue chart works as printed. At each start, two dice set the BFR adjustment, and BF Adjusted equals the pitcher's BF rating plus the adjustment. Once batters faced reach BF Adjusted and the starter has allowed his first earned run, the escalator applies: retire the next two, minus one grade; retire batters three and four, minus one more; any batter reaches, minus one; two consecutive batters reach, minus three; three consecutive reach, straight to D, which is the floor. Grade advancement under Rule 26 trumps the chart until the first earned run.

On model-filled cells only, a grade step moves a pitcher's log5 rates by the factors derived from the project's 24 pitcher cards. One step toward A: hits ×0.9283, walks ×0.9181, strikeouts ×1.1474. A step toward D applies the inverse of each. Home runs scale with hits. On board-resolved cells, the pitcher's live grade letter picks the board column. A longer calibration table is not in this repository. The factors in this section are the standing factors.

### Stealing

Stealing runs on the Master Game Instructions procedure. The Steal Success Number is adjusted by catcher Th and pitcher MF per the printed lists. MF is nullified when the first baseman is not holding the runner. The defense rolls.

The SCBL Rule 34 gate decides who may attempt a called steal. A and B rated runners may steal anytime. C and D rated runners may steal only with their team ahead by 1, tied, or behind by 1. The Base Stealing board is not in Handbook Part 5, so this procedure plus the Rule 34 gate is the standing substitute.

### Other SCBL amendments in force

- Rule 32. Sacrifice with runners on 1st and 3rd: the no-squeeze call holds the runner on 3rd.
- Rule 44. No pre-9th substitution without a rated replacement. After the 8th a losing team may substitute freely with the printed out-of-position ratings. The last catcher is protected except by injury.
- Rules 20c and 35. Hit-and-run steal handling.
- Rule 22. An intentional walk must be called before the dice.

### Manager decisions

The decision menu is full. Recorded bench styles are the Yankees old-school fireman and the Marlins modern matchup. Style picks which legal arm follows. It never decides whether the hook rules apply. Bench styles for the other clubs are not recorded.

Managers decide:

- Steal sends within the Rule 34 gate.
- The sacrifice, with the right players only. Never a named power bat. Bunt-apt means a non-power hitter whose real career home run rate is under 3 percent of plate appearances.
- The safety and suicide squeeze in their proper states.
- The hit-and-run.
- Defensive declarations before the pitch. Holding the runner is HO or NH, default HO. The infield is in (C) or back (D), default back. The infield in, with the runner held at 3rd, turns a throw home into a play at first.
- Pinch hitting in key spots: the tying or go-ahead run at the plate or on base, or to sustain a rally, when the bench bat is a clear upgrade.
- A defensive replacement for a clearly weaker fielder with a lead from the 8th.
- One pinch run per team per game, 8th inning or later, in a tie or a one-run game.

No intentional walk may be called once the hit-and-run or the squeeze has been declared. Pitching changes are governed by Sections 2, 4, and 5.

## APBA-derived rules and Payoff Pitch

From 2026-10-24 the tournament is simulated in Payoff Pitch. R1-01 was simulated in APBA and adopted. The four items below are the APBA stack these rules name. The written rule is in the section cited. R1-02's series record is the evidence for what that Payoff Pitch series actually stored: `resolutions` and `n41` are null, `final_grades` is empty, and the series provenance says Payoff Pitch has no letter grades and that those APBA counters do not exist in Payoff Pitch. Nothing in this section adds a rule.

### Version 23 boards

Section 1 states that play resolution uses the Version 23 boards, with model-filled cells where the catalogue has no cell. R1-01 carries a board-versus-model resolution count. R1-02's `resolutions` is null.

### Master Game symbols

Section 1 states that Master Game symbols are permanent and are not recomputed between games. The symbol tables are not in this repository. R1-02's empty `final_grades` matches its provenance: Payoff Pitch has no letter grades.

### Card-41 injury check

Section 9 states that the card-41 check is the only injury trigger. R1-02 records `n41` as null. Its provenance says that APBA counter does not exist in Payoff Pitch.

### SCBL Rule 34 steal gate

Section 1 states the gate: A and B runners anytime; C and D runners only within one run. The R1-02 record does not say whether that gate was applied. Rules 32, 44, 20c, 35, and 22 are written above as in force. Sections 1, 4, and 5 describe APBA letter-grade fatigue and the run and grade hooks. R1-02 stores `fatigue_end_states` and an empty `final_grades` object.

## 2. Starters never relieve

Starters start only. No starting pitcher appears in relief, in any game, in any round, for any reason. Each bullpen is that club's seven carded relievers. A pitcher carded in a swing or long role is a reliever, and this rule does not bar him from pitching in relief.

A reliever is lifted when he reaches 3 innings pitched in one appearance, unless he is the last available arm. The last available arm stays in and pitches under the fatigue rules, including after a run hook or a grade hook is armed, because a starter cannot relieve and no other reliever remains.

The recorded rotations and bullpens are in [ROSTERS.md](ROSTERS.md). On the Yankees and Marlins rosters the starters are Ford, Ruffing, Gomez, Guidry, and Pettitte, and Johnson, Alcantara, Willis, Beckett, and Fernandez. The relievers are Rivera, Gossage, Lyle, Robertson, Righetti, Stanton, and Reynolds, and Nen, Cishek, Ramos, Scott, Bender, Alfonseca, and Burnett.

## 3. Full rotation

Each club posts its rotation in order, all five starters, and starters take their turns in that order, one per game, cycling through the entire rotation before anyone starts a second time. On an all-time club, every pitcher in the rotation was an ace at some point, so every one of them gets the ball.

The cycle carries across series. A club's next starter is whoever follows its last starter. There are no short-rest starts and no skipping a turn because a game is an elimination game. A starter removed by injury misses only that game (Section 9) and keeps his next scheduled turn. The rotation does not reshuffle around him.

Posted orders are in [ROSTERS.md](ROSTERS.md). The recorded Yankees order is Ford, Ruffing, Gomez, Guidry, Pettitte. The recorded Marlins order is Johnson, Alcantara, Willis, Beckett, Fernandez.

## 4. Blowup hook

An elimination game is not left in one imploding pitcher's hands. A starter's hook arms at the earliest of: (a) 4 runs allowed; (b) a drop of two grades from his starting grade; (c) the fatigue chart's two-consecutive-batters-reach trigger after his BF Adjusted is reached.

Once the hook is armed, the starter is lifted at the end of the current inning at the latest, and immediately if the tying or go-ahead run comes to the plate. The hooks in this section and Section 5 override manager style and override any leash. No six-inning leash, matchup plan, or fireman custom keeps a hooked pitcher in the game. Manager style still governs which reliever follows a hooked starter.

## 5. Reliever hook

A reliever's hook arms at the earlier of 2 runs allowed in the appearance or a drop of two grades from his entry grade. Once armed, the timing is the same as Section 4: out at the end of the inning at the latest, and immediately if the tying or go-ahead run comes to the plate.

A reliever is lifted when he reaches 3 innings pitched in one appearance, unless he is the last available arm. The last available arm stays in and pitches under the fatigue rules, including after a run hook or a grade hook is armed, because a starter cannot relieve and no other reliever remains.

No reliever absorbs a game by default. The five-inning and six-inning relief appearances in the pre-tournament Yankees–Marlins pilot (Robertson in the Payoff Pitch games, Cishek in APBA Game 3) are what this section prevents.

## 6. Rider sanity

Board-cell riders apply only when the game state they describe actually exists. A rider that names a runner, a base, or a throw that is not in the play is ignored, and the cell's main result stands. The example is a slow-runner-out-at-third rider on a single with the bases empty. This rule exists because of the flagged artifact in Game 6 of the pre-tournament Yankees–Marlins pilot, where a rider was booked as an extra out with nobody on base. Riders are part of the printed result only in the situation the printer was describing.

## 7. Availability

Inside a series, a reliever who threw 2 or more innings in a game is capped at 3 outs in the next game, and a reliever who threw 3 or more innings is unavailable for the next game. Starters are governed by Section 3, not by workload.

Between series, every arm resets. No cap and no unavailability carries into the next series, so no elimination game is decided before it starts by a previous series' workload. The game record lists the availability state applied, arm by arm, in `caps_in` and `caps_out` when that series recorded them.

## 8. Announced pinch hitter

Once a pinch hitter is announced, he is the batter of record. Replacing him before he bats is legal only as a substitution, and it consumes both players as used for the game. In the pre-tournament pilot, Judge was announced and Munson then batted in his place at no cost. Under this rule that move costs both men.

## 9. Injuries

The card-41 check is the only injury trigger. On each plate appearance the dice pair is drawn and the batter's raw card first-column result is read before any blending. A 41 hurts a fielder, rotated through the defense by the draw. The pitcher is hurt only in the comebacker case. The plate appearance still resolves normally.

An injured player is out for the rest of that game only and returns at full strength the next game. This simplification overrides the SCBL J-table and any board text awarding a longer absence. No J ratings are assigned. Replacement follows Rule 44. If no rated replacement remains, an out-of-position fill-in plays with arm rating 21 and the manager log records the emergency.

## 10. Reporting

Every game record states the board-versus-model resolution split for an APBA game: board cells, model-filled cells, and unparsed established texts, out of total resolutions. It lists any model-filled cell that decided a play: a game-winning hit, a deciding error, a season-ending out. Those counts are the `resolutions` object. A Payoff Pitch game may store null there; see the section above.

The standing record of a played game is the summary object in `tournament_results.json` and the detail file in `games/`. Rules sources are named with the game, including the standing note that stealing runs on the Master Game Instructions procedure with the SCBL Rule 34 gate because the Base Stealing board is not in Handbook Part 5. Standalone write-ups of individual games are not in this repository. The JSON is the record that is here.

## Tournament format

The field, the seed numbers, and the six Joe-placed pins are in [TOURNAMENT_SEEDS.md](TOURNAMENT_SEEDS.md). That file is the only seed table.

- 32 clubs. Every matchup is a best of 7. A club is eliminated when it loses its second series.
- No byes. All 32 clubs play the opening round, seeded straight: 1 against 32, 2 against 31, and so on through 16 against 17.
- The bracket is the 32-team double-elimination map in [BRACKET.md](BRACKET.md). Winners stages are 16, 8, 4, 2, and 1 series, counting the opening round. Losers stages are 8, 8, 4, 4, 2, 2, 1, and 1 series, alternating survivor-only rounds and drop-in rounds, then the grand final. There are no crossovers.
- Pairings after the opening round are reseeded. At every stage the clubs entering that stage are reseeded by original tournament seed and paired highest against lowest, then second-highest against second-lowest. The highest surviving seed plays the lowest surviving seed. The losers bracket reseeds the same way. A drop-in losers stage pools the previous losers stage's winners with the corresponding winners stage's losers and reseeds that combined pool.
- The grand final is the winners-bracket champion (no series loss) against the losers-bracket champion (one series loss), best of 7. If the one-loss club wins it, one reset series decides the championship. The tournament is 62 series, or 63 if the reset is played.
- Every slot after the opening round exists from the start as an unfilled shell with its pool and its gate. A stage forms only when every series feeding it is complete. Both second-round stages form when all 16 opening series finish. Each later stage forms when its feeding stage finishes, and a losers drop-in stage also waits for the corresponding winners stage. Until a stage forms, its shell has no pairing and does not accept games.
- Home pattern, every series: 2-2-1-1-1, higher seed home first. Games 1 and 2 at the higher seed, games 3 and 4 at the lower seed, game 5 at the higher seed, game 6 at the lower seed, game 7 at the higher seed.

| Game | Home |
|---|---|
| 1, 2, 5, 7 | Higher seed |
| 3, 4, 6 | Lower seed |

A best of 7 turns the five-man rotation and returns to the first and second starters for games 6 and 7. The cycle carries across series, as in Section 3. Availability resets between series, as in Section 7.

## Pool-relative pitching grades

Pitcher letter grades are assigned by ranking the tournament pool. Starters and relievers are separate pools. The pool grades are frozen: the starter A line extends through number 35 (Gibson A). Those frozen grades are the grades of record. Fixed-band grades printed on the cards are kept as history. The frozen grade table is not in this repository. R1-02's `final_grades` object is empty, and that series' provenance says Payoff Pitch has no letter grades.

## Open questions

TODO for Joe:

- The Version 23 board reconstruction, the Master Game symbol tables, the longer grade-calibration table, and the frozen pool-grade table are not in this repository. Confirm whether any of them should be added, and whether pool-relative letter grades still apply in Payoff Pitch.
- Bench styles are recorded only for the Yankees and the Marlins.
- For Payoff Pitch games, confirm whether Version 23 boards, Master Game symbols, the card-41 injury check, Rule 34, Rules 32, 44, 20c, 35, and 22, and the letter-grade fatigue and hook rules still govern, or whether deck resolution replaces them. R1-02 stores null `resolutions`, null `n41`, and an empty `final_grades` object.
- Standalone write-ups of individual games are not in this repository. The JSON is the record.
- Unplayed opening shells R1-05 through R1-16 do not carry `round`. R1-01, R1-02, R1-03, and R1-04 set it to 1. Confirm whether the unplayed shells should say 1.
- The seed regression script and its output file are not in this repository. Confirm whether they should be added.
- San Francisco, Boston, Arizona, Tampa Bay, and Washington have played and have no owner roster card. Positions, managers, and anyone who has not appeared are still unrecorded on those clubs.
