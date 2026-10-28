#!/usr/bin/env python3
"""
hitting_engine.py -- style-first HITTING CARD ENGINE, prototype v1
(workshop, 2026-10-27). NOT the frozen Hitter Engine v0.5 and not used
by any converted set: this prototype learns the band-allocation grammar
of the OFFICIAL 1986 Payoff Pitch cards and is validated against them.

Feed it a hitter's per-side stat line (AB, 2B, 3B, HR, BB, SO, AVG,
OBP, SLG against that side's pitching) and it generates the percentile
band widths for TOUGH, PATIENT and WHEELHOUSE on that side, laid out in
the printed cards' canonical order. IN-PLAY and the OUT table are out
of scope for v1 (no comparably clean grammar found yet; separate dive).

v1.1 addendum (same night): IN-PLAY is now generated too, by
`generate_inplay` below, fitted in the same `Engine.fit` pass and
validated in `validate_inplay.py` (see INPLAY_REPORT.md). The census
of all 1,192 printed sides: IN-PLAY carries ONLY hits -- 1B on 1,054
sides, 2B on 793, 3B on 10, and HR / BB / HBP / SO on none. Its two
live strands price off their own rates exactly like the other bands
(1B off the singles rate, 2B off the doubles rate); direct strands
beat a TOUGH-style hit bundle + remainder on training MAE for both
the total (2.19 vs 2.85) and 1B (1.78 vs 2.61), so no bundle is used.
3B joins the hard zeros: its training median is 0 in every
triples-rate decile. The OUT table remains out of scope. Nothing in
v1's three-band fit or generation changed.

The grammar (fitted on a training subset only, see validate.py):
  * every outcome strand prices off its OWN rate, via a decile bucket
    table (training medians, monotone-enforced, linear interpolation):
      TOUGH SO      <- strikeout rate (SO per PA)
      TOUGH 2B/3B   <- doubles / triples rate per AB
      PATIENT BB    <- walk rate (BB per PA); NO residual power premium
                       (checked: at fixed walk rate the ISO gradient is
                       flat, so the slugger's bigger BB band is entirely
                       his higher walk rate)
      PATIENT 2B/3B <- doubles / triples rate
      PATIENT 1B    <- singles rate, 2-way with walk rate (room left)
      WHEEL HR      <- home-run rate per AB
      WHEEL 2B/3B   <- doubles / triples rate
      WHEEL 1B      <- singles rate, 2-way with ISO (power displaces)
  * TOUGH hit points are the one total priced as a bundle: a 2-way
    bucket table over batting average (quintile) x strikeout rate
    (tercile) -- the style axes. The 2B/3B strands price off their own
    rates and 1B takes the remainder, so the archetype's mix emerges.
  * PATIENT HBP has no driver in the stat line (the cards print no HBP
    counting stat): it takes the archetype's median width.
  * HARD RULES from the population census: TOUGH never prints a homer
    (0 of 1,192 sides), PATIENT never prints a homer or a strikeout,
    WHEELHOUSE never prints a walk or a strikeout. The engine cannot
    emit them.

Archetypes (from the combined two-side line) -- the style lens the
mixes are reported through, and the carrier of the HBP constant:
  free-swinger : strikeout rate >= .200
  power        : ISO >= .170 (and not a free-swinger)
  contact      : ISO <= .130 and AVG >= .255 (and not a free-swinger)
  balanced     : everyone else

CLI demo:  python3 hitting_engine.py --demo
Library:   eng = Engine.fit(train_cards); eng.generate(stats_L, arch)
"""
import hashlib
import json
import math
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECTIONS = ("TOUGH", "PATIENT", "WHEELHOUSE")
# canonical printed layout order per section
LAYOUT = {
    "TOUGH": ("SO", "2B", "3B", "1B"),
    "PATIENT": ("BB", "2B", "3B", "1B", "HBP"),
    "WHEELHOUSE": ("HR", "2B", "3B", "1B"),
    "INPLAY": ("2B", "3B", "1B"),
}
MIN_FIT_AB = 40  # per-side AB floor for fitting (tiny samples are noise)

# Ceiling extrapolation (v1.2.1, 2026-10-28, sandbox PR). The 1986 cards top
# out near 40 HR and ~100-110 walks, so the decile tables went flat above the
# fattest 1986 rate and a Ruth/Bonds/McGwire line got a 1986-max HR or BB band
# (plus filler singles where the missing HR room was). With this on, the two
# strands WHEEL HR and PATIENT BB keep rising past the highest rate seen in
# training, in proportion to the real rate (slope = top-decile width / rate),
# and a section pushed past 99 faces gives up singles first, never the
# extrapolated strand. A line inside the training range is generated exactly
# as before (as is any side under the MIN_FIT_AB floor). Set False (or Engine.fit(..., extrapolate=False)) for the old
# v1.2 behavior.
EXTRAPOLATE_CEILING = True
# Separate, default OFF: when a section inside the training range overflows 99,
# trim singles first instead of the widest strand (usually HR or BB). It changes
# 89 of 1,160 printed 1986 sides, and fits the printed widths better there
# (on the 61 fit-size sides, WHEELHOUSE+PATIENT abs error 2,220 -> 1,804; 741 -> 595 on the
# md5 holdout), but it is not a ceiling fix, so it waits for the owner's call.
TRIM_SINGLES_FIRST = False
EXTRAPOLATED = (("WHEELHOUSE", "HR", "wheel_hr", "hr_rate"),
                ("PATIENT", "BB", "patient_bb", "bb_rate"))
# when a section overflows because of an extrapolated strand, trim in this order
TRIM_ORDER = {"WHEELHOUSE": ("1B", "2B", "3B"),
              "PATIENT": ("1B", "2B", "3B", "HBP")}


# ---------------------------------------------------------------- data
def load_cards():
    return json.loads((HERE / "dataset.json").read_text())


def card_totals(card):
    tot = {"AB": 0, "BB": 0, "SO": 0, "HR": 0, "H": 0.0, "TB": 0.0}
    ok = True
    for side in ("L", "R"):
        s = card["stats"].get(side) or {}
        if not s.get("AB") or s.get("AVG") is None or s.get("SLG") is None:
            ok = False
            continue
        tot["AB"] += s["AB"]
        tot["BB"] += s.get("BB") or 0
        tot["SO"] += s.get("SO") or 0
        tot["HR"] += s.get("HR") or 0
        tot["H"] += s["AVG"] * s["AB"]
        tot["TB"] += s["SLG"] * s["AB"]
    if not ok or tot["AB"] == 0:
        return None
    tot["AVG"] = tot["H"] / tot["AB"]
    tot["ISO"] = tot["TB"] / tot["AB"] - tot["AVG"]
    tot["SO_RATE"] = tot["SO"] / (tot["AB"] + tot["BB"])
    return tot


def classify(tot):
    """Style archetype from the combined line (see module docstring)."""
    if tot is None:
        return "unknown"
    if tot["SO_RATE"] >= 0.200:
        return "free-swinger"
    if tot["ISO"] >= 0.170:
        return "power"
    if tot["ISO"] <= 0.130 and tot["AVG"] >= 0.255:
        return "contact"
    return "balanced"


def side_features(s):
    """Rate features for one side's stat line."""
    ab = s.get("AB") or 0
    bb = s.get("BB") or 0
    pa = ab + bb
    if ab == 0 or pa == 0 or s.get("AVG") is None or s.get("SLG") is None:
        return None
    avg, slg = s["AVG"], s["SLG"]
    h = avg * ab
    xbh = (s.get("2B") or 0) + (s.get("3B") or 0) + (s.get("HR") or 0)
    return {
        "ab": ab, "pa": pa, "avg": avg, "slg": slg, "iso": slg - avg,
        "obp": s.get("OBP") or 0.0,
        "so_rate": (s.get("SO") or 0) / pa,
        "bb_rate": bb / pa,
        "hr_rate": (s.get("HR") or 0) / ab,
        "b2_rate": (s.get("2B") or 0) / ab,
        "b3_rate": (s.get("3B") or 0) / ab,
        "singles_rate": (h - xbh) / ab,
    }


def split_cards(cards):
    """Documented holdout: md5(name) mod 3 == 0 -> TEST (never fitted).
    Split is by card, so a player's two sides never straddle the line."""
    train, test = [], []
    for c in cards:
        h = int(hashlib.md5(c["name"].encode()).hexdigest(), 16)
        (test if h % 3 == 0 else train).append(c)
    return train, test


# ------------------------------------------------------------ fit tools
def _quantile_cuts(vals, k):
    srt = sorted(vals)
    return [srt[min(len(srt) - 1, int(q * len(srt) / k))]
            for q in range(1, k)]


def _bucket(v, cuts):
    return sum(v > c for c in cuts)


class DecileTable:
    """Monotone bucket-median table with linear interpolation."""

    def __init__(self, xs, ys, k=10):
        pairs = sorted(zip(xs, ys))
        n = len(pairs)
        self.centers, self.values = [], []
        self.x_max = pairs[-1][0] if pairs else 0.0
        for i in range(k):
            chunk = pairs[i * n // k:(i + 1) * n // k]
            if not chunk:
                continue
            self.centers.append(st.median([p[0] for p in chunk]))
            self.values.append(st.median([p[1] for p in chunk]))
        # enforce non-decreasing (all engine relations are increasing)
        for i in range(1, len(self.values)):
            self.values[i] = max(self.values[i], self.values[i - 1])

    def predict(self, x, extrapolate=False):
        c, v = self.centers, self.values
        if x <= c[0]:
            return v[0]
        if extrapolate and x > self.x_max and c[-1] > 0:
            # beyond every training rate: keep rising in proportion to the
            # real rate, continuous with the flat top at the training max
            return v[-1] + (x - self.x_max) * v[-1] / c[-1]
        if x >= c[-1]:
            return v[-1]
        for i in range(1, len(c)):
            if x <= c[i]:
                t = (x - c[i - 1]) / (c[i] - c[i - 1]) if c[i] > c[i - 1] else 0
                return v[i - 1] + t * (v[i] - v[i - 1])
        return v[-1]

    def as_rows(self):
        return [(round(c, 4), round(v, 1))
                for c, v in zip(self.centers, self.values)]


class TwoWayTable:
    """Median table over driver A quintiles x driver B terciles,
    monotone-smoothed: non-decreasing in A, non-increasing in B."""

    def __init__(self, rows, key_a, key_b, target):
        self.cuts_a = _quantile_cuts([r[key_a] for r in rows], 5)
        self.cuts_b = _quantile_cuts([r[key_b] for r in rows], 3)
        grid = [[None] * 3 for _ in range(5)]
        for i in range(5):
            for j in range(3):
                cell = [target(r) for r in rows
                        if _bucket(r[key_a], self.cuts_a) == i
                        and _bucket(r[key_b], self.cuts_b) == j]
                grid[i][j] = st.median(cell) if cell else None
        # fill holes from row/col neighbours, then smooth
        for i in range(5):
            for j in range(3):
                if grid[i][j] is None:
                    near = [grid[a][b] for a in range(5) for b in range(3)
                            if grid[a][b] is not None]
                    grid[i][j] = st.median(near)
        for j in range(3):  # non-decreasing down A
            for i in range(1, 5):
                grid[i][j] = max(grid[i][j], grid[i - 1][j])
        for i in range(5):  # non-increasing across B
            for j in range(1, 3):
                grid[i][j] = min(grid[i][j], grid[i][j - 1])
        self.grid = grid

    def predict(self, a, b):
        return self.grid[_bucket(a, self.cuts_a)][_bucket(b, self.cuts_b)]


def _mae(preds, actuals):
    return (sum(abs(p - a) for p, a in zip(preds, actuals)) / len(actuals)
            if actuals else float("nan"))


# ---------------------------------------------------------------- engine
class Engine:
    def __init__(self, extrapolate=None, trim_singles_first=None):
        self.tables = {}
        self.diagnostics = {}
        self.extrapolate = EXTRAPOLATE_CEILING if extrapolate is None else extrapolate
        self.trim_singles_first = (TRIM_SINGLES_FIRST if trim_singles_first is None
                                   else trim_singles_first)

    @classmethod
    def fit(cls, train_cards, extrapolate=None, trim_singles_first=None):
        eng = cls(extrapolate, trim_singles_first)
        rows = []  # (features, widths, archetype)
        for c in train_cards:
            arch = classify(card_totals(c))
            for side in ("L", "R"):
                s = c["stats"].get(side) or {}
                f = side_features(s)
                if f is None or f["ab"] < MIN_FIT_AB:
                    continue
                rows.append((f, c["widths"][side], arch))
        eng.n_fit_sides = len(rows)
        eng.archetypes_fit = sorted({a for _, _, a in rows})

        def col(sec, oc):
            return [w[sec][oc] for _, w, _ in rows]

        def fit1d(driver, sec, oc, label):
            xs = [f[driver] for f, _, _ in rows]
            ys = col(sec, oc)
            tab = DecileTable(xs, ys)
            eng.tables[label] = tab
            eng.diagnostics[label] = {
                "driver": driver, "train_mae":
                round(_mae([tab.predict(x) for x in xs], ys), 2)}

        # TOUGH
        fit1d("so_rate", "TOUGH", "SO", "tough_so")
        fit1d("b2_rate", "TOUGH", "2B", "tough_2b")
        fit1d("b3_rate", "TOUGH", "3B", "tough_3b")
        paired = [(f, w) for f, w, _ in rows]
        tough_hits = _two_way_with_targets(
            [p[0] for p in paired], "avg", "so_rate",
            [p[1]["TOUGH"]["1B"] + p[1]["TOUGH"]["2B"] + p[1]["TOUGH"]["3B"]
             for p in paired],
            smooth="avg_up_so_down")
        eng.tables["tough_hits"] = tough_hits
        eng.diagnostics["tough_hits"] = {
            "driver": "avg x so_rate",
            "train_mae": round(_mae(
                [tough_hits.predict(f["avg"], f["so_rate"]) for f, _, _ in rows],
                [w["TOUGH"]["1B"] + w["TOUGH"]["2B"] + w["TOUGH"]["3B"]
                 for _, w, _ in rows]), 2)}

        # PATIENT
        fit1d("bb_rate", "PATIENT", "BB", "patient_bb")
        fit1d("b2_rate", "PATIENT", "2B", "patient_2b")
        fit1d("b3_rate", "PATIENT", "3B", "patient_3b")
        # PATIENT 1B: 1D on singles rate vs 2-way singles x bb_rate;
        # keep whichever fits training better (documented choice).
        xs = [f["singles_rate"] for f, _, _ in rows]
        ys = col("PATIENT", "1B")
        tab1 = DecileTable(xs, ys)
        mae1 = _mae([tab1.predict(x) for x in xs], ys)
        tab2 = _two_way_with_targets(
            [f for f, _, _ in rows], "singles_rate", "bb_rate", ys)
        mae2 = _mae([tab2.predict(f["singles_rate"], f["bb_rate"])
                     for f, _, _ in rows], ys)
        if mae2 < mae1 * 0.95:
            eng.tables["patient_1b"] = tab2
            eng.diagnostics["patient_1b"] = {
                "driver": "singles_rate x bb_rate (2-way chosen)",
                "train_mae": round(mae2, 2), "alt_1d_mae": round(mae1, 2)}
        else:
            eng.tables["patient_1b"] = tab1
            eng.diagnostics["patient_1b"] = {
                "driver": "singles_rate", "train_mae": round(mae1, 2),
                "alt_2way_mae": round(mae2, 2)}

        # WHEELHOUSE
        fit1d("hr_rate", "WHEELHOUSE", "HR", "wheel_hr")
        fit1d("b2_rate", "WHEELHOUSE", "2B", "wheel_2b")
        fit1d("b3_rate", "WHEELHOUSE", "3B", "wheel_3b")
        xs = [f["singles_rate"] for f, _, _ in rows]
        ys = col("WHEELHOUSE", "1B")
        tab1 = DecileTable(xs, ys)
        mae1 = _mae([tab1.predict(x) for x in xs], ys)
        tab2 = _two_way_with_targets(
            [f for f, _, _ in rows], "singles_rate", "iso", ys)
        mae2 = _mae([tab2.predict(f["singles_rate"], f["iso"])
                     for f, _, _ in rows], ys)
        if mae2 < mae1 * 0.95:
            eng.tables["wheel_1b"] = tab2
            eng.diagnostics["wheel_1b"] = {
                "driver": "singles_rate x iso (2-way chosen)",
                "train_mae": round(mae2, 2), "alt_1d_mae": round(mae1, 2)}
        else:
            eng.tables["wheel_1b"] = tab1
            eng.diagnostics["wheel_1b"] = {
                "driver": "singles_rate", "train_mae": round(mae1, 2),
                "alt_2way_mae": round(mae2, 2)}

        # IN-PLAY (v1.1 addendum): hits only in print (census in the
        # module docstring). 1B and 2B price off their own rates,
        # strand by strand; a bundle + remainder fit was tested and
        # lost on training MAE (see docstring), so none is used.
        fit1d("singles_rate", "INPLAY", "1B", "inplay_1b")
        fit1d("b2_rate", "INPLAY", "2B", "inplay_2b")

        # PATIENT HBP: archetype median (no stat-line driver exists)
        eng.hbp_by_arch = {}
        for arch in eng.archetypes_fit + ["balanced", "contact", "power",
                                          "free-swinger", "unknown"]:
            vals = [w["PATIENT"]["HBP"] for _, w, a in rows if a == arch]
            allv = [w["PATIENT"]["HBP"] for _, w, _ in rows]
            eng.hbp_by_arch[arch] = (round(st.median(vals)) if vals
                                     else round(st.median(allv)))
        eng.hbp_overall = round(st.median(
            [w["PATIENT"]["HBP"] for _, w, _ in rows]))

        # archetype TOUGH mix shares (grammar documentation)
        eng.arch_tough_mix = {}
        for arch in eng.archetypes_fit:
            sub = [(w["TOUGH"]["1B"], w["TOUGH"]["2B"], w["TOUGH"]["3B"])
                   for _, w, a in rows if a == arch]
            tot = [sum(x) for x in sub if sum(x) > 0]
            if tot:
                eng.arch_tough_mix[arch] = {
                    oc: round(st.mean([x[i] / sum(x) for x in sub
                                       if sum(x) > 0]), 3)
                    for i, oc in enumerate(("1B", "2B", "3B"))}
        return eng

    # ------------------------------------------------------------ generate
    def generate(self, stats_side, archetype="balanced"):
        """stats_side: one side's printed stat line (dict with AB, 2B,
        3B, HR, BB, SO, AVG, OBP, SLG). Returns {section: {outcome: int
        width}} with the hard structural rules applied."""
        f = side_features(stats_side)
        if f is None:
            raise ValueError("stat line needs AB, AVG, SLG")
        t = self.tables
        gen = {sec: {} for sec in SECTIONS}

        def rnd(x):
            return max(0, int(math.floor(x + 0.5)))

        # TOUGH: SO off the whiff rate; hit bundle off AVG x SO table;
        # 2B/3B strands off their own rates; 1B takes the remainder.
        gen["TOUGH"]["SO"] = rnd(t["tough_so"].predict(f["so_rate"]))
        hits = rnd(t["tough_hits"].predict(f["avg"], f["so_rate"]))
        b2 = rnd(t["tough_2b"].predict(f["b2_rate"]))
        b3 = rnd(t["tough_3b"].predict(f["b3_rate"]))
        if b2 + b3 > hits:  # keep strands inside the bundle
            scale = hits / (b2 + b3) if (b2 + b3) else 0
            b2, b3 = rnd(b2 * scale), rnd(b3 * scale)
        gen["TOUGH"]["2B"] = b2
        gen["TOUGH"]["3B"] = b3
        gen["TOUGH"]["1B"] = max(0, hits - b2 - b3)
        gen["TOUGH"]["HR"] = 0  # hard rule: no TOUGH homers, ever

        # PATIENT: walks off the walk rate (no power premium in print);
        # hit strands off their own rates; HBP is the archetype median.
        # tiny samples (under the fit floor) are noise, not a real rate
        ext = self.extrapolate and f["ab"] >= MIN_FIT_AB
        gen["PATIENT"]["BB"] = rnd(t["patient_bb"].predict(f["bb_rate"], ext))
        gen["PATIENT"]["2B"] = rnd(t["patient_2b"].predict(f["b2_rate"]))
        gen["PATIENT"]["3B"] = rnd(t["patient_3b"].predict(f["b3_rate"]))
        p1 = t["patient_1b"]
        gen["PATIENT"]["1B"] = rnd(
            p1.predict(f["singles_rate"], f["bb_rate"])
            if isinstance(p1, TwoWayTable) else p1.predict(f["singles_rate"]))
        gen["PATIENT"]["HBP"] = self.hbp_by_arch.get(
            archetype, self.hbp_overall)
        gen["PATIENT"]["HR"] = 0
        gen["PATIENT"]["SO"] = 0

        # WHEELHOUSE: power lives here; every strand off its own rate.
        gen["WHEELHOUSE"]["HR"] = rnd(t["wheel_hr"].predict(f["hr_rate"], ext))
        gen["WHEELHOUSE"]["2B"] = rnd(t["wheel_2b"].predict(f["b2_rate"]))
        gen["WHEELHOUSE"]["3B"] = rnd(t["wheel_3b"].predict(f["b3_rate"]))
        w1 = t["wheel_1b"]
        gen["WHEELHOUSE"]["1B"] = rnd(
            w1.predict(f["singles_rate"], f["iso"])
            if isinstance(w1, TwoWayTable) else w1.predict(f["singles_rate"]))
        gen["WHEELHOUSE"]["BB"] = 0
        gen["WHEELHOUSE"]["SO"] = 0

        # beyond-range strands: cap at 99, then other strands make room,
        # singles first (they were filling the HR / BB room)
        beyond = set()
        if ext:
            for sec, oc, label, rate in EXTRAPOLATED:
                if f[rate] > t[label].x_max:
                    beyond.add(sec)
                    gen[sec][oc] = min(gen[sec][oc], 99)
                    over = sum(gen[sec].values()) - 99
                    for k in TRIM_ORDER[sec]:
                        if over <= 0:
                            break
                        cut = min(over, gen[sec][k])
                        gen[sec][k] -= cut
                        over -= cut
        # no section may cover more than the 99 live points
        for sec in SECTIONS:
            tot = sum(gen[sec].values())
            if tot > 99 and sec not in beyond and self.trim_singles_first and sec in TRIM_ORDER:
                # HR / BB are the strands the line is about: singles give
                # way first (old rule cut the widest strand, usually HR/BB)
                over = tot - 99
                for k in TRIM_ORDER[sec]:
                    cut = min(over, gen[sec][k])
                    gen[sec][k] -= cut
                    over -= cut
            elif tot > 99 and sec not in beyond:
                biggest = max(LAYOUT[sec], key=lambda oc: gen[sec][oc])
                gen[sec][biggest] -= tot - 99
        return gen

    # ------------------------------------------------------ IN-PLAY v1.1
    def generate_inplay(self, stats_side, archetype="balanced"):
        """IN-PLAY band widths for one side (v1.1 addendum; see
        INPLAY_REPORT.md). Returns {outcome: int width} for all seven
        outcomes. HR, BB, HBP and SO are hard zeros (the section never
        prints them, 0 of 1,192 sides) and 3B is a hard zero (printed
        on 10 of 1,192 sides; no stat-line rate prices it). The
        archetype argument is accepted for symmetry with generate();
        no IN-PLAY strand prices off it."""
        f = side_features(stats_side)
        if f is None:
            raise ValueError("stat line needs AB, AVG, SLG")
        t = self.tables

        def rnd(x):
            return max(0, int(math.floor(x + 0.5)))

        gen = {"HR": 0, "BB": 0, "HBP": 0, "SO": 0, "3B": 0}
        gen["2B"] = rnd(t["inplay_2b"].predict(f["b2_rate"]))
        gen["1B"] = rnd(t["inplay_1b"].predict(f["singles_rate"]))
        tot = sum(gen.values())
        if tot > 99:  # never cover more than the 99 live points
            gen["1B"] -= tot - 99
        return gen

    def inplay_grammar(self):
        """The fitted IN-PLAY relations, as readable rows."""
        out = {}
        for label in ("inplay_1b", "inplay_2b"):
            tab = self.tables[label]
            if isinstance(tab, DecileTable):
                out[label] = tab.as_rows()
        out["diagnostics"] = {k: self.diagnostics[k]
                              for k in ("inplay_1b", "inplay_2b")}
        return out

    def grammar(self):
        """The fitted relations, as readable rows for the report."""
        out = {}
        for label in ("tough_so", "patient_bb", "wheel_hr",
                      "tough_2b", "patient_2b", "wheel_2b"):
            tab = self.tables[label]
            if isinstance(tab, DecileTable):
                out[label] = tab.as_rows()
        th = self.tables["tough_hits"]
        out["tough_hits_grid"] = {
            "avg_cuts": [round(x, 3) for x in th.cuts_a],
            "so_cuts": [round(x, 3) for x in th.cuts_b],
            "grid": [[round(v, 1) for v in row] for row in th.grid],
        }
        out["hbp_by_arch"] = self.hbp_by_arch
        out["arch_tough_mix"] = self.arch_tough_mix
        out["diagnostics"] = self.diagnostics
        return out


def _two_way_with_targets(rows, key_a, key_b, targets, smooth=None):
    """TwoWayTable variant taking an explicit target list. With
    smooth='avg_up_so_down' the grid is made non-decreasing down axis A
    and non-increasing across axis B (the TOUGH-hits shape)."""
    tab = TwoWayTable.__new__(TwoWayTable)
    tab.cuts_a = _quantile_cuts([r[key_a] for r in rows], 5)
    tab.cuts_b = _quantile_cuts([r[key_b] for r in rows], 3)
    grid = [[None] * 3 for _ in range(5)]
    for i in range(5):
        for j in range(3):
            cell = [t for r, t in zip(rows, targets)
                    if _bucket(r[key_a], tab.cuts_a) == i
                    and _bucket(r[key_b], tab.cuts_b) == j]
            grid[i][j] = st.median(cell) if cell else None
    for i in range(5):
        for j in range(3):
            if grid[i][j] is None:
                near = [grid[a][b] for a in range(5) for b in range(3)
                        if grid[a][b] is not None]
                grid[i][j] = st.median(near)
    if smooth == "avg_up_so_down":
        for j in range(3):
            for i in range(1, 5):
                grid[i][j] = max(grid[i][j], grid[i - 1][j])
        for i in range(5):
            for j in range(1, 3):
                grid[i][j] = min(grid[i][j], grid[i][j - 1])
    tab.grid = grid
    return tab


def layout_ranges(gen_sec, order):
    """Lay widths out contiguously from 1 in canonical order and
    render as printed-style range strings."""
    out, cur = {}, 1
    for oc in order:
        w = gen_sec.get(oc, 0)
        if w > 0:
            out[oc] = f"{cur}-{cur + w - 1}" if w > 1 else f"{cur}"
            cur += w
        else:
            out[oc] = ""
    return out


def demo():
    cards = load_cards()
    train, _ = split_cards(cards)
    eng = Engine.fit(train)
    print(f"fitted on {eng.n_fit_sides} training sides "
          f"(archetypes: {', '.join(eng.archetypes_fit)})")
    for name in ("Tony Fernandez", "Dave Kingman", "Wade Boggs"):
        c = next(x for x in cards if x["name"] == name)
        tot = card_totals(c)
        arch = classify(tot)
        print(f"\n=== {name} ({c['team']}) -- archetype: {arch}, "
              f"line: .{int(tot['AVG']*1000):03d} AVG, ISO {tot['ISO']:.3f}, "
              f"SO rate {tot['SO_RATE']:.3f}")
        for side in ("L", "R"):
            s = c["stats"][side]
            gen = eng.generate(s, arch)
            print(f" vs{side} (AB {s['AB']}, AVG {s['AVG']}, SLG {s['SLG']}):")
            for sec in SECTIONS:
                g = layout_ranges(gen[sec], LAYOUT[sec])
                p = {oc: (f"{c['widths'][side][sec][oc]}"
                          if c["widths"][side][sec][oc] else "-")
                     for oc in LAYOUT[sec]}
                print(f"   {sec:10s} gen " +
                      "  ".join(f"{oc} {g[oc] or '-':>7s}" for oc in LAYOUT[sec]))
                print(f"   {'':10s} prt " +
                      "  ".join(f"{oc} {p[oc]:>7s}" for oc in LAYOUT[sec]) +
                      "   (printed shown as widths)")


if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        demo()
    else:
        print("usage: hitting_engine.py --demo   (or import Engine)")


# ============================================================== OUT chart
# v1.2 addendum (2026-10-27, OUT chart dive; see OUTCHART_REPORT.md).
# Everything below is additive: no v1 / v1.1 fit or generation code is
# altered. The dive's findings, in brief: every printed OUT table is
# the same 15-slot template (codes P4 P6 P2 P3 P5 G1 L4 G3 L6 G5 plus
# an outfield tail whose order mirrors by handedness) tiling
# [start, 99] contiguously, so coverage is one number (width =
# 100 - start). L4 and L6 are 1 point on all 596 cards. The type mix
# (G/F/P/L) is individualized only mildly, mostly through the start
# slot P4, which is priced off the quality axis (AVG / SO rate). The
# directional mix (pull / middle / opposite) is a handedness template:
# it does not track power, spray reputation, or anything else in the
# line beyond a few points. Accordingly this generator works at the
# SHARE level -- printed type shares, directional shares (mapping A
# of the report), and the start point -- and does not pretend to
# regenerate the exact percentile ranges slot by slot.
#
# Records schema (plain dicts, see load_out_records):
#   {"name", "bats" ("L"/"R"/"B"), "archetype",
#    "totals": {"AVG", "ISO", "SO_RATE", "HR_RATE", "B3_RATE",
#               "BB_RATE", "AB"},
#    "type_shares": {"G","F","P","L"}, "dirA": {"pull","middle","opp"},
#    "start": int}

OUT_TYPE_KEYS = ("G", "F", "P", "L")
OUT_DIR_KEYS = ("pull", "middle", "opp")
OUT_MIN_FIT_AB = 100  # combined-AB floor for fitting the OUT models


def _out_is_test(name):
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    return h % 3 == 0


def load_out_records():
    """Join dataset.json (stat lines) with out_dataset.json (printed
    OUT tables from extract_out_dataset.py) into generator records."""
    cards = {(c["name"], c["page"]): c for c in load_cards()}
    raw = json.loads((HERE / "out_dataset.json").read_text())
    records = []
    for r in raw:
        c = cards.get((r["name"], r["page"]))
        if c is None:
            continue
        tot = card_totals(c)
        ab = tot["AB"] if tot else 0
        b3 = sum((c["stats"][s].get("3B") or 0) for s in ("L", "R"))
        bb = tot["BB"] if tot else 0
        totals = None
        if tot is not None:
            totals = {"AVG": tot["AVG"], "ISO": tot["ISO"],
                      "SO_RATE": tot["SO_RATE"],
                      "HR_RATE": (tot["HR"] / ab) if ab else 0.0,
                      "B3_RATE": (b3 / ab) if ab else 0.0,
                      "BB_RATE": (bb / (ab + bb)) if (ab + bb) else 0.0,
                      "AB": ab}
        records.append({
            "name": r["name"], "bats": r["bats"],
            "archetype": classify(tot), "totals": totals,
            "type_shares": r["type_shares"], "dirA": r.get("dirA"),
            "start": r["start"]})
    return records


def _share_median(recs, key, sub=None):
    """Component-wise median share vector, renormalized to sum 1."""
    keys = OUT_TYPE_KEYS if key == "type_shares" else OUT_DIR_KEYS
    vec = {}
    for k in keys:
        vals = [r[key][k] for r in recs
                if r.get(key) and (sub is None or sub(r))]
        vec[k] = st.median(vals) if vals else 0.0
    tot = sum(vec.values())
    return {k: (v / tot if tot else 0.0) for k, v in vec.items()}


def _renorm(vec, keys):
    tot = sum(max(0.0, vec.get(k, 0.0)) for k in keys)
    return {k: (max(0.0, vec.get(k, 0.0)) / tot if tot else 0.0)
            for k in keys}


class OutMixModel:
    """Share-level OUT-chart generator (v1.2 addendum). Fitted on
    TRAIN records only by fit_outmix; candidate model families are
    compared on training MAE and the winner per target is stored, in
    the same documented-choice style as the v1 PATIENT 1B fit."""

    def __init__(self):
        self.choice = {}
        self.diag = {}

    @classmethod
    def fit(cls, records):
        m = cls()
        fit = [r for r in records if r["totals"]
               and r["totals"]["AB"] >= OUT_MIN_FIT_AB]
        m.n_fit = len(fit)

        def mae(vecs, key):
            keys = OUT_TYPE_KEYS if key == "type_shares" else OUT_DIR_KEYS
            errs = [abs(v[k] - r[key][k]) for v, r in zip(vecs, fit)
                    for k in keys if r.get(key)]
            return sum(errs) / len(errs) if errs else float("nan")

        # ---- type shares: global vs archetype vs driver-priced ----
        glob = _share_median(fit, "type_shares")
        by_arch = {a: _share_median(fit, "type_shares",
                                    lambda r, a=a: r["archetype"] == a)
                   for a in {r["archetype"] for r in fit}}
        m.type_global, m.type_by_arch = glob, by_arch
        cand = {"global": [glob] * len(fit),
                "archetype": [by_arch[r["archetype"]] for r in fit]}
        # driver-priced: per-share decile table on the best single
        # driver (train MAE) among so_rate / avg / iso; either
        # orientation is allowed (DecileTable enforces an increasing
        # relation, so a decreasing one is fitted on the negated
        # driver); L = remainder
        tabs, drivers = {}, {}
        for t in ("G", "F", "P"):
            best = None
            for drv, key in (("so_rate", "SO_RATE"), ("avg", "AVG"),
                             ("iso", "ISO")):
                xs = [r["totals"][key] for r in fit]
                ys = [r["type_shares"][t] for r in fit]
                for sgn in (1, -1):
                    tab = DecileTable([sgn * x for x in xs], ys)
                    e = _mae([tab.predict(sgn * x) for x in xs], ys)
                    if best is None or e < best[0]:
                        best = (e, drv, tab, sgn)
            tabs[t], drivers[t] = best[2], (best[1], best[3])
        m.type_tabs, m.type_drivers = tabs, drivers

        def drv_vec(r):
            key = {"so_rate": "SO_RATE", "avg": "AVG", "iso": "ISO"}
            v = {t: tabs[t].predict(drivers[t][1]
                                    * r["totals"][key[drivers[t][0]]])
                 for t in ("G", "F", "P")}
            v["L"] = max(0.0, 1.0 - sum(v.values()))
            return _renorm(v, OUT_TYPE_KEYS)
        cand["driver"] = [drv_vec(r) for r in fit]
        scores = {k: mae(v, "type_shares") for k, v in cand.items()}
        m.choice["type_shares"] = min(scores, key=scores.get)
        m.diag["type_shares"] = {k: round(v, 4) for k, v in scores.items()}

        # ---- directional shares: global vs bats vs bats x archetype
        dglob = _share_median(fit, "dirA")
        by_bats = {b: _share_median(fit, "dirA",
                                    lambda r, b=b: r["bats"] == b)
                   for b in ("L", "R", "B")}
        by_ba = {}
        for b in ("L", "R", "B"):
            for a in {r["archetype"] for r in fit}:
                sub = [r for r in fit
                       if r["bats"] == b and r["archetype"] == a]
                if len(sub) >= 8:
                    by_ba[(b, a)] = _share_median(sub, "dirA")
        m.dir_global, m.dir_by_bats, m.dir_by_ba = dglob, by_bats, by_ba
        dcand = {"global": [dglob] * len(fit),
                 "bats": [by_bats[r["bats"]] for r in fit],
                 "bats_x_arch": [by_ba.get((r["bats"], r["archetype"]),
                                           by_bats[r["bats"]])
                                 for r in fit]}
        dscores = {k: mae(v, "dirA") for k, v in dcand.items()}
        m.choice["dir_shares"] = min(dscores, key=dscores.get)
        m.diag["dir_shares"] = {k: round(v, 4) for k, v in dscores.items()}

        # ---- start point: decile table on the better of so_rate/avg
        # (either orientation; see the type-share note above)
        best = None
        for drv, key in (("so_rate", "SO_RATE"), ("avg", "AVG")):
            xs = [r["totals"][key] for r in fit]
            ys = [r["start"] for r in fit]
            for sgn in (1, -1):
                tab = DecileTable([sgn * x for x in xs], ys)
                e = _mae([tab.predict(sgn * x) for x in xs], ys)
                if best is None or e < best[0]:
                    best = (e, drv, tab, sgn)
        m.start_tab, m.start_driver = best[2], (best[1], best[3])
        m.diag["start"] = {"driver": best[1],
                           "train_mae_pts": round(best[0], 2)}
        return m

    # ------------------------------------------------------------ use
    def _type_vec(self, totals, archetype):
        ch = self.choice["type_shares"]
        if ch == "archetype":
            return self.type_by_arch.get(archetype, self.type_global)
        key = {"so_rate": "SO_RATE", "avg": "AVG", "iso": "ISO"}
        if ch == "driver":
            v = {t: self.type_tabs[t].predict(
                self.type_drivers[t][1]
                * totals[key[self.type_drivers[t][0]]])
                for t in ("G", "F", "P")}
            v["L"] = max(0.0, 1.0 - sum(v.values()))
            return _renorm(v, OUT_TYPE_KEYS)
        return self.type_global

    def _dir_vec(self, archetype, bats):
        ch = self.choice["dir_shares"]
        if ch == "bats_x_arch":
            return self.dir_by_ba.get((bats, archetype),
                                      self.dir_by_bats.get(
                                          bats, self.dir_global))
        if ch == "bats":
            return self.dir_by_bats.get(bats, self.dir_global)
        return self.dir_global

    def generate_outmix(self, totals, archetype="balanced", bats="R"):
        """Generate the OUT-chart mix for one hitter from his combined
        totals (the load_out_records 'totals' dict), archetype and
        batting hand. Returns printed-style shares and the table start:
        {"type_shares", "dir_shares", "start", "width"}."""
        drv, sgn = self.start_driver
        key = {"so_rate": "SO_RATE", "avg": "AVG"}[drv]
        start = int(math.floor(
            self.start_tab.predict(sgn * totals[key]) + 0.5))
        start = min(45, max(1, start))
        return {"type_shares": self._type_vec(totals, archetype),
                "dir_shares": self._dir_vec(archetype, bats),
                "start": start, "width": 100 - start}


def fit_outmix(records=None):
    """Fit the OutMixModel on TRAIN records only (the documented v1
    holdout: md5(name) mod 3 == 0 is TEST and is never fitted)."""
    if records is None:
        records = load_out_records()
    train = [r for r in records if not _out_is_test(r["name"])]
    return OutMixModel.fit(train)
