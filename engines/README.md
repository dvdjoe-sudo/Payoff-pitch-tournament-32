# Card conversion engines

The solvers that built every converted Payoff Pitch card in this
tournament. Each engine starts from a player's prime window, his five
best seasons with the club, and solves backward for the printed card
whose expected results reproduce that stat line: the outcome tables,
the fielding label, the range, the error number, and the arm.

Both engines are frozen. A new engine version creates a new card
version; it never overwrites the cards an earlier version built.

## hitter-v0.5

HITTER ENGINE v0.5, frozen 2026-10-08. Built the 184 hitter cards of
Historical Cards Release 1.0 (99 PASS, 85 architecture-limited).

- `hitter_solver.py`: the solver. Section comps from the digitized 1986
  cards, then a coordinate-descent tuner aligns expected AVG, OBP, SLG,
  BB%, SO%, HR%, and HBP% with the target line.
- `batch_runner.py`: runs a CSV of hitters and produces the review lists.
- `qa.py`: structural QA warnings for generated cards.
- `review_packet.py`: compact human-readable summary for flagged cards.

## pitcher-v0.2.3

PITCHER ENGINE v0.2.3, frozen for production 2026-10-08. Built the 157
pitcher cards of Historical Cards Release 1.0 (82 PASS, 75
architecture-limited). Three-primary optimization on SO/BF, BB/BF, and
HR/BF; hits are diagnostic only. Era normalization over actual career
spans, calibrated to the printed 1986 cards.

- `pitcher_solver.py`: the base solver, legal 2d6 tables from target rates.
- `historical_solver.py`: historical pitchers, with special-category escalation.
- `production_run.py`: the v0.2.3 production pipeline.
- `calibration.py`: the 1986 calibration and the supplemental SO modifier.
- `translation.py`: the historical translation layer (1986 baselines).
- `event_vectors.py`: exact event vectors against the frozen 1986 population.
- `career_spans.py`: career spans used for era normalization.
- `aliases.py`: player name aliases.
- `reconstruct.py`: reconstruction check, actual lines against generated cards.
- `stress_test.py`: the 24-pitcher stress test.
- `test_v011.py`: the solver's unit tests.

## pitcher-v2

- `engine_v2.py`: the card_version 2 resolution path. The v2 refit of
  all 157 library pitchers was completed 2026-10-24 and adopted the
  same day; the tournament's converted sets play on v2 pitcher cards.
  The one change from v1 semantics is the TOUGH-band widening rule
  described at the top of the file.

## New generation (adopted 2026-10-28)

Adopted 2026-10-28 as the card system for the whole tournament going
forward: every club's cards are being rebuilt under it. The frozen
engines above are the previous generation; series already played
stand as played on the cards they were built with. The new engines
learned the printed game's own grammar from the real 1986 cards
instead of solving backward from a target line.

- `hitting_engine_v1_2.py`: hitting engine, research build v1.2.
  Style-first generation: the hitter is classified from his line
  (contact, balanced, power, free-swinger), the style supplies the
  band shapes, and his exact numbers are fit inside that shape.
  Reads `dataset.json` and `out_dataset.json` from beside itself.
  Carries the Elite Power Edit (adopted 2026-10-28 after a measured
  two-variant probe; the tail-only variant is the recorded loser):
  past the wheel_hr table's top rate, the WHEELHOUSE HR band
  continues on the table's own last-segment slope instead of
  clamping at 73 points, and when the section overflows, the
  overflow is displaced from 1B (floor 2), 2B (floor 1), then 3B
  (floor 0) before HR. Cards at or below the gate are unchanged.
- `dataset.json`: the 596 printed 1986 hitter cards the hitting
  engine fits from.
- `out_dataset.json`: the printed OUT charts of the 1986 set.
- `pitcher_grammar_generator.py`: the pitcher table generator, a
  faithful standalone extraction of the workshop build scripts of
  2026-10-28 (the smoothed decile-ladder fit and the greedy face
  assignment). Fits itself from `pitchers_1986.json` beside it and
  carries its validation anchor in its header.
- `pitchers_1986.json`: the parse of all 484 printed 1986 pitcher
  cards (dice tables, ratings, stat lines).

See the Engines page on the tournament site for the plain-language
version of how a conversion runs.
