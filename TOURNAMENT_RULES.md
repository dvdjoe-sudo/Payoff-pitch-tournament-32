# Payoff Pitch Tournament 32 — Rules

Standing rules for every series in this tournament. Adopted 2026-10-22; rewritten 2026-10-25 under Joe's ruling of that date to state the Payoff Pitch governance that has actually applied since R1-02. Dated rulings are in CHANGELOG.md. Where this file and an earlier series note disagree, this file governs.

Seeds are only in TOURNAMENT_SEEDS.md. The bracket map is BRACKET.md. The game record is tournament_results.json and the per-game files kept with each series. The master archive in the workspace is the data source of truth; this repository is its published view.

## Provenance: R1-01

One series predates Payoff Pitch play. R1-01, New York Yankees 4-0 over the Miami Marlins, was played under APBA and adopted into this Payoff Pitch tournament by Joe's ruling of 2026-10-24. Its records stand exactly as played, it is never replayed, and nothing in the rules below is applied to it retroactively. Every other series in this tournament is played in Payoff Pitch under these rules.

## Rosters and converted sets

Every club carries **26 active players**: nine in the posted lineup, five in the starting rotation, and the remaining twelve divided between bench and bullpen. Five bench players and seven relievers is the **default**, not a mandatory split. The owner-approved canonical all-time roster and Joe's dated amendments govern each club; an explicitly approved roster may carry more bench players and fewer relievers, or vice versa. The current Dodgers, Cubs, Guardians, Reds and Cardinals rosters remain valid with their recorded bench/bullpen counts. The Philadelphia Athletics' 2026-10-27 approved change restores their active roster to 9/6/5/6 with Foxx at DH and Fain at 1B.

**Two-way players count once (Joe, 2026-10-27):** Roster limit counts **distinct players, not the number of role entries or cards**. One person listed as both a hitter and pitcher occupies one of the 26 active player places, while keeping separate batting/pitching eligibility and the corresponding authentic cards. In `data/rosters.json`, the same `id` may appear once for each eligible kind (hitter and pitcher); count that shared `id` only once toward 26. Boston Babe Ruth (`ruthba01`) is bench hitter slot 6 and additional bullpen pitcher slot 7: the Red Sox have 27 role entries but **26 unique active people**, so no one is removed. A second pitching role does not grant an automatic pitching exception to fatigue, rotation or relief restrictions, and does not authorize invented cards. Existing played games, card files and all dice/FAC records stay unchanged.

**Roster flexibility during the tournament (Joe, 2026-10-26):** bench and bullpen sizes and individual roster assignments may be changed as the tournament progresses, but only with Joe's approval. Record each change as a dated roster amendment before it takes effect, and keep the club at 26 active players. The newly approved roster governs subsequent games only; previously played games, their recorded lineups and cards, box scores, dice/FAC logs, and results remain unchanged. Where a staged or converted set differs from the latest approved roster, it must be reconciled before use; no mismatch authorizes an automatic player change.

A club's Payoff Pitch set is built when its fixture comes up, to the standing conversion standard:

- Prime windows are each player's five best franchise seasons, franchise play only, with floors of 300 plate appearances for hitters, 100 innings for starters, and 30 innings for relievers. Short windows are disclosed in the set's report.
- The 2026 rule (Joe, 2026-10-25): any active player's completed 2026 season counts like any other season in his prime window, franchise play only. A 2026 season played for another club does not count for the set.
- Cards are built only with the frozen engines (Hitter v0.5, Pitcher v0.2.3). Pitchers play on their version 2 cards. The pitcher addendum, with its measured and defaulted accounting, is part of every set.
- Fielding and arm labels come from the standing one-time mapping and are measured where the data measures; Joe reviews each set's label file, and a label he vetoes is re-run. A stress test verdict never authorizes a card edit by itself.
- A pitcher carded in a swing or long role is a bullpen arm, not a starter, and the starters-in-relief rule below does not bar him from pitching in relief.

**Card system (Joe's ruling, 2026-10-28).** As of 2026-10-28, all tournament cards are built with the new-generation engines only: the research hitting engine v1.2 (including the OUT coordination rule) and the smoothed pitcher grammar. The frozen Hitter v0.5 and Pitcher v0.2.3 engines and the v2 solver build path are retired as card-building tools; they are preserved, read-only, as the provenance of cards already played and as app downloads, and are never used to build, rebuild, or refit a card. The old governing cards are quarantined, labeled do-not-use, as the audit record. Series already played (R1-01 through R1-05) stand as played, on the cards of their day; the game-play engines that play games with current cards are unaffected.

## Play resolution

Games resolve on the FAC deck: the 256-card Fast Action Card deck mode is the tournament's mode, with the full governed stack for every game: version 2 pitcher cards, the pitcher addendum, the fatigue fix layer, both addenda rulings, and the managers' encoded traits. FAC chart mode exists and is proven, but deck mode is what tournament games use. Every governed game is reproducible from its recorded seed.

There is no home-field advantage adjustment. Home and away results are tracked, not handicapped.

## The designated hitter

Every club plays with the designated hitter in every series (Joe, 2026-10-26). No club plays NL-style. This settles the question the Open questions section previously carried about St. Louis; it is now closed. The ruling changes nothing already recorded: every governed series to date was played with a designated hitter, and every converted lineup carries a DH slot, so no recorded game, set file, or archive entry changes.

## Governance hierarchy

When rules speak to the same decision, they apply in this order (Joe's rulings):

1. The book's own mechanics first: pitcher fatigue and the Rest Chart.
2. The one house hard rule, below.
3. The managers' encoded traits, where they speak.
4. The hook policy and the closer branch, as default policy where nothing above them speaks.

## Pitcher fatigue

Fatigue runs on the shared fatigue fix layer, which wraps the engines and edits no engine file. Its off mode reproduces pre-fix games exactly. Standing named gap: no converted card carries a printed save symbol, and none is invented.

## The house hard rule: starters in relief

No starting pitcher appears in relief, except for a club facing elimination. A starter who does relieve has his next start pushed back one day. This is the tournament's only house hard rule.

## The closer branch

Default policy: in the ninth inning, with a lead of one to three runs, if the starter has recorded 21 or more outs, the closer comes in.

## Manager traits

Each club's manager governs under his encoded profile, built before the club's first game and proven in the sandbox battery before it governs. A profile is Joe's authored text, filed word for word; every place the encoding had to interpret the text is flagged in the traits specification for Joe's veto. Traits never override the book's mechanics or the house hard rule; they act inside the hierarchy above.

The designated hitter rule above has one recorded consequence here. Tony La Russa's Second Leadoff cannot fire under a DH: the sets carry no pitcher batting cards, so there is no pitcher's spot in the order for it to act on. His Double-Switch Master fires only in its combined-move form. Both mechanics stand as encoded.

## Rotation

Each club posts its rotation in order, all five starters, and starters take their turns in that order, one per game, cycling through the entire rotation before anyone starts a second time. The cycle carries across series: a club's next starter is whoever follows its last starter. There are no short-rest starts and no skipping a turn because a game is an elimination game. A starter removed during a game keeps his next scheduled turn unless the starters-in-relief rule above moves it.

## Availability

Inside a series, availability is governed by the book's Rest Chart and the addendum accounting, as applied in the governed series records. Between series, every arm resets: no cap and no unavailability carries into the next series, so no elimination game is decided before it starts by a previous series' workload.

## Scoring

The sacrifice play counts as a plate appearance but not as an at-bat (Joe, 2026-10-25). This includes the bunt fielder's choice in which the lead runner is thrown out and the batter is safe: the batter is credited with a sacrifice and a plate appearance, and no at-bat. The recorded lines of games already played were corrected to this rule under the same ruling; results and scores were not touched.

## Rare plays

A printed rare-play clause that reads "the next N batters this pitcher faces" is carried by count, and the count carries across inning breaks: the force states (wheelhouse, tough, in-play) are installed when the clause lands and are spent one per batter faced until the count runs out. A sacrifice bunt resolves at the bunt seam and spends no clause count; that seam is disclosed, not hidden.

## Parks

A club hosts on its real printed park card where one has been adopted by Joe's ruling: Detroit on the 1986 Tiger Stadium card, St. Louis on the 1986 Busch Stadium card, Arizona on Chase Field, Washington on Nationals Park. Every other club hosts on the standard composite card until Joe rules otherwise. Games already played on the composite stand as played; an adopted card governs from the club's next home game.

## Injuries and removals

There is no separate injury table and no dice-based injury check. A player leaves a game only as the Payoff Pitch resolution itself produces it (a chart removal, an ejection under a rare play, a hook, or a substitution), and the game record states what happened.

## Announced pinch hitter

Once a pinch hitter is announced, he is the batter of record. Replacing him before he bats is legal only as a substitution, and it consumes both players as used for the game.

## Reporting and the archive

Every governed game keeps the full data archive: the complete state file, the play-by-play and governance log, the flip-by-flip FAC history, complete batting and pitching lines in batting order, the substitution and pitching-change sequence, hook triggers, run attribution, availability in and out, and the seed. Categories the engine cannot produce are named honestly, never padded. Every series gets a Markdown data summary, and at its end a series summary naming a Series MVP and a runner-up when the race is close. Nothing in any archive is pruned; a superseded game or ruling is preserved in a labeled file, never deleted and never silently replaced.

## Tournament format

The field, the seed numbers, and the six Joe-placed pins are in TOURNAMENT_SEEDS.md. That file is the only seed table.

- 32 clubs. Every matchup is a best of 7. A club is eliminated when it loses its second series.
- No byes. All 32 clubs play the opening round, seeded straight: 1 against 32, 2 against 31, and so on through 16 against 17.
- The bracket is the 32-team double-elimination map in BRACKET.md. Winners stages are 16, 8, 4, 2, and 1 series, counting the opening round. Losers stages are 8, 8, 4, 4, 2, 2, 1, and 1 series, alternating survivor-only rounds and drop-in rounds, then the grand final. There are no crossovers.
- Pairings after the opening round are reseeded. At every stage the clubs entering that stage are reseeded by original tournament seed and paired highest against lowest, then second-highest against second-lowest. The highest surviving seed plays the lowest surviving seed. The losers bracket reseeds the same way. A drop-in losers stage pools the previous losers stage's winners with the corresponding winners stage's losers and reseeds that combined pool.
- The grand final is the winners-bracket champion (no series loss) against the losers-bracket champion (one series loss), best of 7. If the one-loss club wins it, one reset series decides the championship. The tournament is 62 series, or 63 if the reset is played.
- Every slot after the opening round exists from the start as an unfilled shell with its pool and its gate. A stage forms only when every series feeding it is complete. Both second-round stages form when all 16 opening series finish. Each later stage forms when its feeding stage finishes, and a losers drop-in stage also waits for the corresponding winners stage. Until a stage forms, its shell has no pairing and does not accept games.
- Home pattern, every series: 2-2-1-1-1, higher seed home first. Games 1 and 2 at the higher seed, games 3 and 4 at the lower seed, game 5 at the higher seed, game 6 at the lower seed, game 7 at the higher seed.

| Game | Home |
|---|---|
| 1, 2, 5, 7 | Higher seed |
| 3, 4, 6 | Lower seed |

## Open questions

Kept open for Joe, because play has not settled them:

- The Rest Chart's days-based rest accounting diverges from the house outs-based convention in some states. The governed games so far have not forced the choice; it is Joe's call when it bites.
- Whether any fixed relief-innings cap applies beyond the Rest Chart, the hook policy, and manager traits. Governed play has applied no separate cap; none is written here until Joe rules.
