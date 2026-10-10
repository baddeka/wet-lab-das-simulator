"""Run the whole screen and write what the page needs into platform.json.

The page renders; it does not compute. Every number it shows - separations,
folds, sensitivities, panels - is produced here by the same Python the tests
cover, so there is no second implementation of the statistics in JavaScript to
drift away from the first. This project already made that mistake once with the
model constants and spent a month serving a Km of 83 uM after the model had
moved to 310.

    python build_platform.py            write platform.json
    python build_platform.py --print    also print a summary

Everything traces to data/. Nothing is invented here: a module with no
constant, or a study with no spread, is exported with the reason it could not
be evaluated, and the page shows that reason.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import sensorlab                                           # noqa: E402
from sensorlab import (data, panels, performance, report,   # noqa: E402
                       stage1, stage2, tables)

OUT = os.path.join(HERE, "platform.json")
PAGE = os.path.join(HERE, "index.html")

TYPE_LABEL = {
    "A": "oxidase → H₂O₂ → OxyR",
    "B": "transcription factor → promoter",
}


def _f(x, nd=None):
    """JSON-safe float."""
    if x is None:
        return None
    x = float(x)
    return round(x, nd) if nd is not None else x


def export_sensor(s):
    return dict(
        biomarker=s.biomarker, module_type=s.module_type,
        type_label=TYPE_LABEL.get(s.module_type),
        protein=s.protein_name, organism=s.organism, uniprot=s.uniprot,
        km_uM=_f(s.km_uM), kcat_s=_f(s.kcat_s), kd_uM=_f(s.kd_uM),
        efficiency=_f(s.efficiency, 5),
        ph=_f(s.ph), temp_c=_f(s.temp_c),
        doi=s.source_doi, confidence=s.confidence, notes=s.notes,
        missing=s.missing(),
    )


def export_study(s1):
    row = s1["row"]
    return dict(
        biomarker=row.biomarker, cancer=row.cancer, biofluid=row.biofluid,
        stat_type=row.stat_type, units=row.units,
        healthy=_f(row.healthy_value), sick=_f(row.sick_value),
        n_healthy=_f(row.n_healthy), n_sick=_f(row.n_sick),
        normalization=row.normalization, cutoff=_f(row.cutoff),
        auc_reported=_f(row.auc), doi=row.source_doi, notes=row.notes,
        fold=_f(s1["fold"], 4), fold_magnitude=_f(s1["fold_magnitude"], 4),
        direction=s1["direction"],
        cohens_d=_f(s1["cohens_d"], 3), p_value=_f(s1["p_value"]),
        sd_healthy=_f(s1["sd_healthy"], 4), sd_sick=_f(s1["sd_sick"], 4),
        verdict=s1["verdict"], route=s1["route"], reason=s1["reason"],
        cautions=s1["notes"],
    )


def export_candidate(c):
    s = c["sensor"]
    s1 = c.get("stage1")
    perf = c.get("performance")
    out = dict(
        biomarker=s.biomarker, module_type=s.module_type,
        type_label=TYPE_LABEL.get(s.module_type),
        protein=s.protein_name, organism=s.organism, doi=s.source_doi,
        light=c["light"], stage=c["stage"], reason=c["reason"],
        cancer=s1["row"].cancer if s1 else None,
        biofluid=s1["row"].biofluid if s1 else None,
        study_doi=s1["row"].source_doi if s1 else None,
        clinical_fold=_f(s1["fold_magnitude"], 4) if s1 else None,
        direction=s1["direction"] if s1 else None,
        stage1_verdict=s1["verdict"] if s1 else None,
        stage1_reason=s1["reason"] if s1 else None,
        cautions=(s1["notes"] if s1 else []) + c.get("notes", []),
        c_healthy_uM=_f(c.get("c_healthy_uM"), 5),
        c_sick_uM=_f(c.get("c_sick_uM"), 5),
        device_fold=_f(c.get("best_fold_magnitude"), 4),
        required_conc=_f(c.get("required_conc_factor"), 2),
        anchor_name=c.get("anchor_name"), anchor_uM=_f(c.get("anchor_uM")),
        analyte_over_anchor=_f(c.get("analyte_over_anchor"), 5),
        max_cv=_f(c.get("max_cv_at_best"), 4),
        selectivity_note=c.get("selectivity_source"),
        competitors=[dict(biomarker=k["biomarker"], kd_uM=_f(k["kd_uM"]),
                          healthy_uM=_f(k["healthy_uM"], 4),
                          sick_uM=_f(k["sick_uM"], 4))
                     for k in c.get("competitors", [])],
        competitors_unevaluated=c.get("competitors_unevaluated", []),
        performance_missing=c.get("performance_missing"),
    )
    if s.module_type == "A":
        out.update(knockout_required=c.get("knockout_required"),
                   knockout_helps=c.get("knockout_helps"),
                   fold_wildtype=_f(c.get("fold_wildtype"), 4),
                   fold_knockout=_f(c.get("fold_knockout"), 4))
    if perf:
        out.update(
            compression=_f(perf["compression"], 4),
            auc_device=_f(perf["auc_at_reader"], 4),
            sensitivity=_f(perf["sensitivity_youden"], 4),
            specificity=_f(perf["specificity_youden"], 4),
            spec_at_90_sens=_f(c.get("sens_at_90_spec"), 4),
            reader_dominates=perf["reader_dominates"],
            d_device=_f(perf["d_at_reader"], 3),
        )
    return out


def export_panel(p, platform):
    v, why = panels.verdict(p, platform)
    return dict(
        cancer=p["cancer"], biomarkers=p["biomarkers"], size=p["size"],
        modules=[dict(biomarker=m["sensor"].biomarker,
                      protein=m["sensor"].protein_name,
                      module_type=m["sensor"].module_type,
                      d=_f(m["performance"]["d_at_reader"], 3))
                 for m in p["modules"]],
        auc_worst=_f(p["auc_worst"], 4), auc_best=_f(p["auc_best"], 4),
        auc_independent=_f(p["auc_independent"], 4),
        sens_worst=_f(p["sens_worst"], 4), sens_best=_f(p["sens_best"], 4),
        rho_worst=_f(p["rho_worst"], 3), rho_best=_f(p["rho_best"], 3),
        suppressor=p["suppressor"],
        verdict=v, verdict_why=why,
    )


def positioning(bundle, res):
    """Where each module's constant sits against its analyte's clinical range.

    This is the one picture that explains most of the screen's verdicts, so it
    is built for every module that has a constant - including those that never
    reach stage 2 - with the reason carried alongside. A module is shown against
    the best study for its analyte whose units convert to uM, even if that study
    failed stage 1, because "the enzyme is three orders above the clinical
    range" is worth seeing whether or not the cohort separated.
    """
    ut = bundle["unit_table"]
    creat = bundle["scenario"].get("creatinine")
    by_marker = {}
    for s1 in res["stage1"]:
        row = s1["row"]
        h, _ = ut.to_uM(row.healthy_value, row.units, creat)
        k, _ = ut.to_uM(row.sick_value, row.units, creat)
        if h is None or k is None or h <= 0 or k <= 0:
            continue
        rank = (s1["verdict"] == stage1.PASS, s1["fold_magnitude"] or 0)
        cur = by_marker.get(row.biomarker)
        if cur is None or rank > cur[0]:
            by_marker[row.biomarker] = (rank, s1, h, k)

    best_light = {}
    for c in res["candidates"]:
        key = (c["sensor"].biomarker, c["sensor"].protein_name)
        order = {"green": 0, "yellow": 1, "red": 2}
        if key not in best_light or order[c["light"]] < order[best_light[key]["light"]]:
            best_light[key] = c

    rows = []
    for s in bundle["sensors"]:
        anchor = s.km_uM if s.module_type == "A" else s.kd_uM
        if anchor is None or s.biomarker not in by_marker:
            continue
        _, s1, h, k = by_marker[s.biomarker]
        cand = best_light.get((s.biomarker, s.protein_name))
        rows.append(dict(
            biomarker=s.biomarker, protein=s.protein_name,
            module_type=s.module_type, type_label=TYPE_LABEL.get(s.module_type),
            anchor_name="Km" if s.module_type == "A" else "Kd",
            anchor_uM=_f(anchor),
            healthy_uM=_f(min(h, k), 5), sick_uM=_f(max(h, k), 5),
            ratio_to_anchor=_f(max(h, k) / anchor, 5),
            cancer=s1["row"].cancer, biofluid=s1["row"].biofluid,
            study_doi=s1["row"].source_doi,
            stage1_passed=s1["verdict"] == stage1.PASS,
            light=cand["light"] if cand else "red",
            reason=cand["reason"] if cand else "not screened",
        ))
    rows.sort(key=lambda r: r["ratio_to_anchor"], reverse=True)
    return rows


def build(scenario="screen_default"):
    bundle = sensorlab.load(scenario)
    pf = bundle["platform"]
    res = report.build(bundle)

    cands = [export_candidate(c) for c in res["candidates"]]
    all_panels = panels.all_cancers(res["candidates"], pf)

    counts = {}
    for c in cands:
        counts[c["light"]] = counts.get(c["light"], 0) + 1

    biomarkers = sorted({s.biomarker for s in bundle["sensors"]}
                        | {r.biomarker for r in bundle["clinical"]})
    cancers = sorted({r.cancer for r in bundle["clinical"] if r.cancer})

    return dict(
        generated_from="data/sensors.csv, data/clinical.csv, data/platform.csv, "
                       "data/scenarios.csv, data/out_of_scope.csv",
        scenario=dict(
            name=scenario,
            mode=bundle["scenario"].get("mode"),
            OD=_f(bundle["scenario"].get("OD")),
            sample_frac=_f(bundle["scenario"].get("sample_frac")),
            T_read=_f(bundle["scenario"].get("T_read")),
            creatinine=_f(bundle["scenario"].get("creatinine")),
        ),
        thresholds=dict(
            auc_pass_min=_f(pf["auc_pass_min"]),
            p_pass_max=_f(pf["p_pass_max"]),
            cohens_d_pass_min=_f(pf["cohens_d_pass_min"]),
            cv_reader=_f(pf["cv_reader"]), n_rep=_f(pf["n_rep"]),
            z_required=_f(pf["z_required"]),
            conc_factor_max=_f(pf["conc_factor_max"]),
            fold_needed=_f(stage2.fold_needed(pf), 4),
            reader_log_sd=_f(performance.reader_log_sd(pf), 4),
            rho_max=_f(pf["panel_rho_correlated"]),
            panel_max_size=_f(pf["panel_max_size"]),
        ),
        anchors=dict(
            k_mem=_f(pf["k_mem"]), P_endo=_f(pf["P_endo"]),
            k_scav=_f(pf["k_scav"]), K_oxyr=_f(pf["K_oxyr"]),
            resting_h2o2=_f(pf["P_endo"] / pf["k_scav"], 4),
            gradient=_f(1.0 + pf["k_scav"] / pf["k_mem"], 2),
            k_scav_knockout=_f(pf["k_scav_knockout"]),
        ),
        biomarkers=biomarkers, cancers=cancers,
        sensors=[export_sensor(s) for s in bundle["sensors"]],
        studies=[export_study(s) for s in res["stage1"]],
        candidates=cands,
        positioning=positioning(bundle, res),
        counts=counts,
        panels={k: [export_panel(p, pf) for p in v] for k, v in all_panels.items()},
        out_of_scope=tables.read("out_of_scope.csv"),
        gaps=dict(
            no_clinical=sorted({c["biomarker"] for c in cands
                                if c["stage1_verdict"] is None}),
            no_sensor=res["orphan_biomarkers"],
            missing_constants=[dict(biomarker=s.biomarker,
                                    module_type=s.module_type,
                                    protein=s.protein_name,
                                    missing=s.missing())
                               for s in bundle["sensors"] if s.missing()],
        ),
    )


def main(argv):
    payload = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False, sort_keys=True)
    size = os.path.getsize(OUT) / 1024.0
    print("wrote %s (%.1f KB)" % (os.path.basename(OUT), size))
    print("  %d sensors, %d studies, %d candidates"
          % (len(payload["sensors"]), len(payload["studies"]),
             len(payload["candidates"])))
    print("  traffic light: %s"
          % ", ".join("%s %d" % (k, v) for k, v in sorted(payload["counts"].items())))
    print("  panels for: %s" % (", ".join(payload["panels"]) or "none"))

    if "--json" not in argv:
        import page_layout
        html = page_layout.page(payload)
        with open(PAGE, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(html)
        print("wrote %s (%.1f KB)"
              % (os.path.basename(PAGE), len(html.encode("utf-8")) / 1024.0))
        for need in ("<!DOCTYPE html>", "</html>", "Km", "References"):
            assert need in html, "missing from the page: " + need
        # A Python None in the markup means a figure the renderer thought it had
        # and did not. It must surface as an em dash and a stated reason, never
        # as the word None.
        assert ">None<" not in html and " None " not in html, \
            "a Python None reached the markup"
        print("  page checks passed")

    if "--print" in argv:
        for c in payload["candidates"]:
            if c["light"] != "red":
                print("   %-6s %-11s %-1s %-22s AUC %s sens %s"
                      % (c["light"], c["biomarker"], c["module_type"],
                         c["protein"][:22], c.get("auc_device"),
                         c.get("sensitivity")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
