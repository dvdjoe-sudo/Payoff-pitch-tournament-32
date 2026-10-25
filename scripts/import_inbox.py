#!/usr/bin/env python3
"""Import every box score dropped in inbox/.

A clean file is moved to inbox/imported/ after it is applied. A file that
fails is left in inbox/, and the problems are written to inbox/errors/.
Exit 0 when there is nothing to do or the import landed. Exit 2 when a
report was written and the archive was not changed.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "inbox"
IMPORTED = INBOX / "imported"
ERRORS = INBOX / "errors"

sys.path.insert(0, str(ROOT / "scripts"))
import import_game  # noqa: E402


def sources() -> list[Path]:
    found = []
    if not INBOX.is_dir():
        return found
    for path in sorted(INBOX.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".csv"}:
            continue
        if path.name.lower() == "readme.md":
            continue
        found.append(path)
    return found


def write_report(files: list[Path], problems: list[str]) -> None:
    ERRORS.mkdir(parents=True, exist_ok=True)
    lines = [
        "Inbox import failed.",
        "",
        "The source file was left in inbox/. Fix the box score and push it again.",
        "",
    ]
    for path in files:
        lines.append(f"File: inbox/{path.name}")
    lines.append("")
    for problem in problems:
        lines.append(f"- {problem}")
    lines.append("")
    text = "\n".join(lines)
    for path in files:
        (ERRORS / f"{path.stem}.txt").write_text(text, encoding="utf-8")
    print(text)


def main() -> int:
    files = sources()
    if not files:
        print("no box scores in inbox/")
        return 0
    parsed = []
    problems = []
    for path in files:
        try:
            games = import_game.load_path(path)
        except SystemExit as exc:
            problems.append(f"{path.name}: {exc}")
            continue
        except Exception as exc:
            problems.append(f"{path.name}: {exc}")
            continue
        for game, detail, shape in games:
            if shape or not game:
                problems.extend(f"{path.name}: {item}" for item in (shape or ["could not be read"]))
            parsed.append((game, detail, shape))
    if problems:
        write_report(files, problems)
        return 2
    apply_problems = import_game.apply_games(parsed)
    if apply_problems:
        write_report(files, apply_problems)
        return 2
    IMPORTED.mkdir(parents=True, exist_ok=True)
    for path in files:
        target = IMPORTED / path.name
        if target.exists():
            target = IMPORTED / f"{path.stem}-{path.stat().st_mtime_ns}{path.suffix}"
        path.replace(target)
        print(f"moved {path.name} to inbox/imported/")
    print("inbox import finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
