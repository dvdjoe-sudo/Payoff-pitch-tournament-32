#!/usr/bin/env python3
"""Write ROSTERS.md from tournament_results.json.

Game files record who appeared. They do not record positions, and they
do not record a player who has not yet played. The Yankees and Marlins
blocks below are the roster text that used to live in TOURNAMENT_RULES.md,
copied here so that text stays in the repo. They are not inferred from
the box scores. The owner's later cards are in data/announced_rosters.json.
A club that has already played and was not given one of those cards stays
on the game record only.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "tournament_results.json"
ANNOUNCED = ROOT / "data" / "announced_rosters.json"
OUT = ROOT / "ROSTERS.md"

# Surname plus the original roster line. Surnames are matched against the
# last token of a name in the results file ("Alex Rodriguez" -> Rodriguez).
CANONICAL = {
    "NYY": {
        "manager": "Casey Stengel",
        "lineup": [
            ("Jeter", "1 Jeter SS"),
            ("Judge", "2 Judge RF"),
            ("Ruth", "3 Ruth DH"),
            ("Gehrig", "4 Gehrig 1B"),
            ("Mantle", "5 Mantle LF"),
            ("DiMaggio", "6 DiMaggio CF"),
            ("Rodriguez", "7 A. Rodriguez 3B"),
            ("Berra", "8 Berra C"),
            ("Randolph", "9 Randolph 2B"),
        ],
        "bench": [
            ("Munson", "Munson (C2)"),
            ("Lazzeri", "Lazzeri (IF/BAT)"),
            ("Mattingly", "Mattingly (1B/BAT)"),
            ("Williams", "B. Williams (OF)"),
            ("Jackson", "R. Jackson (OF/BAT)"),
        ],
        "rotation": [
            ("Ford", "Ford"),
            ("Ruffing", "Ruffing"),
            ("Gomez", "Gomez"),
            ("Guidry", "Guidry"),
            ("Pettitte", "Pettitte"),
        ],
        "bullpen": [
            ("Rivera", "Rivera (CL)"),
            ("Gossage", "Gossage (FIRE)"),
            ("Lyle", "Lyle (LH FIRE)"),
            ("Robertson", "Robertson (RH SET)"),
            ("Righetti", "Righetti (LATE/MULTI)"),
            ("Stanton", "Stanton (LH SPEC)"),
            ("Reynolds", "Reynolds (LONG/SWING)"),
        ],
    },
    "MIA": {
        "manager": "Jack McKeon",
        "lineup": [
            ("Castillo", "1 Castillo 2B"),
            ("Yelich", "2 Yelich CF"),
            ("Sheffield", "3 Sheffield DH"),
            ("Stanton", "4 Stanton RF"),
            ("Cabrera", "5 Cabrera 3B"),
            ("Ramirez", "6 Ramirez SS"),
            ("Floyd", "7 Floyd LF"),
            ("Conine", "8 Conine 1B"),
            ("Realmuto", "9 Realmuto C"),
        ],
        "bench": [
            ("Johnson", "C. Johnson (C2)"),
            ("Lopez", "Lopez (UTIL)"),
            ("Uggla", "Uggla (INF/POWER)"),
            ("Ozuna", "Ozuna (OF4)"),
            ("Lee", "Lee (1B/POWER)"),
        ],
        "rotation": [
            ("Johnson", "Johnson"),
            ("Alcantara", "Alcantara"),
            ("Willis", "Willis"),
            ("Beckett", "Beckett"),
            ("Fernandez", "Fernandez"),
        ],
        "bullpen": [
            ("Nen", "Nen (CL)"),
            ("Cishek", "Cishek (SU)"),
            ("Ramos", "Ramos (SU)"),
            ("Scott", "Scott (LH)"),
            ("Bender", "Bender (MR)"),
            ("Alfonseca", "Alfonseca (MR)"),
            ("Burnett", "Burnett (LR/EMER SP)"),
        ],
    },
}

# Fact carried from the 2026-10-23 seed note. The build report itself is
# not in this repo. See CHANGELOG.md.
PHA_NOTE = (
    "TODO for Joe: no roster in `tournament_results.json`. "
    "A 2026-10-23 note said this club's graphic names 25 distinct players, "
    "so the club was recorded with 25 cards. Confirm the roster before the club plays."
)


def load() -> dict:
    with RESULTS.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_announced() -> dict:
    with ANNOUNCED.open(encoding="utf-8") as handle:
        return json.load(handle)


def surname(name: str) -> str:
    token = name.replace(".", " ").split()[-1]
    return token.casefold()


def appearances(data: dict) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for team in data["teams"]:
        found[team["code"]] = {
            "lineup": {},
            "subs": [],
            "rotation": [],
            "bullpen": [],
            "seen": set(),
            "seen_ids": set(),
        }
    for game in data["games"]:
        for line in game["batting"]:
            bucket = found[line["team"]]
            bucket["seen"].add(surname(line["name"]))
            bucket["seen_ids"].add(line["player_id"])
            slot = line.get("lineup_slot")
            if line.get("is_substitute"):
                label = f"{line['name']} (`{line['player_id']}`), slot {slot}"
                if label not in bucket["subs"]:
                    bucket["subs"].append(label)
                continue
            if slot is None:
                continue
            bucket["lineup"].setdefault(slot, []).append(
                f"{line['name']} (`{line['player_id']}`) in {game['id']}"
            )
        starters_seen = {code: False for code in found}
        for line in sorted(game["pitching"], key=lambda item: item["appearance_order"]):
            bucket = found[line["team"]]
            bucket["seen"].add(surname(line["name"]))
            bucket["seen_ids"].add(line["player_id"])
            label = f"{line['name']} (`{line['player_id']}`)"
            if line["appearance_order"] == 1 and not starters_seen[line["team"]]:
                bucket["rotation"].append(f"{label} started {game['id']}")
                starters_seen[line["team"]] = True
                continue
            if any(item.startswith(label) for item in bucket["bullpen"]):
                continue
            bucket["bullpen"].append(f"{label}, first seen in {game['id']}")
    return found


def next_starts(data: dict) -> dict[str, list[str]]:
    notes: dict[str, list[str]] = {}
    for series in data["series"]:
        carry = series.get("carry") or {}
        pending = carry.get("rotation_next_start") or {}
        for code, name in pending.items():
            notes.setdefault(code, []).append(f"{series['id']}: next start {name}")
    return notes


def unseen(code: str, seen: set[str]) -> list[str]:
    canonical = CANONICAL.get(code)
    if not canonical:
        return []
    missing = []
    for group in ("lineup", "bench", "rotation", "bullpen"):
        for sur, label in canonical[group]:
            if sur.casefold() not in seen:
                missing.append(label)
    return missing


def section_list(title: str, lines: list[str]) -> list[str]:
    if not lines:
        return []
    block = [f"### {title}", ""]
    for line in lines:
        block.append(f"- {line}")
    block.append("")
    return block


def section_heading(roster: dict, key: str, fallback: str) -> str:
    custom = (roster.get("headers") or {}).get(key)
    return custom or fallback


def render_announced(lines: list[str], roster: dict) -> None:
    lines += [
        f"Manager: {roster['manager']}.",
        "",
        "Official roster provided by the tournament owner. The lines are copied from that card. No tournament stats were added. Peak 162 franchise lines are on the club page.",
        "",
        f"### {section_heading(roster, 'lineup', 'Lineup')}",
        "",
    ]
    for label in roster["lineup"]:
        lines.append(f"- {label}")
    lines += ["", f"### {section_heading(roster, 'bench', 'Bench')}", ""]
    for label in roster["bench"]:
        lines.append(f"- {label}")
    lines += ["", f"### {section_heading(roster, 'rotation', 'Rotation')}", ""]
    for label in roster["rotation"]:
        lines.append(f"- {label}")
    lines += ["", f"### {section_heading(roster, 'bullpen', 'Bullpen')}", ""]
    for label in roster["bullpen"]:
        lines.append(f"- {label}")
    lines.append("")
    honors = roster.get("honorable_mentions") or []
    if honors:
        title = "Honorable mentions"
        if roster.get("honorable_note"):
            title += f" ({roster['honorable_note']})"
        lines += [f"### {title}", ""]
        lines.append("These names are not on the active roster.")
        lines.append("")
        for label in honors:
            lines.append(f"- {label}")
        lines.append("")
    if roster.get("what_if"):
        lines += [
            f"### {roster.get('what_if_label') or 'What if'}",
            "",
            f"- {roster['what_if']}",
            "",
        ]


def render_team(team: dict, appeared: dict, pending: list[str], announced: dict) -> list[str]:
    code = team["code"]
    lines = [
        f"## {team['seed']}. {team['name']} ({code})",
        "",
        f"Bracket: {team.get('bracket', '—')}. Series losses: {team.get('losses', team['series_losses'])}. Full 26 Index: {team['index']}.",
        "",
    ]
    if code in ("PHA", "MON"):
        lines += [
            "The Full 26 Index stored for this club is a calibrated estimate. See TOURNAMENT_SEEDS.md.",
            "",
        ]
    canonical = CANONICAL.get(code)
    if canonical:
        lines += [
            f"Manager: {canonical['manager']}.",
            "",
            "This roster text is the one previously published in the tournament rules. Positions are from that text. The results file does not record positions.",
            "",
            "### Lineup",
            "",
        ]
        for _sur, label in canonical["lineup"]:
            lines.append(f"- {label}")
        lines += ["", "### Bench", ""]
        for _sur, label in canonical["bench"]:
            lines.append(f"- {label}")
        lines += ["", "### Rotation", ""]
        for _sur, label in canonical["rotation"]:
            lines.append(f"- {label}")
        lines += ["", "### Bullpen", ""]
        for _sur, label in canonical["bullpen"]:
            lines.append(f"- {label}")
        lines.append("")
        missing = unseen(code, appeared["seen"])
        if missing:
            lines += [
                "Recorded on that roster and not yet in a box score:",
                "",
            ]
            for label in missing:
                lines.append(f"- {label}")
            lines.append("")
    elif code in announced:
        render_announced(lines, announced[code])
    elif code == "PHA":
        lines += [PHA_NOTE, ""]
    elif not appeared["lineup"] and not appeared["rotation"]:
        lines += [
            "TODO for Joe: no roster in `tournament_results.json`. Lineup, bench, rotation, and bullpen are unrecorded until this club plays or the graphic is added.",
            "",
        ]

    if code == "ARI":
        lines += [
            "### Approved active roster amendment (2026-10-26)",
            "",
            "David Peralta (`peralda01`) joins the sixth bench spot as a left-handed outfielder (LF). Juan Cruz (`cruzju02`) leaves the active bullpen. The active 26 now have 9 lineup players, 6 bench players, 5 starting pitchers, and 6 relievers.",
            "",
            "The amendment is for games after R1-04 only. Cruz's appearances below, original converted card (if on file), and all game results remain historical records. Peralta's frozen Hitter v0.5 conversion is pending and no card ratings are assumed. Active personnel are listed in `data/rosters.json`.",
            "",
        ]

    if appeared["lineup"] or appeared["rotation"] or appeared["bullpen"] or appeared["subs"]:
        lines += ["### Players in the results file", ""]
        if not canonical and code not in announced:
            lines.append("Positions are not in the results file. TODO for Joe: positions, manager, and anyone who has not appeared.")
            lines.append("")
        lineup_lines = []
        for slot in sorted(appeared["lineup"]):
            # First game establishes the slot; later games are the same check.
            first = appeared["lineup"][slot][0]
            extra = len(appeared["lineup"][slot]) - 1
            suffix = f" (same starter in {extra} later game{'s' if extra != 1 else ''})" if extra else ""
            # Only claim "same starter" when every entry is the same player id.
            ids = {item.split("`")[1] for item in appeared["lineup"][slot]}
            if len(ids) == 1:
                lineup_lines.append(f"Slot {slot}: {first}{suffix}")
            else:
                lineup_lines.append(f"Slot {slot}: " + "; ".join(appeared["lineup"][slot]))
        lines += section_list("Lineup slots that have batted", lineup_lines)
        lines += section_list("Substitutes who have batted", appeared["subs"])
        lines += section_list("Starts, in the order the games were played", appeared["rotation"])
        lines += section_list("Relievers who have appeared", appeared["bullpen"])
    if pending:
        lines += section_list("Rotation carry recorded on the series", pending)
    return lines


def build() -> str:
    data = load()
    announced = load_announced()
    appeared = appearances(data)
    pending = next_starts(data)
    parts = [
        "# Payoff Pitch Tournament 32 — Rosters",
        "",
        "Generated by `scripts/build_rosters.py`. This file is the roster record. The rules point here.",
        "",
        "Three sources are in use, and they are labeled:",
        "",
        "- Yankees and Marlins: the roster text previously published in the rules, including players who have not appeared.",
        "- Clubs in `data/announced_rosters.json`: the owner's card, copied line for line. A bench or a bullpen is listed as given, even when the count is not five or seven. Honorable mentions are a separate list and are not on the active roster. No graphic cards were made from these lines.",
        "- Everyone who has played: the batting and pitching lines in `tournament_results.json`. A player who has not appeared is absent from that extract.",
        "",
        "The October 2026 Yankees–Marlins exhibition used different lineups and pitcher pools. It is not the tournament roster. History of that exhibition is in `CHANGELOG.md`.",
        "",
        "Reynolds (Yankees) and Burnett (Marlins) are bullpen arms in the swing and long roles. They are relievers. The starters-never-relieve rule does not bar them from pitching in relief.",
        "",
        "## Roster status",
        "",
        "| Seed | Code | Team | Record |",
        "|---:|---|---|---|",
    ]
    for team in sorted(data["teams"], key=lambda item: item["seed"]):
        code = team["code"]
        showed = appeared[code]
        if code in CANONICAL:
            record = "Roster text on file, plus game appearances"
        elif code in announced:
            record = "Official roster, plus game appearances" if showed["lineup"] or showed["rotation"] else "Official roster"
        elif showed["lineup"] or showed["rotation"]:
            record = "Appearances only"
        else:
            record = "Unrecorded"
        parts.append(f"| {team['seed']} | {code} | {team['name']} | {record} |")
    parts += ["", ""]
    for team in sorted(data["teams"], key=lambda item: item["seed"]):
        parts += render_team(team, appeared[team["code"]], pending.get(team["code"], []), announced)
    return "\n".join(parts).rstrip() + "\n"


def main() -> None:
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
