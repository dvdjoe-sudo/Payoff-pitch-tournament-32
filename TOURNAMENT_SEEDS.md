# All-Time Team Tournament: Seeds (32 teams)

Corrected table, Joe's seed reset of 2026-10-24. This table
governs. The 2026-10-23 table it replaces is preserved
below under SUPERSEDED.

## The reset (Joe, 2026-10-24)

Joe reset the Round 1 seeding and, with it, all Round 1
games except Yankees vs Marlins, the only series left in
the official posted results. The voided Giants-Expos and
Red Sox-Philadelphia series are archived in full in
superseded_r1_02_r1_03_seed_reset_2026-10-24.json.

Six slots are JOE-PLACED pins, recorded as such; they
override the index order:

- #1 New York Yankees (also #1 on the index)
- #17 Philadelphia Athletics (no index on the graphic;
  pinned at #14 in the reset, moved to #17 by Joe's
  amendment below)
- #22 Oakland Athletics (index of record 800.6, the merged
  Athletics value; the slot is Joe's placement)
- #27 Montreal Expos (no index on the graphic)
- #31 Washington Nationals (index of record 570.8; the
  slot is Joe's placement)
- #32 Miami Marlins (also last on the index)

The other 26 teams fill the remaining slots strictly by
their Full 26 Index from Joe's Legacy Lore graphic
"ALL-TIME FULL-FRANCHISE RANKINGS, Top 30 MLB teams by
Full 26-Man Index" (Engine v0.9.8 + Slot Scoring v1, Big
Moments ON), sent 2026-10-22. Full 26 Index = starting
nine + bench + rotation + bullpen; an additive
roster-strength index, not projected wins.

Philadelphia and Montreal index values: the split teams
were never on the graphic and the v0.9.8 engine is not in
the workspace, so their values below are calibrated
estimates (2026-10-24), recorded for reference only;
their slots are Joe-pinned, not estimate-placed. Method:
OLS regression of the graphic's index values on Legacy
Lore Studio APEX roster sums over the same APBA 26-man
rosters (Career-sum field; fit excluding Oakland and
Washington, whose graphic values describe the merged
franchises: R2 0.947, residual SD 42.6, leave-one-out
RMSE 44.2). Philadelphia estimates at 699.2 (APEX_100
cross-check 718.6); Montreal at 543.2 (cross-check
545.7). Full record: conversion_work/index_calibration.py
and index_calibration.json.

## Amendment (Joe, 2026-10-24)

Later the same day, Joe moved Philadelphia's pin from
#14 to #17, accepting the calibration estimate's #17-ish
placement (estimate 699.2, which sits #17 on the pure
index scale once Oakland is counted at its index
position). The White Sox (764.1), Orioles (758.4), and
Astros (668.5) each rose one slot by index, to #14, #15,
and #16. The pin set is now Yankees #1, Philadelphia
#17, Oakland #22, Montreal #27, Washington #31, Miami
#32. Only three Round 1 pairings changed (R1-14 White
Sox vs Mariners, R1-15 Orioles vs Royals, R1-16 Astros
vs Philadelphia); no played result was affected, R1-01
remaining the only posted series. The table below is
the amended table and governs.

| Seed | Team | Full 26 Index | Placement |
|---:|---|---:|---|
| 1 | New York Yankees | 1021.6 | Joe-placed pin |
| 2 | San Francisco Giants | 971.2 | index |
| 3 | Boston Red Sox | 942.9 | index |
| 4 | Detroit Tigers | 922.1 | index |
| 5 | St. Louis Cardinals | 872.1 | index |
| 6 | Chicago Cubs | 864.4 | index |
| 7 | Atlanta Braves | 857.5 | index |
| 8 | Pittsburgh Pirates | 830.6 | index |
| 9 | Cincinnati Reds | 814.3 | index |
| 10 | Los Angeles Dodgers | 810.9 | index |
| 11 | Philadelphia Phillies | 809.1 | index |
| 12 | Minnesota Twins | 808.5 | index |
| 13 | Cleveland Guardians | 801.2 | index |
| 14 | Chicago White Sox | 764.1 | index |
| 15 | Baltimore Orioles | 758.4 | index |
| 16 | Houston Astros | 668.5 | index |
| 17 | Philadelphia Athletics | 699.2 (est.) | Joe-placed pin |
| 18 | Kansas City Royals | 647.4 | index |
| 19 | Seattle Mariners | 606.1 | index |
| 20 | Los Angeles Angels | 605.6 | index |
| 21 | New York Mets | 600.6 | index |
| 22 | Oakland Athletics | 800.6 | Joe-placed pin |
| 23 | Milwaukee Brewers | 569.9 | index |
| 24 | Texas Rangers | 566.2 | index |
| 25 | Toronto Blue Jays | 565.6 | index |
| 26 | San Diego Padres | 494.7 | index |
| 27 | Montreal Expos | 543.2 (est.) | Joe-placed pin |
| 28 | Colorado Rockies | 467.4 | index |
| 29 | Arizona Diamondbacks | 442.8 | index |
| 30 | Tampa Bay Rays | 387.0 | index |
| 31 | Washington Nationals | 570.8 | Joe-placed pin |
| 32 | Miami Marlins | 385.9 | Joe-placed pin |

Format notes (unchanged):
- 32 teams, standard static double-elimination chart
  (BRACKET.md): winners bracket 16/8/4/2/1 series by
  round, losers bracket drop-in rounds 8/8/4/4/2/2/1/1,
  grand final plus one reset series if the one-loss
  finalist wins the first final. 62 series total, 63 with
  the reset. No byes.
- A team is eliminated on its second series loss.
- Every matchup is a best-of-7 series; home pattern
  2-2-1-1-1, higher seed home first (TOURNAMENT_RULES.md).
- Rotation rule from TOURNAMENT_RULES.md (full five-man
  cycle, carries across rounds) applies to every series.
- The reseeded numbers above are the original seeds for
  all downstream stage reseeding under Joe's reseeding
  rule (2026-10-23).

---

## SUPERSEDED (2026-10-23 table, replaced 2026-10-24)

Source for seeds 1-29 and 32: Joe's Legacy Lore graphic
"ALL-TIME FULL-FRANCHISE RANKINGS, Top 30 MLB teams by
Full 26-Man Index" (Engine v0.9.8 + Slot Scoring v1, Big
Moments ON), sent 2026-10-22. Full 26 Index = starting
nine + bench + rotation + bullpen; an additive
roster-strength index, not projected wins.

32-team conversion (Joe, 2026-10-23: "Go to 32 teams";
"easy one is split washington and expos"): the two merged
franchises split into their city teams. Seeds 1-29 are
unchanged. Oakland keeps the merged Athletics' #14 slot
and index; Washington keeps #22 and its index. The two
split-off teams take the bottom slots: Philadelphia
Athletics #30 and Montreal Expos #31 (Philadelphia's half
carries the stronger historical roster; Joe can flip this
order on his word). The Marlins slide from #30 to #32. No
Full 26 Index exists for Philadelphia or Montreal: the
split teams were never on the Top 30 graphic, and no index
number is invented for them.

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

Format notes (as of 2026-10-23):
- 32 teams, standard static double-elimination chart
  (BRACKET.md): winners bracket 16/8/4/2/1 series by
  round, losers bracket drop-in rounds 8/8/4/4/2/2/1/1,
  grand final plus one reset series if the one-loss
  finalist wins the first final. 62 series total, 63 with
  the reset. No byes.
- A team is eliminated on its second series loss.
- Every matchup is a best-of-7 series; home pattern
  2-2-1-1-1, higher seed home first (TOURNAMENT_RULES.md).
- Rotation rule from TOURNAMENT_RULES.md (full five-man
  cycle, carries across rounds) applies to every series.
- Cards status: all 32 teams are built on the
  prime-window basis (the four split teams built
  2026-10-23 from their own graphics; Philadelphia's
  graphic names 25 distinct players, so that team carries
  25 cards; see teams/pha/BUILD_REPORT.md).
