"""Turning whatever spread a paper reported into a standard deviation.

The sources use six different conventions and some report none at all. Each
recipe lives in data/spread.csv; this module only applies them. A row with no
spread yields None, which stops it at stage 1 as "no spread reported" rather
than letting it through on an assumed variance.
"""
from scipy.stats import norm

from . import tables

Z75 = norm.ppf(0.75)     # 0.6745; (hi-lo)/(2*Z75) turns an IQR into an SD
Z975 = norm.ppf(0.975)   # 1.9600; the 95% CI half-width in SEs


class SpreadTable:
    def __init__(self, rows=None):
        rows = rows if rows is not None else tables.read("spread.csv")
        self.recipes = {r["spread_type"]: r for r in rows}

    def to_sd(self, raw, spread_type, n):
        """Return (sd, reason_if_none). Crude recipes are flagged by the caller."""
        if spread_type is None or raw is None:
            return None, "no spread reported"
        if spread_type not in self.recipes:
            raise KeyError("spread type %r is not in spread.csv" % spread_type)

        row = self.recipes[spread_type]
        recipe = row["recipe"]
        pars = tables.params(row["params"])
        lo, hi = tables.bounds(raw)
        width = (hi - lo) if lo is not None else tables.num(raw)

        if recipe == "as_is":
            return tables.num(raw), None

        if recipe == "sem":
            if n is None:
                return None, "SEM given but n is missing, so SD cannot be recovered"
            return tables.num(raw) * n ** 0.5, None

        if recipe == "iqr":
            return width / (2.0 * Z75), None

        if recipe == "range_hozo":
            if n is None:
                return None, "range given but n is missing"
            div = pars["div_small"] if n <= pars["n_split"] else pars["div_large"]
            return width / div, None

        if recipe == "ci95":
            if n is None:
                return None, "95% CI given but n is missing"
            return n ** 0.5 * width / (2.0 * Z975), None

        raise KeyError("recipe %r in spread.csv is not implemented" % recipe)

    def is_crude(self, spread_type):
        """True for recipes that only approximate an SD."""
        if spread_type is None:
            return False
        return self.recipes[spread_type]["recipe"] in ("range_hozo", "iqr")
