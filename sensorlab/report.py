"""Building the candidate matrix and rendering the traffic-light table.

A candidate is one sensor paired with one clinical study, because the same
protein can look feasible against one cohort and hopeless against another, and
collapsing that away would hide the disagreement between studies.

Negative results are printed, not filtered. Every red entry states its reason
and the stage that rejected it.
"""
from . import stage1, stage2

GREEN, YELLOW, RED = stage2.GREEN, stage2.YELLOW, stage2.RED
ORDER = {GREEN: 0, YELLOW: 1, RED: 2}
MARK = {GREEN: "GREEN ", YELLOW: "YELLOW", RED: "RED   "}


def build(bundle):
    """Run both stages over every sensor-study pair."""
    s1_all = stage1.assess_all(bundle)

    by_marker = {}
    for s1 in s1_all:
        by_marker.setdefault(s1["biomarker"], []).append(s1)

    candidates = []
    for sensor in bundle["sensors"]:
        rows = by_marker.get(sensor.biomarker, [])
        if not rows:
            candidates.append(dict(
                sensor=sensor, stage1=None, light=RED, stage="stage 1",
                reason="no clinical separation data: clinical.csv has no row for %s"
                       % sensor.biomarker,
                best_fold_magnitude=None, required_conc_factor=None))
            continue
        for s1 in rows:
            if s1["verdict"] != stage1.PASS:
                label = ("no clinical separation" if s1["verdict"] == stage1.FAIL
                         else "clinical data insufficient")
                candidates.append(dict(
                    sensor=sensor, stage1=s1, light=RED, stage="stage 1",
                    reason="%s: %s" % (label, s1["reason"]),
                    best_fold_magnitude=None, required_conc_factor=None))
            else:
                candidates.append(stage2.feasibility(sensor, s1, bundle))

    orphans = sorted({s1["biomarker"] for s1 in s1_all}
                     - {s.biomarker for s in bundle["sensors"]})
    return dict(stage1=s1_all, candidates=candidates, orphan_biomarkers=orphans)


def _rank(c):
    return (ORDER[c["light"]], -(c.get("best_fold_magnitude") or 0.0))


def best_per_sensor(candidates):
    """One row per sensor: its most favourable clinical context."""
    best = {}
    for c in candidates:
        key = (c["sensor"].biomarker, c["sensor"].protein_name)
        if key not in best or _rank(c) < _rank(best[key]):
            best[key] = c
    return sorted(best.values(), key=_rank)


def _fmt(x, spec="%.3g"):
    return "-" if x is None else spec % x


def _wrap(text, width):
    """Wrap a reason onto fixed-width lines without pulling in textwrap."""
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = word if not line else line + " " + word
    if line:
        lines.append(line)
    return lines


def _context(c):
    s1 = c.get("stage1")
    if not s1:
        return "no clinical row"
    row = s1["row"]
    return "%s / %s" % (row.cancer or "?", row.biofluid)


def _study(c):
    """Context plus a short study tag, so two studies of the same fluid differ."""
    s1 = c.get("stage1")
    if not s1:
        return "no clinical row"
    doi = s1["row"].source_doi or "?"
    return "%s  [%s]" % (_context(c), doi.rsplit("/", 1)[-1][:28])


# --------------------------------------------------------------------------
def render_header(bundle, result):
    pf, sc = bundle["platform"], bundle["scenario"]
    need = stage2.fold_needed(pf)
    print("=" * 108)
    print("BIOSENSOR MODULE SCREEN")
    print("=" * 108)
    print("scenario           : %s (mode=%s, OD=%g, sample %g%% v/v, read %gs)"
          % (bundle["scenario_name"], sc.get("mode"), sc.get("OD"),
             100 * sc.get("sample_frac", 0), sc.get("T_read")))
    print("data               : %d sensor rows, %d clinical rows, %d candidate pairs"
          % (len(bundle["sensors"]), len(bundle["clinical"]), len(result["candidates"])))
    print("stage 1 passes if  : reported AUC >= %.2f, else Welch p < %.2g and |d| >= %.1f"
          % (pf["auc_pass_min"], pf["p_pass_max"], pf["cohens_d_pass_min"]))
    print("stage 2 passes if  : fold >= %.3f, the reader's limit at CV %.0f%% and n=%g"
          % (need, 100 * pf["cv_reader"], pf["n_rep"]))
    print("                     green needs no concentration, yellow needs up to %gx"
          % pf["conc_factor_max"])
    print("assumed for B and C: Hill n = %g (no source reports one)" % pf["hill_n_binding"])
    print("sample assumption  : urine creatinine %g g/L, needed by the "
          "creatinine-normalised units" % sc.get("creatinine", float("nan")))


def render_stage1(result):
    print()
    print("-" * 108)
    print("STAGE 1  clinical separation, before any sensor is considered")
    print("-" * 108)
    print("%-11s %-13s %-30s %7s %7s %8s %6s  %s"
          % ("biomarker", "cancer", "biofluid", "fold", "d", "p", "AUC", "verdict"))
    for s1 in sorted(result["stage1"], key=lambda r: (r["biomarker"], r["label"])):
        row = s1["row"]
        print("%-11s %-13s %-30s %7s %7s %8s %6s  %s"
              % (row.biomarker, (row.cancer or "-")[:13], (row.biofluid or "-")[:30],
                 _fmt(s1["fold"], "%.3f"), _fmt(s1["cohens_d"], "%.2f"),
                 _fmt(s1["p_value"], "%.1e"), _fmt(row.auc, "%.2f"),
                 s1["verdict"]))
    counts = {}
    for s1 in result["stage1"]:
        counts[s1["verdict"]] = counts.get(s1["verdict"], 0) + 1
    print("  " + ", ".join("%s: %d" % (k, counts[k]) for k in sorted(counts)))


def render_summary(result, title="SUMMARY  best clinical context per sensor"):
    rows = best_per_sensor(result["candidates"])
    print()
    print("-" * 108)
    print(title)
    print("-" * 108)
    print("%-6s %-11s %-1s %-22s %-24s %8s %4s %7s %6s"
          % ("light", "biomarker", "T", "protein", "clinical context",
             "fold", "dir", "need x", "CV max"))
    for c in rows:
        s, s1 = c["sensor"], c.get("stage1")
        print("%-6s %-11s %-1s %-22s %-24s %8s %4s %7s %6s"
              % (MARK[c["light"]], s.biomarker, s.module_type,
                 s.protein_name[:22], _context(c)[:24],
                 _fmt(c.get("best_fold_magnitude"), "%.3f"),
                 (s1 and s1["direction"]) or "-",
                 _fmt(c.get("required_conc_factor"), "%g"),
                 _fmt(c.get("max_cv_at_best") and 100 * c["max_cv_at_best"], "%.0f%%")))
    print("  fold is the magnitude of the change; dir says whether the biomarker "
          "rises or falls in disease")
    tally = {}
    for c in rows:
        tally[c["light"]] = tally.get(c["light"], 0) + 1
    print("  %d sensors: %s" % (len(rows), ", ".join(
        "%s %d" % (k, tally[k]) for k in (GREEN, YELLOW, RED) if k in tally)))


def render_passes(bundle, result):
    passes = [c for c in result["candidates"] if c["light"] in (GREEN, YELLOW)]
    print()
    print("-" * 108)
    print("PASSING CANDIDATES  detail")
    print("-" * 108)
    if not passes:
        print("  none")
        return
    for c in sorted(passes, key=_rank):
        s, s1 = c["sensor"], c["stage1"]
        print("%s  %s  [type %s]" % (MARK[c["light"]], s.label, s.module_type))
        print("        clinical  : %s, fold %.3f %s"
              % (_study(c), s1["fold"], s1["direction"]))
        print("        separation: %s" % s1["reason"])
        print("        levels    : healthy %.4g uM, sick %.4g uM in the raw biofluid"
              % (c["c_healthy_uM"], c["c_sick_uM"]))
        print("        response  : fold %.4f at best %gx concentration; %s/%s = %.3g"
              % (c["best_fold_magnitude"], c["best_conc_factor"],
                 "analyte", c["anchor_name"], c["analyte_over_anchor"]))
        for comp in c.get("competitors", []):
            print("        competes  : %s also binds this protein, Kd %g uM, at "
                  "%.3g uM healthy / %.3g uM sick"
                  % (comp["biomarker"], comp["kd_uM"],
                     comp["healthy_uM"], comp["sick_uM"]))
        if c.get("fold_without_competition") is not None:
            clean = c["fold_without_competition"]
            clean_mag = max(clean, 1.0 / clean)
            print("                    fold would be %.4f with the target alone, "
                  "so competition costs %.0f%% of it"
                  % (clean_mag, 100 * (1 - c["best_fold_magnitude"] / clean_mag)))
        if c.get("selectivity_source"):
            print("        selectiv. : %s" % c["selectivity_source"])
        print("        verdict   : %s" % c["reason"])
        if s.module_type == "A":
            if c["knockout_required"]:
                verdict = "REQUIRED"
            elif c["knockout_helps"]:
                verdict = "helps"
            elif c["fold_knockout"] < c["fold_wildtype"]:
                verdict = "HARMFUL, it saturates OxyR"
            else:
                verdict = "not needed"
            print("        scavengers: knockout %s (fold %.4f WT -> %.4f in Hpx-)"
                  % (verdict, c["fold_wildtype"], c["fold_knockout"]))
        if s.module_type == "C":
            print("        note      : occupancy fold; no amplification and the read "
                  "time does not enter. Converting to a measured")
            print("                    fluorescence fold needs the protein's dynamic "
                  "range, which sensors.csv does not carry.")
            if c["analyte_over_anchor"] < bundle["platform"]["kd_ratio_lo"]:
                print("                    analyte/Kd = %.3g, well below Kd: the "
                      "occupancy RATIO is preserved there, but the absolute"
                      % c["analyte_over_anchor"])
                print("                    fluorescence change is small, and how "
                      "small cannot be judged without the dynamic range.")
        for n in s1["notes"]:
            print("        caution   : %s" % n)


def render_rejections(result):
    reds = [c for c in result["candidates"] if c["light"] == RED]
    print()
    print("-" * 108)
    print("REJECTED  %d of %d candidate pairs, with the stage that rejected them"
          % (len(reds), len(result["candidates"])))
    print("-" * 108)

    # Grouped on the full reason, so each distinct reason is stated once and in
    # full, and every affected candidate is still listed under it.
    groups = {}
    for c in reds:
        groups.setdefault((c["stage"], c["reason"]), []).append(c)

    for (stage, reason), bucket in sorted(
            groups.items(), key=lambda kv: (kv[0][0], -len(kv[1]), kv[0][1])):
        print()
        print("  [%s]  %d candidate%s" % (stage, len(bucket),
                                          "" if len(bucket) == 1 else "s"))
        for line in _wrap(reason, 100):
            print("    %s" % line)
        for c in sorted(bucket, key=lambda x: (x["sensor"].biomarker,
                                               x["sensor"].protein_name)):
            s = c["sensor"]
            print("      %-11s %-1s %-30s %s"
                  % (s.biomarker, s.module_type, s.protein_name[:30], _study(c)))


def render_gaps(bundle, result):
    print()
    print("-" * 108)
    print("GAPS")
    print("-" * 108)
    if result["orphan_biomarkers"]:
        print("  clinical data but no sensor element in sensors.csv:")
        for b in result["orphan_biomarkers"]:
            print("      %s" % b)
    no_clin = sorted({c["sensor"].biomarker for c in result["candidates"]
                      if c["stage1"] is None})
    if no_clin:
        print("  sensor element but no clinical row in clinical.csv:")
        for b in no_clin:
            print("      %s" % b)
    incomplete = [s for s in bundle["sensors"] if s.missing()]
    if incomplete:
        print("  sensor rows missing the constant their module type needs:")
        for s in incomplete:
            print("      %-11s %-1s %-26s missing %s"
                  % (s.biomarker, s.module_type, s.protein_name,
                     ", ".join(s.missing())))


def render_all(bundle, result, full=False):
    render_header(bundle, result)
    render_stage1(result)
    render_summary(result)
    render_passes(bundle, result)
    render_rejections(result)
    render_gaps(bundle, result)
    if full:
        print()
        print("-" * 108)
        print("FULL MATRIX  every sensor against every clinical study")
        print("-" * 108)
        for c in sorted(result["candidates"],
                        key=lambda x: (x["sensor"].biomarker,
                                       x["sensor"].protein_name, _rank(x))):
            s = c["sensor"]
            print("%-6s %-11s %-1s %-22s %-26s %s"
                  % (MARK[c["light"]], s.biomarker, s.module_type,
                     s.protein_name[:22], _context(c)[:26], c["reason"][:60]))
