#!/usr/bin/env python3
"""Build data/peak162.json from the Lahman database and the owner's cards.

Peak 162 is a display line. It does not change a tournament box score.
Lahman has no WAR, so the window is chosen by league OPS+ for hitters and
by ERA+ times innings for pitchers. The club lists and the formula are
documented in MODELS.md.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import tarfile
import unicodedata
import urllib.request
import warnings
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import rdata

warnings.filterwarnings("ignore", message="Missing constructor for R class")

ROOT = Path(__file__).resolve().parents[1]
ROSTERS = ROOT / "data" / "announced_rosters.json"
RESULTS = ROOT / "tournament_results.json"
OUT = ROOT / "data" / "peak162.json"
LAHMAN_URL = "https://cran.r-project.org/src/contrib/Lahman_14.0-0.tar.gz"
LAHMAN_SHA256 = "48d05d6ffafb977846b14cfb273d2faf21b5519604cbb337792cb3ec8d25dd31"
CACHE = Path("/tmp/lahman/Lahman.tar.gz")

# Team IDs are the franchise seasons that count for that tournament club.
# Philadelphia and Oakland are separate clubs. Montreal and Washington are
# separate clubs. Washington has already played, so it is not in the roster
# file and gets no peak line.
FRANCHISE = {
    "COL": {"COL"},
    "LAD": {"BR3", "BRO", "LAN"},
    "SD": {"SDN"},
    "LAA": {"LAA", "CAL", "ANA"},
    "HOU": {"HOU"},
    "OAK": {"OAK", "ATH"},
    "SEA": {"SEA"},
    "TEX": {"WS2", "TEX"},
    "ATL": {"BSN", "ML1", "ATL"},
    "DET": {"DET"},
    "PHI": {"PHI"},
    "MON": {"MON"},
    "BAL": {"MLA", "SLA", "BAL"},
    "NYM": {"NYN"},
    "CWS": {"CHA"},
    "MIL": {"SE1", "ML4", "MIL"},
    "MIN": {"WS1", "MIN"},
    "PIT": {"PT1", "PIT"},
    "TOR": {"TOR"},
    "KC": {"KCA"},
    "NYY": {"NYA"},
    "MIA": {"FLO", "MIA"},
    "CHC": {"CHN"},
    "CLE": {"CLE"},
    "CIN": {"CN2", "CIN"},
    "STL": {"SL4", "SLN"},
    "PHA": {"PHA"},
}
YEAR_BOUNDS = {
    "PHA": (1901, 1954),
    "MON": (1969, 2004),
    "OAK": (1968, 2025),
}
# The Yankees and Marlins have already played. The owner confirmed the
# full names after those games, and the card ids have to match the box scores.
FROZEN = {"WSH", "BOS", "TB", "ARI", "SF"}
# Alou had only 14 games with Montreal in 1990; his owner-approved
# representative five-season window is 1992-1996, without that cameo.
HITTER_WINDOW_EXCLUDE = {("MON", "aloumo01"): {1990}}
# Lahman stores him as Charles Bender. The card says Chief. He is the only
# Bender on the 1901-1954 Athletics.
MANUAL = {
    # Lahman lists him as Charles Bender. The card says Chief. He is the
    # only Bender on the 1901-1954 Athletics.
    ("PHA", "chief bender"): "bendech01",
    # The card says Zach. Lahman spells him Zack. brittza01 is that pitcher.
    ("BAL", "zach britton"): "brittza01",
    # The card does not say Jr. walshed02 is the son, and both pitched
    # for the White Sox. The rotation ace is Edward Augustine Walsh.
    ("CWS", "ed walsh"): "walshed01",
    # The box scores already use these ids. The other man with the name
    # is a different player, or the Lahman spelling does not match the line.
    ("NYY", "goose gossage"): "gossari01",
    ("NYY", "mike stanton"): "stantmi02",
    ("NYY", "david robertson"): "roberda08",
    ("NYY", "bernie williams"): "willibe02",
    ("NYY", "reggie jackson"): "jacksre01",
    ("NYY", "allie reynolds"): "reynoal01",
    ("NYY", "alex rodriguez"): "rodrial01",
    ("MIA", "giancarlo stanton"): "stantmi03",
    ("MIA", "josh johnson"): "johnsjo09",
    ("MIA", "charles johnson"): "johnsch04",
    ("MIA", "luis castillo"): "castilu01",
    ("MIA", "otto lopez"): "lopezot01",
    ("MIA", "anthony bender"): "bendean01",
    ("MIA", "tanner scott"): "scottta01",
    ("MIA", "jose fernandez"): "fernajo02",
    ("MIA", "a j ramos"): "ramosaj01",
    ("MIA", "a j burnett"): "burneaj01",
    ("MIA", "hanley ramirez"): "ramirha01",
}

POSITION = {
    "c", "1b", "2b", "3b", "ss", "lf", "cf", "rf", "dh", "of", "if", "p",
    "ut", "util", "inf", "ph", "pr", "ci", "mi", "mif", "flex", "sp", "cl",
    "su", "mr",
}
ROLE = {
    "sp1", "sp2", "sp3", "sp4", "sp5", "sp6", "cl1", "cl2", "su1", "su2",
    "mr1", "mr2", "mr3", "c2", "of2", "of3", "of4", "of5", "if2", "bat",
    "bat2", "mid1", "lhs", "lhp", "rhp", "lr", "utl", "4th", "rh", "lh",
    "set", "stop", "brg", "fire", "fireman", "pwr", "def", "spec", "fr", "high",
    "lev", "emer", "swing", "multi", "mid", "util", "flex", "1a",
}
CAPS_ONLY = {"long", "late"}
DESCRIPTORS = {
    "utility", "defense", "bat", "power", "veteran", "elite", "listed",
    "honorable", "mention", "bullpen", "card", "stats", "shown",
}
ROLE_RE = re.compile(r"^(?:sp|cl|su|mr|of|if|c|bat|mid)\d+[a-z]?$")
SLOT_RE = re.compile(r"^\d+[ab]$")
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def half_up_div(total: int, numer: int, denom: int) -> int:
    if denom <= 0:
        return 0
    value = Decimal(int(total)) * Decimal(int(numer)) / Decimal(int(denom))
    return int(value.to_integral_value(rounding=ROUND_HALF_UP))


def quantize(numer, denom, places: int):
    if denom <= 0:
        return None
    return (Decimal(numer) / Decimal(denom)).quantize(
        Decimal(10) ** -places, rounding=ROUND_HALF_UP
    )


def fmt_quant(number, places: int, drop_lead: bool = False) -> str:
    if number is None:
        return "—"
    text = f"{number:.{places}f}"
    if drop_lead and text.startswith("0."):
        return text[1:]
    return text


def strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text))
    return "".join(char for char in text if not unicodedata.combining(char))


def norm_name(text: str) -> str:
    text = strip_accents(text).lower().replace(".", " ")
    text = text.replace("'", "").replace("’", "").replace("-", " ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def pop_suffix(name: str) -> tuple[str, str]:
    parts = name.split()
    if parts and parts[-1] in SUFFIXES:
        return " ".join(parts[:-1]), parts[-1]
    return name, ""


def token_low(raw: str) -> str:
    return strip_accents(raw).lower().strip(".,")


def is_part(low: str) -> bool:
    return (
        low in POSITION
        or low in ROLE
        or low in CAPS_ONLY
        or low in DESCRIPTORS
        or bool(ROLE_RE.match(low) or SLOT_RE.match(low))
    )


def skippable(raw: str) -> bool:
    raw = raw.strip().strip(",")
    if not raw or raw in {"—", "–", "-"}:
        return True
    if re.fullmatch(r"[A-Za-z]\.", raw):
        return False
    low = token_low(raw)
    if re.fullmatch(r"\d{1,2}", low):
        return True
    if re.fullmatch(r"(?:18|19|20)\d{2}", low):
        return True
    if re.fullmatch(r"\d{4}-\d{4}", low):
        return True
    if low in {"r", "l", "s", "b"}:
        return True
    if "/" in raw or (raw.isupper() and "-" in raw):
        parts = [part for part in re.split(r"[/-]", low) if part]
        return bool(parts) and all(is_part(part) for part in parts)
    if raw.isupper() and low in CAPS_ONLY:
        return True
    if low in POSITION or low in ROLE or low in DESCRIPTORS:
        return True
    if ROLE_RE.match(low) or SLOT_RE.match(low):
        return True
    return False


def extract_name(line: str) -> str:
    text = re.sub(r"\([^)]*\)", " ", line)
    text = re.sub(r'"[^"]*"', " ", text)
    text = re.sub(r"[“”]", " ", text)
    text = re.split(r"\s+[—–]\s+", text)[0]
    if "," in text:
        text = text.split(",", 1)[0]
    tokens = text.split()
    while tokens and skippable(tokens[0]):
        tokens.pop(0)
    while tokens and skippable(tokens[-1]):
        tokens.pop()
    return " ".join(tokens)


def printed_seasons(line: str) -> int | None:
    """The card's own count of franchise seasons, when it printed one."""
    parens = re.findall(r"\((\d{1,2})\)", line)
    if parens:
        return int(parens[-1])
    tokens = line.split()
    if tokens and re.fullmatch(r"\d{1,2}", tokens[-1]):
        return int(tokens[-1])
    return None


def slot_kind(group: str, line: str) -> str:
    if group == "rotation":
        return "sp"
    if group == "bullpen":
        return "rp"
    if group in {"lineup", "bench"}:
        return "hit"
    low_line = norm_name(line)
    if "bullpen" in low_line:
        return "rp"
    tokens = [token_low(token) for token in line.replace("(", " ").replace(")", " ").split()]
    if any(token == "sp" or re.fullmatch(r"sp\d+", token) for token in tokens):
        return "sp"
    return "auto"


def load_table(tar: tarfile.TarFile, name: str):
    raw = tar.extractfile(f"Lahman/data/{name}.RData").read()
    converted = rdata.conversion.convert(rdata.parser.parse_data(raw))
    for value in converted.values():
        if hasattr(value, "columns"):
            return value
    raise RuntimeError(f"{name} did not contain a table")


def lahman_path() -> Path:
    if CACHE.exists() and hashlib.sha256(CACHE.read_bytes()).hexdigest() == LAHMAN_SHA256:
        return CACHE
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(LAHMAN_URL, CACHE)
    digest = hashlib.sha256(CACHE.read_bytes()).hexdigest()
    if digest != LAHMAN_SHA256:
        raise SystemExit(f"Lahman download hash {digest} does not match the pin")
    return CACHE


def as_int(value) -> int:
    if value is None:
        return 0
    try:
        if math.isnan(float(value)):
            return 0
    except (TypeError, ValueError):
        return 0
    return int(value)


def debut_year(value) -> int:
    match = re.match(r"(\d{4})", str(value))
    return int(match.group(1)) if match else 0


def blank(text) -> str:
    if text is None:
        return ""
    rendered = str(text)
    if rendered in {"<NA>", "NA", "nan", "None"}:
        return ""
    return rendered


def add_counting(bucket: dict, **stats: int) -> None:
    for key, amount in stats.items():
        bucket[key] = bucket.get(key, 0) + int(amount)


def window_bounds(years: list[int]) -> tuple[int, list[tuple[int, int]]]:
    count = len(years)
    if count >= 5:
        size = 5
    elif count >= 3:
        size = 3
    else:
        size = count
    spans = [(index, index + size - 1) for index in range(0, count - size + 1)]
    return size, spans


def season_notes(total: int, size: int, start: int, end: int) -> list[str]:
    words = {1: "One", 2: "Two", 3: "Three", 4: "Four"}
    notes = []
    if total < 3:
        if total == 1:
            notes.append("One franchise season")
        else:
            notes.append(f"{words.get(total, total)} franchise seasons; all of them")
    elif total < 5:
        notes.append(f"{words.get(total, total)} franchise seasons; best {size}")
    if end - start + 1 != size:
        notes.append("Years away from the franchise inside this span are not in the totals")
    return notes


def year_label(start: int, end: int) -> str:
    if start == end:
        return f"({start})"
    return f"({start}\u2013{end})"


def hitter_line(stats: dict, games: int) -> str:
    factor_num, factor_den = 162, games
    scaled = {
        key: half_up_div(stats[key], factor_num, factor_den)
        for key in ("G", "PA", "AB", "R", "H", "D", "T", "HR", "RBI", "SB", "BB", "SO")
    }
    obp = quantize(stats["H"] + stats["BB"] + stats["HBP"], stats["AB"] + stats["BB"] + stats["HBP"] + stats["SF"], 3)
    slg = quantize(stats["H"] + stats["D"] + 2 * stats["T"] + 3 * stats["HR"], stats["AB"], 3)
    avg = quantize(stats["H"], stats["AB"], 3)
    ops = None if obp is None or slg is None else obp + slg
    if avg is not None and (avg < 0 or avg > 1):
        raise ValueError("batting average out of range")
    if obp is not None and (obp < 0 or obp > 1):
        raise ValueError("on-base percentage out of range")
    return (
        f"{scaled['G']} G, {scaled['PA']} PA, {scaled['AB']} AB, {scaled['R']} R, "
        f"{scaled['H']} H, {scaled['D']} 2B, {scaled['T']} 3B, {scaled['HR']} HR, "
        f"{scaled['RBI']} RBI, {scaled['SB']} SB, {scaled['BB']} BB, {scaled['SO']} SO, "
        f"{fmt_quant(avg, 3, True)}/{fmt_quant(obp, 3, True)}/{fmt_quant(slg, 3, True)}/{fmt_quant(ops, 3, True)}"
    )


def pitcher_line(stats: dict, kind: str) -> str:
    if kind == "sp" and stats["GS"] > 0:
        numer, denom, label = 34, stats["GS"], "GS"
        scaled_role = half_up_div(stats["GS"], numer, denom)
    else:
        numer, denom, label = 65, stats["G"], "G"
        scaled_role = half_up_div(stats["G"], numer, denom)
    scaled = {
        key: half_up_div(stats[key], numer, denom)
        for key in ("W", "L", "SV", "H", "ER", "BB", "SO")
    }
    scaled_outs = half_up_div(stats["OUTS"], numer, denom)
    era = quantize(27 * stats["ER"], stats["OUTS"], 2)
    whip = quantize(3 * (stats["H"] + stats["BB"]), stats["OUTS"], 2)
    k9 = quantize(27 * stats["SO"], stats["OUTS"], 1)
    ip = f"{scaled_outs // 3}.{scaled_outs % 3}"
    prefix = f"{scaled_role} {label}"
    if kind == "sp" and stats["GS"] == 0:
        prefix = f"{scaled_role} G"
    return (
        f"{prefix}, {scaled['W']}-{scaled['L']}, {scaled['SV']} SV, {ip} IP, "
        f"{scaled['H']} H, {scaled['ER']} ER, {scaled['BB']} BB, {scaled['SO']} SO, "
        f"{fmt_quant(era, 2)} ERA, {fmt_quant(whip, 2)} WHIP, {fmt_quant(k9, 1)} K/9"
    )


def combine(rows: list[dict]) -> dict:
    total = defaultdict(int)
    for row in rows:
        for key, amount in row.items():
            if key in {"lg"}:
                continue
            total[key] += amount
    return total


def best_hitter(years: list[int], rows: dict, weights: dict, league: dict):
    if not years:
        return None
    size, spans = window_bounds(years)
    best = None
    for start_i, end_i in spans:
        chosen = years[start_i:end_i + 1]
        stats = combine([rows[year] for year in chosen])
        if stats["AB"] <= 0 or stats["G"] <= 0:
            continue
        weighted_obp = Decimal(0)
        weighted_slg = Decimal(0)
        weight = Decimal(0)
        for year in chosen:
            for lg, pa in weights[year].items():
                rate = league.get((year, lg))
                if not rate or pa <= 0 or rate["obp"] is None or rate["slg"] is None:
                    continue
                weighted_obp += Decimal(pa) * rate["obp"]
                weighted_slg += Decimal(pa) * rate["slg"]
                weight += Decimal(pa)
        if weight <= 0:
            continue
        lg_obp = weighted_obp / weight
        lg_slg = weighted_slg / weight
        if lg_obp <= 0 or lg_slg <= 0:
            continue
        obp = Decimal(stats["H"] + stats["BB"] + stats["HBP"]) / Decimal(stats["AB"] + stats["BB"] + stats["HBP"] + stats["SF"])
        slg = Decimal(stats["H"] + stats["D"] + 2 * stats["T"] + 3 * stats["HR"]) / Decimal(stats["AB"])
        score = 100 * (obp / lg_obp + slg / lg_slg - 1)
        rank = (round(float(score), 6), stats["PA"], -chosen[0])
        if best is None or rank > best[0]:
            best = (rank, chosen, stats, size, len(years))
    return best


def best_pitcher(years: list[int], rows: dict, weights: dict, league: dict):
    if not years:
        return None
    size, spans = window_bounds(years)
    best = None
    for start_i, end_i in spans:
        chosen = years[start_i:end_i + 1]
        stats = combine([rows[year] for year in chosen])
        if stats["OUTS"] <= 0 or stats["G"] <= 0:
            continue
        weighted_era = Decimal(0)
        weight = Decimal(0)
        for year in chosen:
            for lg, outs in weights[year].items():
                rate = league.get((year, lg))
                if not rate or outs <= 0 or rate["era"] is None:
                    continue
                weighted_era += Decimal(outs) * rate["era"]
                weight += Decimal(outs)
        if weight <= 0:
            continue
        lg_era = weighted_era / weight
        ip = Decimal(stats["OUTS"]) / Decimal(3)
        earned = Decimal(stats["ER"]) if stats["ER"] > 0 else Decimal("0.5")
        era_plus = 100 * lg_era / (Decimal(9) * earned / ip)
        score = era_plus * ip
        rank = (round(float(score), 6), stats["OUTS"], -chosen[0])
        if best is None or rank > best[0]:
            best = (rank, chosen, stats, size, len(years))
    return best


def side_text(team: str, chosen: list[int], stats: dict, size: int, total: int, kind: str) -> str:
    notes = season_notes(total, size, chosen[0], chosen[-1])
    label = f"Peak 162 with {team} {year_label(chosen[0], chosen[-1])}"
    if kind == "hit":
        body = hitter_line(stats, stats["G"])
    else:
        body = pitcher_line(stats, kind)
        if kind == "sp" and stats["GS"] == 0:
            notes.append("No starts in the peak window, so the counting stats are scaled to 65 appearances")
    if notes:
        return label + ". " + ". ".join(notes) + ". " + body
    return label + ": " + body


def secondary_text(kind: str, chosen: list[int], stats: dict, size: int, total: int) -> str:
    notes = season_notes(total, size, chosen[0], chosen[-1])
    title = "Batting" if kind == "hit" else "Pitching"
    body = hitter_line(stats, stats["G"]) if kind == "hit" else pitcher_line(stats, kind)
    label = f"{title} {year_label(chosen[0], chosen[-1])}"
    if notes:
        return label + ". " + ". ".join(notes) + ". " + body
    return label + ": " + body


def resolve_kind(kind: str, bat_rows: dict, pit_rows: dict) -> str:
    if kind != "auto":
        return kind
    pa = sum(row["PA"] for row in bat_rows.values())
    outs = sum(row["OUTS"] for row in pit_rows.values())
    games = sum(row["G"] for row in pit_rows.values())
    starts = sum(row["GS"] for row in pit_rows.values())
    pitcher = "sp" if starts > 0 and starts * 2 >= games else "rp"
    # A few mop-up innings do not make a hitter's peak a pitching line.
    if pa >= 200 and starts < 10 and outs < 150:
        return "hit"
    if outs > 0 and (pa < 200 or starts >= 10 or outs >= 150):
        return pitcher
    if pa > 0:
        return "hit"
    if outs > 0:
        return pitcher
    return "hit"


def show_secondary(primary: str, bat_stats: dict | None, pit_stats: dict | None) -> bool:
    if primary == "hit":
        if not pit_stats:
            return False
        return pit_stats["GS"] >= 10 or pit_stats["OUTS"] >= 150
    if not bat_stats:
        return False
    bat_games = bat_stats["G"]
    pit_games = pit_stats["G"] if pit_stats else 0
    return bat_stats["PA"] >= 200 and bat_stats["PA"] >= pit_games * 8 and bat_games > 0


def main() -> None:
    announced = json.loads(ROSTERS.read_text(encoding="utf-8"))
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    if len(results["teams"]) != 32:
        raise SystemExit("the tournament field is not 32 clubs")
    codes = {team["code"] for team in results["teams"]}
    for code in ("MON", "WSH", "PHA", "OAK"):
        if code not in codes:
            raise SystemExit(f"{code} is missing from the 32-club field")
    frozen_hit = sorted(FROZEN & set(announced))
    if frozen_hit:
        raise SystemExit(f"refusing a roster card for a played club: {frozen_hit}")
    names = {team["code"]: team["name"] for team in results["teams"]}
    team_of = {}
    for club, ids in FRANCHISE.items():
        for team_id in ids:
            if team_id in team_of:
                raise SystemExit(f"{team_id} is listed for two clubs")
            team_of[team_id] = club

    samples = {
        "1 Charlie Blackmon CF L 14": "Charlie Blackmon",
        "SP1 Lefty Grove 9": "Lefty Grove",
        "9 Ferris Fain DH L 6": "Ferris Fain",
        'SP2 Mordecai "Three Finger" Brown': "Mordecai Brown",
        "5 Goose Goslin LF 1921-1930, 1933, 1938 (12)": "Goose Goslin",
        "INF Jeff Cirillo 1994-1999, 2005-2006 (8) 3B/1B/Utility": "Jeff Cirillo",
        "Mike Marshall, MIN 1978-1980 (3) — bullpen honorable mention (card stats shown: 2.99 ERA, 141 ERA+, 54 SV)": "Mike Marshall",
        "8 J.T. Realmuto C R 8": "J.T. Realmuto",
        "CL 1A Kenley Jansen 12": "Kenley Jansen",
        "LR/EMER SP Ranger Suárez 8": "Ranger Suárez",
        "1 Herman Long SS R": "Herman Long",
        "OF/Power PH Jay Buhner 15": "Jay Buhner",
        "HIGH LEV Brad Lidge 4": "Brad Lidge",
        "Ken Griffey Jr. (Legacy Hero) 9": "Ken Griffey Jr.",
        "5 Shoeless Joe Jackson RF 6": "Shoeless Joe Jackson",
        "SP3 Grover Cleveland Alexander 8": "Grover Cleveland Alexander",
        "C2 B.J. Surhoff 1987-1995 (9) C/OF Utility": "B.J. Surhoff",
        "1B Cecil Cooper 1977-1987 (11) 1B/Bat": "Cecil Cooper",
        "C Alejandro Kirk C 7": "Alejandro Kirk",
        "UTL Billy Herman": "Billy Herman",
        "PH/3B Stan Hack": "Stan Hack",
        "DEF IF Andrelton Simmons 5": "Andrelton Simmons",
        "4TH OF Willie Davis 14": "Willie Davis",
        "LONG/SWING Kenny Rogers 13": "Kenny Rogers",
        "EMER SP Denny McLain 8": "Denny McLain",
        "OF3 Danny Murphy 12": "Danny Murphy",
        "2B/BAT Max Bishop 10": "Max Bishop",
        "MULTI Jack Quinn 6": "Jack Quinn",
        "SP4 Pete Alexander": "Pete Alexander",
        "Pete Crow-Armstrong CF": "Pete Crow-Armstrong",
        "Fernando Tatis Jr. SS R 6": "Fernando Tatis Jr.",
        "Home Run Baker 3B 7": "Home Run Baker",
        "Chief Bender 12": "Chief Bender",
        "Tip O'Neill": "Tip O'Neill",
        "J.R. Richard 10": "J.R. Richard",
        "Ha-Seong Kim 4": "Ha-Seong Kim",
        "FR/LR Rollie Fingers 4": "Rollie Fingers",
    }
    for raw, expected in samples.items():
        got = extract_name(raw)
        if got != expected:
            raise SystemExit(f"name parse {raw!r} -> {got!r}, expected {expected!r}")

    with tarfile.open(lahman_path()) as tar:
        people = load_table(tar, "People")
        batting = load_table(tar, "Batting")
        pitching = load_table(tar, "Pitching")
        teams = load_table(tar, "Teams")

    people_by_id = {}
    exact = defaultdict(list)
    alias = defaultdict(list)
    for row in people.itertuples(index=False):
        pid = str(row.playerID)
        first = blank(row.nameFirst)
        last = blank(row.nameLast)
        if not first or not last:
            continue
        person = {
            "id": pid,
            "name": f"{first} {last}",
            "debut": debut_year(row.debut),
        }
        people_by_id[pid] = person
        full = norm_name(f"{first} {last}")
        parts = full.split()
        if len(parts) < 2:
            continue
        exact[full].append(pid)
        alias[full].append(pid)
        first_parts, last_tok = parts[:-1], parts[-1]
        if all(len(part) == 1 for part in first_parts):
            alias["".join(first_parts) + " " + last_tok].append(pid)
        elif len(first_parts) >= 2:
            alias[first_parts[-1] + " " + last_tok].append(pid)
        given = norm_name(blank(row.nameGiven))
        if given:
            given_parts = given.split()
            alias[given_parts[0] + " " + last_tok].append(pid)
            alias[given + " " + last_tok].append(pid)

    def column(frame, name: str):
        if name not in frame.columns:
            raise SystemExit(f"Lahman table is missing {name}")
        return frame[name].tolist()

    def numeric(frame, names: list[str]) -> dict[str, list[int]]:
        out = {}
        for name in names:
            out[name] = [as_int(value) for value in column(frame, name)]
        return out

    league = {}
    t_year = [as_int(value) for value in column(teams, "yearID")]
    t_lg = [blank(value) for value in column(teams, "lgID")]
    t_team = [blank(value) for value in column(teams, "teamID")]
    t_num = numeric(teams, ["AB", "H", "X2B", "X3B", "HR", "BB", "HBP", "SF", "ER", "IPouts"])
    league_raw = defaultdict(lambda: defaultdict(int))
    seen_ids = set()
    for index, team_id in enumerate(t_team):
        seen_ids.add(team_id)
        key = (t_year[index], t_lg[index])
        for name in t_num:
            league_raw[key][name] += t_num[name][index]
    missing = sorted(set(team_of) - seen_ids)
    if missing:
        raise SystemExit(f"Lahman has no team row for {missing}")
    for key, stats in league_raw.items():
        obp_den = stats["AB"] + stats["BB"] + stats["HBP"] + stats["SF"]
        obp = Decimal(stats["H"] + stats["BB"] + stats["HBP"]) / Decimal(obp_den) if obp_den else None
        slg = Decimal(stats["H"] + stats["X2B"] + 2 * stats["X3B"] + 3 * stats["HR"]) / Decimal(stats["AB"]) if stats["AB"] else None
        era = Decimal(27 * stats["ER"]) / Decimal(stats["IPouts"]) if stats["IPouts"] else None
        league[key] = {"obp": obp, "slg": slg, "era": era}

    bat_rows = defaultdict(dict)
    bat_lg = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    pit_rows = defaultdict(dict)
    pit_lg = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    franchise_players = defaultdict(set)
    played = set()

    b_pid = [str(value) for value in column(batting, "playerID")]
    b_year = [as_int(value) for value in column(batting, "yearID")]
    b_team = [blank(value) for value in column(batting, "teamID")]
    b_lg = [blank(value) for value in column(batting, "lgID")]
    b_num = numeric(batting, ["G", "AB", "R", "H", "X2B", "X3B", "HR", "RBI", "SB", "BB", "SO", "HBP", "SH", "SF"])
    for index, pid in enumerate(b_pid):
        played.add(pid)
        club = team_of.get(b_team[index])
        if not club:
            continue
        year = b_year[index]
        lo, hi = YEAR_BOUNDS.get(club, (0, 9999))
        if not lo <= year <= hi:
            continue
        pa = b_num["AB"][index] + b_num["BB"][index] + b_num["HBP"][index] + b_num["SF"][index] + b_num["SH"][index]
        if b_num["G"][index] <= 0 and pa <= 0:
            continue
        slot = bat_rows[(club, pid)].setdefault(year, defaultdict(int))
        add_counting(
            slot, G=b_num["G"][index], PA=pa, AB=b_num["AB"][index], R=b_num["R"][index],
            H=b_num["H"][index], D=b_num["X2B"][index], T=b_num["X3B"][index], HR=b_num["HR"][index],
            RBI=b_num["RBI"][index], SB=b_num["SB"][index], BB=b_num["BB"][index], SO=b_num["SO"][index],
            HBP=b_num["HBP"][index], SH=b_num["SH"][index], SF=b_num["SF"][index],
        )
        if pa and b_lg[index]:
            bat_lg[(club, pid)][year][b_lg[index]] += pa
        franchise_players[club].add(pid)

    p_pid = [str(value) for value in column(pitching, "playerID")]
    p_year = [as_int(value) for value in column(pitching, "yearID")]
    p_team = [blank(value) for value in column(pitching, "teamID")]
    p_lg = [blank(value) for value in column(pitching, "lgID")]
    p_num = numeric(pitching, ["W", "L", "G", "GS", "SV", "IPouts", "H", "ER", "BB", "SO"])
    for index, pid in enumerate(p_pid):
        played.add(pid)
        club = team_of.get(p_team[index])
        if not club:
            continue
        year = p_year[index]
        lo, hi = YEAR_BOUNDS.get(club, (0, 9999))
        if not lo <= year <= hi:
            continue
        if p_num["G"][index] <= 0 and p_num["IPouts"][index] <= 0:
            continue
        slot = pit_rows[(club, pid)].setdefault(year, defaultdict(int))
        add_counting(
            slot, W=p_num["W"][index], L=p_num["L"][index], G=p_num["G"][index],
            GS=p_num["GS"][index], SV=p_num["SV"][index], OUTS=p_num["IPouts"][index],
            H=p_num["H"][index], ER=p_num["ER"][index], BB=p_num["BB"][index], SO=p_num["SO"][index],
        )
        if p_num["IPouts"][index] and p_lg[index]:
            pit_lg[(club, pid)][year][p_lg[index]] += p_num["IPouts"][index]
        franchise_players[club].add(pid)

    def unique(pids: list[str]) -> list[str]:
        seen = set()
        ordered = []
        for pid in pids:
            if pid not in seen:
                seen.add(pid)
                ordered.append(pid)
        return ordered

    def match(club: str, line: str):
        extracted = extract_name(line)
        if not extracted:
            return None, "the roster line has no player name"
        base, suffix = pop_suffix(norm_name(extracted))
        manual = MANUAL.get((club, base))
        if manual:
            if manual not in franchise_players[club]:
                return None, f"{manual} has no seasons with this franchise"
            return people_by_id[manual], ""
        if suffix in {"jr", "sr"}:
            pool = [pid for pid in exact.get(base, []) if pid in played and people_by_id[pid]["debut"]]
            pool.sort(key=lambda pid: (people_by_id[pid]["debut"], pid))
            if pool:
                chosen = pool[-1] if suffix == "jr" else pool[0]
                if chosen not in franchise_players[club]:
                    return None, f"the {suffix} {people_by_id[chosen]['name']} did not play for this franchise"
                return people_by_id[chosen], ""
        cands = [pid for pid in unique(alias.get(base, [])) if pid in franchise_players[club]]
        exact_cands = [pid for pid in cands if pid in exact.get(base, [])]
        if len(cands) == 1:
            return people_by_id[cands[0]], ""
        if len(exact_cands) == 1:
            return people_by_id[exact_cands[0]], ""
        if club == "PHA" and base == "danny murphy" and len(cands) > 1:
            keep = []
            for pid in cands:
                years = set(bat_rows[(club, pid)]) | set(pit_rows[(club, pid)])
                if any(1902 <= year <= 1913 for year in years):
                    keep.append(pid)
            if len(keep) == 1:
                return people_by_id[keep[0]], ""
            cands = keep or cands
        want = printed_seasons(line)
        if want is not None and len(cands) > 1:
            counted = []
            for pid in cands:
                years = set(bat_rows[(club, pid)]) | set(pit_rows[(club, pid)])
                if len(years) == want:
                    counted.append(pid)
            if len(counted) == 1:
                resolved.append((club, line, counted[0], want))
                return people_by_id[counted[0]], ""
        if not cands:
            return None, "no franchise player matched this name"
        listed = ", ".join(f"{pid} {people_by_id[pid]['name']}" for pid in sorted(cands))
        return None, f"ambiguous: {listed}"

    clubs = {}
    unavailable = []
    resolved = []
    for club in announced:
        if club not in FRANCHISE:
            raise SystemExit(f"{club} has a roster card and no franchise map")
        roster = announced[club]
        lines = []
        for group in ("lineup", "bench", "rotation", "bullpen"):
            for line in roster.get(group) or []:
                lines.append((group, line))
        for line in roster.get("honorable_mentions") or []:
            lines.append(("honorable_mentions", line))
        if roster.get("what_if"):
            lines.append(("what_if", roster["what_if"]))
        if len(lines) != len({line for _, line in lines}):
            raise SystemExit(f"{club} repeats a roster line")
        club_out = {}
        team_name = names[club]
        for group, line in lines:
            person, reason = match(club, line)
            if not person:
                club_out[line] = {"status": "unavailable", "text": "Peak stats unavailable", "reason": reason}
                unavailable.append((club, line, reason))
                continue
            pid = person["id"]
            batting_seasons = bat_rows[(club, pid)]
            pitching_seasons = pit_rows[(club, pid)]
            if club == "BAL" and pid == "sislege01":
                # Baltimore franchise history includes the St. Louis Browns.
                # Owner authorized *only* Sisler's Browns seasons, never any
                # of his time with Washington or the Boston Braves.
                batting_seasons = {year: row for year, row in batting_seasons.items()
                                   if 1915 <= year <= 1927}
                pitching_seasons = {year: row for year, row in pitching_seasons.items()
                                   if 1915 <= year <= 1927}
            kind = resolve_kind(slot_kind(group, line), batting_seasons, pitching_seasons)
            try:
                if kind == "hit":
                    eligible_years = sorted(year for year in batting_seasons
                        if year not in HITTER_WINDOW_EXCLUDE.get((club, pid), set()))
                    found = best_hitter(eligible_years, batting_seasons, bat_lg[(club, pid)], league)
                    other = best_pitcher(sorted(pitching_seasons), pitching_seasons, pit_lg[(club, pid)], league)
                    other_kind = "sp" if other and other[2]["GS"] > 0 and other[2]["GS"] * 2 >= other[2]["G"] else "rp"
                else:
                    found = best_pitcher(sorted(pitching_seasons), pitching_seasons, pit_lg[(club, pid)], league)
                    other = best_hitter(sorted(batting_seasons), batting_seasons, bat_lg[(club, pid)], league)
                    other_kind = "hit"
                if not found:
                    club_out[line] = {
                        "status": "unavailable",
                        "text": "Peak stats unavailable",
                        "lahman_id": pid,
                        "reason": "no franchise seasons with a league rate",
                    }
                    unavailable.append((club, line, club_out[line]["reason"]))
                    continue
                _, chosen, stats, size, total = found
                peak_team_name = ("St. Louis Browns"
                                  if club == "BAL" and pid == "sislege01"
                                  else team_name)
                text = side_text(peak_team_name, chosen, stats, size, total, kind)
                if other and show_secondary(kind, other[2] if other_kind == "hit" else stats, stats if other_kind == "hit" else other[2]):
                    if not text.endswith("."):
                        text += "."
                    text += " " + secondary_text(other_kind, other[1], other[2], other[3], other[4])
                club_out[line] = {
                    "status": "ok",
                    "lahman_id": pid,
                    "text": text,
                    "years": [int(year) for year in chosen],
                }
            except ValueError as exc:
                club_out[line] = {
                    "status": "unavailable",
                    "text": "Peak stats unavailable",
                    "lahman_id": pid,
                    "reason": str(exc),
                }
                unavailable.append((club, line, str(exc)))
        clubs[club] = club_out

    payload = {
        "source": "Lahman Baseball Database 2025, CRAN package Lahman 14.0-0, seasons 1871 through 2025. No park factor and no WAR; Lahman does not publish WAR.",
        "cutoff": 2025,
        "cutoff_note": "Peak 162 uses Lahman seasons through 2025. The 2026 season is not in that file.",
        "clubs": clubs,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} clubs {len(clubs)} unavailable {len(unavailable)} resolved {len(resolved)}")
    for club, line, pid, want in resolved:
        print(f"RESOLVED {club} | {line} | {pid} | card seasons {want}")
    for club, line, reason in unavailable:
        print(f"UNMATCHED {club} | {line} | {reason}")

    def row(club: str, line: str) -> dict:
        return clubs[club][line]

    checks = [
        ("SD", "2 Tony Gwynn RF L 20", "gwynnto01"),
        ("SEA", "3 Ken Griffey Jr. CF L 13", "griffke02"),
        ("CIN", "Ken Griffey Sr. 12", "griffke01"),
        ("SD", "1 Fernando Tatis Jr. SS R 6", "tatisfe02"),
        ("ATL", "OF4 Ronald Acuña Jr. (Speed/Power)", "acunaro01"),
        ("PHA", "SP4 Chief Bender 12", "bendech01"),
        ("PHA", "6 Home Run Baker 3B 7", "bakerfr01"),
        ("PHA", "SP1 Lefty Grove 9", "grovele01"),
        ("LAD", "9 Pee Wee Reese SS R 16", "reesepe01"),
        ("MIN", "SP1 Walter Johnson 1907-1927 (21)", "johnswa01"),
        ("ATL", "SP2 Kid Nichols R", "nichoki01"),
        ("OAK", "SP1 Catfish Hunter", "hunteca01"),
        ("MON", "1 Tim Raines LF S 13", "raineti01"),
        ("CWS", "5 Joe Jackson DH", "jacksjo01"),
        ("BAL", "BAT2 George Sisler 1B (St. Louis Browns 1915-1927)", "sislege01"),
        ("CLE", "5 Shoeless Joe Jackson RF 6", "jacksjo01"),
        ("PHI", "SP3 Grover Cleveland Alexander 8", "alexape01"),
        ("CHC", "SP4 Pete Alexander", "alexape01"),
    ]
    for club, line, pid in checks:
        got = row(club, line)
        if got.get("lahman_id") != pid:
            raise SystemExit(f"{club} {line} matched {got.get('lahman_id')} ({got.get('reason')}), expected {pid}")
    murphy = row("PHA", "OF3 Danny Murphy 12")
    if murphy.get("status") != "ok" or people_by_id[murphy["lahman_id"]]["debut"] > 1915:
        raise SystemExit(f"PHA Danny Murphy matched {murphy}")
    if any(year < 1968 or year > 2025 for year in row("OAK", "SP1 Catfish Hunter")["years"]):
        raise SystemExit("Catfish Hunter peak is outside Oakland seasons")
    if any(year > 1954 or year < 1901 for year in row("PHA", "SP1 Lefty Grove 9")["years"]):
        raise SystemExit("Lefty Grove peak is outside the Philadelphia Athletics")
    if any(year < 1969 or year > 2004 for year in row("MON", "1 Tim Raines LF S 13")["years"]):
        raise SystemExit("Tim Raines peak is outside the Expos")
    sisler = row("BAL", "BAT2 George Sisler 1B (St. Louis Browns 1915-1927)")
    if (not all(1915 <= year <= 1927 for year in sisler["years"])
            or "Peak 162 with St. Louis Browns" not in sisler["text"]):
        raise SystemExit("George Sisler's display must use St. Louis Browns years only")
    if min(row("MIN", "SP1 Walter Johnson 1907-1927 (21)")["years"]) > 1960:
        raise SystemExit("Walter Johnson peak did not use the Senators")
    if "Pitching" not in row("LAD", "4 Shohei Ohtani DH L 2")["text"]:
        raise SystemExit("Ohtani's Dodgers line has no pitching peak")
    gwynn = row("SD", "2 Tony Gwynn RF L 20")["text"]
    if ".3" not in gwynn.split(", ")[-1][:4] and not gwynn.split(", ")[-1].startswith(".3"):
        # The batting line ends with avg/obp/slg/ops. Gwynn's peak average stays above .300.
        average = gwynn.split(", ")[-1].split("/")[0]
        if not average.startswith(".3") and not average.startswith(".4"):
            raise SystemExit(f"Gwynn average looks wrong: {gwynn}")
if __name__ == "__main__":
    main()
