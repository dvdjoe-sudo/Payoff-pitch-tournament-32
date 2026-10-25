# Adding a game

A new game stays out of `tournament_results.json` until Joe reviews it and merges it by hand. The tools on this page build and check a summary file and a detail file. They do not change a score that is already on the book.

## In the site

Open `#/add` (Add game in the menu). Fill the series id, game number, clubs, line scores, batting rows, and pitching rows.

Batting, one player per line:

```
TEAM, Name, AB, R, H, HR, RBI, BB, SO
```

Pitching, one pitcher per line:

```
TEAM, Name, IP, H, R, ER, BB, SO
```

Check rejects a tie, a line score that does not add up to the batting runs, and pitching runs that do not add up to the opponent's score. A passing check enables download and copy for two files:

- `<id>.json`, the summary, with `detail` set to `games/<id>.json`
- `<id>.detail.json`, the detail file, with an empty `rolls` array and a null `manager_log`

The shape matches [SCHEMA.md](SCHEMA.md). Player ids in the downloaded summary are shortened from the name. Replace them with the real ids before a merge. The form does not write the repository.

## From a CSV

`scripts/import_game.py` reads a GameChanger-style or Game Pulse-style box score.

Comment lines name the series:

```
# series R1-04
# game 1
# date 2026-10-26
# away ARI
# home DET
# away_name Arizona Diamondbacks
# home_name Detroit Tigers
# rng_seed 1
# line_ARI 0,0,0,1,0,0,0,0,0
# line_DET 1,0,0,0,2,0,0,0
# winner_name Hal Newhouser
# loser_name Randy Johnson
# recap One sentence.
```

A batting row uses `Player`, `Team`, `AB`, `R`, `H`, `HR`, `RBI`, `BB`, `SO`. A pitching row uses `IP`. Put runs allowed in `RA` (or `R` when the row is pitching only), hits allowed in `H_allowed` or `H`, walks allowed in `BB_allowed`, and strikeouts in `SO_allowed` or `SO`. `Role` may be `B` or `P`. A header of `Player,AB,R,H,RBI,BB,SO` is enough for a GameChanger batting export when a `Team` column is present. A Game Pulse export can use the same columns and add `IP` on pitching rows.

```
python3 scripts/import_game.py samples/boxscore.csv
```

That writes `imports/<id>.json` and `imports/<id>.detail.json` and prints `shape check passed`, or exits 1 and lists the mismatches. `imports/` is gitignored. The sample file is a fictional Diamondbacks at Tigers box. It is there to show the columns. It is not a tournament result and it must not be copied into `tournament_results.json`.

## Merging, later

Merging is a separate step, and it is not done by these tools. Joe checks the JSON, puts the real rolls in the detail file, and updates the series wins, team records, and `games` array so `python3 scripts/validate_results.py` still passes. Then `python3 scripts/build_leaders.py` rewrites the leaders, feeds, odds, share pages, and the weekly recap.
