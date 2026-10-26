# Changelog

Dated rulings and repo history. The rules, seeds, and bracket in force are [TOURNAMENT_RULES.md](TOURNAMENT_RULES.md), [TOURNAMENT_SEEDS.md](TOURNAMENT_SEEDS.md), and [BRACKET.md](BRACKET.md). This file is the history those pages used to carry inline.

## 2026-10-26 — Head to head

The Head to head page compares any two clubs, lineup spot by lineup spot. An owner card is used when one is stored. Otherwise the converted lineup is used, with the peak line taken from that card. A club with neither says "Roster not announced yet." No player or stat is added. The service worker cache is payoff-pitch-v16. No game result was changed.

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
