# Adding a game

The site form and a plain `scripts/import_game.py` run write a preview only. `--apply` and the inbox workflow are what put a new game on the book. None of them change a score that is already stored.

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

## From a file

`scripts/import_game.py` reads three shapes.

A GameChanger-style or Game Pulse-style CSV:

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

A markdown box score uses the same layout as the R1-03 file. A whole series can live in one file. Each game starts with a heading:

```
# R1-04 Game 1: Arizona Diamondbacks at Detroit Tigers
```

Under that, a linescore table (`Team`, innings, `R`, `H`, `E`; `x` when the home club did not bat), a decisions line (`W:`, `L:`, and `SV:` with the club in parentheses), then `## Club batting` and `## Club pitching` tables. Batting columns are `#`, `Player`, `AB`, `R`, `H`, `2B`, `3B`, `HR`, `RBI`, `BB`, `SO`, `HBP`, `SB`, `CS`, `SAC`, `GIDP`. A `*` on the name marks a substitute. Pitching columns are `Player`, `IP`, `H`, `R`, `ER`, `BB`, `SO`, `HR`, `HB`, `BF`. A `Pitches` column is stored when the file has one. Optional lines: `**Date:** YYYY-MM-DD`, `**Seed:** 123`, `**Game recap:**`, `**Series state after this game:**`.

```
python3 scripts/import_game.py path/to/series.md
python3 scripts/import_game.py path/to/series.md --check
python3 scripts/import_game.py path/to/series.md --apply
```

The first command only writes a preview under `imports/`. `--check` compares the file with games already stored and changes nothing. `--apply` adds games that are not already in the archive, updates that series' wins and the club records from the games, runs `scripts/validate_results.py`, and regenerates leaders, rosters, feeds, odds, share pages, and graphics. If the new game differs from a stored line, or if it would edit R1-01, R1-02, or R1-03, the command stops and restores the archive. It does not invent rolls. The detail file keeps an empty `rolls` array until Joe adds the real log.

## Inbox

Put the `.md` or `.csv` in [`inbox/`](inbox/) on `main`. [`.github/workflows/inbox.yml`](.github/workflows/inbox.yml) runs on that push, and from the Actions tab (Run workflow). It imports every box score in the folder, validates, regenerates, commits, and deploys. The same push also starts the Tournament site workflow, which deploys again.

A file that fails is left in `inbox/`. The reason is committed to `inbox/errors/<name>.txt`. A file that lands moves to `inbox/imported/`. The workflow's token needs permission to push to `main` (Actions, workflow permissions, read and write).

## Posting a final

After the Tournament site workflow deploys `main`, it runs `scripts/announce.py`. The step posts each new final's score graphic and share link. It posts to Discord when the repository secret `DISCORD_WEBHOOK_URL` is set. It posts to X when all four of `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, and `X_ACCESS_TOKEN_SECRET` are set. If a secret is absent, that destination is skipped and the step still succeeds. No secret is written into the repo, and none are set by this change.

Create the secrets in the repository settings, under Secrets and variables, Actions. The Discord value is the channel webhook URL. The X values are the app's consumer key and secret plus the user access token and token secret, with permission to post. A push that does not add a game posts nothing.

## Merging, later

Joe can still merge a preview by hand. He checks the JSON, puts the real rolls in the detail file, and updates the series wins, team records, and `games` array so `python3 scripts/validate_results.py` still passes. Then `python3 scripts/build_leaders.py` rewrites the leaders, feeds, odds, share pages, and the weekly recap. `--apply` and the inbox workflow do that bookkeeping for a new game. They do not replace a line that is already stored.
