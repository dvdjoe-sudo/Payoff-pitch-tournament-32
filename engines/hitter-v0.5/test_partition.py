#!/usr/bin/env python3
"""Partition, repack, and review-classification checks. No 1986 data."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from partition import validate_hand, validate_solver_card
import hitter_solver as hs


def hand(hr, single=None):
    table = {'HR': hr, '3B': None, '2B': None, '1B': single,
             'BB': None, 'HBP': None, 'SO': None}
    return table


def test_exact_cover():
    table = hand([1, 40], [41, 99])
    rows = []
    problems = validate_hand(table, rows, exact=True)
    assert problems == [], problems


def test_inverted_overlap_and_past_99():
    table = hand([1, 40], [30, 50])
    table['2B'] = [30, 20]
    table['3B'] = [90, 120]
    problems = validate_hand(table, [], exact=True)
    text = ' '.join(problems)
    assert 'inverted' in text
    assert 'outside 01-99' in text
    assert 'overlaps' in text


def test_hole_without_out_fails_resolved_reading():
    table = hand([1, 40], [41, 90])
    problems = validate_hand(table, [], exact=False)
    assert any('hole' in problem for problem in problems)


def test_shared_out_table_covers_holes():
    table = hand([1, 40], [80, 99])
    rows = [{'range': [41, 99], 'result': 'P4'}]
    assert validate_hand(table, rows, exact=False) == []
    # The printed out row overlaps the single. The resolved reading
    # still gives face 80 to 1B. The strict reading does not.
    assert validate_hand(table, rows, exact=True)


def test_project_shaped_pulls_triples_back_onto_comps():
    widths = {}
    for sec, keys in hs.CANON.items():
        for hand in ('vsLHP', 'vsRHP'):
            for key in keys:
                widths[(sec, hand, key)] = 0
    widths[('WHEELHOUSE', 'vsLHP', '3B')] = 1
    widths[('WHEELHOUSE', 'vsRHP', '3B')] = 3
    shares = hs.shape_shares(widths)
    dumped = dict(widths)
    dumped[('WHEELHOUSE', 'vsLHP', '3B')] = 13
    dumped[('WHEELHOUSE', 'vsRHP', '3B')] = 13
    dumped[('IN-PLAY', 'vsLHP', '3B')] = 9
    projected = hs.project_shaped(dumped, shares)
    assert projected[('IN-PLAY', 'vsLHP', '3B')] == 0, projected
    left = projected[('WHEELHOUSE', 'vsLHP', '3B')]
    right = projected[('WHEELHOUSE', 'vsRHP', '3B')]
    assert left + right == 35, (left, right)
    assert abs(left / 35 - 0.25) < 0.05, (left, right)
    assert abs(right / 35 - 0.75) < 0.05, (left, right)


def test_repack_clears_neighborhood_overlap():
    sections = {}
    for sec, keys in hs.CANON.items():
        sections[sec] = {}
        for side in ('vsLHP', 'vsRHP'):
            sections[sec][side] = {key: None for key in keys}
    sections['WHEELHOUSE']['vsLHP']['HR'] = [1, 74]
    sections['WHEELHOUSE']['vsLHP']['1B'] = [58, 319]
    packed = hs.repack_sections(sections)
    hr = packed['WHEELHOUSE']['vsLHP']['HR']
    single = packed['WHEELHOUSE']['vsLHP']['1B']
    assert hr[0] == 1 and hr[1] <= 99
    assert single is None or single[0] > hr[1]
    assert single is None or single[1] <= 99
    per, shared = hs.out_tables_from_holes(packed, [
        {'range': [1, 99], 'result': 'P4'}])
    card = {'sections': packed, 'out_by_hand': per, 'out_table': shared}
    assert validate_solver_card(card) == [], validate_solver_card(card)
    holes = hs.hole_faces(packed['WHEELHOUSE']['vsLHP'])
    covered = []
    for row in per['WHEELHOUSE']['vsLHP']:
        covered.extend(range(row['range'][0], row['range'][1] + 1))
    assert covered == holes


def test_classify_review_gap():
    assert hs.classify_review(True, 0.02, 0.01)[0] == 'PASS'
    assert hs.classify_review(False, 0.02, 0.01)[0] == 'SOLVER-REVIEW'
    assert hs.classify_review(False, 0.01, 0.01)[0] == 'ARCHITECTURE-LIMITED'
    assert hs.classify_review(False, 0.004, 0.001)[0] == 'ARCHITECTURE-LIMITED'
    assert hs.classify_review(False, 0.02, None)[0] == 'SOLVER-REVIEW'


def test_modules_import_without_reference_files():
    import importlib
    import event_vectors
    import pitcher_solver
    import historical_solver
    importlib.reload(event_vectors)
    importlib.reload(pitcher_solver)
    importlib.reload(historical_solver)


if __name__ == '__main__':
    test_exact_cover()
    test_inverted_overlap_and_past_99()
    test_hole_without_out_fails_resolved_reading()
    test_shared_out_table_covers_holes()
    test_project_shaped_pulls_triples_back_onto_comps()
    test_repack_clears_neighborhood_overlap()
    test_classify_review_gap()
    # Pitcher modules live next door. Put them on the path for the import test.
    pit = os.path.join(os.path.dirname(HERE), 'pitcher-v0.2.3')
    sys.path.insert(0, pit)
    test_modules_import_without_reference_files()
    print('partition tests passed')
