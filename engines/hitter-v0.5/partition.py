"""Percentile partition checks for a hitter hand and its out table.

Faces are 1 through 99. Face 00 is the rare-play face and is not part
of the partition.

A published card has one out table shared by every section and hand.
Those hands do not share the same holes, so the printed table cannot
be disjoint from every hand's result bands at once. The resolved
reading is: a result band owns the face; an out-table row owns a face
only when no result band does. Under that reading every face 01-99
has exactly one outcome, and the out rows that cover the holes are
the hole assignment.

Uncertain: a game engine might instead treat an overlapping out row
as a second legal reading of that face. The repaired cards were
approved with that printed overlap left in place. exact=True, used
for a table the solver just built for one hand, requires the out
table's faces to equal that hand's holes with no overlap.
"""

RESULT_KEYS = ('HR', '3B', '2B', '1B', 'BB', 'HBP', 'SO')
SECTIONS = ('WHEELHOUSE', 'PATIENT', 'TOUGH', 'IN-PLAY')
HANDS = ('vsLHP', 'vsRHP')


def _span(rng):
    if rng is None:
        return None
    if not isinstance(rng, (list, tuple)) or len(rng) < 2:
        return 'malformed'
    try:
        lo, hi = int(rng[0]), int(rng[1])
    except (TypeError, ValueError):
        return 'malformed'
    return lo, hi


def collect_claims(bands):
    """bands: iterable of (label, range or None).

    Returns (face -> label, problem strings). The first claim keeps
    the face only long enough to report the next overlap; a later
    overlap is still a problem.
    """
    faces = {}
    problems = []
    for label, rng in bands:
        if rng is None:
            continue
        span = _span(rng)
        if span == 'malformed':
            problems.append('%s range is malformed' % label)
            continue
        lo, hi = span
        if lo > hi:
            problems.append('%s %s-%s is inverted' % (label, lo, hi))
            continue
        if lo < 1 or hi > 99:
            problems.append('%s %s-%s is outside 01-99' % (label, lo, hi))
            continue
        for face in range(lo, hi + 1):
            if face in faces:
                problems.append('%s overlaps %s at %02d' % (label, faces[face], face))
                break
            faces[face] = label
    return faces, problems


def validate_hand(result_bands, out_rows, exact=False):
    """Return problem strings. An empty list is a legal hand.

    exact=False resolves a shared out table: result bands win a face
    they share with an out row, and every hole must be covered by
    exactly one out row.
    exact=True requires the out table's faces to equal the holes.
    """
    problems = []
    result_faces, result_problems = collect_claims(
        (key, (result_bands or {}).get(key)) for key in RESULT_KEYS)
    extra = [(key, rng) for key, rng in (result_bands or {}).items()
             if key not in RESULT_KEYS and rng]
    if extra:
        extra_faces, extra_problems = collect_claims(extra)
        problems.extend(extra_problems)
        for face, label in extra_faces.items():
            if face in result_faces:
                problems.append('%s overlaps %s at %02d' % (
                    label, result_faces[face], face))
            else:
                result_faces[face] = label
    problems.extend(result_problems)

    out_bands = []
    for index, row in enumerate(out_rows or []):
        if not isinstance(row, dict):
            problems.append('out row %s is malformed' % index)
            continue
        label = 'out:%s' % (row.get('result') or index)
        out_bands.append((label, row.get('range')))
    out_faces, out_problems = collect_claims(out_bands)
    problems.extend(out_problems)

    holes = [face for face in range(1, 100) if face not in result_faces]
    if exact:
        for face, label in out_faces.items():
            if face in result_faces:
                problems.append('%s overlaps result %s at %02d' % (
                    label, result_faces[face], face))
        out_only = set(out_faces)
        hole_set = set(holes)
        missing = sorted(hole_set - out_only)
        extra_faces = sorted(out_only - hole_set)
        if missing:
            problems.append('out table misses holes ' + ','.join(
                '%02d' % face for face in missing[:12]))
        if extra_faces:
            problems.append('out table covers non-holes ' + ','.join(
                '%02d' % face for face in extra_faces[:12]))
        return problems

    uncovered = [face for face in holes if face not in out_faces]
    if uncovered:
        problems.append('%d hole faces have no out, starting at %02d' % (
            len(uncovered), uncovered[0]))
    return problems


def validate_hitter_card(card_bat, exact=False):
    """Check every section and hand on a published hitter card."""
    if not card_bat or not card_bat.get('sections'):
        return []
    problems = []
    out_rows = card_bat.get('out_table') or []
    sections = card_bat.get('sections') or {}
    for sec in SECTIONS:
        section = sections.get(sec)
        if not isinstance(section, dict):
            problems.append('missing section %s' % sec)
            continue
        for hand in HANDS:
            table = section.get(hand)
            if not isinstance(table, dict):
                problems.append('%s %s missing' % (sec, hand))
                continue
            for problem in validate_hand(table, out_rows, exact=exact):
                problems.append('%s %s: %s' % (sec, hand, problem))
    return problems


def validate_solver_card(card):
    """Strict check for a card the solver just built.

    Per-hand out tables must match that hand's holes. A card that only
    has the shared published out table uses the resolved reading.
    """
    sections = card.get('sections') or {}
    per_hand = card.get('out_by_hand')
    if not per_hand:
        return validate_hitter_card(
            {'sections': sections, 'out_table': card.get('out_table') or []},
            exact=False)
    problems = []
    for sec in SECTIONS:
        for hand in HANDS:
            table = (sections.get(sec) or {}).get(hand) or {}
            rows = (per_hand.get(sec) or {}).get(hand) or []
            for problem in validate_hand(table, rows, exact=True):
                problems.append('%s %s: %s' % (sec, hand, problem))
    return problems


def validate_pitcher_table(table):
    """A 2d6 chart has each total from 2 through 12 exactly once."""
    if not isinstance(table, dict) or not table:
        return ['missing 2d6 table']
    problems = []
    keys = set(str(key) for key in table.keys())
    need = {str(n) for n in range(2, 13)}
    missing = sorted(need - keys, key=int)
    extra = sorted(keys - need)
    if missing:
        problems.append('missing 2d6 totals ' + ','.join(missing))
    if extra:
        problems.append('unexpected 2d6 keys ' + ','.join(extra))
    for key, outcome in table.items():
        if str(key) in need and not outcome:
            problems.append('empty 2d6 outcome for %s' % key)
    return problems
