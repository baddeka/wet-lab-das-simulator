"""Stage 2: can a sensor actually read a difference that stage 1 called real.

Only candidates that cleared stage 1 reach here, because a sensor for a
biomarker that does not separate patients is wasted effort regardless of its
constants.

Three module types, three branches:

  A  enzyme        analyte -> oxidase -> H2O2 -> OxyR -> promoter -> GFP.
                   The two-compartment ODE in das_model, unchanged. Needs
                   km_uM and kcat_s. Amplifies, because one enzyme turns over
                   many analyte molecules, but competes against the cell's own
                   peroxide flux.
  B  direct TF     analyte -> TF -> repression relieved -> promoter -> GFP.
                   No peroxide stage. Hill occupancy of the TF sets the
                   promoter activation, then the same reporter. Needs kd_uM.
                   Amplifies through transcription, so it still gains from the
                   read time.
  C  binding FP    analyte -> binding protein -> conformation -> fluorescence.
                   No transcription, no reporter gene, no amplification, and
                   the response is instantaneous, so the read time does not
                   enter. Needs kd_uM. The response is the fold change in
                   occupancy; converting that to a measured fluorescence fold
                   would need each protein's dynamic range, which no column of
                   sensors.csv carries, so it is not estimated.

A missing constant stops the branch. Nothing is defaulted and nothing is
borrowed from a similar protein.
"""
import numpy as np

import das_model

from . import performance

GREEN, YELLOW, RED = "green", "yellow", "red"


def fold_needed(platform):
    """Smallest fold the reader can call apart at the configured replicate count."""
    spread = platform["cv_reader"] * (2.0 / platform["n_rep"]) ** 0.5
    return float(np.exp(platform["z_required"] * spread))


def max_cv(fold, platform):
    """Largest reader CV that still resolves this fold."""
    if fold is None or fold <= 1.0:
        return 0.0
    return float(np.log(fold) / (platform["z_required"]
                                 * (2.0 / platform["n_rep"]) ** 0.5))


def _assay_conc(c_raw, p):
    return c_raw * p["conc_factor"] * p["sample_frac"]


def _fold_A(p, c_h, c_s):
    """Type A: the existing two-compartment ODE, run at the two clinical levels."""
    mode = p.get("mode", "free")
    r_h = das_model.response(dict(p, C_raw_uM=c_h), mode)
    r_s = das_model.response(dict(p, C_raw_uM=c_s), mode)
    g_h, g_s = r_h["gfp_signal"], r_s["gfp_signal"]
    return (g_s / g_h if g_h > 0 else None), dict(
        h2o2_cyt_peak=r_s["h2o2_cyt_peak"],
        h2o2_cyt_rest=r_s["h2o2_cyt_rest"],
        converted=1.0 - r_s["das_left"] / r_s["das_assay"] if r_s["das_assay"] else None,
        sb_sick=r_s["sb"], sb_healthy=r_h["sb"])


def _theta(binders, p):
    """Fraction of the binding site occupied, over every analyte that binds it.

    binders is [(kd, conc_healthy, conc_sick), ...] with the target first. Every
    entry is a measured Kd for the same protein, so they all compete for the one
    site and - for the sensors in sensors.csv, which are published as responding
    to each of their listed analytes - they all produce signal. The readout is
    therefore total occupancy, not the target's share of it:

        theta = sum_i (A_i / Kd_i) / (1 + sum_i (A_i / Kd_i))

    With a single binder this is A/(Kd+A), identical to the Hill form at n=1.
    The competitive sum is exact only at n=1; the caller keeps the Hill form when
    there is nothing to compete with, and flags the approximation when there is.
    """
    n = p["hill_n_binding"]
    if len(binders) == 1:
        kd, c_h, c_s = binders[0]
        return (das_model.occupancy(p["alpha"] * _assay_conc(c_h, p), kd, n),
                das_model.occupancy(p["alpha"] * _assay_conc(c_s, p), kd, n))
    s_h = sum(p["alpha"] * _assay_conc(c_h, p) / kd for kd, c_h, _ in binders)
    s_s = sum(p["alpha"] * _assay_conc(c_s, p) / kd for kd, _, c_s in binders)
    return s_h / (1.0 + s_h), s_s / (1.0 + s_s)


def _fold_B(p, binders):
    """Type B: occupancy of the TF drives the promoter, then the reporter."""
    th_h, th_s = _theta(binders, p)
    g_h = das_model.reporter_response(p, th_h)
    g_s = das_model.reporter_response(p, th_s)
    return (g_s / g_h if g_h > 0 else None), dict(
        occupancy_healthy=th_h, occupancy_sick=th_s)


def _fold_A_binders(p, binders):
    """Type A keeps its own ODE; only the target concentration enters here.

    Cross-reactivity for an enzyme is competition for catalysis, not for a
    binding site, and the ODE already carries it through p["interferent"] and
    p["selectivity"]. feasibility() fills those from the data when sensors.csv
    shows the same enzyme acting on another analyte.
    """
    _, c_h, c_s = binders[0]
    return _fold_A(p, c_h, c_s)


BRANCH = {"A": _fold_A_binders, "B": _fold_B}


def cross_binders(sensor, bundle):
    """Other analytes this very protein is published as binding or turning over.

    Read straight out of sensors.csv: the same protein_name against a different
    biomarker, with the constant its type needs. Nothing is assumed about
    cross-reactivity - either the data file records the same protein twice, or
    this returns nothing.
    """
    need = "kd_uM" if sensor.module_type == "B" else "km_uM"
    return [o for o in bundle["sensors"]
            if o.protein_name == sensor.protein_name
            and o.biomarker != sensor.biomarker
            and getattr(o, need) is not None]


def same_study_level(clin_row, biomarker, bundle, unit_table, creatinine):
    """That competitor's levels in the SAME study as the target's row.

    Same DOI, same cancer, same biofluid. Levels from a different cohort would
    mix populations and assays, so a competitor measured only elsewhere counts
    as not evaluated rather than as a number.
    """
    for r in bundle["clinical"]:
        if (r.biomarker == biomarker
                and r.source_doi == clin_row.source_doi
                and r.biofluid == clin_row.biofluid
                and r.cancer == clin_row.cancer):
            h, _ = unit_table.to_uM(r.healthy_value, r.units, creatinine)
            s, _ = unit_table.to_uM(r.sick_value, r.units, creatinine)
            if h is not None and s is not None:
                return h, s, r
    return None


def _conc_grid(platform, points=14):
    return np.unique(np.round(np.geomspace(1.0, platform["conc_factor_max"], points), 3))


def feasibility(sensor, s1, bundle):
    """Judge one sensor against one clinical row that already cleared stage 1."""
    pf, ut = bundle["platform"], bundle["unit_table"]
    row = s1["row"]
    out = dict(sensor=sensor, stage1=s1, notes=[], light=RED,
               reason=None, stage="stage 2")

    # --- does the sensor have the constants its own branch needs? ----------
    missing = sensor.missing()
    if missing:
        out["reason"] = "no sensor data: %s not reported for %s" % (
            ", ".join(missing), sensor.protein_name)
        return out

    # --- can the clinical levels become an absolute concentration? --------
    p0 = das_model._data.build_params(pf, bundle["scenario"], sensor)
    creat = p0.get("creatinine")
    c_h, why_h = ut.to_uM(row.healthy_value, row.units, creat)
    c_s, why_s = ut.to_uM(row.sick_value, row.units, creat)
    if c_h is None or c_s is None:
        out["reason"] = why_h or why_s
        return out
    out["c_healthy_uM"], out["c_sick_uM"] = c_h, c_s

    branch = BRANCH[sensor.module_type]
    need = fold_needed(pf)
    out["fold_needed"] = need

    # --- who else does this same protein bind? -----------------------------
    binders = [(sensor.kd_uM, c_h, c_s)]
    competitors, unevaluated = [], []
    for other in cross_binders(sensor, bundle):
        lv = same_study_level(row, other.biomarker, bundle, ut, creat)
        if lv is None:
            unevaluated.append(other.biomarker)
            continue
        competitors.append(dict(biomarker=other.biomarker, kd_uM=other.kd_uM,
                                healthy_uM=lv[0], sick_uM=lv[1],
                                source_doi=lv[2].source_doi))
        if sensor.module_type == "B":
            binders.append((other.kd_uM, lv[0], lv[1]))
    out["competitors"] = competitors
    out["competitors_unevaluated"] = sorted(set(unevaluated))

    if competitors and sensor.module_type == "B":
        if pf["hill_n_binding"] != 1.0:
            out["notes"].append(
                "the competitive occupancy sum is exact only at Hill n = 1, and "
                "the platform assumes n = %g" % pf["hill_n_binding"])
        clean, _ = branch(p0, [binders[0]])
        out["fold_without_competition"] = clean

    if sensor.module_type == "A":
        # An enzyme's cross-reactivity is competition for catalysis. The ODE
        # already carries it, so fill its two terms from the data when
        # sensors.csv lists this enzyme against another analyte measured in the
        # same study. Otherwise say plainly that the scenario's number is a
        # guess, instead of letting it pass for a measurement.
        rival = None
        for other in cross_binders(sensor, bundle):
            lv = same_study_level(row, other.biomarker, bundle, ut, creat)
            if lv and other.efficiency and sensor.efficiency:
                rival = (other, lv)
                break
        if rival is not None:
            other, lv = rival
            p0 = dict(p0,
                      interferent=lv[0],
                      selectivity=sensor.efficiency / other.efficiency)
            out["selectivity_source"] = (
                "derived from sensors.csv: (kcat/Km) of %s over %s = %.3g, with "
                "%s at %.3g uM from the same study"
                % (sensor.protein_name, other.protein_name,
                   p0["selectivity"], other.biomarker, lv[0]))
        else:
            out["selectivity_source"] = (
                "not evaluated: sensors.csv lists %s against %s only, so the "
                "scenario's selectivity of %g and interferent of %g uM are "
                "assumptions, not measurements"
                % (sensor.protein_name, sensor.biomarker,
                   p0.get("selectivity", float("nan")),
                   p0.get("interferent", float("nan"))))
            if not p0.get("interferent"):
                out["notes"].append(
                    "cross-reactivity is NOT in this verdict: the scenario runs "
                    "with no interferent and an assumed selectivity of %g"
                    % p0.get("selectivity", float("nan")))
    if unevaluated:
        out["notes"].append(
            "this protein also binds %s with a measured Kd, but %s has no level "
            "in this study, so the interference could not be evaluated here"
            % (", ".join(sorted(set(unevaluated))),
               "it" if len(set(unevaluated)) == 1 else "they"))

    # Kept so analysis.py can re-run this module on the identical parameter
    # set rather than reassembling one that might differ. Neither is exported.
    out["params"], out["binders"] = p0, binders

    # --- fold at the scenario's own concentration factor -------------------
    base_fold, extras = branch(p0, binders)
    out["fold_at_scenario"] = base_fold
    out["extras"] = extras
    out["conc_factor_scenario"] = p0["conc_factor"]

    # --- sweep the concentration factor -----------------------------------
    best, needed_cf = (None, None), None
    for cf in _conc_grid(pf):
        f, _ = branch(dict(p0, conc_factor=float(cf)), binders)
        if f is None:
            continue
        mag = max(f, 1.0 / f)
        if best[0] is None or mag > best[0]:
            best = (mag, float(cf))
        if needed_cf is None and mag >= need:
            needed_cf = float(cf)
    out["best_fold_magnitude"], out["best_conc_factor"] = best
    out["required_conc_factor"] = needed_cf
    out["max_cv_at_best"] = max_cv(best[0], pf)

    # --- where does the analyte sit relative to the sensor's constant? ----
    anchor = sensor.km_uM if sensor.module_type == "A" else sensor.kd_uM
    anchor_name = "Km" if sensor.module_type == "A" else "Kd"
    cf_use = needed_cf or best[1] or p0["conc_factor"]
    ratio = _assay_conc(c_s, dict(p0, conc_factor=cf_use)) / anchor
    out["anchor_name"], out["anchor_uM"], out["analyte_over_anchor"] = (
        anchor_name, anchor, ratio)

    # --- type A only: does it need the scavengers knocked out? ------------
    if sensor.module_type == "A":
        ko = dict(p0, conc_factor=cf_use, k_scav=pf["k_scav_knockout"])
        f_ko, _ = branch(ko, binders)
        f_wt, _ = branch(dict(p0, conc_factor=cf_use), binders)
        out["fold_knockout"], out["fold_wildtype"] = f_ko, f_wt
        wt_ok = f_wt is not None and max(f_wt, 1 / f_wt) >= need
        ko_ok = f_ko is not None and max(f_ko, 1 / f_ko) >= need
        out["knockout_required"] = bool(ko_ok and not wt_ok)
        out["knockout_helps"] = bool(
            f_ko is not None and f_wt is not None
            and max(f_ko, 1 / f_ko)
            > max(f_wt, 1 / f_wt) * pf["knockout_gain_min"])

    # --- what the device would achieve on patients -------------------------
    # The fold alone is not a diagnostic: the biological spread is squeezed by
    # the same transfer function as the signal, and the reader's own noise sits
    # on top. performance.py propagates both.
    best_mag = best[0]
    perf, perf_why = (None, "no device fold")
    if best_mag:
        perf, perf_why = performance.separation(s1, best_mag, pf)
    out["performance"], out["performance_missing"] = perf, perf_why
    if perf:
        out["sens_at_90_spec"] = performance.at_cutoff(s1, perf, 0.90)

    # --- the light ---------------------------------------------------------
    scen_mag = None if base_fold is None else max(base_fold, 1.0 / base_fold)
    if scen_mag is not None and scen_mag >= need:
        out["light"] = GREEN
        out["reason"] = ("fold %.3f%s at the scenario's %gx concentration, above "
                         "the %.3f the reader resolves"
                         % (scen_mag, " (a decrease)" if base_fold < 1 else "",
                            p0["conc_factor"], need))
    elif needed_cf is not None:
        out["light"] = YELLOW
        out["reason"] = ("needs the sample concentrated %gx to reach fold %.3f"
                         % (needed_cf, need))
    else:
        out["light"] = RED
        out["reason"] = _red_reason(out, sensor, pf, anchor_name, ratio)
    return out


def _red_reason(out, sensor, pf, anchor_name, ratio):
    """Name the dominant cause, in the vocabulary the report uses."""
    best = out["best_fold_magnitude"]
    if sensor.module_type == "B":
        if ratio < pf["kd_ratio_lo"]:
            return ("analyte stays below %s even concentrated %gx: analyte/%s = "
                    "%.3g, so the sensor sits in its dead zone"
                    % (anchor_name, pf["conc_factor_max"], anchor_name, ratio))
        if ratio > pf["kd_ratio_hi"]:
            return ("analyte is above %s and the sensor is saturated: analyte/%s "
                    "= %.3g" % (anchor_name, anchor_name, ratio))
    elif ratio > pf["kd_ratio_hi"]:
        return ("analyte is above %s and the enzyme is saturated: analyte/%s = %.3g"
                % (anchor_name, anchor_name, ratio))
    if best is None:
        return "the response could not be evaluated"
    return ("best fold %.4f over concentration factors up to %gx is below the "
            "%.3f the reader resolves at CV %.0f%% and n=%g"
            % (best, pf["conc_factor_max"], out["fold_needed"],
               100 * pf["cv_reader"], pf["n_rep"]))
