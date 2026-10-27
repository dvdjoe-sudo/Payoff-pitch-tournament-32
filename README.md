# Payoff Pitch Tournament 32

Payoff Pitch is the baseball simulator this tournament is played in. Thirty-two all-time franchise clubs play a double-elimination bracket. Every matchup is a best-of-7 series. A club is eliminated on its second series loss. There are no byes. After the opening round, each stage is reseeded by original seed, highest survivor against lowest.

A game is simulated, then written into [`tournament_results.json`](tournament_results.json). That file is the bracket, the series, and the box score of every completed game. The dice or deck record for each game, and the manager log, live in [`games/`](games/) and are linked from the summary. R1-01 was simulated in APBA and adopted into the tournament; it is not replayed. R1-02 and R1-03 were simulated in Payoff Pitch on 2026-10-24 and adopted the same way. R1-04 was simulated in Payoff Pitch on 2026-10-25. Later series are simulated in Payoff Pitch as each club's set is ready.

The bracket viewer is [`index.html`](index.html). It reads the results file and draws the bracket, standings, game pages, team pages, the awards race, the milestone list, derived stats, and a history timeline. The home page rotates a recorded moment by the calendar date. Each game page charts a labeled win-probability estimate from the line score and can print a scorecard. Static scorecard PDFs are in [`scorecards/`](scorecards/). Share links for a game or a series are static pages in [`share/`](share/), because the in-site routes are hashes. Club marks and colors are [`data/teams.json`](data/teams.json). Each club uses a real classic cap logo. Where the files came from is [`CREDITS.md`](CREDITS.md). [`ADDING_GAMES.md`](ADDING_GAMES.md) is the way to add the next game, including a markdown box score dropped in [`inbox/`](inbox/). [`PWA.md`](PWA.md) covers install.

Current standing (22 games played):

- R1-01: New York Yankees 4-0 over the Miami Marlins. Complete. Played under APBA before the switch; adopted into this tournament by Joe's ruling; never to be replayed.
- R1-02: San Francisco Giants 4-1 over the Washington Nationals. Complete. Played in Payoff Pitch on 2026-10-24.
- R1-03: Boston Red Sox 4-3 over the Tampa Bay Rays. Complete. Played in Payoff Pitch. Game 1 was a Pedro Martinez no-hitter at Fenway. Boston advances on the winners side at 1-0. Tampa Bay drops to the losers side at 0-1 and is not eliminated. Series MVP: Roger Clemens. Runner-up: Jimmie Foxx.
- R1-04: Detroit Tigers 4-2 over the Arizona Diamondbacks. Complete. Played in Payoff Pitch on 2026-10-25. Arizona took the first two games in Detroit, Game 2 in thirteen innings; Detroit won the last four after Joe's lineup ruling started Harry Heilmann in left field. Game 5 was played twice; the fresh re-play is the official game, and the superseded first playing is not in this archive. Detroit advances on the winners side at 1-0. Arizona drops to the losers side at 0-1 and is not eliminated. Series MVP: Harry Heilmann. Runner-up: George Kell.

## Seeds

Six seeds are Joe's pins. They are pins, and they are not filled by walking down the Full 26 Index: New York Yankees 1, Philadelphia Athletics 17, Oakland Athletics 22, Montreal Expos 27, Washington Nationals 31, Miami Marlins 32. The Yankees pin is also the top of the index, and the Marlins pin is also last on the index. Oakland, Philadelphia, Montreal, and Washington are pinned off the index rank. The other 26 clubs fill the remaining slots by the index. The table is [`TOURNAMENT_SEEDS.md`](TOURNAMENT_SEEDS.md).

## Bracket

| Slot | Pairing | Result |
|---|---|---|
| R1-01 | #1 New York Yankees vs #32 Miami Marlins | Yankees 4-0 |
| R1-02 | #2 San Francisco Giants vs #31 Washington Nationals | Giants 4-1 |
| R1-03 | #3 Boston Red Sox vs #30 Tampa Bay Rays | Complete. Boston won 4-3 |
| R1-04 | #4 Detroit Tigers vs #29 Arizona Diamondbacks | Complete. Detroit won 4-2 |
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

Winners Round 2 and Losers Round 1 form when all 16 opening series are complete. Until then those slots are empty. The stage map is [`BRACKET.md`](BRACKET.md).

## Standings

Series is series wins and series losses. Games is game wins and game losses. Bracket is `winners` with no series loss, `losers` with one, and `eliminated` with two. Nobody is eliminated. Boston's series win puts Tampa Bay on the losers side with one series loss, and Detroit's puts Arizona there.

| Seed | Team | Bracket | Series | Games |
|---:|---|---|---:|---:|
| 1 | New York Yankees | Winners | 1-0 | 4-0 |
| 2 | San Francisco Giants | Winners | 1-0 | 4-1 |
| 3 | Boston Red Sox | Winners | 1-0 | 4-3 |
| 4 | Detroit Tigers | Winners | 1-0 | 4-2 |
| 5 | St. Louis Cardinals | Winners | 0-0 | 0-0 |
| 6 | Chicago Cubs | Winners | 0-0 | 0-0 |
| 7 | Atlanta Braves | Winners | 0-0 | 0-0 |
| 8 | Pittsburgh Pirates | Winners | 0-0 | 0-0 |
| 9 | Cincinnati Reds | Winners | 0-0 | 0-0 |
| 10 | Los Angeles Dodgers | Winners | 0-0 | 0-0 |
| 11 | Philadelphia Phillies | Winners | 0-0 | 0-0 |
| 12 | Minnesota Twins | Winners | 0-0 | 0-0 |
| 13 | Cleveland Guardians | Winners | 0-0 | 0-0 |
| 14 | Chicago White Sox | Winners | 0-0 | 0-0 |
| 15 | Baltimore Orioles | Winners | 0-0 | 0-0 |
| 16 | Houston Astros | Winners | 0-0 | 0-0 |
| 17 | Philadelphia Athletics | Winners | 0-0 | 0-0 |
| 18 | Kansas City Royals | Winners | 0-0 | 0-0 |
| 19 | Seattle Mariners | Winners | 0-0 | 0-0 |
| 20 | Los Angeles Angels | Winners | 0-0 | 0-0 |
| 21 | New York Mets | Winners | 0-0 | 0-0 |
| 22 | Oakland Athletics | Winners | 0-0 | 0-0 |
| 23 | Milwaukee Brewers | Winners | 0-0 | 0-0 |
| 24 | Texas Rangers | Winners | 0-0 | 0-0 |
| 25 | Toronto Blue Jays | Winners | 0-0 | 0-0 |
| 26 | San Diego Padres | Winners | 0-0 | 0-0 |
| 27 | Montreal Expos | Winners | 0-0 | 0-0 |
| 28 | Colorado Rockies | Winners | 0-0 | 0-0 |
| 29 | Arizona Diamondbacks | Losers | 0-1 | 2-4 |
| 30 | Tampa Bay Rays | Losers | 0-1 | 3-4 |
| 31 | Washington Nationals | Losers | 0-1 | 1-4 |
| 32 | Miami Marlins | Losers | 0-1 | 0-4 |

## Bracket viewer

From the repository root:

```
python3 -m http.server 8000
```

Open `http://localhost:8000/`. The page fetches `tournament_results.json` and the files in `games/`. Opening `index.html` as a `file://` page will not load them.

The site is static. GitHub Pages serves it from the repository root. `.nojekyll` is in the repo so Pages does not pass the JSON through Jekyll. After this work is on `main`, the site is [https://dvdjoe-sudo.github.io/Payoff-pitch-tournament-32/](https://dvdjoe-sudo.github.io/Payoff-pitch-tournament-32/).

Pages setup, once:

1. Repository Settings, Pages, Build and deployment.
2. Source: GitHub Actions.
3. The workflow [`.github/workflows/pages.yml`](.github/workflows/pages.yml) validates the archive, rebuilds the generated pages, and deploys on every push to `main`.

The first deploy needs the Pages source set to GitHub Actions. A branch deploy and an Actions deploy should not both be selected.

## Documents

- [Bracket](BRACKET.md) is the stage map.
- [Rules](TOURNAMENT_RULES.md) are the standing tournament rules.
- [Seeds](TOURNAMENT_SEEDS.md) are the only seed table.
- [Rosters](ROSTERS.md) are the 32 clubs. Rebuild with `python3 scripts/build_rosters.py`.
- [Leaders](LEADERS.md) are the batting and pitching boards. Rebuild with `python3 scripts/build_leaders.py`.
- [Team stats](TEAM_STATS.md) are the club lines from that same script.
- [Box scores](box_scores/) are one markdown file per game, generated from the JSON.
- [Awards](AWARDS.md) and [records](RECORDS.md) use the formulas in [MODELS.md](MODELS.md).
- [Changelog](CHANGELOG.md) holds the dated rulings.
- [Schema](SCHEMA.md) describes the results file and the per-game files.
- [License](LICENSE) covers the code and these documents.
- [Viewer](index.html) draws the bracket from the JSON.
- [Adding games](ADDING_GAMES.md) covers the in-site form and `scripts/import_game.py`.
- [Install](PWA.md) covers the manifest and the service worker.
- [Team marks](data/teams.json) are the logo and color swap file.
- [Rosters and cards](data/rosters.json) list the converted clubs' roster spots, and [player cards](data/cards.json) carry each rostered player's peak line, converted card, and tournament line. Rebuild with `python3 scripts/build_cards.py`.
- [Odds](feed/odds.json) are the Monte Carlo series and title chances from [MODELS.md](MODELS.md).
- [JSON feed](feed/tournament.json) and [RSS](feed/games.xml) list the games played.
- [LEADERBOARDS.md](LEADERBOARDS.md) points at the one leaderboard. It is not a second board.

`python3 scripts/validate_results.py` checks that the box scores, series, and team records still reconcile, and that the split did not change a stat line. `python3 scripts/build_leaders.py` rewrites leaders, team stats, box scores, awards, records, feeds, and share graphics.

## Rosters and player cards

The current **converted-club count and club list are derived from** [`data/rosters.json`](data/rosters.json) by the live [Rosters and player cards page](https://dvdjoe-sudo.github.io/Payoff-pitch-tournament-32/#/rosters). They are not repeated as a fixed number here, since new sets continue to be added. Every club's roster is on its team page. Where an owner card is also on that page, the owner card is the list and the converted set sits under Payoff Pitch cards. A player page labels the stretch `Peak 162 with <club> (YYYY–YYYY)`. Counting stats are scaled to a 162-game season. The averages and ERA are that stretch's own. Clubs that have not yet played a tournament series show their players' available peak lines and converted cards without tournament stats.

`scripts/build_cards.py` writes `data/rosters.json` and `data/cards.json` from the converted set files and the master archive in the workspace, plus the Lahman Teams table for the pitcher peak scaling; it is run by hand when a new set is converted, and its header documents the inputs and the 162-game-average method. Adding a club is one row in its SETS table plus a rerun. No game, series, or locked line is read for writing, and the validator's locked checks do not cover these two files.

## R1-03 — Complete FAC and play-by-play

The owner's 101-page *R1-03 FAC and Dice Rolls* record was supplied on 2026-10-26. Every FAC flip and the full play-by-play for Boston–Tampa Bay is transcribed in the linked game files: [Game 1](games/R1-03-G1.fac.md) · [Game 2](games/R1-03-G2.fac.md) · [Game 3](games/R1-03-G3.fac.md) · [Game 4](games/R1-03-G4.fac.md) · [Game 5](games/R1-03-G5.fac.md) · [Game 6](games/R1-03-G6.fac.md) · [Game 7](games/R1-03-G7.fac.md). The game pages also display the ordered FAC history. Games 3–7 now have their actual FAC sequences in the per-game JSON record, checked against the owner-provided transcript; the original Games 1–2 sequences match it exactly. The official box scores, standings, and series results were not changed. The source record preserves hand-resolved rare-play notes and the full narration; no missing manager log was invented.

## 2026-10-27 Texas Rangers approved Rubén Sierra for Kenny Rogers

Texas adds switch-hitting outfielder **Rubén Sierra** (`sierrru01`) as sixth bench hitter and backup RF/OF using only Rangers seasons **1986–1992, 2000–2001 and 2003**, excluding all other franchise performance. Kenny Rogers (`rogerke01`) becomes inactive in the bullpen, retaining his original genuine historical converted pitcher card. Darold Knowles takes RP6; Wetteland, Feliz, Zimmerman, Kern and Jeff Russell remain. The original nine hitters, **Corey Seager batting ninth at DH**, and all five starters are unchanged. Active 26: **9 lineup / 6 bench / 5 starters / 6 relievers**. All historical cards, played games, box scores, results and dice/FAC logs are preserved. Sierra's authentic Hitter v0.5 playable conversion is pending, and the Rangers-only five-year Peak 162 display awaits a verified Lahman build. PED matters remain separate.

## 2026-10-27 Milwaukee Brewers approved Ben Oglivie for Freddy Peralta

Milwaukee's sixth bench hitter is Ben Oglivie (left-handed LF/corner-OF reserve) using **Milwaukee Brewers franchise statistics from 1978–1986 only**. Freddy Peralta leaves the active bullpen and retains his authentic original converted historical card. The six remaining relievers are Josh Hader, Devin Williams, Rollie Fingers, Dan Plesac, Ken Sanders and Jeremy Jeffress. All nine original starters, **Prince Fielder batting fourth at DH**, and the five-man rotation remain unchanged. Active roster **9/6/5/6**, 26 unique players. No historical cards, previously played games, dice/FAC logs, results or box scores were modified. Oglivie's Milwaukee-only five-year Peak 162 (1978–1982) is verified from Lahman; the playable genuine frozen Hitter v0.5 conversion remains pending. No invented card ratings or statistics. PED reviews remain separate.

## 2026-10-27 Oakland Athletics approved Eric Chavez for Gene Nelson

Oakland's sixth bench hitter is Eric Chavez (LH, reserve 3B) using **Oakland Athletics 1998–2010 franchise performance exclusively**. Gene Nelson leaves the active bullpen and retains his historical original converted card; Rick Honeycutt becomes RP6 while Eckersley, Fingers, Bailey, Doolittle and Hendriks remain in bullpen roles. The full starting lineup and five SPs remain unchanged, **José Canseco batting fifth as DH**. Active roster now 9/6/5/6, 26 distinct players. All original player cards, previously played games, results, box scores and FAC/dice rolls unchanged. Pending authentic Hitter v0.5 Eric Chavez playable conversion. PED decisions are expressly separate, no automatic exclusions made.

## 2026-10-27 New York Mets approved Howard Johnson / Sid Fernandez active roster

Howard Johnson (switch hitter, 3B/IF defensive reserve) replaces Sid Fernandez as sixth Mets bench bat. Use **Mets 1985–1993 only** for Johnson, never his Detroit, Colorado or Chicago years. Sid Fernandez's original historical pitching card stays archived. Billy Wagner, Edwin Díaz, Armando Benítez, Tug McGraw, John Franco and Jesse Orosco retain their relief slots. The unchanged nine-hitter lineup includes **Pete Alonso at DH batting sixth**; **John Olerud remains on the bench fifth**. No changes to the five-man rotation. Official and converted active Mets roster is **9/6/5/6**, 26 distinct people. Original cards and previously played games, scores, stats, box scores, and FAC/dice records remain unchanged. Genuine Mets-only frozen Hitter v0.5 Howard Johnson playable conversion remains pending.

## 2026-10-27 Los Angeles Angels approved Rod Carew for Doug Corbett

Rod Carew is the sixth Angels bench hitter, left-handed 1B/PH, using **California Angels 1979–1985 seasons exclusively**. Doug Corbett is no longer active but his original pitcher card remains in the historical catalog. Scot Shields and Bryan Harvey retain their existing roles while Scott Downs becomes RP5 and Darren Oliver RP6. The starting nine and entire rotation remain intact, including Shohei Ohtani as **starting DH batting first**. Angels now have **9 lineup / 6 bench / 5 SP / 6 RP**, 26 distinct active players. All historical player cards, completed games, results, box scores, dice rolls and FAC records are untouched. Rod Carew's genuine California-only Hitter v0.5 playable conversion is pending.

## 2026-10-27 Seattle Mariners approved Adrián Beltré / Mike Moore roster

The Mariners' sixth bench hitter is Adrián Beltré, right-handed reserve 3B, with **2005–2009 Seattle-only performance**. Mike Moore is inactive while his historical original converted card is preserved. The other six relievers are J.J. Putz, Andrés Muñoz, Edwin Díaz, Jeff Nelson, Arthur Rhodes and Kazuhiro Sasaki in relief slots 1–6. All nine hitters, including **Edgar Martínez batting fourth as the starting DH**, and the five rotation pitchers stay unchanged. Updated active 26 has **9 lineup / 6 bench / 5 SP / 6 RP**. All historical cards, previously played games, scores, results, box scores and original dice/FAC rolls are preserved. Beltré's authentic Seattle-only frozen Hitter v0.5 playable card conversion is still pending.

## 2026-10-27 Kansas City Royals approved John Mayberry, Danny Tartabull at DH

Kansas City adds John Mayberry as the sixth bench hitter (LH 1B), using his **Royals seasons 1972–1977 only**, and removes Charlie Leibrandt from the active bullpen. Danny Tartabull becomes the starting #2 DH, and Hal McRae moves into Tartabull's former bench #5. All other lineup slots and the five starting pitchers are unchanged. The six relievers are Dan Quisenberry, Jeff Montgomery, Joakim Soria, Greg Holland, Kelvin Herrera and Steve Mingori. Active roster is **9/6/5/6**, 26 unique players. Original historical cards, including Leibrandt's, all played games, results, box scores and FAC/dice logs remain unchanged. John Mayberry's genuine frozen Hitter v0.5 playable card conversion remains pending.

## 2026-10-27 Philadelphia Athletics approved Foxx DH, Fain 1B and Shantz/Barry

The active 26 now uses Foxx as DH (lineup #4) and Fain at first base (lineup #9), with the same nine hitters and pitching rotation. Bobby Shantz is the new left-handed long/swing pitcher at bullpen #6; Jack Barry is inactive but his original converted card is preserved. Shantz's statistics are **Philadelphia 1949–1954 only**; never include Kansas City Athletics or the Yankees/other clubs. Max Bishop moves to bench #5 and Elmer Valo #6, giving 9 lineup / 6 bench / 5 SP / 6 RP. Existing historical cards and completed games, stats, scores, FAC/dice rolls and box scores are unchanged. Shantz's genuine playable frozen Pitcher v0.2.3 card is pending conversion, and his display-only Peak 162 line must not be read as a pure relief forecast.

## 2026-10-27 Houston Astros approved Alou / Dotel roster

Moisés Alou (RH LF/RF) replaces Octavio Dotel as the sixth Astros bench hitter. Only Alou's Houston seasons **1998, 2000 and 2001** count; no Montreal or other club performance is used. Joe Sambito and Dave Smith are bullpen slots 5 and 6, preserving the left-handed and late roles. Official, converted and generated rosters now agree on **9 lineup / 6 bench / 5 SP / 6 RP** (26 unique players). All prior historical cards, completed games, recorded results, FAC/dice logs and box scores are unchanged. Alou's genuine Houston-franchise frozen Hitter v0.5 playable conversion is not yet provided.

## 2026-10-27 Baltimore Orioles approved George Sisler / Sammy Stewart 6/6

George Sisler becomes the sixth Baltimore bench hitter (LH 1B), with franchise performance drawn **only from the St. Louis Browns (1915–1927)**, and Sammy Stewart leaves active relief duty. The six relievers are Gregg Olson, Zach Britton, Félix Bautista, Stu Miller, Dick Hall and Tippy Martinez. The official owner roster, converted active 26, generator, and validator all agree on **9 lineup / 6 bench / 5 SP / 6 RP**, 26 unique players. Original Stewart conversion and all completed games, box scores, results and FAC/dice histories are untouched. Sisler's authentic frozen Hitter v0.5 playable card remains pending conversion.

## 2026-10-27 Chicago White Sox approved Dick Allen / Bob Locker 6/6

Dick Allen (RH 1B/DH, Chicago franchise seasons only) becomes bench #6. Bob Locker leaves active relief duty. The White Sox active 26 and official owner card now agree on **9 lineup / 6 bench / 5 rotation / 6 bullpen**; Bobby Thigpen, Hoyt Wilhelm, Bobby Jenks, Keith Foulke, Dámaso Marte and Eddie Cicotte remain the relief staff. Original converted cards (including Locker), completed games, results, original box scores and FAC/dice rolls remain unchanged. Allen's authentic playable Hitter v0.5 conversion remains pending; no ratings were invented.

## 2026-10-27 Minnesota Twins approved Bob Allison / Firpo Marberry 6/6

Joe approved **Bob Allison** as Minnesota's sixth bench player (RH power, OF/1B) in place of **Firpo Marberry** on the active pitching staff. The official owner roster, active 26, generated `ROSTERS.md` and rebuild script agree on **9 lineup / 6 bench / 5 starting pitchers / 6 bullpen**. With Marberry inactive, the bullpen comprises Joe Nathan, Al Worthington, Rick Aguilera, Jhoan Duran, Taylor Rogers and Jim Perry; the original roles are unchanged. All existing converted cards, including Marberry's historical pitching chart, plus previously played games, box scores, outcomes and dice/FAC records remain untouched. Bob Allison's card still needs a genuine Hitter v0.5 conversion using the Senators/Twins franchise seasons only; the current roster slot does not supply imaginary ratings.

## 2026-10-27 Phillies approved Chuck Klein / Ryan Madson 6/6

Joe approved **Chuck Klein** as the Phillies sixth bench hitter, and removed **Ryan Madson** from the active bullpen. The active 26 (`data/rosters.json`), official owner roster (`data/announced_rosters.json`) and generated `ROSTERS.md` now match **9 lineup / 6 bench / 5 starting pitchers / 6 relievers**. The bullpen keeps Jonathan Papelbon, Gene Garber, Tug McGraw, Ron Reed, Brad Lidge and Ranger Suárez. The roster card is available for future games, but Klein's playable Payoff Pitch frozen Hitter v0.5 card still needs the authentic Phillies-franchise-only conversion and no statistics or card odds have been fabricated. The original `data/cards.json`, including Madson's archived pitching card, `tournament_results.json`, every game and box score, and FAC/dice histories remain untouched. The full-build adapter and validation record this dated approved personnel change.

## 2026-10-27 Pittsburgh Pirates approved Waner/McBean 6/6

Joe approved **Paul Waner** as Pittsburgh's sixth bench hitter (RF/LF, left-handed contact), replacing **Al McBean** on the active bullpen. Grant Jackson moves to bullpen #5 and Sam Leever to bullpen #6; their roles remain unchanged. The official owner roster, the canonical `data/rosters.json` and the generated `ROSTERS.md` are synchronized at **9 starting hitters / 6 bench / 5 rotation / 6 bullpen = 26**. Waner's playable frozen Hitter v0.5 card will require an authentic Pirates-only peak conversion; roster inclusion does not imply a playable card. The original card archive, including McBean's historical card, plus all previous games, scores, box scores and FAC/dice logs remain untouched. A full set-file rebuild retains this dated owner-approved change.

## 2026-10-27 Atlanta Braves approved Horner/Wohlers 6/6

Joe selected **Bob Horner**, not Hugh Duffy, for the Braves' sixth bench slot and directed a reliever other than Phil Niekro to be removed. Mark Wohlers is made inactive, leaving Craig Kimbrel, Raisel Iglesias, Mike Remlinger, Gene Garber, Jonny Venters and Phil Niekro in the bullpen. The published official roster (`data/announced_rosters.json`), active roster (`data/rosters.json`), and `ROSTERS.md` now reflect **9 lineup / 6 bench / 5 starting pitchers / 6 relievers**. All historical games, dice/FAC and existing converted cards, including Wohlers's original, remain unchanged. Horner's genuine Braves-only Hitter v0.5 conversion is pending. Future explicit rebuilds retain this owner-approved roster switch, and the validator confirms that the historical Wohlers card is still archived.

## 2026-10-27 Detroit Tigers approved Gibson/Holton roster 6/6

Joe approved Kirk Gibson as Detroit's sixth bench hitter (OF/pinch-runner), replacing Tyler Holton's left-handed relief spot, effective for games **after completed R1-04 vs. Arizona**. The current active 26 in `data/rosters.json` are **9 lineup / 6 bench / 5 starters / 6 bullpen**. The official owner roster in `data/announced_rosters.json` and the generated `ROSTERS.md` match. Bullpen numbering has Dizzy Trout at RP5 and Denny McLain at RP6. Original `data/cards.json`, `tournament_results.json`, `games/`, the six historical game box scores and all FAC/dice histories remain untouched; Holton's converted card is retained for the archive. Gibson's playable frozen Hitter v0.5 card requires a genuine Detroit-only peak conversion. The card builder applies this future-only roster change on full set regeneration.

## 2026-10-27 two-way roster counting (Joe-approved)

A genuine two-way player counts as **one of the 26 active players**, even when the roster data lists a hitter role and a pitcher role for the same player ID. Boston's Babe Ruth (`ruthba01`) remains both bench hitter #6 and pitcher/bullpen #7, with no Boston cut: 27 role records represent 26 distinct players. The two roles retain their original cards and stay subject to normal pitching and fatigue rules. See [tournament roster rules](TOURNAMENT_RULES.md#rosters-and-converted-sets) and [roster schema](SCHEMA.md#roster-and-card-data). All pre-existing game and card files remain untouched.

## 2026-10-27 San Francisco Giants approved 6/6 roster

Joe approved Monte Irvin as the sixth bench player (LF) in place of Javier López on the active Giants 26. The active roster is now **9 lineup / 6 bench / 5 rotation / 6 relievers**. Only future tournament games are affected after the completed R1-02 Giants–Nationals series. No played results, box scores, FAC/dice rolls, historical converted cards or player identities in the original game archive were changed; Javier López's prior card stays stored in `data/cards.json`. The full-set card builder's idempotent Giants amendment preserves this personnel decision without altering the old set. Monte Irvin requires the authentic frozen Hitter v0.5 conversion and Giants franchise-only prime years; an active roster entry is **not** a playable card.

## 2026-10-26 San Diego Padres approved 6/6 roster

Brian Giles (left-handed OF) was added as sixth bench player, and Craig Lefferts was removed from the active 26. The active roster is 9 lineup / 6 bench / 5 SP / 6 RP. Lefferts' previously converted card stays in `data/cards.json` as archived historical source data and must not be confused with an active roster spot. Giles' original Hitter v0.5 conversion has **not** been produced in this change: he is marked as awaiting conversion on his roster/player page, and no simulated card ratings were invented. The franchise Peak 162 display is Padres-only; his stats from other franchises must never be included.

## 2026-10-27 Yankees and Marlins franchise cards

The approved card conversion is the active 26. New York is 9 lineup, 5 bench, 5 starters, and 7 relievers, with Mike Stanton (`stantmi02`) the left-handed specialist. Miami is the same shape, with Josh Johnson (`johnsjo09`) leading the rotation, Otto Lopez (`lopezot01`) at utility, and A.J. Burnett (`burneaj01`) the long reliever. A 2026-10-26 roster sync had put Rickey Henderson and Juan Pierre on those clubs and moved Stanton and Burnett off the active lists; that sync is not the active roster, and no card was invented for Henderson or Pierre. Played games, box scores, and the results file are unchanged. Stanton and Burnett still have their recorded appearances.

## 2026-10-26 Washington Nationals approved 6/6 roster

The Nationals add Jayson Werth (RF/LF/DH) as the sixth bench hitter and remove Craig Stammen from the active bullpen. Active total: 9 lineup / 6 bench / 5 starters / 6 relievers. Stammen's original converted card in `data/cards.json` and all five completed R1-02 games, pitching appearances, box scores and dice/FAC history remain untouched. Werth has not yet been converted via the frozen Hitter v0.5 engine; his current roster/player page labels the Payoff Pitch card and Washington-only peak as pending. The approved adjustment applies only to future games and is preserved by the card rebuild adapter.

## 2026-10-26 Tampa Bay Rays approved 6/6 roster

Aubrey Huff (OF, also 1B/3B/DH) joins bench OF6; Kevin Kelly leaves the active bullpen and J.P. Howell becomes bullpen slot 6. Tampa Bay's new active count is 9 lineup / 6 bench / 5 rotation / 6 relievers. Kelly's original converted card remains untouched in `data/cards.json`, and all of the previously played R1-03 Boston series, box scores, FAC/dice sequences and historical appearances remain unchanged. Huff's original Hitter v0.5 conversion and Rays-franchise-only peak profile are **pending**; do not confuse the roster entry with a playable card. Changes take effect only in future tournament games. `scripts/build_cards.py` preserves the approved roster when sets are rebuilt, and `scripts/validate_results.py` checks the active 26.

## 2026-10-26 Arizona Diamondbacks approved 6/6 roster

David Peralta has been added as the sixth Arizona bench player (left-handed LF); Juan Cruz is off the active 26. The active split is 9 lineup / 6 bench / 5 SP / 6 RP. Cruz appeared during R1-04, so his box scores and prior results remain exactly as played, and his converted card remains historical reference data. No invented hitter-card results are supplied for Peralta. His actual frozen Hitter v0.5 conversion and franchise-only five-season peak profile are still needed before play. `data/rosters.json` records the active 26; ROSTERS.md separately preserves previous game appearances. This roster change applies only to future games.

## 2026-10-26 Montreal Expos approved 6/6 roster

Moisés Alou (RH outfielder) is the Expos' sixth bench player; Jeff Fassero leaves the active roster. Montreal now has 9 lineup / 6 bench / 5 SP / 6 RP. Fassero's existing converted pitcher card is retained in `data/cards.json` as historical data. Alou's Hitter v0.5 card is **pending Joe's original conversion**; no fake dice, fielding, or ratings have been generated. His franchise Peak 162 profile uses Montreal seasons 1992–1996 only and omits his brief 1990 cameo. Past games remain unchanged.

## 2026-10-26 Philadelphia Athletics converted-set alignment

Joe approved reconciling the staged Philadelphia Athletics player-card roster to the official 26-man owner roster. Ferris Fain is lineup/DH (slot 9), Max Bishop is a bench infielder (slot 6), Elmer Valo is the left-handed outfielder/bat on the bench (slot 7), and George Earnshaw was removed from this club's converted roster and card listing. No completed tournament game, opponent, or official result was changed.

**Conversion status:** Elmer Valo is an approved roster member, **not yet a playable converted card**. The repository has a five-season franchise Peak 162 *display line* for him, but the frozen Hitter v0.5 source engine and original conversion input live in the external `~/workspace/payoff-pitch-alltime-teams` / builder workspace and are not in this GitHub repository. `data/cards.json` intentionally has `card_bat: null` and a visible pending-conversion flag for Valo. No percentile bands, fielding ratings, or fake QA pass were invented. Before Philadelphia's first game, generate Valo with the actual frozen Hitter v0.5 engine, reconcile his five seasons and hand/position labels, and replace the pending entry with the genuine converted result. `scripts/build_cards.py` applies the owner roster amendment after reading the old staged source; regenerate the set upstream too so the source agrees.
