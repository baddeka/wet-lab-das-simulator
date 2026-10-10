"""Guard the published page against the failure that already happened once.

site.html used to carry its own copy of every model constant. That copy drifted:
the model moved Km from 83 to 310 uM and the page went on serving 83 to anyone
who opened it. These checks make that impossible to repeat quietly.

    python tests/test_site.py

What is enforced:

  1. The config block committed in site.html matches what the data files
     produce. If someone edits a CSV and forgets to rebuild, this fails.
  2. index.html, the file GitHub Pages actually serves, matches too. If someone
     edits site.html and forgets to rebuild, this fails.
  3. No model constant appears in site.html as a literal any more.
  4. The Km the page ships is the Km of the working row of sensors.csv, checked
     end to end rather than by eye.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import build_site                                     # noqa: E402
from sensorlab import data                            # noqa: E402

FAILURES = []

# Parameter names the model owns. None of these may be followed by a number in
# site.html: they have to come from the injected config.
MODEL_KEYS = [
    "V_das", "creatinine", "conc_factor", "sample_frac", "interferent",
    "selectivity", "OD", "phi_per_OD", "peri_frac", "k_mem", "k_scav",
    "P_endo", "k_chem", "kcat", "Km", "E", "alpha", "K_oxyr", "n_hill",
    "beta", "leak", "k_mat", "mu_pre", "T_read", "cv", "n_rep",
    "v_healthy", "v_cutoff",
]


def check(name, cond, detail=""):
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name,
                           "" if cond else "\n         -> " + str(detail)))
    if not cond:
        FAILURES.append(name)


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def main():
    print("the page's config comes from the data files")
    expected = build_site.build_config()

    source = read("site.html")
    in_source = build_site.extract(source)
    check("site.html carries a config block", in_source is not None,
          "no <script id=\"model-config\"> found")
    if in_source is not None:
        check("site.html's config matches the data files", in_source == expected,
              "run: python build_site.py --sync")

    built_path = os.path.join(ROOT, "simulator.html")
    check("simulator.html exists", os.path.exists(built_path),
          "run: python build_site.py")
    if os.path.exists(built_path):
        built = read("simulator.html")
        in_built = build_site.extract(built)
        check("simulator.html's config matches the data files", in_built == expected,
              "the served page is stale; run: python build_site.py")
        check("simulator.html is a standalone document",
              built.lstrip().startswith("<!DOCTYPE html>"))

    print()
    print("no model constant survives as a literal in site.html")
    # Strip the injected config block before scanning: it is generated, and it
    # is the one place numbers are supposed to appear.
    scan = re.sub(r'<script id="model-config".*?</script>', "", source, flags=re.S)

    # Prose counts too. The page told readers "Km 83 uM" in its opening
    # paragraph long after the model had moved to 310, because the first version
    # of this check only looked for the object-literal form "Km:83".
    for key in ("k_mem", "P_endo", "k_scav", "K_oxyr", "kcat", "Km"):
        prose = re.findall(
            r"%s\s*(?:&asymp;|&#8776;|≈|=)?\s*(-?[0-9][0-9.]*)" % re.escape(key),
            scan)
        prose = [v for v in prose if float(v) != 0.0]
        check("%s is not quoted in the prose" % key, not prose,
              "the text still states %s; fill it from CFG.anchors instead"
              % ", ".join(prose))

    for key in MODEL_KEYS:
        # Only object-literal key positions count, so a ternary such as
        # "p.cr_norm ? 1/p.creatinine : 1" is not mistaken for an assignment.
        # A literal zero is allowed: it means "absent" - computing the fold with
        # interferent:0 is a counterfactual, not a smuggled constant.
        hits = [m for m in re.findall(
            r"[{,]\s*%s\s*:\s*(-?[0-9][0-9.eE+\-]*)" % re.escape(key), scan)
            if float(m) != 0.0]
        check("%s is not hardcoded" % key, not hits,
              "literal(s) %s left in site.html; move the value into a data file"
              % ", ".join(hits))

    print()
    print("end to end: sensors.csv reaches the page")
    sc = data.load_scenarios()["web_default"]
    rows = [s for s in data.load_sensors()
            if s.biomarker == sc["sensor_biomarker"]
            and s.protein_name == sc["sensor_protein"]]
    check("the scenario's enzyme row exists", len(rows) == 1, rows)
    if len(rows) == 1:
        sensor = rows[0]
        check("the page's Km is the row's Km",
              expected["P0"]["Km"] == sensor.km_uM,
              (expected["P0"]["Km"], sensor.km_uM))
        check("the page's kcat is the row's kcat",
              expected["P0"]["kcat"] == sensor.kcat_s,
              (expected["P0"]["kcat"], sensor.kcat_s))
        check("the page names its enzyme", expected["labels"]["enzyme"] == sensor.protein_name)
        check("the page carries the enzyme's DOI",
              expected["labels"]["enzyme_source"] == sensor.source_doi)

    print()
    print("the presets are the ones in web_presets.csv")
    presets, default_index = build_site.presets()
    labels = [p["n"] for p in presets]
    check("every preset has a label and parameters",
          all(p["n"] and p["p"] for p in presets), labels)
    check("exactly one preset is the default",
          sum(1 for r in data.tables.read("web_presets.csv") if r["default"]) == 1)
    check("the default index is in range", 0 <= default_index < len(presets),
          default_index)
    check("preset modes are valid",
          all(p["p"].get("mode") in (None, "free", "peri", "cyto") for p in presets),
          [p["p"].get("mode") for p in presets])

    print()
    if FAILURES:
        print("%d check(s) failed: %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
