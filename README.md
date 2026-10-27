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

## 2026-10-26 San Diego Padres approved 6/6 roster

Brian Giles (left-handed OF) was added as sixth bench player, and Craig Lefferts was removed from the active 26. The active roster is 9 lineup / 6 bench / 5 SP / 6 RP. Lefferts' previously converted card stays in `data/cards.json` as archived historical source data and must not be confused with an active roster spot. Giles' original Hitter v0.5 conversion has **not** been produced in this change: he is marked as awaiting conversion on his roster/player page, and no simulated card ratings were invented. The franchise Peak 162 display is Padres-only; his stats from other franchises must never be included.

## 2026-10-26 Philadelphia Athletics converted-set alignment

Joe approved reconciling the staged Philadelphia Athletics player-card roster to the official 26-man owner roster. Ferris Fain is lineup/DH (slot 9), Max Bishop is a bench infielder (slot 6), Elmer Valo is the left-handed outfielder/bat on the bench (slot 7), and George Earnshaw was removed from this club's converted roster and card listing. No completed tournament game, opponent, or official result was changed.

**Conversion status:** Elmer Valo is an approved roster member, **not yet a playable converted card**. The repository has a five-season franchise Peak 162 *display line* for him, but the frozen Hitter v0.5 source engine and original conversion input live in the external `~/workspace/payoff-pitch-alltime-teams` / builder workspace and are not in this GitHub repository. `data/cards.json` intentionally has `card_bat: null` and a visible pending-conversion flag for Valo. No percentile bands, fielding ratings, or fake QA pass were invented. Before Philadelphia's first game, generate Valo with the actual frozen Hitter v0.5 engine, reconcile his five seasons and hand/position labels, and replace the pending entry with the genuine converted result. `scripts/build_cards.py` applies the owner roster amendment after reading the old staged source; regenerate the set upstream too so the source agrees.
