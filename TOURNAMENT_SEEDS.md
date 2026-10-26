# Payoff Pitch Tournament 32 — Seeds

This is the only seed table. It is the corrected table from Joe's seed reset of 2026-10-24, as amended the same day. Dated rulings, the table this one replaced, and the voided opening series are in [CHANGELOG.md](CHANGELOG.md).

Six seeds are Joe's picks. They are pins, and they override index order:

| Seed | Club | Why it is a pin |
|---:|---|---|
| 1 | New York Yankees | Joe's pin. Also #1 on the index. |
| 17 | Philadelphia Athletics | Joe's pin. No index on the graphic. The stored 699.2 is an estimate. |
| 22 | Oakland Athletics | Joe's pin. Index of record 800.6, the merged Athletics value. |
| 27 | Montreal Expos | Joe's pin. No index on the graphic. The stored 543.2 is an estimate. |
| 31 | Washington Nationals | Joe's pin. Index of record 570.8. |
| 32 | Miami Marlins | Joe's pin. Also last on the index. |

The other 26 clubs fill the remaining slots by their Full 26 Index, from Joe's Legacy Lore graphic "ALL-TIME FULL-FRANCHISE RANKINGS, Top 30 MLB teams by Full 26-Man Index" (Engine v0.9.8 + Slot Scoring v1, Big Moments ON), sent 2026-10-22. Full 26 Index is starting nine plus bench plus rotation plus bullpen. It is an additive roster-strength index, not projected wins.

These seed numbers are the original seeds for every later reseeding. The bracket map is [BRACKET.md](BRACKET.md). Format rules are [TOURNAMENT_RULES.md](TOURNAMENT_RULES.md).

## Seed table

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

## Index estimates for Philadelphia and Montreal

Philadelphia and Montreal were never on the graphic, and their slots are Joe's pins. The index numbers above are calibrated estimates, recorded for reference. They did not place the clubs.

The estimates are an ordinary least-squares regression of the graphic's index values on Legacy Lore Studio APEX roster sums, over the same 26-man rosters (career-sum field). Oakland and Washington were left out of the fit because their graphic values describe the merged franchises. The fit was R² 0.947, residual standard deviation 42.6, leave-one-out RMSE 44.2. Philadelphia estimates at 699.2, with an APEX_100 cross-check of 718.6. Montreal estimates at 543.2, with a cross-check of 545.7.

The regression script and its output file are not in this repository. Whether they should be added is an open question in [TOURNAMENT_RULES.md](TOURNAMENT_RULES.md).

The amendment that put Philadelphia at #17 accepted this estimate's #17-ish place on the index scale once Oakland is counted at its index position. That history is in the changelog. The table above is the one that governs.
