"""Unit tests for the three module branches, the loaders and the unit layer.

The regression test proves the refactor preserved the type A numbers. It cannot
say anything about types B and C, and it cannot exercise the refusal paths,
because the real data files happen not to reach them: both type B rows in
sensors.csv have no Kd, so the B branch never runs during a normal screen.
Untested branches in a tool that decides what to build are a liability, so they
are exercised here with synthetic rows.

    python tests/test_branches.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import das_model                                       # noqa: E402
import sensorlab                                       # noqa: E402
from sensorlab import data, stage1, stage2, tables     # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name,
                           "" if cond else "   <- " + str(detail)))
    if not cond:
        FAILURES.append(name)


def close(a, b, rel=1e-6):
    return a is not None and b is not None and abs(a - b) <= rel * max(abs(a), abs(b), 1e-30)


def sensor(**kw):
    row = dict(biomarker="X", module_type="A", protein_name="synthetic",
               organism=None, uniprot=None, km_uM=None, kcat_s=None, kd_uM=None,
               ph=None, temp_c=None, source_doi="synthetic", confidence=None,
               notes=None)
    row.update(kw)
    return data.Sensor({k: (None if v is None else str(v)) for k, v in row.items()})


def clinical(**kw):
    row = dict(biomarker="X", cancer="Test", biofluid="Urine", stat_type="mean",
               healthy_value=None, healthy_spread=None, healthy_spread_type=None,
               sick_value=None, sick_spread=None, sick_spread_type=None,
               n_healthy=None, n_sick=None, units="uM", normalization=None,
               cutoff=None, auc=None, source_doi="synthetic", notes=None)
    row.update(kw)
    return data.Clinical({k: (None if v is None else str(v)) for k, v in row.items()})


# ---------------------------------------------------------------- unit layer
def test_units(bundle):
    print("units")
    ut = bundle["unit_table"]
    v, why = ut.to_uM(5.0, "uM")
    check("uM passes through", close(v, 5.0), v)
    v, why = ut.to_uM(5.0, "nmol/L")
    check("nmol/L -> uM is /1000", close(v, 0.005), v)
    v, why = ut.to_uM(5.0, "nmol/mL")
    check("nmol/mL -> uM is identity", close(v, 5.0), v)
    v, why = ut.to_uM(2.0, "umol/g creatinine", 1.5)
    check("umol/g creatinine scales by creatinine", close(v, 3.0), v)
    v, why = ut.to_uM(1.0, "umol/mol creatinine", 1.0)
    check("umol/mol creatinine uses molar creatinine",
          close(v, 1.0 / bundle["platform"]["creatinine_MW_g_per_mol"]), v)
    v, why = ut.to_uM(2.0, "umol/g creatinine", None)
    check("missing creatinine refuses rather than defaults", v is None and why, why)
    v, why = ut.to_uM(2.0, "nmol/mg DNA")
    check("nmol/mg DNA is not convertible", v is None and "not convertible" in why, why)

    f, _ = ut.fold(2.0, 6.0, "uM")
    check("linear fold is a quotient", close(f, 3.0), f)
    f, _ = ut.fold(-0.4, 0.1, "log2 ratio")
    check("log2 fold is base^delta", close(f, 2 ** 0.5), f)
    try:
        ut.get("made up unit")
        check("unknown unit raises", False)
    except KeyError:
        check("unknown unit raises", True)


# --------------------------------------------------------------- spread layer
def test_spreads(bundle):
    print("spreads")
    st = bundle["spread_table"]
    sd, _ = st.to_sd("3.0", "sd", 10)
    check("sd passes through", close(sd, 3.0), sd)
    sd, _ = st.to_sd("2.0", "sem", 25)
    check("sem -> sd multiplies by sqrt(n)", close(sd, 10.0), sd)
    sd, _ = st.to_sd("1.0:3.0", "iqr_bounds", 20)
    check("iqr bounds -> sd", close(sd, 2.0 / (2 * 0.674489750196)), sd)
    sd_small, _ = st.to_sd("0:40", "range_bounds", 50)
    sd_large, _ = st.to_sd("0:40", "range_bounds", 200)
    check("Hozo divisor switches on n", close(sd_small, 10.0) and close(sd_large, 40 / 6.0),
          (sd_small, sd_large))
    sd, why = st.to_sd("2.0", "sem", None)
    check("sem without n refuses", sd is None and why, why)
    sd, why = st.to_sd(None, None, 10)
    check("no spread refuses", sd is None and why, why)


# --------------------------------------------------------------------- stage 1
def test_stage1(bundle):
    print("stage 1")
    b = dict(bundle)

    row = clinical(healthy_value=1.0, sick_value=3.0, healthy_spread=0.1,
                   healthy_spread_type="sd", sick_spread=0.1,
                   sick_spread_type="sd", n_healthy=30, n_sick=30)
    r = stage1.assess(row, b)
    check("clean separation passes", r["verdict"] == stage1.PASS, r["reason"])
    check("fold is right", close(r["fold"], 3.0), r["fold"])
    check("direction up", r["direction"] == "up")

    row = clinical(healthy_value=1.0, sick_value=1.02, healthy_spread=1.0,
                   healthy_spread_type="sd", sick_spread=1.0,
                   sick_spread_type="sd", n_healthy=30, n_sick=30)
    r = stage1.assess(row, b)
    check("overlapping distributions fail", r["verdict"] == stage1.FAIL, r["reason"])

    row = clinical(healthy_value=1.0, sick_value=3.0)
    r = stage1.assess(row, b)
    check("no spread is insufficient, not a fail",
          r["verdict"] == stage1.INSUFFICIENT, r["reason"])

    row = clinical(healthy_value=1.0, sick_value=1.01, auc=0.95,
                   healthy_spread=5.0, healthy_spread_type="sd",
                   sick_spread=5.0, sick_spread_type="sd",
                   n_healthy=30, n_sick=30)
    r = stage1.assess(row, b)
    check("a reported AUC overrides the rebuilt statistics",
          r["verdict"] == stage1.PASS and r["route"] == "reported AUC", r["reason"])

    row = clinical(healthy_value=1.0, sick_value=3.0, auc=0.55,
                   healthy_spread=0.01, healthy_spread_type="sd",
                   sick_spread=0.01, sick_spread_type="sd",
                   n_healthy=99, n_sick=99)
    r = stage1.assess(row, b)
    check("a low reported AUC fails despite a huge d",
          r["verdict"] == stage1.FAIL, r["reason"])

    # reconstructed SD larger than the central value -> insufficient
    row = clinical(stat_type="median", healthy_value=0.14,
                   healthy_spread="0.07:0.28", healthy_spread_type="range_bounds",
                   sick_value=0.46, sick_spread="0.03:24.6",
                   sick_spread_type="range_bounds", n_healthy=52, n_sick=248)
    r = stage1.assess(row, b)
    check("skewed range reconstruction is insufficient, not a fail",
          r["verdict"] == stage1.INSUFFICIENT and "skewed" in r["reason"], r["reason"])

    # a directly reported SEM is never second-guessed the same way
    row = clinical(healthy_value=0.53, sick_value=4.13, healthy_spread=0.07,
                   healthy_spread_type="sem", sick_spread=1.29,
                   sick_spread_type="sem", n_healthy=29, n_sick=42)
    r = stage1.assess(row, b)
    check("a reported SEM is judged, not rejected",
          r["verdict"] in (stage1.PASS, stage1.FAIL), r["reason"])

    row = clinical(healthy_value=6.0, sick_value=1.0, healthy_spread=0.1,
                   healthy_spread_type="sd", sick_spread=0.1,
                   sick_spread_type="sd", n_healthy=30, n_sick=30)
    r = stage1.assess(row, b)
    check("a decrease still separates",
          r["verdict"] == stage1.PASS and r["direction"] == "down", r["reason"])
    check("fold magnitude is orientation free", close(r["fold_magnitude"], 6.0),
          r["fold_magnitude"])


# --------------------------------------------------------------------- stage 2
def _passing_row(**kw):
    base = dict(healthy_value=1.0, sick_value=3.0, healthy_spread=0.1,
                healthy_spread_type="sd", sick_spread=0.1, sick_spread_type="sd",
                n_healthy=30, n_sick=30)
    base.update(kw)
    return clinical(**base)


def test_stage2(bundle):
    print("stage 2")
    b = dict(bundle)
    s1 = stage1.assess(_passing_row(), b)
    assert s1["verdict"] == stage1.PASS

    # --- refusal paths ---
    r = stage2.feasibility(sensor(module_type="A", km_uM=10), s1, b)
    check("type A without kcat refuses",
          r["light"] == stage2.RED and "kcat_s" in r["reason"], r["reason"])
    r = stage2.feasibility(sensor(module_type="B"), s1, b)
    check("type B without Kd refuses",
          r["light"] == stage2.RED and "kd_uM" in r["reason"], r["reason"])
    try:
        sensor(module_type="C", kd_uM=1)
        check("type C is rejected: the platform has two module types", False)
    except ValueError as exc:
        check("type C is rejected: the platform has two module types",
              "out_of_scope" in str(exc), exc)
    try:
        sensor(module_type="D", kd_uM=1)
        check("an unknown module type raises", False)
    except ValueError:
        check("an unknown module type raises", True)

    s1_bad_units = stage1.assess(_passing_row(units="nmol/mg DNA", auc=0.9), b)
    r = stage2.feasibility(sensor(module_type="B", kd_uM=10), s1_bad_units, b)
    check("unconvertible units stop stage 2",
          r["light"] == stage2.RED and "not convertible" in r["reason"], r["reason"])

    for mt, kw in (("A", dict(km_uM=310, kcat_s=158)), ("B", dict(kd_uM=2.0))):
        r = stage2.feasibility(sensor(module_type=mt, **kw), s1, b)
        ok = r.get("best_fold_magnitude") is not None and r["best_fold_magnitude"] > 0
        check("type %s branch runs" % mt, ok, r["reason"])

    r = stage2.feasibility(sensor(module_type="B", kd_uM=1e-6), s1, b)
    check("a saturated type B is red and says so",
          r["light"] == stage2.RED and "saturated" in r["reason"], r["reason"])

    sb = sensor(module_type="B", kd_uM=2.0)
    short = dict(b, scenario=dict(b["scenario"], T_read=60.0))
    long_ = dict(b, scenario=dict(b["scenario"], T_read=3600.0))
    check("type B response depends on the read time",
          not close(stage2.feasibility(sb, s1, short)["best_fold_magnitude"],
                    stage2.feasibility(sb, s1, long_)["best_fold_magnitude"]))

    need = stage2.fold_needed(b["platform"])
    check("fold_needed and max_cv invert each other",
          close(stage2.max_cv(need, b["platform"]), b["platform"]["cv_reader"]))

    # --- competition for the binding site ---
    # Two sensors.csv rows, one protein, two analytes: that is the evidence of
    # cross-reactivity, and it must come out of the data, never from a default.
    shared = [sensor(biomarker="X", module_type="B", protein_name="shared", kd_uM=2.0),
              sensor(biomarker="Y", module_type="B", protein_name="shared", kd_uM=2.0)]
    rival_row = clinical(biomarker="Y", healthy_value=5.0, sick_value=5.0)
    bc = dict(b, sensors=shared, clinical=list(b["clinical"]) + [rival_row])

    check("cross-binders are found in sensors.csv",
          [o.biomarker for o in stage2.cross_binders(shared[0], bc)] == ["Y"])
    check("a protein listed once has no cross-binders",
          stage2.cross_binders(sensor(module_type="B", kd_uM=1), bc) == [])

    lone = stage2.feasibility(shared[0], s1, dict(b, sensors=shared))
    check("a competitor with no level in this study is flagged, not assumed zero",
          lone.get("competitors") == [] and lone["competitors_unevaluated"] == ["Y"]
          and any("could not be evaluated" in n for n in lone["notes"]),
          (lone.get("competitors_unevaluated"), lone["notes"]))

    s1_shared = stage1.assess(_passing_row(biomarker="X"), bc)
    withc = stage2.feasibility(shared[0], s1_shared, bc)
    check("a competitor measured in the same study enters the calculation",
          len(withc["competitors"]) == 1
          and withc["competitors"][0]["biomarker"] == "Y", withc["competitors"])
    check("competition reports the clean fold for comparison",
          withc.get("fold_without_competition") is not None)
    clean = withc["fold_without_competition"]
    check("a constant competitor dilutes the fold",
          withc["best_fold_magnitude"] < max(clean, 1 / clean),
          (withc["best_fold_magnitude"], clean))

    # a competitor with a far weaker Kd should barely matter
    weak = [shared[0], sensor(biomarker="Y", module_type="B",
                              protein_name="shared", kd_uM=1e7)]
    r_weak = stage2.feasibility(weak[0], s1_shared, dict(bc, sensors=weak))
    check("a very weak competitor barely changes the fold",
          close(r_weak["best_fold_magnitude"], max(clean, 1 / clean), rel=1e-3),
          (r_weak["best_fold_magnitude"], clean))

    # single-binder theta must still equal the Hill form exactly
    p_single = data.build_params(b["platform"], b["scenario"], shared[0])
    th = stage2._theta([(2.0, 1.0, 3.0)], p_single)
    hill = (das_model.occupancy(p_single["alpha"] * 1.0 * p_single["conc_factor"]
                                * p_single["sample_frac"], 2.0,
                                p_single["hill_n_binding"]),)
    check("one binder reproduces the Hill form", close(th[0], hill[0]), (th[0], hill[0]))

    check("type A records whether selectivity was measured or assumed",
          "assumptions, not measurements" in stage2.feasibility(
              sensor(module_type="A", km_uM=310, kcat_s=158), s1, b
          )["selectivity_source"])



# ----------------------------------------------------------------- data files
def test_data(bundle):
    print("data files")
    check("sensors.csv loaded", len(bundle["sensors"]) > 0)
    check("clinical.csv loaded", len(bundle["clinical"]) > 0)
    for s in bundle["sensors"]:
        check_name = "%s has its type's constants or declares them missing" % s.label
        needed = data.Sensor.REQUIRED[s.module_type]
        consistent = all((getattr(s, f) is not None) != (f in s.missing())
                         for f in needed)
        if not consistent:
            check(check_name, False)
    check("every sensor row is self-consistent", True)

    ut = bundle["unit_table"]
    for row in bundle["clinical"]:
        try:
            ut.get(row.units)
        except KeyError as exc:
            check("clinical units %r are declared in units.csv" % row.units,
                  False, exc)
    check("every clinical unit is declared in units.csv", True)

    st = bundle["spread_table"]
    for row in bundle["clinical"]:
        for t in (row.healthy_spread_type, row.sick_spread_type):
            if t is not None and t not in st.recipes:
                check("spread type %r is declared in spread.csv" % t, False)
    check("every spread type is declared in spread.csv", True)

    check("absent markers become None",
          tables._clean("N/A") is None and tables._clean("Not reported") is None
          and tables._clean("  ") is None)
    check("a real value survives cleaning", tables._clean(" 3.6 ") == "3.6")

    # the reference scenario must still build and still carry its own levels
    p = das_model.load_defaults("das_reference")
    check("das_reference builds", p["Km"] is not None)
    check("das_reference carries its own clinical levels",
          p.get("v_healthy") is not None and p.get("v_cutoff") is not None)
    check("C_raw_uM overrides the legacy conversion",
          close(das_model.analyte_in_biofluid(dict(p, C_raw_uM=0.5)), 0.5))
    check("the legacy conversion still works",
          close(das_model.analyte_in_biofluid(p), p["V_das"] * p["creatinine"] / 1000.0))


def main():
    bundle = sensorlab.load("screen_default")
    for fn in (test_units, test_spreads, test_stage1, test_stage2, test_data):
        fn(bundle)
        print()
    if FAILURES:
        print("%d check(s) failed: %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
