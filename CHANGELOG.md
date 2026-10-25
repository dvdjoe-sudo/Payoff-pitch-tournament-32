# Changelog

Dated rulings and repo history. The rules, seeds, and bracket in force are [TOURNAMENT_RULES.md](TOURNAMENT_RULES.md), [TOURNAMENT_SEEDS.md](TOURNAMENT_SEEDS.md), and [BRACKET.md](BRACKET.md). This file is the history those pages used to carry inline.

## 2026-10-25 — Records and documents

The results file was split. Each game's rolls and manager log moved to `games/<id>.json`. The summary kept the box scores and gained `schema_version`, a per-game `date`, and `rng_seed` (the old per-game `seed`). Teams gained `bracket` and `losses`. No score, line, batting line, pitching line, or series result was changed. `scripts/validate_results.py` checks that reconciliation.

R1-03 Games 1 and 2, Boston leading Tampa Bay 2-0, were recorded on `main` and brought into this split. The series stays `in-progress`. Those games are dated 2026-10-24, the day the provenance says they were played. The date is not a stat. Pedro Martinez's Game 1 no-hitter is the recorded line: 9 innings, 0 hits.

One generator, `scripts/build_leaders.py`, writes [LEADERS.md](LEADERS.md), [TEAM_STATS.md](TEAM_STATS.md), the files in `box_scores/`, [AWARDS.md](AWARDS.md), [RECORDS.md](RECORDS.md), the JSON and RSS feeds, and the share graphics. [LEADERBOARDS.md](LEADERBOARDS.md) only points at that leaderboard. Award points, win probability, and series odds are display models in [MODELS.md](MODELS.md). They do not change a result.

The main documents now state the current tournament only. This file holds the dated rulings. [index.html](index.html) draws the bracket from the JSON. [LEADERS.md](LEADERS.md) and [ROSTERS.md](ROSTERS.md) are generated from the results file.

## 2026-10-24 — Payoff Pitch, the seed reset, and the amendment

### Engine

Joe closed APBA. From this date the tournament is simulated in Payoff Pitch.

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

Card status as recorded that day: all 32 clubs were described as built on the prime-window basis, the four split clubs from their own graphics. Philadelphia's graphic was said to name 25 distinct players, so that club was recorded with 25 cards. The build report is not in this repository. [ROSTERS.md](ROSTERS.md) leaves Philadelphia as a TODO until the roster is confirmed.

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
