# Changelog

Dated rulings and repo history. The rules, seeds, and bracket in force are [TOURNAMENT_RULES.md](TOURNAMENT_RULES.md), [TOURNAMENT_SEEDS.md](TOURNAMENT_SEEDS.md), and [BRACKET.md](BRACKET.md). This file is the history those pages used to carry inline.

## 2026-10-28 — Hitting engine v1.2: HR and walk bands extrapolate past the 1986 range (engine only, no cards rebuilt)

The owner requested this change. A trust test of 16 tournament players against the 1986 pitching found the elite and power hitters short on HR and walks. Two causes in `engines/hitting_engine_v1_2.py`:
- `DecileTable.predict` went flat above the highest 1986 rate.
- The 99-face overflow trim cut the widest strand, usually the HR or the walk strand.

Fix:
- **`EXTRAPOLATE_CEILING`** (default on, `Engine.fit(..., extrapolate=False)` restores the old behavior). Above the top 1986 rate, the WHEELHOUSE HR and PATIENT BB (walk target BB+IBB) widths keep growing in proportion to the rate. The section then gives up its singles, then doubles and triples (and HBP), before the HR or walk strand is cut. Only sides with at least `MIN_FIT_AB` AB extrapolate.
- **`TRIM_SINGLES_FIRST`** (default off) is an opt-in for in-range sections. It changes 89 printed 1986 sides, so it is left for the owner to decide on.

Checks:
- With the default, 0 of 1,160 printed 1986 sides change, and `--demo` output is identical.
- In the 1986 blind test (14 hitters), only Schmidt vs LHP changes: HR 1-62 to 1-75 (official card 1-96), sim HR 29.7 to 31.4 (real 37). Everything else is byte-identical.
- New `engines/test_hitting_engine_extrapolation.py`.

`data/cards.json` is untouched. No card in the live set is rebuilt by this change.

## 2026-10-27 — Phillies: Johnny Callison replaces Billy Hamilton

The owner requested this change.
- **Roster.** Johnny Callison (RF, bats L, 10 Phillies seasons) takes Billy Hamilton's lineup slot 1. Hamilton is removed from `rosters.json`, `announced_rosters.json`, `ROSTERS.md`, `peak162.json` and `cards.json`. The bench (6) and bullpen (6) are unchanged.
- **Card.** It uses the franchise-card method (`scripts/build_callison_card.py`, a wrapper for `build_sixth_bench_cards.py`).
  - Window: the five best Phillies seasons by league OPS+ with PA>=300, which are 1962, 1963, 1964, 1965 and 1968. Baseball-Reference OPS+ gives the same five.
  - Solver: Hitter v0.5, then `card_postpass` (platoon re-split, IBB as walks, jump and steal letter from SB+CS, OF arm), then `derive_hitter_fielding`. QA PASS.
  - Fielding: RF range B, error 4, arm 4 (top bucket: 100 assists in 739 games, 2.36x league). Jump 3, steal C.
  - Card vs real: AVG .274/.275, OBP .334/.334, SLG .485/.487, HR .040/.040, SO .154/.154.
- **Peak 162 line.** 1961-1965, the consecutive-window display method.
- `sw.js` cache v87.
- **Carlos Ruiz replaces J.T. Realmuto** (owner request). Ruiz is the starting C in slot 8. Realmuto's Phillies card and roster row are removed; his Marlins card is untouched.
  - Hitting card: franchise method, window 2009-2012 and 2014 (league OPS+ 111, 136, 114, 159, 108). QA PASS. Card vs real: AVG .283/.284, OBP .374/.374, SLG .429/.432, HR .021/.021.
  - **User-directed override:** catcher range A, error 5, arm 1, the best value on each rulebook scale. Derived values were range C, error 4, arm 6 (default).
- **Roberto Clemente (PIT)** outfield arm set to 3 (**user-directed override**). Rulebook page 8 says 3 is the best outfield arm. He was 4. No other card is rated 3.
- **Phillies lineup, owner's CF choice:** Ashburn now starts in CF and leads off. Callison bats 2nd in RF. Abreu moves to the 4TH OF bench role, swapping places with Ashburn. Howard stays DH: his card OPS is .963 to Abreu's .957.
- `engines/sim/test_game.py`: the `tournament_results.json` fingerprint is updated to main's current file (b19407d). The results file itself is unchanged.

## 2026-10-27 — R1-01 player pages get their missing tournament lines

A stat-recording audit found every existing tournament block in `data/cards.json` exact (149 stints, 2,281 fields, zero mismatches) but the whole R1-01 Yankees/Marlins casts, 42 stints, carried `tournament: null`, so their player pages showed no tournament stats while LEADERS.md already counted the series. Root cause: the Yankees and Marlins cards were created by the empty-team batch builder after the last tournament refresh, and no refresh ran afterward. Fix: one run of the preserve path in `scripts/build_cards.py`, which replaces only the tournament block from the repo's own `tournament_results.json`. Exactly 42 cards changed (NYY 20, MIA 22), every one a null-to-block transition with the card body byte-identical; the other 12 Yankees/Marlins cards belong to men who never appeared in R1-01 and stay null. Verified independently of the builder: each new block was recomputed from the raw game lines (batting, pitching, W/L/SV, game lists) with zero mismatches, the two clubs' block AB total ties the archive's R1-01 total exactly (297), and cross-team men keep separate blocks per club (Cabrera's Miami block carries R1-01 only, his Detroit block R1-04 only). Validator: all checks passed. A second run refreshes 0 and leaves the file byte-identical.

## 2026-10-27 — Thirteen bullpen cards get their missing stamina lines

A full-population audit found 13 pitcher cards in `data/cards.json` with `stamina {start: null, relief: null}`, so the fatigue rules (rulebook pp.10–11) had nothing to read: Stewart (BAL), Locker (CWS), Dotel (HOU), Leibrandt (KC), Corbett (LAA), Burnett (MIA), Peralta (MIL), Marberry (MIN), Fernandez (NYM), Reynolds (NYY), Nelson (OAK), Madson (PHI), Moore (SEA). Root cause: the empty-team batch builder leaves stamina and the addenda empty on purpose, expecting `scripts/derive_pitcher_ratings.py` to fill them, but that pass only visits players listed in `data/rosters.json`; these men were the seventh bullpen arm dropped when their clubs went to a six-man bench, and a card outlives its roster spot (`build_cards.py` never deletes one), so the pass never reached them again. Fix: the derive pass now also visits any pitcher card no roster row covers whose stamina is still completely empty, deriving from that card's own peak window by the same 1986-fitted method as the rest of the population. The same visit filled the 13 cards' other empty derived ratings (WP, DP, Hold, Injury, pickoff line, pitcher fielding), the way it treats any card it visits. No other card changed; a second run is a no-op. Values: Start 1–9 from innings per start, Relief Long for every man who both started and relieved in his window, Short for Locker, the one pure reliever. Report: `historical-cards/accuracy/pitcher_ratings.json`.

## 2026-10-27 — Intentional walks count as walks on hitter cards

Owner ruling: the engine has no intentional walk, so a hitter's real IBB are printed as ordinary walks. Card walk target is BB (IBB included) over full PA, in `hitter_solver.build_one`/`event_targets` and `scripts/capacity_retune.py`. The pass widens PATIENT BB (both hands) from empty faces, then from PATIENT hit faces, which the IN-PLAY/TOUGH re-tune puts back. PATIENT holds about 22.9% of PA; a card that cannot reach its walk target is flagged `card_bat.capacity_basis.walk_cap_hit`, and the walks it cannot print are dropped as plate appearances (other bands scaled by 1/(1−shortfall)) instead of becoming outs, so only OBP falls short. Flagged: Barry Bonds (28.3% target, 21.7% on card) and Ted Williams (22.6% vs 22.3%). Basis on each card: `ibb`, `walk_target_bbp`, `walk_expected_bbp`, `walk_shortfall`, `target`. Idempotent (re-run changes nothing). 439 cards differ from the pre-repair cards.
- Card vs average pitcher: Bonds .334/.471/.723 → .332/.485/.725, McCovey OBP .388 → .418, Judge .417 → .437, Ruth .489 → .512.
- Stress (2,976 games): runs 5.14 → 5.28, BB 2.96 → 3.28, OBP .319 → .326, AVG .258, SLG .435 → .436.

## 2026-10-27 — Monster-hitter repair; supplemental SO on by default

**Why the great hitters hit low (Ruth .245 vs .375, Bonds .230 vs .346).** Traced with `scripts/hitter_gap_trace.py` (real → card vs average pitcher → card vs all tournament pitchers → games):
- **Opponent quality (largest, inherent).** Every hitter loses about .045 AVG, .06 OBP and .12 SLG moving from an average pitcher to this all-star pitching field. Not a bug.
- **Card build for extreme hitters (two bugs, fixed).** (1) The solver divided every event by PA that still included intentional walks, while IBB was dropped from BB, so each IBB became an out (Bonds 10.5% of PA, 1% on average); superseded by the IBB-as-walks entry above. (2) Shape projection clipped hits off full PATIENT/WHEELHOUSE sections (Ruth had 69 empty IN-PLAY faces). `scripts/capacity_retune.py` rescales bands for IBB and moves lost singles/doubles/triples into IN-PLAY/TOUGH within printed 1986 widths; it keeps a change only if AVG rises and SLG does not fall. 224 cards changed; history in `card_bat.capacity_basis`. Ruth card .298 → .359 AVG, Bonds .301 → .334. It runs in `card_postpass.py` after the platoon split.
- **Format ceilings (inherent).** HR prints only in WHEELHOUSE (max about 8.1% of PA) and BB only in PATIENT (about 22.9%). The engine has no intentional walk, so real OBP that came from IBB cannot appear.
- **Parks, fatigue, fielders, FAC:** ±.02 AVG by team. **Platoon re-split:** about zero; lefty stars are not hurt vs LHP.
- Stress (2,976 games): runs 5.05 → 5.14, AVG .256 → .258, SLG .430 → .435. Hitters at 84.6% of real AVG (was 84.1%).

**Supplemental strikeout rule (page 11) on by default.** Owner choice. Turn off with `supplemental_so=False` or `stress_sim.py --no-supplemental-so`. The 34 bands are estimates, not printed, and are labelled `so_band_source: "estimate"`.

## 2026-10-27 — Platoon splits, per-hand pitcher calibration, 1986 steal/arm calibration, optional SO band

**Lefty pitchers allowed ~25% more runs than righties (stress RA9 6.21 vs 4.95; real 3.01 vs 2.93).** Two causes, both fixed:
- **Hitter platoon split.** The hitter solver picked comps by stats only, so left-handed batters lost the 1986 platoon split (1986 L batters print WHEELHOUSE HR about half as wide vs LHP as vs RHP; ours were near even). `scripts/platoon_resplit.py` re-splits every hitter card (482) to the same-side L:R ratio on qualified printed 1986 cards, keeping the 0.28/0.72 weighted total per section and result, so each hitter's expected line moves by rounding only (≤ .005 AVG). The out table is rebuilt over the moved holes. Previous sections and out table are kept in `card_bat.platoon_basis`.
- **Pitcher calibration by hand.** The printed-1986 calibration line pooled both hands; residuals split by hand (LHP H −.009/BF, SO +.005). `calibrate.py` now fits a per-hand intercept (`hand_offset`), and all 377 tables were re-solved.
- Result: LHP 6.21 → 4.91, RHP 4.95 → 5.24.

**Steal ratings and OF arms recalibrated to 1986.** The 1986 set prints 1986 stats, but the Jump, steal letter and OF arm cuts had been fitted on 1985. Refit on 1986 Lahman (`scripts/calibrate_steal_1986.py`, `reference/steal_calibration_1986.json`): Jump exact match 92% (was 49%), letter 40% exact / 79% within one, Derived OF arm 35% exact (was 21%). Re-applied: Jump changed on 95 cards, letter on 28, OF arm on 15. Jumps 7-9 rest on few 1986 cards.

**One post-pass for every builder.** `scripts/card_postpass.py` (platoon split, Jump/letter, pitcher v0.3 table, Derived OF arm) now runs in `build_cards.py`, `build_sixth_bench_cards.py`, `build_empty_team_cards.py` and `build_missing_hitters.py`, so sixth-bench and derived cards get the same treatment on a rebuild. Running it on the current cards changes nothing.

**Optional page 11 Supplemental Strikeout band (off by default).** The rulebook (page 11) has an optional SO band; the 2024 set prints it from 50, the 1986 set leaves it blank. 34 high-K pitchers whose real SO rate is beyond their table get a derived band (`card_pit.so_band`, marked not printed). Toggle `supplemental_so`. Stress: SO 7.59 → 7.72, runs unchanged.

Stress (2,976 games), before → after: R 5.07 → 5.05, H 8.72 → 8.68, HR 1.27 → 1.27, BB 2.87 → 2.91, SO 7.67 → 7.59, DP .62 → .60, SB% .621 → .643, AVG/OBP/SLG .256/.316/.430 → .256/.317/.430. Sample game reseeded (Toronto 7, Boston 1). Cache v84.

## 2026-10-27 — Pitcher 2d6 tables re-solved (solver v0.3), owner-approved

Every pitcher card's 2d6 table (377 cards) is re-solved by `engines/pitcher-v0.3` through `scripts/resolve_pitcher_tables.py` (also called by `build_cards.py`, seeded per card so rebuilds match).
- **DEFENSE** is no longer the v0.2.3 placeholder (25% singles, no errors). Its event mix is measured in `game.py` itself (`defense_probe.py`, 88,739 DEFENSE plate appearances with tournament parks and fielders): 1B 16.4%, 2B 2.6%, 3B 0.8%, reached on error 27.1%, fielder's choice 4.5%, out 48.6%.
- **BALLPARK** uses the 1986 park cards' WHEELHOUSE share instead of 50/50. TOUGH applies the page-39 +10/+20 shift the way the engine does.
- **Target**: H, HR, BB, SO and HBP per batter faced from the card's own window, relative to the league in the same seasons (Lahman), mapped to card rates by lines fitted on the printed 1986 cards (205 pitchers with 60+ IP matched to their 1986 Lahman lines; R² H .37, HR .75, BB .90, SO .90, HBP .01). 2B/3B allowed are not in pitching records and are not targeted.
- **Result shares** are pulled toward the printed 1986 mix and kept inside its range. TOUGH-OUT / PATIENT-OUT are no longer used (2 of 2,893 printed 1986 slots).
- **Validation**: re-solving the 205 printed 1986 pitchers from their real 1986 stats gives mean card-rate gaps vs the printed tables of H .005, HR .002, BB .006, SO .011 per BF, and a mean 6.8% of 2d6 weight on a different result.
- Share of 2d6 weight, all pitchers, old → new: DEFENSE 19.9% → 5.6%, IN-PLAY 3.9% → 17.8%, TOUGH 45.6% → 47.3%, PATIENT 19.9% → 18.9%, BALLPARK 8.6% → 8.1%, WHEELHOUSE 2.1% → 2.3%.

Other pitcher ratings are unchanged: SO modifier, stamina, WP, hold, DP, pickoff, injury and fielding. The previous table is kept in `card_pit.table_basis`. Stress run (2,976 games): errors per team-game 1.77 → 0.55, AVG .215 → .256, reached without a hit 7.4% → 3.6% of AB. Sample game reseeded (Toronto 7, Boston 3). Cache v83.

## 2026-10-27 — PHA stand-in park, steal letters, Derived OF arms; error and Coors audit

**PHA park (stand-in).** No Shibe Park / Connie Mack Stadium card exists in the 1986 or 2024 sets, so Philadelphia A's home games use the 1986 Veterans Stadium card, labelled a stand-in: the game log header says "STAND-IN for PHA", the note is logged as a gap, and the game report carries `park_stand_in`. All 2,976 stress games now run (93 PHA games failed before). The site does not display park names.

**Steal letters.** The set-file letters ran about one grade harsh against the 1986 cards (real window SB% by set-file letter B .87, C .79, D .71, F .56 vs 1986 A .79, B .74, C .69, D .65, F .59; no A at all vs 11% A in 1986). `scripts/fix_steal_letter.py` sets the letter from shrunk SB% plus attempt rate with cut points fitted to the 1986 cards (305 matched; exact 32%, within one grade 68% — single letters are uncertain). 482 cards, 301 changed (e.g. Henderson, Raines, Brock, Wills A; Ortiz D); 23 cards with no caught-stealing data keep the set-file letter. Set-file letter and score are kept in `letter_basis`. Catcher arms were already fitted to 1986 (70/74 reproduced) and are unchanged.

**Derived OF arms.** 78 Derived-fielding cards had the engine default OF arm 6. `scripts/derive_of_arm.py` rates them from OF assists per game vs league over the card window (Lahman), fitted to 1986 printed OF arms (104 matched; exact 21%, within one 65%). 50 changed (5:10, 6:28, 7:34, 8:6); 2 flagged. Report: `historical-cards/accuracy/derived_of_arms.json`.

**Errors (audit, no rule change).** The engine reads the DEFENSE result, the FAC defense lines, the park error bands and the error digit as the rulebook prints them. The high error rate comes from the pitcher 2d6 tables: DEFENSE is 19.9% of our pitchers' 2d6 weight vs 4.6% on the printed 1986 cards, because the pitcher solver uses a no-error placeholder for DEFENSE. Not changed here (it would re-solve every pitcher card).

**Coors.** Transcription re-checked against the page image; no misread. Coors plays as the highest-scoring park. Sample game: steal letters in the log change only. Cache v82.

## 2026-10-27 — Outfield arms, 2024 park cards, injuries, steal jump

**Outfield arm.** Rulebook page 8 rates OF Arm 3 (best) to 10 (worst), and the page 16 extra-base check (safe on 2d6 <= ARM) already reads it that way. 70 set-file cards stored it reversed (Elite/Great 8, Poor 4); `scripts/fix_of_arm_scale.py` mirrors them (12 − arm; 52 arms change, e.g. Clemente RF 4, Mays CF 4, Poor arms now 8). Catchers, infield rows and Derived cards are unchanged; `build_cards.py` applies it on a rebuild.

**Parks.** The 2024 Season PDF's park cards for Chase Field (ARI), Coors Field (COL), loanDepot park (MIA), Tropicana Field (TB) and Nationals Park (WSH) are transcribed exactly into `historical-cards/reference/ballparks_2024.json`. No 1986 card exists for those clubs. Philadelphia A's (PHA) still has no park card. Cleveland keeps its chart.

**Injuries.** A removed or injured player is replaced for the rest of that game only (bench player at his position, else same side of the field; pitchers from the bullpen). Clubs load fresh each game, so he is back next game. A pitcher who leaves cannot return in the same game (relievers had been re-entering).

**Steals.** The auto-steal logic matches page 7. A 2d6 of 12 pickoff is now scored as a pickoff, not caught stealing. Jump numbers were capped at 5 on the set files, so slow non-runners went as often as base stealers; `scripts/fix_jump_from_attempts.py` sets Jump from each card's window (SB+CS) per time on first, with cut points fit to the printed 1986 cards (477 cards, 446 changed; 23 pre-CS-era cards estimated as SB/0.7 and flagged in `jump_basis`). Steal letters are unchanged. Sample game reseeded (Toronto 0, Boston 4). Cache v81.

## 2026-10-27 — Error ratings on the rulebook direction; engine stress test

**Error digit.** Page 2 of the rulebook rates the batter's error 1 (worst) to 5 (best); the printed park cards and 1986 cards agree, and the engine reads the digit as printed. 166 hitter cards whose fielding came from the set files stored it the other way round (Elite A/1, Great A/2, Above Average B/3, Below Average D/5, Poor F/5), so Elite fielders drew the largest error band. Their digit is flipped (6 − e) by `scripts/fix_error_scale.py` (e.g. Ozzie Smith A/4, matching his 1986 card; Willie Mays A/5; David Ortiz D/1). Range, arm, labels, Derived cards, pitcher fielding, rosters and played results are unchanged. `scripts/build_cards.py` applies the same flip on a rebuild.

**Engine fixes from a 2,418-game stress run** (`scripts/stress_sim.py`; results are not tournament stats): a restarted at-bat (dropped foul, rare-play replay, delay) no longer counts as a batter faced; the FAC bunt result `E?` is now played (it used to do nothing and the batter's plate appearance vanished); safe on a dropped third strike is one at-bat, not two; the page 22 "reaches second, out at third" liner is one at-bat, not two; a batter whose hit ends the inning because a runner is thrown out keeps his at-bat and hit; a starter tired at the end of a half is replaced when his side next takes the field, so a game that ends first no longer lists a reliever with no batters faced. Sample game reseeded (Toronto 1, Boston 4). Cache v80.

## 2026-10-27 — Derived hitter range and error

313 hitter cards that carried the engine Average fielding default (range C, error 4) now carry range and error derived from franchise-window fielding stats (Lahman; 2026 from the MLB Stats API), calibrated per position to the printed 1986 cards (`scripts/derive_hitter_fielding.py`, `engines/sim/hitter_fielding_method.json`). Their fielding label reads Derived. Arms, cards with set-file fielding, 2d6 and result tables, rosters and played results are unchanged. Biggio (HOU, C) and Ohtani (LAA, LAD) keep the default: no usable games at the card position.

## 2026-10-27 — Sixth-bench cards and derived pitcher ratings

Every rostered player now has a card. **22 cards built** for players added since the last card build (Sisler, Allison, Henderson, Klein, P. Waner, Irvin, Werth, Horner, C. González, D. Allen, Gibson, M. Alou, Mayberry, Carew, Lowell, Oglivie, H. Johnson, Chavez, Beltré, Sierra, G. Carter, and Bobby Shantz with a full pitcher card), with the franchise-window method used for every other built card (`scripts/build_sixth_bench_cards.py`). **Pitcher ratings** missing from the set files are derived from real franchise-window stats and calibrated to the printed 1986 cards (`scripts/derive_pitcher_ratings.py`, `engines/sim/pitcher_rating_method.json`): stamina, Hold, DP, Injury and pickoff for 155 pitchers, WP for 170, and a pitcher FIELDING line for all 353. No 2d6 table, roster, or played result changed. Flags per player: `historical-cards/accuracy/pitcher_ratings.json`.

## 2026-10-27 — Final Yankees/Marlins six-bench approvals

All **32 teams** now have six bench hitters. **New York Yankees #1:** Rickey Henderson is the new sixth reserve (Yankees-only 1985–1989), replacing active long reliever Allie Reynolds. **Miami Marlins #32:** Mike Lowell joins as sixth reserve (Florida/Miami-only 1999–2005), replacing active long reliever A.J. Burnett. Both 26-player clubs are now **9 lineup / 6 bench / 5 SP / 6 RP**. Original nine starting hitters, DH assignments, rotations, six other relievers, all historical converted cards and all four previously completed R1-01 games, box scores, FAC/dice records remain untouched. Verified Lahman Peak 162: **Rickey Henderson (Yankees 1985–1989): .288/.395/.455/.850, 21 HR, 69 RBI, 89 SB**; **Mike Lowell (Marlins 2000–2004): .280/.349/.485/.834, 27 HR, 104 RBI**. Both use their own franchise seasons only. Authentic frozen playable Hitter v0.5 card conversions remain pending; no dice ratings were fabricated.

## 2026-10-27 — Arizona Christian Walker starting DH, 1B eligible (owner-approved)

Approved Arizona Diamondbacks #29 metadata correction: **Christian Walker (`walkech02`) starts at DH, batting fifth, but remains eligible at 1B/DH**. **Paul Goldschmidt (`goldspa01`) stays at first base, batting second.** Same nine starting hitters, all 26 active players and original batting order, rotation, bench and bullpen. Exactly **9/6/5/6**; the changed starting defensive assignment applies only after the six recorded R1-04 games. Preserve original cards and spots, scores, FAC/dice data, box scores, play-by-play and all completed tournament history. Missing Arizona owner-announced roster and Peak 162 data will be addressed separately; no fabricated statistics.

## 2026-10-27 — Colorado Rockies Carlos González for Ian Desmond (future games only)

Colorado #28 owner approval: **Carlos González** (`gonzaca01`) replaces Ian Desmond (`desmoia01`) at **bench slot #5**, serving as a left-handed reserve for LF/CF/RF. Count **Colorado Rockies seasons 2009–2018 only** for Peak 162 and his future frozen Hitter v0.5 playable card. Desmond is inactive but the original historical converted card stays archived. **Future games only**, after Colorado's recorded four-game R1-05 series; results, box scores, dice/FAC rolls and all played game records remain unchanged. The nine-man starting lineup (including Andrés Galarraga DH ninth), all five SP, all six RP and other five bench players stay intact. Exactly 9/6/5/6 active, 26 unique players. González's Rockies-only **Peak 162** is verified from Lahman over 2009–2013: per 162 games 32 HR, 105 RBI, 28 SB and .307/.368/.552/.920. The original playable Hitter v0.5 conversion remains pending; no invented dice outcomes.

## 2026-10-27 — Padres Ken Caminiti starting DH with 3B eligibility (owner-approved)

The original San Diego Padres #26 batting order remains untouched. **Ken Caminiti (`caminke01`) starts at DH batting fourth**, and is **eligible at both 3B and DH**; **Manny Machado (`machama01`) starts at 3B batting sixth**. The active roster stores Caminiti's starting position as `DH`, with `eligible_positions: ["3B", "DH"]`. Future roster rebuilding and the club's player-card roster display keep both positions visible. The owner-announced lineup already showed Caminiti DH. All 26 players remain 9/6/5/6, with unchanged bench, rotation and bullpen. Original converted cards, tournament games, box scores and dice/FAC history remain untouched.

## 2026-10-27 — Toronto Blue Jays Joe Carter for Jim Clancy (owner-approved)

Toronto's owner-approved 26 adds **Joe Carter** (`cartejo01`) as bench #6, a right-handed RF/LF reserve and pinch-hit power bat using **Blue Jays 1991–1997 seasons exclusively**. Jim Clancy (`clancji01`) leaves the active bullpen, retaining his authentic historical pitcher card. Six original relievers remain: Henke, Eichhorn, Ward, Osuna, Downs and Quantrill. **All nine starting hitters, José Bautista batting fifth at DH, and the complete five-man rotation remain unchanged.** Active roster **9/6/5/6**, 26 unique people. All historical cards, game results, dice/FAC logs and box scores are untouched. Joe Carter's Toronto-only five-year Peak 162 was verified from Lahman using **1991–1995**: 34 HR, 118 RBI and .802 OPS per 162 games. His genuine playable Hitter v0.5 conversion remains pending. No invented dice ratings or historical results.

## 2026-10-27 — Texas Rangers Rubén Sierra for Kenny Rogers (owner-approved)

Texas adds switch-hitting outfielder **Rubén Sierra** (`sierrru01`) as sixth bench hitter and backup RF/OF using only Rangers seasons **1986–1992, 2000–2001 and 2003**, excluding all other franchise performance. Kenny Rogers (`rogerke01`) becomes inactive in the bullpen, retaining his original genuine historical converted pitcher card. Darold Knowles takes RP6; Wetteland, Feliz, Zimmerman, Kern and Jeff Russell remain. The original nine hitters, **Corey Seager batting ninth at DH**, and all five starters are unchanged. Active 26: **9 lineup / 6 bench / 5 starters / 6 relievers**. All historical cards, played games, box scores, results and dice/FAC logs are preserved. Sierra's Texas-only five-year Peak 162 display is verified from Lahman for **1989–1992 plus 2000**, normalized to .292/.338/.477/.815 with 22 HR and 106 RBI per 162 games. His authentic Hitter v0.5 playable conversion is still pending. PED matters remain separate.

## 2026-10-27 — Milwaukee Brewers Ben Oglivie for Freddy Peralta (owner-approved)

Milwaukee's sixth bench hitter is Ben Oglivie (left-handed LF/corner-OF reserve) using **Milwaukee Brewers franchise statistics from 1978–1986 only**. Freddy Peralta leaves the active bullpen and retains his authentic original converted historical card. The six remaining relievers are Josh Hader, Devin Williams, Rollie Fingers, Dan Plesac, Ken Sanders and Jeremy Jeffress. All nine original starters, **Prince Fielder batting fourth at DH**, and the five-man rotation remain unchanged. Active roster **9/6/5/6**, 26 unique players. No historical cards, previously played games, dice/FAC logs, results or box scores were modified. Oglivie's Milwaukee-only five-year Peak 162 (1978–1982) is verified from Lahman; the playable genuine frozen Hitter v0.5 conversion remains pending. No invented card ratings or statistics. PED reviews remain separate.

## 2026-10-27 — Oakland Athletics Eric Chavez for Gene Nelson (owner-approved)

Eric Chavez joins Oakland's active bench as sixth hitter and left-handed defensive reserve 3B; only 1998–2010 Oakland Athletics franchise seasons may count. Gene Nelson leaves the active bullpen but his original authentic converted pitcher card remains historically archived. Honeycutt moves to relief slot 6; other relievers, starting pitchers and all nine starting hitters, including José Canseco batting fifth as DH, remain unchanged. Active 26 is 9 lineup/6 bench/5 SP/6 RP, 26 unique people. No PED eligibility changes authorized in this transaction; separate review remains pending. Original player cards, every previously played game, results, box scores, dice/FAC logs and archive are untouched. Chavez's genuine frozen Hitter v0.5 playable card remains pending without invented ratings.

## 2026-10-27 — New York Mets Howard Johnson for Sid Fernandez (owner-approved)

Howard Johnson is added as sixth Mets bench hitter and switch-hitting 3B/IF reserve using ONLY his 1985–1993 New York Mets performance, excluding every non-Mets season. Sid Fernandez is removed from the active bullpen with his historical genuine pitcher card preserved. Six remaining relievers stay unchanged: Billy Wagner, Edwin Díaz, Armando Benítez, Tug McGraw, John Franco and Jesse Orosco. The entire nine-hitter lineup (including Pete Alonso DH #6 and John Olerud bench #5) and five starting pitchers are unchanged. 9/6/5/6 = 26 unique active people. Every historical converted card, completed game, original FAC/dice log, score and box score remains untouched. Howard Johnson's genuine Hitter v0.5 conversion is pending; never invent playable card values.

## 2026-10-27 — Angels Rod Carew / Doug Corbett (owner-approved)

Rod Carew joins the Angels' active bench #6 as left-handed first-base reserve/pinch hitter, counting **only California Angels 1979–1985**, never Minnesota. Doug Corbett is inactive; his authentic historical converted card remains intact. Remaining six relievers: Troy Percival, Francisco Rodríguez, Scot Shields, Bryan Harvey, Scott Downs and Darren Oliver (RP1–RP6). All starting hitters, five SPs and **Shohei Ohtani at DH batting first** are unchanged. Canonical and announced sources now carry 9 lineup/6 bench/5 SP/6 RP, exactly 26 distinct players. Every original card, tournament result, played game, box score, and FAC/dice log remains unchanged. Carew's authentic Hitter v0.5 playable card remains pending conversion; no values fabricated.

## 2026-10-27 — Seattle Mariners Adrián Beltré for Mike Moore (owner-approved)

Seattle adds Adrián Beltré as sixth bench hitter / reserve 3B. Only 2005–2009 Seattle Mariners performance qualifies; no years with any other franchise are used. Mike Moore leaves the active bullpen but keeps his original archived pitching card. J.J. Putz, Andrés Muñoz, Edwin Díaz, Jeff Nelson, Arthur Rhodes, Kazuhiro Sasaki become relief slots 1–6 without changing their pitching responsibilities. The entire starting batting order and rotation are unchanged, including Edgar Martínez at DH batting fourth. 26 unique active players, with 9/6/5/6. Original cards and completed tournament games, FAC/dice logs, scores, box scores and results all remain intact; Beltré's frozen playable Hitter v0.5 conversion is pending, never invented.

## 2026-10-27 — Kansas City Royals Mayberry/Leibrandt and DH swap (owner-approved)

John Mayberry joins the Royals as sixth bench bat (LH 1B/PH; 1972–1977 Kansas City performance only) and Charlie Leibrandt leaves the active bullpen while retaining his original historical converted card. Danny Tartabull becomes lineup #2 starting DH, and Hal McRae moves to Tartabull's old bench #5 spot. The six remaining relievers are Quisenberry, Montgomery, Soria, Holland, Herrera and Mingori. Every other starting hitter and all five SPs stay in place. Kansas City now meets 9 lineup / 6 bench / 5 SP / 6 RP with 26 unique players. All original player cards, games, scores, original box scores and FAC/dice logs are preserved. Mayberry's authentic frozen Hitter v0.5 card remains pending, without invented ratings.

## 2026-10-27 — Philadelphia Athletics Foxx/Fain DH swap, Shantz for Barry (owner-approved)

Philadelphia Athletics #17: Jimmie Foxx moves to DH at batting slot 4; Ferris Fain to 1B at slot 9. Jack Barry leaves the active six-man bench but his original converted card remains historically preserved. Bobby Shantz becomes the sixth bullpen arm (left-handed long/swing). Count Shantz's Philadelphia Athletics 1949–1954 seasons exclusively, not Kansas City or his later career. Bishop becomes bench 5 and Valo bench 6. The roster is 9/6/5/6, 26 distinct people. The entire historical card catalog, games, box scores, original scores, FAC/dice rolls and outcomes remain intact. Shantz's authentic playable Pitcher v0.2.3 conversion is pending and must not be fabricated; Peak 162 is display-only and can reflect starter innings.

## 2026-10-27 — Houston Astros Moisés Alou for Octavio Dotel (owner-approved)

Houston adds Moisés Alou as its sixth bench bat (RH LF/RF), strictly using his **1998, 2000 and 2001 Houston Astros seasons**; Dotel leaves the active bullpen. Joe Sambito and Dave Smith move into relief positions 5 and 6, retaining their existing pitching functions. Houston now has 9 lineup hitters, 6 bench players, 5 starters, 6 relievers: 26 distinct active players. All original player card bodies, including Dotel's and Alou's unrelated Montreal card, and historical scores, games, box scores and original dice/FAC logs remain unchanged. No Hitter v0.5 ratings are invented; Astros Alou's playable conversion is pending.

## 2026-10-27 — Baltimore Orioles George Sisler for Sammy Stewart (owner-approved)

George Sisler is Baltimore's active sixth bench bat (LH 1B), based exclusively on his St. Louis Browns franchise seasons, 1915–1927. Sammy Stewart leaves the active bullpen; Olson, Britton, Bautista, Miller, Hall and Tippy Martinez remain in their existing slots. The active and official rosters and generated outputs are now 9/6/5/6, 26 unique active people. All original converted cards (including Stewart), earlier games, results, box scores and original dice/FAC records remain intact. Sisler's authentic Hitter v0.5 playable conversion is still pending; no invented ratings.

## 2026-10-27 — Chicago White Sox Dick Allen for Bob Locker (owner-approved)

Dick Allen joins Chicago as RH 1B/DH bench #6, replacing Bob Locker on the active 26. Dámaso Marte shifts to bullpen slot 5 and Eddie Cicotte remains the long/swing option at slot 6; all existing lineup and starting rotation roles are unchanged. Chicago's official, active and generated rosters follow 9/6/5/6. All original conversions, including Locker's, historical games, outcomes, box scores and dice/FAC archives are preserved. Allen's genuine Chicago-only Hitter v0.5 playable conversion is pending and no card ratings are fabricated.

## 2026-10-27 — Minnesota Twins Bob Allison for Firpo Marberry (Joe-approved)

Bob Allison becomes active Minnesota bench #6 (OF/1B RH power); Firpo Marberry leaves the active bullpen while his original converted card remains historical. Duran, Rogers and Perry shift to bullpen #4–6. The 26-player active team now follows 9/6/5/6, aligned in the official owner roster, active JSON, generated roster page, full-build adapter and validators. All original player cards, played games, box scores and original dice/FAC records remain intact. Allison's playable original Hitter v0.5 card remains pending a Senators/Twins-only conversion.

## 2026-10-27 — Philadelphia Phillies Chuck Klein for Ryan Madson (Joe-approved)

Chuck Klein joins the active 26 as RF/LF bench hitter #6 and Ryan Madson leaves active relief duty. Papelbon, Garber, McGraw, Reed, Lidge and Suárez remain, now numbered 1-6 in the bullpen. Starting lineup and rotation are untouched. The canonical roster, official owner roster, generator, roster document and validator now agree on 9/6/5/6. Madson's authentic original card remains in archived cards; no existing cards, tournament results, played games, FAC/dice logs or box scores were altered. Klein requires a genuine Phillies-franchise-only Hitter v0.5 card conversion; roster inclusion is not a playable card.

## 2026-10-27 — Pittsburgh Pirates Paul Waner for Al McBean (Joe-approved)

Paul Waner becomes the sixth bench bat (RF/LF, LH contact) while Al McBean moves off the active bullpen. Grant Jackson now occupies bullpen #5 and Sam Leever remains the long/swing option at bullpen #6. The Pirates active 26 are 9/6/5/6, synchronized in both current roster sources, generated roster output, rebuild adapter and validator. No historical cards (including McBean), games, box scores, original results or FAC/dice logs were edited. Paul Waner's genuine Pirates-only Hitter v0.5 conversion is pending; active roster inclusion does not invent a playable card.

## 2026-10-27 — Atlanta Braves Bob Horner for Mark Wohlers (Joe-approved)

Bob Horner becomes bench hitter #6 (RH power, third and first base coverage); Mark Wohlers becomes inactive. Phil Niekro remains in the long/emergency relief role at bullpen #6, with Jonny Venters moved to bullpen #5. Atlanta's active roster becomes 9/6/5/6, with only 26 distinct players. The original Braves cards, including Wohlers's converted pitching chart, remain stored unchanged; all completed games, box scores, scores and FAC/dice records remain unchanged. A genuine Braves-only Horner Hitter v0.5 conversion remains pending. Update is synchronized to all active roster sources and to the full-rebuild procedure.

## 2026-10-27 — Detroit Tigers Kirk Gibson for Tyler Holton (Joe-approved)

Kirk Gibson (OF/PR) becomes Detroit's bench6 hitter, Tyler Holton becomes inactive and the two surviving later relief roles are renumbered to RP5 Dizzy Trout / RP6 Denny McLain. Active 26: 9/6/5/6. Detroit's owner roster, converted active roster, rebuild adapter, website and validation are synchronized. Every R1-04 Detroit–Arizona game, authentic earlier card (including Holton), archived box score, manager log and dice/FAC sequence remains unchanged. Gibson's genuine Detroit-franchise-only Hitter v0.5 conversion remains pending, without fabricated card ratings.

## 2026-10-27 — Two-way players count once toward the active 26 (Joe-approved)

A player rostered as both hitter and pitcher counts **one unique person**, not two roster slots. Boston Babe Ruth remains bench hitter #6 and bullpen pitching option #7: the 27 entries in the team roster describe exactly 26 active distinct players. Both real hitter and pitcher roles remain available, subject to normal gameplay and fatigue rules. No Boston personnel changes, new ratings, historic cards, box scores, R1-03 results, or dice/FAC logs were touched. The roster schema, published rules, UI and validation now distinguish role entries from unique players.

## 2026-10-27 — San Francisco Giants Monte Irvin / Javier López roster switch (Joe-approved)

Following the completed R1-02 series, Monte Irvin replaces Javier López on the Giants active 26: Irvin is LF/bench6 and López is inactive. The roster now has 9 starting hitters, 6 bench players, 5 starting pitchers, and 6 relievers. Played games, card files, box scores, FAC/dice records, and historical relief appearances remain unchanged. The saved Giants converted cards are archived; Irvin's original playable Hitter v0.5 card with Giants-only franchise seasons remains pending conversion. The active roster validator and full rebuild adapter enforce the approved change.

## 2026-10-27 — Offline cache v54

The service worker cache is payoff-pitch-v54 so the ten new franchise-card clubs replace a cached roster or script. No game result was changed.

## 2026-10-27 — Empty-team cards, Mariners, Marlins, and Yankees (sandbox)

Seattle, Miami, and the Yankees now have playable cards for every active roster spot. The Marlins bench name is Otto Lopez. The Yankees bullpen name is Mike Stanton, the left-handed reliever. Josh Johnson is the Marlins rotation ace. Tanner Scott and Anthony Bender are the Marlins lefty and middle reliever. Babe Ruth is the Yankees DH, Reggie Jackson is the OF/BAT bench bat, Allie Reynolds is the long/swing reliever, Gary Sheffield is the Marlins DH, and A.J. Burnett is the long/emergency starter. The window rule is unchanged. Lahman stops at 2025. A 2026 line is included only from the MLB Stats API snapshot retrieved 2026-10-27. Cal Raleigh, Julio Rodríguez, Andrés Muñoz, Otto Lopez, Sandy Alcantara, and Anthony Bender take a 2026 season. Aaron Judge's 2026 line is 283 plate appearances, under the 300 floor, so it stays out. Tanner Scott's 2026 innings are with the Dodgers. Miami and New York have already played; the new card ids match the box scores, and no game result was changed. The active 26s are these converted rosters: A.J. Burnett and Mike Stanton stay active. Juan Pierre and Rickey Henderson are not on the active lists, and no card was invented for them. Fielding stays the engine Average default. Pitcher stamina and the set-file addenda are empty. The comparison is `historical-cards/accuracy/empty_teams_sea_mia_nyy.json`. The 2026 pull is `historical-cards/sources/mlb_2026_sea_mia_nyy.json`. The service worker cache stays payoff-pitch-v51.

## 2026-10-27 — Empty-team cards, Twins, Mets, Athletics, and Phillies (sandbox)

Minnesota, the Mets, Oakland, and Philadelphia now have playable cards for every active roster spot. The window rule is unchanged. Lahman stops at 2025. A 2026 line is included only from the MLB Stats API snapshot retrieved 2026-10-27. Byron Buxton, Taylor Rogers, and Bryce Harper take a 2026 season. Jhoan Duran's 2026 innings are with the Phillies, Pete Alonso's with the Orioles, Jeff McNeil's with the Athletics, Edwin Díaz's with the Dodgers, and Ranger Suárez's with the Red Sox, so those lines stay off these cards. Fielding stays the engine Average default. Pitcher stamina and the set-file addenda are empty. The comparison is `historical-cards/accuracy/empty_teams_min_nym_oak_phi.json`. The 2026 pull is `historical-cards/sources/mlb_2026_min_nym_oak_phi.json`. No game result was changed. The service worker cache stays payoff-pitch-v51.

## 2026-10-27 — Empty-team cards, Royals, Angels, and Brewers (sandbox)

Kansas City, Los Angeles, and Milwaukee now have playable cards for every active roster spot. The window rule is the same as the Baltimore group: five best franchise seasons by one-decimal league OPS+ for hitters (at least 300 plate appearances) and by one-decimal ERA+ times innings for pitchers (100 innings in the rotation, 30 in the bullpen). Lahman stops at 2025. A 2026 line is included only from the MLB Stats API snapshot retrieved 2026-10-27. Bobby Witt Jr., William Contreras, and Brice Turang take a 2026 season. Salvador Pérez, Mike Trout, Christian Yelich, and Brandon Woodruff were checked and stay on earlier seasons. Devin Williams' 2026 innings are with the Mets, and Freddy Peralta's are with the Mets and Rays, so neither 2026 line is on the Brewers card. Fielding stays the engine Average default. Pitcher stamina and the set-file addenda are empty. The comparison is `historical-cards/accuracy/empty_teams_kc_laa_mil.json`. The 2026 pull is `historical-cards/sources/mlb_2026_kc_laa_mil.json`. No game result was changed. The service worker cache stays payoff-pitch-v51.

## 2026-10-27 — Empty-team cards, first batch (sandbox)

Baltimore, Cleveland, the White Sox, and Houston now have playable cards for every active roster spot. Hitters use the five best franchise seasons by one-decimal league OPS+, at least 300 plate appearances. Pitchers use the five best franchise seasons by one-decimal ERA+ times innings, with a 100-inning floor for the rotation and a 30-inning floor for the bullpen. A 2026 line is included only when the MLB Stats API, retrieved 2026-10-27, has a season split for that franchise. Lahman in this repo stops at 2025. Yordan Alvarez, Jeremy Peña, Cade Smith, and Josh Hader are the cards that take a 2026 season. Fielding stays the engine Average default. Pitcher stamina and the set-file addenda are empty. The comparison is `historical-cards/accuracy/empty_teams_batch.json`. The 2026 pull is `historical-cards/sources/mlb_2026_batch.json`. Miami and the Yankees are not built. No game result was changed. The service worker cache is payoff-pitch-v51.

## 2026-10-27 — Five missing hitter cards (sandbox)

David Peralta, Moises Alou, Brian Giles, Aubrey Huff, and Elmer Valo now have playable hitter cards. Each window is the five best franchise seasons by one-decimal league OPS+, among seasons of at least 300 plate appearances. Plate appearances are AB + BB + HBP + SF. Peralta is 2014, 2015, 2018, 2019, and 2022, Arizona only. Alou is 1992–1996. Giles is 2004–2008. Huff is 2001–2005. Valo is 1946, 1947, 1948, 1951, and 1952. Fielding stays the engine Average default. Valo's intentional walks and sacrifice flies are unrecorded in Lahman and stored as zero. No 2026 line was added. The comparison is `historical-cards/accuracy/missing_hitters.json`. The service worker cache is payoff-pitch-v50. No game result was changed.

## 2026-10-27 — Old-method dice refit (sandbox)

The 252 converted-roster cards whose windows did not change now use the same solver as the 215. That is 120 hitters and 132 pitchers, 251 cards, because Babe Ruth is both. Windows, peak lines, fielding, stamina, and the tournament block stay. Hitter dice include doubles and triples in the objective, and a DEFENSE roll uses the rulebook position check. Pitcher charts use the page-39 shift on TOUGH only. The four missing hitters and Elmer Valo's placeholder were not filled. No game result was changed. The per-card comparison is `historical-cards/accuracy/rebuild_252.json`. The service worker cache is payoff-pitch-v48.

## 2026-10-27 — Window-card dice refit

The 215 cards whose peak window changed have new dice and pitching charts. Doubles and triples follow the 1986 card shapes, and a DEFENSE roll is a position check against a neutral fielder and the 1986 park charts rather than an automatic out. A reached-on-error is an at-bat and not a hit. Fielding, stamina, and peak lines stay as they were. A game import still refreshes only the tournament block on each card. The service worker cache is payoff-pitch-v47. No game result was changed.

## 2026-10-27 — Card repairs kept after Game 2

R1-05 Game 2 rebuilt the converted cards from the set files and put the old windows and dice back. The repairs are on the cards again, and the Game 2 tournament lines stay. DH slots are labeled again. The service worker cache is payoff-pitch-v41. No game result was changed.

## 2026-10-27 — Card windows, dice, and DH labels

Hitter dice on the converted clubs cover 01–99. A band that ran past 99 keeps only the open faces, and a face left out of both the result bands and the out table is an out. Franchise windows are the five best seasons under the same one-decimal rule used for Colorado and St. Louis, with a verified 2026 MLB line included when the player played for that franchise. The raw counting line and the 162-game scale come from those seasons. Shane McClanahan's card id is `mcclash01`. Played games still store `mcclasha01`, and the viewer opens the same player from either id. Where an owner card names a DH, that lineup slot is labeled DH and the carded position is unchanged. Arizona, Boston, San Francisco, Tampa Bay, and Washington have no owner DH, so no slot was guessed. Bill Mazeroski's fifth season, 1964 or 1966, is still open. The R1-05 game file had regenerated the Rockies and Cardinals cards; those repairs are restored, and Kyle Freeland's 2026 season does not enter his window. No game result was changed. The printed dice on a card whose seasons changed still need a frozen-engine rebuild. The service worker cache is payoff-pitch-v40.

## 2026-10-26 — New York Yankees synchronized, Rickey Henderson for Mike Stanton (Joe-approved)

Rickey Henderson takes the Yankees' sixth bench spot (OF/PR) and Mike Stanton is inactive, leaving 9 lineup / 6 bench / 5 starters / 6 bullpen. All four played R1-01 Yankees–Marlins games, box scores, manager logs, FAC/dice sequences, original converted cards, and Stanton's historical appearances remain unchanged. The full Yankees active roster is synchronized to the current `data/rosters.json` schema and the printed owner roster is amended. A future card rebuild preserves NYY's active 26 and **all** historical NYY card bodies without inventing missing cards. Rickey's five-season Yankees-only peak (1985–1989) and playable Hitter v0.5 conversion are pending.

## 2026-10-26 — Miami Marlins roster synchronized and approved 6/6

Joe approved adding Juan Pierre to the sixth bench slot and moving A.J. Burnett off the active bullpen. The official Marlins roster and `data/rosters.json` now agree on 9 starting hitters, 6 bench, 5 starting pitchers and 6 relievers. Historical tournament results, cards, box scores and game logs remain untouched, including Burnett's recorded R1-01 appearance. The five bench players already approved in the published roster remain, with Juan Pierre added as a pinch-running CF. Miami is a roster-only synchronization until all original Payoff Pitch cards have been converted. The owner roster's surname-only utility `Lopez` is represented provisionally as Otto Lopez for the active roster; this identity requires confirmation before original card conversion. A future full build retains Miami's roster and all preexisting Miami cards (including archived inactive pitchers).

## 2026-10-26 — Washington Nationals 6/6 active roster (Joe-approved)

Jayson Werth joins bench OF6 and Craig Stammen leaves the active bullpen. Washington now has 9 lineup, 6 bench, 5 rotation, 6 bullpen (26 total). The approval applies only to games after the completed R1-02 series. Stammen's historical converted card and all prior pitching appearances, played lineups, box scores, FAC/dice logs, and official game/series results are preserved exactly as recorded. Werth's original Hitter v0.5 conversion remains Joe's responsibility, using Nationals-franchise stats only; no guessed playable ratings were added. Rebuild and validator safeguards record the new active roster without erasing history.

## 2026-10-26 — Tampa Bay Rays 6/6 active roster (Joe-approved)

Aubrey Huff joins bench OF6 and Kevin Kelly leaves the Rays' active 26. J.P. Howell moves from the seventh to sixth active relief slot, leaving nine starting hitters, six bench players, five starting pitchers, and six relievers. The change applies only **after the completed R1-03 Boston series**. Keep every original box score, FAC/dice record, bullpen appearance, game outcome, and Kelly's genuine converted card in historical data; neither cards nor tournament results have been rewritten. Huff's original frozen Hitter v0.5 card and his Rays-only five-season peak line are pending Joe's conversion. No unverified card or peak statistics have been fabricated.

## 2026-10-26 — Arizona Diamondbacks 6/6 active roster (Joe-approved)

David Peralta (LF, left-handed bat) becomes Arizona's sixth bench player and Juan Cruz leaves its active bullpen. The Diamondbacks retain 26 active players: nine lineup, six bench, five starters, six relievers. Their six completed R1-04 games are historical records, so Cruz's pitching appearances, original converted card, box scores, and dice/FAC history are left intact. The swap applies only to future tournament games. Peralta's Hitter v0.5 conversion is to be supplied by Joe, not fabricated; his future card and peak must use Diamondbacks seasons only. Other clubs and official results are unchanged.

## 2026-10-26 — Montreal Expos 6/6 active roster (Joe-approved)

Moisés Alou takes bench OF6 and Jeff Fassero leaves the active 26. Montreal now has nine in the lineup, six on the bench, five starters and six relievers. Fassero's original Payoff Pitch card stays in the archive as historical, inactive data. Alou's Hitter v0.5 card is not yet converted and will be handled by Joe; no simulated card ratings were invented. His Montreal-only Peak 162 window is 1992–1996 rather than including his brief 1990 Expos cameo. All recorded tournament games, cards for other active players, and other clubs are unchanged.

## 2026-10-26 — Rockies and Cardinals card repairs

Colorado and St. Louis hitter dice now cover 01–99. A band that ran past 99 keeps only the open faces, and a face left out of both the result bands and the out table is an out. Ten hitters and seven pitchers use a new franchise window. The raw counting line and the 162-game scale come from those seasons. The printed dice on those seventeen cards stay the repaired chart until a frozen-engine rebuild. Andres Galarraga and Enos Slaughter bat in the DH slot. Their cards stay first base and right field. Larry Walker's right field is range C and arm 6. Trevor Story's and Yadier Molina's arms are 7. Garrett Hampson also plays second base. Al Brazle is bullpen-only. Jason Isringhausen's owner slot is SU3. No game result was changed. The service worker cache is payoff-pitch-v39.

## 2026-10-26 — Milestone feed

The home page, the Results page, and each player page list feats from the box scores: a cycle, a shutout, a complete game, a multi-home-run game, a four-hit game, a game of 10 or more strikeouts, and a no-hitter. A complete game is a start that recorded every out for that club. A shutout is that complete game with no runs allowed. A combined shutout names every pitcher who recorded an out. No cycle is on the book. The definitions are on the Formulas page. The lines wrap on a phone. A new game is on the list when it is in the archive. The service worker cache is payoff-pitch-v38. No game result was changed.

## 2026-10-26 — Team batting and pitching

The Team stats page sums each club's batting and pitching lines from the box scores. Batting is ranked by OPS. Pitching is ranked by ERA, lowest first. A club with no game is listed as not played yet. The rates are on the Formulas page. Each club page links to its line. The rows stay on a phone. A new game moves the ranks when it is in the archive. The service worker cache is payoff-pitch-v37. No game result was changed.

## 2026-10-26 — Awards race on a phone

The Awards page ranks tournament MVP, Cy Young, and reliever points from the box scores. MVP is total bases + R + RBI + SB + 0.5×BB + 0.5×HBP − CS. Cy Young, for a pitcher with a start, is IP + 0.4×K + 5×W − 1.5×ER − 0.3×BB. The formula is on the Formulas page and in MODELS.md. Each row keeps the name, the club, the points, and the counting line on a phone. The list is the top 15, and a tie at the fifteenth line stays. A new game moves the race when it is in the archive. The service worker cache is payoff-pitch-v36. No game result was changed.

## 2026-10-26 — Flexible 26-man roster composition (Joe's Issue 5 ruling)

Joe approved allowing different bench and bullpen sizes by club, and allowing owner-approved roster adjustments during the tournament. Every club must keep 26 active players, with nine lineup spots and five scheduled starters; the usual five-man bench and seven-man bullpen is only the default. The current Dodgers, Cubs, Guardians, Reds, Cardinals, and Philadelphia Athletics roster distributions are valid as published. Future changes require Joe's approval and a dated amendment, effective only for future games. This ruling did not change any player, card, seed, lineup already played, or tournament result. See [TOURNAMENT_RULES.md](TOURNAMENT_RULES.md).

## 2026-10-26 — San Diego Padres 6/6 active roster (Joe-approved)

Brian Giles joins the bench as OF6; Craig Lefferts leaves the active 26. The Padres now carry nine lineup spots, six bench players, five scheduled starters, and six relievers. Lefferts' existing converted Payoff Pitch card remains available as **historical, inactive data**. Giles' hitter conversion is Joe's responsibility, and no guessed ratings or counterfeit card are published; his card is pending. Any Peak 162 display must use **Padres-franchise statistics only**. San Diego has not played an official tournament game, and all other teams, cards and recorded results are unchanged. This roster amendment supports the club-by-club transition toward 6/6.

## 2026-10-26 — Results timeline

The Results page is a day-by-day scoreboard of every game on the book. Each day lists the games played that day, with the club logos, the final score, and a link to the game. Games with no stored date sit after the dated days. The layout stays on a phone. The service worker cache is payoff-pitch-v32. No game result was changed.

## 2026-10-26 — Player game logs

A player page lists one row for each tournament game. Batting shows AB, R, H, 2B, 3B, HR, RBI, BB, SO, and SB. Pitching shows IP, H, R, ER, BB, K, and the stored decision. The date and the opponent sit in the first cell, and the row links to the game. A game with no date says so. The columns stay on a phone. The service worker cache is payoff-pitch-v31. No game result was changed.

## 2026-10-26 — Single-game records

The Records page lists one-game highs from the box scores: hits, home runs, runs batted in, total bases, runs, stolen bases, walks, pitcher strikeouts, and innings. Each list is the top 10, and a tie at the tenth line stays. The row uses the club logo and color, links the player, and links the game. The tables keep the full name on a phone. The milestone lists stay. The service worker cache is payoff-pitch-v30. No game result was changed.

## 2026-10-26 — Inbox import rebuild

An inbox import now rebuilds the Peak 162 file, the roster page, the leaders and feeds, the series-preview images, and the bracket image, the same commands the site workflow runs. A pushed game then passes that workflow's generated-file check. The service worker cache is payoff-pitch-v29. No game result was changed.

## 2026-10-26 — Clemens ERA

Roger Clemens allowed 2 earned runs in 48 outs, 16.0 innings. ERA is 27 × 2 / 48 = 1.125. Baseball-Reference rounds a half hundredth to the even hundredth, so the printed ERA is 1.12. The leaders page and the player page had been rounding that half up to 1.13. Carl Hubbell, 1 earned run in 8.0 innings, is the same 1.125 and now prints 1.12 as well. The innings and the earned runs were not changed. WHIP still rounds half up. The service worker cache is payoff-pitch-v28.

## 2026-10-26 — Boston series dates

Joe ruled that every game of R1-03, Boston against Tampa Bay, was played on 2026-10-23. All seven game dates are that day. Games 1 and 2 had been 2026-10-24, and Games 3 through 7 had no date. Scores, lines, and decisions are unchanged. The service worker cache is payoff-pitch-v27.

## 2026-10-26 — Peak 162 series projections

An upcoming or in-progress series shows a projection on the bracket and on the series preview. Offense is the mean Peak 162 OPS of the owner lineup. Pitching is the mean Peak 162 ERA of the owner rotation. One game is the log5 of the two Pythagorean win percentages, and the series chance is the best of 7 from the wins already stored. The line is labeled Projection. A club without an announced roster says Odds TBD. The projection is for the pairing as it stands, and the next round is projected again after the re-seed. The formula is on the Formulas page and in MODELS.md. The service worker cache is payoff-pitch-v26. No game result was changed.

## 2026-10-26 — Tournament leaders page

The Leaders page lists the top 10 from the played games: batting average, home runs, runs batted in, hits, runs, stolen bases, and OPS, then earned run average, WHIP, wins, strikeouts, and saves. Rate hitting needs 10 plate appearances. Rate pitching needs 5 innings. A tie at the tenth place stays on the list. Each row uses the club logo and color and links to the player page. The numbers are the same book as [LEADERS.md](LEADERS.md), counted in the browser from the loaded games, so a game that is pushed is on the board when the site updates. OPS is on-base percentage plus slugging. The service worker cache is payoff-pitch-v25. No game result was changed.

## 2026-10-26 — Series MVP from the box scores

A finished series now names a series MVP from the games in that series. A hitter uses the awards MVP line. A pitcher uses IP + 0.4×K + 5×W + 3×SV − 1.5×ER − 0.3×BB, with wins and saves taken from the stored decisions. A player who both hit and pitched keeps the higher score. The formula is in [MODELS.md](MODELS.md) and on the Formulas page. The name is on the series page and on the bracket card. A name already stored in the series file is left in the file and is still shown when it differs. No game result was changed. The service worker cache is payoff-pitch-v24.

## 2026-10-26 — Head to head

The Head to head page compares any two clubs, lineup spot by lineup spot. An owner card is used when one is stored. Otherwise the converted lineup is used, with the peak line taken from that card. A club with neither says "Roster not announced yet." No player or stat is added. The service worker cache is payoff-pitch-v23. No game result was changed.

## 2026-10-26 — Bracket image

The build writes `graphics/bracket.png`, 1200 by 1500. The title is Payoff Pitch Tournament 32. A finished series puts the winner in gold with a WIN tag and dims the loser. A series that is scheduled or in progress is labeled UPCOMING. The footer says "All rounds will be re-seeded." The image has no site address. The bracket page links it as Download bracket image. The service worker cache is payoff-pitch-v22. No game result was changed.

## 2026-10-26 — Series lineup previews

Each scheduled series with both clubs named has a lineup preview. The two owner lineups sit side by side, with the stored Peak 162 line under each name. The leader is the lineup hitter with the highest OPS on that line. The starter is the rotation arm with the lowest ERA on his. A club without an owner card says "Roster not announced yet." The build writes a 1200 by 1500 PNG for each of those series, and the page has a Download image link. The service worker cache is payoff-pitch-v21. No game result was changed.

## 2026-10-26 — Classic cap logos

Every club on the team page and the bracket shows a real cap logo. The marks already in the repo stay for the clubs that had a 1986 file, except Cleveland: the field club is the Guardians, so the Indians cap is replaced by the Guardians cap. Miami, Tampa Bay, Arizona, Colorado, Washington, and the Philadelphia Athletics had monograms. Those are now real cap logos. Sources are in [CREDITS.md](CREDITS.md). The service worker cache is payoff-pitch-v20. No game result was changed.

## 2026-10-26 — Club colors on the team page and the bracket

Each club in the 32-team field has a primary and a secondary color in `data/team_colors.json`, matched to the club as it is named in the field. Los Angeles is Dodger blue, Montreal is the Expos tricolor, the Philadelphia Athletics are navy, Oakland is green and gold, Cleveland is the Guardians' navy and red, and Miami is black and blue. The team-page header sits on the primary color, with light or dark text chosen by contrast. Roster slot chips use the same pair. On the bracket, a club row keeps a color bar and a swatch, and the name takes a team color only when that color stays readable on the card. Winners stay in the site's winner color. The gold theme is unchanged, and the same rules hold in dark mode. The service worker cache is payoff-pitch-v19. No game result was changed.

## 2026-10-26 — Payoff Pitch cards fit a phone

On a phone, a player card keeps the percentile bands on the screen. The result column is narrow, the hand columns read vs L and vs R, and the band numbers stay in view. Hitter and pitcher attributes sit in label chips, two to a row. Each fielding spot is the position plus range, error, and arm. The pitcher 2d6 line is a two-column grid. Wider screens still show vs LHP and vs RHP and a wrapping chip row. The service worker cache is payoff-pitch-v18. No card number and no game result was changed.

## 2026-10-26 — Roster tables fit a phone

Team-page lineup, bench, rotation, and bullpen tables keep a narrow left-aligned slot, a wrapping player name, and a compact position. The hand, the years on the owner card, and the Peak 162 line stack under the name. Converted Payoff Pitch cards use the same layout. Nothing in the tables runs off the side of a phone. The service worker cache is payoff-pitch-v11. No roster line and no game result was changed.

## 2026-10-26 — Site cleanups

The Players page now says converted cards exist for eleven clubs (ARI, BOS, CHC, COL, DET, MON, PHA, SF, STL, TB, WSH), including the Rockies and Cardinals sets, and that every club's roster is on its team page. On a club that has both an owner card and a converted set, the owner card is the list and the converted set is behind a Payoff Pitch cards toggle. Peak lines use one label, `Peak 162 with <club> (YYYY–YYYY)`, and one note. About and Formulas are pages in the site. The walkthrough video link is gone. `data/cards.json` and `data/peak162.json` load when opened, and they are out of the service worker install cache (`payoff-pitch-v10`). `scripts/split_game_detail.py` is removed. The Philadelphia roster, the 25 owner cards, and the waiting-on-a-graphic note are closed. Open questions are gathered in [TOURNAMENT_RULES.md](TOURNAMENT_RULES.md). No game result was changed.

## 2026-10-25 — St. Louis Cardinals converted set joins; bench BAT chair corrected to Mark McGwire (Joe's ruling)

The St. Louis Cardinals' converted Payoff Pitch set joins the site: 26 players with peak lines shown as 162-game averages and converted cards, and no tournament lines, because St. Louis has not played a series yet. Eleven clubs now have converted sets, 286 players and 287 roster spots in `data/cards.json` and `data/rosters.json`; the 112 players with tournament lines are unchanged. `scripts/build_cards.py` gained the one SETS row for the club. The set's audit stands at 15 PASS and 11 architecture-limited of 26, its engineered battery's three games all audit clean, and its sampled stress test returns PLAYS TRUE for all three tested hitters; the full build report lives in the payoff-pitch-cardinals set folder.

The Cardinals' announced roster is also corrected to the governing roster: the bench BAT chair is Mark McGwire, per Joe's 2026-10-23 ruling ("Make all changes with recommendations but keep Nichols"), confirmed by Joe on 2026-10-25, and Tip O'Neill is out of the 26. The correction is made in `data/announced_rosters.json` and `ROSTERS.md`, and `data/peak162.json` is regenerated from the corrected roster, so O'Neill's peak line is replaced by McGwire's. The same correction pattern was used for the Cubs' Dawson chair earlier today.

The 2026 check for this set, under Joe's rule that the completed 2026 season counts in prime windows: the only rostered Cardinal who appeared in 2026 was Ryan Helsley, and he pitched for Baltimore, so no St. Louis window takes a 2026 season and every window in the set stands as computed from St. Louis seasons only.

No game, series, or locked line changed: the tournament archive still holds 22 games. The validator passes with no re-lock, a second generator run is a zero diff, and the service worker cache moved to payoff-pitch-v9 for the updated data files.

## 2026-10-25 — Colorado Rockies converted set joins; 2026 seasons counted in prime windows (Joe's rule)

Two changes land in one regeneration. First, the Colorado Rockies' converted Payoff Pitch set joins the site: 26 players with peak lines shown as 162-game averages and converted cards, and no tournament lines, because Colorado has not played a series yet. Ten clubs now have converted sets, 260 players and 261 roster spots in `data/cards.json` and `data/rosters.json`; the 112 players with tournament lines are unchanged. `scripts/build_cards.py` gained the one SETS row for the club.

Second, Joe's rule of 2026-10-25 ("Yes any active player can use 2026 season is over") is applied across the converted sets: any active player's prime window is computed with the completed 2026 season counting like any other season, franchise seasons only. Twelve windows changed and their cards were rebuilt under the frozen engines: Washington (Keibert Ruiz, CJ Abrams, James Wood), Tampa Bay (Yandy Díaz, Junior Caminero, Shane McClanahan, Kevin Kelly), Detroit (Tyler Holton), and Arizona (Corbin Carroll, Ketel Marte, Gabriel Moreno, Geraldo Perdomo). Pete Crow-Armstrong's identical rebuild for Chicago landed earlier the same day. Each rebuilt player's page now shows the new window years and the new 162-game peak line; the set folders carry the dated amendment in each SET_REPORT.md with old and new fits. Players whose 2026 was played for another club do not count it for their set, and every other card is byte-identical.

No game, series, or locked line changed: the tournament archive still holds 22 games, and the games already played with the old cards stand as played. The validator passes with no re-lock, a second generator run is a zero diff, and the service worker cache moved to payoff-pitch-v8 for the updated data files.

## 2026-10-25 — Chicago Cubs converted set joins; bench chair corrected

The Chicago Cubs' converted Payoff Pitch set is on the site: 26 players (15 hitters, 11 pitchers) with peak lines shown as 162-game averages, converted cards, and the tournament state stated plainly, because Chicago has not played a series yet. Nine clubs now have converted sets, 234 players and 235 roster spots in `data/cards.json` and `data/rosters.json`; the 112 players with tournament lines are unchanged. The set was built to the standing conversion standard (frozen engines, v2 pitcher cards, pitcher addendum) in the workspace; its own reports live with the set. `scripts/build_cards.py` gained the one SETS row and the Lahman team-games id for the club (CHN).

The owner's announced Cubs card is corrected in the same commit. Joe's rulings of 2026-10-23, confirmed 2026-10-25, put Andre Dawson in the bench outfield chair: `data/announced_rosters.json` and `ROSTERS.md` now list Dawson on the bench, Jimmy Ryan is off the 26, and Dawson no longer appears in the honorable mentions. `data/peak162.json` was regenerated to match. Frank Chance is the recorded manager; his manager profile is a separate build and is not part of this change.

No game, series, or locked line changed, and the validator passes with its fingerprint, frozen-series hash, and counting totals unchanged. The service worker cache moved to payoff-pitch-v7 for the updated data files.

## 2026-10-26 — Converted cards sit beside the owner rosters

Main's converted Payoff Pitch sets and player cards are on the same site as the owner's announced cards and the franchise Peak 162 lines. A club with a converted set shows that set. A club with an owner card shows that card. Detroit shows both, plus the game lines already on the book. Washington keeps the converted set and the game record; the Nationals owner card stays off. No game result was changed. The service worker cache is payoff-pitch-v6 so both sets of data files are in the shell.

## 2026-10-25 — Owner cards for the remaining clubs, and Peak 162

The owner's second set of cards is in `data/announced_rosters.json` with the first nine. Montreal maps to the Expos. Cleveland maps to the Guardians. The Twins card includes the 1901–1960 Senators. The Philadelphia Athletics card is separate from Oakland. Connie Mack's lineup spot 9 is Ferris Fain at DH. Lefty Grove stays the first starter only, and Fain is not on the bench. Benches and bullpens that list six names are kept at six. Honorable mentions and the what-if lines are separate and are not on the active roster.

The Nationals card was not applied. Washington has already played, as have the Yankees, Giants, Red Sox, Rays, Diamondbacks, and Marlins. Those pages are unchanged. Detroit has played, and the owner's Tigers card is shown beside the existing game lines. No game result was changed.

Peak 162 on each of those cards is a Major League franchise line from the 2025 Lahman database, through the 2025 season. The formula is in [MODELS.md](MODELS.md). A player who cannot be matched says "Peak stats unavailable."

## 2026-10-25 — Official rosters for nine clubs

The tournament owner supplied rosters for the Rockies, Dodgers, Padres, Angels, Astros, Athletics, Mariners, Rangers, and Braves. They are stored in `data/announced_rosters.json` and shown on those team pages and in `ROSTERS.md`. The Rockies manager is Bud Black. Names and accents are copied as given. No graphic cards, bios, or counting stats were added. The other clubs that have not played still say "Roster not announced yet." No game result was changed.

## 2026-10-25 — Peak lines shown as 162-game averages

Joe's call: the peak section on each player page now shows a 162-game average of the prime years instead of the multi-season window totals. The raw window totals stay in `data/cards.json` as `peak_bat` and `peak_pit`, untouched: they are the card's build line, and the viewer still computes AVG, OBP, SLG, and ERA from them, so every rate on the page is the window's own and has not moved. What changed is the counting line beside the rates, in new `peak_bat_162` and `peak_pit_162` blocks written by `scripts/build_cards.py`; the method is documented in the script header and in [SCHEMA.md](SCHEMA.md).

Batters scale by 162 / window games, rounded half up, with games shown as 162. Harry Heilmann is the shape of it: his 1921, 1923, 1924, 1925, and 1927 window (737 games, a .386/.456/.590 line) now reads as 162 games, 688 PA, 610 AB, 120 runs, 235 hits, 49 doubles, 13 triples, 16 homers, 137 RBI, 76 walks, and 35 strikeouts, at the same .386/.456/.590. Pitchers become an average season on a 162-game schedule: the per-season average rescaled by (162 x window seasons) / the club's total team games across the window seasons, from the Lahman Teams table. Hal Newhouser's 1944-48 window ran against 778 Detroit team games, so his line now reads 25-12 with a 2.35 ERA over 307.1 innings and 207 strikeouts instead of the five-season bulk. Innings are scaled in outs and rendered back in thirds. A window season with no Lahman row for the club counts as 162 team games and would be named in the generator's log; no window season needed the fallback in this build. No game, series, tournament line, or card changed, and the validator's fingerprint, frozen-series hash, and counting totals are unchanged. The service worker cache moved to payoff-pitch-v5 for the updated viewer and data.

## 2026-10-25 — Player cards and rosters

The viewer gained a Rosters view and, on each converted club's page, the full roster in set order. Eight clubs have converted Payoff Pitch sets: Boston, Philadelphia, San Francisco, Montreal, Washington, Tampa Bay, Detroit, and Arizona, 208 players and 209 roster spots (Babe Ruth holds two Boston spots, bench bat and bullpen arm, and his player page shows both of his cards). Each player page now shows his peak prime-window line, the line his converted card was built from, and the card itself: for hitters the positions with range, error, and arm, the four result sections as percentile bands against each hand, the out table, and the run, steal, and bunt ratings the card prints; for pitchers the v2 card's 2d6 section table, strikeout modifier, special ratings, stamina line, and addendum ratings. The tournament tables on the same page are headed "Tournament batting" and "Tournament pitching" and now carry games, OBP, and SLG for hitters and games, runs, and home runs for pitchers, all from the same archive lines. 112 of the 208 players have tournament lines. Philadelphia and Montreal have not played a series, so their players show peak lines and cards with that stated.

`scripts/build_cards.py` generates `data/rosters.json` and `data/cards.json` from the set files and the master archive; its header documents the inputs and how a future converted set joins. Player identity keys on the Lahman id from the set inputs, except where this site already publishes the same player under a different id: Shane McClanahan is `mcclash01` in the inputs and the master archive and `mcclasha01` here, so the card data keys on the published id and his tournament line, matched by name, is intact. The locked series are untouched: no game, series, or line changed, and the validator's fingerprint, frozen-series hash, and counting totals are unchanged. The service worker cache moved to payoff-pitch-v4 for the new data files.

## 2026-10-25 — R1-04 complete, Detroit 4-2

Opening Round Series 4 was played in Payoff Pitch on 2026-10-25 and recorded from the series' saved state files in the master archive. The six games sum to the series totals in the series summary: Detroit 25 runs and 49 hits, Arizona 14 runs and 42 hits. Arizona took the first two games in Detroit, Game 2 in thirteen innings. Detroit won the last four after Joe's lineup ruling started Harry Heilmann in left field in Bobby Veach's slot for Games 3 through 6. Detroit is 1-0 on the winners side. Arizona is 0-1 on the losers side and is not eliminated. Series MVP is Harry Heilmann. Runner-up is George Kell.

Game 5 was played twice. The first playing, an 8-5 Arizona win, was set aside by Joe's ruling after he had the game played fresh from scratch; the fresh re-play, a 3-1 Detroit win, is the official Game 5 here. The superseded playing is preserved in the series' own files outside this repo and is not in this archive.

Unlike R1-03 Games 3-7, these games come with their full record. Each detail file stores the complete FAC roll log and manager log from the state files, and each summary carries the fatigue end states, caps, and scoring plays. All six games are dated 2026-10-25, the day they were played; `scripts/split_game_detail.py` gained R1-04 in its dated-series map so the date survives a re-split. Detroit home games were played on the 1986 Tiger Stadium park card under Joe's ruling; Arizona home games on the standard composite park he accepted. No locked game, series, or line was changed: R1-01, R1-02, and R1-03 stay exactly as stored, and the validator's locked fingerprint, frozen-series hash, and counting totals are unchanged because they cover the locked games only.

## 2026-10-25 — Win probability, daily highlight, scorecards

Each game page charts a home win-probability estimate from the inning line. The formula is in [MODELS.md](MODELS.md). The chart says it is a model estimate. A game with no inning line has no chart. Stored scoring plays are used for the finer steps when they add up to the final score. The home page shows one recorded moment for the calendar date: a no-hitter, a 10-strikeout game, a walk-off, a 10-run game, or a finished series. The same date always shows the same moment. `scripts/build_leaders.py` writes a PDF scorecard for every game. That step needs the packages in `requirements.txt` (`fpdf2`). The Actions workflows install them. Each game page has a Print / Save as PDF button. No score, line, or series result was changed.

## 2026-10-25 — Inbox import, derived stats, history

The videos hub, its nav link, `videos.json`, and the video blocks on game and series pages were removed. The walkthrough link in the header stays. The install notes no longer describe an Android wrapper. The installable page is unchanged.

`scripts/import_game.py` reads a CSV or a markdown box score, including a whole series file in the R1-03 layout. `inbox/` is the drop folder. The Inbox import workflow applies new games, runs the validator, regenerates the pages, commits, and deploys. A bad file stays in `inbox/` and the reason is written to `inbox/errors/`. Games already on the book are not rewritten. R1-01, R1-02, and R1-03 stay locked.

After a deploy, the site workflow can post a new final to Discord and to X. It does that only when `DISCORD_WEBHOOK_URL` or the `X_*` secrets are set. No secret is stored in the repo. Setup is in [ADDING_GAMES.md](ADDING_GAMES.md).

The stats page counts hit streaks, pitcher workload, club splits, head-to-head results, and batter-versus-pitcher plate appearances where a roll log names the batter. The history page lists series results and milestones from the box scores, then the rulings in this file. No score, line, or series result was changed.

## 2026-10-25 — R1-03 complete, Boston 4-3

Joe's official box scores closed Opening Round Series 3. Games 1 and 2 already in the archive match those box scores on the site, the linescore, the decisions, and every batting and pitching line. Games 3 through 7 were added in the same shape. The seven games sum to the series totals in the series summary: Boston 27 runs and 53 hits, Tampa Bay 17 runs and 35 hits, and the player batting and pitching tables. Boston is 1-0 on the winners side. Tampa Bay is 0-1 on the losers side and is not eliminated. Series MVP is Roger Clemens. Runner-up is Jimmie Foxx.

Games 3-7 have no per-game calendar date in the box scores, so the date is null. Games 1-2 stay 2026-10-24. The series summary dates the series to October 24 and 25, 2026, without assigning the later games to a day. The box scores also do not include the roll log, so those five detail files store an empty `rolls` array. The win-probability chart for those games steps through the linescore. Tampa Bay's plate appearances are one short of Boston's batters faced, which the series summary already notes: Toby Hall's Game 5 catcher's interference is a plate appearance the batting line does not carry. The published batting table and the box scores agree with each other. That one-plate gap was not filled in. The series summary prints Clemens's ERA as 1.12. Sixteen innings and two earned runs are 1.125, and this archive rounds that half up to 1.13, the same rule already used for Hubbell. The 16.0 innings and two earned runs were not changed.

## 2026-10-25 — Sharing, logos, and the installable site

The viewer gained a compact phone header, static share pages under `share/`, Open Graph images, Monte Carlo series and title odds in `feed/odds.json`, matchup previews, a weekly recap, an in-site game form, and a service worker. Club marks come from `data/teams.json`. A 1986 logo file is used where the franchise matches that sheet. Marlins, Rays, Diamondbacks, Rockies, Nationals, and Philadelphia Athletics use a monogram because they are not in that sheet. Bios in `data/bios.json` cover only players who appear in the recorded games. Clubs that have not played still have an empty roster stub. The site says "Roster not announced yet." No score, line, or series result was changed.

## 2026-10-25 — Records and documents

The results file was split. Each game's rolls and manager log moved to `games/<id>.json`. The summary kept the box scores and gained `schema_version`, a per-game `date`, and `rng_seed` (the old per-game `seed`). Teams gained `bracket` and `losses`. No score, line, batting line, pitching line, or series result was changed. `scripts/validate_results.py` checks that reconciliation.

R1-03 Games 1 and 2, Boston leading Tampa Bay 2-0, were recorded on `main` and brought into this split. The series stays `in-progress`. Those games are dated 2026-10-24, the day the provenance says they were played. The date is not a stat. Pedro Martinez's Game 1 no-hitter is the recorded line: 9 innings, 0 hits.

One generator, `scripts/build_leaders.py`, writes [LEADERS.md](LEADERS.md), [TEAM_STATS.md](TEAM_STATS.md), the files in `box_scores/`, [AWARDS.md](AWARDS.md), [RECORDS.md](RECORDS.md), the JSON and RSS feeds, and the share graphics. [LEADERBOARDS.md](LEADERBOARDS.md) only points at that leaderboard. Award points, win probability, and series odds are display models in [MODELS.md](MODELS.md). They do not change a result.

The main documents now state the current tournament only. This file holds the dated rulings. [index.html](index.html) draws the bracket from the JSON. [LEADERS.md](LEADERS.md) and [ROSTERS.md](ROSTERS.md) are generated from the results file.

## 2026-10-24 — Payoff Pitch, the seed reset, and the amendment

### Engine

From this date the tournament is simulated in Payoff Pitch.

R1-02, San Francisco Giants 4-1 over the Washington Nationals, was simulated in Payoff Pitch on 2026-10-24 as a standalone governed series and adopted as R1-02, the same kind of adoption as R1-01. The series record names FAC deck mode, version 2 pitcher cards, the pitcher addendum, manager traits, and the fatigue fix layer from Game 3. Its games are dated 2026-10-24. R1-01 has no date stored.

### Seed reset

Joe reset the Round 1 seeding and, with it, every Round 1 series except Yankees vs Marlins. Six slots were pinned: Yankees #1, Philadelphia Athletics #14 in this reset, Oakland #22, Montreal #27, Washington #31, Marlins #32. The other 26 clubs filled the remaining slots by Full 26 Index.

The Giants–Expos and Red Sox–Philadelphia series played under the previous table were voided. They count for nothing. Those four clubs started the new Round 1 at 0-0, with rotation cycles and availability back at their pre-series condition. The archive of the voided series is not in this repository.

### Amendment, later the same day

Joe moved Philadelphia's pin from #14 to #17, accepting the calibration estimate's #17-ish placement (estimate 699.2, which sits #17 on the pure index scale once Oakland is counted at its index position). The White Sox (764.1), Orioles (758.4), and Astros (668.5) each rose one slot by index, to #14, #15, and #16. The pin set became Yankees #1, Philadelphia #17, Oakland #22, Montreal #27, Washington #31, Miami #32. The opening pairings that changed were R1-14 White Sox vs Mariners, R1-15 Orioles vs Royals, and R1-16 Astros vs Philadelphia. The amendment itself did not change a played result.

The index estimates for Philadelphia (699.2) and Montreal (543.2) are summarized in [TOURNAMENT_SEEDS.md](TOURNAMENT_SEEDS.md). The regression script and its output file are not in this repository.

## 2026-10-23 — Thirty-two clubs, reseeding, home pattern

Joe's direction: "Go to 32 teams." The two merged franchises split into their city clubs (Athletics into Oakland and Philadelphia; Washington into Washington and Montreal).

Reseeding, in Joe's words: "winners should play next lowest rank winner left so not a 1 vs 2 in 2nd round; 2nd round winners should reseed 1 vs lowest rank winner and so on; and same with loser bracket, best rank loser vs lowest rank loser." That rule replaced the fixed chart of named feeders. The current statement is in [BRACKET.md](BRACKET.md).

Home pattern became 2-2-1-1-1, higher seed home first. It replaced the 2-3-2 pattern used in the pilot exhibitions.

The bracket is winners stages of 16, 8, 4, 2, and 1 series counting the opening round, losers stages of 8, 8, 4, 4, 2, 2, 1, and 1, then the grand final and one reset if the one-loss finalist wins the first final. There are no crossovers. With 32 clubs both sides stay even. That structure replaced the earlier crossover and 30-team language.

Pool-relative pitcher grades were frozen. The starter A line extends through #35 (Gibson A). The frozen table is not in this repository. The current statement is in [TOURNAMENT_RULES.md](TOURNAMENT_RULES.md).

Card status as recorded that day: all 32 clubs were described as built on the prime-window basis, the four split clubs from their own graphics. Philadelphia's graphic was said to name 25 distinct players, so that club was recorded with 25 cards. The build report is not in this repository. The Philadelphia roster was later confirmed: it is Connie Mack's card in [ROSTERS.md](ROSTERS.md), with Ferris Fain at DH. The waiting-on-a-graphic note is closed.

### Seed table this day used

Replaced on 2026-10-24. Kept here so the reset has something to be compared with. Seeds 1–29 and 32 came from the Full 26 graphic. Oakland kept the merged Athletics' #14 and index. Washington kept #22 and its index. Philadelphia Athletics were #30 and Montreal Expos #31, with no index invented for them. The Marlins moved from #30 to #32.

| Seed | Team | Full 26 Index |
|---:|---|---:|
| 1 | New York Yankees | 1021.6 |
| 2 | San Francisco Giants | 971.2 |
| 3 | Boston Red Sox | 942.9 |
| 4 | Detroit Tigers | 922.1 |
| 5 | St. Louis Cardinals | 872.1 |
| 6 | Chicago Cubs | 864.4 |
| 7 | Atlanta Braves | 857.5 |
| 8 | Pittsburgh Pirates | 830.6 |
| 9 | Cincinnati Reds | 814.3 |
| 10 | Los Angeles Dodgers | 810.9 |
| 11 | Philadelphia Phillies | 809.1 |
| 12 | Minnesota Twins | 808.5 |
| 13 | Cleveland Guardians | 801.2 |
| 14 | Oakland Athletics | 800.6 |
| 15 | Chicago White Sox | 764.1 |
| 16 | Baltimore Orioles | 758.4 |
| 17 | Houston Astros | 668.5 |
| 18 | Kansas City Royals | 647.4 |
| 19 | Seattle Mariners | 606.1 |
| 20 | Los Angeles Angels | 605.6 |
| 21 | New York Mets | 600.6 |
| 22 | Washington Nationals | 570.8 |
| 23 | Milwaukee Brewers | 569.9 |
| 24 | Texas Rangers | 566.2 |
| 25 | Toronto Blue Jays | 565.6 |
| 26 | San Diego Padres | 494.7 |
| 27 | Colorado Rockies | 467.4 |
| 28 | Arizona Diamondbacks | 442.8 |
| 29 | Tampa Bay Rays | 387.0 |
| 30 | Philadelphia Athletics | (not on the graphic) |
| 31 | Montreal Expos | (not on the graphic) |
| 32 | Miami Marlins | 385.9 |

### Reseeding check

A scratch check was run on 2026-10-23 against a copy of the results file, then described again after the file held R1-01, R1-02, and 9 game records. The scripts are not in this repository. The seed numbers in the examples are the 2026-10-23 table above, not the current table. The check recomputed each stage's pool after every completed series and compared the pairings to high-against-low order, and it checked that no stage held pairings before its feeders were complete.

- Favorites path (higher seed wins every series): the Yankees, undefeated, in 62 series, with F-02 not needed. Winners Round 2 opened NYY (#1) against BAL (#16), and the #2 seed drew #15.
- Mixed path (underdogs win R1-03 through R1-16, favorites after that, and the one-loss finalist wins the grand final): the reset filled and a champion was decided in 63 series. Winners Round 2 opened NYY (#1) against PHA (#30). Losers Round 1 opened BOS (#3) against MIA (#32).
- On both paths every non-champion finished at two series losses, no club occupied two live series, and drop-in stages pooled survivors with drop-ins. The played games were left unchanged. A migration that put W2-01 and L1-01 back to shells was checked the same way.

Those pairings are not the pairings the current seeds would produce. They are the record of the check.

## 2026-10-22 — Standing rules, and the index graphic

Joe adopted the rules stack from the Yankees vs Marlins pilot, plus five changes Cooper proposed after that series, plus the full rotation rule. The pilot was six games, and the Yankees won it 4 games to 2. It was played with lineups and pitcher pools that are not the tournament rosters. Tournament R1-01 is a different series: Yankees 4-0 over the Marlins, adopted later and not replayed. The adopted text is [TOURNAMENT_RULES.md](TOURNAMENT_RULES.md). This repository does not itemize Cooper's five changes separately from that text.

The same day, Joe adopted pool-relative pitching grades: letter grades ranked inside the tournament pool, starters and relievers separate, instead of the engine's fixed bands.

The Full 26 Index graphic that seeds the non-pinned clubs was sent this day. The citation is in [TOURNAMENT_SEEDS.md](TOURNAMENT_SEEDS.md).

The Version 23 board reconstruction, the Master Game symbol tables, and the longer grade-calibration table are not in this repository. The factors and the audit counts that were written into the rules are still in [TOURNAMENT_RULES.md](TOURNAMENT_RULES.md).
