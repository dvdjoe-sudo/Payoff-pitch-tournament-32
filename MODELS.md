# Display models

These formulas drive the awards race, the win-probability chart, and the series-odds bars. They are display models. They do not change a box score, a series score, or a seed. [AWARDS.md](AWARDS.md) and [RECORDS.md](RECORDS.md) are the current tables, generated from `tournament_results.json`.

## Awards

Points are not an official vote and they are not a Major League award.

- MVP, hitters: total bases + R + RBI + SB + 0.5×BB + 0.5×HBP − CS. Total bases = H + 2B + 2×3B + 3×HR.
- Cy Young, pitchers with at least one start (`appearance_order` 1): IP + 0.4×K + 5×W − 1.5×ER − 0.3×BB. IP is outs / 3.
- Reliever, pitchers with zero starts: 5×SV + 2×IP + 0.4×K − 1.5×ER.

A pitcher who has started is only on the Cy Young list. Saves on that pitcher's line do not move him to the reliever list.

## Win probability

Win probability is a display model, not a simulation. Before the first run the home club is 0.50. After each scoring event the home win probability is 1 / (1 + exp(−1.35 × margin / sqrt(innings left))), where margin is home runs minus away runs and innings left is max(0.5, 9.5 − inning − 0.5 when the half is the bottom).

Scoring plays are read from the archive. A Payoff Pitch play carries both club codes and the score. An APBA play's trailing pair is home-away. When a game has no scoring plays, the same curve is stepped through the line score, top then bottom, one run at a time, and the chart is labeled as a line-score fallback.

## Series odds

Series odds are a display model. Each remaining game is an independent 0.55 win for the higher seed. The bar is the probability that club reaches 4 wins before the other club does. A completed series shows the winner at 1.

## Run differential

Run differential is runs scored minus runs allowed, summed from the game scores. It is not a model.

## Milestones

Taken only from recorded lines:

- No-hitter: a start (`appearance_order` 1) of at least 27 outs with 0 hits.
- High-strikeout game: a pitching line with at least 10 strikeouts.
- Big scoring game: a club score of at least 10 runs.

## Share graphics

`graphics/games/` and `graphics/series/` are drawn from the final score and the series wins. They are for sharing. They are not a second box score.
