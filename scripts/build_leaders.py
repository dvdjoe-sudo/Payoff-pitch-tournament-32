#!/usr/bin/env python3
"""Write the tournament's generated documents from one publisher.

`build()` returns LEADERS.md. `main()` also writes team stats, box scores,
the awards and records pages, the JSON and RSS feeds, and the share graphics.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _publish():
    path = Path(__file__).resolve().parent / "publish.py"
    spec = importlib.util.spec_from_file_location("publish_docs", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build() -> str:
    return _publish().leaders_markdown()


def main() -> None:
    _publish().write_all()


if __name__ == "__main__":
    main()
