#!/usr/bin/env python3
"""v0.3 batch runner: process a CSV of hitters, produce three review lists.

Usage: python3 batch_runner.py input.csv
Output (in ../output/):
  - pass_list.csv: clean cards, no review needed
  - architecture_limited.csv: best legal card, format compromise noted
  - solver_review.csv: genuine technical problems, inspect before approving
  - batch_summary.txt: counts and overall report
"""
import csv, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hitter_solver import build_one, expected, event_targets, diagnose, \
    fit_report, classify_review, err

HIST = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HIST, 'output')


def run_batch(input_csv, force=False, out_dir=None):
    # Overwrite guard (2026-10-16 audit fix): with no explicit
    # out_dir, run_batch writes to the default OUT tree and refuses
    # to write over an existing card file (see the check at the
    # write below). Passing an explicit new output directory is the
    # supported way to produce a fresh set; existing cards there are
    # treated the same way. --force no longer silently replaces a
    # card in the default tree.
    out_root = os.path.abspath(out_dir) if out_dir else OUT
    with open(input_csv) as f:
        rows = list(csv.DictReader(f))
    passed, arch, solver = [], [], []
    for row in rows:
        name = row.get('Name', 'UNKNOWN')
        # v0.5: resumable — skip if v0.5 card already exists
        slug = __import__('re').sub(r'[^a-z0-9]+', '-',
                                    name.lower()).strip('-')
        existing = os.path.join(out_root, 'cards', slug + '-card.json')
        if not force and os.path.exists(existing):
            try:
                if json.load(open(existing)).get('audit', {}).get(
                        'solver_version') == '0.5':
                    print(f"{name}: SKIP (v0.5 card exists, use --force to rebuild)")
                    continue
            except Exception:
                pass
        try:
            built = build_one(row)
        except Exception as e:
            solver.append({'name': name, 'status': 'SOLVER-REVIEW',
                           'primary_issue': f'build failed: {e}',
                           'fit_error': '', 'best_possible': '',
                           'file': ''})
            print(f"{name}: BUILD FAILED ({e})")
            continue
        if built is None:
            print(f"{name}: SKIP (pitcher)")
            continue
        card, exp, tgt, best_comp, slug, actual_err, best_err, diag = built
        # write card JSON
        outdir = os.path.join(out_root, 'cards')
        os.makedirs(outdir, exist_ok=True)
        out = os.path.join(outdir, slug + '-card.json')
        if out_dir is None and os.path.exists(out):
            raise RuntimeError(
                "refusing to overwrite existing card file %s; pass "
                "an explicit new output directory (out_dir or "
                "--out-dir) to write a fresh set instead" % out)
        json.dump(card, open(out, 'w'), indent=1)
        # classify
        _, _, fit_ok_str = fit_report(exp, tgt)
        fit_ok = (fit_ok_str == 'PASS')
        status, reason = classify_review(fit_ok, actual_err, best_err)
        ev_tgt = event_targets(row)
        _, issue = diagnose(exp, ev_tgt, tgt)
        rec = {'name': card['name'], 'status': status,
               'primary_issue': issue,
               'fit_error': round(actual_err, 4),
               'best_possible': round(best_err, 4),
               'opt_status': diag['opt_status'],
               'improvement': round(diag['improvement'], 1),
               'reason': reason, 'file': out}
        if status == 'PASS':
            passed.append(rec)
        elif status == 'ARCHITECTURE-LIMITED':
            arch.append(rec)
        else:
            solver.append(rec)
        print(f"{card['name']}: {status} ({issue})")
    # write the three lists
    os.makedirs(out_root, exist_ok=True)
    for lst, fname in ((passed, 'pass_list.csv'),
                       (arch, 'architecture_limited.csv'),
                       (solver, 'solver_review.csv')):
        with open(os.path.join(out_root, fname), 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['name', 'status',
                                              'primary_issue', 'fit_error',
                                              'best_possible', 'opt_status',
                                              'improvement', 'reason',
                                              'file'])
            w.writeheader()
            w.writerows(lst)
    # summary
    total = len(passed) + len(arch) + len(solver)
    summary = (f"Batch complete: {total} players\n"
               f"  PASS: {len(passed)}\n"
               f"  ARCHITECTURE-LIMITED: {len(arch)}\n"
               f"  SOLVER-REVIEW: {len(solver)}\n")
    with open(os.path.join(out_root, 'batch_summary.txt'), 'w') as f:
        f.write(summary)
    print("\n" + summary)
    print(f"Lists written to {out_root}/")


if __name__ == '__main__':
    force = '--force' in sys.argv
    out_dir = None
    args = []
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--out-dir' and i + 1 < len(argv):
            out_dir = argv[i + 1]
            i += 2
        elif a.startswith('--out-dir='):
            out_dir = a.split('=', 1)[1]
            i += 1
        elif a.startswith('--'):
            i += 1
        else:
            args.append(a)
            i += 1
    csv_path = args[0]
    run_batch(csv_path, force=force, out_dir=out_dir)
