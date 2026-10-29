# Series Play Spec — "Play Next Game" from the Bracket (Playable Phase 2)
## Draft v4, 2026-10-29. Status: Draft v4 FROZEN. Goldfish cold-review rounds 1-4 all returned NOT READY; the gate was overruled by Joe on 2026-10-29 ("build it overrule the gate") and the build is authorized with the 16 round-4 findings as the build checklist.
## v4 changes: the generator's decision order is stated once and every null next_game follows from it; the mode contract (the button's series signal, the series file's fetch path, and the disagreement behavior) is specified; the selectable staff is defined field by field with the rotation and availability structures declared display-only; the cap trigger is greater-than-or-equal, with an overshoot battery case; the button rule is reconciled with the awaiting-booking state around one named offered-state operation, applySeriesFile, which also owns the landed clearing; the manual-dismiss rule is rewritten coherently; the playable-data definition is narrowed to exactly the completeness verdict's checks, the verdict gains cardinalities (9-man lineups, six-and-six benches and pens, non-empty rotations), and a runtime missing-data hold covers what no verdict checks; the two testable operations section 4.3 executes are named with their argument and return shapes; the dispatched flag's JSON encoding, its parse-failure behavior, and the game's persisted finish-date field (GS.finished_on) are specified; the club-record rule and the fingerprint's true scope are stated from the code; "frozen series" is defined from the importer's constant, and the inbox graduation rule is cited by file, section, and numeric criterion; section 4.1 prints the expected lineups, benches, pens, and stored games verbatim and pins the availability cross-check to exact array row counts (5 rows for the Game 2 load, 6 for Game 3); section 4.6 adds a pinned executable case for every edge the earlier drafts left unproven.
## v3 changes (kept): every mechanism the earlier drafts pointed at is stated in the text — the series file's schema field by field, the input schemas (including the IP parse rule and the aggregation fallback), the dispatched file's exact format and how each of its lines is produced, one button rule stated once, the seal contradiction resolved in favor of re-enterability, the booking actors named per route, the duplicate law and clinch proven as executable cases in section 4, and the assembly proof rebuilt on book-plus-fixture inputs with a full expected availability table.
## v2 changes (kept): the rest convention stated in full; the runtime data path specified; Joe's booking decision recorded as ruled (section 3.3); the game-number rule, "playable data," the clinch rule, and the single-source rule defined.

## 1. The ask (Joe, 2026-10-29)

"How can I continue a series once it starts, or play a series? It would be
nice to load from the bracket section and have Play Next Game."

## 2. Current state (verified in the code and the book, 2026-10-29)

- The app's Play link loads ONE baked fixture (data/playable_r106.json):
  Chicago vs Montreal in its Game 1 configuration, Wrigley, the Game 1
  staged lineups and starters. It reads nothing about the series: no game
  number, no series score, no park switch, no availability.
- Cross-game availability and the Rest Chart between games were explicitly
  deferred to Phase 2 in PLAYABLE_MODE_SPEC section 6.2. This spec is that
  Phase 2 item.
- R1-06 itself is underway in the book: tied 1-1, Games 1 and 2 stored.
  Game 1 was played by Joe in the app and booked through the
  export/import path; Game 2 was booked from Joe's scorecard. What the
  app never did was assemble Game 2 for him; the park, the starters,
  and the availability all had to be carried by hand.
- The series entry in the book already holds the scheduling facts: the
  stored games list, the wins, the status, and home_by_game (Game 3 home
  club: Montreal). The booked games carry full pitching lines, so rest
  and availability are derivable from the book itself, under the
  convention stated in section 3.2.

## 3. The feature

### 3.1 Entry point, playable data, the offered state, and the mode contract

**Playable data**, defined: for a series, exactly the artifacts the
generator's completeness verdict (section 3.2) checks, and nothing
else — (a) the fixture file data/playable_r106.json, whose fixture
block carries, for both of the series' clubs: `clubs` with a park
named for each club; `lineups` of exactly 9 entries per club;
`benches` of at least 6 names per club and `pens` of at least 6 names
per club (the tournament's six-and-six minimums); `rotations`
non-empty per club; `closers` present per club; and a top-level
`parks` record under the exact name of each club's park; (b) a park
face image under assets/parks/ for each of those parks (Wrigley Field
and Stade Olympique, shipped 2026-10-29); (c) the series file
data/series_r106.json, generated as section 3.2 describes. The
fixture's card bodies, FAC deck, and `pen_roles` are NOT part of this
definition and no verdict covers them; the runtime hold in section
3.2 covers their absence instead. Whether a series is
playable-data-complete is a verdict the generator computes and
records in the series file (section 3.2); the series file is
generated for the pilot fixture regardless of that verdict, so the
file's existence is never itself evidence of completeness. In the
pilot only R1-06 can qualify.

**The offered state and the button rule, stated once; every other
section refers back to this paragraph.** What a device offers for a
series is computed by one operation, `applySeriesFile` (defined in
section 3.3), from exactly two inputs: the series file and the
device's own localStorage (its dispatched flag and autosave slots,
section 3.3). Its result is one of: an offer of a game ("play"), the
awaiting-booking state for a dispatched game ("awaiting"), or no
offer ("none", with a blocked reason). The **Play next game** button,
on the bracket and on the series page alike, renders from that
result: for "play" it shows, naming the game ("Play Game 3"); for
"awaiting" it shows the awaiting-booking state for that number
instead of a fresh start; for "none" it does not show. Both pages
call the same operation over the same two inputs, so on one device
they can never disagree. The dispatched flag is device-local by
design: two devices can legitimately show different states for the
same number, and the book is the arbiter when a file is booked
(section 3.3).

**The mode contract.** The button is a link to the play route
carrying a series signal: its href is `#/play?series=<series id>`
(for the pilot, `#/play?series=R1-06`) — the play route's hash with a
`series` query parameter naming the series. The plain Play
navigation link carries no signal and always opens the exhibition
screen, unchanged. On entry (initial load and every hash change),
the play screen reads the signal: with no `series` parameter it opens
exhibition mode. With one, it fetches that series' file from the
site's data/ directory — the file name is `series_` plus the series
id lowercased with every non-alphanumeric character removed, plus
`.json` (R1-06 → data/series_r106.json, the same directory the
fixture file ships in) — and runs `applySeriesFile` on the result.
If the result is "play", the play screen enters series mode for the
offered game (section 3.2's assembly, resuming the game's slot if one
exists, section 3.6). If the result is "awaiting", it opens the
awaiting-booking state for that number (section 3.3). If the result
is "none" — including the fetch itself failing, for which
`applySeriesFile` receives null — the play screen does NOT enter
series mode: it opens the exhibition screen and shows a notice naming
the reason (the blocked reason from the result, or "no series file"
when the fetch failed). Signal and file disagreeing can therefore
never start a series game the file does not offer.

### 3.2 Assembly: inputs, the generator, the series file, the game number

#### Input schemas — exactly what the generator reads

From **the book** (tournament_results.json):

- The series entry for the fixture, fields: `id` (string, "R1-06");
  `team_a`, `team_b` (club codes); `status` (string); `wins` (an object
  keyed by club code with integer values, both clubs present);
  `games` (array of stored game ids); `home_by_game` (an object keyed
  by the game number as a string, "1" through "7", with the home club's
  code as each value).
- Each stored game of the series, fields: `id`, `series_id`,
  `game_in_series` (integer), `away`, `home`, `winner` (club codes),
  and `pitching`: an array of pitching lines, one per appearance, each
  line carrying `team` (club code), `name`, `player_id`,
  `appearance_order` (integer, 1-based within the club for that game,
  assigned in appearance order), and `outs` (integer). **`outs` is the
  field that holds outs**; stored lines carry outs directly, never IP
  text. A club's starter in a stored game is the line with
  `appearance_order` 1 for that club. Aggregation fallback: if a game
  somehow held two lines for the same club and pitcher name, the
  derivation sums their `outs` into a single appearance before applying
  any rule in this spec. (No stored R1-06 game does this — Games
  1 and 2 have exactly one line per appearing pitcher — the rule exists
  so the generator has a defined answer, not a crash or a double count;
  section 4.6 proves it on a fabricated split line.)
- Where the book's `outs` values come from, stated once: the importer's
  parse of the dispatched file's IP text (section 3.4), by the rule
  **outs = 3 × whole innings + the single digit after the decimal
  point**, where that digit is itself an out count of 0, 1, or 2
  (baseball notation: "6.1" is 6 innings and 1 out, 19 outs; "8.0" is
  24 outs; text with no decimal point is whole innings × 3). The
  generator never parses IP; it reads `outs`.

From **the fixture file** (data/playable_r106.json), the generator reads
only these fields of its `fixture` block and top level:

- `fixture.clubs`: object keyed by club code; each value carries
  `name` (full club name), `park` (park name), `short`, `manager`.
- `fixture.lineups`: object keyed by club code; each value an array of
  9 objects `{name, pos}` in batting order (the staged lineups).
- `fixture.benches`: object keyed by club code; each value an array of
  player names.
- `fixture.pens`: object keyed by club code; each value an array of
  pitcher names (the bullpen).
- `fixture.rotations`: object keyed by club code; each value an ordered
  array of pitcher names — the rotation chairs in order (chair 1 is
  the first name). For the pilot: CHC [Fergie Jenkins, Mordecai Brown,
  Rick Reuschel, Pete Alexander, Carlos Zambrano], MON [Steve Rogers,
  Pedro Martinez, Dennis Martinez, Bryn Smith, Javier Vazquez].
- `fixture.closers`: object keyed by club code. The generator checks
  only that it is present for both clubs (the completeness verdict
  below); the closer names are read by the play screen at runtime.
- `parks` (top level): an object keyed by park name; the generator
  reads only which keys exist.

The generator does not read the fixture's card bodies, the FAC deck,
or `pen_roles`; the play screen reads those from the fixture
file directly at runtime, as it does today.

#### The generator and when it runs

A new generator, scripts/build_series_data.py, sibling to
scripts/build_playable_data.py, bakes data/series_r106.json from the
two inputs above and nothing else. It reads nothing outside the repo
(in particular it never imports a set home's governed stack), and it is
deterministic (sorted keys, fixed separators, like
build_playable_data.py).

It runs at exactly these times:

1. Inside the importer's regenerate() step: the build appends
   build_series_data.py to the end of regenerate()'s script tuple in
   scripts/import_game.py, so every booking on either route rebuilds
   the series file from the new book in the same pass that rebuilds
   every other generated file (section 3.3 states the full order).
2. In the pages workflow's check job: the build adds
   build_series_data.py to that workflow's "Rebuild generated pages"
   step, so the check's `git diff --exit-code` covers the series file
   like every other generated file (section 4.5).
3. Standalone, whenever the fixture or the book changes outside a
   booking (the same way its sibling generators are run by hand).

**Completeness, computed here, not in the browser.** At bake time the
generator sets the series file's `playable_data_complete` to true if
and only if all of the following hold: (a) the book's series entry
exists and its `home_by_game` has all of the keys "1" through "7";
(b) the fixture file exists and its `fixture` block carries, for both
clubs: `clubs` (with a `park` named for each club), `lineups` of
exactly 9 entries per club, `benches` of at least 6 names per club,
`pens` of at least 6 names per club, `rotations` non-empty per club,
and `closers` present per club; (c) for each club's named park, the
fixture's top-level `parks` table has a record under that exact name
AND the repo contains the park's face
image at assets/parks/<slug>.webp, where the slug is the park name
lowercased with each run of non-alphanumeric characters replaced by a
single hyphen ("Wrigley Field" → wrigley-field, "Stade Olympique" →
stade-olympique — the two files shipped 2026-10-29). The generator —
running where the repo's files can actually be stat'ed — is the only
place this verdict is computed; pages and the play screen only read
the field. For the pilot today all three conditions hold, so the
pilot's series file records true.

**The generator's decision order, evaluated in this order at every
bake.** (1) If the stored game numbers are not a dense prefix,
`next_game` is null and `blocked_reason` is "gap". (2) Else, if the
series is complete — either club's wins at 4 or more, or the book's
series status is "complete" — `next_game` is null and
`blocked_reason` is "complete". (3) Else, if the completeness verdict
above is false, `next_game` is null and `blocked_reason` is
"not-playable-data-complete". (4) Else the generator assembles the
next game (the assembly below). `blocked_reason` is null exactly when
step 4 runs. Every expectation in section 4 about a null `next_game`
follows from this order and from nothing else; section 4.6 pins steps
1 and 3 as executable cases.

**Runtime hold.** The completeness verdict covers only the artifacts
of section 3.1's definition. If the play screen, on entering series
mode, finds anything else it needs missing or malformed in the
fixture file — card bodies, the FAC deck, `pen_roles`, or any other
fixture content the game cannot run without — it holds and reports
the gap on screen instead of starting a partial game. A hold is never
a partial start.

#### The series file (data/series_r106.json), field by field

- `series_id`: string. The fixture's series id ("R1-06").
- `team_a`, `team_b`: strings. The two club codes, copied from the
  book's series entry.
- `status`: string. Copied from the book's series entry ("scheduled",
  "in-progress", or "complete").
- `wins`: object keyed by club code with integer values; both clubs
  are always present, including at 0. Copied from the book's series
  entry. (Never an array, never a single number.)
- `stored_games`: array of objects, one per stored game of the series,
  sorted by game number, each `{number: integer, id: string,
  away: club code, home: club code}`.
- `playable_data_complete`: boolean, computed as above.
- `blocked_reason`: null when `next_game` is an object. When
  `next_game` is null, exactly one of: "gap" (the stored numbers are
  not a dense prefix), "complete" (the series is complete),
  "not-playable-data-complete" (the completeness verdict is false) —
  whichever the generator's decision order reaches first.
- `next_game`: **null** — the field present, its value null, never an
  absent field and never an object with null members — when there is
  no next game to offer, with `blocked_reason` saying why. Otherwise
  an object with exactly these fields:
  - `number`: integer. The next unplayed game number (rule below).
  - `id`: string. The game id ("R1-06-G3").
  - `home`, `away`: club codes. Home from `home_by_game` for this
    number; away is the other club.
  - `park`: string. The home club's park name (the key into the
    fixture's `parks` table and the source of the face slug).
  - `lineups`: object keyed by club code; each value the club's staged
    lineup, an array of 9 `{name, pos}` objects copied from the
    fixture.
  - `benches`: object keyed by club code; each value the club's bench
    name array, copied from the fixture.
  - `rotation`: object keyed by club code; each value the club's
    rotation name array in chair order, copied from the fixture.
    Display and derivation data only (see "Selectable staff" below);
    no name is selectable by appearing here.
  - `proposed_starters`: object keyed by club code; each value the
    proposed starter's name (string), or null for a club whose
    starter is blocked (see `starter_blocked`).
  - `starter_blocked`: array of club codes, empty in the normal case.
    A club is listed when the starter derivation (below) finds no
    legal starter for it.
  - `pens`: object keyed by club code; each value the club's usable
    bullpen for this game: the fixture's pen array in its original
    order with every unavailable arm removed. Capped arms remain,
    carrying their cap in `availability`.
  - `availability`: object keyed by club code; each value an array of
    rows, one per pitcher who appeared in game N-1, in that game's
    appearance order, each row `{name: string, prev_outs: integer,
    status: "free" | "capped" | "unavailable", cap_outs: 3 | null}`.
    `cap_outs` is 3 exactly when `status` is "capped", else null. A
    pitcher with no row did not appear in game N-1 and is free
    (assembly item 4 below).

**Selectable staff, defined.** The `rotation` arrays and the
`availability` rows are display and derivation data only: the load
screen shows them, and no name becomes selectable by appearing in
either. The selectable staff the play screen builds for the loaded
game is exactly: for each club, the selectable starters are the
club's rotation names whose availability status is free (a row with
status "free", or no row at all) — one of whom is the proposed
starter — plus, through Joe's override, any other free pitcher on
the club (assembly item 3); and the selectable bullpen is the club's
`pens` array (the generator has already removed every unavailable
arm), each capped arm carrying its `cap_outs` from its availability
row. A name whose availability row reads "unavailable" is selectable
in no role; a capped name is selectable only in relief, never as a
starter (the strict default of assembly item 4). Section 4.1 asserts
this for Game 3 by name.

#### Game number and the dense prefix

The next game is the lowest number in the series' scheduled sequence
(the `home_by_game` keys, "1" through "7") with no stored game in the
book. Invariant: stored numbers are expected to be a dense prefix
(1..k stored, k+1 next). If the stored numbers are not a dense prefix,
the generator's decision order (step 1) writes `next_game` null with
`blocked_reason` "gap", the button does not render (by the button
rule), and the generator prints the gap in its output; nobody guesses
a number. A stored number is never offered again — enforced by
construction here, and again at booking by the importer (section 4.3).

#### Assembly of the next game N

1. **Home club and park**: `home_by_game` for N; the park is that
   club's park from the fixture's `clubs` (Game 3: Montreal, Stade
   Olympique). Completeness (above) has already established that the
   park has a fixture record and a face; if it had neither, the
   verdict would be false and no game would be offered at all.
2. **Lineups**: the staged lineups from the fixture file. Per Joe's
   ruling (2026-10-29) lineups are his: the app loads the existing
   staged lineups and he edits them before first pitch if he wants.
   The AI never builds a lineup.
3. **Starters**: the pointer rule. "Most recent booked game" means,
   per club, the stored game of this series with the highest game
   number. The pointer starts at the chair following that game's
   starter for the club, in the fixture's `rotations` order, cycling
   (after the last chair comes chair 1); with no booked games, chair
   1. If the most recent booked starter is not a rotation chair (an
   emergency start — including a starter Joe named from outside the
   rotation, see the override below), the pointer follows the last
   booked starter who was a chair, or chair 1 if there is none
   (section 4.6 proves this fallback on a booked emergency start).
   From the proposed chair, advance chair by chair — cycling the same
   way, past the last chair to chair 1 — past any arm the availability
   derivation marks unavailable or capped, and propose the first free
   arm. If a full cycle finds every chair unavailable or capped, there
   is no legal starter for that club: `proposed_starters` for the club
   is null, the club is listed in `starter_blocked`, and the load
   holds and reports: the play screen shows a hold notice naming the
   club and the reason instead of a startable game, and the generator
   prints the block in its output, where the section 4.6
   starter-blocked case surfaces it. The pick is shown before first
   pitch; **Joe may override it with any FREE pitcher on the club** —
   a rotation chair or not (a bullpen arm may be named). An
   unavailable or capped arm cannot be named: availability is book
   law, not a preference (section 4.6 proves both rejections). The
   override needs no pointer bookkeeping: the pointer derives from
   booked starters at every load, and an override simply becomes the
   booked starter the next pointer follows (or, if he is not a chair,
   the emergency-start fallback above applies to the following game).
   Check against the record: Game 1 starters were the chair-1 arms
   (Jenkins, Rogers); Game 2's were chair 2 (Brown, Pedro Martinez);
   Game 3's proposals must be chair 3 (Reuschel, Dennis Martinez).
4. **Availability — the house outs convention, stated in full.**
   Source: the fatigue-fix layer that every governed stack installs,
   fatigue_fix.py (function _availability, with the convention stated
   in its own header) in the Nationals set home, mirrored line for
   line in the app as ffAvailability in js/play.js, and written into
   the official game records as each game's availability section
   (PP_R1_06_G1_OFFICIAL_seed229154.md, PP_R1_06_G2_OFFICIAL.md). At
   the end of a game, each pitcher who appeared gets one row for the
   NEXT game from the outs he recorded in that game:
   - under 6 outs: **free** (no restriction);
   - 6, 7, or 8 outs: **capped** — available next game, capped at
     3 outs;
   - 9 or more outs: **unavailable** next game.
   The bands are role-blind: the same outs bands apply to starters
   and relievers; the layer computes the row from the pitching span
   alone. A restriction lasts exactly one game: the derivation for
   game N reads ONLY the pitching lines of game N-1 (the stored game
   with number N-1; the dense-prefix invariant guarantees it exists,
   and game 1 has no derivation, every arm free). A pitcher who did
   not appear in game N-1 has no row and is free — which is also how
   a pitcher who sat out his unavailable game returns. In the book, a
   pitcher's outs for a game are the stored pitching line's `outs`
   (with the aggregation fallback of the input schemas), so the
   derivation recomputes from tournament_results.json alone.
   Unavailable pitchers are excluded from the loaded game entirely
   (assembly: they are absent from `next_game.pens` and can never be
   proposed; enforcement in the game: "In-game enforcement" below);
   capped arms carry their 3-out cap into the game. The derived rows
   are displayed on the load screen before first pitch.
   Worked check, Game 3 from Game 2's lines: Pedro Martinez 24 outs →
   unavailable; Mordecai Brown 18 → unavailable; Wetteland 3, Strop
   2, Sutter 4, Smith 3 → free. And Game 2 from Game 1's lines:
   Jenkins 19 and Rogers 19 → unavailable; Wood 6 → capped at 3;
   Burke 5 and Sutter 2 → free. Both match the recorded availability
   sections exactly (the row counts are pinned in section 4.1).
   **Marked gap, for Joe**: the convention caps a pitcher's USE at 3
   outs and never distinguishes roles, and no recorded case presents
   a capped arm as a starter. Whether a capped arm may be NAMED the
   starter (a start the cap would end after 3 outs) is not determined
   by the sources. Until Joe rules, the assembly treats a capped arm
   as not proposable and not nameable as the starter (assembly item
   3), the strict reading; his ruling can loosen it without touching
   anything else in this section.
5. **Series state on screen**: series score, game number, park, and
   the availability rows, visible before and during the game.

#### In-game enforcement of availability

- **Unavailable arms** are enforced twice, so there is no path around
  them: the generator excludes them from the game's usable roster
  (`next_game.pens` omits them and the starter derivation can never
  propose them), and the play screen builds each club's selectable
  staff for the game from the series file's assembly exactly as
  "Selectable staff" defines — an unavailable arm is never loaded
  into the game and so is not selectable at any point.
- **Capped arms**: the cap travels in the pitcher's `availability`
  row (`cap_outs`: 3). The play screen today has NO in-game cap
  enforcement point: its ffAvailability computes next-game rows at
  the end of a game and nothing checks a pitcher's outs against a
  cap while he pitches. The build therefore adds the enforcement
  explicitly: at every plate-appearance boundary, before the next
  plate appearance is offered, the play screen's pitching-change
  logic compares the active pitcher's outs recorded in this game
  against his `cap_outs`; when the recorded outs are **greater than
  or equal to** the cap, a pitching change is forced — the
  change-pitcher decision is presented and play cannot continue
  until a new pitcher is selected. The comparison is ≥, deliberately:
  outs accrue inside a plate appearance (a double play adds two), so
  a capped pitcher can stand at 2 outs and arrive at the next
  boundary at 4 without ever equalling 3 at a boundary; an equality
  check would let him pitch on. That PA boundary is the enforcement
  point, and section 4.5's battery gains cases that reach a cap
  exactly and that overshoot it, proving the forced change fires in
  both.

**Single source of truth.** The book is authoritative for assembly
and for validation. The set-home series records (the official game
records in the Cubs set home) are a cross-check that must agree with
the derivation; the assembly proof (section 4.1) performs that
comparison for the pilot, and a disagreement blocks any booking built
on the derivation and is reported to Joe, never silently resolved in
either direction.

### 3.3 Identity, the confirmation tap, and booking

- The loaded game carries its real identity from the first pitch:
  series id and game number (R1-06, Game 3), not the EXHIBITION stamp
  the Phase 1 fixture uses.
- **Joe's ruling (2026-10-29)**: on completion, ONE in-app
  confirmation tap books the game directly. Joe's part is the tap
  and nothing else; the named actors below do the rest.

**What the tap does.** The app is a static site with no repo
credentials; it cannot commit or push, and no in-app write path to
the repo exists in this architecture. The tap is therefore
finalize-and-dispatch, in this exact order:

1. The finished game is sealed against further play and undo in the
   app (the play screen's seal state), and the app builds the
   import-ready markdown file for the game in the exact format of
   section 3.4, named for its identity (R1-06-G3.md).
2. The app downloads the file to Joe's device and sets the
   **dispatched flag** for the game identity: a localStorage key
   `pp-series-dispatched-<game id>` (for the pilot,
   `pp-series-dispatched-R1-06-G3`) whose value is a JSON string of
   exactly this shape: `{"game_id": <string>, "dispatched_on":
   <string>, "file_name": <string>}`, where `dispatched_on` is the
   device-local date of the tap in YYYY-MM-DD form — for a pilot
   dispatch on 2026-10-29, the value is `{"game_id": "R1-06-G3",
   "dispatched_on": "2026-10-29", "file_name": "R1-06-G3.md"}`. The
   prefix deliberately does not start with the autosave prefix
   `pp-play-r106-`, because the play screen's save scan (peekSave)
   parses every key under that prefix as a saved game. The flag is
   local bookkeeping only, never evidence a booking landed. If a flag
   value ever fails to parse as JSON of that shape, `applySeriesFile`
   treats the flag as absent, removes the corrupt key, and reports
   the unreadable marker in its result's `notices`; a corrupt flag
   never blocks an offer and never fabricates one.
3. The autosave slot for the game identity is **retained, not
   cleared** — this is the one place series play departs from the
   exhibition seal, which clears its slot at export. The retained
   slot holds the finished game, which Joe can re-enter to view the
   final and re-download the file (the "open it for export" path the
   play screen already offers for a finished save). Sealing closes
   undo and play; it never strands the only copy of a played game.

**Awaiting booking.** While the dispatched flag for a game is set and
the series file does not list the game among `stored_games`,
`applySeriesFile` returns the awaiting state for that number: no
fresh start for that number on that device. The actions offered are
reopening the finished game (to re-download the file) and dismissing
the dispatch (below). The flag clears in exactly two ways:

- **Landed**: the clearing is owned by `applySeriesFile`. Whenever it
  runs (bracket render, series-page render, play-screen entry) and
  finds a flag set for a game the applied series file lists among
  `stored_games`, it clears the flag and discards the retained
  autosave slot for that identity before computing the offer; the
  offer then comes from the series file alone, which is the
  following game.
- **Manual dismiss**: Joe dismisses the dispatch from the play
  screen's awaiting-booking banner. The banner exists only while the
  flag is set AND the game is not in the applied series file's
  `stored_games`; once the game has landed, the landed clearing above
  has already removed the flag, so there is no banner to dismiss.
  Dismissing means "I have handled this dispatch myself" — he booked
  it by another path, threw the file away, or would rather replay
  the number. It clears the flag AND discards the retained slot for
  that identity. The offered state is then recomputed from the series
  file alone: the following game if this one is in fact stored, this
  same number as a fresh start if it is not, and no game at all if
  the series is complete (a clinched series, or Game 7 already
  stored). The dismiss exists so a dead dispatch — a file Joe decided
  not to book, or a game he would rather replay — can never lock a
  number forever on a device.

**The two routes to the repo, and who performs each step.** Both
routes converge on scripts/import_game.py; the importer is the only
writer of the book on either route.

- **Route A (local importer) — the route every app booking to date
  has used.** (1) Joe hands Cooper the downloaded file in chat.
  (2) Cooper stages the file in the repo's gitignored imports/ area
  (never inbox/) and rehearses it in section 4.2's form — the real
  file applied to a scratch clone of the repo; a rehearsal failure
  stops everything and is reported to Joe with the importer's problem
  list. (3) Cooper runs
  `~/workspace/tools/pp-t32-venv/bin/python scripts/import_game.py
  imports/R1-06-G3.md --apply` in the real repo. On exit 0, Cooper
  makes ONE commit containing everything the apply produced — the
  updated tournament_results.json, the new games/R1-06-G3.json detail
  file, and every regenerated output, data/series_r106.json included
  — and pushes it to main. (4) The push triggers the pages workflow
  ("Tournament site", .github/workflows/pages.yml): its check job
  validates the archive, rebuilds the generated files, and requires
  `git diff --exit-code` to pass before the deploy job publishes the
  site with the new series file.
- **The inbox route.** (1) The file enters inbox/ by a commit to main
  that adds inbox/R1-06-G3.md: Joe makes that commit himself (for
  example by uploading the downloaded file through GitHub's web UI),
  or hands the file to Cooper, who commits and pushes it for him.
  Either way, a human's commit is what puts the file in inbox/; the
  workflow never fetches it from anywhere else. (2) The push triggers
  the "Inbox import" workflow (.github/workflows/inbox.yml), which
  runs scripts/import_inbox.py — the same import_game.py apply path —
  and then itself makes ONE commit ("Import box scores from inbox.",
  by github-actions[bot]) containing the updated book, the detail
  file, every regenerated output including data/series_r106.json,
  and the source file's move to inbox/imported/, and pushes it; its
  deploy job then publishes the site. (3) A failed import on this
  route: the file stays in inbox/, the workflow commits only the
  error report to inbox/errors/R1-06-G3.txt, the run fails, and
  nothing else in the repo changes.

**Regeneration order, stated once.** Inside a successful apply, the
importer (1) appends the game and its detail file, refreshes the
series entry (wins, status, games list) and recomputes the club
records, and writes tournament_results.json; then (2) regenerate()
runs its script tuple in order — build_peak162.py, build_rosters.py,
build_leaders.py, build_series_previews.py, build_bracket_image.py,
build_cards.py, and build_series_data.py appended last by this build
— rebuilding every generated file from the NEW book, the series file
included; then (3) validate_results.py runs. So the book is written
first and the series file is always rebuilt from the book that
contains the new game, and one commit carries both. A failure at any
step makes the importer restore the pre-import archive and re-run
regeneration against the restored book, so no generated file can
carry a refused game.

**Failure.** The importer is atomic: a game it refuses changes
nothing in the archive (it restores the archive on refusal), and a
Route A failure never becomes a commit. So a failed dispatch leaves
the game unbooked and says so: on Route A, Cooper reports the
importer's problem list to Joe; on the inbox route, the error report
lands in inbox/errors/ and Cooper surfaces it the same way. The
series file never shows the game, the dispatched flag stays set
(awaiting booking), the finished game stays re-enterable in the app
for a corrected re-dispatch, and the manual dismiss remains the exit
if Joe would rather replay the number. There is no half-booked state
to clean up.

- Standing law, unchanged: a game counts only when Joe plays it, and
  no AI-played game ever books.

**The two testable operations.** The build exposes two operations so
section 4.3 can execute the seal rules headlessly; the bracket, the
series page, the play screen, and the batteries all call the same
operations, never parallel logic.

- `dispatchSeriesGame(finishedState)` → `{fileName: string, content:
  string}`. Builds the section 3.4 file for a finished series game
  state and returns its name and full text. (Setting the flag and
  retaining the slot are the seal flow's storage effects around this
  call; section 4.3 asserts them.)
- `applySeriesFile(seriesFile, storage)` → `{kind: "play" |
  "awaiting" | "none", number: integer | null, id: string | null,
  blocked_reason: "gap" | "complete" | "not-playable-data-complete" |
  "no-series-file" | null, notices: array of strings}`. Applies a
  series file (or null, when the fetch failed) against a storage
  object (the browser's localStorage in the app; the harness's
  in-memory storage in tests) and returns the offered state of
  section 3.1. Its side effects, in order: it discards every autosave
  slot whose game id the file lists among `stored_games` (for a
  dispatched game this is the landed clearing, and the game's flag
  is cleared with it; for an undispatched mid-game slot it is the
  stale-slot discard of section 3.6); it removes a corrupt dispatched
  flag and notes the removal in `notices`. The result is then:
  "awaiting" when a live flag names the file's next offered number
  and that game is not stored; "play" when the file offers a game and
  no live flag covers its number; "none" otherwise, with
  `blocked_reason` from the file ("no-series-file" when `seriesFile`
  is null).

### 3.4 The dispatched file, element by element

The importer (scripts/import_game.py) keys a markdown game entirely
from the file's own text. The series export is a NEW emitter built to
the layout below — not today's exhibition emitter, whose heading
("# Exhibition Game:"), short club names in the linescore, PA/SH/SF/GDP
batting columns, "Pitcher" pitching header, and unmarked substitutes
are exactly why app games to date needed conversion before booking.
The dispatched file, in order:

1. **Heading**, one line, by this pattern:
   `# <series id> Game <number>: <away club full name> at <home club full name>`
   — the importer's GAME_HEADING pattern (series id, game number, and
   the two clubs resolved by full name against the archive's club
   index; it is an Away-at-Home pattern: the club before "at" is the
   away club, the club after it is the home club). The away club is
   the club that is not the home club; the home club is
   `home_by_game` for the number. For Game 3 the home club is
   Montreal, so the heading is:
   `# R1-06 Game 3: Chicago Cubs at Montreal Expos`.
2. **`**Date:** YYYY-MM-DD`** — the game's finish date, stored as the
   game's date. Production: the play screen stamps the game state
   once, at the moment the game reaches its final state, into the
   persisted field `GS.finished_on` (YYYY-MM-DD, device-local — the
   finish-date counterpart of `GS.seed`, which is set at creation),
   and the emitter reads `GS.finished_on` when the file is built at
   dispatch. A re-download of a dispatched game re-reads the same
   field, so the stamped date is always the original finish date,
   never the re-download date.
3. **`**Seed:** <integer>`** — the game's seed. Production: the play
   screen records the seed on the game state at creation (GS.seed,
   set from the setup screen's Seed field when the game is created)
   and holds it for the whole game; the emitter reads GS.seed when
   the file is built at dispatch and writes it here. (Game 1's stored
   record carries its seed this way; Game 2's record carries 0
   because its booking came from a paper scorecard. A dispatched file
   always carries the real seed.)
4. **`**Game recap:** <text>`** — stored as the game's recap.
   Production: the emitter composes it from the finished game's
   linescore totals and the heading's clubs, by the fixed template
   `<series id> Game <number>. <away full name> <away runs> at <home
   full name> <home runs>.` — for the Game 3 example above, "R1-06
   Game 3. Chicago Cubs 2 at Montreal Expos 4." No hand-written text
   is involved.
5. **`**Series state after this game:** <text>`** — stored as the
   series recap text. Production: the emitter computes the post-game
   wins from data it holds — the series file's `wins` (the pre-game
   state it loaded) adjusted by this game's winner — and renders
   exactly one of three templates: if the post-game wins are level,
   "Series tied <w>-<w> after Game <number>."; if a club leads
   without clinching, "<leader full name> leads the series
   <leader wins>-<other wins> after Game <number>."; if the winner
   reaches 4 wins, "<winner full name> wins the series
   <winner wins>-<loser wins>."
6. **The linescore**, the file's first table. Header row: `Team`,
   then one column per inning played (9, or more for extra innings —
   extra innings simply add columns), then `R`, `H`, `E`. One row per
   club, **full club name** in the first cell (the importer resolves
   it through the club index; the exhibition emitter's short names do
   not resolve and are not used here). Each inning cell is that
   half-inning's runs; the one exception is the home club's cell for
   a bottom half-inning it did not bat (possible only in the final
   inning), written `x`, which the importer skips. `R` is the club's
   total runs, `H` its total hits, `E` its errors.
7. **The decisions line**: `**Decisions:** ` followed by entries
   joined by ` · `, each entry of the form `<label>: <name> (<club
   full name>)`. `W:` and `L:` are always written (the importer
   records a problem for a game with no winning or no losing
   pitcher); the W entry names a pitcher on the winning club, the L
   entry a pitcher on the losing club. `SV:` is written only when
   the game produced a save, naming a pitcher on the winning club
   who is not the W pitcher; when no save exists the entry is simply
   absent and the importer stores no save. Names and clubs come from
   the game's recorded decisions (the play screen's deriveDecisions).
   (The importer also resolves a club code in the parentheses; the
   app always writes the full name.)
8. **Four sections**, away club first, then home club, each club
   contributing `## <club full name> batting` then `## <club full
   name> pitching`:
   - The **batting table**, columns in this exact order:
     `#`, `Player`, `AB`, `R`, `H`, `2B`, `3B`, `HR`, `RBI`, `BB`,
     `SO`, `HBP`, `SB`, `CS`, `SAC`, `GIDP`. The `#` cell is the
     lineup slot: starters are numbered 1-9 in batting order; a
     substitute's row carries the slot at which he entered, and his
     Player cell is his name followed by ` *` — the substitute
     marker is a trailing asterisk on the name (the importer detects
     the asterisk in the name cell, and independently treats a
     repeated slot as a substitution). Rows are ordered by slot, and
     within a slot by entry order (the starter's row first, then his
     substitutes in the order they entered). Every value is the
     player's game total as an integer. The `SAC` cell carries the
     player's sacrifice total from the app record, SH + SF (both are
     sacrifices under the tournament's scoring rule; the importer's
     layout has the one SAC column and stores it as the line's sac).
     There is no totals row: the importer validates sums itself, and
     a totals row would be read as a player.
   - The **pitching table**, columns in this exact order: `Player`,
     `IP`, `H`, `R`, `ER`, `BB`, `SO`, `HR`, `HB`, `BF`. Rows are in
     appearance order (the starter's row first — the importer assigns
     `appearance_order` by row order). `IP` is baseball notation as
     defined in section 3.2: whole innings, a dot, and the extra outs
     (24 outs writes "8.0"; 19 outs writes "6.1"; 2 outs writes
     "0.2"). `HB` is hit batters (the app record's HBP-against).
     Every value is an integer except IP. No totals row.

With those elements the file satisfies the importer's keying by
mechanism: series and number from the heading; the club pair and the
home club checked by the importer at apply time against the book's
series entry (R1-06's entry pairs CHC with MON, and its home_by_game
for Game 3 is MON, matching the heading); and the stored-game
comparison by game id (R1-06-G3, section 4.3). One refusal bounds the
mechanism, stated exactly: the importer's apply refuses any FRESH
game whose series is in its FROZEN_SERIES set (scripts/import_game.py)
— R1-01, R1-02, R1-03 — with the problem "would change locked series
<series id>". Those are the three series whose entries the validator
separately hashes (FROZEN_SERIES and FROZEN_SERIES_HASH in
scripts/validate_results.py; the validator's own comment: the hash is
of R1-01, R1-02, and R1-03 only — later series may gain games, these
three may not). Frozen is an importer lock, not a synonym for
complete: R1-04 and R1-05 are complete but not frozen (section 3.5).
R1-06 is not frozen; the refusal is named here only to mark the
boundary of the mechanism.

### 3.5 Clinch rule and club records

The series format is best of seven, first to 4 wins. Established from
the book on 2026-10-29: all 16 R1 series entries carry `home_by_game`
for games 1-7, and the five completed R1 series (R1-01 through
R1-05) each stand at exactly 4 wins for the winner. (Later-round
series are formed only when their feeding round completes — the L1
entries currently read "awaiting-feeders" with no `home_by_game` —
and are outside this spec until they exist.) The importer's
refresh_series maintains the series entry from the stored games on
every apply: it recomputes the wins, sets the status to "complete"
(with winner and loser) when a club reaches 4 wins, and to
"in-progress" when at least one game is stored. The series file
copies that status, and the generator's decision order (section 3.2,
step 2) does the rest: at 4-1 the series is complete and games 6 and
7 are simply never offered; the wins reaching 4, not the exhaustion
of the schedule, is what completes a series. Section 4.4 proves this
end to end.

**Club records, as the importer actually recomputes them.** Every
apply ends with recompute_teams over the whole book
(scripts/import_game.py), after refresh_series has updated the
touched series: `game_wins` and `game_losses` are counted over all
stored games; `series_wins` gains 1 for the winner of each series
whose status is "complete", and `series_losses` 1 for its loser; a
club's `bracket` is "winners" while its `series_losses` is 0,
"losers" at exactly 1, and "eliminated" at 2 or more (the club's
`eliminated` flag mirrors `series_losses` ≥ 2). The first-loss rule
is exactly that middle step: a club's first series loss drops it to
the losers side; it is not eliminated. Section 4.4's club-record
expectations are read off this rule.

Complete and frozen are different properties of a series: five R1
series are complete; only R1-01, R1-02, and R1-03 are frozen
(section 3.4).

### 3.6 In-progress games and the dispatched flag

The play screen already autosaves to localStorage under the prefix
`pp-play-r106-` plus a game id, one slot per id, with resume and
discard paths (peekSave / loadSave / discardSave in js/play.js; the
resume banner surfaces one saved game at a time, the first slot found
under the prefix). For series play the game id IS the fixture identity
(e.g. R1-06-G3 — so the slot key is `pp-play-r106-R1-06-G3`), with no
suffix disambiguation: exactly one slot per series game number. An
unfinished exhibition keeps its own generated ids, so an unfinished
series game and an unfinished exhibition are separate slots and
starting one never clobbers the other. Pressing Play next game for a
number with an existing slot resumes that game. A series game Joe
walks away from mid-game stays resumable indefinitely; nothing in
this feature expires a slot.

A finished series game that Joe dispatches keeps its slot under the
rules of section 3.3, which is the only place the dispatch, landed,
and dismiss rules are stated. Separately: if a number becomes stored
by some other path while a mid-game slot for it exists (say Joe plays
the game at the table and it is imported from a scorecard), then on
the next `applySeriesFile` run against a series file listing the
number among `stored_games`, the stale slot is discarded and the
following game is offered — a stored number is never resumable.
Section 4.6 proves this discard.

### 3.7 What does not change

- The free-standing exhibition fixture stays as it is for pickup
  games, including its own export stamp, its seal-clears-the-slot
  behavior, and its autosave ids.
- No other series becomes playable by this spec; each future fixture
  needs its playable data (section 3.1) built the way R1-06's was.
- The manager AI pilot is a separate build. When both exist, a series
  game loads the same way and the managers behave per that pilot's
  governing state; neither spec assumes the other.

## 4. Validation

**"Arithmetically valid", defined once for all of section 4**: a file
passes the importer's own validation (check_shape in
scripts/import_game.py) with no problems — all of the following: the
game is not tied; batting rows exist, and both clubs have batting
rows; each club's batting R sum equals its linescore R; each club's
pitching R sum equals the opponent's linescore R; total batting H
equals total pitching H; total batting SO equals total pitching SO;
each club's batting H sum equals its linescore H column; the W and L
decisions are both present; and no parse problems (the linescore
carries R and E columns and resolvable club names, and every named
club section has its table).

### 4.1 Assembly proof (no app build needed)

Run the generator logic against its two real inputs — the book
(tournament_results.json) PLUS the fixture file
(data/playable_r106.json) — and confirm the Game 3 assembly equals
every value derived below from the lines the book stores. The
derivation for Game 3 reads ONLY Game 2 (the N-1 rule); the Game 1
column is listed to prove the one-game duration.

Game 2's stored pitching lines (outs): MON — Pedro Martinez 24,
Wetteland 3. CHC — Brown 18, Strop 2, Sutter 4, Smith 3.
Game 1's stored pitching lines (outs): MON — Rogers 19, Burke 5.
CHC — Jenkins 19, Wood 6, Sutter 2.

Expected availability picture for Game 3 — every arm that appeared in
Games 1-2. Only Game 2's appearances produce rows in the generated
file's `availability` arrays; a pitcher who did not appear in Game 2
has NO row and is implicitly free:

| Pitcher | Club | Game 1 outs | Game 2 outs | Game 3 derivation |
|---|---|---|---|---|
| Pedro Martinez | MON | did not appear | 24 | row: unavailable (Game 2 outs ≥ 9) |
| John Wetteland | MON | did not appear | 3 | row: free |
| Mordecai Brown | CHC | did not appear | 18 | row: unavailable (Game 2 outs ≥ 9) |
| Pedro Strop | CHC | did not appear | 2 | row: free |
| Bruce Sutter | CHC | 2 | 4 | row: free (the Game 2 row governs) |
| Lee Smith | CHC | did not appear | 3 | row: free |
| Steve Rogers | MON | 19 | did not appear | no row — implicitly free (his Game 1 unavailability governed Game 2 only) |
| Tim Burke | MON | 5 | did not appear | no row — implicitly free |
| Fergie Jenkins | CHC | 19 | did not appear | no row — implicitly free (his Game 1 unavailability governed Game 2 only) |
| Kerry Wood | CHC | 6 | did not appear | no row — implicitly free (his Game 1 cap governed Game 2 only) |

**Pinned row counts.** The generated file's `availability` arrays for
the Game 3 load contain exactly 6 rows: CHC 4 (Brown, Strop, Sutter,
Smith, in Game 2 appearance order) and MON 2 (Pedro Martinez,
Wetteland). The arrays for the Game 2 load contain exactly 5 rows:
CHC 3 (Jenkins unavailable, Wood capped at 3, Sutter free) and MON 2
(Rogers unavailable, Burke free). The cross-check against the
set-home records is pinned to those arrays: the availability section
of PP_R1_06_G1_OFFICIAL_seed229154.md lists exactly 5 rows and that of
PP_R1_06_G2_OFFICIAL.md exactly 6, and each load's arrays must agree
with the corresponding record row for row — name, prev_outs, status,
and cap. Any disagreement fails the proof and is reported to Joe; it
is never edited into agreement.

Expected next_game in full: number 3; id "R1-06-G3"; home MON, away
CHC; park "Stade Olympique"; the series file's top-level fields read
status "in-progress", `wins` {"CHC": 1, "MON": 1}; `proposed_starters`
CHC Rick Reuschel, MON Dennis Martinez (chair 3 for both clubs,
following the Game 2 starters Brown and Pedro Martinez at chair 2;
both proposals free); `starter_blocked` empty; `availability` rows as
pinned above; and the copied structures verbatim from the fixture
file and the book:

- `lineups` — CHC: [Ryne Sandberg 2B, Mark Grace 1B, Ron Santo 3B,
  Sammy Sosa RF, Billy Williams LF, Ernie Banks SS, Hack Wilson DH,
  Gabby Hartnett C, Pete Crow-Armstrong CF]; MON: [Tim Raines LF,
  Jose Vidro 2B, Larry Walker RF, Vladimir Guerrero DH, Gary Carter
  C, Andre Dawson CF, Ron Fairly 1B, Tim Wallach 3B, Orlando Cabrera
  SS].
- `benches` — CHC: [Johnny Kling, Billy Herman, Andre Dawson, Joe
  Tinker, Stan Hack, Anthony Rizzo]; MON: [Brian Schneider, Mike
  Lansing, Marquis Grissom, Chris Speier, Rusty Staub, Moises Alou].
- `pens` — CHC: [Hippo Vaughn, Sean Marshall, Pedro Strop, Kerry
  Wood, Lee Smith, Bruce Sutter]; MON: [Andy McGaffigan, Woodie
  Fryman, Mel Rojas, Tim Burke, Jeff Reardon, John Wetteland] — the
  fixture's pen arrays unchanged, because neither unavailable arm is
  a pen member.
- `rotation` — CHC: [Fergie Jenkins, Mordecai Brown, Rick Reuschel,
  Pete Alexander, Carlos Zambrano]; MON: [Steve Rogers, Pedro
  Martinez, Dennis Martinez, Bryn Smith, Javier Vazquez].
- `stored_games` — [{number 1, id "R1-06-G1", away "MON", home
  "CHC"}, {number 2, id "R1-06-G2", away "MON", home "CHC"}].

**Selectable-staff assertion.** The selectable staffs constructed
from this file (section 3.2) contain neither Mordecai Brown nor Pedro
Martinez in any role for Game 3: neither is a proposed starter,
neither appears in `pens`, and each name occurs in the file only in
`rotation` (display-only) and in his own availability row (status
unavailable).

Cross-check: the same derivation for Game 2 from Game 1's lines must
produce the 5-row table pinned above — and both games' arrays must
agree row for row with the availability sections recorded in
PP_R1_06_G1_OFFICIAL_seed229154.md and PP_R1_06_G2_OFFICIAL.md in the
Cubs set home.

### 4.2 Booking proof (the format rehearsal)

In a scratch clone of the repo at origin/main, write a test Game 3
file in the exact format of section 3.4 with these pinned results:
heading `# R1-06 Game 3: Chicago Cubs at Montreal Expos`; seed
20261503; Montreal wins 4-2; pitching lines — MON: Dennis Martinez
IP "7.0" (21 outs), John Wetteland "2.0" (6 outs); CHC: Rick
Reuschel "5.0" (15 outs), Bruce Sutter "2.0" (6 outs), Lee Smith
"1.0" (3 outs); decisions W: Dennis Martinez (Montreal Expos),
L: Rick Reuschel (Chicago Cubs), SV: John Wetteland (Montreal
Expos); batting tables constructed to be arithmetically valid per
section 4's definition, with club R sums of 2 (CHC) and 4 (MON).
Run `scripts/import_game.py imports/R1-06-G3.md --apply` in the
clone with the pipeline venv python. Expected:

a. Exit 0; the output contains "applied 1 game(s)" and ends with
   "archive matches the validator".
b. The series entry (parsed JSON): games ["R1-06-G1", "R1-06-G2",
   "R1-06-G3"]; wins {"CHC": 1, "MON": 2}; status "in-progress". The
   stored Game 3 summary: away CHC, home MON, winner MON, score
   CHC 2, MON 4, seed 20261503.
c. Club game records: CHC game_wins 1, game_losses 2; MON
   game_wins 2, game_losses 1.
d. The regenerated data/series_r106.json offers Game 4: number 4,
   home MON (home_by_game "4"), park "Stade Olympique"; Game 4
   availability derived from the test game's lines — Dennis
   Martinez 21 outs → unavailable; Reuschel 15 → unavailable;
   Wetteland 6 → capped at 3; Sutter 6 → capped at 3; Smith 3 →
   free; proposed starters: CHC Pete Alexander, MON Bryn Smith
   (chair 4 for both, following the test game's chair-3 starters;
   both free).
e. Games 1 and 2 unchanged, proven by the one comparison method used
   everywhere in this spec: parse tournament_results.json in the
   clone and in the untouched real repo, locate each of R1-06-G1
   and R1-06-G2's stored summary records in the games collection,
   and compare the two parsed objects field by field; they must be
   equal. (Byte comparison is not the method: key order and
   formatting are not meaning.)

### 4.3 Duplicate law, and the slot and flag procedure

**Duplicate law at the importer**, proven in the section 4.2 clone
immediately after its booking:

a. Re-run the identical command on the identical file
   (`scripts/import_game.py imports/R1-06-G3.md --apply`). The
   importer's actual behavior on an unchanged duplicate: it parses
   the file, finds the game id already stored, compares the file
   against the stored record field by field, finds no difference,
   adds nothing, and succeeds — expected exit 0, output with NO
   "applied" line, ending "archive matches the validator", and a
   parsed comparison of the clone's tournament_results.json before
   and after the re-run showing zero differences anywhere (stored
   summaries, series entries, club records). An unchanged duplicate
   is a successful no-op, never a second counting.
b. Copy the file, change exactly one compared field in a way that
   keeps the file arithmetically valid (one batter's SB from 0 to
   1 — SB enters none of the sums the importer checks), and run
   --apply on the copy. Expected: exit 1; output beginning "import
   failed:" and listing the comparison difference for that batting
   line; the clone's tournament_results.json unchanged from before
   this run (parsed comparison). A changed duplicate is refused
   outright — never merged, never partially applied.

**Slot and flag procedure** (the section 3.3 seal rules, executed
against the two testable operations of section 3.3). Environment:
Node, headless, loading js/play.js the way scripts/batteries.mjs
loads it (its exported createGame, peekSave, loadSave, discardSave,
SAVE_PREFIX, and the two operations this build adds to that exported
surface: dispatchSeriesGame and applySeriesFile), with the battery
harness's in-memory storage standing in for localStorage and the
harness's clock fixed at 2026-10-29 (so `dispatched_on` is pinned).
The series file is supplied from disk: the pre-booking file (the
current repo's series file, Game 3 next) and the section 4.2 clone's
regenerated file (Game 3 stored, Game 4 next). Steps:

1. Call `applySeriesFile(pre-booking file, empty storage)`: expect
   `{kind: "play", number: 3, id: "R1-06-G3"}`. Create the series
   game for R1-06-G3 through the play screen's game creation and play
   one plate appearance. Assert storage holds the key
   `pp-play-r106-R1-06-G3` and peekSave returns gameId "R1-06-G3",
   unfinished.
2. Complete the game with the battery harness's scripted-play
   mechanism (the same mechanism the batteries use to finish games
   headlessly) and run the seal: call
   `dispatchSeriesGame(finished state)`. Assert the result is
   `{fileName: "R1-06-G3.md", content: <text>}` whose content's first
   line is `# R1-06 Game 3: Chicago Cubs at Montreal Expos` and whose
   full text parses with no problems under the importer's parse in
   the clone. Assert storage now also holds
   `pp-series-dispatched-R1-06-G3` whose parsed value equals exactly
   `{"game_id": "R1-06-G3", "dispatched_on": "2026-10-29",
   "file_name": "R1-06-G3.md"}`; and `pp-play-r106-R1-06-G3` is STILL
   present — the slot is retained, not cleared, exactly as section
   3.3 states.
3. Call `applySeriesFile(pre-booking file, storage)`: expect
   `{kind: "awaiting", number: 3, id: "R1-06-G3"}`; the offered
   actions are reopen and dismiss; no fresh start is offered.
4. Call `applySeriesFile(section 4.2 regenerated file, storage)` (the
   landed case): expect `{kind: "play", number: 4, id:
   "R1-06-G4"}`; the flag key is gone and the autosave key is gone —
   `applySeriesFile` performed the landed clearing.
5. Reset to the end state of step 2 and invoke the play screen's
   dismiss action (the manual-clear case): flag key gone, autosave
   key gone; then call `applySeriesFile(pre-booking file, storage)`:
   expect `{kind: "play", number: 3, id: "R1-06-G3"}` — Game 3 offered
   as a fresh start.

### 4.4 Clinch case

Continue in the section 4.2 clone. Write test files for Games 4 and
5 in the section 3.4 format, arithmetically valid per section 4's
definition, Montreal winning both (any valid lines), and apply each
in turn with the same command. Expected after Game 4: exit 0 with
"applied 1 game(s)"; wins {"CHC": 1, "MON": 3}; status
"in-progress"; the regenerated series file offers Game 5, home CHC
(home_by_game "5"), park "Wrigley Field". Expected after Game 5:
Montreal reaches 4 wins: the series entry reads status
"complete", winner "MON", loser "CHC"; the club series records read
MON series_wins 1 with bracket "winners", CHC series_losses 1 with
bracket "losers" and eliminated false — exactly the recompute_teams
rule of section 3.5 (a first series loss drops a club to the losers
side; it is not eliminated); the regenerated series file reads
status "complete", `next_game` null, `blocked_reason` "complete"
(the generator's decision order, step 2); by the button rule
(section 3.1) no Play button renders on either page; and Games 6 and
7 are never offered — their fate is that they cease to exist as
offers the moment the fourth win books. Scope note, stated plainly:
the clinch is enforced by this feature's flow (no assembly and no
button past "complete"); the importer itself applies no clinch
check, so a Game 6 file pushed by hand outside this feature would
still book at the importer level. Such a booking is outside the
feature and would surface as a book anomaly for Joe — the feature
never creates one.

### 4.5 The four standing gates, defined

The build keeps all four standing gates green; each is defined by
its command, its pass criterion, and where it runs:

1. **Replay gate**: `node scripts/replay_driver.mjs` in the repo.
   Pass: both recorded replays reproduce every recorded plate
   appearance with zero divergence (Replay A 80 of 80 PAs, Replay B
   50 of 50, per PLAYABLE_MODE_SPEC section 11.1). Runs in the
   build's local verification before any push.
2. **Cardview parity**: `scripts/check_cardview_parity.py` exits 0
   (the two card renderers agree on section order and labels). Runs
   in the build's local verification.
3. **Playable batteries**: `node scripts/batteries.mjs` finishes
   with zero failed checks (154 checks at the last ship; the count
   may grow, the criterion is zero failures). This build adds cases
   to it: the section 3.2 cap case at exact reach (a capped pitcher
   reaching his cap mid-game forces the pitching change at the
   plate-appearance boundary), the cap overshoot case (a capped
   pitcher standing at 2 outs records a double play and arrives at
   the next boundary at 4 outs; the forced change fires at that
   boundary — the ≥ rule of section 3.2), and the section 4.3
   slot-and-flag assertions, run through the same harness. Runs in
   the build's local verification.
4. **Validator and tournament fingerprint**:
   `~/workspace/tools/pp-t32-venv/bin/python
   scripts/validate_results.py` exits 0 in the repo. Its locked-game
   fingerprint check, stated exactly: the FINGERPRINT constant in
   scripts/validate_results.py is a digest over ONLY the 16 games in
   its LOCKED_GAME_IDS (R1-01 Games 1-4, R1-02 Games 1-5, R1-03
   Games 1-7) — for each, the archive summary's score, winner, home,
   away, seed, linescore, batting lines (restricted to the
   validator's BATTING_FIELDS), pitching lines (its PITCHING_FIELDS),
   decisions (wls), and team errors, plus the per-game detail file's
   rolls and manager_log; the validator's EXPECTED_TOTALS accumulate
   over the same locked games only. The fingerprint covers nothing
   else: not any unlocked game (the games of R1-04, R1-05, and R1-06
   are all outside it — which is why the R1-06 Games 1 and 2 bookings
   of 2026-10-29 passed the validator with the constant untouched),
   not series entries (the frozen three are hashed separately), and
   not team records (reconciled by recomputation elsewhere in the
   validator). The pass criterion for this build is therefore the
   true one: the build changes no locked game, no locked detail
   file, and nothing the fingerprint reads, so the digest still
   equals the constant exactly as before the build. No code path
   re-locks the fingerprint; the constant has only ever moved by a
   manual edit under one of Joe's dated correction rulings, with the
   old value and the reason recorded in the validator's header
   comments, and this build neither needs nor performs one. Runs in
   the build's local verification, inside every import
   (import_game.py runs the validator on apply), and in the pages
   workflow's check job on every push.

### 4.6 Pinned edge cases

Each case below is executable as written, against scratch copies of
the generator's inputs (the generator invoked on the copies, the
produced series file the assertion target), the section 4.2 clone, or
the section 4.3 harness, as stated. No case is left unproven or
deferred.

a. **Stored-number gap (decision order step 1).** Copy
   tournament_results.json; in the copy, remove R1-06-G2's summary
   from the games collection and add a fabricated G3 summary (a copy
   of G2's summary with id "R1-06-G3" and game_in_series 3), setting
   the series' games list to ["R1-06-G1", "R1-06-G3"]. Run the
   generator on the copy with the real fixture file. Expected:
   `next_game` null, `blocked_reason` "gap", and the generator's
   output names the missing number 2. (The fabricated summary's
   contents are irrelevant: the gap check precedes every other step
   of the decision order.)
b. **Playable data incomplete (decision order step 3).** In a scratch
   copy of the repo, delete assets/parks/stade-olympique.webp and run
   the generator. Expected: `playable_data_complete` false,
   `next_game` null, `blocked_reason`
   "not-playable-data-complete" (the series is in-progress with a
   dense prefix, so steps 1 and 2 pass and step 3 is the one that
   fires); `applySeriesFile` on the produced file returns kind "none"
   with that blocked reason; no button renders.
c. **Starter blocked.** Copy the book; in the copy's stored Game 2
   summary, append fabricated Montreal pitching lines — Steve Rogers
   6 outs, Dennis Martinez 9 outs, Bryn Smith 7 outs, Javier Vazquez
   12 outs, appearance_order continuing that game's sequence — so all
   five Montreal chairs are capped or unavailable for Game 3 (Pedro
   Martinez's real 24 outs stand). Run the generator. Expected:
   `proposed_starters` CHC "Rick Reuschel", MON null;
   `starter_blocked` ["MON"]; `blocked_reason` null (the game is
   still assembled; the block is per-club). In the section 4.3
   harness, applying this file and attempting the load shows the
   section 3.2 hold notice naming Montreal instead of a startable
   game.
d. **Aggregation fallback.** Copy the book; in the copy's Game 2
   summary, split Pedro Martinez's pitching line into two lines for
   the same club and name (20 outs and 4 outs, appearance_order 1 and
   5). Run the generator. Expected: Montreal's `availability` array
   still holds exactly 2 rows, and Pedro Martinez's row reads
   prev_outs 24, status unavailable — the fallback summed the two
   lines into one appearance before any rule applied.
e. **Emergency-starter pointer fallback.** In a fresh scratch clone
   (section 4.2's form), apply a variant of section 4.2's Game 3
   file, identical except that Chicago's starter is Bruce Sutter (IP
   "5.0", 15 outs) and Rick Reuschel does not appear for Chicago, the
   tables adjusted to stay arithmetically valid. Expected: exit 0;
   the regenerated series file's Game 4 `proposed_starters`: CHC
   "Rick Reuschel" — the pointer follows the last booked CHAIR
   starter (Brown, Game 2, chair 2) to chair 3, because Sutter's
   emergency start is not a chair start, and Reuschel is free (no
   Game 3 appearance) — and MON "Bryn Smith", as in section 4.2(d);
   Game 4's CHC availability includes Sutter (prev_outs 15,
   unavailable) and the Game 4 `pens` omit him.
f. **Starter-override rejections** (section 4.3 harness, through the
   load screen's starter-override control — the same handler the
   override button calls). (i) Load Game 3 (the real assembly) and
   invoke the override for Chicago with Mordecai Brown. Expected:
   refused, the refusal naming his status (unavailable), the proposed
   starter unchanged (Rick Reuschel). (ii) Generate the Game 2 series
   file from a book copy truncated to Game 1 only, load Game 2, and
   invoke the override for Chicago with Kerry Wood. Expected:
   refused, naming his status (capped — the strict default of section
   3.2, assembly item 4), proposed starter unchanged (Mordecai
   Brown).
g. **Stale mid-game slot discard.** In the section 4.3 harness,
   create the R1-06-G3 series game from the pre-booking series file
   and play one plate appearance — slot present, no dispatch, no
   flag. Then call `applySeriesFile` with section 4.2's regenerated
   file (Game 3 stored). Expected: the slot key
   `pp-play-r106-R1-06-G3` is gone (discarded as stale, section 3.6),
   no flag existed or was created, and the result is `{kind: "play",
   number: 4, id: "R1-06-G4"}`.

## 5. Gate

Implementation starts only after (a) a fresh cold review of this v4
returns READY, and (b) Joe approves the spec or directs changes.
Open for Joe, carried from earlier drafts: the capped-arm-as-starter
question (section 3.2, assembly item 4 — the strict default stands
until he rules) and the first real booking's route (Route A
supervised, as every booking to date; the inbox route graduates only
per OFFLINE_IMPORT_SPEC.md section 3, "Route B, the inbox route
(graduates later)": one clean supervised Route A landing — every
verification criterion passed, no rollback, no manual repair —
unlocks the inbox route's first landing, itself supervised, and only
a clean supervised Route B landing makes the inbox route the
unattended default — this spec names both routes' mechanics either
way).

## 6. Glossary

- **The book**: tournament_results.json in the pp-t32-site repo — the
  master archive of series, games, and club records, with one detail
  file per game under games/. Authoritative for everything this
  feature derives.
- **Staged lineups**: the preset batting orders shipped in the
  fixture file's `lineups`; Joe's lineups, loaded as-is.
- **Baked**: generated into a committed data file at build or booking
  time, as opposed to computed in the browser at runtime.
- **Playable data**: the repo artifacts of section 3.1 whose presence
  and shape the generator's `playable_data_complete` verdict records
  — exactly the checks of section 3.2's completeness rule, no more.
- **Offered state**: the result of `applySeriesFile` (section 3.3) —
  "play", "awaiting", or "none" — from which the bracket button, the
  series-page button, and the play screen's entry all render.
- **Series signal**: the `series` query parameter in the play route's
  hash (`#/play?series=R1-06`) that puts the play screen into series
  mode for the named series (section 3.1).
- **Set home**: a club's own directory (~/workspace/payoff-pitch-
  <club>/, or a shared home for paired clubs) holding its converted
  card set, its engine stack, and its official game records — e.g.
  the Cubs set home, which holds PP_R1_06_G2_OFFICIAL.md.
- **Governed stack**: a set home's engine installation (engine,
  fatigue-fix layer, manager governance) that plays governed games
  for that club. This feature's generator never imports one; it is
  named only to mark that boundary.
- **FAC deck**: the 256 Fast Action Cards the play screen draws as
  its dice surface; the deck's data ships inside the fixture file and
  its printed faces under assets/fac/.
- **Chair**: one slot in a club's rotation order — chair 1 is the
  first name in the fixture's `rotations` array for that club.
- **Dispatched flag**: the localStorage marker of section 3.3,
  recording that a finished game's file has been dispatched for
  booking but not yet seen landed.
- **Dense prefix**: the stored game numbers of a series forming
  1..k with no gaps (section 3.2).
- **Rehearsal**: a full import run against a throwaway clone of the
  repo (section 4.2's form), proving a file lands cleanly before the
  same file is applied to the real book.
- **Pages workflow**: .github/workflows/pages.yml, named "Tournament
  site": on every push to main its check job validates the archive,
  rebuilds the generated files, and fails unless the committed files
  match the rebuild (`git diff --exit-code`); only then does it
  deploy the site.
