"""Panels: which combination of modules separates one cancer best.

A single metabolite almost never gives usable specificity. Urinary polyamines
rise in colorectal cancer, but they also rise in benign gastrointestinal
disease, which is exactly what costs the published assays their specificity.
The way out is to read several modules at once and combine them, and since the
plasmid skeleton is fixed, combining modules is a cloning job rather than a new
design.

What this module does: for one cancer, take every module that cleared both
stages, keep the best one per biomarker (two modules for the same analyte add
nothing but cost), and ask what the combination would achieve.

What it does not do, and this is the important caveat: it cannot know how the
markers co-vary. The combined separation of jointly normal markers depends on
their correlation matrix, and that needs the markers measured in the same
patients. Not one source in clinical.csv reports it. So every panel is given as
a range between two stated assumptions - uncorrelated, and correlated at the
value in platform.csv - and never as a single number. A panel whose two bounds
straddle the usefulness threshold is reported as undecided, because that is
what the evidence supports.
"""
import itertools

from . import performance, stage2


def _best_per_biomarker(candidates):
    """One module per analyte: the strongest, measured at the reader."""
    best = {}
    for c in candidates:
        perf = c.get("performance")
        if not perf:
            continue
        bm = c["sensor"].biomarker
        if bm not in best or perf["d_at_reader"] > best[bm]["performance"]["d_at_reader"]:
            best[bm] = c
    return best


def for_cancer(cancer, candidates, platform):
    """Every panel worth reporting for one cancer, largest separation first."""
    passing = [c for c in candidates
               if c["light"] in (stage2.GREEN, stage2.YELLOW)
               and c.get("stage1") and c["stage1"]["row"].cancer == cancer]
    pool = _best_per_biomarker(passing)
    if not pool:
        return []

    rho_lo = platform["panel_rho_independent"]
    rho_hi = platform["panel_rho_correlated"]
    kmax = int(platform["panel_max_size"])
    # Scan rather than take two points: with unequal effect sizes the curve is
    # U-shaped in rho, so neither end is reliably the worst case.
    grid = [rho_lo + (rho_hi - rho_lo) * i / 24.0 for i in range(25)]

    out = []
    names = sorted(pool)
    for size in range(1, min(kmax, len(names)) + 1):
        for combo in itertools.combinations(names, size):
            ds = [pool[b]["performance"]["d_at_reader"] for b in combo]
            scan = [(r, performance.panel(ds, r)) for r in grid]
            scan = [(r, d) for r, d in scan if d is not None]
            if not scan:
                continue
            d_ind = performance.panel(ds, rho_lo)
            rho_worst, d_worst = min(scan, key=lambda rd: rd[1])
            rho_best, d_best = max(scan, key=lambda rd: rd[1])
            out.append(dict(
                cancer=cancer,
                biomarkers=list(combo),
                modules=[pool[b] for b in combo],
                size=size,
                d_independent=d_ind,
                d_worst=d_worst, rho_worst=rho_worst,
                d_best=d_best, rho_best=rho_best,
                auc_independent=performance.auc_from_d(d_ind),
                auc_worst=performance.auc_from_d(d_worst),
                auc_best=performance.auc_from_d(d_best),
                sens_worst=_youden(d_worst),
                sens_best=_youden(d_best),
                # the best case riding on a near-perfect correlation is a
                # suppressor effect, not a design you can build on
                suppressor=rho_best > rho_lo + 0.5 * (rho_hi - rho_lo)
                           and d_best > d_ind * 1.02,
            ))
    out.sort(key=lambda p: -p["d_worst"])
    return out


def _youden(d):
    from scipy.stats import norm
    return float(norm.cdf(d / 2.0))


def all_cancers(candidates, platform):
    cancers = sorted({c["stage1"]["row"].cancer
                      for c in candidates
                      if c.get("stage1") and c["stage1"]["row"].cancer
                      and c["light"] in (stage2.GREEN, stage2.YELLOW)})
    return {k: for_cancer(k, candidates, platform) for k in cancers}


def verdict(panel, platform):
    """Does the panel hold up across every correlation we cannot rule out.

    Judged on the worst point of the scan, never on the independent case and
    never on the best: a panel is only as good as its weakest admissible
    correlation, because nothing in the literature pins rho down.
    """
    lo, hi = panel["auc_worst"], panel["auc_best"]
    if lo is None:
        return "undecided", "the scan produced no usable value"
    threshold = platform["auc_pass_min"]
    rho_hi = platform["panel_rho_correlated"]

    # A single module has nothing to correlate with, so the rho sentence below
    # is not merely redundant for it, it is wrong: it claims an independence
    # from an assumption that was never in play.
    if panel["size"] < 2:
        if lo >= threshold:
            return "holds", ("AUC %.3f on its own, above the %.2f this screen "
                             "asks for" % (lo, threshold))
        return "fails", ("AUC %.3f on its own, below the %.2f this screen asks "
                         "for" % (lo, threshold))

    if lo >= threshold:
        return "holds", ("AUC stays at or above %.3f for every correlation from "
                         "0 to %g, so the panel does not depend on an "
                         "assumption about rho" % (lo, rho_hi))
    if hi >= threshold:
        extra = ""
        if panel.get("suppressor"):
            extra = (" The upper end comes from a suppressor effect at rho = "
                     "%.2f, where correlated markers cancel shared variation; "
                     "that gain needs rho known exactly and does not survive "
                     "estimating it." % panel["rho_best"])
        return "undecided", ("AUC spans %.3f to %.3f across the correlation "
                             "range, and no source measures these markers in "
                             "the same patients.%s" % (lo, hi, extra))
    return "fails", ("below the %.2f threshold at every correlation in the "
                     "range; the best case is AUC %.3f" % (threshold, hi))
