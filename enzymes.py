"""Put different enzymes on the same biomarker and compare them.

    python enzymes.py                        all biomarkers that have type A rows
    python enzymes.py --biomarker DiAcSpm    one of them
    python enzymes.py --scenario das_reference

Every enzyme comes from data/sensors.csv. To compare a new one, add a row
there; nothing in this file needs changing.

What the comparison is for: catalytic efficiency and fold change are not the
same question. Below Km the branch is first order in kcat/Km, so efficiency
sets how much enzyme you must load to turn the analyte over inside the read
time. The fold change is set by how much peroxide the analyte can make against
the cell's own flux, and that ceiling does not move when the enzyme improves.
An enzyme two orders more efficient can therefore buy a hundredfold lower
enzyme loading and almost no extra signal.
"""
import math
import sys

import das_model
import sensorlab
from sensorlab import stage1, stage2


def min_enzyme_uM(sensor, platform, T_read):
    """Enzyme needed to convert the target fraction of analyte within the read.

    Below Km the decay is first order with rate (kcat/Km)*E, so
    E = -ln(1 - target) / ((kcat/Km) * T).
    """
    eff = sensor.efficiency
    if eff is None or T_read in (None, 0):
        return None
    return -math.log(1.0 - platform["conversion_target"]) / (eff * T_read)


def best_clinical_row(biomarker, bundle):
    """The clinical study for this biomarker that cleared stage 1 most strongly."""
    passing = [s1 for s1 in stage1.assess_all(bundle)
               if s1["biomarker"] == biomarker and s1["verdict"] == stage1.PASS]
    if not passing:
        return None
    return max(passing, key=lambda s: s["fold_magnitude"] or 0.0)


def compare(biomarker, bundle):
    pf = bundle["platform"]
    enzymes = [s for s in bundle["sensors"]
               if s.biomarker == biomarker and s.module_type == "A"]
    if not enzymes:
        return

    print("=" * 108)
    print("ENZYME COMPARISON  %s  (%d type A rows, scenario %s)"
          % (biomarker, len(enzymes), bundle["scenario_name"]))
    print("=" * 108)

    usable = [e for e in enzymes if not e.missing()]
    for e in enzymes:
        if e.missing():
            print("  %-24s no data: %s not reported (%s)"
                  % (e.protein_name, ", ".join(e.missing()), e.source_doi))
    if not usable:
        print("  nothing to compare")
        return

    effs = [e.efficiency for e in usable]
    print()
    print("%-24s %-26s %8s %8s %11s %9s"
          % ("enzyme", "organism", "kcat", "Km uM", "kcat/Km", "rel."))
    for e in sorted(usable, key=lambda x: -x.efficiency):
        print("%-24s %-26s %8.1f %8.1f %11.3f %8.1fx"
              % (e.protein_name[:24], (e.organism or "not recorded")[:26],
                 e.kcat_s, e.km_uM, e.efficiency, e.efficiency / min(effs)))
    print("  spread in catalytic efficiency: %.0fx, %.2f orders of magnitude"
          % (max(effs) / min(effs), math.log10(max(effs) / min(effs))))

    s1 = best_clinical_row(biomarker, bundle)
    if s1 is None:
        print()
        print("  no clinical study for %s clears stage 1, so there is no clinical"
              % biomarker)
        print("  level at which to compare the response. Efficiency above is all"
              " that can be said.")
        return

    row = s1["row"]
    print()
    print("against %s / %s  (%s, fold %.3f %s)"
          % (row.cancer, row.biofluid, row.source_doi, s1["fold"], s1["direction"]))
    print("%-24s %9s %9s %10s %12s %11s"
          % ("enzyme", "fold", "need x", "converted", "min [E] uM", "[E] margin"))

    results = {e.protein_name: stage2.feasibility(e, s1, bundle) for e in usable}
    for e in sorted(usable, key=lambda x: -x.efficiency):
        res = results[e.protein_name]
        e_min = min_enzyme_uM(e, pf, bundle["scenario"]["T_read"])
        e_have = bundle["scenario"]["E"]
        conv = (res.get("extras") or {}).get("converted")
        margin = e_have / e_min
        print("%-24s %9s %9s %10s %12.3g %11s"
              % (e.protein_name[:24],
                 "%.4f" % res["best_fold_magnitude"] if res.get("best_fold_magnitude") else "-",
                 "%g" % res["required_conc_factor"] if res.get("required_conc_factor") else "-",
                 "%.1f%%" % (100 * conv) if conv is not None else "-",
                 e_min,
                 ("%.0fx" % margin) if margin >= 10 else ("%.2gx" % margin)))

    folds = [results[e.protein_name]["best_fold_magnitude"] for e in usable]
    folds = [f for f in folds if f]
    if len(folds) > 1:
        print()
        print("  catalytic efficiency spans %.0fx; the fold change spans %.2fx."
              % (max(effs) / min(effs), max(folds) / min(folds)))
        print("  min [E] is the enzyme needed to turn over %.0f%% of the analyte in "
              "the %gs read." % (100 * pf["conversion_target"],
                                 bundle["scenario"]["T_read"]))
        print("  [E] margin is how far the scenario's %g uM exceeds that minimum."
              % e_have)


def main(argv):
    scenario = "screen_default"
    if "--scenario" in argv:
        scenario = argv[argv.index("--scenario") + 1]
    bundle = sensorlab.load(scenario)

    if "--biomarker" in argv:
        markers = [argv[argv.index("--biomarker") + 1]]
    else:
        markers = sorted({s.biomarker for s in bundle["sensors"]
                          if s.module_type == "A"})

    for i, m in enumerate(markers):
        if i:
            print()
        compare(m, bundle)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
