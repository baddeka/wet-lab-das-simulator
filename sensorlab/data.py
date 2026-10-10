"""Loaders: CSV rows in, typed records and parameter dicts out.

This module is the only place that knows the names of columns. It is also the
only place that may turn a blank into None - never into a number.
"""
import math

from . import tables

LN2 = math.log(2.0)


class Sensor:
    """One row of sensors.csv: a protein that could read one biomarker."""

    REQUIRED = {"A": ("km_uM", "kcat_s"),
                "B": ("kd_uM",),
                "C": ("kd_uM",)}

    def __init__(self, row):
        self.biomarker = row["biomarker"]
        self.module_type = row["module_type"]
        self.protein_name = row["protein_name"]
        self.organism = row["organism"]
        self.uniprot = row["uniprot"]
        self.km_uM = tables.num(row["km_uM"], "km_uM")
        self.kcat_s = tables.num(row["kcat_s"], "kcat_s")
        self.kd_uM = tables.num(row["kd_uM"], "kd_uM")
        self.ph = tables.num(row["ph"], "ph")
        self.temp_c = tables.num(row["temp_c"], "temp_c")
        self.source_doi = row["source_doi"]
        self.confidence = row["confidence"]
        self.notes = row["notes"]

        if self.module_type not in self.REQUIRED:
            raise ValueError("module_type %r for %s is not A, B or C"
                             % (self.module_type, self.protein_name))

    @property
    def label(self):
        return "%s / %s" % (self.biomarker, self.protein_name)

    def missing(self):
        """Names of the constants this module type needs and does not have."""
        return [f for f in self.REQUIRED[self.module_type] if getattr(self, f) is None]

    @property
    def efficiency(self):
        """kcat/Km in 1/uM/s, or None. Only meaningful for type A."""
        if self.kcat_s is None or self.km_uM in (None, 0):
            return None
        return self.kcat_s / self.km_uM


class Clinical:
    """One row of clinical.csv: one biomarker in one fluid in one study."""

    def __init__(self, row):
        self.biomarker = row["biomarker"]
        self.cancer = row["cancer"]
        self.biofluid = row["biofluid"]
        self.stat_type = row["stat_type"]
        self.healthy_value = tables.num(row["healthy_value"], "healthy_value")
        self.healthy_spread = row["healthy_spread"]
        self.healthy_spread_type = row["healthy_spread_type"]
        self.sick_value = tables.num(row["sick_value"], "sick_value")
        self.sick_spread = row["sick_spread"]
        self.sick_spread_type = row["sick_spread_type"]
        self.n_healthy = tables.num(row["n_healthy"], "n_healthy")
        self.n_sick = tables.num(row["n_sick"], "n_sick")
        self.units = row["units"]
        self.normalization = row["normalization"]
        self.cutoff = tables.num(row["cutoff"], "cutoff")
        self.auc = tables.num(row["auc"], "auc")
        self.source_doi = row["source_doi"]
        self.notes = row["notes"]

    @property
    def label(self):
        return "%s / %s / %s" % (self.biomarker, self.cancer or "?", self.biofluid)


def load_platform():
    """Chassis, reporter, reader and threshold constants. Nothing biomarker-specific."""
    return {r["name"]: tables.num(r["value"], r["name"])
            for r in tables.read("platform.csv")}


def load_scenarios():
    """Assay-design and sample assumptions, keyed by scenario name.

    Values stay as strings when they are not numeric (the enzyme localisation
    mode), so the caller gets 'peri' rather than a parse error.
    """
    out = {}
    for r in tables.read("scenarios.csv"):
        name, param, raw = r["scenario"], r["param"], r["value"]
        try:
            value = tables.num(raw, param)
        except ValueError:
            value = raw
        out.setdefault(name, {})[param] = value
    return out


def load_sensors():
    return [Sensor(r) for r in tables.read("sensors.csv")]


def load_clinical():
    return [Clinical(r) for r in tables.read("clinical.csv")]


def build_params(platform, scenario, sensor=None):
    """Assemble the parameter dict the ODE core consumes.

    Rate constants that the data files store as half-lives or doubling times are
    turned into 1/s here, so the core never divides a log by a time.
    Precedence: platform constants, then the scenario, then the sensor's own
    kinetics. A scenario may override a platform constant by name.
    """
    p = {k: v for k, v in platform.items()}

    p["k_mat"] = LN2 / platform["gfp_maturation_halflife_s"]
    p["mu_pre"] = LN2 / platform["growth_doubling_pre_s"]
    p["mu"] = LN2 / platform["growth_doubling_s"]

    p.update(scenario)

    if sensor is not None:
        if sensor.km_uM is not None:
            p["Km"] = sensor.km_uM
        if sensor.kcat_s is not None:
            p["kcat"] = sensor.kcat_s
        if sensor.kd_uM is not None:
            p["Kd"] = sensor.kd_uM
    return p
