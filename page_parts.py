# -*- coding: utf-8 -*-
"""The pieces a model write-up needs that a feature page does not.

Numbered references with citations that point into them, display equations with
their symbols defined underneath, and parameter tables that say for every
constant whether it was measured, derived, assumed or simply chosen.

That last column is the point of this module. A parameter table is the easiest
place in a dry-lab write-up to launder an assumption into a fact: put 90 s
inverse next to a unit and a tidy note and it reads as measured. Of the 31
constants this platform runs on, two are measured, two are derived from those,
eight are assumed and the rest are decisions. The table says so on every row.
"""
import io
import json
import os
import re

import equations
from render_page import e, num, sig

# Groups of data/platform.csv, in the order a reader meets them.
PHYSICAL = ["geometry", "h2o2", "oxyr", "reporter", "reader", "chemistry",
            "binding"]
RULES = ["threshold", "panel"]

GROUP_TITLE = {
    "geometry": "cell geometry",
    "h2o2": "peroxide in the two compartments",
    "oxyr": "the OxyR switch",
    "reporter": "transcription, maturation and dilution",
    "reader": "the measurement",
    "chemistry": "unit conversion",
    "binding": "ligand binding, module type B",
    "threshold": "thresholds the screen applies",
    "panel": "panel assumptions",
}

KIND_TITLE = {
    "measured": "a published measurement fixes this value",
    "derived": "computed from other published measurements, not fitted",
    "assumed": "a modelling assumption; no source in this project measures it",
    "chosen": "a decision of this screen, not a property of anything",
    "definition": "a definition, not a measurement",
}

# Symbols, where the parameter has one in the equations above it.
# Only where the symbol in the equations differs from the name in the file. A
# column that printed "leak leak" and "n_rep n_rep" was carrying no information
# at all.
SYMBOLS = {
    "phi_per_OD": "φ / OD", "k_scav_knockout": "k_scav (Hpx⁻)",
    "K_oxyr": "K", "n_hill": "n", "beta": "β", "cv_reader": "CV",
    "hill_n_binding": "n (binding)",
}


# ----------------------------------------------------------------- references

class Refs(object):
    """Numbered references, numbered in the order the page first cites them.

    Sorting by DOI instead would be easier and would put [1] somewhere in the
    middle of the page, which is not what a number next to a sentence is for.
    Anything in the data files that no sentence cites is still listed, after the
    cited ones: a source that went into a verdict has to be findable whether or
    not the prose happened to point at it.
    """

    def __init__(self):
        self.order = []
        self.index = {}
        self.uses = {}

    def _n(self, doi):
        if doi not in self.index:
            self.order.append(doi)
            self.index[doi] = len(self.order)
        return self.index[doi]

    def cite(self, *dois):
        """Superscript links, collapsed into one bracket."""
        got = [d for d in dois if d]
        if not got:
            return ""
        out = []
        for doi in got:
            n = self._n(doi)
            out.append("<a class='cite' href='#r%d' title='%s'>%d</a>"
                       % (n, e(doi), n))
        return "<span class='cites'>[%s]</span>" % ",".join(out)

    def note_use(self, doi, text):
        if doi:
            self.uses.setdefault(doi, set()).add(text)

    def collect(self, d):
        """Record what each source supplies, and list anything not yet cited."""
        for s in d["sensors"]:
            self.note_use(s["doi"], "module: %s (%s)"
                          % (s["protein"], s["biomarker"]))
        for s in d["studies"]:
            self.note_use(s["doi"], "clinical cohort: %s in %s"
                          % (s["biomarker"], s["cancer"] or "unstated"))
        for r in d["out_of_scope"]:
            self.note_use(r["source_doi"], "out of scope: %s" % r["protein_name"])
        for r in d.get("parameters", []):
            if r.get("source_doi"):
                self.note_use(r["source_doi"], "constant: %s" % r["name"])
        for doi in sorted(self.uses):
            self._n(doi)

    def html(self):
        out = ['<ol class="refs">']
        for doi in self.order:
            uses = "; ".join(sorted(self.uses.get(doi, ()))) or \
                   "cited in the text"
            href = doi if doi.startswith("http") else "https://doi.org/" + doi
            # One DOI in the library contains angle brackets, which are not
            # legal in a URI unencoded (RFC 3986). Encode them in the href and
            # leave the link text as the DOI was published.
            href = href.replace("<", "%3C").replace(">", "%3E")
            out.append('<li id="r%d"><a href="%s" rel="noreferrer">%s</a>'
                       '<span class="use">%s</span></li>'
                       % (self.index[doi], e(href), e(doi), e(uses)))
        out.append("</ol>")
        return "\n".join(out)


# ------------------------------------------------------------------ equations

_KATEX = None


def katex(name):
    """The rendered maths for one equation or symbol, from data/katex.json.

    Rendered by KaTeX at build time rather than in the browser, so the maths is
    in the markup: present with JavaScript off, present in print, and carrying
    the MathML KaTeX emits beside its visual output. A name with no entry stops
    the build instead of leaving a hole on the page.
    """
    global _KATEX
    if _KATEX is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "katex.json")
        with io.open(path, encoding="utf-8") as fh:
            _KATEX = json.load(fh)
    got = _KATEX.get(name)
    if not got:
        raise SystemExit("no rendered maths for %r. Run: python build_math.py"
                         % name)
    return got["html"]


def eq(name):
    """A display equation, with every symbol in it defined underneath.

    The 'where:' list is not decoration. An equation in a write-up is read by
    someone checking whether it is the equation they would have written, and
    they cannot do that without knowing which letter is which.
    """
    label, _tex, where = equations.EQUATIONS[name]
    out = ["<div class='eq'>"]
    if label:
        out.append("<span class='eqlab'>%s</span>" % e(label))
    out.append(katex(name))
    out.append("</div>")
    if where:
        out.append("<dl class='where'>")
        for i, (_sym, mean) in enumerate(where):
            out.append("<dt>%s</dt><dd>%s</dd>"
                       % (katex("%s.sym%d" % (name, i)), mean))
        out.append("</dl>")
    return "\n".join(out)


# ----------------------------------------------------------- parameter tables

def _value(row):
    """What the data file says, spelled out.

    This used to run every value through sig() at four figures, which turned a
    molar mass of 113.12 into 113.1: a table of constants losing a digit of the
    constant. The file's own text is authoritative, and only exponential
    notation is expanded, because 8e-4 is not a form a reader checks against a
    paper.
    """
    raw = (row.get("value") or "").strip()
    try:
        f = float(raw)
    except (TypeError, ValueError):
        return e(raw or "-")
    return sig(f, 4) if "e" in raw.lower() else e(raw)


def _unit(row):
    u = (row.get("units") or "").strip()
    if not u or u in ("dimensionless", "count", "fraction"):
        return "<span class='u'>%s</span>" % e(u or "-")
    return e(u.replace("uM", "µM").replace("1/s", "s⁻¹")
             .replace("um", "µm"))


def parameters_table(d, groups, refs, cls="params"):
    """Every constant in the given groups, with what fixed it."""
    rows = [r for r in d.get("parameters", []) if r.get("group") in groups]
    if not rows:
        return None
    out = ['<table class="%s"><thead><tr>'
           '<th>parameter</th><th class="n">value</th><th>unit</th>'
           '<th>what it is</th><th>how it was fixed</th>'
           '</tr></thead><tbody>' % cls]
    for g in groups:
        mine = [r for r in rows if r["group"] == g]
        if not mine:
            continue
        out.append('<tr class="grphead"><td colspan="5">%s</td></tr>'
                   % e(GROUP_TITLE.get(g, g)))
        for r in mine:
            kind = (r.get("source_kind") or "chosen").strip()
            prov = (r.get("source_note") or "").strip()
            cite = refs.cite(r.get("source_doi"))
            sym = SYMBOLS.get(r["name"])
            name = "<span class='nm'>%s</span>" % e(r["name"])
            if sym:
                name += " <span class='u'>%s</span>" % e(sym)
            # Both text columns are cut to one or two lines. The data file keeps
            # the full wording, and the title attribute carries it to anyone who
            # hovers; untruncated, these two columns alone ran the constants
            # table to two thousand pixels.
            out.append('<tr><td class="nm">%s</td><td class="n">%s</td>'
                       '<td class="u">%s</td>'
                       '<td class="pnote" title="%s">%s</td>'
                       '<td class="pnote" title="%s"><span class="kind %s" '
                       'title="%s">%s</span> %s%s</td></tr>'
                       % (name, _value(r), _unit(r),
                          e(_squash(r.get("note"))),
                          e(_short(r.get("note"), 112)),
                          e(_squash(prov)), e(kind),
                          e(KIND_TITLE.get(kind, "")), e(kind),
                          e(_short(prov, 180)), cite))
    out.append("</tbody></table>")
    return "\n".join(out)


def _squash(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def _short(text, limit=190):
    """Keep a note to one readable cell; the full text stays in the data file."""
    t = _squash(text)
    if len(t) <= limit:
        return t
    cut = t[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:.") + "…"


def scenario_table(d, cls="params"):
    """The operating point: what the screen was told to assume about the assay."""
    rows = d.get("scenario_rows") or []
    if not rows:
        return None
    out = ['<table class="%s"><thead><tr><th>setting</th><th class="n">value'
           '</th><th>unit</th><th>what it means</th></tr></thead><tbody>' % cls]
    for r in rows:
        if r.get("param") == "scenario":
            continue
        out.append('<tr><td class="nm">%s</td><td class="n">%s</td>'
                   '<td class="u">%s</td><td class="pnote">%s</td></tr>'
                   % (e(r.get("param")), _value(r), _unit(r),
                      e(_short(r.get("note")))))
    out.append("</tbody></table>")
    return "\n".join(out)


def kind_key():
    """What the four words in the provenance column mean."""
    out = ['<p class="fignote">']
    out.append(" &middot; ".join(
        "<span class='kind %s'>%s</span> %s" % (k, k, e(KIND_TITLE[k]))
        for k in ("measured", "derived", "assumed", "chosen")))
    out.append("</p>")
    return "".join(out)
