"""Unit conversion, done once at load time.

Everything downstream of this module is in uM, s, and 1/s. No calculation
converts anything. Units that cannot reach uM at all - per mg of tissue, per mg
of DNA, log ratios, units the source never stated - convert to None with a
reason, and the candidate carries that reason into the report instead of a
number.
"""
from . import tables


class Unit:
    def __init__(self, row):
        self.name = row["unit"]
        self.factor = tables.num(row["to_uM_factor"])
        self.needs = row["needs"]
        self.log_base = tables.num(row["log_base"])
        self.note = row["note"]

    @property
    def convertible(self):
        return self.factor is not None

    @property
    def is_log(self):
        return self.log_base is not None


class UnitTable:
    def __init__(self, rows=None, platform=None):
        rows = rows if rows is not None else tables.read("units.csv")
        self.units = {r["unit"]: Unit(r) for r in rows}
        self.platform = platform

    def get(self, name):
        if name not in self.units:
            raise KeyError("unit %r is not in units.csv; add it there rather "
                           "than converting in code" % name)
        return self.units[name]

    def _context(self, creatinine_g_per_L):
        """Resolve the external quantities that some units need."""
        if creatinine_g_per_L is None:
            return {}
        mw = self.platform["creatinine_MW_g_per_mol"]
        return {"creatinine_g_per_L": creatinine_g_per_L,
                "creatinine_mol_per_L": creatinine_g_per_L / mw}

    def to_uM(self, value, unit_name, creatinine_g_per_L=None):
        """Return (uM_value, reason_if_none)."""
        unit = self.get(unit_name)
        if value is None:
            return None, "no value reported"
        if not unit.convertible:
            return None, "units %r are not convertible to uM (%s)" % (unit.name, unit.note)
        if unit.needs:
            ctx = self._context(creatinine_g_per_L)
            if unit.needs not in ctx:
                return None, "units %r need %s, which the scenario does not set" % (
                    unit.name, unit.needs)
            return value * unit.factor * ctx[unit.needs], None
        return value * unit.factor, None

    def fold(self, healthy, sick, unit_name):
        """Fold change on the native scale of the unit.

        A log unit is a difference, not a quotient, so the fold is base^delta.
        """
        unit = self.get(unit_name)
        if healthy is None or sick is None:
            return None, "no central values reported"
        if unit.is_log:
            return unit.log_base ** (sick - healthy), None
        if healthy == 0:
            return None, "healthy value is zero, fold is undefined"
        return sick / healthy, None
