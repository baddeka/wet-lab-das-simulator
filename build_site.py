# -*- coding: utf-8 -*-
"""Build index.html from site.html, with the model constants injected from data/.

Two jobs, and the second is the important one.

1. site.html is the page source as the Artifact runtime served it. A plain web
   server supplies no document skeleton and no reset, so everything the runtime
   provided has to be written out here.

2. The page used to carry its own copy of every model constant - its own Km, its
   own kcat, its own scavenging rate, its own preset scenarios. That copy drifted
   away from the Python model and went on serving a Km of 83 uM after the model
   had moved to 310. So the page no longer owns any of them: this script reads
   data/platform.csv, data/scenarios.csv, data/sensors.csv and
   data/web_presets.csv, and writes a single JSON block into the page. The page
   reads its starting state out of that block and nothing else.

   The consequence worth remembering: to change what the published page
   computes, edit a CSV and rebuild. Never edit a number in site.html.

    python build_site.py                 write index.html
    python build_site.py --sync          also refresh site.html's own copy of
                                         the block, so the committed source is
                                         not stale
    python build_site.py out.html        write somewhere else

tests/test_site.py fails if site.html's block and the data files disagree, or if
a model constant creeps back into the page as a literal.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import das_model                                      # noqa: E402
from sensorlab import data, tables                    # noqa: E402

SRC = os.path.join(HERE, "site.html")
CONFIG_ID = "model-config"

# The keys the page's JS actually reads, and where each comes from. Anything not
# listed here stays out of the page, so the thresholds and screening parameters
# of the Python tool are not shipped to the browser.
PAGE_KEYS = [
    "V_das", "creatinine", "conc_factor", "sample_frac", "interferent",
    "selectivity", "cr_norm", "OD", "phi_per_OD", "peri_frac", "k_mem",
    "k_scav", "P_endo", "k_chem", "kcat", "Km", "E", "alpha", "mode",
    "K_oxyr", "n_hill", "beta", "leak", "k_mat", "mu_pre", "growing",
    "T_read", "cv", "n_rep",
]
BOOLEAN_KEYS = {"cr_norm", "growing"}
RENAMED = {"cv": "cv_reader"}


def _coerce(key, value):
    if key in BOOLEAN_KEYS:
        return bool(value)
    return value


def starting_state(scenario="web_default"):
    """The page's P0, assembled from the data files exactly as the model is."""
    p = das_model.load_defaults(scenario)
    out = {}
    missing = []
    for key in PAGE_KEYS:
        source = RENAMED.get(key, key)
        if source not in p:
            missing.append(source)
            continue
        out[key] = _coerce(key, p[source])
    if missing:
        raise SystemExit("the page needs %s, which scenario %r does not supply; "
                         "add them to the data files rather than to site.html"
                         % (", ".join(missing), scenario))
    return out


def presets():
    """The named scenarios behind the page's 'Load a scenario' control."""
    rows = tables.read("web_presets.csv")
    rows.sort(key=lambda r: tables.num(r["order"]))
    out, default_index = [], 0
    for i, r in enumerate(rows):
        p = {}
        for key, raw in r.items():
            if key in ("order", "label", "default", "note") or raw is None:
                continue
            if key == "mode":
                p[key] = raw
            else:
                p[key] = _coerce(key, tables.num(raw, key))
        out.append({"n": r["label"], "p": p, "note": r["note"]})
        if r["default"]:
            default_index = i
    return out, default_index


def build_config(scenario="web_default"):
    sc = data.load_scenarios()[scenario]
    sensor_name = sc.get("sensor_protein")
    sensor = next((s for s in data.load_sensors()
                   if s.protein_name == sensor_name
                   and s.biomarker == sc.get("sensor_biomarker")), None)
    preset_list, default_index = presets()
    # The prose at the top of the page restates the model's literature anchors.
    # Those are the platform values, not the scenario's: the page starts on
    # non-growing cells at P_endo 4, while the anchor quoted from Seaver & Imlay
    # is the growing-culture figure of 14. Keeping them separate stops the text
    # and the sliders from contradicting each other.
    pf = data.load_platform()
    anchors = {
        "k_mem": pf["k_mem"],
        "P_endo": pf["P_endo"],
        "k_scav": pf["k_scav"],
        "K_oxyr": pf["K_oxyr"],
        "resting_h2o2": pf["P_endo"] / pf["k_scav"],
        "kcat": sensor.kcat_s if sensor else None,
        "Km": sensor.km_uM if sensor else None,
        "gradient": 1.0 + pf["k_scav"] / pf["k_mem"],
    }
    return {
        "P0": starting_state(scenario),
        "anchors": anchors,
        "presets": preset_list,
        "activePreset": default_index,
        "labels": {
            "v_healthy": sc["v_healthy"],
            "v_cutoff": sc["v_cutoff"],
            "cutoff_note": sc["cutoff_note"],
            "cr_low": sc["cr_low"],
            "cr_high": sc["cr_high"],
            "enzyme": sensor_name,
            "enzyme_source": sensor.source_doi if sensor else None,
        },
        "_generated_from": "data/platform.csv, data/scenarios.csv (%s), "
                           "data/sensors.csv, data/web_presets.csv" % scenario,
    }


def render_block(config):
    return ('<script id="%s" type="application/json">\n%s\n</script>'
            % (CONFIG_ID, json.dumps(config, indent=2, sort_keys=True)))


def inject(html, config):
    """Replace the page's config block, or refuse if it is not there."""
    pattern = re.compile(
        r'<script id="%s" type="application/json">.*?</script>' % CONFIG_ID,
        re.S)
    if not pattern.search(html):
        raise SystemExit(
            'site.html has no <script id="%s"> block. The page must carry one '
            "for its constants to come from the data files; see the module "
            "docstring." % CONFIG_ID)
    return pattern.sub(lambda _: render_block(config), html, count=1)


def extract(html):
    """The config the given HTML currently carries, or None."""
    m = re.search(r'<script id="%s" type="application/json">(.*?)</script>'
                  % CONFIG_ID, html, re.S)
    return json.loads(m.group(1)) if m else None


def wrap(body, config):
    """Turn the page source into a standalone document."""
    m = re.search(r"<title>(.*?)</title>", body, re.S)
    title = m.group(1).strip() if m else "DAS Branch Simulator"
    body = body.replace(m.group(0), "", 1) if m else body

    links = re.findall(r'<link\b[^>]*>', body)
    for l in links:
        body = body.replace(l, "", 1)

    desc = ("Interactive two-compartment model of the DAS to H2O2 to OxyR to GFP "
            "biosensor: set the reagents and the culture and see whether a healthy "
            "urine sample can still be told apart from one at the "
            "colorectal-cancer cutoff.")

    head = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="color-scheme" content="light dark">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#129515;</text></svg>">
{links}
<style>
/* reset the Artifact runtime used to supply */
html{{color-scheme:light dark}}
body{{margin:0}}
img{{max-width:100%}}
[hidden]{{display:none!important}}
</style>
</head>
<body>
"""
    return (head.format(title=title, desc=desc, links="\n".join(links))
            + body.strip() + "\n</body>\n</html>\n")


def main(argv):
    sync = "--sync" in argv
    rest = [a for a in argv if not a.startswith("--")]
    out = rest[0] if rest else os.path.join(HERE, "index.html")

    config = build_config()
    source = open(SRC, encoding="utf-8").read()
    source = inject(source, config)

    if sync:
        open(SRC, "w", encoding="utf-8", newline="\n").write(source)
        print("synced the config block in", os.path.basename(SRC))

    html = wrap(source, config)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "w", encoding="utf-8", newline="\n").write(html)
    print("wrote %s (%.1f KB)" % (out, len(html.encode("utf-8")) / 1024))
    print("  Km   = %g uM   (%s)" % (config["P0"]["Km"], config["labels"]["enzyme"]))
    print("  kcat = %g /s" % config["P0"]["kcat"])
    print("  fold quoted as F(%g) / F(%g)"
          % (config["labels"]["v_cutoff"], config["labels"]["v_healthy"]))

    for need in ("<!DOCTYPE html>", "[hidden]{display:none!important}",
                 "fonts.googleapis.com", "<title>", "</body>", "</html>",
                 'id="%s"' % CONFIG_ID):
        assert need in html, "missing: " + need
    assert html.count("<style>") == 2, \
        "expected the reset block plus the page stylesheet"
    assert "<link" not in html.split("</head>")[1], \
        "a stylesheet link escaped into the body"
    assert extract(html) == config, "the injected config did not survive wrapping"
    print("checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
