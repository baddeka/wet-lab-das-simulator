"""CSV reading primitives.

One rule governs this module: an empty cell means "no data" and becomes None.
It never becomes zero and never becomes a default. Anything downstream that
needs a number must check for None and refuse to compute without it.
"""
import csv
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Spellings that sources use for "this was not reported". Treated as empty.
_ABSENT = {"", "n/a", "na", "nr", "none", "not reported", "not stated",
           "no", "-", "--", "nan"}


def _clean(s):
    if s is None:
        return None
    s = s.strip()
    return None if s.lower() in _ABSENT else s


def read(name):
    """Read data/<name> and return a list of dicts with blanks as None."""
    path = os.path.join(DATA_DIR, name)
    with open(path, newline="", encoding="utf-8") as fh:
        return [{k: _clean(v) for k, v in row.items() if k is not None}
                for row in csv.DictReader(fh)]


def num(value, field=None):
    """Parse a numeric cell. None stays None; junk raises rather than defaulting."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError("cannot read %r as a number%s"
                         % (value, " in field %s" % field if field else ""))


def bounds(value):
    """Parse a 'lo:hi' cell into (lo, hi). A single number returns (None, None)."""
    if value is None or ":" not in value:
        return None, None
    lo, _, hi = value.partition(":")
    return num(lo), num(hi)


def params(value):
    """Parse a 'k=v;k=v' cell into a dict of floats."""
    out = {}
    if value:
        for part in value.split(";"):
            if "=" in part:
                k, _, v = part.partition("=")
                out[k.strip()] = num(v)
    return out
