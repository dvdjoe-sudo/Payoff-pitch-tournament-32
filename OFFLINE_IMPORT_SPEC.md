# Offline Box-Score Import — Spec

Status: READY. Passed the cold review on round 6, 2026-10-29 (zero
blockers; the round's three major findings are folded into this v7
text). Rounds 1 to 5 each returned NOT READY on one blocker: the
proof never exercised the primary route; the apply step's mechanics
were unspecified; the completeness threshold could not fill the
required tables; the inbox route's rollback re-triggered the import;
the duplicate-send guarantee was undelivered. Owner: the workshop
chat (this project's build and testing conversation).
Joe's ask (2026-10-29): "setup app so can import and give you box score and
add to app and tourment bracket ... so if play game offline."

The actors: Joe is the player at the table and the sole ruling
authority for the tournament. Cooper is the operator who executes
every step below.

Terms used below. A game's `rolls` are the per-plate-appearance dice and
FAC record an engine-played game produces (FAC: the 256-card Fast Action
Card deck the engines draw from). The `manager_log` is the engine's record
of managerial decisions in that game. "Frozen" series (R1-01, R1-02, R1-03)
are locked against edits. "Peak 162" is a generated per-player data file
the app displays. The "fingerprint" is the validator's hash over stored
game results. The app's `#/add` form derives a shortened player id from
the player's name (first letters plus "01") because it cannot know the
real ids; those shortened ids are never valid at merge time. A "fixture"
is one scheduled series pairing in the bracket (for example R1-06,
Cubs vs Expos). "Leaders" are the app's generated leaderboards, and a
"series preview" is the generated matchup data for an upcoming series.
The "pages workflow" is `.github/workflows/pages.yml`, the workflow
that checks and deploys the site on pushes to main.

## 1. Purpose

Joe plays a Payoff Pitch game offline, at the physical table, away from the
app and the engines. He hands Cooper the box score. The game lands in the
app and the bracket the same way an engine-played game does;
section 4 states where its record is thinner, and the record is
honestly labeled as a box-score record of a table game.

An imported box score is taken on Joe's word that the game was played with
the tournament rosters and rules (universal DH, pitcher availability, the
hook and closer conventions of his table). No mechanical verification of
that is possible from a box score, and none is attempted. Joe is the
league office for his own table.

## 2. What already exists (verified 2026-10-29, repo at f81f4dc)

- `scripts/import_game.py` accepts a GameChanger / Game Pulse CSV, a
  markdown box score, or a whole-series markdown file. Preview writes to
  `imports/` (gitignored) and touches nothing. `--apply` adds games not
  already stored, refuses a changed line for a stored game, refuses edits
  to frozen series R1-01, R1-02, R1-03, updates series wins and club
  records, runs `scripts/validate_results.py`, and regenerates leaders,
  rosters, and the rest of the generated set the site workflow checks
  (the site's feed files, its odds page data, its per-series share
  pages, and its graphics, bracket image included).
- `scripts/import_inbox.py` applies every box score in `inbox/` through
  the same importer; `.github/workflows/inbox.yml` runs it in CI on a
  push of `inbox/*.md` or `inbox/*.csv` to main, commits the result, and
  deploys the site. Failures stay in `inbox/` with the reason committed
  to `inbox/errors/<name>.txt`; successes move to `inbox/imported/`. The
  import also rebuilds Peak 162, series previews, and the bracket image.
- The inbox has never been used: `inbox/imported/` and `inbox/errors/`
  are empty. The CI pipeline is built but unproven end to end, and its
  deploy job deploys the checked-out ref, so it cannot be rehearsed on
  a scratch branch without risking a deploy of test content to the live
  site. Section 6 therefore makes the local route the primary route
  until the CI route has been proven by one supervised real landing.
- `#/add` in the app: a form that checks a box score (rejects ties,
  linescore/batting/pitching run mismatches) and downloads two JSON
  files in the archive shape. The form does not write the repository.
- `ADDING_GAMES.md` governs the markdown box-score layout the conversion
  targets; `SCHEMA.md` governs the archive shape. If the two ever
  disagree about an imported game's fields, SCHEMA.md wins for what is
  stored and ADDING_GAMES.md wins for the file Joe's box score becomes.
- The required markdown shape, in brief: a heading
  `# R1-NN Game N: Away at Home`; a linescore table (Team, innings, R,
  H, E; `x` when the home club did not bat); a decisions line (W, L, SV
  with the club in parentheses); `## Club batting` and `## Club pitching`
  tables. Batting columns: #, Player, AB, R, H, 2B, 3B, HR, RBI, BB, SO,
  HBP, SB, CS, SAC, GIDP (a `*` on the name marks a substitute). Pitching
  columns: Player, IP, H, R, ER, BB, SO, HR, HB, BF (batters faced).
  Optional lines:
  Date, Seed, Game recap, Series state after this game.
- Two archive copies exist. The repo's `tournament_results.json`
  (schema 1, summaries in the file, rolls and manager logs in
  `games/<id>.json`) is the archive the importer writes and the app is
  generated from; it holds all 26 games played so far and is canonical
  for the tournament book. The older monolith at
  `~/workspace/apba-card-builder/all_time_rosters/apba_games/tournament_results.json`
  is the recorder-era master, kept current by the mirror step in
  section 3 (the mapping and the series entries' identical shapes
  were verified firsthand against both files on 2026-10-29). The
  restoreResultsFromArchive route named in old notes was
  the recorder-era app-sync mechanism; this flow does not use it. The
  canonical claim is about what the app reads. How engine-played and
  co-managed games are recorded is outside this spec; this flow's
  mirror duty covers imported games only.

## 3. The flow

Every check and determination in this section runs against the
current archive: Route A's sync step (step 0 below) happens before
the conversion checks, and on Route B the CI checks out main fresh
by construction.

Linescore shapes. The linescore table carries one column per inning
played: extra-inning games simply have more columns, and shortened
or called games fewer; the parser reads the columns present. A table
game that ends in a tie is unimportable, because the bracket needs a
winner: it is held and reported, never imported, and Joe decides
whether it is replayed at the table.

Intake. Joe gives Cooper the box score by any of these routes:
  a. a photo of his paper scorecard sent in chat;
  b. the typed box score in chat, in any reasonable layout;
  c. the two JSON files downloaded from the app's `#/add` form. These
     are converted field by field into the same markdown target as the
     other routes (the importer takes CSV or markdown, not JSON), with
     the form's shortened player ids replaced during name resolution.

Completeness threshold. A submittable box score carries: the
linescore by inning with team R, H, and E, a batting line for every
player the scorecard lists (at minimum AB, R, H, RBI), a pitching
line for every pitcher the scorecard lists (IP, H, R, ER, BB, SO),
and the decisions. If the scorecard lacks the inning-by-inning
linescore, the team H or E, or the per-player lines, the import
holds and Cooper tells Joe exactly what is missing. There are no
partial records and no reconstructed lines. A score-only result can
be talked about in chat but is not imported.

Columns. The linescore always carries its full shape (Team, innings,
R, H, E); the threshold above makes that a condition of importing at
all. For the batting and pitching tables, the converter writes each
table with exactly the columns Joe's box score carries: every column
the scorecard has is written, and no column it lacks is written. One
standing example: strikeouts. The importer requires the batting and
pitching strikeout totals to agree, so if a scorecard records
strikeouts on one side only, the other side's SO column is a
completeness gap under the threshold: the import holds and Cooper
names it, rather than dropping the side that was recorded. The importer's parser
reads whatever columns a table presents, so a thinner table is a
valid table; the stored record then simply has no values for the
absent stats, which is the truth of that scorecard. The converter
never zero-fills a missing column and never drops one the scorecard
has. The threshold minimums above are the floor for a table to be
written at all. If the validator rejects a record for a field the
scorecard does not carry, the import holds under the same rule: the
missing item is named to Joe, never supplied by Cooper.

Conversion and checks. Cooper converts what arrived into the markdown
shape above and cross-checks it before anything is applied: linescore
sums to the final score, batting runs match the linescore per club,
pitching runs allowed match the opponent's score, no tie, and the
decisions check out exactly: the winning pitcher is on the winning
club, the losing pitcher is on the losing club, and a save, when
credited, belongs to the winning club and is not the winning
pitcher. The decision pitchers named in the decisions line pass
through the same name resolution as every other name and must appear
in the pitching lines. A table game has no seed: no Seed line is
written for one, and the seed fields in both archives stay empty for
imported games. The fixture is checked too:
the series id must name a scheduled fixture in the archive, the
heading's away and home clubs must be that fixture's clubs, and the
home club must match the home club the series entry records for the
assigned game number (each series entry carries its home pattern
and the home club for every game), and the game takes that series'
next unplayed number (see Identity and dating). A box score that is internally consistent but
belongs to a different fixture fails here and lands nowhere. Any
discrepancy goes back to Joe as a question, never a silent fix.

Duplicate test. A game number is assigned only after the converted
box score has been compared against every game already stored in
that series. If a stored game in the series has the same two clubs,
the same final score, and the same linescore, and the played dates
(when both are known) also match, the box score is a duplicate: the
import refuses it, Cooper reports that the game is already on the
book, and nothing is assigned or applied. Joe can overrule the
presumption by confirming the box score is a distinct game (two
games in a series can share a score); his confirmation is noted in
the game recap and the import proceeds. A box score matching a
stored game on clubs and score but differing in its lines is not a
duplicate but a changed line, and is refused under section 5. A box
score sent for a fixture whose feeding round has not completed, so
the series entry has no clubs yet, fails the fixture check safe: it
lands nowhere, and Cooper reports that the series is not formed yet
and holds the box score.

Name resolution. Every player name resolves to the real (team,
player_id), in this source order: (1) the player's existing stat lines
for that club in the archive; (2) the club's roster and card data
(`data/rosters.json`, `data/cards.json`). An unresolved or ambiguous
name stops the import and is reported to Joe; ids are never guessed. A
name that resolves cleanly to a player who is NOT on that club's 26 for
the fixture also stops the import: Joe rules whether his table roster
differed (the import then proceeds, with his ruling noted in the game
recap) or the name was misread.

Identity and dating. A game is identified by (series id, game number).
Game numbers follow PLAY order, not receipt order: Joe states the
order, or the scorecard dates settle it, and each game takes the next
unplayed number in that series in play order. When Joe sends several
at once, Cooper confirms the order with him before applying any of
them. If an earlier-played game's scorecard arrives after a
later-played game in the same series is already stored, the numbers
are wrong until fixed; the fix is a renumbering correction under
section 5 (Joe's ruling, executed across that series' imported games
before the series completes; once a series is complete and its
summary published, the numbers stand and the played dates on the
records carry the true order). Renumbering never touches an
engine-played or co-managed game: if a late table game was played
before a stored engine game in the same series, the table game takes
the next unplayed number instead, and its played date and recap line
carry the true order. The game's date is the date Joe played
it (from the scorecard or his word; if unknown, Cooper asks). The
import date appears only in the provenance line, never as the game
date.

Route A, the primary route (local), specified step by step. The
markdown file is staged in the repo's gitignored `imports/` area and
is never placed in `inbox/` under this route. (0) Sync: Cooper first
brings the repo checkout current with origin/main and stops if the
tree is dirty or behind; every determination below (next unplayed
number, already-stored, fixture state) is computed against the
current archive, never a stale local copy. (1) Rehearsal: Cooper
runs `scripts/import_game.py <file> --apply` in a scratch clone of
the repo and inspects the regenerated leaders, series preview,
bracket image, and club records before the real archive is touched,
and confirms every stored player_id in the rehearsed game is an
archive or roster id, never a fresh name slug (the importer's player
index consults stored lines first, then `data/rosters.json`, and the
slug is only a last resort for a player neither knows, which the
name-resolution step exists to catch first).
This per-import rehearsal is distinct from the one-time pipeline
proof in section 6: the proof uses a fictional game and establishes
the pipeline; the rehearsal uses the real game and establishes this
import.
(2) Apply: the same command, `scripts/import_game.py <file> --apply`,
runs in the real repo checkout. Because the file never sits in
`inbox/`, the resulting commit contains only archive and generated
files, no `inbox/*.md` or `inbox/*.csv`, so the push cannot trigger
`inbox.yml`; the double-processing hazard does not arise on this
route. A failed apply never becomes a commit: the importer itself
restores the archive when it refuses a game, and for any other
failure or any unexpected diff, Cooper restores the checkout from
git (tracked files restored, generated untracked files cleaned),
reports the failure, and stops. Nothing is committed or pushed
until the local diff has been inspected and matches the expected
deltas. (3) Push: the commit goes to main and deploys through the
pages workflow, as every app change does. (4) Verification: Cooper
verifies the landing against the "Verification of a landing"
criteria below, with the rollback ready. (5) Mirror: Cooper copies
the landed game into the apba_games monolith. The mapping is exact,
from the two files' current shapes: the repo game summary and the
monolith game object share every field except that the summary
carries `detail` (the path to its `games/<id>.json`) and `rng_seed`,
while the monolith carries `rolls` and `manager_log` inline and
names the seed `seed`. The mirror therefore takes the summary,
drops `detail` and `rng_seed`, sets `seed` to the `rng_seed` value,
and sets `rolls` and `manager_log` from the game's detail file
(empty list and null for an imported game). The two files' series
entries have identical shapes, so the series' wins, status, and game
list and the club records are updated to the same values the
importer computed for the repo file. Verification reloads both files
and compares all of it: the full game summary (score, linescore,
batting and pitching totals, decisions), the series entry (wins,
status, game list), and the two clubs' records. If the mirror write
or its comparison fails, Cooper recomputes the mirror from the repo
record (the repo governs, so the mirror is always recomputable) and
verifies again; only a second failure is flagged to Joe as drift,
as an open item with the repo copy governing in the meantime.

Route B, the inbox route (graduates later). After one clean Route A
landing with Joe watching (clean means: the verification criteria
below all passed, with no rollback and no manual repair), the inbox
route may be used, and its FIRST landing also runs with Joe present
in chat, because that route has never run end to end. Only after a
clean supervised Route B landing does it become the unattended
default: push the verified markdown to `inbox/` on main and let
`inbox.yml` import, commit, and deploy. Route A remains the fallback. CI counts as unavailable for
Route B when the inbox run fails, when no run has started within 15
minutes of the push, or when Actions is visibly down. Before using the
Route A fallback on a game already pushed to `inbox/`, Cooper first
confirms the CI run has concluded or removes the file from `inbox/`,
so the game cannot be processed twice; the importer's refusal of an
already-stored game is the backstop, and any inbox file left behind by
a fallback is removed in the same push that lands the game.

Rollback. Verification (below) happens after deploy, so it is backed
by a standing rollback. On Route A the import commit contains no
inbox file, so a plain git revert of it is safe: Cooper reverts,
confirms the prior state redeploys, and only then reports. On Route B
a plain revert is FORBIDDEN: the CI import commit also moved the box
score from `inbox/` to `inbox/imported/`, so reverting it would put
the file back in `inbox/`, and the revert push itself would trigger
`inbox.yml` to re-import the game the rollback just removed. The
Route B rollback is a single new forward commit that (a) restores
`tournament_results.json` and the generated files to their
pre-import state and (b) deletes the box-score file from
`inbox/imported/` in the same commit. It adds no file under `inbox/`,
so it cannot re-trigger the import, and the pages workflow redeploys
the corrected state. Either way, a rollback also restores the
mirror: if the mirror step had already run for the rolled-back game,
the monolith is restored for that game and its series and club
entries in the same rollback, and the mirror comparison is re-run,
so a rolled-back game never lingers in the second archive.
Rolling back a botched landing is Cooper's
standing authority under this spec. It is not the correction path in
section 5, which governs changing data that landed correctly.

Verification of a landing. Before applying, Cooper computes the
expected deltas from the checked box score: the winner's series wins
increase by one, the two clubs' win/loss records move by one game
each, and the series state (in progress, or complete with its
winner) follows. After the push: on Route A, the pages workflow run
for the landing commit concluded SUCCESS (Route A has no import CI
run; its import already ran locally); on Route B, the inbox workflow
run concluded SUCCESS and the file moved to `inbox/imported/`. The
live check is mechanical: Cooper fetches the live series page and
the served results data from the site and compares the game's score
and lines, and the series wins and club records, against the
expected deltas exactly, not merely for the game's presence. The bracket image is expected to change
only when the import completes a series, and round formation only
when a whole feeding round completes; a mid-series import that
leaves the bracket unchanged is a correct landing, not a failure.

## 4. Record fidelity

An offline game's record is a box-score record: full linescore, batting
and pitching lines, and decisions, with an empty `rolls` array and a
null `manager_log`, exactly as the existing importer writes. No
play-by-play, FAC history, or engine state is created or implied. The
game recap line states the provenance: played offline at the table,
box score imported on the import date. This is a deliberate, Joe-ruled
relaxation of the full-data archive standard for table-played games
only; engine-played and co-managed games keep the full standard.

## 5. Governance

- An offline game counts as an OFFICIAL tournament game when Joe sends
  its box score as a game of a scheduled fixture. Sending the box score
  is the adoption; no separate ruling is needed.
- Exhibitions are outside this pipeline: the importer has no exhibition
  mode or store, and this spec does not create one. If Joe wants a
  table exhibition kept on the record, that is a separate decision and
  a separate build. Until then, a game Joe labels a test or an
  exhibition is simply not imported.
- Frozen series R1-01, R1-02, R1-03 cannot be edited by import; the
  importer's refusal stands.
- A box score that would change a game already on the book is refused
  and reported, never forced. Corrections to a correctly landed game
  need Joe's ruling first; the renumbering of imported games whose
  play order was wrong (section 3) is one such correction.
- If Joe sends the same box score twice, the duplicate test in
  section 3 refuses the second copy before any game number is
  assigned; Cooper reports that the game is already on the book and
  nothing changes.
- A box score sent for a series that is already complete has no next
  unplayed number to take. The import refuses it and Cooper reports
  it; a completed series changes only through Joe's correction
  ruling, outside this flow.
- A renumbering correction (section 3) is executed as one commit
  that, for each affected imported game, rewrites its id and
  `game_in_series`, renames its detail file `games/<id>.json` and
  the summary's `detail` path to match, and reorders the series
  entry's game list; two games exchanging numbers pass one of them
  through a temporary id so no step collides. The correction ends
  the way a landing does: `scripts/validate_results.py` runs, the
  generated set is regenerated, and Cooper verifies the live pages
  against the corrected ids before reporting it done. The mirror
  copy is renumbered in the same correction and verified to the
  same standard as the mirror step.
- When an import completes a series, the standing series deliverables
  still apply: Cooper prepares the series summary with a named MVP and
  runner-up from the archive, as with engine-played series. Bracket
  formation is unchanged: later rounds form only when the whole
  feeding round completes.

## 6. Proof before first real use

In a scratch clone of the repo (never on main, never in the real
archive), place one fictional box score for an unplayed fixture slot
in the clone's `inbox/` and run `scripts/import_inbox.py`, the real CI
entry point. The fictional file is built exactly as a real table
game's file is: no Seed line, and the batting and pitching tables at
the completeness threshold's minimum columns, so the proof exercises
the seedless, thinnest record every real import may take. Verify:
validation passes; the series wins and club
records move; the bracket image, series preview, and leaders
regenerate with the fictional game; the file moves to the clone's
`inbox/imported/`; and the stored records of the 26 pre-existing real
games are equal before and after, compared as parsed game summaries
for the 26 existing game ids (not a hash of the whole archive, which
necessarily changes when a game is added). Then
discard the clone. Nothing fictional is ever pushed to the real
`inbox/` or applied to the real archive. The fictional sample in
`samples/` stays a shape demo only, as its own header warns.

The first real import runs Route A with Joe present in chat, under
Joe's standing rule that every new automation runs once supervised
before it runs unattended, with the rollback in section 3 ready.
Route B's first landing is supervised the same way; only after it
verifies clean does Route B become the unattended default.

## 7. Out of scope

- No changes to the playable app (`#/play`), the engines, or any card.
- No new app UI; the `#/add` form already exists and stays as is.
- No exhibition store or mode (section 5).
- No automatic import of anything Joe has not sent for a named fixture.
