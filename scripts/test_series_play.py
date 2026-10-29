#!/usr/bin/env python3
"""Series Play validation (SERIES_PLAY_SPEC.md section 4).

Covers 4.1 (assembly proofs on the real book, read-only), 4.2 (the
scratch-clone booking proof), 4.3's importer parts (duplicate run,
changed duplicate), 4.4 (the clinch case), 4.6's pinned scratch
cases, and a parse pass over the real app's dispatched file (left
by the series battery at /tmp/series-dispatch-R1-06-G3.md).

EVERY booking runs in a scratch copy under /tmp/series-play-test.
The real book is never written: the only writes outside /tmp are
none at all.

Premise stated once (round-4 Finding 14): the club-record
expectations in 4.2 and 4.4 rest on CHC and MON having stored
games only in R1-06, so the importer's recompute over all stored
games moves exactly the R1-06 counts. Verified against the book
below before any clone is booked.

Run with the pipeline venv python:
  ~/workspace/tools/pp-t32-venv/bin/python scripts/test_series_play.py
Exit 1 on any failed check.
"""
import copy
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = Path("/tmp/series-play-test")
VENV_PY = Path.home() / "workspace/tools/pp-t32-venv/bin/python"
CUBS_HOME = Path.home() / "workspace/payoff-pitch-cubs"
PY = str(VENV_PY) if VENV_PY.exists() else sys.executable

RESULTS = []


def check(label, cond, detail=""):
    RESULTS.append((label, bool(cond)))
    print(("PASS " if cond else "FAIL ") + label + ("" if cond else " -- " + str(detail)))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def gen_series_file(book_path, out_path, root=ROOT):
    rc, out = run([PY, str(ROOT / "scripts/build_series_data.py"),
                   "--root", str(root), "--book", str(book_path),
                   "--out", str(out_path)], cwd=ROOT)
    assert rc == 0, out
    return load_json(out_path), out


def copy_repo(dst):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(
        ".git", "__pycache__", "imports"))
    return dst


def import_in(clone, md_path):
    return run([PY, "scripts/import_game.py", str(md_path), "--apply"], cwd=clone)


def series_entry(book, sid="R1-06"):
    return next(s for s in book["series"] if s["id"] == sid)


def game_rec(book, gid):
    return next(g for g in book["games"] if g["id"] == gid)


def team_rec(book, code):
    return next(t for t in book["teams"] if t["code"] == code)


# ---------------------------------------------------------------- files
def batting_md(names, rows):
    """rows: (AB,R,H,2B,3B,HR,RBI,BB,SO,HBP,SB,CS,SAC,GIDP) per name."""
    out = ["| # | Player | AB | R | H | 2B | 3B | HR | RBI | BB | SO | HBP | SB | CS | SAC | GIDP |",
           "|" + " --- |" * 16]
    for i, (name, r) in enumerate(zip(names, rows), 1):
        out.append("| " + " | ".join([str(i), name] + [str(x) for x in r]) + " |")
    return out


def pitching_md(rows):
    """rows: (name, IP, H, R, ER, BB, SO, HR, HB, BF)."""
    out = ["| Player | IP | H | R | ER | BB | SO | HR | HB | BF |",
           "|" + " --- |" * 10]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return out


def game_md(number, away_full, home_full, date, seed, recap, state,
            line_rows, decisions, sections):
    """sections: [(club_full, batting_lines, pitching_lines), ...] in
    away-batting, away-pitching, home-batting, home-pitching order
    is NOT assumed; caller passes (title, lines) pairs in order."""
    lines = [f"# R1-06 Game {number}: {away_full} at {home_full}",
             f"**Date:** {date}", f"**Seed:** {seed}",
             f"**Game recap:** {recap}",
             f"**Series state after this game:** {state}", ""]
    head = ["Team"] + [str(i) for i in range(1, len(line_rows[0][1]) + 1)] + ["R", "H", "E"]
    lines.append("| " + " | ".join(head) + " |")
    lines.append("|" + " --- |" * len(head))
    for full, cells, r, h, e in line_rows:
        lines.append("| " + " | ".join([full] + [str(c) for c in cells] +
                                        [str(r), str(h), str(e)]) + " |")
    lines += ["", f"**Decisions:** {decisions}"]
    for title, body in sections:
        lines += ["", f"## {title}"] + body
    return "\n".join(lines) + "\n"


FIXTURE = load_json(ROOT / "data/playable_r106.json")["fixture"]
CHC_NAMES = [s["name"] for s in FIXTURE["lineups"]["CHC"]]
MON_NAMES = [s["name"] for s in FIXTURE["lineups"]["MON"]]

# Pinned Game 3 (section 4.2): Montreal 4, Chicago 2 at Stade
# Olympique. Pitching: Martinez 7.0 + Wetteland 2.0; Reuschel 5.0,
# Sutter 2.0, Smith 1.0. Decisions W Martinez, L Reuschel, SV
# Wetteland. Batting matrices sum to the linescore (CHC R2 H7 SO9;
# MON R4 H9 SO7) and cross-match the pitching totals.
G3_CHC_BAT = [
    (4, 0, 1, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0),
    (4, 1, 2, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0),
    (4, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0),
    (3, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0),
    (4, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0),
    (3, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0),
    (3, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0),
    (3, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1),
    (3, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
]
G3_MON_BAT = [
    (4, 1, 2, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0),
    (4, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0),
    (4, 1, 2, 0, 0, 1, 2, 0, 1, 0, 0, 0, 0, 0),
    (4, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0),
    (3, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0),
    (3, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
    (3, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0),
    (3, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1),
    (2, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0),
]
G3_CHC_PIT = [("Rick Reuschel", "5.0", 7, 4, 3, 1, 4, 1, 1, 24),
              ("Bruce Sutter", "2.0", 1, 0, 0, 0, 2, 0, 0, 7),
              ("Lee Smith", "1.0", 1, 0, 0, 1, 1, 0, 0, 4)]
G3_MON_PIT = [("Dennis Martinez", "7.0", 5, 2, 2, 2, 6, 1, 0, 27),
              ("John Wetteland", "2.0", 2, 0, 0, 0, 3, 0, 0, 7)]


def sums(rows, idx):
    return sum(r[idx] for r in rows)


def derived_pa(bat_rows):
    """The validator's standing PA definition: AB + BB + HBP + SAC
    (SF and CI are null/zero in these pinned files)."""
    return sum(r[0] + r[7] + r[9] + r[12] for r in bat_rows)


def fix_bf(pit_rows, target_pa):
    """Set the starter's BF so the staff total equals the opposing
    derived PA, the validator's cross-check. BF is otherwise a
    free column in a pinned file."""
    rows = [list(r) for r in pit_rows]
    rows[0][9] = target_pa - sum(r[9] for r in rows[1:])
    assert rows[0][9] > 0
    return [tuple(r) for r in rows]


def build_g3(chc_pit=G3_CHC_PIT, dec_l="Rick Reuschel (Chicago Cubs)"):
    return game_md(
        3, "Chicago Cubs", "Montreal Expos", "2026-10-29", 20261503,
        "R1-06 Game 3. Chicago Cubs 2 at Montreal Expos 4.",
        "Montreal Expos leads the series 2-1 after Game 3.",
        [("Chicago Cubs", [0, 1, 0, 0, 0, 0, 1, 0, 0], 2, 7, 1),
         ("Montreal Expos", [1, 0, 2, 0, 0, 1, 0, 0, "x"], 4, 9, 0)],
        f"W: Dennis Martinez (Montreal Expos) · L: {dec_l} · SV: John Wetteland (Montreal Expos)",
        [("Chicago Cubs batting", batting_md(CHC_NAMES, G3_CHC_BAT)),
         ("Chicago Cubs pitching", pitching_md(fix_bf(chc_pit, derived_pa(G3_MON_BAT)))),
         ("Montreal Expos batting", batting_md(MON_NAMES, G3_MON_BAT)),
         ("Montreal Expos pitching", pitching_md(fix_bf(G3_MON_PIT, derived_pa(G3_CHC_BAT))))])


# Pinned Game 4 (section 4.4): Montreal 5, Chicago 3 at Montreal.
G4_CHC_BAT = [
    (4, 1, 2, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
    (4, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0),
    (4, 1, 2, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0),
    (4, 0, 1, 0, 0, 1, 2, 0, 1, 0, 0, 0, 0, 0),
    (4, 0, 0, 0, 0, 0, 0, 1, 2, 0, 0, 0, 0, 0),
    (3, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
    (3, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0),
    (3, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1),
    (3, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
]
G4_MON_BAT = [
    (5, 1, 2, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0),
    (4, 1, 2, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
    (4, 1, 2, 0, 0, 1, 3, 0, 1, 0, 0, 0, 0, 0),
    (4, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0),
    (4, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
    (3, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (3, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0),
    (3, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1),
    (3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0),
]
G4_CHC_PIT = [("Pete Alexander", "8.0", 10, 5, 5, 2, 5, 1, 0, 36)]
G4_MON_PIT = [("Bryn Smith", "7.0", 8, 3, 3, 1, 6, 1, 0, 30),
              ("John Wetteland", "2.0", 1, 0, 0, 0, 2, 0, 0, 7)]


def build_g4():
    return game_md(
        4, "Chicago Cubs", "Montreal Expos", "2026-10-30", 20261504,
        "R1-06 Game 4. Chicago Cubs 3 at Montreal Expos 5.",
        "Montreal Expos leads the series 3-1 after Game 4.",
        [("Chicago Cubs", [0, 0, 1, 0, 2, 0, 0, 0, 0], 3, 9, 0),
         ("Montreal Expos", [2, 0, 0, 1, 0, 2, 0, 0, "x"], 5, 10, 1)],
        "W: Bryn Smith (Montreal Expos) · L: Pete Alexander (Chicago Cubs) · SV: John Wetteland (Montreal Expos)",
        [("Chicago Cubs batting", batting_md(CHC_NAMES, G4_CHC_BAT)),
         ("Chicago Cubs pitching", pitching_md(fix_bf(G4_CHC_PIT, derived_pa(G4_MON_BAT)))),
         ("Montreal Expos batting", batting_md(MON_NAMES, G4_MON_BAT)),
         ("Montreal Expos pitching", pitching_md(fix_bf(G4_MON_PIT, derived_pa(G4_CHC_BAT))))])


# Pinned Game 5 (section 4.4): Montreal 6, Chicago 4 at Chicago.
G5_MON_BAT = [
    (5, 1, 2, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0),
    (5, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0),
    (4, 1, 2, 0, 0, 1, 3, 0, 1, 0, 0, 0, 0, 0),
    (4, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0),
    (4, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (4, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
    (3, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0),
    (3, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 1),
    (3, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0),
]
G5_CHC_BAT = [
    (4, 1, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (4, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0),
    (4, 1, 2, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0),
    (4, 1, 1, 0, 0, 1, 2, 0, 1, 0, 0, 0, 0, 0),
    (4, 0, 0, 0, 0, 0, 0, 1, 2, 0, 0, 0, 0, 0),
    (3, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (3, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0),
    (3, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1),
    (3, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
]
G5_MON_PIT = [("Javier Vazquez", "7.0", 7, 4, 4, 1, 6, 1, 0, 30),
              ("Jeff Reardon", "1.0", 1, 0, 0, 0, 1, 0, 0, 4),
              ("John Wetteland", "1.0", 0, 0, 0, 1, 1, 0, 0, 4)]
G5_CHC_PIT = [("Carlos Zambrano", "5.0", 7, 5, 5, 1, 4, 1, 1, 24),
              ("Lee Smith", "2.0", 2, 1, 1, 0, 2, 0, 0, 8),
              ("Pedro Strop", "1.0", 1, 0, 0, 1, 1, 0, 0, 4)]


def build_g5():
    return game_md(
        5, "Montreal Expos", "Chicago Cubs", "2026-10-31", 20261505,
        "R1-06 Game 5. Montreal Expos 6 at Chicago Cubs 4.",
        "Montreal Expos wins the series 4-1.",
        [("Montreal Expos", [1, 0, 2, 0, 2, 0, 1, 0, 0], 6, 10, 0),
         ("Chicago Cubs", [0, 2, 0, 1, 0, 0, 1, 0, 0], 4, 8, 1)],
        "W: Javier Vazquez (Montreal Expos) · L: Carlos Zambrano (Chicago Cubs) · SV: John Wetteland (Montreal Expos)",
        [("Montreal Expos batting", batting_md(MON_NAMES, G5_MON_BAT)),
         ("Montreal Expos pitching", pitching_md(fix_bf(G5_MON_PIT, derived_pa(G5_CHC_BAT)))),
         ("Chicago Cubs batting", batting_md(CHC_NAMES, G5_CHC_BAT)),
         ("Chicago Cubs pitching", pitching_md(fix_bf(G5_CHC_PIT, derived_pa(G5_MON_BAT))))])


def parse_set_home_availability(path, game_number):
    """Rows from a set home's official record: per-club subsequences
    of (name, outs, status, cap_outs) in the record's own order."""
    text = Path(path).read_text(encoding="utf-8")
    m = re.search(rf"## Game {game_number} availability.*?\n(.*?)(?:\n## |\Z)",
                  text, re.S)
    rows = {"CHC": [], "MON": []}
    club_of = {"Chicago": "CHC", "Montreal": "MON"}
    # Entries wrap across lines in the record; split the section
    # into bullet chunks first, then read each whole chunk.
    for chunk in re.split(r"\n- ", "\n" + m.group(1)):
        mm = re.match(r"-?\s*(.+?) \((Chicago|Montreal)\): (\d+) outs", chunk)
        if not mm:
            continue
        status, cap = "free", None
        if "Unavailable" in chunk:
            status = "unavailable"
        cm = re.search(r"capped at (\d+) outs", chunk)
        if cm:
            status, cap = "capped", int(cm.group(1))
        rows[club_of[mm.group(2)]].append(
            (mm.group(1), int(mm.group(3)), status, cap))
    return rows


def avail_tuples(series_file, club):
    ng = series_file["next_game"]
    return [(r["name"], r["prev_outs"], r["status"], r["cap_outs"])
            for r in ng["availability"][club]]


def main():
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    book = load_json(ROOT / "tournament_results.json")
    real_g1 = copy.deepcopy(game_rec(book, "R1-06-G1"))
    real_g2 = copy.deepcopy(game_rec(book, "R1-06-G2"))
    real_d1 = load_json(ROOT / "games/R1-06-G1.json")
    real_d2 = load_json(ROOT / "games/R1-06-G2.json")

    # Finding 14 premise: CHC/MON appear in no other series' games.
    others = [g["id"] for g in book["games"]
              if g["series_id"] != "R1-06" and {g["away"], g["home"]} & {"CHC", "MON"}]
    check("premise: CHC and MON have stored games only in R1-06",
          not others, others)

    # ------------------------------------------------------ 4.1
    sf = load_json(ROOT / "data/series_r106.json")
    check("4.1 series file status and score",
          sf["status"] == "in-progress" and sf["wins"] == {"CHC": 1, "MON": 1}
          and sf["playable_data_complete"] is True and sf["blocked_reason"] is None,
          json.dumps({k: sf[k] for k in ("status", "wins", "blocked_reason")}))
    check("4.1 stored games are Games 1-2 in order",
          sf["stored_games"] == [
              {"number": 1, "id": "R1-06-G1", "away": "MON", "home": "CHC"},
              {"number": 2, "id": "R1-06-G2", "away": "MON", "home": "CHC"}],
          json.dumps(sf["stored_games"]))
    ng = sf["next_game"]
    check("4.1 Game 3 assembly: Montreal home, Stade Olympique",
          ng["number"] == 3 and ng["id"] == "R1-06-G3" and ng["home"] == "MON"
          and ng["away"] == "CHC" and ng["park"] == "Stade Olympique",
          json.dumps({k: ng[k] for k in ("number", "id", "home", "away", "park")}))
    check("4.1 proposed starters Reuschel and Dennis Martinez, no block",
          ng["proposed_starters"] == {"CHC": "Rick Reuschel", "MON": "Dennis Martinez"}
          and ng["starter_blocked"] == [],
          json.dumps(ng["proposed_starters"]))
    check("4.1 Game 3 availability rows",
          avail_tuples(sf, "CHC") == [("Mordecai Brown", 18, "unavailable", None),
                                      ("Pedro Strop", 2, "free", None),
                                      ("Bruce Sutter", 4, "free", None),
                                      ("Lee Smith", 3, "free", None)]
          and avail_tuples(sf, "MON") == [("Pedro Martinez", 24, "unavailable", None),
                                          ("John Wetteland", 3, "free", None)],
          json.dumps(ng["availability"]))
    unavail = {r["name"] for c in ("CHC", "MON") for r in ng["availability"][c]
               if r["status"] == "unavailable"}
    check("4.1 unavailable arms are selectable in no role",
          all(ng["proposed_starters"][c] not in unavail for c in ("CHC", "MON"))
          and all(n not in unavail for c in ("CHC", "MON") for n in ng["pens"][c]),
          str(unavail))
    check("4.1 lineups, benches, pens copied from the fixture",
          ng["lineups"] == FIXTURE["lineups"] and ng["benches"] == FIXTURE["benches"]
          and ng["pens"] == {c: [n for n in FIXTURE["pens"][c] if n not in unavail]
                             for c in ("CHC", "MON")})
    # Cross-check row for row against the set home's own records.
    rec2 = parse_set_home_availability(CUBS_HOME / "PP_R1_06_G2_OFFICIAL.md", 3)
    check("4.1 availability matches the Game 2 record row for row (6 rows)",
          avail_tuples(sf, "CHC") == rec2["CHC"] and avail_tuples(sf, "MON") == rec2["MON"]
          and len(rec2["CHC"]) + len(rec2["MON"]) == 6,
          json.dumps(rec2))
    # The Game 2 load, from a book truncated to Game 1.
    g1_book = copy.deepcopy(book)
    g1_book["games"] = [g for g in g1_book["games"] if g["id"] == "R1-06-G1"]
    e = series_entry(g1_book)
    e["games"] = ["R1-06-G1"]
    e["wins"] = {"CHC": 1, "MON": 0}
    g1_book_path = WORK / "book_g1.json"
    g1_book_path.write_text(json.dumps(g1_book), encoding="utf-8")
    g2load_dir = WORK / "g2load"
    g2load_dir.mkdir()
    sf2, _ = gen_series_file(g1_book_path, g2load_dir / "series_r106.json")
    ng2 = sf2["next_game"]
    check("4.1 Game 2 load: Chicago home, Wrigley, Brown and Pedro proposed",
          ng2["number"] == 2 and ng2["home"] == "CHC" and ng2["park"] == "Wrigley Field"
          and ng2["proposed_starters"] == {"CHC": "Mordecai Brown", "MON": "Pedro Martinez"},
          json.dumps({k: ng2[k] for k in ("number", "home", "park", "proposed_starters")}))
    check("4.1 Game 2 availability rows (the pinned 5)",
          avail_tuples(sf2, "CHC") == [("Fergie Jenkins", 19, "unavailable", None),
                                       ("Kerry Wood", 6, "capped", 3),
                                       ("Bruce Sutter", 2, "free", None)]
          and avail_tuples(sf2, "MON") == [("Steve Rogers", 19, "unavailable", None),
                                           ("Tim Burke", 5, "free", None)],
          json.dumps(ng2["availability"]))
    rec1 = parse_set_home_availability(
        CUBS_HOME / "PP_R1_06_G1_OFFICIAL_seed229154.md", 2)
    check("4.1 Game 2 availability matches the Game 1 record row for row (5 rows)",
          avail_tuples(sf2, "CHC") == rec1["CHC"] and avail_tuples(sf2, "MON") == rec1["MON"]
          and len(rec1["CHC"]) + len(rec1["MON"]) == 5,
          json.dumps(rec1))

    # ------------------------------------------------------ 4.2
    # The pinned files' internal arithmetic, asserted before use:
    # (R, H, SO) index into the batting tuples: R=1, H=2, SO=8.
    assert (sums(G3_CHC_BAT, 1), sums(G3_CHC_BAT, 2), sums(G3_CHC_BAT, 8)) == (2, 7, 9)
    assert (sums(G3_MON_BAT, 1), sums(G3_MON_BAT, 2), sums(G3_MON_BAT, 8)) == (4, 9, 7)
    assert (sums(G4_CHC_BAT, 1), sums(G4_CHC_BAT, 2), sums(G4_CHC_BAT, 8)) == (3, 9, 8)
    assert (sums(G4_MON_BAT, 1), sums(G4_MON_BAT, 2), sums(G4_MON_BAT, 8)) == (5, 10, 5)
    assert (sums(G5_MON_BAT, 1), sums(G5_MON_BAT, 2), sums(G5_MON_BAT, 8)) == (6, 10, 7)
    assert (sums(G5_CHC_BAT, 1), sums(G5_CHC_BAT, 2), sums(G5_CHC_BAT, 8)) == (4, 8, 8)

    clone = copy_repo(WORK / "clone42")
    g3_path = clone / "R1-06-G3.md"
    g3_path.write_text(build_g3(), encoding="utf-8")
    rc, out = import_in(clone, g3_path)
    check("4.2 test Game 3 books in the scratch clone",
          rc == 0 and "applied 1 game(s)" in out and out.rstrip().endswith("archive matches the validator"),
          out[-400:])
    cbook = load_json(clone / "tournament_results.json")
    ce = series_entry(cbook)
    check("4.2 series moves to 2-1 Montreal, still in progress",
          ce["games"] == ["R1-06-G1", "R1-06-G2", "R1-06-G3"]
          and ce["wins"] == {"CHC": 1, "MON": 2} and ce["status"] == "in-progress",
          json.dumps({k: ce[k] for k in ("games", "wins", "status")}))
    g3 = game_rec(cbook, "R1-06-G3")
    check("4.2 Game 3 summary fields",
          g3["away"] == "CHC" and g3["home"] == "MON" and g3["winner"] == "MON"
          and g3["score"] == {"CHC": 2, "MON": 4} and g3["rng_seed"] == 20261503,
          json.dumps({k: g3.get(k) for k in ("away", "home", "winner", "score", "rng_seed")}))
    chc, mon = team_rec(cbook, "CHC"), team_rec(cbook, "MON")
    check("4.2 club records per the recompute rule",
          (chc["game_wins"], chc["game_losses"]) == (1, 2)
          and (mon["game_wins"], mon["game_losses"]) == (2, 1),
          json.dumps([(t["code"], t["game_wins"], t["game_losses"]) for t in (chc, mon)]))
    csf = load_json(clone / "data/series_r106.json")
    # Snapshot for the series battery (section 4.3 step 4 applies
    # exactly this file: Game 3 booked, Game 4 offered).
    snap = WORK / "after_g3"
    snap.mkdir(exist_ok=True)
    shutil.copy(clone / "data/series_r106.json", snap / "series_r106.json")
    ng4 = csf["next_game"]
    check("4.2 regenerated file offers Game 4 at Montreal",
          ng4["number"] == 4 and ng4["home"] == "MON" and ng4["park"] == "Stade Olympique",
          json.dumps({k: ng4[k] for k in ("number", "home", "park")}))
    check("4.2 Game 4 availability from Game 3's outs",
          avail_tuples(csf, "CHC") == [("Rick Reuschel", 15, "unavailable", None),
                                       ("Bruce Sutter", 6, "capped", 3),
                                       ("Lee Smith", 3, "free", None)]
          and avail_tuples(csf, "MON") == [("Dennis Martinez", 21, "unavailable", None),
                                           ("John Wetteland", 6, "capped", 3)],
          json.dumps(ng4["availability"]))
    check("4.2 Game 4 proposed starters are the next chairs (Alexander, Bryn Smith)",
          ng4["proposed_starters"] == {"CHC": "Pete Alexander", "MON": "Bryn Smith"},
          json.dumps(ng4["proposed_starters"]))
    check("4.2 Games 1-2 parsed records identical to the real book afterward",
          game_rec(cbook, "R1-06-G1") == real_g1 and game_rec(cbook, "R1-06-G2") == real_g2
          and load_json(clone / "games/R1-06-G1.json") == real_d1
          and load_json(clone / "games/R1-06-G2.json") == real_d2)

    # ------------------------------------------- 4.3 importer parts
    before = load_json(clone / "tournament_results.json")
    rc, out = import_in(clone, g3_path)
    check("4.3 duplicate run: accepted as already booked, nothing applied",
          rc == 0 and "applied" not in out and out.rstrip().endswith("archive matches the validator"),
          out[-300:])
    check("4.3 duplicate run leaves the archive parsed-identical",
          load_json(clone / "tournament_results.json") == before)
    sb_path = clone / "R1-06-G3-sb.md"
    sb_text = build_g3().replace("| 1 | " + CHC_NAMES[0] + " | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |",
                                 "| 1 | " + CHC_NAMES[0] + " | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 1 |")
    assert sb_text != build_g3()
    sb_path.write_text(sb_text, encoding="utf-8")
    rc, out = import_in(clone, sb_path)
    check("4.3 changed duplicate is refused by the importer",
          rc == 1 and "import failed:" in out and "sb 1 != 0" in out,
          out[:300])
    check("4.3 the refused run leaves the archive parsed-identical",
          load_json(clone / "tournament_results.json") == before)

    # ------------------------------------------------------ 4.4
    g4_path = clone / "R1-06-G4.md"
    g4_path.write_text(build_g4(), encoding="utf-8")
    rc, out = import_in(clone, g4_path)
    cbook = load_json(clone / "tournament_results.json")
    ce = series_entry(cbook)
    csf = load_json(clone / "data/series_r106.json")
    check("4.4 Game 4 books; series 3-1, Game 5 offered at Wrigley",
          rc == 0 and "applied 1 game(s)" in out and ce["wins"] == {"CHC": 1, "MON": 3}
          and ce["status"] == "in-progress" and csf["next_game"]["number"] == 5
          and csf["next_game"]["home"] == "CHC" and csf["next_game"]["park"] == "Wrigley Field",
          out[-200:] + json.dumps(csf["next_game"] or {}))
    g5_path = clone / "R1-06-G5.md"
    g5_path.write_text(build_g5(), encoding="utf-8")
    rc, out = import_in(clone, g5_path)
    cbook = load_json(clone / "tournament_results.json")
    ce = series_entry(cbook)
    chc, mon = team_rec(cbook, "CHC"), team_rec(cbook, "MON")
    csf = load_json(clone / "data/series_r106.json")
    check("4.4 the fourth win completes the series for Montreal",
          rc == 0 and ce["status"] == "complete" and ce["winner"] == "MON" and ce["loser"] == "CHC",
          out[-200:] + json.dumps({k: ce.get(k) for k in ("status", "winner", "loser")}))
    check("4.4 bracket consequences: Montreal to the winners side, Chicago to the losers side, not eliminated",
          mon["series_wins"] == 1 and mon["bracket"] == "winners"
          and chc["series_losses"] == 1 and chc["bracket"] == "losers"
          and chc["eliminated"] is False,
          json.dumps([(t["code"], t.get("series_wins"), t.get("series_losses"), t.get("bracket"), t.get("eliminated")) for t in (chc, mon)]))
    check("4.4 no Game 6 is offered after the clinch",
          csf["status"] == "complete" and csf["next_game"] is None
          and csf["blocked_reason"] == "complete",
          json.dumps({k: csf[k] for k in ("status", "next_game", "blocked_reason")}))

    # ------------------------------------------------------ 4.6a gap
    gap_book = copy.deepcopy(book)
    g3_fake = copy.deepcopy(real_g2)
    g3_fake["id"] = "R1-06-G3"
    g3_fake["game_in_series"] = 3
    gap_book["games"] = [real_g1, g3_fake]
    ge = series_entry(gap_book)
    ge["games"] = ["R1-06-G1", "R1-06-G3"]
    gap_path = WORK / "book_gap.json"
    gap_path.write_text(json.dumps(gap_book), encoding="utf-8")
    gsf, gout = gen_series_file(gap_path, WORK / "series_gap.json")
    check("4.6a gap: no game offered, reason gap, generator names the missing number",
          gsf["next_game"] is None and gsf["blocked_reason"] == "gap" and "game 2 is missing" in gout,
          gout.strip())

    # ------------------------------------------- 4.6b no park face
    nopark = copy_repo(WORK / "nopark")
    (nopark / "assets/parks/stade-olympique.webp").unlink()
    rc, out = run([PY, "scripts/build_series_data.py"], cwd=nopark)
    nsf = load_json(nopark / "data/series_r106.json")
    check("4.6b missing park face: playable_data_complete false, no offer",
          rc == 0 and nsf["playable_data_complete"] is False and nsf["next_game"] is None
          and nsf["blocked_reason"] == "not-playable-data-complete",
          json.dumps({k: nsf[k] for k in ("playable_data_complete", "blocked_reason")}))
    rc, out = run(["node", "-e",
                   "const P=require('./js/play.js');"
                   "const fs=require('fs');"
                   "P.PlayData.load(JSON.parse(fs.readFileSync('data/playable_r106.json','utf8')));"
                   "const f=JSON.parse(fs.readFileSync('/tmp/series-play-test/nopark/data/series_r106.json','utf8'));"
                   "const store={getItem:()=>null,setItem:()=>{},removeItem:()=>{}};"
                   "console.log(JSON.stringify(P.applySeriesFile(f, store)));"],
                  cwd=ROOT)
    applied = json.loads(out.strip().splitlines()[-1]) if rc == 0 else {}
    check("4.6b applySeriesFile on that file returns none with the reason",
          applied.get("kind") == "none" and applied.get("blocked_reason") == "not-playable-data-complete",
          out[-200:])

    # ------------------------------------------- 4.6c starter blocked
    blk_book = copy.deepcopy(book)
    g2b = game_rec(blk_book, "R1-06-G2")
    template = next(p for p in g2b["pitching"] if p["name"] == "Pedro Martinez")
    for name, outs, order in (("Steve Rogers", 6, 3), ("Dennis Martinez", 9, 4),
                              ("Bryn Smith", 7, 5), ("Javier Vazquez", 12, 6)):
        line = copy.deepcopy(template)
        line.update({"name": name, "outs": outs, "appearance_order": order,
                     "player_id": None})
        g2b["pitching"].append(line)
    blk_path = WORK / "book_blocked.json"
    blk_path.write_text(json.dumps(blk_book), encoding="utf-8")
    bsf, _ = gen_series_file(blk_path, WORK / "series_blocked.json")
    bng = bsf["next_game"]
    check("4.6c starter blocked: Montreal has no free chair, Chicago proposes Reuschel",
          bng is not None and bng["proposed_starters"]["MON"] is None
          and bng["starter_blocked"] == ["MON"]
          and bng["proposed_starters"]["CHC"] == "Rick Reuschel"
          and bsf["blocked_reason"] is None,
          json.dumps(bng["proposed_starters"]) + json.dumps(bsf["blocked_reason"]))

    # ------------------------------------------- 4.6d aggregation
    agg_book = copy.deepcopy(book)
    g2a = game_rec(agg_book, "R1-06-G2")
    pedro = next(p for p in g2a["pitching"] if p["name"] == "Pedro Martinez")
    pedro["outs"] = 20
    pedro["appearance_order"] = 1
    second = copy.deepcopy(pedro)
    second["outs"] = 4
    second["appearance_order"] = 5
    g2a["pitching"].append(second)
    agg_path = WORK / "book_agg.json"
    agg_path.write_text(json.dumps(agg_book), encoding="utf-8")
    asf, _ = gen_series_file(agg_path, WORK / "series_agg.json")
    check("4.6d split lines aggregate: Pedro still one row of 24, unavailable",
          avail_tuples(asf, "MON") == [("Pedro Martinez", 24, "unavailable", None),
                                       ("John Wetteland", 3, "free", None)],
          json.dumps(asf["next_game"]["availability"]["MON"]))

    # ------------------------------------------- 4.6e emergency starter
    eclone = copy_repo(WORK / "clone_e")
    e_pit = [("Bruce Sutter", "5.0", 6, 3, 3, 1, 4, 1, 1, 22),
             ("Lee Smith", "2.0", 2, 1, 0, 0, 2, 0, 0, 8),
             ("Pedro Strop", "1.0", 1, 0, 0, 1, 1, 0, 0, 4)]
    eg3 = build_g3(chc_pit=e_pit, dec_l="Bruce Sutter (Chicago Cubs)")
    eg3_path = eclone / "R1-06-G3.md"
    eg3_path.write_text(eg3, encoding="utf-8")
    rc, out = import_in(eclone, eg3_path)
    esf = load_json(eclone / "data/series_r106.json")
    eng = esf["next_game"]
    check("4.6e an emergency starter books and the pointer follows the last chair",
          rc == 0 and eng["proposed_starters"] == {"CHC": "Rick Reuschel", "MON": "Bryn Smith"},
          out[-200:] + json.dumps(eng["proposed_starters"]))
    check("4.6e the emergency starter's own outs govern his next game",
          ("Bruce Sutter", 15, "unavailable", None) in avail_tuples(esf, "CHC")
          and "Bruce Sutter" not in eng["pens"]["CHC"],
          json.dumps(eng["availability"]["CHC"]))

    # --------------------------- the app's own dispatched file parses
    # The series battery writes the dispatch from a real played
    # game; it needs this suite's clones, so on a cold /tmp this
    # suite runs the battery itself at this point to produce it.
    dispatched = Path("/tmp/series-dispatch-R1-06-G3.md")
    if not dispatched.exists():
        run(["node", "scripts/batteries.mjs", "series"], cwd=ROOT)
    check("the series battery left a dispatched file from real app play",
          dispatched.exists(), str(dispatched))
    if dispatched.exists():
        sys.path.insert(0, str(ROOT / "scripts"))
        import import_game
        parsed = import_game.load_path(dispatched)
        problems = [p for _, _, ps in parsed for p in ps]
        check("the app's dispatched Game 3 parses with no problems",
              len(parsed) == 1 and not problems, "; ".join(problems[:4]))

    failed = [label for label, ok in RESULTS if not ok]
    print(f"\nSERIES PLAY TESTS: {len(RESULTS) - len(failed)}/{len(RESULTS)} checks pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
