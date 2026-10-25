# APBA All-Time Elimination Tournament: Standing Rules

Adopted 2026-10-22. These rules govern every APBA all-time elimination tournament game played with the project's card sets. They carry forward the rules stack proven in the Yankees vs Marlins all-time series (Games 1 to 6, Yankees won 4 games to 2), plus the five changes Cooper proposed after that series and Joe's full rotation rule, all adopted by Joe on 2026-10-22. Where this file and any earlier series note disagree, this file governs.

## Canonical Rosters

Tournament play uses the rosters on Joe's all-time roster graphics, which are canonical. Each club carries 26 men: a nine-man lineup, a five-man bench, a five-man rotation, and a seven-man bullpen.

**New York Yankees (manager Casey Stengel)**
- Lineup: 1 Jeter SS, 2 Judge RF, 3 Ruth DH, 4 Gehrig 1B, 5 Mantle LF, 6 DiMaggio CF, 7 A. Rodriguez 3B, 8 Berra C, 9 Randolph 2B.
- Bench: Munson (C2), Lazzeri (IF/BAT), Mattingly (1B/BAT), B. Williams (OF), R. Jackson (OF/BAT).
- Rotation, in posted order: Ford, Ruffing, Gomez, Guidry, Pettitte.
- Bullpen: Rivera (CL), Gossage (FIRE), Lyle (LH FIRE), Robertson (RH SET), Righetti (LATE/MULTI), Stanton (LH SPEC), Reynolds (LONG/SWING).

**Miami Marlins (manager Jack McKeon)**
- Lineup: 1 Castillo 2B, 2 Yelich CF, 3 Sheffield DH, 4 Stanton RF, 5 Cabrera 3B, 6 Ramirez SS, 7 Floyd LF, 8 Conine 1B, 9 Realmuto C.
- Bench: C. Johnson (C2), Lopez (UTIL), Uggla (INF/POWER), Ozuna (OF4), Lee (1B/POWER).
- Rotation, in posted order: Johnson, Alcantara, Willis, Beckett, Fernandez.
- Bullpen: Nen (CL), Cishek (SU), Ramos (SU), Scott (LH), Bender (MR), Alfonseca (MR), Burnett (LR/EMER SP).

Reynolds and Burnett are bullpen arms in the swing and long roles, not starters; Section 2 does not bar them from relieving.

Note: the Yankees vs Marlins exhibition series of October 2026 was played with different lineups and pitcher pools, transcribed before this check against the graphics, and it is not the template for tournament play. Tournament games use the lineups, benches, rotations, and bullpens above.

## 1. Foundation

- Play resolution uses the APBA Basic Game boards, Version 23 (the 2012-2020 printing; Version 24 made no play-result changes), reconstructed from the APBA Handbook Part 5 change catalogue: a cell's value is its latest documented change carried forward. The reconstruction and audit are the standing record in BOARDS_V23.md and boards_v23.json in this folder. Coverage as audited: 1,065 of 2,352 cells established (45.3 percent). Any cell the catalogue could not establish is model-filled: it resolves on the project's card plus log5 model, and every model-filled cell is listed in BOARDS_V23.md. Nothing resolves on an unlabeled fallback.
- Master Game symbols are assigned to every card by the Master Game Instructions' old-card procedures and are permanent: steal allowance letters and steal success numbers, catcher Th and PB ratings, arm ratings, pitcher MF, and QR ratings. The assignments for all 52 Yankees and Marlins cards are in MASTER_SYMBOLS.md and MASTER_SYMBOLS.json. They are never recomputed between games.
- Pitcher grades move during a game by three sources, applied together: the Master Game Instructions Pitcher Fatigue Table (the QR rows, which govern relievers), the Starting Pitcher Fatigue Rating Chart for starters, and the SCBL 2021 amendments Rules 26 to 29 (Rule 24 grade order; Rule 26 starter advancement on consecutive scoreless innings, capped at straight A; Rule 27 starter reductions; Rule 28a six runs allowed drops a pitcher to grade D for the game; Rules 28b to 28d reliever outs-based reductions, floor C; Rule 29 mid-inning entry grade bump against the first same-side batter).
- The starter fatigue chart works as printed: at each start, two dice set the BFR adjustment, and BF Adjusted equals the pitcher's BF rating plus the adjustment. Once batters faced reach BF Adjusted and the starter has allowed his first earned run, the escalator applies: retire the next two, minus one grade; retire batters three and four, minus one more; any batter reaches, minus one; two consecutive batters reach, minus three; three consecutive reach, straight to D, which is the floor. Grade advancement under Rule 26 trumps the chart until the first earned run.
- On model-filled cells only, a grade step moves a pitcher's log5 rates by the calibrated factors derived from the project's 24 pitcher cards (one step toward A: hits x0.9283, walks x0.9181, strikeouts x1.1474; a step toward D applies the inverse of each; home runs scale with hits). On board-resolved cells, the pitcher's live grade letter picks the board column instead. The full calibration table is in SERIES_SO_FAR.md.
- Stealing runs on the Master Game Instructions procedure (Steal Success Number adjusted by catcher Th and pitcher MF per the printed lists; MF nullified when the first baseman is not holding the runner; the defense rolls) with the SCBL Rule 34 gate on who may attempt a called steal: A and B rated runners anytime; C and D rated runners only with their team ahead by 1, tied, or behind by 1. The Base Stealing board itself is not in Handbook Part 5, so this procedure plus the Rule 34 gate is the standing substitute, and game reports say so.
- SCBL amendments in force include Rule 32 (sacrifice with runners on 1st and 3rd: the no-squeeze call holds the runner on 3rd), Rule 44 (substitution constraints: no pre-9th substitution without a rated replacement; after the 8th a losing team may substitute freely with the printed out-of-position ratings; the last catcher is protected except by injury), Rules 20c and 35 (hit-and-run steal handling), and Rule 22 (an intentional walk must be called before the dice).
- The manager decision menu is full and belongs to the two bench styles (Yankees old-school fireman; Marlins modern matchup). Managers decide: steal sends within the Rule 34 gate; the sacrifice, with the right players only (never a named power bat; bunt-apt means a non-power hitter whose real career home run rate is under 3 percent of plate appearances); the safety and suicide squeeze in their proper states; the hit-and-run; defensive declarations before the pitch (holding the runner on, HO or NH, default HO; infield in, C, or back, D, default back, with the printed rule that the infield in and the runner holding at 3rd turns a throw home into a play at first); pinch hitting in key spots (tying or go-ahead run at the plate or on base, or to sustain a rally, when the bench bat is a clear upgrade); defensive replacements for a clearly weaker fielder with a lead from the 8th; and one pinch run per team per game, 8th inning or later in a tie or one-run game. No intentional walk may be called once the hit-and-run or the squeeze has been declared. Pitching changes themselves are governed by Sections 2, 4, and 5 below; manager style picks which legal arm follows, never whether the hook rules apply.

## 2. Starters Never Relieve (Master Rule)

Starters start only. No starting pitcher ever appears in relief, in any game, in any round, for any reason. Bullpens are the seven carded relievers per team only. On the canonical rosters the starters are Ford, Ruffing, Gomez, Guidry, and Pettitte (Yankees) and Johnson, Alcantara, Willis, Beckett, and Fernandez (Marlins); the relievers are Rivera, Gossage, Lyle, Robertson, Righetti, Stanton, and Reynolds (Yankees) and Nen, Cishek, Ramos, Scott, Bender, Alfonseca, and Burnett (Marlins). Reynolds and Burnett carry swing and long roles in the bullpen; they are relievers, not starters, and this rule does not bar them from pitching in relief. If a game outlasts the seven relievers, the last reliever keeps pitching under the fatigue rules; no starter warms up.

## 3. Full Rotation Rule (Joe's Rule)

Each team posts its rotation in order, all five starters from the canonical rosters, and starters take their turns in that order, one per game, cycling through the entire rotation before anyone starts a second time. The reason is Joe's: on an all-time team, every pitcher in the rotation was an ace at some point, so every one of them gets the ball. The posted rotations are Yankees: Ford, Ruffing, Gomez, Guidry, Pettitte. Marlins: Johnson, Alcantara, Willis, Beckett, Fernandez. The cycle carries across tournament rounds: a team's next starter in the next round is whoever follows its last starter in the previous round. There are no short-rest starts and no skipping a turn because a game is an elimination game. A starter removed by injury misses only that game (Section 9) and keeps his next scheduled turn; the rotation does not reshuffle around him.

## 4. Blowup Hook (Both Benches, Uniform)

Elimination games cannot be left in one imploding pitcher's hands. A starter's hook arms at the earliest of: (a) 4 runs allowed; (b) a drop of two grades from his starting grade; (c) the fatigue chart's two-consecutive-batters-reach trigger after his BF Adjusted is reached. Once the hook is armed, the starter is lifted at the end of the current inning at the latest, and immediately if the tying or go-ahead run comes to the plate. The hooks in this section and Section 5 override manager style and override any leash rule: no six-inning leash, matchup plan, or fireman custom keeps a hooked pitcher in the game. Manager style still governs which reliever follows a hooked starter.

## 5. Reliever Hook and Long-Man Protection

A reliever's hook arms at the earlier of 2 runs allowed in the appearance or a drop of two grades from his entry grade. Once armed, the same timing rule as Section 4 applies: out at the end of the inning at the latest, and immediately if the tying or go-ahead run comes to the plate. Separately, lifting a reliever is mandatory at 3 innings pitched in one appearance unless he is the last available arm. No reliever absorbs a game by default: the five-inning and six-inning relief marathons from the Yankees vs Marlins series (Robertson in the Payoff Pitch games, Cishek in APBA Game 3) are exactly what this section exists to prevent. If the last available arm is hooked by runs or grades, he still pitches on under fatigue, because Section 2 leaves nobody else; the hook rules yield only to an empty bench of relievers.

## 6. Rider Sanity Rule

Board-cell riders apply only when the game state they describe actually exists. A rider that names a runner, a base, or a throw that is not in the play (for example, a slow-runner-out-at-third rider on a single with the bases empty) is ignored, and the cell's main result stands. This rule exists because of the flagged artifact in Game 6 of the Yankees vs Marlins series, where a rider was booked as an extra out with nobody on base. Riders are part of the printed result only in the situation the printer was describing.

## 7. Availability

Workload carryover applies within a tournament round exactly as it did in the Yankees vs Marlins series: a reliever who threw 2 or more innings in a game is capped at 3 outs in the next game, and a reliever who threw 3 or more innings is unavailable for the next game. Starters are governed by Section 3, not by workload. Between rounds, every arm resets in full: no cap and no unavailability carries into a new round, so no elimination game is decided before it starts by a previous round's marathon. Game reports list the availability state applied, arm by arm.

## 8. Announced Pinch Hitter

Once a pinch hitter is announced, he is the batter of record. Replacing him before he bats is legal only as a substitution, and it consumes both players as used for the game. This tightens the Game 6 sequence in the Yankees vs Marlins series, where Judge was announced and Munson then batted in his place at no cost. Under this rule that move costs both men.

## 9. Injuries

The card-41 check is the only injury trigger: on each plate appearance the dice pair is drawn and the batter's raw card first-column result read before any blending; a 41 hurts a fielder (rotated through the defense by the draw; the pitcher only in the comebacker case), and the plate appearance still resolves normally. An injured player is out for the rest of that game only and returns at full strength the next game. Joe's simplification overrides the SCBL J-table and any board text awarding a longer absence; no J ratings are assigned. Replacement follows Rule 44, and if no rated replacement remains, an out-of-position fill-in plays with arm rating 21 and the manager log records the emergency.

## 10. Reporting

Every game report states the board-vs-model resolution split for the game (board cells, model-filled cells, and unparsed established texts, out of total resolutions) and lists any model-filled cell that decided a play: a game-winning hit, a deciding error, a season-ending out. The standing record lives in this folder: BOARDS_V23.md and boards_v23.json (the board reconstruction and the model-filled cell list), MASTER_SYMBOLS.md and MASTER_SYMBOLS.json (the permanent symbol assignments), the per-game reports, and the series or tournament summary file. Rules sources are named in every report, including the standing note that stealing runs on the Master Game Instructions procedure with the SCBL Rule 34 gate because the Base Stealing board is not in Handbook Part 5.

## Tournament Format (Joe, 2026-10-22; 32 teams, 2026-10-23)

- Field: 32 all-time teams. The original 30 were seeded by the
  Legacy Lore Full 26 Index (TOURNAMENT_SEEDS.md). On 2026-10-23
  Joe directed "Go to 32 teams": the two merged franchises split
  into their city teams (Athletics into Oakland and Philadelphia;
  Washington into Washington and Montreal), so the field is the
  standard 32. Seeds 1-29 are unchanged, Oakland keeps the merged
  Athletics' #14, Washington keeps #22, the Philadelphia Athletics
  take #30 and the Montreal Expos #31 (that order is flippable on
  Joe's word), and the Marlins slide from #30 to #32.
- Seed reset and games reset (Joe, 2026-10-24): the seeding
  above is superseded by the corrected table in
  TOURNAMENT_SEEDS.md. Six slots are Joe-placed pins:
  Yankees #1, Philadelphia Athletics #14, Oakland Athletics
  #22, Montreal Expos #27, Washington Nationals #31, Miami
  Marlins #32; the other 26 teams slot strictly by their
  Full 26 Index. With the new seeds, Joe also reset all
  Round 1 games EXCEPT Yankees vs Marlins: the official
  posted results contain that series only. The voided
  Giants-Expos and Red Sox-Philadelphia series are
  archived in full in
  superseded_r1_02_r1_03_seed_reset_2026-10-24.json and
  count for nothing: those four clubs start the new
  Round 1 at 0-0 with their rotation cycles and Section 7
  availability states at their pre-series condition. The
  corrected seeds are the original seeds for all
  downstream reseeding.
- Amendment (Joe, 2026-10-24): Philadelphia's pin moved
  from #14 to #17, accepting the calibration estimate's
  #17-ish placement; the White Sox, Orioles, and Astros
  each rose one slot by index (to #14, #15, #16). Only
  the R1-14, R1-15, and R1-16 pairings changed; no played
  result was affected (R1-01 remains the only posted
  series).
- Every matchup is a BEST-OF-7 series. A team is eliminated when it
  loses its second series.
- NO BYES. All 32 teams play in the opening round, seeded straight:
  1v32, 2v31, 3v30, and so on through 16v17.
- The bracket is the standard 32-team double-elimination
  structure (BRACKET.md): winners bracket stages of 16, 8, 4,
  2, and 1 series counting the opening round; losers bracket
  stages of 8, 8, 4, 4, 2, 2, 1, and 1 series, alternating
  survivor-only rounds and drop-in rounds; then the grand
  final. The structure supersedes the earlier crossover and
  30-team language (Joe, 2026-10-23): there are no crossovers,
  because with 32 teams both sides stay even.
- Reseeding (Joe, 2026-10-23): pairings beyond the opening
  round are not fixed. At every stage of both brackets, the
  teams entering that stage are reseeded by their original
  tournament seed and paired highest vs lowest,
  second-highest vs second-lowest, and so on. Winners reseed
  every round, so the highest surviving seed always plays
  the lowest surviving seed (never 1 vs 2 in the second
  round while a lower winner is alive). The losers bracket
  reseeds the same way: the best-ranked loser in a pool plays
  the lowest-ranked loser. A drop-in losers stage pools the
  previous losers stage's winners with the corresponding
  winners stage's losers and reseeds the combined pool. This
  reseeding rule supersedes the fixed-chart pairing language
  that governed the original 32-team chart.
- Grand final: the winners-bracket champion (undefeated) meets the
  losers-bracket champion (one loss) in a best-of-7. If the one-loss
  team wins it, the undefeated team has only one loss, so one reset
  series decides the championship. Total: 62 series, 63 if the
  reset triggers.
- Bracket formation: every slot beyond the opening round exists in
  the results file from the start as an unfilled shell carrying
  its reseeding basis (its pool and its gate). A stage's series
  form only when every series feeding that stage is complete,
  never before: both second-round stages form when all 16 opening
  series finish; each later stage forms when its feeding stage
  finishes (plus the corresponding winners stage, for losers
  drop-in stages). Until its stage forms, a shell holds no
  pairing and refuses game recording, so a team whose stage has
  not formed yet waits for the feeding round to finish; that
  wait is the accepted price of reseeding.
- Home pattern (Joe, 2026-10-23): every series runs 2-2-1-1-1 with
  the higher seed home first: Games 1 and 2 at the higher seed,
  Games 3 and 4 at the lower seed, Game 5 at the higher seed,
  Game 6 at the lower seed, Game 7 at the higher seed. This
  supersedes the 2-3-2 home pattern used in the pilot exhibitions.
- Rotation rule fits the format: a best-of-7 turns the full five-man
  rotation and returns to the #1 and #2 starters for Games 6 and 7.
  The cycle carries across rounds as already ruled; availability
  resets between rounds (here: between series).

## Pool-Relative Pitching Grades (Joe, adopted 2026-10-22)

- Pitcher letter grades are assigned by ranking the tournament pool itself (starters and relievers in separate pools), not by the engine's fixed bands: see the "Pitching grades: POOL-RELATIVE" section of APBA_CARD_BUILDER_RULES.md and the frozen table in POOL_GRADES_PREVIEW.md. FROZEN 2026-10-23 on Joe's ruling (starter A line extended to #35: Gibson A): the frozen pool grades are the grades of record for tournament play, and the fixed-band grades printed on the cards are preserved in the team data as history.
