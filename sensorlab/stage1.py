"""Stage 1: is the clinical difference real before any sensor is considered.

Nothing here touches the kinetic model. A biomarker whose sick and healthy
distributions overlap is not worth engineering a sensor for, however good the
sensor is, so this gate runs first and kills candidates cheaply.

Which evidence decides, in order:

  1. An AUC reported by the source paper. That is a ROC on the actual
     patient-level data, so it beats anything this module can reconstruct from
     a published summary. When present, it decides alone.
  2. Welch's t and Cohen's d, rebuilt from the central values, the spreads and
     the group sizes. Both must clear their thresholds, so a negligible effect
     measured at large n does not pass.
  3. Neither available - the verdict is "insufficient", not "pass".

Stage 1 is scale-free: it works on ratios and standardised differences, so rows
whose units cannot be converted to uM still get a clinical verdict here. They
fail later, at stage 2, where an absolute concentration is unavoidable.
"""
from scipy.stats import norm, t as t_dist

PASS, FAIL, INSUFFICIENT = "pass", "fail", "insufficient"


def _welch(m0, s0, n0, m1, s1, n1):
    """Welch's t, its Satterthwaite df, and the two-sided p."""
    if None in (s0, s1) or None in (n0, n1) or n0 < 2 or n1 < 2:
        return None, None, None
    v0, v1 = s0 * s0 / n0, s1 * s1 / n1
    se = (v0 + v1) ** 0.5
    if se == 0:
        return None, None, None
    tv = (m1 - m0) / se
    df = (v0 + v1) ** 2 / (v0 * v0 / (n0 - 1) + v1 * v1 / (n1 - 1))
    return tv, df, 2.0 * t_dist.sf(abs(tv), df)


def _cohens_d(m0, s0, n0, m1, s1, n1):
    if None in (s0, s1) or None in (n0, n1) or n0 + n1 < 3:
        return None
    pooled_var = ((n0 - 1) * s0 * s0 + (n1 - 1) * s1 * s1) / (n0 + n1 - 2)
    if pooled_var <= 0:
        return None
    return (m1 - m0) / pooled_var ** 0.5


def assess(row, bundle):
    """Judge one clinical row. Returns a dict; never raises on missing data."""
    pf = bundle["platform"]
    ut, st = bundle["unit_table"], bundle["spread_table"]

    out = dict(row=row, biomarker=row.biomarker, label=row.label,
               auc_reported=row.auc, notes=[])

    fold, fold_why = ut.fold(row.healthy_value, row.sick_value, row.units)
    out["fold"] = fold
    out["fold_magnitude"] = max(fold, 1.0 / fold) if fold else None
    out["direction"] = None if fold is None else ("up" if fold > 1 else "down")

    sd_h, why_h = st.to_sd(row.healthy_spread, row.healthy_spread_type, row.n_healthy)
    sd_s, why_s = st.to_sd(row.sick_spread, row.sick_spread_type, row.n_sick)
    out["sd_healthy"], out["sd_sick"] = sd_h, sd_s

    crude = st.is_crude(row.healthy_spread_type) or st.is_crude(row.sick_spread_type)
    if crude:
        out["notes"].append("SD reconstructed from an IQR or a range, so the "
                            "statistics below are approximate")

    # A reconstructed SD larger than the central value of a strictly positive
    # quantity means the distribution is far from normal, so the t and d built
    # on it describe nothing. That is a gap in the evidence, not a negative
    # result, and it is reported as such.
    untrustworthy = None
    if crude:
        for sd, val, who in ((sd_h, row.healthy_value, "healthy"),
                             (sd_s, row.sick_value, "sick")):
            if sd is not None and val not in (None, 0) and \
                    sd / abs(val) > pf["sd_over_value_max"]:
                untrustworthy = (
                    "the %s SD reconstructed from its published range is %.3g, "
                    "%.1fx its central value of %.3g, so this strictly positive "
                    "quantity is strongly skewed and the normal approximation "
                    "behind d and p does not hold"
                    % (who, sd, sd / abs(val), val))
                break

    d = p = None
    if row.healthy_value is not None and row.sick_value is not None:
        d = _cohens_d(row.healthy_value, sd_h, row.n_healthy,
                      row.sick_value, sd_s, row.n_sick)
        _, _, p = _welch(row.healthy_value, sd_h, row.n_healthy,
                         row.sick_value, sd_s, row.n_sick)
    out["cohens_d"], out["p_value"] = d, p
    out["auc_from_d"] = None if d is None else float(norm.cdf(abs(d) / 2 ** 0.5))

    # --- the gate ---------------------------------------------------------
    if row.auc is not None:
        ok = row.auc >= pf["auc_pass_min"]
        out["verdict"] = PASS if ok else FAIL
        out["route"] = "reported AUC"
        out["reason"] = ("reported AUC %.3f %s the %.2f threshold"
                         % (row.auc, "clears" if ok else "is below", pf["auc_pass_min"]))
    elif untrustworthy is not None:
        out["verdict"] = INSUFFICIENT
        out["route"] = "none usable"
        out["reason"] = "no reported AUC and " + untrustworthy
    elif d is not None and p is not None:
        ok = p < pf["p_pass_max"] and abs(d) >= pf["cohens_d_pass_min"]
        out["verdict"] = PASS if ok else FAIL
        out["route"] = "Welch p + Cohen's d"
        out["reason"] = ("d=%.2f (need >=%.1f), p=%.3g (need <%.2g)"
                         % (d, pf["cohens_d_pass_min"], p, pf["p_pass_max"]))
    else:
        out["verdict"] = INSUFFICIENT
        out["route"] = "none available"
        bits = [x for x in (fold_why, why_h, why_s) if x]
        out["reason"] = ("no reported AUC and the statistics cannot be rebuilt: "
                         + "; ".join(dict.fromkeys(bits)) if bits
                         else "no reported AUC and no usable summary statistics")
    return out


def assess_all(bundle):
    return [assess(r, bundle) for r in bundle["clinical"]]
