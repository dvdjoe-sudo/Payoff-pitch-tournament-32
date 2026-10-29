# Playable Mode — Phase 1 Spec: Chicago Cubs vs Montreal Expos

Status: SPEC ONLY. No app code, no card changes. Written 2026-10-28 for Joe's ask;
revised the same day against the cold (Goldfish) review — NOT READY verdict,
3 blockers and 11 should-fixes, all resolved in this revision (the B2 ruling
changed Decision D1's recommendation):
"make it so I can play the game myself, add a dice roller and the FAC cards and
the teams," starting with Cubs and Expos.
REALIGNED the same day (Section 12): the draft and its review revisions
targeted FAC-chart mode; verification against the recorded games showed
governed play runs the FAC deck as a dice surface, and Joe ruled
2026-10-28 that Phase 1 mirrors governed play. The affected sections
were rewritten to that mode; Decision D1's three-source recommendation
is restored.

The playable mode turns the tournament site from a record book into a table:
Joe picks up one club, the app deals the FAC deck (the game's printed
Fast Action Cards: the 256-card deck whose printed faces serve as the
dice — the deck is the dice surface of governed play; defense, steals,
bunts, and advancement resolve on the engine's own charts, Section 5.2),
resolves
every plate appearance off the governing cards, tracks the game to a finished
box score, and hands him the record. This spec covers ONE fixture, the staged
R1-06 matchup (R1-06: Round 1, fixture 06 of the 32-team all-time
tournament), Chicago Cubs vs Montreal Expos. Everything else is Phase 2 or
out of scope (Section 13).

Two actors recur throughout. **Joe**: the user at the screen, the human
manager, and the sole rules authority; every ruling this spec cites is his.
**Cooper**: the agent who drives the Python reference stack at the table
game (Section 1, item 3).

---

## 1. Standing law this build must not break

1. **Exhibition by default.** A game played in the app is an exhibition game.
   It is not a tournament result, it never becomes one inside the app, and it
   enters the official record only if Joe adopts it by a separate ruling
   outside the app, the same as every exhibition before it.
2. **The app never writes the record.** The site is a static GitHub Pages
   build. It cannot and must not modify `tournament_results.json`, any file
   under `games/`, or any locked game. The results validator
   (`scripts/validate_results.py`) locks completed games behind the SHA-256
   fingerprint `5cf9eb31…` over `LOCKED_GAME_IDS`; the playable mode has no
   code path that touches those files, in the browser or in the build.
3. **The official R1-06 Game 1 is not this mode's game.** The official game
   is in progress at the co-managed table (the table game: the official
   game played flip by flip in the companion chat, Cooper driving the
   Python reference stack) (seed 20261401, paused before the
   bottom of the 7th, Montreal 7, Chicago 0, state file
   `state_series_chc_mon_g1.json` in the Cubs set home — a set home being
   a club's directory under ~/workspace/ holding its governing cards,
   engines, and addendum). The playable mode
   starts every game fresh at 0-0 under its own seed. It does not import,
   display, continue, or overwrite the table game's state.
4. **One card system.** All play uses the governing new-generation cards
   exactly as they stand (research hitting engine v1.2 with the OUT
   coordination rule and the Elite Power Edit; smoothed pitcher grammar).
   The retired Hitter v0.5 / Pitcher v0.2.3 engines and the v2 solver build
   path are provenance only and are never a play source.
5. **Universal DH.** Both clubs bat a DH in every game. There is no
   NL-style mode and no toggle.
6. **Governance hierarchy in play:** book mechanics (fatigue, Rest Chart)
   first, then the one house hard rule (no starting pitcher in relief except
   for a club facing elimination; a relieving starter's next start pushes
   back one day), then manager traits, then hook policy and the closer
   branch as default policy.
7. **Sacrifice scoring.** A sacrifice play counts as a PA but not an AB
   (sac bunts, the bunt fielder's choice, sacrifice flies), per Joe's
   2026-10-25 ruling as extended 2026-10-27 and as the set engines now book
   it. The port books it the engine's way, nowhere else.
8. **Save standard.** Entry state governs: tying run on base, at bat, or on
   deck at entry, OR three-plus innings of relief to finish, OR entering
   with a lead of three or fewer and pitching at least one full inning.

## 2. Scope of Phase 1

Ships:

- A new route, `#/play`, in the existing single-page app, implemented as a
  new file `js/play.js` (the existing `js/bracket.js`, 4,411 lines, gains
  only a nav link and a route dispatch entry).
- The R1-06 fixture only: CHC and MON, their governing 26-man rosters, the
  staged R1-06 lineups and bullpen roles (Section 4), two venues (Wrigley
  Field for Chicago home games, Stade Olympique for Montreal home games).
- Full nine-inning-plus-extras game play: the FAC deck as dice surface
  (with the in-app dice roller and manual entry as peer sources for the
  same steps), section
  resolution, defense, runner advancement, rare plays, steals, bunts,
  substitutions, pitching changes, in-game fatigue, hook policy, the closer
  branch, and the vacancy rule.
- One human manager and one profile-driven club, or a human on both sides
  (Decision D2).
- In-progress save and resume in the browser (Decision D7), undo of the
  last play (Decision D5), and a final exportable game record (Section 10).
- A generated data file, `data/playable_r106.json`, produced by a build
  script from the governing sources (Section 3), committed like every other
  generated file so the Pages deploy gate stays green.

## 3. Sources of truth and the data build

The browser must never read set-home files at runtime. Everything it needs
is baked into `data/playable_r106.json` by a new build script,
`scripts/build_playable_data.py`, run from the pinned pipeline venv
(`~/workspace/tools/pp-t32-venv`) and added to the deploy checklist
(Section 11.4). The rule for the build: **serialize what the reference
engines themselves load.** The script imports the reference stack's own
loaders and dumps the loaded card objects, so the web data is the engine's
data by construction, not a hand-copied re-derivation.

The loading mechanism is the G1 setup's own, in one process (this is
what the loaders require, and it is proven by the official game): the
script assembles the Cubs stack the way
`series_chc_mon_setup_g1.py` does, through `chance_setup`; loads
Montreal's cards with the same guest-card loader the setup uses
(`_guest_cards` over the Giants-Expos set home); takes Montreal's
lineup constants from the guest home's engine-constants module (the
one module of the guest engine the setup imports, for its constants
only); merges the guest addendum rows into the home addendum cache
under the home key BEFORE any dump, exactly as the setup's merge does
(the summary's standing warning: merge after the cache exists or it
silently no-ops); and serializes the resulting loaded objects — the
`HITTERS` and `PITCHERS` maps and the merged pitcher objects with
their addendum fields — never the files they were loaded from.

| Content | Source (governing) | Notes |
|---|---|---|
| Hitter card bodies (sections, OUT chart, positions, fielding, run, steal, sac bunt, DP) | The loaded hitter objects of the reference stack: the `HITTERS` maps the G1 setup assembles for both clubs, serialized by the build exactly as the pitcher objects are | 15 hitters per club (nine starters, six bench). `data/cards.json` is not the source; it is the cross-check (see the build assertions): the serialized bodies must byte-compare against the `CHC\|*` / `MON\|*` records for every shared field — two surfaces agreeing, not a file compared with itself. Archived off-roster records in cards.json are excluded by roster membership (cards.json holds one such MON record). **Build note (2026-10-28, from the first build run):** the byte-compare holds for the batting surface (sections, out_table, run, steal, sac_bunt, dp, bats, throws — all 30 fixture hitters agree exactly), but NOT for `positions`: the app pipeline (`build_cards.py`) deliberately transforms the fielding lines it publishes (`rulebook_error_scale` flips the set-file error digit to the rulebook scale, `rulebook_of_arm` derives outfield arm from the fielding label, `derive_hitter_fielding.py` replaces lines from 1986 stats), so cards.json's positions are a display transformation of the governing card by design, and 22 of the 30 fixture hitters differ there. The build therefore byte-compares the batting surface, checks `positions` for agreement of the position sequence itself, and ships the fielding lines from the loaded governing objects — the lines the reference engines actually field with. |
| Pitcher resolution data (2d6 table, SO modifier, special list, stamina, addendum, fielding, throws, and the bump parameter exactly as the engine derives it) | The loaded pitcher objects of the reference stack: `pitcher_output_v2/pitchers_v2.json` in each club's set home plus `pitcher_addendum.json` per home | `cards.json` alone is NOT sufficient: it carries the display 2d6 table and addendum, but the resolution-time pitcher fields live in the set-home files (the same gap the cards PDF documented). The build takes them from the engines' loader. |
| FAC deck (256 cards) | `~/workspace/payoff-pitch-alltime-teams/fac/fac_deck.json` (234,673 bytes, transcribed and verified) | The play surface is each card's printed faces: d2d6 (the printed 2d6 total), pct (the percentile, 0-99), d1d6 (the single die), and the wp wild-pitch marker flag — the faces `sim/fac.py` serves. The file also carries the cards' printed chart columns (single/double text, defense string, hit/err/out columns, sac and steal rows, the play-at-home line); those are `sim/fac_chart.py`'s surface, which governed play does not install and the port does not read (Sections 5.2, 13). The data build ships the faces the dice surface consumes; carrying the chart columns in the shipped file is neither required nor forbidden. The deck prints no 1d10 face: a 1d10 read is the drawn card's printed percentile's rightmost digit (Section 5.2) |
| Rare plays (24) | `~/workspace/payoff-pitch-app/data/special_plays.json` (the tracker app's data, which the v2 engines load as RARE) | Includes the trigger play and the bases-empty / runners-on families by section |
| Parks | `~/workspace/payoff-pitch-app/data/ballparks.json`, entries "Wrigley Field" and "Stade Olympique" | Wrigley is the exact 1986 park card (WHEELHOUSE 1-75 LHB / 1-68 RHB). Stade Olympique is the adopted exact 1986 entry (Joe, 2026-10-27) |
| Fixture configuration (staged lineups, pens with roles, default starters and closers) | `~/workspace/payoff-pitch-cubs/series_chc_mon_setup_g1.py` constants, as printed in `PP_R1_06_G1.md` | Section 4. Overrides the generic `data/rosters.json` listing, which still shows the pre-staging order (Rizzo batting 2nd) and must NOT be used for this fixture |
| Bunt-grade overlay data (the batter's official sac-bunt grade, substituted at the bunt seam while a bunt resolves) | `~/workspace/payoff-pitch-managers/sandbox/bunt_grades.json` | Joe's 2026-10-25 ruling, applied by the G1 setup's overlay; only batters the source carries a grade for are substituted |
| Manager parameters | Chance: `~/workspace/payoff-pitch-managers/sandbox/traits_chance.py` as installed by `sandbox/chance_setup.py`. Williams: the traits2 v2 package (Fireman deployment, strict-platoon pinch hitting, late-inning defensive subs), as re-pointed to the guest slot by the G1 setup | Section 7 |

Build assertions (the script fails, it does not warn): 26 rostered players
per club — 15 hitters and 11 pitchers — by roster membership (no player in
this fixture is both a hitter and a pitcher on the roster; a two-way
player would be counted once for each role his roster spot fills); 256 FAC cards with ids 1-256 each
exactly once; 24 rare plays; both park entries found by name; every staged
lineup name resolves to a rostered card; the serialized hitter bodies
byte-compare against their `data/cards.json` records for every field
the two surfaces share (the batting surface; `positions` is checked
for position-sequence agreement only, per the build note in the
table above) — a cross-check assertion between the engines'
loaded objects and the app's committed records, failing the build if
either surface has drifted, not a comparison of the build's input
against itself; pitcher 2d6 tables
have all 11 totals (2-12); 11 pitcher objects per club carry their merged
addendum fields — Chicago 11, Montreal 11, every rostered pitcher of both
clubs, the guest club explicitly included (a short or zero guest count is
exactly the silent merge failure the loading mechanism above warns of, and
it fails the build); the staged lineups of Section 4 pass the setup
screen's lineup-legality rules (Section 8, S1 (a)-(e)) as shipped. Output
is deterministic: same inputs, same bytes,
so the generated-files deploy gate can diff it.

## 4. The fixture, as staged

Venue and home club are selectable at setup (Decision D8); the default is
the staged Game 1 shape: Chicago home at Wrigley Field, batting last.

**Chicago (Frank Chance).** Lineup: Ryne Sandberg 2B, Mark Grace 1B,
Ron Santo 3B, Sammy Sosa RF, Billy Williams LF, Ernie Banks SS, Hack Wilson
DH, Gabby Hartnett C, Pete Crow-Armstrong CF. Bench: John Kling, Billy
Herman, Andre Dawson, Joe Tinker, Stan Hack, Anthony Rizzo. Rotation chair
for the default start: Fergie Jenkins; the other four chairs, in rotation
order: Mordecai Brown, Rick Reuschel, Pete Alexander, Carlos Zambrano.
Bullpen with roles: Hippo Vaughn
(long), Sean Marshall (mid), Pedro Strop (mid), Kerry Wood (setup), Lee
Smith (setup), Bruce Sutter (closer).

**Montreal (Dick Williams).** Lineup: Tim Raines LF, Jose Vidro 2B, Larry
Walker RF, Vladimir Guerrero DH, Gary Carter C, Andre Dawson CF, Ron Fairly
1B, Tim Wallach 3B, Orlando Cabrera SS. Bench: Brian Schneider, Mark
Lansing, Marquis Grissom, Chris Speier, Rusty Staub, Moises Alou. Default
start: Steve Rogers; the other four chairs, in rotation order: Pedro
Martinez, Dennis Martinez, Bryn Smith, Javier Vazquez. Bullpen: Andy
McGaffigan (long), Woodie Fryman (long),
Mel Rojas (mid), Tim Burke (setup), Jeff Reardon (setup), John Wetteland
(closer).

Both clubs carry six bench and six relievers (the six-and-six rule).
Starting pitchers beyond the default are selectable from each club's five
rotation chairs at setup; the pick is part of the game record.

## 5. Architecture

### 5.1 The reference stack being ported

The port mirrors, function by function, the exact stack the official R1-06
Game 1 setup assembles (`series_chc_mon_setup_g1.py`, whose own assertion
block is the stack's manifest):

- The Cubs' v2 play engine (`payoff-pitch-cubs/pitcher_output_v2/engine_v2.py`)
  for the home slot and the re-pointed Expos copy for the guest slot. In the
  web port there is one engine implementation parameterized by club data;
  the Python two-copy arrangement is an artifact of the set homes, not a
  behavior.
- The FAC deck as dice surface (`sim/fac.py`'s `install`, exactly as
  `chance_setup.py` and the G1 setup install it): `fac.install` replaces
  the engine's four dice functions (`roll2d6`, `rollpct`, `roll1d6`,
  `roll1d10`) with deck draws, so every random input in a governed game
  comes off FAC draws, in the engine's draw order and for the engine's
  purposes (2d6, percentile, and 1d6 — the purposes both recorded
  games' histories carry, alongside their RESHUFFLE markers; the
  1d10 function is part of the installed surface but appears in
  neither recorded history). Defense, steals, bunts, and
  advancement then resolve on the ENGINE's own charts, fed by those
  draws. `sim/fac_chart.py` is NOT part of this stack: it is installed
  nowhere in the governed setups, and the port does not implement it
  (Sections 5.2, 12, 13). The printed reshuffle protocol is part of the
  mode: the deck reshuffles after every
  three full innings (top of the 4th, 7th, 10th, ...) and on exhaustion
  mid-cycle, each reshuffle logged.
- The pitcher addendum layer (`sim/addendum.py` + `pitcher_addendum.json`):
  hold, pickoff, wild pitch, DP, injury ratings as the engines apply them.
  Its live consequences — the wild-pitch trigger and the pickoff chart —
  are Section 6.1 items 16 and 17.
- The fatigue fix layer (wraps the engine; edits no engine file): the
  within-game fatigue bookkeeping of `update_fatigue` /
  `fatigued_section` plus the fix layer's corrections, battery-proven
  23/23 in Python.
- The traits layers as installed for this fixture: Chance over Chicago
  (`traits_chance.py`, battery 42/42), Williams's v2 package over Montreal,
  installed beneath Chance in the G1 stack's order. No other manager layer
  exists in this fixture (the G1 setup pins McGraw off; there is no third
  layer to port).
- The bunt-grade overlay the G1 stack installs at the bunt seam (Joe's
  ruling, 2026-10-25): while a bunt resolves, the batter's sac-bunt letter
  is temporarily his official grade from `sandbox/bunt_grades.json` where
  that source carries one, exactly as the G1 setup applies it. And the
  defense-numbers wrapper the stack installs: logging-only in Python; in
  the port it is simply the play feed's defense display (Section 8, S2),
  which Joe's PA-by-PA audit reporting preference (2026-10-27) requires
  anyway.

### 5.2 Roll sources (dice) and the step

The Python stack already separates the roll source from resolution:
`sim/engine.py` rolls dice directly; `sim/fac.py` supplies the same
`fac_roll2d6 / fac_rollpct / fac_roll1d6 / fac_roll1d10` surface off deck
draws. The port keeps that seam as a `RollSource` interface.

**The step.** The engine never rolls "for a plate appearance." It asks
for one random input at a time, and each single request is a **step**.
A step is identified by its purpose, in the vocabulary the reference
stack itself records in the FAC history: `2d6`, `%`, and `1d6` — the
purposes both recorded games' histories carry, alongside RESHUFFLE
markers (the `1d10` read exists on the installed surface and in the
sources of Section 5.2, but no recorded history carries one). A plate
appearance is a sequence of steps — as few as two (2d6, %) and rarely
more than a dozen — and the sequence is data-dependent: a DEFENSE
read re-rolls its own 2d6 and % inside the resolution (Section
6.1.5), a bunt MISS opens another bunt-attempt sequence, a coach's
choice consumes its own check steps, and so
on. The port's engine exposes exactly this: it runs until it needs a
value, names the pending step (kind and purpose), and waits.

**The two advance controls.**

- **Draw / Roll** serves the current pending step only — one press, one step —
  and displays what it served. Its label names the pending step and
  follows the active source ("Draw — 2d6, section selection" at the
  deck; "Roll — %, defense check" at the dice roller),
  so Joe knows what the next value is for before it is served.
- **Play plate appearance** serves steps in order, automatically,
  until the plate appearance resolves — with three stops. It stops
  (a) at any Section 7.1 decision for the human club, including the
  in-PA ones (a send/hold choice on an extra base, a tag play at
  home, forced coverage after a mid-PA departure); (b) at a rare-play
  stop: a triggered rare play halts
  the sequence and shows the pending play, and the next press (the
  button relabels "Resolve rare play") serves the steps that resolve
  it from the shipped rare-play data — a pause for the audit feed,
  not a decision; and (c) at the end of the half-inning or the game.
  For the profile-driven club, decision points never stop the
  sequence: the profile or the default policy answers them in the
  feed (Section 7.2).

**Undo granularity.** Snapshots sit at plate-appearance boundaries
regardless of steps (Section 5.4). During an unresolved PA the Undo
button reads "Undo — discards this PA": pressing it restores the
boundary snapshot taken before the PA's first step, which discards
the partial PA whole — its consumed flips return with the
full DeckSource state (the complete deck order, the consumed set,
the stream position, and any outstanding peek) and the
roll-history length the snapshot carries, and the feed marks the
PA block "undone (partial)". There
is no mid-PA undo target, by design: the reference stack has no
mid-PA state worth returning to.

**The sources (Phase 1).** Three, chosen at setup (Decision D1) and
recorded in the game record; any of them may serve any step, because
every step is a dice value — a 2d6 pair, a percentile, a single die,
a 1d10 — and each source serves values, not chart text. Switching
between them mid-game, per flip, is allowed and recorded per flip
(Decision D4), with the one refusal below.

**The outstanding-peek exception.** A source switch is refused while a
manual 2d6 peek is outstanding. The peeked card must be flipped next,
served by manual card entry, or the plate appearance undone, before
another source may serve a step; a switch attempt is refused, naming
the peeked
card. The rationale is the peek rule's own: the flip history must be
able to reproduce every 2d6 pair from the cards actually drawn and
entered, and a peek that lapsed silently across a switch would break
that reproduction.

1. **FAC deck (default).** A shuffled 256-card deck per game, seeded.
   A Draw press flips the next card: its id, page, and all faces
   display, and the step consumes the card's printed face for its
   kind, exactly as `sim/fac.py` serves it: a `%` step takes the
   card's pct (0-99); a `1d6` step takes its d1d6; a `2d6` step takes
   the pair convention below; and a `1d10` step takes a derived
   value, not a printed face: the drawn card's printed percentile's
   rightmost digit (the
   percentile mod 10), the printed protocol's own derivation (game
   PDF p13), exactly as `fac_roll1d10` implements it.
   The 2d6 pair convention is the reference stack's own: the pair is
   the drawn card's printed 1d6 and the NEXT card's printed 1d6
   (peeked, not consumed; the next card is still served normally for
   the following step), and the auto-steal jump read uses the last
   card drawn — the port implements both exactly, peek included.
   Reshuffle behavior mirrors `fac_reshuffle` / `maybe_reshuffle`:
   after every three full innings and on exhaustion mid-cycle, the
   deck reshuffles and the event is logged in the feed and the
   ledger (the game state's running governance log: the flag and
   event list the comparator checks in Section 11.1), never silently.
2. **In-app dice roller.** The app rolls the pending step's dice
   itself, with the engine's own dice semantics (the `sim/engine.py`
   surface `fac.install` replaces): a `2d6` step rolls two dice and
   keeps the pair — both faces are recorded, because the pair's low
   die feeds hit advancement (Section 6.1.6) exactly as a deck
   pair's does; a `%` step rolls the percentile dice, 0-99, where
   00 is a live value (it is the rare-play trigger, Section 6.1.8);
   a `1d6` step rolls one die, 1-6; a `1d10` step rolls one value,
   0-9. A dice step touches no deck: the virtual deck's order,
   position, and consumed set are unchanged, no peek arises, and the
   flip history records the roll tagged `dice`.
3. **Manual entry.** Joe supplies the pending step's value by hand,
   in either of two forms; the entry control is generated by the
   pending step and validates against it. Entry of either form is
   refused, with the reason shown, when no step is pending (a
   decision is waiting: resolve it first).
   - **A physical FAC card id.** Joe flips a physical FAC and types
     its card id (an integer 1-256); the port reads that card's
     printed face for the step's kind, under the same mapping as
     the deck source. Manual card entry runs
     against the virtual deck: the entered card is removed from the
     virtual deck's remaining order wherever it sits, so the deck can
     never later deal a card Joe has already flipped physically; the
     entry counts as a draw (the same draws counter, the same flip
     history, tagged `manual-card`); entering a card already consumed in
     the current deck cycle is refused, naming the step that consumed
     it ("FAC 143 already flipped this cycle, PA 38, defense check") — a physical deck
     cannot repeat either. A reshuffle (three-inning or exhaustion)
     restores all 256 cards, manually entered ones included, and
     resets the cycle's consumed set; a card may then legally be
     drawn or entered again. In manual card play the reshuffle is a
     physical act too, and the feed says so in words at both marks:
     at the three-inning mark, "Reshuffle — top of the <N>th: shuffle
     your physical deck now; the new cycle starts with your next
     flip"; on exhaustion, "Deck exhausted: shuffle your physical
     deck now; the new cycle starts with your next flip." The 2d6
     peek in manual card play is physical, not virtual. The pair
     convention needs the NEXT card's printed 1d6 (peeked, not
     consumed), and in a manual card game the next card is the top card of
     Joe's physical deck — the next card he will flip — not the next
     card of the seeded virtual order: a peek read off the virtual
     order would let the app's shuffle deal the second die of every
     2d6 pair inside a game whose point is that Joe's deck deals it,
     and the game's flip history could never reproduce a pair from
     the cards Joe entered. So at a manual card 2d6 step Joe enters two
     ids: the card he flipped, and the id of the top card of his
     remaining deck, looked at and not flipped. The peeked card's
     printed 1d6 serves as the pair's second die; the peek is
     recorded in the flip history as a peek (not a draw, not
     consumed); and the next step's entry must be that card — any
     other id is refused, naming the peeked card ("the 2d6 pair
     peeked FAC 87; flip it next, or undo the PA").
   - **Raw values from physical dice.** Joe rolls real dice and
     types the result: the entry validates against the current
     step's type and range ONLY — two faces 1-6 for a `2d6` step
     (entered as the pair, so the low die is preserved), 0-99 for
     a `%` step, 1-6 for `1d6`, 0-9 for `1d10` — and nothing else:
     no card is read, so no card needs to exist behind the value.
     A raw-value step touches no deck: the virtual deck's order,
     position, and consumed set are unchanged, the draws counter
     does not move, and no peek arises (the pair is entered whole).
     The flip history records the values tagged `manual-value`.

**The mode ruling (corrected; Joe, 2026-10-28).** Phase 1 mirrors
governed play: the FAC deck as a **dice surface**. This paragraph
replaces the earlier B2 ruling, which was written on a false
premise. The draft originally targeted FAC-chart mode — the mode of
`sim/fac_chart.py`, in which defense, hit advancement, steals, and
bunts read the drawn cards' printed chart sections — and, when the
first cold review pressed the point, narrowed the roll sources to
the two card sources on the ground that the chart text is keyed by
the draw and cannot be derived from dice values. Verification
against the recorded games then showed that no governed game has
ever run that mode: both recorded states (the exhibition, seed
20261701, and the official Game 1 segment, seed 20261401) carry
histories whose purposes are only `2d6`, `%`, `1d6`, and RESHUFFLE
markers, with `fc_count` empty, and every governed setup installs
`fac.install` — the deck as a dice surface — and never
`fac_chart.install`. Defense, steals, bunts, and advancement in
governed play resolve on the engine's own charts, fed by FAC draws.
Joe ruled 2026-10-28: mirror governed play. The consequences run
through this spec: the fidelity bar's defense, advancement, steal,
and bunt items are the engine's dice-path functions (Section 6.1);
`fac_chart` is out of scope entirely (Section 13); and because
every step is a dice value, all three sources above serve every
step as peers — the narrowing is reversed, and Decision D1's
three-source recommendation is restored.

Whatever the source, every consumed value lands in the game's flip
history in order — tagged with its source per flip (`deck`, `dice`,
`manual-card`, or `manual-value`; a manual card entry also records
the card id and the faces read) — in the same
audit form as the table game's record ("Flips: #12 FAC 2 2d6 [card:
2d6 7, % 57, 1d6 3]"), so a played game can be re-walked flip by
flip.

### 5.3 Game state

The Python engine's state is a JSON-serializable dict (inning, half, outs,
bases, score, linescore, batting and pitching lines, pitcher spans, the
full DeckSource state (the complete deck order, the consumed set, the
stream position, and any outstanding peek), fatigue, ledger, flags, and
the declarations field —
the per-game declared-player mechanic (Section 9, D3), carried in the
state shape because the reference state carries it, and inert in
Phase 1). The port's
state object mirrors that shape field for field where the names exist, so
that (a) the export in Section 10 is a translation, not a reinterpretation,
and (b) a saved web game can be diffed against a Python state file during
verification. State lives in memory, autosaves to `localStorage` after
every resolved plate appearance and every managerial action (key
`pp-play-r106-<gameId>`), and is never sent anywhere.

**What the autosave persists.** The autosave stores three things: the
current state object above; the complete flip history — every value
served, in order, each entry carrying its step purpose, its per-flip
source tag, and the values it served (the card id and the faces read
for a card source; the faces rolled or entered for a dice or
raw-value step); and the
complete feed — every plate-appearance block and managerial entry, each
tagged to the timeline (live or undone), undone markers included.
Nothing in Section 10's export is reconstructed after the fact: the
detail JSON's `rolls` array is this persisted flip history, so the
full-history export holds identically after a resume.

**Saved-game lifecycle.** One saved game at a time. The gameId is
generated at setup as `r106-<seed>-<suffix>`, the suffix four
characters drawn from the setup randomness. Seed reuse is legal and
supported (Joe may reproduce a shuffle deliberately, Section 8 S1);
if a generated gameId collides with the existing save's key, the
suffix regenerates until unique, so a reused seed never silently
overwrites a different game. Starting a new game while a save exists
never discards it silently: the setup screen carries the resume
banner (Section 8, S6), and Start stays behind an explicit
Discard-and-start confirmation. A tab closed mid-PA, in either
mode, is the same shape in miniature: the autosave holds only the
last PA boundary, so the game resumes there with the partial PA
gone. In deck mode the partial PA's draws were never autosaved as
consumed, so the virtual deck resumes from the boundary state
exactly. In manual card play its flipped cards — never recorded as
consumed — are simply back in Joe's deck, to be flipped again when
they come up. A partial PA served by the dice roller or by raw
values leaves nothing behind at all: no deck state moved.

**Storage failure.** If `localStorage` is unavailable (private
browsing) or a write fails (over quota), the game continues in
memory; the saved indicator shows "Not saved — storage
unavailable," the failure is named once in the feed, and play is
never blocked by it. The game-over screen repeats the warning if
the final autosave failed, so Joe knows the export in his hand is
the only copy.

### 5.4 Undo

Before every plate-appearance resolution and every managerial action, the
port pushes a snapshot of the state onto an in-memory stack. A snapshot
is the complete game state — score, bases, lines, pitcher spans,
fatigue, ledger, the full DeckSource state (the complete deck
order, the consumed set, the stream position, and any outstanding
peek), roll-history length — EXCLUDING the narrative feed text,
which the UI keeps as a
separate append-only list whose plate-appearance blocks are tagged to
the timeline: restoring a snapshot marks every feed block after the
restore point "undone" rather than deleting it, and an export includes
only blocks on the live timeline. Measured against the reference state
files (a full game's state runs ≈ 45 KB with the log array excluded),
a stack of 130 snapshots stays under ≈ 6 MB; the stack is capped at
200 snapshots — beyond any legal game's PA-plus-action count — and is
never persisted: the autosave (Section 5.3) stores the current
state, the flip history, and the feed, never the snapshot stack.

Undo pops one snapshot and restores it exactly. Because a snapshot
carries the complete deck order and the consumed set, undoing
across a reshuffle boundary restores the exact pre-reshuffle deck —
the order and consumed set as they stood before the reshuffle, not
a fresh shuffle — and a peek outstanding when the snapshot was
taken is outstanding again on restore. Its granularity is
the PA boundary (Section 5.2): there are no mid-PA snapshots, and a
partial PA is discarded whole. Undoing past a pitching change or
substitution restores the removed player and erases the entry from
the record being built; the feed shows an "undone" marker rather
than deleting history silently, and any export reflects the restored
timeline only. In manual card play the undone marker carries the physical
instruction as a feed line — "Undo: return FAC <ids> to your deck;
they are back in this cycle and may be flipped again" — listing
every card the restored span had consumed, because the restore
un-flips them on the virtual deck and Joe's deck must match. Undo
is unlimited within the game (Decision D5): a
game is roughly 80-100 plate appearances, snapshots are small, and a
misclick on the 90th PA should not cost the evening.

Two boundaries, stated plainly:

- **Undo does not survive a reload.** The stack is in-memory only.
  A resumed game starts with an empty stack: Joe can undo what he
  does after the resume, never back past it. The resume banner
  says so (Section 8, S6).
- **Undo at game over.** A finished game that has not been exported
  can still be stepped back into: the game-over screen offers
  "Step back into the game," which restores the last PA-boundary
  snapshot, clears the final state, and returns to the game screen.
  Exporting seals the game: once any export is taken, undo is
  disabled and the autosave is cleared.

### 5.5 Inside js/play.js

One file, seven named modules in IIFE sections, in dependency order:

1. **PlayData** — fetches `data/playable_r106.json`, re-checks the
   Section 3 build assertions client-side on load, and serves card,
   park, deck, and rare-play lookups.
2. **RollSource** — the Section 5.2 seam: `DeckSource` (the virtual
   deck state: the full DeckSource state (the complete deck order,
   the consumed set, the stream position, and any outstanding peek),
   and the reshuffle protocol),
   `DiceSource` (the in-app roller, serving the engine's dice ranges
   and leaving the deck state untouched), and `ManualSource`
   (card-id entry against the same deck state, or raw-value entry
   validated against the pending step, also leaving the deck state
   untouched).
   Every served value lands in the flip history with its purpose
   and source.
3. **Engine** — the pure resolution core, one function per
   Section 6.1 behavior, written against the state object only (no
   DOM), exposing the step interface: run until a value is needed,
   name the pending step, resume on serve. This is the module the
   replay driver loads headlessly (Section 11.1), behind a
   `module.exports` guard that ships inert in the browser.
4. **Profiles** — the Chance and Williams decision layers over the
   Engine's decision points, with hook policy and the closer branch
   beneath them (Section 7.2).
5. **GameState** — the state object, the snapshot stack, the
   autosave, and the saved-game lifecycle (Sections 5.3, 5.4).
6. **Feed** — the audit feed: renders state blocks, flips, the
   defense numbers, decisions, and undone markers from the
   GameState timeline.
7. **UI** — screens S0-S6 and their flows, the decision bar, and
   the export builders of Section 10.

**Card rendering.** The player pages render cards inside
`js/bracket.js`'s single closure; nothing there is importable
without restructuring that file beyond the nav-link and dispatch
edits Section 2 allows. So the matchup panel's card renderer is
play.js's own — a deliberate copy of the player-page layout, same
section order, same fields, same labels — and the drift guard is
mechanical, not hopeful: `scripts/check_cardview_parity.py`
extracts the section order, field order, and label strings from
both renderers and fails the ship checklist (Section 11.4) on any
divergence. The shipped DATA cannot drift at all: both renderers
read the same committed card records.

## 6. Resolution: the Phase 1 fidelity bar

Phase 1 is a port, not a redesign. Each behavior below names its reference.
**The Python source is normative wherever Section 6 paraphrases it;
Section 6 is an index of behaviors to mirror, not a complete
restatement.** Anything the reference does that is not listed here is either listed in
Section 6.2 as deferred or is a defect in this spec, to be caught by the
Goldfish review or the replay verification.

### 6.1 Must mirror exactly

1. **Section selection.** The pitcher's 2d6 table (`card_table_2d6`) maps
   the 2d6 total to the read section: WHEELHOUSE, PATIENT, TOUGH, IN-PLAY,
   BALLPARK, or DEFENSE. No other section source exists.
2. **Section reads.** The percentile reads the batter's bands for the
   section against the pitcher's throwing hand (`section_lookup`, priority
   order as coded). A percentile above the section's bands falls through to
   the batter's OUT chart (`out_lookup`), including the fall-through to the
   nearest OUT row for a face below the chart's start, exactly as the
   engines resolve it and as the 2026-10-28 OUT-chart audit established the
   official cards behave.
3. **The v2 bump.** `v2_band_pct`: a TOUGH percentile landing within the
   pitcher's bump points above the top of the batter's printed SO range
   counts as a strikeout. The bump is part of the pitcher's resolution
   data (Section 3) and is applied identically, including its monotonic
   behavior.
4. **BALLPARK channel.** A BALLPARK read resolves on the venue's park
   section for the batter's hand (`ballpark_section`), Wrigley or Stade
   Olympique per the home club.
5. **DEFENSE channel.** `resolve_defense`, the engine's dice-path
   defense — the only defense path in the governed stack.
   `fac_chart.install` is not part of the stack being ported, and no
   DEF-A / DEF-B / DEF-C chain exists in this mode. The sequence:
   the plate appearance's opening steps stand — the 2d6 whose total
   the pitcher's table reads as DEFENSE (the ERROR and RANGE table
   results route here too), and the % step, which the resolution
   receives as `init_pct`. `def_pos` reads `init_pct` and names the
   check kind (RANGE or ERROR) and the fielder; the pitcher's table
   result overrides the check kind (an ERROR result forces an ERROR
   check, a RANGE result a RANGE check, whose fielder at C is
   redirected to CF). Defense then re-rolls its own 2d6 and % steps.
   The re-rolled % is checked against the fielder's fielding line on
   the home park's charts: for a RANGE check, the fielder's range
   letter selects the park RANGE band, and the % falling in its HIT
   span makes the outcome HIT, otherwise OUT; for an ERROR check,
   the fielder's error number selects the park ERROR band, and the
   % falling in its ERR span makes the outcome ERR, otherwise OUT.
   The re-rolled 2d6 then indexes the engine's own outcome tables,
   grouped by the fielder (C / OF / INF for errors and outs;
   position groups for hits):
   - **HIT:** the DEF_HIT table gives the hit type and the bases
     every runner advances; a 2B+ read becomes a triple when the
     batter's RUN rating is 8 or better.
   - **ERR:** the DEF_ERR table gives: 0, a dropped foul, which
     restarts the at-bat with no at-bat booked (RESTART; the engine
     caps repeated dropped fouls at three per plate appearance and
     then ends the PA as a foul ball, logged); -1, a single plus an
     error (the hit, then every runner one more base, those runs
     unearned, the error charged to the fielder); or a one-, two-,
     or three-base error, the batter reaching, runs unearned.
   - **OUT:** the DEF_OUT table gives the out family entire: popout
     and lineout (the log's "converts it"); a lineout double play,
     gated on the fielder's range (A or B) doubling the lead runner
     off; GB+adv, the runners advancing behind the out; GB-fc —
     with a runner on first, the lead runner is forced out and the
     batter safe; with no force, the batter is out (as coded, the
     force exists only off first base); GB-DP A and GB-DP A,B — the
     runner out at second, the double play completed only when the
     range gate opens (A for both texts, B for the A,B text),
     otherwise the batter beats the throw; a short fly, whose
     runner on third tags into a coach's-choice play at home
     against the fielder's arm — safe books the run and converts
     the at-bat to a sacrifice fly (Section 1.7), out adds the
     second out; a short-fly DP, gated on the fielder's arm value
     (5 or under, as coded) doubling the lead runner off; and a
     deep fly, runners from second and third advancing automatically
     on RUN 6 or better and on the coach's-choice read otherwise,
     the run from third converting the at-bat to a sacrifice fly
     the same way.
   Joe's numbers rule attaches to the resolution's own values: the
   feed shows `init_pct` and the fielder and check kind `def_pos`
   dealt, the fielder's range letter and error number, the re-rolled
   2d6 and %, the park band each was read on (the band's span, and
   in or out), and the outcome kind (Joe's 2026-10-27 reporting
   rule, the same standard his PA-by-PA preference states: the
   percentile, the fielder, the band checked against, and whether
   the number fell in or out).
6. **Hits and advancement.** `resolve_hit`: hit location from the
   section % (`hit_location`); runner advancement on singles and
   doubles from the engine's own Advanced Runner Advancement Chart —
   the ADV_1B_FROM1, ADV_1B_FROM2, and ADV_2B_FROM1 tables, keyed by
   the LOW die of the plate appearance's 2d6 pair (which is why
   every source serves a pair, not a total) — including the two-out
   rules (a runner with RUN 6 or better takes the extra base
   automatically) and the PATIENT-section lead-runner option; the
   chart's choice entries become coach's choice decisions (coach's
   choice: the printed Coach's Choice chart, a runner's extra-base
   attempt resolved against the fielder's arm), gated first by the
   engine's attempt check (`decide_attempt`); the play at home
   (`play_at_home`); and runner
   advancement exactly as coded, including which decisions are the
   manager's (Section 7.1) and which are automatic.
7. **Ground and fly outs.** `ground_out` and `fly_out` complete: double
   plays against the coded DP ratings, fielder's choice bookkeeping,
   sacrifice flies booked PA-not-AB, and the **infield-in chart with the
   2026-10-28 fix applied** — the batter's at-bat is booked once, at
   entry; the 9-10 "ball sneaks past" branch adds no second at-bat. The
   port is written from the fixed engines; the pre-fix line exists in no
   governing copy and must not be reintroduced.
8. **Rare plays.** The 24-play set, its trigger, and the section families.
   The trigger, in words: a plate appearance whose opening percentile
   read is 00 does not resolve on its section — the play pends; the
   chart matching the base state (bases empty or runners on) and the
   pitcher's section family is then flipped at a fresh percentile,
   the flipped entry's pitcher-removal effect is applied where its
   text orders one, and the plate appearance completes on its own
   section at a further fresh percentile (the governed stack's
   auto-resolve convention). The section families and the
   **lingering wrapper family**: printed "next N batters"
   clauses carry `force_wheelhouse`, `force_tough_count`, and
   `force_inplay_count` across inning breaks (Joe, 2026-10-25). Disclosed
   seam, preserved: a sacrifice bunt resolves at the bunt seam and spends
   no clause count.
9. **Steals.** `attempt_steal` and the automatic steal check, on the
   engine's own steal charts: the STEAL_COL table keyed by the
   runner's steal rating letter combined with the catcher's arm, and
   STEAL_HOME keyed by the letter alone for a steal of home. The
   attempt's % read resolves in bands: 2 or under is DROP? (a 1d6
   against the covering fielder's error number — the cover named by
   the target base and the next batter's hand; over the number, the
   throw is dropped, an error charged, the runner safe; at or under,
   he is out); 3 through 12 is SB+E2? (the runner safe with the
   steal; a 1d6 against the catcher's error number — over it, the
   throw sails, an error charged and every runner one more base,
   unearned); the column's caught band puts him out; above it he is
   safe. The automatic check reads the jump off the just-resolved
   plate appearance's own 2d6 total against the runner's jump
   rating (with its jump modifiers and the once-a-game jump-1 rule,
   as coded), requires doubles (both dice equal) for a steal of
   third, holds the runner with two outs and a runner on third, and
   sends a jump total of 12 to the addendum's pickoff chart (item
   17). The manager-sent steal and its own 12 are item 17's named
   gap.
10. **Bunts.** `resolve_bunt` including the squeeze, the bunt fielder's
    choice, and the scoring rule of Section 1.7: each attempt draws
    its own 2d6 (whose total is also the squeeze check), a 1d6 naming
    the fielding fielder by the engine's BUNT_FIELDER map, and a %
    read on the engine's BUNT table at the batter's sac-bunt letter —
    the squeeze always on column D. A MISS re-draws the attempt; the
    second MISS books the strikeout. **Named seam:** the
    failed squeeze (runner out at home, batter safe) is scored by the
    engines today as an at-bat; Joe has not ruled on it. The port books it
    as the engine books it and flags the play in the feed as the unruled
    case. The port does not invent a ruling.
11. **Pitcher fatigue, within the game.** `update_fatigue` and
    `fatigued_section` plus the fatigue fix layer: the fatigued section
    shifts apply from the same outs thresholds, and the feed names a
    fatigue shift when it changes a read (the R1-05 audit flags stand as
    the cautionary example: shifts happen in the open, with the conversion
    shown).
12. **Pitching changes and the hook.** `change_pitcher`, `pick_reliever`,
    `maybe_hook`: the hook policy and the closer branch (ninth inning,
    lead of one to three, starter at 21 or more outs, the closer comes in)
    drive the profile-managed club outright and are shown as the
    recommendation on the human club (Section 7). The house hard rule
    gates the reliever list: a starting pitcher is not offered in relief
    unless his club faces elimination, and in a single exhibition game no
    club faces elimination, so starters are simply absent from the relief
    list; the rule text shows on the pitching-change screen so the absence
    is explained, not mysterious.
13. **The vacancy rule.** `substitute` and its fit logic (`_vac_fit_pick`
    and family): when a player leaves for any reason (pinch hit, pinch
    run, injury, ejection, defensive replacement), coverage is chosen as a
    manager would: (1) a man carded at the position; (2) else the best
    card fit, priced on his own fielding line, starter slides allowed when
    they leave the defense stronger overall, the entrant taking the
    departed player's batting slot and a sliding starter keeping his own;
    (3) bench order only as the last resort, a catcher covering an
    infield/outfield spot only when no fit-based option exists. A DH
    vacancy stays bench order. The R1-05 regression case is the acceptance
    test: Ozzie Smith's ejection enters Schoendienst at shortstop, not the
    next bench name (Section 11.2).
14. **Bookkeeping.** Batting and pitching lines in lineup order with
    substitution sequence, run attribution (earned/unearned per the
    engine), error charging by position, pitcher spans (entry state
    preserved for the save standard), batters faced tying to plate
    appearances on both sides — the audit equalities the recorded games
    are checked against. The governed engine's one disclosed divergence
    stands as the engine's: no RBI on a run scoring on a fielder's choice.
15. **Game end.** Regulation and extra innings until decided; the home
    club does not bat in the last half when ahead; walk-off handling as
    the engines book it. No ties: the record format rejects them, and so
    does the port.
16. **Wild pitch.** The book p10 rule as the stack wires it: the first
    percentile read of a plate appearance is checked against the
    current pitcher's WP rating — carried not on the converted card
    but in the addendum, merged into the pitcher object the build
    ships (Section 3) — and on a match with runners aboard, it is a
    wild pitch: all runners advance one base, a run from third is
    booked, and a fresh percentile read resolves the at-bat; a second
    in-range read in the same PA records a second wild pitch, and
    that second read doubles as the resolving percentile read for
    the same section the 2d6 total selected — exactly two percentile
    draws occur, and no third read follows. The trigger the engines
    apply is the rating check: the addendum layer wraps the roll
    surface and checks the plate appearance's first % read (in the
    port, whichever source serves that step); the FAC card's printed
    WP? flag is only the marker the
    printed game uses to spot the band where WP ratings live.
17. **Pickoff.** The book p18 Pick Off chart, as the addendum layer
    applies it, at exactly the sites it intercepts: when an
    auto-steal jump check (item 9) comes up 12 — the batter just
    reached, the read taken from the last card drawn — the chart
    resolves on the pitcher's addendum Hold band: a percentile band
    gives WILD? (checked on a 1d6 against the pitcher's E rating:
    on target but late, the runner back safely; or past the base,
    an error charged and the chart's advancement), CAUGHT (the
    runner is out), BALK (all runners advance one base), or SAFE
    (the runner gets back; no steal attempt follows). **Named gap,
    preserved:** at the manager-sent steal site, a 12 is NOT
    intercepted — the ledger records the gap and the runner holds,
    because that send is a managerial decision point above the
    addendum layer and a pickoff out there cannot be voided cleanly
    inside the PA loop. The port ledgers it identically and
    resolves no pickoff there.

### 6.2 Explicitly deferred to Phase 2

- The **declarations engine** (Decision D3).
- **Cross-game availability and the Rest Chart between games**; a series
  mode with rotation carryover. Phase 1 tracks availability within the
  game only (who has appeared, who has left, pitcher outs and spans).
- **Manager traits beyond this fixture's two encoded profiles** and the
  hook/closer defaults.
- Any **official-adoption workflow** (export exists; adoption is Joe's act
  outside the app).
- The other 30 clubs.

## 7. Who manages, and how the other club decides

### 7.1 The human club

Joe manages his club at the decision moments the engines surface, and only
there; everything else resolves automatically so the game moves:

- **Pitching change:** offered between plate appearances and at the hook
  policy's trigger points. The screen shows the current pitcher's fatigue
  state and the policy's recommendation (including "closer branch: Sutter
  indicated" when it fires) before Joe chooses. He may always override;
  the override is logged.
- **Pinch hitter / pinch runner:** offered when his club is batting with a
  bench available; the bench panel is one tap from the game screen at all
  times during his half-innings.
- **Steal, bunt, squeeze:** intent buttons available when the base state
  makes them legal (a runner to send, a bunt situation); the engines
  resolve the attempt.
- **Send / hold:** when an advancement read offers his runner the
  extra-base option (a choice entry on the engine's advancement
  chart, or the PATIENT-section lead-runner option) or a tag play at
  home arises,
  the choice is Joe's, mid-PA.
- **Forced coverage:** when a departure triggers the vacancy rule on his
  club, the fit pick is presented as the recommendation with its reasoning
  (carded at the position / best fit / bench order last resort); Joe
  confirms or picks another eligible man.
- **Defensive substitutions** between half-innings, from the bench panel.

These decision points are exactly the stops of the Play plate
appearance control (Section 5.2); nothing else interrupts it, and a
rare-play stop is a pause for the feed, not a decision.

### 7.2 The profile-driven club

The other club is driven by its encoded manager profile, inside the
governance hierarchy of Section 1.6:

- **Chicago under Chance** (when Joe manages Montreal): the four encoded
  traits from Joe's verbatim profile text — Tinker to Evers to Chance
  (Defensive Synergy), The Peerless Leader (Player-Manager Momentum),
  Inside Baseball Precision (Offensive Tactics), Combative Accountability
  (Error Recovery) — as `traits_chance.py` implements them over this
  engine, on top of hook policy and the closer branch (Sutter).
- **Montreal under Williams** (when Joe manages Chicago): the v2 package —
  Fireman deployment of the bullpen (Wetteland's chair), strict-platoon
  pinch hitting, late-inning defensive substitutions — in its pre-PA hook
  and wrappers, on top of hook policy and the closer branch. Williams has
  no encoded offensive play-calling traits; his club's plate appearances
  resolve on default policy, and the spec does not invent any.
- Every profile-driven decision is written to the feed with its reason in
  one line ("Williams: Wetteland in, closer branch, 9th, lead 2, Rogers at
  24 outs"), matching the audit standard of the table game's manager log.
  No silent moves.
- Decisions neither profile governs — the fall-throughs the default
  policy answers (Section 5.2) — carry the manager's name with the tag
  spelled out ("Williams (default policy): runner holds"), so a profile
  call and a machinery default are never confused in the feed.

### 7.3 Manage both

If Joe manages both clubs (Decision D2), both sides get the Section 7.1
decision points, the profiles advise in the feed but do not act, and the
hook/closer recommendation banners still show. This is the mode that maps
to how the table game is co-managed, minus Cooper.

## 8. Screens

### S0. Entry

A "Play" link in the existing views nav routes to `#/play`. If a saved
in-progress game exists, S0 is the resume banner (S6) above the setup
screen.

### S1. Fixture setup

- Fixture header: R1-06, Chicago Cubs vs Montreal Expos, exhibition.
- Home club toggle (Chicago at Wrigley Field default; Montreal at Stade
  Olympique). The venue's park card displays in full (both hands'
  BALLPARK sections) — the park is a player in this game and is shown
  like one.
- Starting pitchers: defaults Jenkins and Rogers; each club's five
  rotation chairs selectable.
- Lineups: the staged orders of Section 4, displayed with positions.
  Joe may reorder a lineup or swap a starter with a bench man before
  first pitch; any change is written into the game record as his, and
  the staged default is one tap to restore. (In-game changes go through
  Section 7.1, not this screen.)
- Lineup-editing legality, checked live as he edits (Start stays
  disabled, with the violated rule named, until the nine are legal):
  (a) the nine cover C, 1B, 2B, 3B, SS, LF, CF, RF, and DH exactly
  once each; (b) a fielder may be assigned only a position printed
  on his own card's positions list; the DH slot may take any
  rostered hitter; (c) no player appears twice, and all nine are
  rostered; (d) reordering is free — it changes batting order only;
  (e) a bench swap is one-for-one: the incoming man inherits the
  outgoing man's batting slot AND defensive position, and must be
  carded at that position (for a DH slot, any hitter qualifies);
  the outgoing man returns to the bench with no availability
  consequence — setup swaps are pre-game.
- Manager assignment per club: You / Profile (Decision D2).
  Neither club has a default assignment: Start stays disabled
  until both clubs carry one.
- Dice: FAC deck (default) / in-app dice roller / manual entry
  (a physical FAC card id, or raw values from physical dice)
  (Decision D1; Section 5.2). The pick is the game's default source;
  per-flip switching is D4.
- Declarations: no control exists in Phase 1 (Decision D3). A single
  line of text says so, so the absence is a decision, not an oversight.
- The game's seed, generated at setup and displayed; it is editable
  before first pitch, so a shuffle can be reproduced deliberately,
  and it is written into the game record. Reusing a seed never
  collides with an existing save (Section 5.3).
- Start game button. Starting writes the setup block (fixture, venue,
  lineups as actually fielded, starters, closers, managers, dice mode,
  seed) into the game record before the first pitch.

### S2. Game screen

One screen, no navigation away mid-game:

- **Scorebug:** inning and half, outs, score, and a running linescore.
- **Diamond:** base occupancy with runner names, and the out count.
  The engines track no ball-and-strike count — a plate appearance
  resolves whole — so the diamond shows none.
- **Matchup panel:** the current batter's full card and the current
  pitcher's full resolution data side by side, rendered in the same
  layout the player pages use (all four sections both hands, the OUT
  chart, the ratings strip; for the pitcher, the 2d6 table, stamina,
  hold, and fatigue state). Both cards fully visible is a requirement,
  not a nicety: Joe plays off the cards, and a card he has to tap open
  is a card he cannot play off. Viewport rule: at 1024 CSS px wide and
  above — the landscape tablet and desktop the game screen is designed
  for — both cards render in full, side by side. Below 1024 px the
  panel becomes a segmented toggle, [Batter | Pitcher]: one tap
  switches, it defaults to the batter, and it switches to the pitcher
  on its own whenever the current pitcher changes. The both-cards
  requirement holds wherever the screen fits it; one-tap access to
  the other card is the sanctioned fallback where it does not.
- **Roll panel:** the Draw / Roll button for the active source; the
  last step served displayed in full (for a deck or manual-card
  step, the FAC card id and all its faces; for a dice or raw-value
  step, the values served); in manual entry, the entry field for
  the pending step — a card id or the step's values, as the form
  chosen demands — labeled with the step it serves (and, at a
  manual card 2d6 step, the peek
  entry of Section 5.2).
- **Play feed:** the running audit feed, newest last, one block per plate
  appearance in the table game's form: state before, the flips, the
  section and read, the defense numbers where a defense check occurred,
  the outcome, state after. Managerial actions and profile decisions are
  feed entries too.
- **Decision bar:** contextual. When the human manager has a decision
  (Section 7.1), its buttons live here; otherwise the bar carries the
  single "Play plate appearance" advance. Between half-innings it
  carries pitching-change and defensive-substitution entry points for
  the human club.
- **Bench and bullpen panels:** both clubs, showing who is available,
  who has entered, who has left, each pitcher's in-game outs and fatigue
  state. Tapping a name on Joe's side opens the substitution or
  pitching-change flow (S3/S4).
- **Undo** button (Section 5.4) and a saved indicator ("Saved · after
  PA 47").

### S3. Substitution flow

A modal: the departing player and the reason at the top; the eligible
bench listed with mini card views (positions, fielding line, batting
card summary); the vacancy rule's pick highlighted with its one-line
reason when the departure forces coverage. Confirm, or choose another
eligible man. Illegal choices (a player who has left the game, a second
catcher problem the engine would reject) are not offered.

### S4. Pitching-change flow

A modal: the current pitcher's line and fatigue state; the available pen
with roles, in-game usage, and each arm's card summary; the policy banner
when the hook policy or closer branch indicates a move, naming the
indicated arm; the house hard rule's note (Section 6.1.12) when it is
what keeps starters off the list. Confirm applies the change and logs it
with its trigger (manager's call / hook policy / closer branch / profile:
Fireman).

### S5. Game over

- Final linescore, decisions (W, L, and SV when the save standard of
  Section 1.8 is met, computed off entry state).
- The full box score: batting lines in lineup order with substitutes
  shown in sequence, pitching lines with batters faced, team totals, and
  the audit equalities of Section 6.1.14 checked and shown passing.
- The game record summary: seed, dice mode, FAC draws consumed,
  reshuffles, undo count, managers, venue.
- Export buttons (Section 10) and the standing notice in plain text:
  **Exhibition. This game is not in the tournament record. Adoption is
  Joe's ruling, outside the app.**
- Play again (same fixture, fresh seed) and Back to bracket.

### S6. Resume

On `#/play` with a saved game: a banner naming the fixture, the inning,
and the score, with Resume and Discard. Discard asks once, and
the confirmation carries the only-copy warning in words:
discarding deletes the app's only copy of this game, and if it
was never exported, it is gone for good. Resume
restores the state with an empty undo stack — nothing before the
resume point can be undone (Section 5.4) — and the banner says so.
A finished game is not resumable; it offers its export instead
until cleared.

## 9. Decisions for Joe (defaults recommended; the build follows the default unless Joe rules otherwise)

- **D1. Dice input.** Recommended: **three sources, FAC deck
  tap-draw as the default** — the in-app dice roller and manual
  entry (a physical FAC card id, or raw values from physical dice)
  as peers serving the same steps (Section 5.2). Revision history,
  recorded honestly: the first draft recommended this same three-
  source shape; the cold-review revision then NARROWED it to the
  two card sources, on the premise that governed games run FAC-chart
  mode, whose chart text is keyed by the draw and cannot be derived
  from dice values; verification against the recorded games
  disproved the premise (Section 5.2's mode ruling: governed play
  is the deck as dice surface, engine charts resolving), and Joe's
  ruling of 2026-10-28 restored the three sources. One Joe-visible
  behavior from the narrowed draft SURVIVES the restoration, on its
  own merits: the manual card 2d6 peek of Section 5.2 — at a manual
  card 2d6 step Joe also enters the top card of his physical deck
  as the peek, and his next flip must be that card. The rejected
  alternative, reading the peek off the seeded virtual order, would
  have let the app's shuffle deal one die of every pair in the one
  mode whose point is that Joe's deck deals it.
- **D2. Who manages.** Recommended: **a pick at setup, no default club** —
  Joe chooses Chicago, Montreal, or Both per game. The un-managed club is
  profile-driven per Section 7.2.
- **D3. Declarations.** Recommended: **defer to Phase 2.** Grounds: the
  declaration mechanic is not adopted for tournament play generally; the
  two declarations currently live (Grace the Clutch Bat, Raines the
  Wheels) govern the table chat's official Game 1 only, by Joe's
  2026-10-28 ruling for that game, and this mode must not blur that line.
  The setup screen carries no declarations control. If Joe wants them in
  exhibitions, that is a one-line ruling and a Phase 2 line item, with
  the six-item menu and the public strength roll as designed in the
  pilots.
- **D4. Mid-game dice-source switching.** Recommended: allowed per flip
  among all three sources (deck draw, the dice roller, and manual
  entry in either form; see
  D1), recorded per flip — with the one refusal of Section 5.2: no
  switch while a manual 2d6 peek is outstanding. The alternative, locking the source at
  setup, is cleaner for reproduction and worse for how Joe actually
  plays.
- **D5. Undo depth.** Recommended: **unlimited within the game**
  (Section 5.4), at PA boundaries. Two edges, stated in the spec:
  undo does not survive a reload (a resumed game starts with an
  empty stack), and exporting a finished game seals it — before
  the export, the game-over screen can still step back into the
  game.
- **D6. Profile transparency.** Recommended: **the profile's reasoning
  shows in the feed for every decision** (Section 7.2), matching the
  PA-by-PA audit standard. No quiet mode in Phase 1.
- **D7. Save and resume.** Recommended: **localStorage autosave** after
  every plate appearance and managerial action, one saved game at a
  time. Starting a new game with a save present requires an explicit
  discard (Section 5.3), and unavailable storage degrades to unsaved
  play with the warning shown, never to a blocked game. Session-only
  play (no save at all) is the alternative; it loses a game
  to a closed tab, which on a 100-PA game is a real cost.
- **D8. Home club default.** Recommended: **Chicago home at Wrigley**,
  the staged Game 1 shape, with Montreal at Stade Olympique one toggle
  away. First pitch of the fixture defaults to Jenkins vs Rogers, as
  staged.

## 10. The game record and export

A finished game exports in the archive's standard shapes, extended to the
full-data standard the governed games keep (nothing pruned):

1. **Markdown box score** in the layout `scripts/import_game.py` reads
   (the R1-03 layout): heading, linescore table, decisions line, club
   batting and pitching tables with the full column sets, and the
   optional lines used — Date, Seed, Game recap left blank for Joe,
   Series state line reading "Exhibition, not a tournament game."
2. **Detail JSON** in the `games/<id>.json` shape of `SCHEMA.md`, but
   complete where the manual `#/add` form is not: the `rolls` array
   carries the full flip-by-flip history (FAC ids and faces or dice, in
   order), `manager_log` carries every decision of Section 7 with its
   trigger, and the record adds the governance block the set-engine
   states carry: hook triggers, substitution and pitching-change
   sequence, availability in and out (within the game), fatigue events,
   rare plays and lingering clauses as they fired, undo count, and the
   setup block of S1.
3. **Identity that cannot be confused with the record:** the game id is
   `EXHIBITION-CHC-MON-<seed>-<suffix>` — the seed plus the same
   four-character suffix the game's save id carries (Section 5.3) —
   and the series field is `EXHIBITION`, so two exported games that
   share a deliberately reused seed never collide on the record.
   Nothing in the export names R1-06 as its series; the fixture is
   described as "R1-06 fixture, exhibition" in the recap line only.

Export is a download and a copy button, as with `#/add`. Exporting
ends the game's life in the app: the export seals the game and
clears the autosave (Section 5.4), so after export the finished
game is gone from the app, and the exported files in Joe's hand
are the only copy. The app writes
nothing to the repository; what Joe does with an exported exhibition is
his ruling, outside this spec. (The export id above is the file's
label; it is built on the internal save gameId of Section 5.3,
sharing its seed and suffix under the EXHIBITION-CHC-MON label.)

If any audit equality on the game-over screen fails, the export still
generates — Joe may need the record of a broken game most — but it
carries the failure in its governance block as `AUDIT: FAILED — <the
equality and the two values>`, the standing exhibition notice is
joined by a second plain line ("This export failed an internal audit
check and is not adoption-ready"), and the port never adjusts a
number to make an equality pass.

## 11. Verification plan (before Joe is asked to trust a played result)

The port is not trusted because it reads well. It is trusted when it
reproduces the reference engines on their own recorded inputs.

### 11.1 Golden replay (the pass/fail gate)

Recorded games carry their complete flip history, so a game can be
replayed deterministically by feeding the port the same flips. The
gate is a scripted harness, not a person typing:

- **Driver:** `scripts/replay_driver.mjs` (Node, headless; no
  browser, no human input). It loads `data/playable_r106.json`,
  instantiates the port's Engine module (Section 5.5 — the same
  shipped code the browser runs, loaded through its Node export
  guard), and plays each replay start to finish — for Replay B,
  finish is the recorded segment's end: the driver halts when the
  recorded flip stream is exhausted, with the port's state
  standing at the top of the 7th as recorded, and does not play
  the game out.
- **Flip records (exact sources).** Replay A: the exhibition
  play-test game, seed 20261701 (Game 1 of the play test reported
  in "Play-Test R1-06 Exhibition," `PLAYTEST_R106_EXHIBITION.md` in
  the managers sandbox), recorded at
  `~/workspace/payoff-pitch-cubs/battery/state_EXHIBITION_r106_series_g1_20261701.json`
  — its `fac.history` (196 entries of [fac_id, purpose]) is the
  flip record, its `log` the per-PA outcomes, its batting and
  pitching lines the end state. Its producing stack, for the
  record: played by `playtest_driver.py` through
  `promotion_series_game.py`'s Chicago-host branch on the
  `pilot_chance_setup` stack — the Cubs v2 engine with FAC deck
  mode installed by `sim/fac.py` (the FAC dice surface only;
  `fac_chart` was NOT installed, so defense, steal, bunt, and
  advancement resolved on the engine's own charts fed by FAC
  draws: the history's purposes are 2d6, %, and 1d6 only, and the
  state's `fc_count` is empty), the addendum layer with
  Montreal's addendum merged into the home cache under the guest
  key, traits5 (the Dave Martinez trait-library layer, installed in
  the stack's order and inert in this fixture: no Martinez assignment
  exists in the game's traits state, so each of its wrappers delegates
  to the next layer untouched), the fatigue fix enabled, Chance over Chicago, and
  the Williams traits2 package re-pointed to the guest slot
  beneath Chance with McGraw pinned off; both clubs stack-driven
  from a managed base state (every decision by profile or default
  policy; no human input, no declarations); starters Jenkins and
  Rogers per `playtest_series_cfg_g1.json`, at Wrigley Field. Replay B: the official R1-06
  Game 1 segment as recorded through the top of the 7th, seed
  20261401, from `~/workspace/payoff-pitch-cubs/state_series_chc_mon_g1.json`
  (`fac.history`, 117 entries), cross-checked against the game's
  written record, "R1-06 Game 1" (`PP_R1_06_G1.md`, same home: PA
  numbering and outcomes), and `r106_g1_top7_evidence.json` (same
  home: per-PA and half-inning audits of the segment).
  `scripts/extract_replay_flips.py` converts each state file's
  history into a committed replay file
  (`scripts/replay/replay_a_flips.json`,
  `scripts/replay/replay_b_flips.json`): reshuffle markers
  ([0, purpose] entries) become explicit reshuffle events at their
  stream positions; every other entry is one step's card.
- **The ReplaySource.** A RollSource implementation that serves the
  recorded card ids in order, one per step, through the same step
  interface the UI uses. It bypasses the manual-entry refusal rules
  by design — those rules govern a human at a keyboard (no step
  pending, a duplicate id); the driver is always at a step and the
  recorded sequence is the authority. Peek behavior over the
  recorded stream: when the port's engine peeks (the 2d6 pair's
  second die, Section 5.2), the ReplaySource reads the next
  recorded entry's card without consuming it, and the step that
  follows consumes that same entry — the DeckSource peek
  contract, over the recorded stream. It logs every consumed value
  (PA index, step index within the PA, purpose, fac_id) to the
  driver log, so a divergence report names the exact step.
- **Managerial actions are scripted, not guessed.** Each replay
  carries an action script (`scripts/replay/replay_a_actions.json`,
  `scripts/replay/replay_b_actions.json`): every pitching change,
  substitution, and pinch move of the recorded game, anchored to
  the PA ordinal it precedes, extracted from the recorded state's
  pitcher spans and lines by the extraction script and verified
  once against the written record before the script is committed.
  During a replay the profile layers make no decisions; the driver
  applies the scripted actions at their anchors, and unscripted
  engine decision points (advancement choices and the like) take
  the reference sim's unmanaged-club default policy — which is
  what produced the recorded games, including the table game's
  segment, whose managed calls are all in its script.
- **Comparator.** After every plate appearance it compares the
  PA's outcome, the score, outs, bases, and inning/half against
  the recorded per-PA record. At every half-inning boundary it
  compares the linescore. At the end it compares the full batting
  and pitching lines, the ledger flag multiset, the per-purpose
  FAC consumption counts, and total draws. On the first
  divergence it prints the replay id, the PA index, the step
  index and purpose, the recorded fac_id against the consumed
  fac_id, and every state field that differs (recorded against
  port), and exits nonzero. There is no partial pass.
- **Replay B's declaration override (defined, and the only one).**
  Declarations are deferred (D3), but the recorded segment
  contains one declaration firing the port has no engine for, and
  the recorded implementation's own audit note (in `PP_R1_06_G1.md`)
  discloses that its snapshot restore rewound the FAC history at
  that plate appearance — so PA47's section flips do not survive
  in the final history at all; the original read survives only in
  the declaration trigger record stored in the state. The gate
  therefore carries one override record,
  `scripts/replay/replay_b_overrides.json`, containing: the PA
  index (47); the declaration (THE WHEELS, Tim Raines, Montreal);
  the trigger state (top of the 7th, 1 out, bases empty, Montreal
  5, Chicago 0, Raines batting against Hippo Vaughn); the recorded
  pre-conversion resolution (2d6=7 as 2+3, %=51, section TOUGH,
  result OUT G4, ground out 2B); the recorded live die (2 — the
  1d6 face of FAC 152, final-history position 107); the recorded
  conversion (infield single, Raines holds at 1st; booked delta
  AB 1, H 1, per the state's delta record); and the recorded
  post-conversion step (final-history position 108, FAC 171, the
  auto-steal check: last-card 2d6 total 6, no attempt booked).
  Driver behavior at PA47: it supplies the PA's two section steps
  from the override record (they are not in the history), lets the
  port resolve to the recorded ground out, then at the declaration
  seam — a ground-ball out by the declared player with the bases
  empty, the Wheels trigger exactly — it consumes history
  position 107 as the live die, verifies the die reads 2 (the
  hold-at-1st branch, 1-5), and books the recorded conversion
  instead of the out; the PA's remaining steps then come from the
  history normally, position 108 first. Comparator treatment:
  PA47 is compared on its pre-conversion resolution (against the
  trigger record), its booked outcome (against the recorded
  conversion), and its FAC accounting (against the override
  record: two supplied values plus two history entries) — never
  against the raw stream — and the comparator's output says so.
  Every other PA must match unaided. The segment's second
  declaration needs no override: Grace's Clutch Bat recorded
  qualifying 0 and changed 0 — its trigger (margin of two or
  fewer from the 6th inning) never occurred in a segment played
  at 5-0 and 7-0 — and the comparator asserts exactly that from
  the recorded linescore; if the assertion ever failed, the gate
  would fail rather than improvise a second override. (Fallback
  considered and not taken: substituting a second battery
  exhibition game for Replay B would dodge the only recorded
  interaction between the port and a live declaration seam. The
  override record is small, fully sourced from the state's own
  trigger record, and fenced to one PA, so the gate keeps
  Replay B.)


Pass bar, both replays: **100% of plate appearances resolve to the
recorded outcome — every plate appearance unaided, with the single
named exception of Replay B's PA47, which passes under its override
record exactly as specified above (compared on its pre-conversion
resolution, its booked conversion, and its FAC accounting against
the override record, never against the raw stream)**, identical
linescore at every half-inning boundary,
identical batting and pitching lines at the end, identical ledger flags
and FAC consumption counts. One divergence stops the build; the
divergence is diagnosed against the Python source line, not averaged
away.

### 11.2 Rule batteries, ported

- The **vacancy proofs (22/22 in Python)**, including the Ozzie Smith
  regression (Schoendienst at shortstop), re-run against the port's
  `substitute` equivalent.
- The **fatigue battery (23/23)** against the port's fatigue path.
- The **Chance battery (42/42)** decision points, replayed as setup
  states: the profile layer must make the same calls in the same states.
- **OUT-chart and partition checks** on the shipped data file: every
  shipped hitter card passes the same coverage standard the 2026-10-28
  audit ran over the governing population (no uncovered hole face),
  run over `data/playable_r106.json` itself, not over its sources.
- The **rare-play battery**: engineered states (saved state fixtures,
  in the project's established battery style) triggering each of the
  24 rare plays, asserting the booked outcome family for the
  bases-empty and runners-on variants by section. For the lingering
  wrapper family it asserts that `force_wheelhouse`,
  `force_tough_count`, and `force_inplay_count` are set by the
  triggering play, spent one per qualifying batter, carried across
  an inning break, and cleared at zero — and that a sacrifice bunt
  inside the window spends no count (the disclosed seam of
  Section 6.1.8).
- The **defense battery**: engineered states walking dice-mode
  `resolve_defense` through every coded outcome family: `def_pos`
  fielder and check-kind selection across the percentile bands,
  with the pitcher-table override (an ERROR result forcing an ERROR
  check; a RANGE result forcing a RANGE check, its C fielder
  redirected to CF); the re-rolled % in and out of the park RANGE
  band's HIT span and the ERROR band's ERR span; the HIT table
  (each position group's hit types and advancement bases, and the
  2B+ read converting to a triple at RUN 8 or better); the ERR
  table (dropped foul — the at-bat restarts with no AB booked, and
  the three-restart cap; single plus error with its unearned second
  advance; one-, two-, and three-base errors); the OUT table family
  entire (popout, lineout, lineout-DP with and without the range to
  double the runner off, GB+adv, GB-fc with a force at first and
  with no force, GB-DP A and GB-DP A,B with the range gate open and
  shut, short
  fly with the tag safe — asserting the sacrifice-fly PA-not-AB
  conversion — and with the tag out, short-fly DP on the arm gate,
  deep fly with automatic and with coach's-choice advancement);
  and the % = 00 DEFENSE read, asserting the sequence halts as a
  pending rare play and resumes (Section 5.2).
- The **steal battery**: the engine's STEAL_COL resolution across
  rating-letter and catcher-arm combinations and STEAL_HOME for
  steals of home, each % band asserted: DROP? on both branches of
  its 1d6 error check (and its cover selection — SS or 2B by the
  next batter's hand at second, 3B at third, C at home); SB+E2? on
  both branches of its catcher error check (the extra advance
  unearned); the caught band; and the safe band. The auto-steal
  jump read off the resolved PA's own 2d6 total, including the
  jump modifiers, the once-a-game jump-1 rule, the doubles
  requirement for a
  steal of third, the two-outs-and-runner-on-third hold, and the
  jump-total-12 case resolving through the
  pickoff chart (Section 6.1.17); and the manager-sent 12 case,
  asserting the named gap (ledger line, runner holds, no pickoff
  resolved).
- The **bunt battery**: every sac-bunt letter (A, B, C, D, F)
  against every row of the engine's BUNT table — MISS (each
  re-drawing the attempt's full step sequence; the second
  MISS books the strikeout), PO (including the squeeze double-play
  variant), DP (and its bases-empty reduction to LEAD), LEAD
  (asserting SH booked and no AB, per Section 1.7), E? on both
  branches of the error check (the fielding fielder named by the
  attempt's 1d6), SH — and the squeeze on column D
  both ways: success when the attempt's own 2d6 total is at
  or under the runner's RUN rating, and the failed squeeze (runner
  out at home, batter safe) asserting the engine's current booking
  (an at-bat) and the feed's unruled-case flag (Section 6.1.10).
- The **UI-state battery**: scripted checks against the shipped
  RollSource and GameState modules, run headlessly through the same
  Node export guard as the replay driver, pinning the state
  behaviors the replay gate cannot see. ManualSource: an entered
  card is removed from the virtual deck's remaining order wherever
  it sat, so no later draw this cycle can serve it; entering a card
  already consumed this cycle is refused, naming the step that
  consumed it; a reshuffle (three-inning, and separately exhaustion)
  restores all 256 cards, entered ones included, and clears the
  consumed set; and a 2d6 step served across entered cards takes
  its pair's second die from the peeked physical card of Section
  5.2 — the peek id recorded at the step, the next entry
  constrained to that card, a different id refused naming the
  peeked card. Raw-value entry: a value outside the pending step's
  type or range is refused (a third die face on a 2d6 step, a 100
  on a % step, a pair entered as a total, losing the low die);
  an accepted raw value leaves the deck's order, position, and
  consumed set bitwise unchanged and the draws counter unmoved.
  DiceSource: each step kind serves inside its range (the % serves
  00 as a live value), and a dice step likewise leaves the deck
  state untouched. Snapshots: restoring a PA-boundary snapshot restores
  the full DeckSource state exactly (the complete deck order, the
  consumed set, the stream position, and any outstanding peek):
  a card the undone PA consumed is drawable and enterable again,
  undoing across a reshuffle boundary restores the exact
  pre-reshuffle deck, every feed
  block after the restore point is marked "undone," and an export built after
  the restore contains only live-timeline blocks. Save lifecycle:
  the autosave fires after every resolved PA and every managerial
  action; a resume restores the saved state with an empty undo
  stack, the banner saying so; with storage forced to fail, the
  game stays playable in memory, the indicator reads "Not saved —
  storage unavailable," and the feed names the failure once.

### 11.3 Distribution sanity

200 auto-played games in the port, compared against the Python volume
run's environment (Chicago 5.80 runs/game, Montreal 3.98, Chicago 70%
of games; "R1-06 Volume Play Test," `PLAYTEST_VOLUME.md` in the
managers sandbox). The reference conditions, from that record: the
Python figures come from 60 best-of-7 series, 311 games, on a
2-2-1-1-1 venue pattern (Chicago won 72% of its games at Wrigley,
68% at Stade Olympique), starters rotating by chair within each
series, the Rest Chart book live between games of a series and
reset between series, seeds 20262001 upward in blocks of 10
per series:

- **Auto-play decision policy.** No human plays. Both clubs are
  profile-driven (Section 7.2: Chance over Chicago, the Williams v2
  package over Montreal, hook policy and the closer branch beneath
  them), and every decision point a human would get is answered by
  the reference sim's unmanaged-club default policy — the same
  `decide_attempt` advancement logic, auto-steal checks, and default
  send/hold behavior that produced the Python volume figures. There
  is no second, simpler policy: a policy invented for the test would
  measure the policy, not the port.
- **Fixture conditions, and the disclosed mismatch.** The staged
  lineups of Section 4 exactly; the FAC deck as dice surface
  throughout (the harness's DeckSource serves every step); a fresh
  seed per game. The port's 200 games are independent — Phase 1 has
  no series and no cross-game Rest Chart to carry — so the series
  conditions of the reference run cannot be matched inside Phase 1,
  and the comparison is an aggregate-environment check under the
  closest conditions Phase 1 allows: starters rotate by chair order
  across the 200 games (game 1 is Jenkins vs Rogers; each club's
  next game takes its next rotation chair, wrapping after the
  fifth), so each chair starts an equal share of games, as the
  series rotation gave it; venues alternate by game (odd games at
  Wrigley Field, even games at Stade Olympique), splitting the 200
  evenly between the parks as the 2-2-1-1-1 pattern roughly splits
  a series. The one structural difference stands disclosed: with no
  within-series Rest Chart, port relievers are never rest-limited
  where the Python run's pens were, so the port environment is
  expected to sit at the fresher-bullpen end of the reference
  environment, and a tolerance breach is diagnosed against that
  disclosure before it is read as a port defect.
- **Pass tolerance.** Chicago runs/game within ±0.50 of 5.80,
  Montreal runs/game within ±0.50 of 3.98, and Chicago win share
  within ±7 points of 70%. Basis: at 200 games the sampling
  standard error of a runs/game mean (per-game sd ≈ 3.4 in the
  Python run) is ≈ 0.24 and of a win share ≈ 3.2 points, so each
  band is roughly two standard errors — tight enough that a rule
  firing at the wrong rate (the class of error a replay cannot
  catch: each firing resolves correctly, but too often or too
  rarely) pushes the environment outside it, loose enough that
  honest sampling noise does not fail the build.

  *Build note (2026-10-28, distribution gate as run).* The
  prescribed run (scripts/distribution.mjs: 200 games, seeds
  20263001-20263200, venues alternating, chairs uniform,
  DeckSource throughout, the reference volume's own recorded
  environment — the promotion_series_game stack, which never
  calls Williams' pre_pa: the volume book records zero bench
  plate appearances in 622 team-games) landed Chicago 5.71
  (in band), Montreal 4.49 (band top 4.48), Chicago win share
  62.5% (band floor 63%): two figures marginally outside.
  Diagnosis, from the recorded evidence rather than the port:
  (1) Chicago's line matches the reference across every
  sample (five independent 200-game port samples pool to
  5.79 against the reference 5.80); the residual sits
  entirely in Montreal scoring (port samples 4.24-4.53,
  pooled 4.41, against the reference 3.98, whose own sampling
  error at 311 games is about ±0.17). (2) The reference
  blends two different Python engine builds: its 169 Wrigley
  games ran on the Cubs set's engine_v2.py (the stack this
  port ports, arbitrated exact by both scripted replays),
  while its 142 Stade Olympique games ran through run_sm on
  the Giants-Expos set's older engine.py. Measured directly,
  that engine at Stade over 40 games yields Chicago 4.33 and
  Montreal 3.35, a lower-scoring environment for both clubs
  than the same card on the governing stack (port at Stade:
  5.29 and 4.18); the blend accounts for much of the
  residual. (3) The app-game environment of Section 7.2
  (Williams' pre_pa live, bunt overlay on) was also measured
  on the gate seeds: Chicago 6.12, Montreal 4.53, win share
  69.5% (in band). (4) The per-PA event rates localize the
  residual: walks and strikeouts match the reference for
  both clubs and Chicago matches on every rate (hits .252
  vs .253 per PA, home runs .031 vs .035, walks .099 vs
  .103, strikeouts .168 vs .162); only Montreal's hit rate
  runs hot (.245 vs .233, about 1.9 sampling standard
  errors), the channel where the two engine builds' defense
  handling diverges. No tolerance, reference figure, or
  recorded datum was adjusted. The gate as specified stands
  marginally unpassed on the Montreal and win-share figures;
  the divergence evidence is this note, and whether the mode
  ships on it is Joe's ruling, not the build's.

### 11.4 Ship checklist

- `scripts/build_playable_data.py` output committed, and the playable
  build joins the CI generated-files gate itself: the check job
  rebuilds `data/playable_r106.json` and diffs it like the other
  generators, so a stale playable file fails the deploy the same way
  a stale peak162 (`data/peak162.json`, the generated 162-game peak
  stat lines) did in wave 2. The five existing CI generators
  re-run and their outputs unchanged (the playable build must
  not perturb rosters, peak162, leaders, previews, or the bracket image).

  *Build note (2026-10-28).* The rebuild itself cannot run on a
  clean CI runner: the build's inputs are the governing set
  homes, which live outside this repo and stay read-only. As
  shipped, the gate is two-part: the build is re-run locally at
  ship time (deterministic; two runs, one md5) and its output
  committed, and the CI check job runs
  `scripts/verify_playable_data.py`, which re-checks the
  committed file against the in-repo record (every fixture
  hitter's batting surface against data/cards.json's card_bat,
  position sequences, the 256-face deck, the fixture partition
  over the shipped rosters). A stale or hand-edited playable
  file fails the deploy on that step. The shipped file measures
  196,624 bytes, under the 1 MB line below, so it joins the
  service worker SHELL as written.
- `scripts/check_cardview_parity.py` passes (Section 5.5): the matchup
  panel's card renderer and the player pages' renderer agree on
  section order, field order, and labels.
- `validate_results.py` passes with the fingerprint unchanged.
- `sw.js`: CACHE version bumped; `js/play.js` and
  `data/playable_r106.json` added to the SHELL list (the deck-inclusive
  data file is roughly 700 KB by source sizes; if the shipped file
  exceeds 1 MB, it stays out of SHELL and is runtime-cached on first
  fetch like `data/cards.json`, and this spec line is amended with the
  measured size).
- The GitHub Actions run for the landing commit is SUCCESS and the
  served `data/playable_r106.json` byte-compares against the committed
  file — the standing deploy gate, learned the hard way in wave 2.
- A Pristine detector pass over the changed page source, per the
  standing pre-publish checks.

## 12. Risks and named seams

- **The corrected premise (2026-10-28).** This spec originally
  targeted FAC-chart mode: the draft, and the cold-review revisions
  that followed it, assumed governed games resolve defense,
  advancement, steals, and bunts off the FAC cards' printed chart
  sections (`sim/fac_chart.py`). No governed game has ever used
  that mode. The correction came from verification, not argument:
  both recorded states' flip histories carry only `2d6`, `%`, `1d6`,
  and RESHUFFLE purposes with `fc_count` empty, and every governed
  setup installs `fac.install` (the deck as dice surface) and never
  `fac_chart.install` — a fact §11.1's Replay A provenance recorded
  before the rest of the document caught up with it. Joe ruled
  2026-10-28 that Phase 1 mirrors governed play; Sections 5.1, 5.2,
  6.1, 6.2, 9, 11.2, and this section were realigned, and Decision
  D1's three-source recommendation was restored. The standing
  lesson, in the project's own discipline: a mode claim about the
  reference stack is verified against the recorded states before it
  is built on.
- **Pitcher data sufficiency.** The single most likely build surprise:
  a resolution-time pitcher field the web data build missed because
  `cards.json` does not carry it. Mitigated by construction (Section 3:
  serialize the engines' own loaded objects) and caught by Replay A if
  it happens anyway.
- **The two-copy engine arrangement.** The Python stack runs a re-pointed
  Expos copy under the Cubs engine with the Williams layer beneath
  Chance. The port is one implementation; the replay gate is what proves
  the merge did not change behavior, particularly layer order at hook
  checks.
- **Manual-entry trust.** Manual entry trusts Joe's typed card ids
  and typed dice values alike; a
  typo produces a legal but wrong game. The flip history makes it
  auditable after the fact, and the range and duplicate checks catch
  the impossible (an id outside 1-256, a card already consumed this
  cycle). The peek is checked too: the flip after a 2d6 peek must be
  the peeked card (Section 5.2), so a mistyped peek id surfaces at
  the next entry — refused, naming the peeked card — instead of
  dealing a wrong pair silently. But the port cannot catch a
  plausible wrong card. That is the nature of physical cards, and
  it is Joe's call at D1/D4.
- **localStorage limits.** One saved game, current state only: well
  under quota at this state size (snapshots are in-memory and never
  persisted, Section 5.4). Unavailable or over-quota storage degrades
  to unsaved play with the warning shown (Section 5.3); it never
  blocks a game. If a future phase keeps multiple saved
  games, this needs revisiting; Phase 1 does not.
- **The unruled failed squeeze** (Section 6.1.10) and the **fielder's
  choice RBI divergence** (Section 6.1.14) are the engines' standing
  behaviors. The port mirrors both and invents neither ruling.

## 13. Out of scope (explicit)

- Writing, merging, or altering any official tournament result, in the
  app or via its exports, without Joe's separate adoption ruling.
- Continuing, importing, or displaying the table chat's official R1-06
  Game 1 state.
- The other 30 clubs, their set homes, and their manager profiles.
- Declarations (Phase 2 candidate, Decision D3).
- **FAC-chart mode** (`fac_chart.install`: defense, advancement,
  steals, and bunts read off the FAC cards' printed chart
  sections). It has never governed a recorded game in this project;
  it is an unplayed variant, excluded outright — not a Phase 2
  deferral candidate unless Joe rules otherwise.
- Series play, cross-game availability, the Rest Chart between games,
  rotation carryover, standings, and any bracket effect.
- Manager traits beyond Chance and Williams as encoded for this fixture.
- Editing, rebuilding, or refitting any card; any use of the retired
  v0.5 / v0.2.3 engines or the v2 solver build path.
- The separate 1986 tracker app (`~/workspace/payoff-pitch-app/`); its
  data files are read-only sources here (parks, rare plays), nothing
  more.
- Multiplayer, accounts, network play, or any server component. The
  mode is one browser, one game, saved locally.
- A spectate mode (watching two profile-driven clubs play out a
  game in the app). The replay harness can already drive a game
  headlessly (Section 11.1); a watch-it-live surface is a
  conscious exclusion from this scope, not an oversight.
- Cosmetic card art. The matchup panel renders the cards' data in the
  player-page layout; no new graphics are commissioned by this spec.

---

*End of spec. Companion copy filed in the managers sandbox. This revision
answers the Goldfish review's blockers and should-fixes; no code starts
until the review's blockers are confirmed resolved or Joe overrules them,
per the standing EGM rule.*
