# Payoff Pitch Tournament 32 — Results schema

`schema_version` is **1**. This file describes `tournament_results.json` and the per-game files in `games/`. `scripts/validate_results.py` checks the archive against this shape and against the stat lines that were on record before the split.

`version` is the archive version that was already on the file (currently 1). It is not `schema_version`.

Player stats are stored per `(team, player_id)`. A player on two clubs has one line per club. The two Robb Nen lines, San Francisco and Miami, stay separate.

## Files

| File | What it holds |
|---|---|
| `tournament_results.json` | Format, teams, all 63 series slots, and a summary of every completed game. |
| `games/<id>.json` | That game's `rolls` and `manager_log`. The summary links here with `detail`. |

The summary is the box score. The detail file is the only copy of the rolls and the manager log. Scores and stat lines were not rewritten when the files were split.

## Top level

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | number | This document. Currently 1. |
| `version` | number | Pre-existing archive version. |
| `format` | object | Tournament format strings and flags: `best_of`, `series_target_wins`, `double_elimination`, `no_byes`, `teams`, `chart`, `home_pattern`, `formation_gate`, `final`. |
| `stat_keying` | string | The per-team player identity note above. |
| `teams` | array | 32 clubs. |
| `series` | array | 63 slots. |
| `games` | array | One summary object per completed game, in archive order. |

## Team

| Field | Type | Meaning |
|---|---|---|
| `seed` | number | Original tournament seed. This is the reseeding key. It is not an RNG seed. |
| `code` | string | Club code. |
| `name` | string | Club name. |
| `index` | number | Full 26 Index. Philadelphia and Montreal are the calibrated estimates. |
| `game_wins`, `game_losses` | number | Games won and lost. |
| `series_wins`, `series_losses` | number | Series won and lost. |
| `eliminated` | boolean | True at two series losses. |
| `champion` | boolean | True for the tournament champion. |
| `bracket` | string | `winners`, `losers`, or `eliminated`. |
| `losses` | number | Series losses. Same quantity as `series_losses`. Zero is the winners bracket, one is the losers bracket, two is eliminated. |

`bracket` is derived from the record, not stored as a separate opinion. `eliminated` or `series_losses >= 2` maps to `eliminated`. One series loss maps to `losers`. Zero maps to `winners`, including a club that has not played. The opening round is part of the winners bracket.

## Series

Every slot has `id`, `side`, `label`, `team_a`, `team_b`, `seed_a`, `seed_b`, `team_a_side`, `team_b_side`, `home_pattern`, `home_by_game`, `wins`, `games`, `status`, `winner`, and `loser`.

`games` is a list of game ids. The box score is the matching object in the top-level `games` array.

`status` is `complete`, `in-progress`, `scheduled`, or `awaiting-feeders`. `in-progress` means games are on the series and neither club has 4 wins yet. `winner` and `loser` stay null until the series is complete.

Opening-round ids are `R1-01` through `R1-16`. Later ids are `W2`–`W5`, `L1`–`L8`, `F-01`, and `F-02`.

Optional fields, present only where the archive had them:

| Field | Where |
|---|---|
| `round` | Completed opening series, and every shell after the opening round. |
| `stage`, `formation`, `feeders`, `feeder_labels` | Shells after the opening round. `formation.pool` and `formation.gate` say what the slot is waiting on. |
| `provenance`, `carry` | R1-02 and R1-03. `carry.rotation_next_start` is the next starter named for each club. |

R1-01, R1-02, R1-03, and R1-04 set `round` to 1. Unplayed opening shells R1-05 through R1-16 do not carry `round`. They were left as stored. Whether they should say 1 is an open question in [TOURNAMENT_RULES.md](TOURNAMENT_RULES.md).

`home_by_game` is filled for a paired series. Keys are game numbers `"1"` through `"7"`. An unfilled shell has an empty object.

## Game summary

| Field | Type | Meaning |
|---|---|---|
| `id` | string | `R1-01-G1`, `R1-02-G3`, and so on. |
| `series_id` | string | Series id. |
| `game_in_series` | number | 1-based game number inside the series. |
| `date` | string or null | Calendar date, `YYYY-MM-DD`, when known. Every R1-02 game, and R1-03 Games 1 and 2, are `2026-10-24`. R1-03 Games 3-7 have no per-game date. R1-01 games are null. |
| `away`, `home` | string | Club codes. |
| `teams` | object | Code to display name, for the two clubs. |
| `score` | object | Code to runs. |
| `line` | object | Code to a list of inning runs. The home list is shorter when the home club did not bat in the last inning. |
| `winner` | string | Club code. |
| `wls` | object | `W`, `L`, and `S`. Each decision is `{team, player_id, name}` or null. `S` is null when there was no save. |
| `resolutions` | object or null | APBA board / model / unparsed counts. Null on a Payoff Pitch game. |
| `batting` | array | Batting lines. See below. |
| `pitching` | array | Pitching lines. See below. |
| `errors_by` | array | `{team, player_id, name, errors}`. |
| `team_errors` | object | Code to error total. |
| `final_grades` | object | Grade letter by `TEAM\|player_id`, or empty. |
| `game_recap`, `series_recap` | string | Prose recaps stored with the game. |
| `rng_seed` | number | The RNG seed the game was simulated with. This field was named `seed` before schema 1. The number was not changed. |
| `detail` | string | Relative path of the detail file, `games/<id>.json`. |
| `injuries` | array | Injury notes. Empty when none were recorded. |
| `n41` | number or null | Card-41 count. Null on a Payoff Pitch game. |
| `caps_in`, `caps_out` | object | Availability caps by club, when recorded. |

Optional, present only on the games that had them: `scoring_plays` (array of strings), `fatigue_end_states`, `grade_log`, `starting_grades`, `bfr`, `team_sb`, `team_cs`. R1-01-G2 has no `scoring_plays` and no manager log.

### Batting line

`team`, `player_id`, `name`, `lineup_slot`, `entry_order`, `is_substitute`, `ab`, `r`, `h`, `rbi`, `bb`, `k`, `hbp`, `sb`, `cs`, `sac`, `sf`, `gidp`, `ibb`, `doubles`, `triples`, `hr`.

`sf` and `ibb` are null on Payoff Pitch lines. The series provenance says those states were not split out; `sac` is the single sacrifice category. A null is not a zero. Some lines also carry `entry_inning` and `entry_half`.

The results file does not record a defensive position.

### Pitching line

`team`, `player_id`, `name`, `appearance_order`, `outs`, `h`, `r`, `er`, `bb`, `k`, `bf`, `hb`, `entry_diff`, `entry_inning`.

`outs` is outs recorded, not baseball innings. 23 outs is 7.2 innings. Payoff Pitch lines also carry `hr`. `hb` is null when the source did not record hit batsmen by pitcher. `entry_diff` is null on those lines.

`appearance_order` 1 is the starter.

## Game detail

`games/<id>.json`:

| Field | Meaning |
|---|---|
| `id`, `series_id`, `game_in_series` | The same identity as the summary. |
| `rolls` | The play record, verbatim. |
| `manager_log` | Array of strings, or null. R1-01-G2 has null. |

### Two roll shapes

Both are stored as they were recorded.

- APBA games (R1-01) store an object per plate appearance: `seq`, `inning`, `half`, `team`, `batter`, `player_id`, `roll`, `card_first`, `prn`, `second_column`, `column`, `kind`, `result_text`, `source`, plus any extra key that appearance had.
- Payoff Pitch games (R1-02 and R1-03) store a two-item array, `[number, purpose]`. The series provenance says this is the FAC flip history, card number and draw purpose.

## Dates

| Series | `date` |
|---|---|
| R1-02 and R1-03, every game | `2026-10-24` |
| R1-01, and any game whose date is unknown | `null` |

## What schema 1 does not change

Series winners, series scores, game scores, inning lines, batting lines, pitching lines, decisions, and the numeric RNG seeds. Renames and added fields are the ones in this document.

## Roster and card data

Two generated files sit beside the results file. They are not part of schema 1 and no locked check covers them. `scripts/build_cards.py` writes both from the converted set files and the master archive; rerunning it with unchanged inputs rewrites byte-identical files.

`data/rosters.json` is keyed by club code: `code`, `name`, `seed`, `played` (whether the club has a game in the archive), and `players`, the roster spots in set order. Each spot is `id`, `name`, `group` (`lineup`, `bench`, `rotation`, or `bullpen`), `slot` within the group, `pos` as the set carries it, and `kind` (`hitter` or `pitcher`). A two-way player holds two spots; Babe Ruth is Boston's bench spot 6 and bullpen spot 7.

`data/cards.json` is keyed `CODE|player_id`, the way `data/bios.json` is keyed. Each entry carries `id`, `name`, `team`, the player's `spots`, and four blocks, any of which can be null:

| Block | Contents |
|---|---|
| `peak_bat` | The prime-window batting line from the hitter card's own stat line, counting fields as recorded, plus `window_years` and the line's `team_line`. |
| `peak_bat_162` | The same window as a 162-game average, the form the player page displays: every counting field scaled by 162 / window games and rounded half up, `G` shown as 162, plus `window_years`, `team_line`, and the raw `window_games`. AVG, OBP, and SLG are not carried here; the viewer computes them from `peak_bat`, so the rates are the window's own. |
| `peak_pit` | The prime-window pitching line: W and L, IP, H, HR, BB, SO, HBP, and BF from the v2 card's input row, plus G, GS, SV, R, and ER from the set inputs, and `window_years`. |
| `peak_pit_162` | The same window as an average season on a 162-game schedule, the form the player page displays: the per-season average (window total / window seasons) rescaled by (162 x seasons) / `team_games`, the club's total team games across the window seasons from the Lahman Teams table, which multiplies out to window total x 162 / `team_games`. Counting fields round half up; IP is scaled in outs (`ip_outs`) and rendered back in baseball thirds (`ip`, so "307.1" is 307 and a third). The block also carries `window_years`, `seasons`, and `team_games`; a window season with no Lahman row for the club counts as 162 team games and is named in `team_games_fallback` and in the generator's build log. ERA is not carried here; the viewer computes it from `peak_pit`, unchanged. |
| `card_bat` | The converted hitter card: bats, throws, `positions` (pos, range, e, arm), `sections` (the four sections, each hand, each result a percentile band or null), `out_table`, `dp`, `steal` (jump and rating), `run`, `sac_bunt`, the stat line's fielding and arm labels, and the set's QA status. |
| `card_pit` | The converted v2 pitcher card: throws, `card_type`, the `table_2d6` section map, `so_modifier`, `special` ratings, the addendum `stamina` (start number, relief class), the addendum ratings (wp, dp, hold, pickoff, inj), and the card's QA classification. |
| `tournament` | The player's line aggregated from the master archive only: `batting` and `pitching` counting lines (pitching carries outs, not innings) and the `games` he appears in, in archive order. Null when he has no appearance; Philadelphia, Montreal, and Chicago players are all null today. |

Player ids are the Lahman ids from the set inputs, unless the published results file already carries the same player under a different id; the published id wins so links keep working, and the generator prints each such case as a reconciliation. McClanahan is the one case today: `mcclash01` in the inputs and the master archive, `mcclasha01` here.
