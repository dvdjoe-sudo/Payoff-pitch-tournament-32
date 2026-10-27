# Payoff Pitch full-game rule coverage

The only sources used here are the 146-page Payoff Pitch Baseball rulebook (©2021 Sideline Strategy Games, Joe Bryan) and the 1986 season card set. The Quick Results booklet and the separate two-page Ratings and Symbols sheet are not official and are not used. Page 39 of the rulebook is the Ratings and Symbols Addendum. It is part of the book.

Status words:

- **Implemented.** The code follows the printed sentence.
- **Ambiguous.** The book can be read more than one way. The log says which reading was used.
- **Missing data.** The chart needs a rating the card or roster does not have. No rating is invented.

Dice only is `fac=False`. The default game draws the Fast Action Card deck (pages 12–15 and 40–71).

The 1986 season card set PDF is players and parks. It has no Fast Action Card sheet. The 256-card deck was read from rulebook pages 40–71, eight cards a page. `engines/sim/fac_deck.json` stores each card as printed. 26 cards print `WP?` beside the 1d6. Those are the only cards whose percentile is 30 through 39. The mark means wild pitch. Pages 12–15 do not say whether the mark is itself a wild pitch or a prompt to use the page 10 rating check. This game uses the page 10 check, and the log flags that reading as uncertain. Three cards (page 48 column 3, page 59 column 1, page 65 column 1) replace the stealing grades with: use the previous card’s 1d6; 1–3 out and check the runner for injury; 4–6 safe and check the fielder for injury. Their HOME line is only `C` or `P`, so a play at home is not read from those cards. Every other line matched the printed vocabulary.

The rate harness in `pa_sim.py` is a different tool. It is unchanged. Its error chart treats several page-20 error faces as outs and treats SINGLE+error as a reached-on-error. This game follows the printed ERR chart: a numbered error is that many bases, and SINGLE+error is a hit plus one extra base.

## Plate appearance

- **Pitcher 2d6, then the batter section (pages 2–4).** Implemented. Percentile 00 on the initial roll is a rare play (page 4). A face that misses the section is an out (page 4).
- **PATIENT-OUT (page 2).** Implemented. A walk or hit by pitch counts. Anything else uses the OUT section. If that face is also outside the OUT section, page 2 says to use the out printed with the pitcher result. These cards store the words PATIENT-OUT and do not store that out. The log names the gap and records an out with no fielding code.
- **TOUGH-OUT (page 2).** Implemented. A strikeout counts. A face above the strikeout band is an out, including a face that sits in a hit band. A face below the band keeps its printed result.
- **Page 39 +10 / +20.** Implemented on a plain TOUGH result, on by default, because it is a printed rating. 00 is not shifted. A sum over 99 keeps the original face. **Ambiguous:** the addendum names TOUGH and does not name TOUGH-OUT. The shift is not applied to TOUGH-OUT.
- **BALLPARK (pages 2 and 9).** Implemented. The home park’s wheelhouse column follows the batter’s stance (left column `wh_l`, right column `wh_r`). Inside that range, the re-roll is read on WHEELHOUSE. Otherwise it is read on IN-PLAY. **Ambiguous:** page 9 says re-roll the dice. Page 2 and the FAC instructions (page 13) name the percentile. This game re-rolls the percentile and keeps the 2d6.
- **/IN-PLAY/ (page 3).** Toggle `slash_in_play`. `normal` (the default) always reads IN-PLAY, which is the cross-era option. `first_inning` uses the printed first-inning / later-inning split. `out_section` uses the batter’s OUT section. These cards do not contain `/IN-PLAY/`, and they do not store the out printed beside it. **Missing data** if that mode is turned on.
- **Supplemental strikeout band (page 11, optional rule).** Toggle `supplemental_so`, **default on** (owner choice, 2026-10-27); turn off with `supplemental_so=False` or `stress_sim.py --no-supplemental-so`. When a batter-card out falls in the pitcher's SO range, it is a strikeout. The 2024 set prints the band from 50 (e.g. Mason Miller 50-73); the 1986 set leaves it blank. 34 cards carry `card_pit.so_band`. **Derived, not printed:** the band is sized from the gap between the pitcher's real SO rate and what his solved table can give (gaps under 0.015 per BF get none), starting at 50 like the 2024 set. Pitchers with no band are unaffected. Each band card carries `so_band_source: "estimate"`, and the game log says the range is an estimate. Stress effect (with the 2026-10-27 hitter repair): SO 7.71 → 7.84 per team-game, runs 5.14 → 5.14.
- **Optional 00 home run (page 39).** Toggle `zero_hr`, default off. It applies only when the HR range is blank or 0.

## Baserunning

- **Basic (pages 5–6 and 16).** Default. Runners move as many bases as the hit. With two outs, or on a WHEELHOUSE hit, they take one more. A triple or home run scores everyone.
- **PATIENT extra base (pages 6 and 16).** Implemented when the automatic extra base does not already apply. The lead runner goes when a new 2d6 is less than RUN. The coach’s chart then compares 2d6 with RUN and ARM. **Ambiguous:** a PATIENT hit with two outs is named by both sentences. This game uses the two-out extra base and does not add a second attempt.
- **Advanced chart (page 16).** Toggle `running="advanced"`. The low die of the at-bat’s 2d6 is the column. With two outs, RUN 6 or higher takes two on a single and scores on a double. RUN 5 or lower has the coach’s choice. **Ambiguous:** the chart has no column for a runner on third, or for a runner on second when the hit is a double. That runner takes the same number of bases as the hit, and the log says so.
- **Fast Action Card running (pages 13–14).** Default when the deck is on. A single or a double with a runner on base draws the next card and follows the SINGLE or DOUBLE lines. `+?` uses that card’s 1d6: the lead runner tries when RUN is higher, then the coach’s chart. Page 14 also allows the next card’s 1d6. This game uses the same card and says so. With two outs, RUN 6 or higher takes two bases on a single and scores on a double. RUN 5 or lower follows the card. A triple or home run has no FAC line; runners take as many bases as the hit. `running="basic"` or `running="advanced"` still selects those charts while the deck supplies the numbers. **Ambiguous:** advanced running needs the lower die, and stealing third needs doubles. A card prints only the 2d6 total. Those two checks roll real dice. Page 15 allows dice with the deck.
- **Hit location (page 16).** Implemented from the ones digit. A slash uses the left fielder for a left-handed batter and the right fielder for a right-handed batter. A switch hitter stands opposite the pitcher (page 5 does not say this in those words; the card engine already treats a switch hitter that way, and the park column uses the same stand).

## Outs, double plays, flies, bunts, hit and run, infield in

- **Strikeout, popout, lineout (pages 5 and 17).** Implemented. Runners hold.
- **Ground ball with a runner on first and fewer than two outs (pages 6 and 17).** Implemented. The lower of the pitcher DP and the batter DP is the rating. 2d6 at or under it is a double play. 2d6 of 11 or 12 is a play at first and the runners advance one. Anything between is a fielder’s choice. The at-bat percentile’s exceptions are included: a 5 with runners on first and second and the ball to the third baseman, shortstop, or pitcher puts the runner from second out at third; a 5 on a fielder’s choice to the shortstop or third baseman puts the runner from second out at third; a 6 to the shortstop is the ordinary 4-6-3. **Ambiguous:** the first exception does not say what the runner on first does, or whether a runner on third scores. They hold. **Missing data:** if one of the two DP ratings is absent, the one that exists is used alone and the log says page 6 wanted the lower of the two. A missing rating is not filled in with 12.
- **G3 unassisted (page 17).** Implemented as a log note. A percentile ending in 3–9 is unassisted. Ending in 0, 1, or 2 is a throw to the pitcher covering. The batter is out either way.
- **Ground ball with first base empty (page 17).** Implemented, including the pitcher’s look-back, the automatic score from third on a ball to the second baseman or shortstop, the choice from third on a ball to the corners, and the runner on second.
- **Fly balls (page 17).** Implemented. WHEELHOUSE and PATIENT are deep. A runner who scores from third, when the catch is not the third out, is a sacrifice fly and not an at-bat. **Ambiguous:** page 17 says a runner on third scores on a deep fly and does not mention the third out. This game does not count a run on the third out.
- **Sacrifice bunt, option 1 (page 9 and the page 19 chart).** Implemented. With the deck on, the card’s letter result (SH, LEAD, DP, PO, MISS, E?) replaces the percentile chart, and the card’s 1d6 names the fielder (pages 13–14). A miss draws another card. Option 2 cannot run. **Missing data:** the cards store the bunt letter and do not store the 2d6 auto-bunt numbers. A declared bunt is a usage choice: the 8 or 9 hitter, a runner on first, nobody on third, fewer than two outs. The squeeze is coded (column D, page 19) and is not called on its own.
- **Hit and run (pages 10 and 18).** Optional, and on. The moment it is called is a usage choice: runner on first, nobody on third, one out, lineup slot 2 or 6. WHEELHOUSE re-rolls all four dice. Doubles are read as a normal wheelhouse. 00–49 is a single and the runners take two. 50–99 is the OUT section. PATIENT is a foul re-rolled on IN-PLAY. A walk is refused. **Ambiguous:** the book does not say what that walk becomes. It is re-read on IN-PLAY. **Ambiguous:** PATIENT-OUT is not named, so it follows PATIENT. A lineout doubles off the lead runner. **Ambiguous:** the book says the closest runner and does not say how to measure closest. A runner rated 7 or higher scores from first on a single when the outfielder’s arm is 8 or higher. Otherwise he stops at third. F8 and F9 with a runner still on first use the extra 2d6 and 1d10. **Ambiguous:** 1d10 is read as 0–9. The book does not say whether 0 is 10.
- **Infield in (pages 7 and 19).** Optional. Declared only from the 7th inning on, with a runner on third, fewer than two outs, and the score within one. That moment is a usage choice. The 2–5, 6–8, 9–10, and 11–12 rows are implemented, including the bases-loaded notes and the play at home. **Ambiguous:** the bases-loaded 1d10 is read as 0–9.

## Steals, pickoffs, wild pitches

- **Auto steal (page 7, option 2).** Default. One check when the batter reaches and the next base is open. Third base needs doubles and a total at or under Jump. No Jump rating means he does not go. With the deck on, the 2d6 is the one on the card whose result put him on base (page 13), and the next card’s STEALING column is Safe, Out, Drop?, or SB+E2?. **Ambiguous:** the dice game does not say whether the 2d6 is the at-bat’s roll or a new roll, so `fac=False` rolls a new 2d6. Stealing third still needs doubles. The card does not show the two dice, so those two dice are rolled (page 15). The three injury cards use the previous card’s 1d6, as printed.
- **Manager’s choice (page 7, option 1).** Not the unattended default. The stealing and stealing-home charts are transcribed. Auto steal never sends a runner home, because option 2 only checks the batter who just reached.
- **Hold (page 7, option 3).** Toggle `steal="hold"`. A new 2d6 is compared with the pitcher’s Hold. **Ambiguous:** the book says to roll four dice and does not say the roll is separate from the at-bat. **Missing data** when Hold is blank.
- **Jump + / − and Jump 1 (pages 8 and 39).** Implemented. The plus or minus applies the first time he reaches with a steal chance. Jump 1 is used as 2 that once, and he is not checked again.
- **Steal dagger (page 39).** **Missing data.** No card stores the dagger after the steal letter, and the book gives no rule for awarding it, so a catcher arm of 1 or 2 is not rewritten to 3.
- **Hitter range and error (pages 8 and 18–19).** Implemented from the card. Cards built from franchise windows used to carry the engine Average default (range C, error 4). 313 of them now carry a range and error derived over the card’s franchise window (`scripts/derive_hitter_fielding.py`, cutpoints in `engines/sim/hitter_fielding_method.json`): range from (PO+A) per inning at the position against the league (per game, with its own cuts, where Lahman has no innings), error from E per chance against the league. Cutpoints are fitted per position to the printed 1986 hitter cards. Error reproduces the 1986 grade 95–100% exact per position; range only 48–56% exact and 81–97% within one grade, so range is the weaker rating. Error 5 is the fewest errors (the park chart’s smallest error band). Three cards keep the default because the window has no usable games at the card position (Biggio at C, Ohtani on both clubs); the log still names them. Per-card flags: `historical-cards/accuracy/hitter_fielding.json`.
- **Catcher arm (page 8).** The chart is arms 1 through 5, 1 the best. The 1986 cards use that scale for catchers and a different scale for outfielders: Rich Gedman C arm 1, Ernie Whitt C arm 2, Carlton Fisk C arm 3 and LF arm 8, Tony Pena C arm 2. Every 1986 catcher arm in `historical-cards/reference/cards_1986.json` is 1–5 (110 catchers). Outfield arms in that set run from 4 to 9. Roster catcher arms are now on that 1–5 scale. They were re-rated from catcher CS/(CS+SB) versus the league over each card’s franchise peak window (Lahman `Fielding.csv`; 2026 from the MLB Stats API). Relative CS% cutpoints were fitted to the printed 1986 catcher arms (70 of 74 matched at ≥15 attempts): rel ≥0.44 → 1, ≥0.07 → 2, ≥−0.23 → 3, ≥−0.37 → 4, else 5. Outfield arms are unchanged. The table and flags are in `engines/sim/catcher_arm_rerate.json`. Five deadball/1930s catchers have no usable Lahman CS and default to 3 (uncertain). An arm outside 1–5 still holds the runner.
- **Pickoff on double 6s (pages 8 and 18).** Implemented when Hold exists. **Ambiguous:** a wild pickoff has a second error roll on page 18. This game advances the runners one base and does not assign that error.
- **Steal DROP fielder (page 18).** **Ambiguous:** the key uses the batter’s hand. After the batter has reached, the runner’s hand is what the base dict still has. The log says so.
- **Wild pitch (page 10).** Implemented, including a second wild pitch on the re-roll. Ratings stored as `30` or `30-32` are both read. A pitcher with no rating can wild-pitch only from a rare-play cell. Ratings missing from the set files are now derived (`scripts/derive_pitcher_ratings.py`, method in `engines/sim/pitcher_rating_method.json`): wild pitches per batter faced against the league, cut to match the printed 1986 cards (84.5% exact, 99.7% within one step). Fourteen roster pitchers fall below the `30` cut and have no rating, as the 1986 set prints for 110 of its pitchers.
- **WP? on a Fast Action Card (pages 10 and 12–15).** **Ambiguous.** The mark means wild pitch. Page 10 is the only printed wild-pitch procedure: the percentile equals the pitcher’s WP rating or falls in the printed range, and at least one runner is on, so every runner advances one base. The percentile is then re-rolled to resolve the at-bat. A second result inside the range is a second wild pitch, and that same roll resolves the at-bat. A pitcher with no rating wild-pitches only from the Rare Play charts. Pages 12–15 never say whether `WP?` is that check or an automatic wild pitch. This game uses the page 10 check. It does not treat the mark as automatic. When the marked card is the at-bat percentile, the re-roll is taken. When the marked card was drawn for something else (the pitch card, a park check, a running card, a steal card), the runners advance one base and no new at-bat percentile is drawn. The log names that once. Bases empty: page 10 does not call a wild pitch. Every percentile from 30 through 39 in the deck is printed on one of the 26 `WP?` cards, so a page-10 hit while the deck is in use is a marked card.

## Defense, errors, parks

- **Defense chart (pages 2, 13, and 20).** Implemented. With the deck on, the next card’s DEFENSE line names RANGE or ERROR and the position (or DEF RARE PLAY). The next card’s percentile is the park check. The card after that is the HIT, ERR, or OUT row for that position. DEF RARE PLAY draws one more card for the fielder and one for the rare-play percentile. Park symbols are ignored (page 13). A park percentile of 00 is outside every 1–99 band and is played as an out. With `fac=False`, the at-bat percentile picks the position and all four dice are re-rolled for the park. RANGE that lands on the catcher uses center field (page 2).
- **HIT chart stars and the dagger triple (page 20).** Implemented.
- **ERR chart (page 20).** Implemented as printed. A dropped foul restarts the at-bat. SINGLE+error is a hit plus one extra base.
- **OUT chart (page 20).** Implemented, including the range letters on the double-play rows and the arm-5 short-fly double play. **Ambiguous:** the double-play row does not say whether other runners advance. They hold. The lineout double play says the closest runner. The lead runner is used.
- **Park charts.** Home park is the 1986 card when that stadium is also one of the 12 charts in the rulebook (pages 109–110). Fenway’s faces match. A club with no 1986 park in that set is refused. Colorado, Miami, Tampa Bay, Arizona, Washington, and the Philadelphia Athletics are in that group.
- **Error rating direction (page 2, park cards).** Page 2: “The ‘E’ rating is the batter’s Error rating with 1 being the worst and 5 the best.” The printed park cards agree (error 5 has the smallest ERR band, e.g. Cleveland 1986: 5 = 1–32, 1 = 1–69) and so do the printed 1986 cards (Ozzie Smith SS A 4). The engine reads the digit as printed. 166 set-file hitter cards (labels Elite, Great, Above Average, Below Average, Poor, plus Larry Walker COL) had the digit the other way round (Elite A/1 … Poor F/5); it is flipped (6 − e) by `scripts/fix_error_scale.py`, and those cards carry `error_scale`. Range, arm and label are unchanged.
- **Pitcher fielding.** Implemented. Every roster pitcher card carries `card_pit.fielding`, the range and error grade the 1986 pitcher cards print under FIELDING. It is derived from franchise-window pitcher (PO+A) and E per inning against the league, cut to match the printed 1986 grades (range 80.8% exact, error 85.2%). A batting card's own position line still comes first (Ruth).
- **Average fielding.** Where a card still has the engine default (range C, error 4, label Average), the log says that grade is not a printed rating. Boston and Toronto fielders in the sample game are not in that group. Empty-roster clubs are.

## Fatigue, relief, injury

- **Starter fatigue (pages 10–11 and 21).** Implemented when Start stamina exists. He tires in the inning equal to Start if he has allowed 3 or more runs, and at 6 runs in any inning. A fatigued BALLPARK is read on WHEELHOUSE with the same percentile. PATIENT and TOUGH are re-read on the page 21 chart. A fatigue single uses the original PATIENT or TOUGH advancement. Slash and OUT qualities are ignored while he is tired (page 21).
- **Short and long relief (page 11).** Implemented. Each inning he appears in counts as one. Short tires at 2 runs, or after the second inning ends. Long tires at 3 runs, or after the third inning ends.
- **Removing a tired pitcher.** Not required. The book lets him stay on the fatigue card. All of this is usage, not rule. Option `bullpen`, default `"manager"` (owner choice 2026-10-27):
  - A fatigued starter is pulled before the next batter, and so is a starter who has allowed 5 runs.
  - A starter goes his Start rating in innings, then comes out at the end of a half. He may continue only while leading with 1 run or fewer allowed.
  - From the 9th, a lead of 1-3 brings the closer, the first unused Short man in roster order, for a starter who has gone 7.
  - The reliever is a Short man (roster order) from the 7th inning with the score from -1 to +3, a Long man before the 7th, and otherwise the last Short man.
  - The closer call is re-checked on the score at the moment of the change. A reliever who is fatigued (page 11) comes out before the next batter if the pen has an unused arm.
  - A Short man still comes out after one inning and a Long man after three. A pitcher who leaves cannot return.
  - `bullpen="book"` keeps the old behaviour: a fatigued starter comes out only at the end of a half, and the next name in the bullpen comes in.
- **Official scoring (not in the book; MLB rules 9.04, 9.16-9.19).**
  - RBI: none on a run that scores on a steal, pickoff or wild pitch, when the batter reached on an error, or when he grounded into a double play.
  - Runs: each run is charged to the pitcher who put the runner on base, so inherited runners count against the earlier pitcher.
  - Earned runs: a run is unearned when the runner reached on an error, or when the outs plus the errors in the half reach three. This is an approximation of rule 9.16; passed balls are not counted.
  - Pitcher lines: H, BB, SO, HR and HBP come from the batter lines.
  - W/L/S/H: the decisions use the run that put the winner ahead for good.
    - A starter under 5 innings gets no win; the win goes to the most effective reliever.
    - A save needs a save situation at entry: a lead of 1-3, or the tying run on base, at bat or on deck. The pitcher must then work an inning, or work 3 innings with any lead.
    - Holds use the same save situation.
  - The fatigue counter (pages 10-11) still counts every run that scores while the pitcher is in.
- **Save symbol #, †, or + (pages 11 and 39).** **Missing data.** No card stores it. It is not derived: on the 1986 cards the `+` does not follow saves (Bedrosian and Franco, 29 saves, have none; some starters with one save print `Long+`). The save-situation exception is not applied.
- **Empty stamina.** Filled. Pitchers built for clubs without a printed stamina line (Whitey Ford and the other once-empty rosters) now carry Start and Relief stamina derived from franchise-window innings per start and per relief game, cut to match the printed 1986 FATIGUE line (Start 79.2% exact, 94.3% within one; Short/Long 100%). Following 1986, a pitcher gets Start if he started and Relief if he relieved; one who did both is Long. If a card still has no stamina, the log says pages 10–11 cannot say when he tires. Pedro Martinez (Start 6) and Dave Stieb (Start 7) have stamina. The sample game uses them.
- **Pitcher rest chart (page 21).** Not applied. It is days of rest between games. This is one game.
- **Injury chart (page 21).** Implemented when a coded play calls for it. A player with no Prone / Normal / Durable / Iron rating is not given Normal. Most rare-play injury sentences sit in cells that are not transcribed.

## Rare plays (pages 22–30)

A 00 re-rolls the percentile and looks up the cell. Coded cells, bases empty unless noted:

- Wheelhouse 00–05 and Patient 00–05: the pitcher leaves and is checked for injury.
- Wheelhouse 06–13: foul ball, catcher injury check, the at-bat is not a result.
- Wheelhouse 14–16: line drive off the pitcher. RUN 6 or less is out. RUN 7 or more is a single.
- Wheelhouse 17–26: groundout, batter leaves.
- Wheelhouse 27–56: weather die. 1–2 no effect. 3–4 both current pitchers leave. 5–6 postponed. Official only from the sixth inning.
- Wheelhouse 57–66: RUN 5 or less is a single. RUN 6 or more is a double and then out at third.
- Wheelhouse 67–76: home run unless the center fielder’s range is A.
- Wheelhouse 77–79 and 92–99: the printed outs.
- Wheelhouse 80–86: out if the left fielder’s range is A, otherwise a single.
- Wheelhouse 87–91: double.
- Patient walks, strikeouts, and hit by pitches on page 22, for the bands in `rare.py`.
- Tough 00–12 strikeouts, and 45–64 the dropped third strike.
- In-play 06–11: single off the pitcher.
- Defense 94–99, bases empty: restart the at-bat.
- Runners on, wheelhouse 70–79: single, runners advance two.

Every other cell is **not transcribed**. The log names the section and the percentile. The at-bat is rolled again. The book does not say to replay it. Replay exists so a test game can finish.

Lasting sentences that are coded only in part: the extra out on a dropped third strike is logged and not added. Ejections, suspensions, and “every TOUGH becomes a strikeout for the rest of the game” are not modeled. Those cells are mostly still in the uncoded set.

## Things the book does not define

- **Designated hitter.** The word does not appear. Any of the nine lineup hitters may be the DH. The pitcher does not bat, because the roster lists nine hitters. Jose Bautista is Toronto’s DH and does not field. **Ambiguous:** Boston lists David Ortiz and Jimmie Foxx both at first base. The book does not say who fields. Ortiz fields. Foxx hits and does not field.
- **Extra innings.** The book does not say. A tie after nine continues one full inning at a time until one side leads. Nobody is placed on second. A safety stop at 30 innings is not a rule. The sample game did not need it.
- **Earned runs.** Not defined. The box counts runs only.
- **Which hand covers second on a steal DROP after the batter is already aboard.** See steals.

## Logged game

`engines/sim/samples/tor-at-bos-seed1.txt`

Toronto at Boston, Fenway Park, seed 1, Fast Action Cards. Final: Boston 9, Toronto 1, nine innings. Pedro Martinez pitched all nine (W). Dave Stieb (L) went 4.2 innings; Toronto used three relievers.

Before manager bullpen usage and official scoring (2026-10-27), it was Boston 5, Toronto 1. Before intentional walks were counted as walks on hitter cards (2026-10-27), it was Toronto 7, Boston 1 (the capacity repair and default supplemental SO had left that unchanged). Before the platoon re-split and per-hand pitcher calibration (2026-10-27), it was Toronto 7, Boston 3. The same seed with dice, before the deck was wired, was Toronto 5, Boston 8. With the FAC deck and catcher arms still on the old 4–8 word scale, it was Toronto 0, Boston 4. Before set-file error digits were put on the rulebook direction (2026-10-27), it was Toronto 0, Boston 2. Before the pitcher 2d6 tables were re-solved with solver v0.3 (2026-10-27), it was Toronto 0, Boston 4. Every change to a card or to the deck sequence changes the line score.

`WP?` on this seed: thirteen marked cards drawn, none fired. Five came up with the bases empty. Eight missed the pitcher’s rating (Pedro Martinez and Dave Stieb are rated 30). No drawn card met a pitcher who has no WP rating.

Steals on this seed: five FAC steal resolutions. Tris Speaker and Josh Donaldson were caught stealing. Nomar Garciaparra was safe on SB+E2? (Whitt's error 1, so the throw sailed). Dustin Pedroia and Jimmie Foxx stole.

The catcher re-rate table is `engines/sim/catcher_arm_rerate.json`.

The file is a hand check. It is not in `tournament_results.json`. Played games are unchanged. The service-worker cache is unchanged.

`python3 scripts/stress_sim.py --seeds 3` plays every ordered pair of clubs with a 1986 park card on the deck and checks crashes, hangs, outs, runners, batting order, box-score totals (runs, PA = AB+BB+HBP+SF+SH, pitcher BF) and rule-path coverage. It writes only to /tmp.

`python3 engines/sim/test_game.py` checks the charts, a scripted double play, sacrifice, steal, defense hit, ballpark split, fatigue single, the extra-inning continuation, the FAC deck, and this seed. `python3 engines/sim/test_pa_sim.py` still passes. The rate harness was not edited.

- **Outfield arm direction.** Rulebook page 8: outfield Arm runs 3 (best) to 10 (worst); the extra-base chart (page 16) makes the runner safe on 2d6 <= ARM, so the engine already reads it that way. Set-file cards had it backwards (Elite/Great 8, Poor 4); `scripts/fix_of_arm_scale.py` mirrors them (12 - arm) and marks `of_arm_scale`. Catchers, infield rows and Derived cards (default 6) are unchanged.
- **Injuries and removals.** A removed or injured player is replaced for the rest of that game only: a batter by a bench player at his position (else same infield/outfield side, else first unused bench player), a runner on base by that substitute, a pitcher by the next unused reliever. A pitcher who has left cannot come back (relievers used to ping-pong). Clubs load fresh each game, so the player is back next game. The book names no replacement rule; this is a usage choice.
- **Stealing.** Auto steal (page 7, option 2): one check when the batter reaches first or second with the next base open, 2d6 <= Jump; third needs doubles too; no Jump number, no auto steal; Jump +/- applies the first time on base (page 8). A 2d6 of 12 goes to the pickoff chart (pages 8 and 18); a pickoff out is now scored `po`, not `cs`. Jump numbers were recalibrated from real attempt rates (`scripts/fix_jump_from_attempts.py`).
- **Parks.** ARI, COL, MIA, TB and WSH use their 2024 Season PDF park cards (`historical-cards/reference/ballparks_2024.json`); no 1986 card exists for them. PHA has no park card in either set; its games use the 1986 Veterans Stadium card as a labelled stand-in (log header, gap note, `park_stand_in` in the report).
- **Steal letter and Derived OF arms.** Steal letters come from window SB% and attempt rate fitted to the 1986 cards (`scripts/fix_steal_letter.py`); Derived-fielding outfield arms come from OF assists per game vs league fitted to 1986 printed arms (`scripts/derive_of_arm.py`).
- **Error rate / pitcher tables.** DEFENSE, FAC defense lines, park error bands and the error digit follow the rulebook. The old v0.2.3 solver modelled DEFENSE as 25% singles with no errors and gave it 19.9% of the 2d6 weight (1986 cards: 4.6%). Every pitcher table is now re-solved by `engines/pitcher-v0.3` (DEFENSE vector measured in this engine, full H/HR/BB/SO/HBP target, result shares held to the printed 1986 cards); `scripts/resolve_pitcher_tables.py`.
