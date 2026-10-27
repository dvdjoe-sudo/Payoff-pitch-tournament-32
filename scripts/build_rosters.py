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
            ("Jeter", "1 Derek Jeter SS"),
            ("Judge", "2 Aaron Judge RF"),
            ("Ruth", "3 Babe Ruth DH"),
            ("Gehrig", "4 Lou Gehrig 1B"),
            ("Mantle", "5 Mickey Mantle LF"),
            ("DiMaggio", "6 Joe DiMaggio CF"),
            ("Rodriguez", "7 Alex Rodriguez 3B"),
            ("Berra", "8 Yogi Berra C"),
            ("Randolph", "9 Willie Randolph 2B"),
        ],
        "bench": [
            ("Munson", "Thurman Munson (C2)"),
            ("Lazzeri", "Tony Lazzeri (IF/BAT)"),
            ("Mattingly", "Don Mattingly (1B/BAT)"),
            ("Williams", "Bernie Williams (OF)"),
            ("Jackson", "Reggie Jackson (OF/BAT)"),
        ],
        "rotation": [
            ("Ford", "Whitey Ford"),
            ("Ruffing", "Red Ruffing"),
            ("Gomez", "Lefty Gomez"),
            ("Guidry", "Ron Guidry"),
            ("Pettitte", "Andy Pettitte"),
        ],
        "bullpen": [
            ("Rivera", "Mariano Rivera (CL)"),
            ("Gossage", "Goose Gossage (FIRE)"),
            ("Lyle", "Sparky Lyle (LH FIRE)"),
            ("Robertson", "David Robertson (RH SET)"),
            ("Righetti", "Dave Righetti (LATE/MULTI)"),
            ("Stanton", "Mike Stanton (LH SPEC)"),
            ("Reynolds", "Allie Reynolds (LONG/SWING)"),
        ],
    },
    "MIA": {
        "manager": "Jack McKeon",
        "lineup": [
            ("Castillo", "1 Luis Castillo 2B"),
            ("Yelich", "2 Christian Yelich CF"),
            ("Sheffield", "3 Gary Sheffield DH"),
            ("Stanton", "4 Giancarlo Stanton RF"),
            ("Cabrera", "5 Miguel Cabrera 3B"),
            ("Ramirez", "6 Hanley Ramirez SS"),
            ("Floyd", "7 Cliff Floyd LF"),
            ("Conine", "8 Jeff Conine 1B"),
            ("Realmuto", "9 J.T. Realmuto C"),
        ],
        "bench": [
            ("Johnson", "Charles Johnson (C2)"),
            ("Lopez", "Otto Lopez (UTIL)"),
            ("Uggla", "Dan Uggla (INF/POWER)"),
            ("Ozuna", "Marcell Ozuna (OF4)"),
            ("Lee", "Derrek Lee (1B/POWER)"),
        ],
        "rotation": [
            ("Johnson", "Josh Johnson"),
            ("Alcantara", "Sandy Alcantara"),
            ("Willis", "Dontrelle Willis"),
            ("Beckett", "Josh Beckett"),
            ("Fernandez", "Jose Fernandez"),
        ],
        "bullpen": [
            ("Nen", "Robb Nen (CL)"),
            ("Cishek", "Steve Cishek (SU)"),
            ("Ramos", "A.J. Ramos (SU)"),
            ("Scott", "Tanner Scott (LH)"),
            ("Bender", "Anthony Bender (MR)"),
            ("Alfonseca", "Antonio Alfonseca (MR)"),
            ("Burnett", "A.J. Burnett (LR/EMER SP)"),
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

    if code == "HOU":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "Moisés Alou (`aloumo01`) becomes Houston bench hitter #6 (right-handed corner outfielder, LF/RF), replacing Octavio Dotel (`doteloc01`) on the active 26. **Only Alou's Houston Astros seasons 1998, 2000 and 2001 count** for his prime and Peak 162, excluding his entire non-Houston career and the 1999 injury season. The official Houston roster is now 9 starting hitters, 6 bench hitters, 5 starters and 6 relievers: 26 unique active players.",
            "",
            "Joe Sambito moves to bullpen spot 5 and Dave Smith to spot 6, retaining their left-handed and late relief roles. All previously converted cards (including Dotel and Alou's separate Montreal record), old games, scores, original dice/FAC logs, box scores and prior tournament results remain untouched. Houston Alou's genuine frozen Hitter v0.5 playable card requires its own Astros-only conversion; no guessed card values are supplied.",
            "",
        ]

    if code == "SD":
        lines += [
            "### Approved Padres DH and 3B position eligibility correction (2026-10-27)",
            "",
            "Ken Caminiti (`caminke01`) is the **starting DH in batting-order slot 4**, with **eligible positions 3B/DH** (third base and designated hitter). Manny Machado (`machama01`) remains the **starting third baseman batting sixth**. Caminiti may be assigned to play 3B when needed; his starting role on this announced roster remains DH. The owner-announced original lineup card already lists Caminiti as DH.",
            "",
            "No personnel, batting-order, rotation, bench or bullpen changes were authorized: San Diego remains **9 lineup / 6 bench / 5 starting pitchers / 6 relievers** with **26 distinct active players**. This is position metadata only. All original historical cards, previously played games, box scores, scores, FAC/dice rolls and tournament results are unchanged.",
            "",
        ]
    if code == "COL":
        lines += [
            "### Approved Colorado active-roster amendment (2026-10-27; future games only)",
            "",
            "Carlos González (`gonzaca01`) replaces Ian Desmond (`desmoia01`) as **Colorado Rockies bench hitter #5**, a **left-handed outfield reserve (LF/CF/RF)**. González is evaluated **only from his Colorado Rockies 2009–2018 seasons**, excluding Oakland and Cleveland. The change is approved **only for games after the already-played R1-05 series**. Desmond leaves the **active 26** but his authentic converted historical card remains archived; prior appearances, if any, still count as historical records.",
            "",
            "Colorado keeps the entire nine-man starting batting order, including Andrés Galarraga **starting at DH batting ninth**, all five rotation pitchers, all six bullpen pitchers and the other five bench hitters. The active roster stays **9 lineup / 6 bench / 5 rotation / 6 bullpen**, 26 distinct players. All prior game results, scores, standings, original box scores, FAC/dice roll logs and historical converted cards remain unchanged.",
            "",
            "González's verified Colorado-only Peak 162 display is awaiting a Lahman generator rebuild and his genuine frozen **Hitter v0.5** playable conversion remains pending; **no fabricated dice ratings or statistics** are published.",
            "",
        ]
    if code == "TOR":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "Joe Carter (`cartejo01`) joins the **Toronto Blue Jays** active 26 as **sixth bench hitter**, a right-handed pinch-hit power option and **RF/LF outfield reserve**. His franchise-specific Peak 162 and future authentic Hitter v0.5 card must count **only Toronto seasons 1991–1997**, excluding his earlier Cleveland, San Diego and subsequent Baltimore and San Francisco years.",
            "",
            "Jim Clancy (`clancji01`) leaves the active bullpen, while his authentic converted pitcher card remains in the historical card archive. The six relief pitchers remain in their previous order: **Tom Henke, Mark Eichhorn, Duane Ward, Roberto Osuna, Scott Downs and Paul Quantrill**. All **nine starting hitters and five rotation pitchers are unchanged**, including **José Bautista starting at DH batting fifth**. Toronto has **9 lineup / 6 bench / 5 rotation / 6 bullpen**, 26 distinct active players.",
            "",
            "All historical cards, prior box scores, completed games, FAC/dice logs and tournament results remain unchanged. Carter's verified Toronto-only **Peak 162** covers **1991–1995** (Lahman): 162 G, 168 H, 34 HR, 118 RBI, 14 SB, .263/.314/.488/.802. His frozen authentic **Hitter v0.5** playable card conversion remains pending; no simulated card ratings were invented.",
            "",
        ]
    if code == "TEX":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "Rubén Sierra (`sierrru01`) joins the **Texas Rangers** active 26 as **sixth bench hitter**, a switch-hitting pinch-hit power option and **right-field / corner-outfield reserve**. Only his **Texas Rangers franchise seasons (1986–1992, 2000–2001, 2003)** qualify, never Oakland, New York, Detroit, Toronto, Cincinnati, Chicago, Seattle or Minnesota statistics.",
            "",
            "Kenny Rogers (`rogerke01`) leaves the **active bullpen** but keeps any existing original historical converted pitcher card. Darold Knowles advances from RP7 to **RP6**; the other five active relievers stay **John Wetteland, Neftalí Feliz, Jeff Zimmerman, Jim Kern and Jeff Russell**. **The entire starting nine and five-man rotation remain unchanged, including Corey Seager starting at DH batting ninth**. The Rangers now have **9 lineup / 6 bench / 5 rotation / 6 bullpen** with 26 unique players.",
            "",
            "All original historical player cards, completed games, box scores, FAC/dice logs and tournament results remain unchanged. Sierra's verified Texas Rangers-only **Peak 162** uses seasons **1989–1992 and 2000** (Lahman): 162 G, 186 H, 22 HR, 106 RBI, .292/.338/.477/.815. His genuine frozen **Hitter v0.5** playable card remains pending authentic conversion; **no invented dice ratings** have been supplied. PED eligibility questions remain separate.",
            "",
        ]
    if code == "MIL":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "Ben Oglivie (`oglivbe01`) joins the **Milwaukee Brewers** active 26 as **sixth bench hitter**, a left-handed pinch-hit power option and **left-field / corner-outfield reserve**. Only his **Milwaukee Brewers seasons (1978–1986)** qualify; all Boston and Detroit statistics are excluded from his future Peak 162 and authentic Hitter v0.5 conversion.",
            "",
            "Freddy Peralta (`peralfr01`) leaves the active bullpen but keeps his original authentic historical converted pitcher card. The remaining six relievers are **Josh Hader, Devin Williams, Rollie Fingers, Dan Plesac, Ken Sanders and Jeremy Jeffress**, in the same RP1–RP6 order. The **entire starting nine, Prince Fielder at DH batting fourth, and five starting pitchers stay unchanged**. The active roster has **9 lineup / 6 bench / 5 rotation / 6 bullpen** and 26 unique players.",
            "",
            "All historical cards, played games, box scores, results and FAC/dice logs remain unchanged. Oglivie's verified Milwaukee-only five-year Peak 162 display uses **1978–1982** (Lahman). His playable **Hitter v0.5** card remains pending authentic conversion; **no fabricated dice ratings** are published. Any PED eligibility discussion is separate.",
            "",
        ]
    if code == "OAK":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "Eric Chavez (`chaveer01`) joins the **Oakland Athletics** active roster as **sixth bench hitter**, a left-handed pinch-hit option and **third-base defensive reserve**. His Peak 162, and the eventual frozen Hitter v0.5 card, count **only his Oakland Athletics seasons (1998–2010)**; New York Yankees and Arizona Diamondbacks statistics never qualify.",
            "",
            "Gene Nelson (`nelsoge01`) leaves the active bullpen, but his original authentic pitcher card stays in the historical card catalog. Rick Honeycutt shifts from RP7 to RP6, with the other five relievers still Dennis Eckersley, Rollie Fingers, Andrew Bailey, Sean Doolittle and Liam Hendriks. **All nine hitters and five starting pitchers remain exactly unchanged**, including **José Canseco starting at DH batting fifth**. The roster has **9 lineup / 6 bench / 5 rotation / 6 bullpen**, 26 unique active players.",
            "",
            "This approval does **not** resolve the separate PED eligibility discussion and does not authorize removing or changing any starting hitter. All original historical player cards, completed games, original box scores, dice/FAC logs and results remain unchanged. Chavez's authentic Oakland-only playable **Hitter v0.5** conversion is pending and must not be fabricated.",
            "",
        ]

    if code == "NYM":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "Howard Johnson (`johnsho01`) becomes the **sixth bench hitter** for the New York Mets, providing switch-hitting power, speed and 3B/infield reserve coverage. **Only his 1985–1993 New York Mets seasons count**, excluding his earlier Detroit and subsequent Colorado/Chicago franchises. Sid Fernandez (`fernasi01`) becomes inactive in the bullpen and keeps his original genuine historical pitching card. The six active relievers stay in their existing sequence: Billy Wagner, Edwin Díaz, Armando Benítez, Tug McGraw, John Franco and Jesse Orosco.",
            "",
            "The entire starting nine and five-man rotation stay unchanged. **Pete Alonso remains the starting DH batting sixth**, while **John Olerud remains bench #5**. The owner-approved active roster now has **9 lineup / 6 bench / 5 rotation / 6 bullpen** and 26 distinct players.",
            "",
            "This prospective roster amendment preserves the original archive of every historical card, completed game, box score, final score and FAC/dice roll. Howard Johnson's authentic Mets-only frozen Hitter v0.5 playable conversion is **pending**; no fabricated dice-table numbers, percentage bands or fielding ratings are introduced.",
            "",
        ]

    if code == "LAA":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "Rod Carew (`carewro01`) joins the Angels' bench in **slot 6**, as a left-handed contact / pinch hitter and **backup first baseman**. Only his **1979–1985 California Angels seasons** count for the franchise-specific Peak 162 and eventual frozen Hitter v0.5 card. His Minnesota Twins seasons and accomplishments do **not** count.",
            "",
            "Doug Corbett (`corbedo01`) leaves the active bullpen, but his original converted pitcher card remains preserved in the historical catalog. The other six relievers retain their identities and responsibilities: Troy Percival (RP1), Francisco Rodríguez (RP2), Scot Shields (RP3), Bryan Harvey (RP4), Scott Downs (RP5), Darren Oliver (RP6). All nine starters and five rotation pitchers remain unchanged; **Shohei Ohtani is still the starting DH batting first**. The Angels' roster totals **9 lineup / 6 bench / 5 starting pitchers / 6 relievers**, exactly 26 different players.",
            "",
            "Existing original cards and played games, results, box scores, scoresheets, FAC and dice-roll logs are unchanged. Carew's authentic California Angels-only playable Hitter v0.5 conversion is **pending**; do not invent ratings or dice-chart results.",
            "",
        ]

    if code == "SEA":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "Adrián Beltré (`beltrad01`) joins the **Seattle Mariners** active 26 in sixth bench slot as a **third-base defensive reserve and right-handed pinch hitter**. Only his **2005–2009 Seattle Mariners seasons** count toward his franchise-specific peak and eventual frozen Hitter v0.5 conversion. All Dodgers, Red Sox and Rangers seasons are excluded.",
            "",
            "Mike Moore (`mooremi01`) becomes inactive; his original converted card stays in the historical archive. The six remaining relievers retain their existing sequence and responsibilities, now assigned RP1–RP6: J.J. Putz, Andrés Muñoz, Edwin Díaz, Jeff Nelson, Arthur Rhodes and Kazuhiro Sasaki. The entire nine-man starting batting order and all five starting pitchers remain unchanged, including **Edgar Martínez batting fourth as DH**. Seattle's active split is **9 lineup / 6 bench / 5 rotation / 6 bullpen**, 26 distinct players.",
            "",
            "All previously created player cards and previously played games, scores, box scores, original dice/FAC logs and results remain untouched. Beltré's authentic Seattle-only Hitter v0.5 playable card is pending conversion: no unverified percentile bands, defensive ratings or dice-chart numbers have been introduced.",
            "",
        ]

    if code == "KC":
        lines += [
            "### Approved active roster amendments (2026-10-27)",
            "",
            "Danny Tartabull (`tartada01`) becomes the **starting designated hitter batting second**, replacing Hal McRae (`mcraeha01`) in lineup slot 2. McRae takes Tartabull's former bench slot 5 as the veteran right-handed DH/pinch-hit option. The remaining eight lineup spots and the entire five-man starting rotation are unchanged.",
            "",
            "John Mayberry (`maybejo01`) joins Kansas City's bench as sixth reserve (left-handed 1B / pinch hitter), and Charlie Leibrandt (`leibrch01`) moves off the active bullpen. Mayberry's conversion and franchise peak use **only Kansas City Royals seasons 1972–1977**, excluding the rest of his career. The Royals now have **9 lineup / 6 bench / 5 rotation / 6 bullpen**, 26 unique players; Steve Mingori remains the left-handed relief specialist at RP6.",
            "",
            "These approvals are prospective only. All genuine original card bodies, including Leibrandt's existing converted pitching card and the original McRae/Tartabull cards, remain historical and unaltered. Every completed tournament game, result, box score and FAC/dice log remains unchanged. Mayberry's authentic frozen Hitter v0.5 playable conversion is pending; no guessed percentile bands, ratings or dice charts have been created.",
            "",
        ]

    if code == "PHA":
        lines += [
            "### Approved active roster amendments (2026-10-27)",
            "",
            "Jimmie Foxx (`foxxji01`) is now the **designated hitter**, and Ferris Fain (`fainfe01`) plays **first base**; their original lineup slots (4 and 9), all nine hitters and all five starting pitchers remain the same. This is a position swap only, with no new batting figures, fielding values or invented card ratings.",
            "",
            "Bobby Shantz (`shantbo01`), a left-handed pitcher, joins the active bullpen as sixth arm in the **long/swing relief role**, replacing reserve shortstop Jack Barry (`barryja01`). **Only Shantz's Philadelphia Athletics seasons 1949–1954 count; no Kansas City or New York years qualify.** Max Bishop shifts to reserve slot 5 and Elmer Valo to slot 6. The active count is now **9 lineup / 6 bench / 5 rotation / 6 bullpen**, 26 unique players.",
            "",
            "Barry's original converted card stays in the historical card catalog, and the original card bodies, scores, finished games, box scores, dice/FAC logs and tournament results are preserved unchanged. Shantz's genuine **Pitcher v0.2.3** playable conversion is pending; he may not be used in a game until the frozen-engine card is available. Because his Philadelphia peak includes substantial starting work, the display-only Peak 162 numbers are not a relief-only projection and must not be treated as an invented relief card.",
            "",
        ]

    if code == "BAL":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "George Sisler (`sislege01`) joins Baltimore franchise bench #6 (LH first baseman and pinch-hitting option) in place of Sammy Stewart (`stewasa01`), who becomes inactive. Sisler's qualifying and peak statistics use **only his St. Louis Browns seasons (1915–1927)**, not any years with Washington or the Boston Braves. The Orioles' current active 26 are 9 lineup hitters, 6 bench players, 5 rotation starters and 6 bullpen pitchers.",
            "",
            "The six remaining relievers are Gregg Olson, Zach Britton, Félix Bautista, Stu Miller, Dick Hall and Tippy Martinez. Their roles and slots do not change. The original Sammy Stewart converted pitcher card, archived cards for all players, previous games, scores, dice/FAC records and box scores remain historical and unchanged. Sisler's genuine frozen Hitter v0.5 playable conversion remains pending; no dice-chart ratings are invented.",
            "",
        ]

    if code == "CWS":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "Dick Allen (`allendi01`) joins Chicago's active bench as BAT2 / RH 1B-DH #6. Bob Locker (`lockebo02`) is inactive from the bullpen. The White Sox now carry 9 lineup hitters, 6 bench hitters, 5 starting pitchers and 6 relievers: 26 unique active players.",
            "",
            "Dámaso Marte moves to relief slot 5 and Eddie Cicotte to relief slot 6, retaining their original specialist and long/swing responsibilities. This amendment is for future games only. All historical converted cards (including Locker), original FAC/dice rolls, box scores, recorded games, tournament results and earlier decisions remain untouched. Allen requires a genuine White Sox-franchise-only Hitter v0.5 playable conversion, which has not been invented.",
            "",
        ]

    if code == "MIN":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "Bob Allison (`allisbo01`) joins Minnesota's active 26 as sixth bench hitter (RH power, OF/1B). Firpo Marberry (`marbefi01`) leaves the active bullpen. The team now has 9 lineup players, 6 bench hitters, 5 starting pitchers and 6 relievers, 26 distinct players.",
            "",
            "Jhoan Duran, Taylor Rogers and Jim Perry move to bullpen slots 4, 5 and 6 respectively without changing their roles. This amendment affects future games only and does not edit any original player cards, archived Firpo Marberry conversion, FAC/dice rolls, box scores, completed games or historical tournament results. Bob Allison's genuine Hitter v0.5 card and Senators/Twins franchise-only peak line require an authentic conversion; no playable card ratings are invented.",
            "",
        ]

    if code == "PHI":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "Chuck Klein (`kleinch01`) is Philadelphia's approved sixth bench bat (left-handed RF/LF). Ryan Madson (`madsory01`) is inactive. The current Phillies roster is 9 starting hitters, 6 bench players, 5 starting pitchers and 6 relievers, 26 unique active players.",
            "",
            "Tug McGraw, Ron Reed, Brad Lidge and Ranger Suárez move into bullpen slots 3, 4, 5 and 6 respectively, without changing their pitching roles. This amendment applies to future games only. Every earlier original converted card, including Madson's, and all tournament games, results, box scores and dice/FAC logs remain untouched. Klein's playable frozen Hitter v0.5 conversion will use Phillies-franchise seasons only and remains pending; no card numbers or ratings are invented.",
            "",
        ]

    if code == "PIT":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "Paul Waner (`wanerpa01`) joins Pittsburgh's active bench as BAT2 / left-handed RF-LF #6. Al McBean (`mcbeaal01`) is removed from the active bullpen. The Pirates now carry 9 lineup hitters, 6 bench hitters, 5 starters and 6 relief pitchers, 26 distinct active players.",
            "",
            "Grant Jackson shifts to bullpen slot 5 and Sam Leever to bullpen slot 6, preserving their left-handed-specialist and long-relief roles. This owner-approved roster switch applies to future tournament games only. All original player cards (including Al McBean's), previous games, box scores, FAC/dice logs and recorded results are unchanged. Waner's genuine Hitter v0.5 playable card requires a Pittsburgh-franchise-only conversion; no chart or card ratings have been invented.",
            "",
        ]

    if code == "ATL":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "Bob Horner (`hornebo01`) joins Atlanta as bench BAT2/3B/1B #6, replacing Mark Wohlers (`wohlema01`) on the active pitching staff. Phil Niekro remains the long-relief/emergency-start option. The active 26 are 9 lineup hitters, 6 bench players, 5 starters and 6 bullpen pitchers.",
            "",
            "Jonny Venters moves to bullpen slot 5 and Phil Niekro to slot 6; their roles are unchanged. This amendment applies to future tournament games only. All authentic earlier cards (including Wohlers's), completed games and original dice/FAC records remain historical and unchanged. Horner's authentic playable Hitter v0.5 conversion must use Braves franchise seasons only; no invented card numbers have been supplied.",
            "",
        ]

    if code == "DET":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "Kirk Gibson (`gibsoki01`) joins Detroit's sixth active bench spot as OF/pinch-runner. Tyler Holton (`holtoty01`) moves off the active bullpen. The Tigers now have 9 lineup players, 6 bench players, 5 starting pitchers and 6 relief pitchers: 26 distinct active players.",
            "",
            "The amendment takes effect only after the completed R1-04 Detroit–Arizona series. All six original games, results, box scores, dice/FAC and manager logs, and all existing player cards (including Holton's converted card) remain historical records. Gibson's playable frozen Hitter v0.5 card requires an authentic Tigers-franchise-only conversion; no unverified card ratings or prime-window figures are generated. Dizzy Trout and Denny McLain move to bullpen slots 5 and 6 without changing their pitching roles.",
            "",
        ]

    if code == "SF":
        lines += [
            "### Approved active roster amendment (2026-10-27)",
            "",
            "Monte Irvin (`irvinmo01`) joins the sixth active Giants bench spot as a left fielder. Javier López (`lopezja02`) is removed from the active bullpen. The Giants now carry 9 starting hitters, 6 bench hitters, 5 starting pitchers, and 6 relievers (26 total).",
            "",
            "This amendment is effective only after the completed R1-02 Giants–Nationals series. All previously played games, historical converted cards (including Javier López), box scores, official results, dice/FAC records and bullpen appearances remain unchanged. Monte Irvin's original Hitter v0.5 card and Giants-only prime-window stats are pending genuine conversion; no ratings have been invented.",
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

    if code == "TB":
        lines += [
            "### Approved active roster amendment (2026-10-26)",
            "",
            "Aubrey Huff (`huffau01`) joins the active roster as bench OF6 (corner infield/outfield/DH). Kevin Kelly (`kellyke02`) moves off the active bullpen. This makes the active club 9 lineup / 6 bench / 5 starting pitchers / 6 relievers, 26 total.",
            "",
            "This approval applies only after R1-03. Previous game results, box scores, FAC/dice records and historical converted Kevin Kelly card are preserved. Huff's frozen Hitter v0.5 Payoff Pitch card remains pending user conversion; use Tampa Bay franchise seasons only. Active slots are in `data/rosters.json`.",
            "",
        ]

    if code == "WSH":
        lines += [
            "### Approved active roster amendment (2026-10-26)",
            "",
            "Jayson Werth (`werthja01`) joins Washington as bench OF6 (RF/LF/DH). Craig Stammen (`stammcr01`) leaves the active bullpen. The Nationals now carry 9 lineup players, 6 bench players, 5 starting pitchers, and 6 relievers, 26 total.",
            "",
            "The roster change applies only after R1-02. Stammen's original converted card (if on file), historical pitching appearances, box scores, dice/FAC records, series results and all other completed games remain unchanged. Werth's original frozen Hitter v0.5 card conversion is still pending, using **Washington franchise seasons only**. Current roster spots are in `data/rosters.json`.",
            "",
        ]

    if code == "NYY":
        lines += [
            "### Franchise cards (2026-10-27)",
            "",
            "The active 26 are the approved franchise-card roster: 9 lineup, 5 bench, 5 starters, and 7 relievers. Mike Stanton (`stantmi02`) is the left-handed specialist. Rickey Henderson is not on the active roster. Played R1-01 results are unchanged.",
            "",
        ]

    if code == "MIA":
        lines += [
            "### Franchise cards (2026-10-27)",
            "",
            "The active 26 are the approved franchise-card roster: 9 lineup, 5 bench, 5 starters, and 7 relievers. A.J. Burnett (`burneaj01`) is the long/emergency starter. Otto Lopez (`lopezot01`) is the utility bench player. Juan Pierre is not on the active roster. Played R1-01 results are unchanged.",
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
