"""Fast Action Cards, transcribed from the rulebook.

The 1986 season card set is players and parks. It has no Fast Action
Card sheets. The deck is printed in the rulebook on pages 40-71, eight
cards to a page, 256 cards. engines/sim/fac_deck.json is that printing.
Nothing here is invented: a line that does not match the printed
vocabulary is stored raw and listed on the card as uncertain.

Pages 12-15 say how to draw. Two cards replace one four-dice roll: the
first card's 2d6 total, the next card's percentile. The small number
beside the 2d6 is the 1d6. A 1d10 is the rightmost percentile digit.
The deck is shuffled at the start and, as the book recommends, again
after every three full innings. The book also allows a hybrid, so a
check that needs the two separate dice (doubles, the low die) is not
read off the total.
"""
from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DECK_PATH = os.path.join(HERE, "fac_deck.json")

STEAL_GRADES = ("EXCELLENT", "VERY GOOD", "NORMAL", "FAIR", "POOR")
SAC_LETTERS = ("A", "B", "C", "D", "F")
SAC_RESULTS = {"SH", "LEAD", "MISS", "E?", "DP", "PO"}
HIT_GROUPS = ("1B,3B", "2B,SS,P", "OF")
ERR_GROUPS = ("C", "IF,P", "OF")

# Printed runner lines. The number is how far that runner goes.
# "score" from second is two bases. "+?" is a coach's-choice offer
# for the lead runner after the stated advance (pages 13-14).
RUNNER_LINES = {
    "Runner on 1st advances 1 base": ("first", 1, False),
    "Runner on 1st advances 2 bases": ("first", 2, False),
    "Runner on 1st advances 1 base +?": ("first", 1, True),
    "Runner on 1st advances 2 bases +?": ("first", 2, True),
    "Runner on 2nd scores": ("second", 2, False),
    "Runner on 2nd 1 base": ("second", 1, False),
    "Runner on 2nd 1 base +?": ("second", 1, True),
    "Runner on 2nd 2 bases": ("second", 2, False),
    "Runners advance 2 bases": ("all", 2, False),
    "Runners advance 2 bases +?": ("all", 2, True),
    "All Runners score": ("score", None, False),
}


def load_deck(path=None):
    with open(path or DECK_PATH, encoding="utf-8") as handle:
        data = json.load(handle)
    cards = data["cards"]
    if len(cards) != 256:
        raise SystemExit("FAC deck has %s cards, not 256" % len(cards))
    return cards


class FacRolls:
    """The dice object the game already calls, backed by the deck.

    pair() returns (None, None, total) because a card prints the 2d6
    total and not the two dice. A check that needs those two dice rolls
    real dice and says so.
    """

    def __init__(self, deck):
        self.deck = deck

    def d6(self):
        return self.deck.one_d6("1d6")

    def d10(self):
        return self.deck.one_d10("1d10")

    def pair(self):
        return None, None, self.deck.two_d6("2d6")

    def pct(self):
        return self.deck.percentile("pct")

    def take(self):
        return self.deck.take()


class Deck:
    """One shuffled FAC deck. draw() is the only way a card enters play."""

    def __init__(self, rng, cards=None):
        self.rng = rng
        self.cards = list(cards if cards is not None else load_deck())
        self.order = list(range(len(self.cards)))
        self.rng.shuffle(self.order)
        self.pos = 0
        self.last = None
        self.trace = []
        self.full_innings = 0

    def note_full_inning(self):
        """Page 12 recommends a shuffle after every three full innings."""
        self.full_innings += 1
        if self.full_innings % 3 == 0:
            self.reshuffle(
                "Recommended reshuffle after three full innings (page 12)."
            )

    def reshuffle(self, reason):
        self.rng.shuffle(self.order)
        self.pos = 0
        self.trace.append("FAC shuffle. %s" % reason)

    def draw(self, purpose):
        if self.pos >= len(self.order):
            self.reshuffle(
                "The deck was used through. Page 15 says not to play it straight through, so it is shuffled again."
            )
        card = self.cards[self.order[self.pos]]
        self.pos += 1
        self.last = card
        mark = " WP?" if card.get("wp") else ""
        self.trace.append(
            "FAC p%d r%d c%d %s 2d6=%s 1d6=%s%s pct=%02d"
            % (
                card["page"], card["row"], card["col"], purpose,
                card["d6_2"], card["d6_1"], mark, card["pct"],
            )
        )
        return card

    def take(self):
        done = self.trace
        self.trace = []
        return done

    def two_d6(self, purpose):
        return self.draw(purpose)["d6_2"]

    def percentile(self, purpose):
        return self.draw(purpose)["pct"]

    def one_d6(self, purpose):
        """The small number on the next card. Page 13."""
        return self.draw(purpose)["d6_1"]

    def one_d10(self, purpose):
        """Rightmost percentile digit. A one-digit percentile is used whole."""
        card = self.draw(purpose)
        return card["pct"] % 10


def star_bases(token):
    """'*' is one base, '**' two, '***' three. The third star is the dagger."""
    stars = token.count("*")
    if stars < 1 or stars > 3 or token.strip("*") != "":
        return None
    return stars


def parse_hit_cell(text):
    """'Double **' -> batter result, runner bases, dagger."""
    parts = text.split()
    if len(parts) != 2 or parts[0] not in {"Single", "Double"}:
        return None
    bases = star_bases(parts[1])
    if bases is None:
        return None
    kind = "1B" if parts[0] == "Single" else "2B"
    return {"result": kind, "bases": bases, "dagger": parts[1] == "***", "text": text}


def parse_err_cell(text):
    known = {
        "1 base": 1,
        "2 bases": 2,
        "3 bases": 3,
        "Single+1": "SINGLE+",
        "Drop foul": "FOUL",
    }
    if text not in known:
        return None
    return known[text]


def parse_out_cell(text):
    known = {
        "GB - fc": "GB-FC",
        "GB + adv": "GB-ADV",
        "Deep Fly": "DEEP",
        "Short Fly": "SHORT",
        "Popout": "POP",
        "Popout (foul)": "POP-FOUL",
        "Lineout": "LINE",
        "GB-DP A": "GB-DP-A",
        "GB-DP A, B": "GB-DP-AB",
        "LO - DP A, B": "LINE-DP-AB",
        "DP?": "SHORT-DP",
        "Short Fly - DP?": "SHORT-DP",
    }
    return known.get(text)


def parse_runner_line(text):
    return RUNNER_LINES.get(text)


def extract(pdf_path, out_path=None):
    """Read rulebook pages 40-71 and write fac_deck.json."""
    import fitz

    doc = fitz.open(pdf_path)
    cards = []
    cols = ((8, 198), (198, 400), (400, 600), (600, 792))
    for page_index in range(39, 71):
        page = doc[page_index]
        words = page.get_text("words")
        for row, y0, y1 in ((0, 0, 308), (1, 308, 620)):
            for col, (x0, x1) in enumerate(cols):
                boxed = [
                    w for w in words
                    if x0 <= w[0] < x1 and y0 <= w[1] < y1
                ]
                cards.append(_card(page_index + 1, row, col, x0, boxed))
    payload = {
        "source": (
            "Payoff Pitch Baseball rulebook, pages 40-71, eight cards a page. "
            "The 1986 season card set PDF contains the player cards and the park "
            "cards. It does not contain a Fast Action Card sheet, so the deck "
            "was read from the rulebook, which is the other official source."
        ),
        "count": len(cards),
        "cards": cards,
    }
    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=1, ensure_ascii=False)
            handle.write("\n")
    return payload


def _card(page, row, col, x0, words):
    uncertain = []
    kept = [w for w in words if not _is_footer(w)]
    raw = _raw_lines(kept)
    big = [w for w in kept if (w[3] - w[1]) >= 24 and _numberish(w[4])]
    big.sort(key=lambda w: w[0])
    mid = [
        w for w in kept
        if 14 <= (w[3] - w[1]) < 20 and w[4].isdigit() and w[4] in "123456"
    ]
    d6_2 = pct = d6_1 = None
    if len(big) != 2:
        uncertain.append("expected two large dice numbers, found %s" % [w[4] for w in big])
    else:
        d6_2 = int(big[0][4])
        pct = int(big[1][4])
        if not 2 <= d6_2 <= 12:
            uncertain.append("2d6 %s is outside 2-12" % d6_2)
        if not 0 <= pct <= 99:
            uncertain.append("percentile %s is outside 00-99" % pct)
    if len(mid) != 1:
        uncertain.append("expected one 1d6, found %s" % [w[4] for w in mid])
    else:
        d6_1 = int(mid[0][4])
    wp = any(w[4] == "WP?" for w in kept)
    if wp:
        uncertain.append(
            "WP? is printed beside the 1d6. Pages 12-15 do not say what it means, so it is not applied."
        )
    sections = _sections(kept, x0, uncertain)
    return {
        "page": page,
        "row": row,
        "col": col,
        "d6_2": d6_2,
        "d6_1": d6_1,
        "wp": wp,
        "pct": pct,
        "single": sections["single"],
        "double": sections["double"],
        "defense": sections["defense"],
        "hit": sections["hit"],
        "err": sections["err"],
        "out": sections["out"],
        "sac": sections["sac"],
        "steal": sections["steal"],
        "home": sections["home"],
        "uncertain": uncertain,
        "raw": raw,
    }


def _is_footer(word):
    if (word[3] - word[1]) < 9:
        return True
    return word[4] in {"PAYOFF", "PITCH", "BASEBALL"} or word[4].startswith("©")


def _numberish(token):
    return token.isdigit()


def _raw_lines(words):
    lines = []
    for _, group in _clusters(words):
        lines.append(" ".join(w[4] for w in sorted(group, key=lambda w: w[0])))
    return lines


def _clusters(words):
    ordered = sorted(words, key=lambda w: (w[1], w[0]))
    lines = []
    for word in ordered:
        if lines and abs(word[1] - lines[-1][0]) <= 2.4:
            lines[-1][1].append(word)
        else:
            lines.append([word[1], [word]])
    return lines


def _sections(words, x0, uncertain):
    lines = _clusters(words)
    single, double = _hit_blocks(lines, uncertain)
    defense = _defense(lines, uncertain)
    hit = _trio(lines, "HIT!", uncertain, "hit")
    err = _trio(lines, "ERR*", uncertain, "err")
    out = _trio(lines, "OUT#", uncertain, "out")
    sac, steal, home = _bottom(lines, x0, uncertain)
    return {
        "single": single,
        "double": double,
        "defense": defense,
        "hit": hit,
        "err": err,
        "out": out,
        "sac": sac,
        "steal": steal,
        "home": home,
    }


def _line_text(group):
    return " ".join(w[4] for w in sorted(group, key=lambda w: w[0]))


def _hit_blocks(lines, uncertain):
    single_at = _find(lines, "SINGLE")
    double_at = _find(lines, "DOUBLE:")
    defense_at = _find(lines, "DEFENSE")
    single = {"location": None, "lines": []}
    double = {"location": None, "lines": []}
    if single_at is None or double_at is None or defense_at is None:
        uncertain.append("missing SINGLE, DOUBLE, or DEFENSE label")
        return single, double
    single_lines = [_line_text(lines[i][1]) for i in range(single_at + 1, double_at)]
    double_lines = [_line_text(lines[i][1]) for i in range(double_at + 1, defense_at)]
    if single_lines:
        single["location"] = single_lines[0]
        single["lines"] = single_lines[1:]
    else:
        uncertain.append("SINGLE has no location line")
    if double_lines:
        double["location"] = double_lines[0]
        double["lines"] = double_lines[1:]
    else:
        uncertain.append("DOUBLE has no location line")
    for text in single["lines"] + double["lines"]:
        if parse_runner_line(text) is None:
            uncertain.append("runner line is not in the printed vocabulary: %s" % text)
    return single, double


def _find(lines, token):
    for index, (_, group) in enumerate(lines):
        texts = [w[4] for w in group]
        if token in texts:
            return index
    return None


def _defense(lines, uncertain):
    index = _find(lines, "DEFENSE")
    if index is None:
        return None
    texts = [w[4] for w in lines[index][1]]
    if "RARE" in texts and "PLAY" in texts:
        return {"check": "RARE", "pos": None, "text": "DEF RARE PLAY"}
    check = "ERROR" if "ERROR?" in texts else "RANGE" if "RANGE?" in texts else None
    pos = None
    for token in texts:
        if token in {"P", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"}:
            pos = token
    if check is None or pos is None:
        uncertain.append("DEFENSE line is not ERROR?/RANGE? plus a position: %s" % " ".join(texts))
    return {"check": check, "pos": pos, "text": " ".join(texts)}


_HIT_LINE = re.compile(
    r"^(Single|Double) (\*+) (Single|Double) (\*+) (Single|Double) (\*+)$"
)
_BOTTOM_LINE = re.compile(
    r"^(A|B|C|D|F) (SH|LEAD|MISS|E\?|DP|PO) "
    r"(EXCELLENT|VERY GOOD|NORMAL|FAIR|POOR) (Safe|Out|Drop\?|SB\+E2\?)$"
)
_SPECIAL_LINE = re.compile(r"^(A|B|C|D|F) PO (.+)$")
_ERR_PHRASES = ("Drop foul", "Single+1", "3 bases", "2 bases", "1 base")
_OUT_PHRASES = (
    "LO - DP A, B",
    "GB-DP A, B",
    "GB - fc",
    "GB + adv",
    "Deep Fly",
    "Short Fly",
    "Lineout",
    "Popout",
    "GB-DP A",
    "DP?",
)
_SPECIAL_STEAL = (
    "Refer to previous card's 1d6 result. 1-3 = Out and "
    "check runner for injury. 4-6 = Safe and check fielder for injury."
)


def _take_phrases(text, phrases):
    rest = text
    found = []
    while rest:
        match = next((phrase for phrase in phrases if rest.startswith(phrase)), None)
        if match is None:
            return None
        found.append(match)
        rest = rest[len(match):].lstrip()
    return found


def _trio(lines, label, uncertain, kind):
    index = _find(lines, label)
    if index is None:
        uncertain.append("missing %s" % label)
        return [None, None, None]
    result = None
    for _, group in lines[index + 1:index + 3]:
        text = _line_text(group)
        if text in {"1B,3B 2B,SS,P OF", "C IF,P OF"}:
            continue
        result = text
        break
    cells = None
    if result and kind == "hit":
        matched = _HIT_LINE.match(result)
        if matched:
            cells = [
                "%s %s" % (matched.group(1), matched.group(2)),
                "%s %s" % (matched.group(3), matched.group(4)),
                "%s %s" % (matched.group(5), matched.group(6)),
            ]
    elif result and kind == "err":
        cells = _take_phrases(result, _ERR_PHRASES)
    elif result and kind == "out":
        cells = _take_phrases(result, _OUT_PHRASES)
    if not cells or len(cells) != 3:
        uncertain.append("%s result could not be split into three columns: %s" % (label, result))
        return [None, None, None]
    for text in cells:
        if kind == "hit" and parse_hit_cell(text) is None:
            uncertain.append("HIT cell is not a printed star result: %s" % text)
        if kind == "err" and parse_err_cell(text) is None:
            uncertain.append("ERR cell is not a printed error result: %s" % text)
        if kind == "out" and parse_out_cell(text) is None:
            uncertain.append("OUT cell is not a printed out result: %s" % text)
    return cells


def _bottom(lines, x0, uncertain):
    del x0
    sac = {}
    steal = {"grades": {}, "special": None}
    home = None
    sac_index = _find(lines, "Sac")
    if sac_index is None:
        uncertain.append("missing Sac Bunt")
        return sac, steal, home
    special_parts = []
    for _, group in lines[sac_index + 1:]:
        text = _line_text(group)
        if "HOME" in text:
            home = text
            break
        matched = _BOTTOM_LINE.match(text)
        if matched:
            letter, result, grade, outcome = matched.groups()
            sac[letter] = result
            steal["grades"][grade] = outcome
            continue
        special = _SPECIAL_LINE.match(text)
        if special:
            sac[special.group(1)] = "PO"
            special_parts.append(special.group(2))
            continue
        if text in {"C", "P", "1B", "3B"}:
            home = text
            uncertain.append(
                "HOME line is only %s. The result words are not on the card, so a play at home is not read from it."
                % text
            )
            break
        uncertain.append("bottom line is not a sac/steal row or a HOME row: %s" % text)
    if special_parts:
        steal["special"] = " ".join(special_parts)
        if steal["special"] != _SPECIAL_STEAL:
            uncertain.append(
                "special steal text does not match the printed injury instruction: %s" % steal["special"]
            )
    elif len(steal["grades"]) != 5:
        uncertain.append("stealing column has %s grades" % sorted(steal["grades"]))
    if any(letter not in sac for letter in SAC_LETTERS):
        uncertain.append("sac column is missing %s" % [letter for letter in SAC_LETTERS if letter not in sac])
    if home is None:
        uncertain.append("no HOME line")
    return sac, steal, home


def _grade_of(text):
    for grade in STEAL_GRADES:
        if text.startswith(grade + " ") or text == grade:
            return grade
    return None


if __name__ == "__main__":
    import sys
    pdf = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else DECK_PATH
    payload = extract(pdf, out)
    cards = payload["cards"]
    flagged = [c for c in cards if c["uncertain"]]
    print("cards", len(cards))
    print("flagged", len(flagged))
    for card in flagged:
        print("p%s r%s c%s" % (card["page"], card["row"], card["col"]), card["uncertain"])
