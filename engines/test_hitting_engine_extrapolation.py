"""Ceiling extrapolation in hitting engine v1.2 (EXTRAPOLATE_CEILING)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hitting_engine_v1_2 as he  # noqa: E402

DS = he.load_cards()
NEW = he.Engine.fit(DS)
OLD = he.Engine.fit(DS, extrapolate=False)


def _sides():
    for c in DS:
        arch = he.classify(he.card_totals(c))
        for side in "LR":
            s = c["stats"].get(side) or {}
            if he.side_features(s) is not None:
                yield s, arch


def test_default_is_on():
    assert he.EXTRAPOLATE_CEILING is True and NEW.extrapolate is True
    assert OLD.extrapolate is False and he.TRIM_SINGLES_FIRST is False


def test_every_printed_1986_side_unchanged():
    n = 0
    for s, arch in _sides():
        assert NEW.generate(s, arch) == OLD.generate(s, arch)
        assert NEW.generate_inplay(s, arch) == OLD.generate_inplay(s, arch)
        n += 1
    assert n > 1000


def _line(ab, h, d, t, hr, bb, so):
    return {"AB": ab, "2B": d, "3B": t, "HR": hr, "BB": bb, "SO": so,
            "AVG": h / ab, "OBP": (h + bb) / (ab + bb), "SLG": (h + d + 2 * t + 3 * hr) / ab}


def test_slugger_hr_and_bb_extrapolate():
    # McGwire-like peak: 64 HR, 140 BB in 525 AB
    s = _line(525, 143, 20, 0, 64, 140, 161)
    old, new = OLD.generate(s, "free-swinger"), NEW.generate(s, "free-swinger")
    assert new["WHEELHOUSE"]["HR"] > old["WHEELHOUSE"]["HR"]
    assert new["WHEELHOUSE"]["1B"] <= old["WHEELHOUSE"]["1B"]  # filler singles give way
    for sec in he.SECTIONS:
        assert sum(new[sec].values()) <= 99
    # Bonds-like walks: BB rate beyond the 1986 maximum
    s = _line(470, 163, 30, 2, 56, 267, 70)
    assert NEW.generate(s, "power")["PATIENT"]["BB"] > OLD.generate(s, "power")["PATIENT"]["BB"]


def test_monotone_beyond_range():
    t = NEW.tables["wheel_hr"]
    xs = [t.x_max + i * 0.005 for i in range(6)]
    vals = [t.predict(x, True) for x in xs]
    assert vals == sorted(vals) and abs(vals[0] - t.predict(t.x_max)) < 1e-9
