#!/usr/bin/env python3
"""Parse the official 1986 Payoff Pitch card-set PDF into reference files.

The engines read three files:

  historical-cards/reference/cards_1986.json
  historical-cards/reference/card_profiles.json
  historical-cards/reference/ballparks.json

Pages 2-136 are player cards, eight to a landscape page. Pages 137-140
are the 26 ballpark cards. The Quick Results PDF and the separate
ratings sheet are not read.

A hitter row prints one result, in the left result column, and that
word applies to every range on the row. The right-hand result is not a
second word. Tokens centered under Pos (about x+132) are positions,
including 1B/2B/3B, and are not band results. A result with no range
on its row is not a band.

Face 00 is not on these sections. Coverage of 01-99 is reported; it is
not forced.
"""
from __future__ import annotations

import json
import os
import re

import pymupdf

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REF_DIR = os.path.join(ROOT, "historical-cards", "reference")
DEFAULT_PDF = os.environ.get(
    "PP_1986_PDF",
    "/cursor/stores/bot/grok-bot/agents/8c000417-b72e-4d5e-9fa4-a9f6d41438a4/attachments/01M5XN4SEN11G8B0J18PPKCHX1.pdf",
)

COLS = (0, 198, 396, 594, 792)
ROWS = (0, 306, 612)
SECTION_WORD = {
    "WHEEL": "WHEELHOUSE",
    "PATIENT": "PATIENT",
    "TOUGH": "TOUGH",
    "IN-PLAY": "IN-PLAY",
    "INPLAY": "IN-PLAY",
    "OUT": "OUT",
}
HIT_RESULTS = ("HR", "3B", "2B", "1B", "BB", "HBP", "SO")
HIT_RESULT = set(HIT_RESULTS)
OUT_RESULT = re.compile(r"^(?:P[1-6]|L[1-6]|G[1-6]|F[7-9])$")
RANGE = re.compile(r"^(\d{1,2})(?:-(\d{1,2}))?$")
PITCH_OUTCOMES = {
    "WHEELHOUSE", "PATIENT", "TOUGH", "IN-PLAY", "BALLPARK", "DEFENSE",
    "TOUGH-OUT", "PATIENT-OUT", "ERROR", "RANGE", "WHEEL",
}


def _num(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _lines(words, tol=2.2):
    """Cluster words into visual rows."""
    rows = []
    for word in sorted(words, key=lambda item: (item[1], item[0])):
        placed = False
        for row in rows:
            if abs(word[1] - row[0][1]) <= tol:
                row.append(word)
                placed = True
                break
        if not placed:
            rows.append([word])
    packed = []
    for row in rows:
        row.sort(key=lambda item: item[0])
        y = sum(item[1] for item in row) / len(row)
        packed.append((y, row))
    packed.sort(key=lambda item: item[0])
    return packed


def _span(token):
    match = RANGE.match(token)
    if not match:
        return None
    lo = int(match.group(1))
    hi = int(match.group(2) or match.group(1))
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def _cell_words(page, x0, x1, y0, y1):
    return [
        word for word in page.get_text("words")
        if x0 + 4 <= word[0] < x1 - 2 and y0 + 2 <= word[1] < y1 - 2
    ]


def _is_park(words):
    text = {word[4] for word in words}
    return "RANGE" in text and "ERROR" in text and "WHEELHOUSE" in text and "BALLPARK" in text


def _is_hitter(words):
    """A hitter card labels the section 'WHEEL'. A pitcher result is the
    whole word WHEELHOUSE next to a 2d6 slot, which is not this token."""
    return any(word[4] == "WHEEL" for word in words)


def _is_pitcher(words):
    text = {word[4] for word in words}
    return "GS" in text and "IP" in text and not _is_hitter(words)


def _name_and_hand(lines):
    """Top line is the name. A lone L/R/S under it is the bat or throw hand."""
    name = ""
    hand = None
    age = None
    team = ""
    league = ""
    partial = ""
    for y, row in lines:
        tokens = [word[4] for word in row]
        if not name and any(token[:1].isalpha() and len(token) > 1 for token in tokens):
            name = " ".join(token for token in tokens if token[:1].isalpha())
            continue
        if name and hand is None and len(tokens) == 1 and tokens[0] in ("L", "R", "S", "B"):
            hand = "S" if tokens[0] == "B" else tokens[0]
            continue
        if "1986" in tokens:
            # "29 1986 Detroit (A)" or "26 1986 Chicago (A) [Jul 26 - Oct 2]"
            if tokens[0].isdigit() and len(tokens[0]) <= 2:
                age = int(tokens[0])
            try:
                year_at = tokens.index("1986")
            except ValueError:
                year_at = 0
            rest = tokens[year_at + 1:]
            cut = []
            bracket = []
            for token in rest:
                if token.startswith("[") or bracket:
                    bracket.append(token)
                else:
                    cut.append(token)
            if cut and re.fullmatch(r"\([A-Z]\)", cut[-1]):
                league = cut[-1].strip("()")
                cut = cut[:-1]
            team = " ".join(cut)
            partial = " ".join(bracket).strip("[]")
            break
    return name, hand, age, team, league, partial


def _add_band(bands, result, lo, hi):
    if result not in HIT_RESULT:
        return
    if lo < 1 or hi > 99:
        return
    bands.setdefault(result, []).append((lo, hi))


def _collapse(bands):
    """Merge ranges of one result that touch. Leave a gap as two parts."""
    collapsed = {}
    for result, parts in bands.items():
        parts = sorted(parts)
        merged = [list(parts[0])]
        for lo, hi in parts[1:]:
            if lo <= merged[-1][1] + 1:
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        collapsed[result] = merged
    table = {}
    for result in HIT_RESULTS:
        parts = collapsed.get(result) or []
        if not parts:
            table[result] = None
        elif len(parts) == 1:
            table[result] = parts[0]
        else:
            # The solver reads one interval. Keep the printed parts, and
            # also the face count, so a gap is not filled in.
            table[result] = parts[0]
            table[result + "_extra"] = parts[1:]
    return table


def _parse_hitter_bands(lines, x0):
    labels = []
    for y, row in lines:
        for word in row:
            section = SECTION_WORD.get(word[4])
            # WHEEL/PATIENT/TOUGH/IN-PLAY sit in the center gutter.
            # OUT sits at the left edge of the out chart.
            centered = x0 + 80 <= word[0] <= x0 + 140
            if section == "OUT" and word[0] < x0 + 90:
                labels.append((y, section))
            elif section and section != "OUT" and centered:
                labels.append((y, section))
    labels.sort()
    per_hand = {"vsLHP": {}, "vsRHP": {}}
    out_rows = []
    out_y = next((y for y, section in labels if section == "OUT"), 10_000)
    for y, row in lines:
        ranges = []
        results = []
        for word in row:
            span = _span(word[4])
            center = (word[0] + word[2]) / 2
            if span and word[0] < x0 + 120:
                ranges.append((word[0], span))
            elif word[4] in HIT_RESULT and center < x0 + 80:
                # Left result column only. 1B/2B/3B under Pos are positions.
                results.append((word[0], word[4]))
            elif OUT_RESULT.match(word[4]) and word[0] < x0 + 160:
                results.append((word[0], word[4]))
        if y >= out_y - 1:
            # Out chart. A result sometimes sits a point under its range.
            continue
        if not ranges:
            continue
        ranges.sort()
        results.sort()
        # Section: the label just below a lead row, otherwise the label above.
        section = None
        for label_y, label in labels:
            if label == "OUT":
                continue
            if -1 <= label_y - y <= 10:
                section = label
                break
        if section is None:
            above = [label for label_y, label in labels if label_y < y and label != "OUT"]
            section = above[-1] if above else None
        if section is None:
            continue
        if len(results) >= 2 and len(ranges) >= 2:
            pairs = [(ranges[0], results[0][1]), (ranges[1], results[1][1])]
        elif len(ranges) >= 2 and len(results) == 1:
            pairs = [(ranges[0], results[0][1]), (ranges[1], results[0][1])]
        elif len(ranges) == 1 and results:
            # One range sits on the left or the right.
            side_result = results[0][1]
            pairs = [(ranges[0], side_result)]
        else:
            continue
        for (rx, span), result in pairs:
            hand = "vsLHP" if rx < x0 + 60 else "vsRHP"
            _add_band(per_hand[hand].setdefault(section, {}), result, span[0], span[1])
    # Out chart rows, including a result printed just under the range.
    chart_words = []
    for y, row in lines:
        if y < out_y - 1 or y > out_y + 70:
            continue
        chart_words.extend(row)
    chart_lines = _lines(chart_words, tol=3.5)
    for y, row in chart_lines:
        pending = None
        for word in row:
            span = _span(word[4])
            if span and word[0] < x0 + 130:
                if pending:
                    out_rows.append(pending)
                pending = {"range": [span[0], span[1]], "result": None, "x": word[0]}
            elif OUT_RESULT.match(word[4]) and pending and pending["result"] is None:
                pending["result"] = word[4]
        if pending:
            out_rows.append(pending)
    # A result that landed on the following clustered row with no range
    # belongs to the previous open range in the same column.
    cleaned = []
    open_by_col = {}
    for row in out_rows:
        col = 0 if row["x"] < x0 + 55 else 1 if row["x"] < x0 + 95 else 2
        if row["result"]:
            cleaned.append({"range": row["range"], "result": row["result"]})
            open_by_col.pop(col, None)
        else:
            open_by_col[col] = row
    # Second pass: results that were clustered onto a later line are
    # already inside `row` when the tolerance is 3.5. Drop empties.
    sections = {}
    for section in ("WHEELHOUSE", "PATIENT", "TOUGH", "IN-PLAY"):
        sections[section] = {
            "vsLHP": _collapse(per_hand["vsLHP"].get(section, {})),
            "vsRHP": _collapse(per_hand["vsRHP"].get(section, {})),
        }
    return sections, [row for row in cleaned if row["result"]]


def _number_after(lines, label):
    """The rating printed to the right of a label, not the first digit on the row.

    A die range such as 55 shares the row with 'DP:'. The rating is the
    digit that follows the label in x-order.
    """
    for y, row in lines:
        tokens = [word[4] for word in row]
        if label not in tokens:
            continue
        after = tokens[tokens.index(label) + 1:]
        for token in after:
            if token.isdigit():
                return int(token)
            match = re.match(r"^(\d)\+$", token)
            if match:
                return int(match.group(1))
    return None


POS_TOKENS = {"C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "OF", "DH", "P", "UT", "PH"}


def _fielding(lines, x0):
    """Position chips under Pos / R / E / Arm. Several rows when a player has several positions."""
    y0 = min(y for y, row in lines)
    found = []
    for y, row in lines:
        if not (y0 + 40 <= y <= y0 + 115):
            continue
        pos = rng = err = arm = None
        for word in row:
            rel = word[0] - x0
            token = word[4]
            if 115 <= rel <= 140 and token in POS_TOKENS:
                pos = token
            elif 135 <= rel <= 155 and token in ("A", "B", "C", "D", "F"):
                rng = token
            elif 155 <= rel <= 172 and token.isdigit() and int(token) <= 5:
                err = int(token)
            elif 172 <= rel <= 195 and token.isdigit() and int(token) <= 9:
                arm = int(token)
        if pos or (rng and err is not None):
            found.append({"pos": pos, "range": rng, "e": err, "arm": arm})
    return found


def _sac_bunt(lines):
    """The letter printed just to the right of 'Bunt', one row below the label."""
    words = [word for y, row in lines for word in row]
    bunt = next((word for word in words if word[4] == "Bunt"), None)
    if bunt is None:
        return None
    letters = [
        word for word in words
        if word[4] in ("A", "B", "C", "D", "F")
        and word[0] >= bunt[0] - 2
        and 0 <= word[1] - bunt[1] < 14
    ]
    if not letters:
        return None
    letters.sort(key=lambda word: word[0])
    return letters[-1][4]


def _parse_hitter(lines, x0):
    name, bats, age, team, league, partial = _name_and_hand(lines)
    sections, out_table = _parse_hitter_bands(lines, x0)
    steal_jump = None
    steal_mod = None
    steal_letter = None
    for y, row in lines:
        tokens = [word[4] for word in row]
        if "Steal:" in tokens:
            after = tokens[tokens.index("Steal:") + 1:]
            for token in after:
                match = re.match(r"^(\d)(\+|-)?$", token)
                if match:
                    steal_jump = int(match.group(1))
                    steal_mod = match.group(2)
                elif token in ("A", "B", "C", "D", "F"):
                    steal_letter = token
    stats = _split_stats(lines)
    positions = _fielding(lines, x0)
    return {
        "name": name,
        "age": age,
        "team": team,
        "league": league,
        "partial": partial or None,
        "bats": bats,
        "throws": None,
        "pitcher": False,
        "positions": positions,
        "dp": _number_after(lines, "DP:"),
        "run": _number_after(lines, "Run:"),
        "steal": {"jump": steal_jump, "jump_mod": steal_mod, "rating": steal_letter},
        "sac_bunt": _sac_bunt(lines),
        "sections": sections,
        "out_table": out_table,
        "stats_split": stats,
    }


def _split_stats(lines):
    """Hitter vs-L / vs-R counting line under the card.

    The card prints AB, 2B, 3B, HR, BB, SO, AVG, OBP, SLG. It does not
    print hits or plate appearances. Hits are recovered from slugging.
    """
    splits = {}
    for y, row in lines:
        tokens = [word[4] for word in row]
        if not tokens or tokens[0] not in ("L", "R"):
            continue
        nums = []
        for token in tokens[1:]:
            value = _num(token)
            if value is None:
                continue
            nums.append(value)
        if len(nums) < 9:
            continue
        ab, doubles, triples, hr, bb, so, avg, obp, slg = nums[:9]
        if ab <= 0:
            continue
        tb = slg * ab
        hits = int(round(tb - doubles - 2 * triples - 3 * hr))
        splits[tokens[0]] = {
            "AB": int(round(ab)),
            "H": hits,
            "2B": int(round(doubles)),
            "3B": int(round(triples)),
            "HR": int(round(hr)),
            "BB": int(round(bb)),
            "SO": int(round(so)),
            "AVG": avg,
            "OBP": obp,
            "SLG": slg,
        }
    return splits


def _pitch_outcome(token):
    """Map a printed 2d6 word to a chart result. Slashes stay noted by the caller."""
    slashed = token.startswith("/") and token.endswith("/")
    raw = token.strip("/")
    if raw == "WHEEL":
        raw = "WHEELHOUSE"
    if raw in PITCH_OUTCOMES and raw != "WHEEL":
        return raw, slashed
    return None, False


def _parse_pitcher(lines):
    name, throws, age, team, league, partial = _name_and_hand(lines)
    results = {}
    slash_slots = []
    stamina = None
    for y, row in lines:
        tokens = [word[4] for word in row]
        for token in tokens:
            if re.fullmatch(r"\d+/Long\+?", token):
                stamina = token
        slot = None
        outcome = None
        slashed = False
        for token in tokens:
            if token.isdigit() and slot is None and 2 <= int(token) <= 12:
                slot = int(token)
                continue
            parsed, is_slash = _pitch_outcome(token)
            if parsed and outcome is None:
                outcome = parsed
                slashed = is_slash
        if slot is not None and outcome:
            results[str(slot)] = outcome
            if slashed:
                slash_slots.append(str(slot))
    so_rating = None
    flat = [word[4] for y, row in lines for word in row]
    if "%roll" in flat:
        bump = 20 if "+20" in flat else 10 if "+10" in flat else None
        if bump:
            so_rating = {"kind": "roll", "bump": bump}
    if so_rating is None:
        for y, row in lines:
            tokens = [word[4] for word in row]
            if len(tokens) == 1:
                span = _span(tokens[0])
                if span and span[0] in (50, 90) and span[1] >= span[0]:
                    so_rating = {"kind": "range", "lo": span[0], "hi": span[1]}
    # Season line: G GS CG SV IP H HR BB SO, then a W-L ERA row.
    line = None
    for y, row in lines:
        tokens = [word[4] for word in row]
        nums = []
        raw_nums = []
        for token in tokens:
            # "9" is a real counting number. Do not skip it because the
            # rate line says "Per 9".
            if token in ("G", "GS", "CG", "SV", "IP", "H", "HR", "BB", "SO", "Per"):
                continue
            value = _num(token)
            if value is not None:
                nums.append(value)
                raw_nums.append(token)
        if len(nums) >= 9 and nums[0] >= 1 and nums[4] >= 0 and nums[1] <= nums[0]:
            # G, GS, CG, SV, IP, H, HR, BB, SO.
            # IP is baseball notation: 72.1 is 72 and one third, 72.2 is two thirds.
            g, gs, cg, sv, ip, hits, hr, bb, so = nums[:9]
            ip_token = raw_nums[4]
            if re.fullmatch(r"\d+\.1", ip_token):
                ip = int(ip_token.split(".")[0]) + 1 / 3
            elif re.fullmatch(r"\d+\.2", ip_token):
                ip = int(ip_token.split(".")[0]) + 2 / 3
            if ip > 400:
                continue
            line = {
                "G": int(g), "GS": int(gs), "CG": int(cg), "SV": int(sv),
                "IP": round(float(ip), 3), "H": int(hits), "HR": int(hr), "BB": int(bb), "SO": int(so),
            }
            break
    return {
        "name": name,
        "age": age,
        "team": team,
        "league": league,
        "partial": partial or None,
        "bats": None,
        "throws": throws,
        "pitcher": {
            "results": results,
            "slash_slots": slash_slots,
            "so_rating": so_rating,
            "stamina": stamina,
        },
        "stats": line,
    }


def _hyphen_spans(tokens):
    """Spans from '1-30' or from the split tokens '1' '-' '30'. A bare digit is not a span."""
    spans = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if "-" in token:
            span = _span(token)
            if span:
                spans.append(span)
            index += 1
            continue
        if (
            token.isdigit()
            and index + 2 < len(tokens)
            and tokens[index + 1] == "-"
            and tokens[index + 2].isdigit()
        ):
            lo, hi = int(token), int(tokens[index + 2])
            if lo > hi:
                lo, hi = hi, lo
            spans.append((lo, hi))
            index += 3
            continue
        index += 1
    return spans


def _parse_park(lines):
    name = ""
    season = ""
    for y, row in lines:
        tokens = [word[4] for word in row]
        text = " ".join(tokens)
        if "©" in text:
            continue
        if "1986" in tokens and not season:
            season = text
            break
        if not name and "BALLPARK" not in tokens and any(len(token) > 2 and token[:1].isalpha() for token in tokens):
            name = text
    wh_l = wh_r = None
    for y, row in lines:
        tokens = [word[4] for word in row]
        if "WHEELHOUSE" not in tokens:
            continue
        spans = _hyphen_spans(tokens)
        if len(spans) >= 2:
            wh_l = spans[0][1]
            wh_r = spans[1][1]
    range_hit = {}
    error_hi = {}
    for y, row in lines:
        tokens = [word[4] for word in row]
        if not tokens or tokens[0] not in ("A", "B", "C", "D", "F"):
            continue
        spans = _hyphen_spans(tokens[1:])
        grade = next((token for token in tokens[1:] if token in ("1", "2", "3", "4", "5")), None)
        if spans:
            # First span is the RANGE hit band. Its hi is the last face that is a hit.
            range_hit[tokens[0]] = spans[0][1]
        # "5 1-31 32-99": the error hit band is the span that starts at 1 after the grade.
        ones = [span for span in spans if span[0] == 1]
        if grade and len(ones) >= 2:
            error_hi[grade] = ones[1][1]
    return {
        "name": name,
        "season": season,
        "wh_l": wh_l,
        "wh_r": wh_r,
        "range_hit_hi": range_hit,
        "error_hi": error_hi,
    }


def _profile(player):
    splits = player.get("stats_split") or {}
    if not splits:
        return None
    ab = h = doubles = triples = hr = bb = so = 0
    for side in splits.values():
        ab += side["AB"]
        h += side["H"]
        doubles += side["2B"]
        triples += side["3B"]
        hr += side["HR"]
        bb += side["BB"]
        so += side["SO"]
    if ab <= 0:
        return None
    pa = ab + bb  # HBP and SF are not printed. Flagged by the caller.
    tb = h + doubles + 2 * triples + 3 * hr
    return {
        "name": player["name"],
        "team": player.get("team"),
        "avg": h / ab,
        "obp": (h + bb) / pa,
        "slg": tb / ab,
        "bbp": bb / pa,
        "sop": so / pa,
        "hrp": hr / pa,
        "hbpp": 0.0,
        "pa_note": "PA is AB+BB. The 1986 card does not print HBP or SF.",
    }


def parse_pdf(path):
    doc = pymupdf.open(path)
    players = []
    parks = []
    for index, page in enumerate(doc):
        if index == 0:
            continue
        for x0, x1 in zip(COLS, COLS[1:]):
            for y0, y1 in zip(ROWS, ROWS[1:]):
                words = _cell_words(page, x0, x1, y0, y1)
                if len(words) < 8:
                    continue
                lines = _lines(words)
                if _is_park(words):
                    park = _parse_park(lines)
                    if park.get("name"):
                        parks.append(park)
                    continue
                if _is_hitter(words):
                    player = _parse_hitter(lines, x0)
                elif _is_pitcher(words):
                    player = _parse_pitcher(lines)
                else:
                    continue
                if player.get("name"):
                    player["source_page"] = index + 1
                    players.append(player)
    # Duplicate names get the team so the comp lookup stays unique.
    seen = {}
    for player in players:
        seen.setdefault(player["name"], []).append(player)
    for name, group in seen.items():
        if len(group) == 1:
            continue
        for player in group:
            player["name"] = "%s (%s)" % (name, player.get("team") or player["source_page"])
    profiles = [profile for profile in (_profile(player) for player in players if not player.get("pitcher")) if profile]
    return players, profiles, parks


def coverage(player):
    """Faces 1-99 claimed by a result band, per section and hand."""
    report = {}
    if player.get("pitcher"):
        table = (player.get("pitcher") or {}).get("results") or {}
        report["slots"] = sorted(int(key) for key in table)
        return report
    for section, hands in (player.get("sections") or {}).items():
        for hand, table in hands.items():
            faces = set()
            for key, rng in table.items():
                if key.endswith("_extra"):
                    for lo, hi in rng:
                        faces.update(range(lo, hi + 1))
                    continue
                if not rng:
                    continue
                faces.update(range(int(rng[0]), int(rng[1]) + 1))
            report["%s %s" % (section, hand)] = len(faces)
    return report


def main():
    players, profiles, parks = parse_pdf(DEFAULT_PDF)
    os.makedirs(REF_DIR, exist_ok=True)
    cards_path = os.path.join(REF_DIR, "cards_1986.json")
    profiles_path = os.path.join(REF_DIR, "card_profiles.json")
    parks_path = os.path.join(REF_DIR, "ballparks.json")
    with open(cards_path, "w") as handle:
        json.dump({"players": players, "source": "1986 Payoff Pitch season PDF"}, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    with open(profiles_path, "w") as handle:
        json.dump(profiles, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    with open(parks_path, "w") as handle:
        json.dump(parks, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    hitters = [player for player in players if not player.get("pitcher")]
    pitchers = [player for player in players if player.get("pitcher")]
    print("players", len(players), "hitters", len(hitters), "pitchers", len(pitchers), "parks", len(parks), "profiles", len(profiles))
    rolls = [p for p in pitchers if (p["pitcher"].get("so_rating") or {}).get("kind") == "roll"]
    ranges = [p for p in pitchers if (p["pitcher"].get("so_rating") or {}).get("kind") == "range"]
    print("roll modifiers", [(p["name"], p["pitcher"]["so_rating"]) for p in rolls])
    print("range modifiers", len(ranges))
    missing_slots = [p["name"] for p in pitchers if set((p["pitcher"].get("results") or {})) != {str(n) for n in range(2, 13)}]
    print("pitchers missing a 2-12 slot", len(missing_slots))
    # Whitaker check
    lou = next(p for p in hitters if p["name"].startswith("Lou Whitaker"))
    print("Whitaker WHEEL", lou["sections"]["WHEELHOUSE"])
    print("Whitaker TOUGH", lou["sections"]["TOUGH"])
    print("Whitaker out", len(lou["out_table"]), "dp", lou["dp"], "run", lou["run"], "pos", lou["positions"], "sac", lou["sac_bunt"])
    print("park names", len(parks), [p["name"] for p in parks])
    empty_err = [p["name"] for p in parks if len(p.get("error_hi") or {}) < 5]
    print("parks missing an error grade", empty_err)


if __name__ == "__main__":
    main()
