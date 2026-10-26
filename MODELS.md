# Display models

These formulas drive the awards race, the win-probability chart, and the series-odds bars. They are display models. They do not change a box score, a series score, or a seed. [AWARDS.md](AWARDS.md) and [RECORDS.md](RECORDS.md) are the current tables, generated from `tournament_results.json`.

## Awards

Points are not an official vote and they are not a Major League award.

- MVP, hitters: total bases + R + RBI + SB + 0.5×BB + 0.5×HBP − CS. Total bases = H + 2B + 2×3B + 3×HR.
- Cy Young, pitchers with at least one start (`appearance_order` 1): IP + 0.4×K + 5×W − 1.5×ER − 0.3×BB. IP is outs / 3.
- Reliever, pitchers with zero starts: 5×SV + 2×IP + 0.4×K − 1.5×ER.

A pitcher who has started is only on the Cy Young list. Saves on that pitcher's line do not move him to the reliever list.

## Series MVP

A finished series scores every player from the box scores in that series only. It does not change a game, a series score, or a name stored on the series file.

- A hitter uses the MVP line above.
- A pitcher uses IP + 0.4×K + 5×W + 3×SV − 1.5×ER − 0.3×BB. IP is outs / 3. Wins and saves are the stored decisions on each game.
- A player who both hit and pitched keeps the higher of the two scores.
- The higher score is the series MVP. The next score is the runner-up. A tie goes to the name that sorts first.

## Win probability

Win probability is a display model, not a simulation, and the game page labels the chart as a model estimate. It is not a recorded probability and it does not change the final score. Before the first pitch the home club is 0.50. After each step the home win probability is 1 / (1 + exp(−1.35 × margin / sqrt(innings left))), where margin is home runs minus away runs and innings left is max(0.5, 9.5 − inning − 0.5 when the half is the bottom). An extra inning uses that 0.5 floor. The chart is omitted when the game has no inning arrays, or when those arrays do not add up to the stored score.

The steps come from the line score: one point per half-inning that is actually in the array, including a zero. A half the home club did not bat is absent, not drawn as a zero. A multi-run half is one step. The file does not say the order of those runs, so the chart does not split them.

When `scoring_plays` is stored and every play names its inning and a score that advances one club at a time to the final score, those plays replace the scoring halves. A Payoff Pitch play carries both club codes. An APBA play ends in a pair of numbers; the chart uses that pair only in the club order that lands on the stored final score. A half with no runs stays a line-score step. If the plays do not match the line, the chart uses the line score alone.

## Daily highlight

The home page card "On this day" is not a model. It walks a fixed list of recorded moments: no-hitters, games of 10 or more strikeouts, walk-offs, games of 10 or more runs, and completed series, the same bars as the records and history pages. The calendar date picks the index `day number mod list length`. The same date always shows the same moment. The card states the stored game date when one exists. It does not invent a moment or a date.

## Series odds

Series odds are a display model. Each remaining game is an independent 0.55 win for the higher seed. The bar is the probability that club reaches 4 wins before the other club does. A completed series shows the winner at 1.

## Peak 162 series projection

An upcoming series, scheduled or in progress, can show a projection on the bracket and on the series preview. The projection is a display model. It does not change a game, a series score, or a seed. It describes the series as the clubs are paired now. After a round is re-seeded, the next pairing is projected again from the clubs in that pairing.

The source is the owner card and the stored Peak 162 line. A club with no announced roster is not rated. Offense is the mean OPS on the lineup spots whose stored peak text has an OPS. Pitching is the mean ERA on the rotation spots whose stored peak text has an ERA. A spot with no stored line is left out of the mean. It is not a zero. If either mean is missing, that club is not rated, and the series says Odds TBD.

Among the announced clubs that have both means, the league OPS is the mean of those offense means and the league ERA is the mean of those pitching means. A club's win percentage against a league-average roster is o² / (o² + e²), where o is the club OPS divided by the league OPS and e is the club ERA divided by the league ERA.

One game is the log5 of the two win percentages. If those percentages are a and b, the first club's chance is (a × (1 − b)) / (a × (1 − b) + b × (1 − a)). The series chance is the probability that club reaches 4 wins before the other one does. Wins already stored on the series count. Each remaining game is an independent trial at the log5 probability. The page labels the figure Projection.

## Run differential

Run differential is runs scored minus runs allowed, summed from the game scores. It is not a model.

## Milestones

Taken only from recorded lines:

- No-hitter: a start (`appearance_order` 1) of at least 27 outs with 0 hits.
- High-strikeout game: a pitching line with at least 10 strikeouts.
- Big scoring game: a club score of at least 10 runs.

## Monte Carlo series and title odds

`feed/odds.json` is a second display model, rebuilt by `scripts/build_leaders.py`. The bracket and the series pages use it when the file is present. The 0.55 higher-seed model above stays in the page for a fallback and is still the closed form in [MODELS.md](MODELS.md).

A club's chance to win one game against another is 1 / (1 + exp(−(index A − index B) / 80)). There is no home-field edge. Each series is played out to 4 wins from the games already on the book. The bracket then reseeds the way [BRACKET.md](BRACKET.md) describes, including a fresh F-02 when the one-loss finalist wins F-01. Four thousand draws use a fixed seed, so the file does not change between rebuilds. A finished series is recorded as 1 for the winner and 0 for the loser, not resimulated. A shown 0.0 means that side won none of the 4,000 draws. It is not a mathematical zero. Joe can change the scale in `scripts/odds.py` if the gaps should produce more upsets. The simulation does not edit a score or a seed.

## Leaders page

The Leaders page reads the played games already on the site. It does not invent a stat and it does not change a box score. Plate appearances, the 10 plate-appearance minimum, the 5-inning minimum, and the counting tie rule are the same limits as [LEADERS.md](LEADERS.md).

- Batting average is hits divided by at-bats, for a player with at least 10 plate appearances. Plate appearances are AB + BB + HBP + SAC + SF as recorded.
- OPS is on-base percentage plus slugging, with that same plate-appearance minimum. On-base percentage is (H + BB + HBP) / (AB + BB + HBP + SF). Slugging is total bases divided by at-bats. Total bases are H + 2B + 2×3B + 3×HR.
- Home runs, runs batted in, hits, runs, and stolen bases are the counting totals. The list is the top 10, and anyone tied with the tenth player stays.
- ERA is 27 × ER / outs, for a pitcher with at least 15 outs. WHIP is (H + BB) × 3 / outs, with the same minimum. Hit batsmen are not in WHIP.
- Wins, strikeouts, and saves are counting totals. A win is the W decision and a save is the S decision.

A pushed game is on the page when that game is in the loaded archive. The page is rebuilt with the site. No second board is stored.

## Peak 162

Peak 162 is a display line on an owner's roster card. It is not a tournament stat and it does not change a box score. The source is the Lahman database, 2025 edition (CRAN package Lahman 14.0-0), seasons 1871 through 2025. The 2026 season is not in that file. Lahman does not publish WAR, so the window is not chosen by WAR.

A franchise season is a year with a batting or pitching stint for that tournament club's franchise only. A mid-season stint with another club is left out. Consecutive means the next season in that list. A year the player did not play for the franchise is not a zero season and is not inside the totals. The label years are the first and last year of the chosen window.

The window is the best 5 of those seasons when the player has at least 5. With 3 or 4, it is the best 3. With fewer than 3, it is every season, and the line says so. Hitters are ranked by league OPS+ on the window's combined totals: 100 times (OBP divided by the league OBP, plus SLG divided by the league SLG, minus 1). Pitchers are ranked by ERA+ times innings. ERA+ is 100 times the league ERA divided by the pitcher's ERA. There is no park adjustment. League rates are the Lahman team totals for that league and year, weighted by the player's plate appearances or outs in the window. A shutout window is ranked as if it had allowed half a run, so the rank stays finite. The printed ERA still uses the real earned runs. Missing hit-by-pitch and sacrifice-fly cells in Lahman are treated as zero, which is how that file records them.

Counting stats are then scaled. Hitters scale to 162 games. A rotation card scales to 34 starts. A bullpen card scales to 65 appearances. The roster slot sets that choice. Honorable mentions and what-if names with no slot are pitchers when they have fewer than 200 franchise plate appearances, or at least 10 franchise starts, or at least 50 franchise innings. Among those, they are starters when franchise starts are at least half their appearances, and relievers otherwise. A hitter who only mopped up stays a hitter. Rates are computed from the unscaled totals, then rounded half up. Counting stats, including outs, are rounded half up. AVG, OBP, SLG, and OPS are three decimals. ERA and WHIP are two. Strikeouts per nine are one.

A hitter's line also shows pitching when the pitching window has at least 10 starts or 50 innings. A pitcher's line also shows batting when the batting window has at least 200 plate appearances and those appearances are more than eight times his pitching appearances in that window, so a pitcher who only batted on the days he pitched does not get a second line.

The label is `Peak 162 with <club> (YYYY–YYYY)`. One season prints a single year. Players who cannot be matched, or who have no franchise seasons, say `Peak stats unavailable`.

Philadelphia Athletics use only the 1901–1954 Athletics (Lahman team `PHA`). Oakland uses only Oakland seasons from 1968 on, including the 2025 Athletics team id `ATH`, and not the Kansas City Athletics. Montreal uses only the Expos, 1969–2004. The Nationals card is not applied: that club has already played. Other clubs use the franchise team ids in `scripts/build_peak162.py`, including Brooklyn for the Dodgers, the Boston and Milwaukee Braves, the 1961–1971 Senators for the Rangers, the 1901–1960 Senators for the Twins, the Browns for the Orioles, and the Pilots for the Brewers. The Pilots are not Mariners seasons. The 1882 American Association Athletics are not the Philadelphia Athletics card.

Clubs that have already played and have no owner card on this page (Yankees, Giants, Red Sox, Rays, Diamondbacks, Marlins, and Nationals) do not get a Peak 162 line. Their game pages are unchanged.

## Share graphics

`graphics/games/` and `graphics/series/` are drawn from the final score and the series wins. They are for sharing. They are not a second box score.
