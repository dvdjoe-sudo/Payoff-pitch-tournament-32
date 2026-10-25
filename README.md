# Payoff Pitch Tournament 32

Payoff Pitch is the baseball simulator this tournament is played in. Thirty-two all-time franchise clubs play a double-elimination bracket. Every matchup is a best-of-7 series. A club is eliminated on its second series loss. There are no byes. After the opening round, each stage is reseeded by original seed, highest survivor against lowest.

A game is simulated, then written into [`tournament_results.json`](tournament_results.json). That file is the bracket, the series, and the box score of every completed game. The dice or deck record for each game, and the manager log, live in [`games/`](games/) and are linked from the summary. R1-01 was simulated in APBA and adopted into the tournament; it is not replayed. On 2026-10-24 Joe closed APBA. R1-02 was simulated in Payoff Pitch that day and adopted the same way. Later series are simulated in Payoff Pitch as each club's set is ready.

Walkthrough: [Payoff Pitch top 32 tournament](https://muse.ai/s/payoff-pitch-top-32-tournament-xck6hxnxfvxsxmfi/CveOB6LiiLsVcK7Go4H5MqGh_DyskYPHOntiaN4jpvs).

The bracket viewer is [`index.html`](index.html). It reads the results file and redraws the bracket, the standings, and the box scores. The tables below are the snapshot with R1-01 and R1-02 complete.

## Seeds

Six seeds are Joe's picks. They are pins, and they are not filled by walking down the Full 26 Index: New York Yankees 1, Philadelphia Athletics 17, Oakland Athletics 22, Montreal Expos 27, Washington Nationals 31, Miami Marlins 32. The Yankees pin is also the top of the index, and the Marlins pin is also last on the index. Oakland, Philadelphia, Montreal, and Washington are pinned off the index rank. The other 26 clubs fill the remaining slots by the index. The table is [`TOURNAMENT_SEEDS.md`](TOURNAMENT_SEEDS.md).

## Bracket

| Slot | Pairing | Result |
|---|---|---|
| R1-01 | #1 New York Yankees vs #32 Miami Marlins | Yankees 4-0 |
| R1-02 | #2 San Francisco Giants vs #31 Washington Nationals | Giants 4-1 |
| R1-03 | #3 Boston Red Sox vs #30 Tampa Bay Rays | Not played |
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

Winners Round 2 and Losers Round 1 form when all 16 opening series are complete. Until then those slots are empty. The stage map is [`BRACKET.md`](BRACKET.md).

## Standings

Series is series wins and series losses. Games is game wins and game losses. Bracket is `winners` with no series loss, `losers` with one, and `eliminated` with two. Nobody is eliminated.

| Seed | Team | Bracket | Series | Games |
|---:|---|---|---:|---:|
| 1 | New York Yankees | Winners | 1-0 | 4-0 |
| 2 | San Francisco Giants | Winners | 1-0 | 4-1 |
| 3 | Boston Red Sox | Winners | 0-0 | 0-0 |
| 4 | Detroit Tigers | Winners | 0-0 | 0-0 |
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
| 29 | Arizona Diamondbacks | Winners | 0-0 | 0-0 |
| 30 | Tampa Bay Rays | Winners | 0-0 | 0-0 |
| 31 | Washington Nationals | Losers | 0-1 | 1-4 |
| 32 | Miami Marlins | Losers | 0-1 | 0-4 |

## Bracket viewer

From the repository root:

```
python3 -m http.server 8000
```

Open `http://localhost:8000/`. The page fetches `tournament_results.json` and the files in `games/`. Opening `index.html` as a `file://` page will not load them.

GitHub Pages needs no build. In the repository: Settings, Pages, Build and deployment, Deploy from a branch. Choose branch `main` and folder `/ (root)`, then save. `.nojekyll` is in the repo so Pages serves the JSON and the scripts as static files. After this work is on `main`, the site is [https://dvdjoe-sudo.github.io/Payoff-pitch-tournament-32/](https://dvdjoe-sudo.github.io/Payoff-pitch-tournament-32/). The Pages screen shows the URL GitHub assigned.

## Documents

- [Bracket](BRACKET.md) is the stage map.
- [Rules](TOURNAMENT_RULES.md) are the standing tournament rules.
- [Seeds](TOURNAMENT_SEEDS.md) are the only seed table.
- [Rosters](ROSTERS.md) are the 32 clubs. Rebuild with `python3 scripts/build_rosters.py`.
- [Leaders](LEADERS.md) are the batting and pitching boards. Rebuild with `python3 scripts/build_leaders.py`.
- [Changelog](CHANGELOG.md) holds the dated rulings.
- [Schema](SCHEMA.md) describes the results file and the per-game files.
- [License](LICENSE) covers the code and these documents.
- [Viewer](index.html) draws the bracket from the JSON.

`python3 scripts/validate_results.py` checks that the box scores, series, and team records still reconcile, and that the split did not change a stat line.
