# -*- coding: utf-8 -*-
"""The reasoning behind the verdicts, as curves rather than as single numbers.

A verdict is one number and it hides its own argument. Five relationships do
the real work of this screen, and every one of them is a curve:

  * how the reporter answers a rising analyte - which is where the gap between
    a clinical fold and a device fold comes from, and the only place the
    compression factor can be seen rather than quoted;
  * how two overlapping patient distributions become one AUC - the only honest
    picture of what a sensitivity of 86% means here;
  * how a panel's separation moves with a correlation nobody measured;
  * where OxyR sits before the assay starts, which is the whole scavenger
    knockout argument;
  * which parameter the answer actually depends on.

Each is computed here, on the same code path that produced the verdict, and
exported as a list of points so the page draws it instead of asserting it.

Two of these are checks rather than illustrations. `reconstruction` compares the
AUC this pipeline rebuilds from summary statistics against the AUC the paper
reported for the same cohort, which is the only external test of the log-normal
route. `tornado` re-runs the model with one input moved at a time, which is the
only test of the claim that scavenging cancels out.

Nothing here invents a datum. Every curve is either a closed form whose
arguments come from the screen, or the model re-run with one input changed.
Where a study lacks what a curve needs, the curve is absent and the reason
travels with it.
"""
import math

import numpy as np
from scipy.stats import norm

import das_model

from . import performance

# One-at-a-time sensitivity sweep. Each entry is a parameter the result could
# plausibly depend on, with what it means and who gets to choose it. The point
# of including k_scav - which the algebra says cancels - is to show that it
# does; a sensitivity analysis that only varies the parameters already believed
# to matter proves nothing.
TORNADO = [
    ("OD",          "cell density at read",          "OD600",  "operator"),
    ("T_read",      "read window",                   "s",      "operator"),
    ("sample_frac", "sample fraction of the assay",  "",       "operator"),
    ("E",           "enzyme concentration",          "µM", "operator"),
    ("Km",          "Michaelis constant",            "µM", "module"),
    ("kcat",        "turnover number",               "s⁻¹", "module"),
    ("k_mem",       "membrane permeability",         "s⁻¹", "chassis"),
    ("P_endo",      "endogenous peroxide production", "µM/s", "chassis"),
    ("k_scav",      "peroxide scavenging",           "s⁻¹", "chassis"),
    ("K_oxyr",      "OxyR half-activation",          "µM", "chassis"),
    ("n_hill",      "OxyR cooperativity",            "",       "chassis"),
]

TORNADO_FACTOR = 2.0


def _pts(xs, ys, nd=5):
    return [[round(float(x), nd), round(float(y), nd)]
            for x, y in zip(xs, ys)]


def _r(x, nd=5):
    return None if x is None else round(float(x), nd)


# --------------------------------------------------------------- separation

def roc_points(sd_h, sd_s, delta, n=65):
    """Binormal ROC for healthy ~ N(0, sd_h^2) against sick ~ N(delta, sd_s^2).

    Cutting at t gives a false positive rate of 1 - Phi(t/sd_h) and a true
    positive rate of 1 - Phi((t - delta)/sd_s), so sweeping t across the healthy
    range traces the curve exactly. Nothing is sampled and nothing is fitted:
    the two spreads and the separation are the entire curve, which is why this
    can be drawn for a cohort published only as mean and SD.
    """
    if not sd_h or not sd_s or delta is None:
        return None
    z = np.linspace(5.0, -5.0, n)                   # cut-off t = sd_h * z
    fpr = 1.0 - norm.cdf(z)
    tpr = norm.cdf((delta - sd_h * z) / sd_s)
    return _pts(np.concatenate(([0.0], fpr, [1.0])),
                np.concatenate(([0.0], tpr, [1.0])))


def reader_distributions(sd_h, sd_s, delta, n=121, span=4.0):
    """The two cohorts as the reader sees them, in fold units above healthy.

    Both are log-normal, so both are normal in ln(signal); x is returned as the
    reading relative to the healthy median, which puts a healthy sample at 1 and
    the sick median at the device fold. The density is the one in ln x, so the
    area under each curve on a logarithmic x axis is 1 and the overlap between
    them is the error rate the AUC summarises.
    """
    if not sd_h or not sd_s or delta is None:
        return None
    lo = min(-span * sd_h, delta - span * sd_s)
    hi = max(span * sd_h, delta + span * sd_s)
    u = np.linspace(lo, hi, n)
    x = np.exp(u)
    return dict(
        healthy=_pts(x, norm.pdf(u / sd_h) / sd_h, 6),
        sick=_pts(x, norm.pdf((u - delta) / sd_s) / sd_s, 6),
        healthy_median=1.0, sick_median=_r(math.exp(delta)),
    )


def separation_figure(cand):
    """Everything the ROC and distribution figures need for one module."""
    perf = cand.get("performance")
    if not perf:
        return None
    s = cand["sensor"]
    eer = performance.equal_error_rate(perf["total_log_sd_healthy"],
                                       perf["total_log_sd_sick"],
                                       perf["delta_log"])
    return dict(
        biomarker=s.biomarker, protein=s.protein_name,
        module_type=s.module_type,
        cancer=cand["stage1"]["row"].cancer,
        study_doi=cand["stage1"]["row"].source_doi,
        # what the clinic itself separates, before any device
        clinical=dict(
            roc=roc_points(perf["bio_log_sd_healthy"], perf["bio_log_sd_sick"],
                           perf["delta_log_clinical"]),
            auc=_r(float(norm.cdf(perf["delta_log_clinical"]
                                  / math.hypot(perf["bio_log_sd_healthy"],
                                               perf["bio_log_sd_sick"]))), 4),
            sd_healthy=_r(perf["bio_log_sd_healthy"], 4),
            sd_sick=_r(perf["bio_log_sd_sick"], 4),
            delta=_r(perf["delta_log_clinical"], 4),
        ),
        # and what survives to the reader
        device=dict(
            roc=roc_points(perf["total_log_sd_healthy"],
                           perf["total_log_sd_sick"], perf["delta_log"]),
            auc=_r(perf["auc_at_reader"], 4),
            sd_healthy=_r(perf["total_log_sd_healthy"], 4),
            sd_sick=_r(perf["total_log_sd_sick"], 4),
            delta=_r(perf["delta_log"], 4),
            compression=_r(perf["compression"], 4),
            reader_log_sd=_r(perf["reader_log_sd"], 5),
        ),
        distributions=reader_distributions(perf["total_log_sd_healthy"],
                                           perf["total_log_sd_sick"],
                                           perf["delta_log"]),
        cutoff_fold=_r(math.exp(eer["cut"]), 4) if eer else None,
        equal_error=_r(eer["value"], 4) if eer else None,
        reported_youden=_r(perf["sensitivity_youden"], 4),
    )


def reconstruction(stage1_rows):
    """Rebuilt AUC against the AUC the paper reported, for the same cohort.

    This is the one external check available on the statistical route. Most of
    clinical.csv gives a mean, a spread and two group sizes and no ROC analysis,
    so the screen has to rebuild the separation on the assumption that each
    cohort is log-normal. Eight studies report both, which makes the assumption
    testable on them.

    Disagreement here is the honest measure of how far the screen's numbers can
    be trusted, and it is reported whichever way it falls.
    """
    out, skipped = [], []
    for s1 in stage1_rows:
        row = s1["row"]
        if row.auc is None:
            continue
        why = None
        if row.healthy_value is None or row.sick_value is None:
            why = "the study reports no central value for one of the groups"
        elif row.healthy_value <= 0 or row.sick_value <= 0:
            why = ("a central value is not positive, so these are differences on "
                   "a log scale already and no log-normal cohort can be rebuilt "
                   "from them")
        elif s1.get("sd_healthy") is None or s1.get("sd_sick") is None:
            why = "the study reports no spread this pipeline can use"
        elif s1.get("fold_magnitude") is None:
            why = "no fold could be formed between the two groups"
        if why:
            skipped.append(dict(biomarker=row.biomarker, cancer=row.cancer,
                                doi=row.source_doi, reported=_r(row.auc, 4),
                                reason=why))
            continue
        lsd_h = performance.log_sd(row.healthy_value, s1["sd_healthy"])
        lsd_s = performance.log_sd(row.sick_value, s1["sd_sick"])
        delta = abs(math.log(s1["fold_magnitude"]))
        rebuilt = float(norm.cdf(delta / math.hypot(lsd_h, lsd_s)))
        out.append(dict(
            biomarker=row.biomarker, cancer=row.cancer, biofluid=row.biofluid,
            doi=row.source_doi, reported=_r(row.auc, 4), rebuilt=_r(rebuilt, 4),
            n_healthy=row.n_healthy, n_sick=row.n_sick,
            spread_type=row.stat_type,
        ))
    out.sort(key=lambda r: r["reported"])
    bias = [r["rebuilt"] - r["reported"] for r in out]
    return dict(
        rows=out, skipped=skipped,
        mean_bias=_r(sum(bias) / len(bias), 4) if bias else None,
        mean_abs=_r(sum(abs(x) for x in bias) / len(bias), 4) if bias else None,
        worst=_r(max(bias, key=abs), 4) if bias else None,
        n=len(out),
    )


def effect_sizes(stage1_rows):
    """Stage 1 as a forest plot: every cohort's effect size with its interval.

    The confidence interval is the standard large-sample one for Cohen's d,

        se(d) = sqrt((n0 + n1) / (n0 n1) + d^2 / (2 (n0 + n1)))

    which needs both group sizes. Where clinical.csv does not report them the
    point is still drawn and the interval is absent, because a study whose
    precision cannot be known is a different thing from a study with a wide
    interval and the figure should not make them look alike.
    """
    out = []
    for s1 in stage1_rows:
        row = s1["row"]
        d = s1.get("cohens_d")
        if d is None:
            continue
        n0, n1 = row.n_healthy, row.n_sick
        lo = hi = None
        if n0 and n1 and n0 > 1 and n1 > 1:
            se = math.sqrt((n0 + n1) / float(n0 * n1)
                           + d * d / (2.0 * (n0 + n1)))
            lo, hi = d - 1.96 * se, d + 1.96 * se
        out.append(dict(
            biomarker=row.biomarker, cancer=row.cancer, biofluid=row.biofluid,
            doi=row.source_doi, d=_r(d, 3), lo=_r(lo, 3), hi=_r(hi, 3),
            n_total=int(n0 + n1) if (n0 and n1) else None,
            verdict=s1["verdict"], route=s1["route"],
            auc_reported=_r(row.auc, 3),
        ))
    out.sort(key=lambda r: (r["biomarker"], -abs(r["d"])))
    return out


# ------------------------------------------------------------ transfer curve

def dose_response(cand, platform, points=36):
    """Device fold against analyte level, on the module's own code path.

    The healthy arm is held at the study's value and the other arm swept, so
    every point is the same ratio of two reporter readings that the screen
    reports, and the point at the study's sick level is the device fold in the
    table exactly. The curve is what compression is: a decade of analyte buys
    far less than a decade of signal, and the local slope in log-log is the
    factor the clinical spread gets multiplied by.
    """
    from . import stage2
    p0, binders = cand.get("params"), cand.get("binders")
    c_h, c_s = cand.get("c_healthy_uM"), cand.get("c_sick_uM")
    if not p0 or not binders or not c_h or not c_s:
        return None
    cf = cand.get("required_conc_factor") or cand.get("best_conc_factor") \
        or p0["conc_factor"]
    p = dict(p0, conc_factor=float(cf))
    branch = stage2.BRANCH[cand["sensor"].module_type]
    kd = binders[0][0]
    rest = binders[1:]

    lo, hi = min(c_h, c_s) / 10.0, max(c_h, c_s) * 200.0
    grid = np.geomspace(lo, hi, points)
    grid = np.unique(np.concatenate((grid, [c_h, c_s])))

    xs, ys = [], []
    for c in grid:
        f, _ = branch(p, [(kd, c_h, float(c))] + rest)
        if f is None:
            continue
        xs.append(c)
        ys.append(f)
    if len(xs) < 4:
        return None

    # local log-log slope, which is the compression the propagation uses
    lx, ly = np.log(xs), np.log(ys)
    with np.errstate(divide="ignore", invalid="ignore"):
        slope = np.gradient(ly, lx)
    i_s = int(np.argmin(np.abs(np.asarray(xs) - c_s)))
    return dict(
        biomarker=cand["sensor"].biomarker,
        protein=cand["sensor"].protein_name,
        module_type=cand["sensor"].module_type,
        anchor_name="Km" if cand["sensor"].module_type == "A" else "Kd",
        anchor_uM=_r(kd if cand["sensor"].module_type == "B"
                     else cand["sensor"].km_uM),
        conc_factor=_r(cf, 3),
        curve=_pts(xs, ys, 6),
        healthy_uM=_r(c_h, 5), sick_uM=_r(c_s, 5),
        fold_at_sick=_r(ys[i_s], 4),
        slope_at_sick=_r(float(slope[i_s]), 4),
        # the chord between the two clinical levels, which is the compression
        # the propagation uses: ln(device fold) / ln(clinical fold)
        slope_chord=_r(math.log(ys[i_s]) / math.log(c_s / c_h), 4)
        if ys[i_s] > 0 and c_s != c_h else None,
        fold_needed=_r(float(np.exp(platform["z_required"]
                                    * platform["cv_reader"]
                                    * math.sqrt(2.0 / platform["n_rep"]))), 4),
        # where the module's own constant falls on this axis, in biofluid units
        anchor_on_axis=_r(cand["anchor_uM"] / (p["alpha"] * p["conc_factor"]
                                               * p["sample_frac"]), 5),
    )


def time_course(cand, points=200, span=2.5):
    """The device fold as a function of how long the reader waits.

    Three integrations on one grid: the sick arm, the healthy arm, and a blank.
    The ratio of the first two at time t is exactly the fold a read window of
    length t would deliver, because the read window only sets where the
    integration stops. So one run gives the fold at every possible window, and
    the figure can mark the one the scenario chose.

    The run goes past the configured window on purpose. The fold rises while the
    analyte is being turned over and falls once the pulse is spent and the
    reporter is accumulating in both arms alike, so there is an optimum, and the
    scenario's window need not sit on it.
    """
    p0 = cand.get("params")
    c_h, c_s = cand.get("c_healthy_uM"), cand.get("c_sick_uM")
    if not p0 or not c_s or not c_h or cand["sensor"].module_type != "A":
        return None
    cf = cand.get("required_conc_factor") or cand.get("best_conc_factor") \
        or p0["conc_factor"]
    T = float(p0["T_read"])
    p = dict(p0, conc_factor=float(cf), T_read=T * span)
    mode = p.get("mode", "free")
    sick = das_model.simulate(dict(p, C_raw_uM=float(c_s)), mode, True, points)
    well = das_model.simulate(dict(p, C_raw_uM=float(c_h)), mode, True, points)
    blank = das_model.simulate(p, mode, False, points)

    g_s, g_h = sick.y[5], well.y[5]
    ok = g_h > 0
    t, ratio = sick.t[ok], g_s[ok] / g_h[ok]
    if len(t) < 4:
        return None
    i_peak = int(np.argmax(ratio))
    # the configured window will not land on an integration grid point, and a
    # figure that disagreed with the table in the third decimal would look like
    # a different calculation rather than a nearest neighbour
    fold_at_T = float(np.interp(T, t, ratio))
    return dict(
        biomarker=cand["sensor"].biomarker,
        protein=cand["sensor"].protein_name,
        T_read=_r(T), span=span, conc_factor=_r(cf, 3),
        fold=_pts(t, ratio, 6),
        h2o2_cyt_sick=_pts(sick.t, sick.y[2], 6),
        h2o2_cyt_healthy=_pts(well.t, well.y[2], 6),
        h2o2_cyt_blank=_pts(blank.t, blank.y[2], 6),
        h2o2_med_sick=_pts(sick.t, sick.y[3], 6),
        analyte_left=_pts(sick.t, sick.y[0], 6),
        analyte_start=_r(float(sick.y[0][0]), 5),
        fold_at_T=_r(fold_at_T, 5),
        fold_peak=_r(float(ratio[i_peak]), 5),
        t_peak=_r(float(t[i_peak]), 1),
        peak_over_T=_r(float(t[i_peak] / T), 3),
        K_oxyr=_r(p["K_oxyr"]),
        gradient_peak=_r(float(sick.y[3].max() / max(sick.y[2].max(), 1e-300)), 2),
    )


# The closed form the project derived for signal over background,
#
#     S/B  ~  S0 / (phi * P_endo * T)
#
# predicts an exponent for each of its four parameters. The full ODE is the
# authority, so the exponents are measured against it rather than asserted.
SCALING = [
    ("phi_per_OD", -1.0, "cell density, through φ"),
    ("P_endo",     -1.0, "endogenous peroxide production"),
    ("T_read",     -1.0, "read window"),
    ("k_scav",      0.0, "peroxide scavenging"),
]


def scaling_check(p, mode, conc=None, factor=2.0, label=None):
    """Measured log-log slope of S/B against each parameter of the closed form.

    A central difference in log space,

        slope = [ln S/B(x f) - ln S/B(x / f)] / (2 ln f)

    which is the exponent the ODE actually obeys near the operating point. Where
    it disagrees with the predicted exponent, the closed form does not hold
    there, and that is reported rather than smoothed over.
    """
    def sb(pp):
        if conc is not None:
            pp = dict(pp, C_raw_uM=float(conc))
        return das_model.response(pp, mode)["sb"]

    base = sb(p)
    rows = []
    for name, predicted, meaning in SCALING:
        if name not in p or not p[name]:
            continue
        v = float(p[name])
        lo, hi = sb(dict(p, **{name: v / factor})), sb(dict(p, **{name: v * factor}))
        if lo <= 0 or hi <= 0:
            continue
        slope = (math.log(hi) - math.log(lo)) / (2.0 * math.log(factor))
        rows.append(dict(
            param=name, meaning=meaning, predicted=predicted,
            measured=_r(slope, 3), value=_r(v, 6),
            sb_low=_r(lo, 8), sb_high=_r(hi, 8),
            holds=bool(abs(slope - predicted) <= 0.25),
        ))
    return dict(label=label, sb_base=_r(base, 8), factor=factor,
                conc_uM=_r(conc, 5) if conc is not None else None,
                mode=mode, rows=rows)


# -------------------------------------------------------------------- chassis

def oxyr_curve(platform, points=97):
    """OxyR activation against cytoplasmic peroxide, with each strain's seat.

    The knockout result is the least intuitive thing the model says - deleting
    the enzymes that destroy the signal makes the signal worse - and it is
    entirely this curve. Resting peroxide is P_endo / k_scav, so cutting the
    scavengers moves the strain to the right, and past the half-activation point
    there is no headroom left for the analyte to use.
    """
    n, k = platform["n_hill"], platform["K_oxyr"]
    rest_wt = platform["P_endo"] / platform["k_scav"]
    rest_ko = platform["P_endo"] / platform["k_scav_knockout"]
    lo = min(rest_wt, rest_ko, k) / 30.0
    hi = max(rest_wt, rest_ko, k) * 30.0
    x = np.geomspace(lo, hi, points)
    x = np.unique(np.concatenate((x, [rest_wt, rest_ko, k])))

    def act(v):
        return v ** n / (k ** n + v ** n)

    return dict(
        curve=_pts(x, act(x), 6),
        K_oxyr=_r(k), n_hill=_r(n),
        wildtype=dict(h2o2=_r(rest_wt, 5), activation=_r(act(rest_wt), 5),
                      headroom=_r(1.0 - act(rest_wt), 5), label="wild type"),
        knockout=dict(h2o2=_r(rest_ko, 5), activation=_r(act(rest_ko), 5),
                      headroom=_r(1.0 - act(rest_ko), 5),
                      label="scavengers deleted"),
    )


# --------------------------------------------------------------------- panels

def panel_rho_curves(panel_list, platform, points=49):
    """Panel AUC across every correlation the markers could have.

    None of the sources measures the correlation, because that needs the markers
    reported in the same patients. So the panel is never one number: it is this
    curve, and the verdict is read off its worst point.
    """
    out = []
    for p in panel_list:
        ds = [m["performance"]["d_at_reader"] for m in p["modules"]]
        if len(ds) < 2:
            continue
        rho = np.linspace(0.0, platform["panel_rho_correlated"], points)
        xs, ys = [], []
        for r in rho:
            d = performance.panel(ds, float(r))
            if d is None:
                continue
            xs.append(r)
            ys.append(performance.auc_from_d(d))
        if not xs:
            continue
        best_single = max(performance.auc_from_d(d) for d in ds)
        out.append(dict(
            biomarkers=p["biomarkers"], size=p["size"],
            curve=_pts(xs, ys, 5),
            auc_worst=_r(p["auc_worst"], 4), auc_best=_r(p["auc_best"], 4),
            rho_worst=_r(p["rho_worst"], 3),
            best_single=_r(best_single, 4),
            suppressor=p["suppressor"],
        ))
    return out


# ------------------------------------------------------------------- tornado

def tornado(cand, platform, factor=TORNADO_FACTOR):
    """One input moved at a time, with the verdict recomputed from scratch.

    Each parameter is multiplied and divided by the same factor and the whole
    chain re-run - fold, compression, propagation - so the bars are differences
    in the quantity the verdict actually rests on rather than in an intermediate.

    A parameter absent from this module's parameter set is skipped rather than
    invented, and a run that fails to produce a fold is reported as a gap.
    """
    from . import stage2
    p0, binders = cand.get("params"), cand.get("binders")
    s1, perf = cand.get("stage1"), cand.get("performance")
    if not p0 or not binders or not s1 or not perf:
        return None
    cf = cand.get("required_conc_factor") or cand.get("best_conc_factor") \
        or p0["conc_factor"]
    base_p = dict(p0, conc_factor=float(cf))
    branch = stage2.BRANCH[cand["sensor"].module_type]

    def run(p):
        f, _ = branch(p, binders)
        if f is None:
            return None, None
        mag = max(f, 1.0 / f)
        got, _ = performance.separation(s1, mag, platform)
        return mag, (got["auc_at_reader"] if got else None)

    base_fold, base_auc = run(base_p)
    if base_auc is None:
        return None

    rows, skipped = [], []
    for name, meaning, unit, who in TORNADO:
        if name not in base_p or not isinstance(base_p[name], (int, float)):
            skipped.append(name)
            continue
        v = float(base_p[name])
        if v == 0.0:
            skipped.append(name)
            continue
        lo_f, lo_a = run(dict(base_p, **{name: v / factor}))
        hi_f, hi_a = run(dict(base_p, **{name: v * factor}))
        if lo_a is None or hi_a is None:
            skipped.append(name)
            continue
        rows.append(dict(
            param=name, meaning=meaning, unit=unit, chosen_by=who,
            value=_r(v, 6),
            auc_low=_r(lo_a, 4), auc_high=_r(hi_a, 4),
            fold_low=_r(lo_f, 4), fold_high=_r(hi_f, 4),
            swing=_r(abs(hi_a - lo_a), 4),
        ))
    rows.sort(key=lambda r: -r["swing"])
    return dict(
        biomarker=cand["sensor"].biomarker,
        protein=cand["sensor"].protein_name,
        factor=factor, conc_factor=_r(cf, 3),
        base_fold=_r(base_fold, 4), base_auc=_r(base_auc, 4),
        rows=rows, skipped=sorted(skipped),
    )


# ---------------------------------------------------------------------- entry

def build(bundle, res, all_panels=None, max_roc=6):
    """Everything above, for the modules worth drawing."""
    pf = bundle["platform"]
    scored = [c for c in res["candidates"] if c.get("performance")]
    scored.sort(key=lambda c: -c["performance"]["auc_at_reader"])

    # one row per protein, so four diacetylspermine oxidases that land within
    # 0.001 of each other do not become four indistinguishable ROC curves
    seen, picked = set(), []
    for c in scored:
        key = (c["sensor"].biomarker, c["sensor"].protein_name)
        if key in seen:
            continue
        seen.add(key)
        picked.append(c)
        if len(picked) >= max_roc:
            break

    best = picked[0] if picked else None
    best_A = next((c for c in picked if c["sensor"].module_type == "A"), None)

    panel_curves = []
    for cancer, plist in (all_panels or {}).items():
        for row in panel_rho_curves(plist, pf):
            panel_curves.append(dict(row, cancer=cancer))

    # The closed form is checked in both scenarios it is supposed to cover: the
    # screen's own, with the enzyme free in the medium, and the periplasmic
    # diacetylspermine reference it was first derived for.
    scaling = []
    if best_A is not None:
        p = dict(best_A["params"],
                 conc_factor=float(best_A.get("required_conc_factor")
                                   or best_A.get("best_conc_factor")
                                   or best_A["params"]["conc_factor"]))
        scaling.append(scaling_check(
            p, p.get("mode", "free"), best_A["c_sick_uM"],
            label="%s / %s, screen scenario"
                  % (best_A["sensor"].biomarker, best_A["sensor"].protein_name)))
    ref = das_model.load_defaults("das_reference")
    if ref.get("v_cutoff"):
        scaling.append(scaling_check(
            dict(ref, V_das=ref["v_cutoff"]), ref.get("mode", "peri"),
            label="diacetylspermine reference scenario"))

    return dict(
        separation=[separation_figure(c) for c in picked],
        reconstruction=reconstruction(res["stage1"]),
        effect_sizes=effect_sizes(res["stage1"]),
        dose_response=dose_response(best, pf) if best else None,
        time_course=time_course(best_A) if best_A else None,
        oxyr=oxyr_curve(pf),
        panel_rho=panel_curves,
        tornado=tornado(best, pf) if best else None,
        scaling=scaling,
    )
