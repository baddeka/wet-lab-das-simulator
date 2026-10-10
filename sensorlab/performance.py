"""What the device would actually achieve on patients: sensitivity and
specificity at our own limit of detection.

A fold change is not a diagnostic. Two things stand between them.

**Compression.** The device does not report the analyte, it reports
fluorescence, and the chain from one to the other is sublinear. A clinical
ratio of 2.29 arrives at the reader as 1.36. The surviving fraction of the log
difference is measured here directly, by running the module at both clinical
levels and comparing:

    c = ln(device fold) / ln(clinical fold)

c is the slope of the whole transfer function in log-log, including the Hill
compression at OxyR and the dilution of the signal into the cell's own
peroxide. It is what the biological spread gets multiplied by as well, so it
cannot be recovered by rescaling afterwards.

**Reader noise.** On top of the squeezed biological spread sits the
measurement error, cv_reader over sqrt(n_rep). That is the limit of detection
in the only sense that matters for classification: the smallest difference the
reader can still call apart.

Everything is done on the log scale, because concentrations of urinary
metabolites are roughly log-normal and because a reader CV is multiplicative.
With both groups normal on that scale,

    d = c * |ln(sick/healthy)| / pooled total SD
    AUC = Phi(d / sqrt(2))

and at the Youden-optimal cut-off sensitivity equals specificity equals
Phi(d/2). Choosing a cut-off elsewhere trades one against the other, which
`at_cutoff` does.

Nothing here invents a distribution. If clinical.csv gives no spread, the
functions return None with a reason, and the candidate is reported as lacking
the data rather than being given an assumed variance.
"""
import math

from scipy.stats import norm


def log_sd(value, sd):
    """Spread on the natural-log scale, from a mean and an SD on the raw scale.

    For a log-normal with small relative spread this is just sd/value; the exact
    form sqrt(ln(1 + (sd/value)^2)) is used so it stays sane when the spread is
    comparable to the mean, which several of these cohorts are.
    """
    if value is None or sd is None or value <= 0 or sd < 0:
        return None
    cv = sd / value
    return math.sqrt(math.log(1.0 + cv * cv))


def compression(clinical_fold, device_fold):
    """Fraction of the log difference that survives to the reader."""
    if not clinical_fold or not device_fold:
        return None
    lc, ld = math.log(clinical_fold), math.log(device_fold)
    if lc == 0:
        return None
    return ld / lc


def reader_log_sd(platform):
    """Measurement spread on the log scale: this is the limit of detection."""
    return platform["cv_reader"] / math.sqrt(platform["n_rep"])


def separation(s1, device_fold, platform):
    """Return (result dict, reason_if_none) for one module on one study."""
    row = s1["row"]
    if s1.get("fold") is None:
        return None, "no clinical fold, so nothing can be propagated"
    sd_h, sd_s = s1.get("sd_healthy"), s1.get("sd_sick")
    if sd_h is None or sd_s is None:
        return None, ("clinical.csv reports no usable spread for this study, so "
                      "sensitivity and specificity cannot be computed; only the "
                      "fold change is available")

    lsd_h = log_sd(row.healthy_value, sd_h)
    lsd_s = log_sd(row.sick_value, sd_s)
    if lsd_h is None or lsd_s is None:
        return None, "central values must be positive to work on the log scale"

    c = compression(abs(s1["fold_magnitude"]), device_fold)
    if c is None:
        return None, "the device fold could not be compared with the clinical fold"

    rdr = reader_log_sd(platform)
    # the biological spread is squeezed by the same factor as the signal
    tot_h = math.hypot(c * lsd_h, rdr)
    tot_s = math.hypot(c * lsd_s, rdr)
    pooled = math.sqrt(0.5 * (tot_h ** 2 + tot_s ** 2))
    if pooled <= 0:
        return None, "pooled spread is zero"

    delta = c * abs(math.log(s1["fold_magnitude"]))
    d = delta / pooled
    auc = float(norm.cdf(d / math.sqrt(2.0)))
    youden = float(norm.cdf(d / 2.0))

    return dict(
        compression=c,
        reader_log_sd=rdr,
        bio_log_sd_healthy=lsd_h, bio_log_sd_sick=lsd_s,
        total_log_sd_healthy=tot_h, total_log_sd_sick=tot_s,
        d_at_reader=d, auc_at_reader=auc,
        sensitivity_youden=youden, specificity_youden=youden,
        reader_dominates=rdr > c * max(lsd_h, lsd_s),
    ), None


def at_cutoff(s1, perf, sens_target):
    """Specificity obtainable at the cut-off that delivers a target sensitivity.

    Clinical practice fixes sensitivity first for a screening test and accepts
    whatever specificity follows, so that is the direction reported.
    """
    if perf is None or not 0.0 < sens_target < 1.0:
        return None
    d = perf["d_at_reader"]
    # cut-off placed z_s SDs below the sick mean
    z_s = norm.ppf(sens_target)
    # distance of that cut-off above the healthy mean, in healthy SDs
    z_h = d - z_s * (perf["total_log_sd_sick"] / perf["total_log_sd_healthy"])
    return float(norm.cdf(z_h))


def panel(members, rho):
    """Combine several modules into one panel score.

    members is a list of per-module d values on the reader. For jointly normal
    markers with equal pairwise correlation rho, the panel's separation is the
    Mahalanobis distance d_panel = sqrt(d' R^-1 d).

    **Correlation is not simply bad.** With equal effect sizes it degrades the
    panel monotonically, from sqrt(k)*d at rho = 0 down towards d. With unequal
    effect sizes it does not: the curve is U-shaped and diverges as rho -> 1,
    because correlated markers that respond by different amounts let their
    *difference* cancel the shared variation. By Cauchy-Schwarz the numerator
    sum(d^2) - sum(d)^2/k is strictly positive whenever the effects differ, so
    the quadratic form blows up against the vanishing (1 - rho).

    That is real statistics, not an artefact, but it is worthless here: the gain
    exists only if rho is known exactly, and estimating it with any error
    destroys it. So do not treat rho = 0 as the optimistic end and a high rho as
    the pessimistic one. Scan the range and report the envelope, which is what
    panels.py does.

    The real quantity needs the covariance matrix of the markers measured in the
    same patients, and none of the published summaries in clinical.csv contain
    it.
    """
    ds = [d for d in members if d is not None and d > 0]
    k = len(ds)
    if k == 0:
        return None
    if k == 1:
        return ds[0]
    if rho <= -1.0 / (k - 1) or rho >= 1.0:
        return None
    ssq = sum(d * d for d in ds)
    ssum = sum(ds)
    # For an equicorrelation matrix R = (1-rho)I + rho*J,
    #     R^-1 = [ I - rho*J/(1 + (k-1)rho) ] / (1 - rho)
    # so d' R^-1 d = [ sum(d^2) - rho*sum(d)^2 / (1 + (k-1)rho) ] / (1 - rho).
    # Sanity check for k = 2 with equal d: this gives 2d^2/(1+rho), which falls
    # as rho rises. If a panel ever looks better correlated than independent,
    # this expression is wrong.
    quad = (ssq - rho * ssum * ssum / (1.0 + rho * (k - 1))) / (1.0 - rho)
    return math.sqrt(quad) if quad > 0 else None


def auc_from_d(d):
    return None if d is None else float(norm.cdf(d / math.sqrt(2.0)))
