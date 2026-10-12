# -*- coding: utf-8 -*-
"""Assemble index.html from the exported platform data.

Organised the way a dry-lab write-up is organised rather than the way a feature
page is: numbered sections, a figure sequence that runs the length of the
document, every equation followed by its symbols, every constant in a table that
says what fixed it, and numbered references that the prose points into.

The prose lives here, next to the numbers it frames, so a figure and the
sentence about it cannot drift apart. Nothing is computed in this file - every
quantity comes out of platform.json, which build_platform.py wrote.
"""
import re

import charts
import figures
import page_parts
from page_parts import Refs, eq, frac, kind_key, parameters_table, scenario_table
from render_page import (CSS, FONTS, JS, PALETTE, PALETTE_DARK, SKELETON_SVG, e,
                         enzymes_section, gaps_section, hero_strip,
                         library_table, limits_callout, mechanism_figure, num,
                         panels_section, pct, positioning_table,
                         positioning_legend, sig, stat_tiles)


def _dec(x, nd=3):
    """A plain decimal, for a quantity quoted beside AUCs given to three.

    num() gives three significant figures, which is right for a constant and
    wrong for a difference between two AUCs: 0.0313 next to 0.933 reads as a
    different kind of number."""
    return "\u2014" if x is None else (("%." + str(nd) + "f") % x)

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Biosensor module platform</title>
<meta name="description" content="A fixed plasmid skeleton, interchangeable recognition modules, and a model that decides which module is worth building. Screens a library of biomarkers against published clinical distributions and measured enzyme kinetics.">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#129516;</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="%s">
<style>:root{%s}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){%s}}
:root[data-theme="dark"]{%s}
%s</style>
</head>
<body>
<div class="shell">
%s
<main class="col">
"""

ROMAN = " "          # thin space


class Doc(object):
    """A numbered document: sections, subsections, figures, tables, citations.

    The contents rail is built from the headings as they are emitted, so it
    cannot list a section that is not there or miss one that is.
    """

    def __init__(self, d):
        self.d = d
        self.num = charts.Numbering()
        self.refs = Refs()
        self.nav = []
        self.out = []
        self.n1 = 0
        self.n2 = 0
        self.missing = []
        # Figure numbers are only known once the figure is emitted, and the
        # prose that points at one usually comes first. So a reference is
        # written as a token and resolved in body(); a token for a figure that
        # never got drawn resolves to its fallback wording rather than to a
        # dangling number.
        self.names = {}

    # ---- structure
    def section(self, anchor, title, sub=None):
        if self.n1:
            self.out.append("</section>")
        self.n1 += 1
        self.n2 = 0
        self.nav.append((1, str(self.n1), title, anchor))
        self.out.append(
            "<section id='%s'>\n<h2><span class='secno'>%d</span>%s</h2>"
            % (anchor, self.n1, e(title)))
        if sub:
            self.out.append("<p class='h2sub'>%s</p>" % sub)
        return self

    def sub(self, anchor, title, lead=None):
        self.n2 += 1
        label = "%d.%d" % (self.n1, self.n2)
        self.nav.append((2, label, title, anchor))
        self.out.append("<h3 id='%s'><span class='secno'>%s</span>%s</h3>"
                        % (anchor, label, e(title)))
        if lead:
            self.out.append("<p class='h3sub'>%s</p>" % lead)
        return self

    def p(self, html):
        self.out.append("<p>%s</p>" % html)
        return self

    def aside(self, html):
        self.out.append("<p class='aside'>%s</p>" % html)
        return self

    def raw(self, html):
        self.out.append(html)
        return self

    def flag(self, head, *paras):
        self.out.append("<aside class='flag'><span class='h'>%s</span>%s</aside>"
                        % (e(head), "".join("<p>%s</p>" % p for p in paras)))
        return self

    # ---- numbered figures and tables
    def figure(self, svg, caption, note=None, scroll=True, missing=None,
               name=None):
        """Number and caption a figure, or say what was missing instead."""
        if not svg:
            self.missing.append(missing or caption)
            if name:
                self.names[name] = None
            self.out.append("<p class='empty'>%s</p>"
                            % e(missing or "This figure could not be drawn from "
                                           "the data available."))
            return self
        self.out.append(self.num.figure(svg, caption, note=note, scroll=scroll))
        if name:
            self.names[name] = ("Figure", self.num.fig, "fig%d" % self.num.fig)
        return self

    def ref(self, name, fallback="below"):
        """A reference to a numbered figure or table, resolved in body()."""
        return "\x01" + name + "|" + fallback + "\x01"

    def adopt(self, html, caption_prefix=True):
        """Number a figure that already built its own caption."""
        if not html:
            return self
        self.out.append(self.num.adopt(html))
        return self

    def table(self, html, caption, missing=None, scroll=True, name=None):
        if not html:
            self.missing.append(missing or caption)
            if name:
                self.names[name] = None
            self.out.append("<p class='empty'>%s</p>"
                            % e(missing or "No rows to show."))
            return self
        self.out.append(self.num.table(html, caption, scroll=scroll))
        if name:
            self.names[name] = ("Table", self.num.tab, "tab%d" % self.num.tab)
        return self

    def cite(self, *dois):
        return self.refs.cite(*dois)

    # ---- output
    def rail(self):
        out = ["<nav class='rail' aria-label='Contents'>"
               "<p class='railhead'>Contents</p><ol>"]
        depth = 1
        for level, label, title, anchor in self.nav:
            if level == 2 and depth == 1:
                out.append("<ol>")
                depth = 2
            elif level == 1 and depth == 2:
                out.append("</ol>")
                depth = 1
            out.append("<li><a href='#%s' data-sec='%s'>"
                       "<span class='num'>%s</span>%s</a></li>"
                       % (anchor, anchor, e(label), e(title)))
        if depth == 2:
            out.append("</ol>")
        out.append("</ol></nav>")
        return "".join(out)

    def body(self):
        html = "\n".join(self.out + (["</section>"] if self.n1 else []))
        return re.sub("\x01([^|\x01]+)\\|([^\x01]*)\x01", self._resolve, html)

    def _resolve(self, m):
        got = self.names.get(m.group(1))
        if not got:
            return m.group(2)
        kind, number, anchor = got
        return ("<a class='xref' href='#%s'>%s&nbsp;%d</a>"
                % (anchor, kind, number))


# ----------------------------------------------------------------- the page

def _best(d):
    cands = [x for x in d["candidates"] if x.get("auc_device")]
    return max(cands, key=lambda x: x["auc_device"]) if cands else None


def _das_best(d):
    vals = [x["auc_device"] for x in d["candidates"]
            if x["biomarker"] == "DiAcSpm" and x.get("auc_device")]
    return max(vals) if vals else None


def page(d):
    t, a = d["thresholds"], d["anchors"]
    an = d.get("analysis") or {}
    best, das = _best(d), _das_best(d)
    doc = Doc(d)
    C = doc.cite

    SEAVER = next((r["source_doi"] for r in d.get("parameters", [])
                   if r["name"] == "P_endo" and r.get("source_doi")), None)
    ASLUND = next((r["source_doi"] for r in d.get("parameters", [])
                   if r["name"] == "K_oxyr" and r.get("source_doi")), None)

    # ------------------------------------------------------------ the header
    lede2 = ""
    if best:
        if best["biomarker"] != "DiAcSpm" and das:
            lede2 = (
                "<p class='lede'>The strongest module in the library is not the "
                "one this project started with. <b>%s</b>, read by <b>%s</b>, "
                "reaches AUC %s at the reader with sensitivity and specificity "
                "%s. Diacetylspermine reaches %s on the same scale, and only "
                "after the sample is concentrated.</p>"
                % (e(best["biomarker"]), e(best["protein"]),
                   num(best["auc_device"], 3), pct(best["sensitivity"]),
                   num(das, 3)))
        else:
            lede2 = ("<p class='lede'>Strongest module in the library: <b>%s</b> "
                     "read by <b>%s</b>, AUC %s at the reader.</p>"
                     % (e(best["biomarker"]), e(best["protein"]),
                        num(best["auc_device"], 3)))

    header = (
        "<header>\n<h1>A platform for biomarker detection,<br>not a sensor for "
        "one</h1>\n<p class='lede'>One plasmid skeleton that never changes "
        "- origin, resistance, reporter, and two fixed insertion sites. "
        "Between them sits a module that recognises one biomarker. Another "
        "biomarker, another module, same skeleton.</p>\n%s\n"
        "<p class='sub'>Colorectal cancer stays as the worked example, not as "
        "the project. Every figure and every number on this page is computed "
        "from %s and written into the markup at build time; the page itself "
        "calculates nothing.</p>\n</header>" % (lede2, e(d["generated_from"])))

    doc.figure(figures.library_map(d),
               "Every module in the library measured against every clinical "
               "study it could be measured against, grouped by biomarker. The "
               "passes are not spread thinly across the library: they sit on "
               "one analyte. Hover any mark for the pair behind it.",
               missing="No candidate pairs were screened.", name="map")
    doc.raw(stat_tiles(d))

    # ===================================================== 1. the platform
    doc.section("architecture", "The platform",
                "Two module types, because one is not enough")
    doc.sub("arch-skeleton", "One skeleton, two insertion sites")
    doc.p("Everything outside the two insertion sites is fixed: the origin, the "
          "resistance marker and the reporter never change between modules. "
          "That is the whole claim of the design - a second biomarker is "
          "a cloning job, not a redesign - and it is also the constraint "
          "that decides what counts as a module at all.")
    doc.figure(SKELETON_SVG,
               "The fixed skeleton and the two module types that plug into it. "
               "Type A converts the analyte to hydrogen peroxide and lets OxyR "
               "read it; type B binds the analyte with a transcription factor "
               "and drives the promoter directly. Both hand their signal to the "
               "same reporter, which is what makes them interchangeable.",
               scroll=False, name="skeleton")
    doc.sub("arch-why-two", "Why there are two module types")
    doc.aside("Type A exists for only a handful of analytes, because oxidases "
              "are scarce: of %d biomarkers in this library, %d have a "
              "published oxidase with both constants. Type B is the fallback "
              "where no oxidase exists, and having both is what makes this an "
              "architecture rather than one device. A sensor that carries its "
              "own fluorophore is a third thing and is left out on purpose "
              "- binding changes its fluorescence directly, with no "
              "transcription and no reporter gene, so it would replace the "
              "skeleton instead of plugging into it."
              % (len(d["biomarkers"]),
                 len({s["biomarker"] for s in d["sensors"]
                      if s["module_type"] == "A" and s["km_uM"] and s["kcat_s"]})))

    # ========================================================== 2. the model
    doc.section("model", "The model",
                "Two compartments, nothing fitted")
    doc.sub("model-objective", "What it has to answer")
    doc.p("The question is not whether the biomarker can make hydrogen "
          "peroxide - it can - but whether that peroxide is "
          "audible over the peroxide <i>E.&nbsp;coli</i> makes anyway. So the "
          "model is built around a competition between two fluxes, and the "
          "quantity it reports is a ratio between two samples rather than an "
          "absolute brightness.")
    doc.raw("<p class='aside'><b>Assumptions.</b> (1)&nbsp;The cytoplasm is "
            "quasi-steady on a millisecond timescale, so it follows the medium; "
            "the medium is integrated explicitly, because at low cell density "
            "it equilibrates over minutes. (2)&nbsp;Peroxide crosses the "
            "membrane as a single first-order exchange in both directions. "
            "(3)&nbsp;Scavenging is one first-order constant, which is adequate "
            "in the sub-micromolar range this design works in and is not "
            "adequate above it. (4)&nbsp;OxyR activation is instantaneous "
            "relative to transcription. (5)&nbsp;The reporter is diluted by "
            "growth and not degraded. (6)&nbsp;Both clinical cohorts are "
            "log-normal on the concentration scale, which "
            "section&nbsp;3.3 tests rather than assumes.</p>")

    doc.sub("model-compartments", "Peroxide in the two compartments")
    doc.raw(eq([
        "%s = P<sub>endo</sub> + v<sub>cyt</sub> + k<sub>mem</sub>&#8201;"
        "([H₂O₂]<sub>med</sub> − [H₂O₂]<sub>cyt</sub>) "
        "− k<sub>scav</sub>&#8201;[H₂O₂]<sub>cyt</sub>"
        % frac("d[H₂O₂]<sub>cyt</sub>", "dt"),
        "%s = v<sub>med</sub> + φ&#8201;k<sub>mem</sub>&#8201;"
        "([H₂O₂]<sub>cyt</sub> − [H₂O₂]<sub>med</sub>) "
        "− k<sub>chem</sub>&#8201;[H₂O₂]<sub>med</sub>"
        % frac("d[H₂O₂]<sub>med</sub>", "dt"),
    ], label="the two compartments", where=[
        ("[H₂O₂]<sub>cyt</sub>, [H₂O₂]<sub>med</sub>",
         "peroxide in the cytoplasm and in the medium, µM"),
        ("P<sub>endo</sub>",
         "the cell's own cytoplasmic peroxide production, µM/s - the "
         "competitor, and the denominator of the whole design"),
        ("v<sub>cyt</sub>, v<sub>med</sub>",
         "enzymatic production, in whichever compartment the oxidase sits"),
        ("k<sub>mem</sub>", "first-order exchange across the membrane, s⁻¹"),
        ("k<sub>scav</sub>",
         "intracellular scavenging by KatG, KatE and AhpCF, s⁻¹"),
        ("k<sub>chem</sub>",
         "chemical loss of peroxide in the medium, s⁻¹; zero unless "
         "the sample matrix contributes"),
        ("φ", "fraction of the assay volume that is cytoplasm"),
    ]))
    doc.p("The enzymatic term is Michaelis-Menten in the analyte, which "
          "is why a module's K<sub>m</sub> matters at all: it decides whether "
          "the branch is first order in the biomarker or already saturated.")
    doc.raw(eq("v = %s"
               % frac("k<sub>cat</sub>&#8201;[E]&#8201;[S]",
                      "K<sub>m</sub> + [S]"),
               label="production by the oxidase", where=[
        ("[S]", "analyte in the compartment the enzyme occupies, µM"),
        ("[E]", "enzyme concentration, µM"),
        ("k<sub>cat</sub>, K<sub>m</sub>",
         "the module's own published constants, from data/sensors.csv"),
    ]))

    doc.sub("model-oxyr", "The OxyR switch and the reporter")
    doc.raw(eq([
        "f<sub>OxyR</sub> = %s"
        % frac("[H₂O₂]<sub>cyt</sub><sup>n</sup>",
               "K<sup>n</sup> + [H₂O₂]<sub>cyt</sub><sup>n</sup>"),
        "%s = β&#8201;f<sub>OxyR</sub> + leak − (k<sub>mat</sub> + "
        "μ)&#8201;m" % frac("dm", "dt"),
        "%s = k<sub>mat</sub>&#8201;m − μ&#8201;g"
        % frac("dg", "dt"),
    ], label="activation, transcription, maturation", where=[
        ("f<sub>OxyR</sub>", "fraction of OxyR in its activated form"),
        ("K, n", "half-activation point and Hill coefficient of OxyR"),
        ("m, g", "immature and mature reporter, µM"),
        ("β, leak", "promoter output when fully activated, and at rest"),
        ("k<sub>mat</sub>", "reporter maturation rate, ln2 over its half-life"),
        ("μ", "growth rate; the reporter is diluted, not degraded"),
    ]))
    doc.p("A type B module skips the first two terms entirely. There is no "
          "oxidase and no peroxide: the analyte binds the transcription factor "
          "and the occupancy is what drives the promoter. Where the same "
          "protein is published as binding more than one analyte, all of them "
          "compete for the one site, so the readout is total occupancy rather "
          "than the target's share of it.")
    doc.raw(eq("θ = %s"
               % frac("∑<sub>i</sub> [A<sub>i</sub>]&#8201;/&#8201;"
                      "K<sub>d,i</sub>",
                      "1 + ∑<sub>i</sub> [A<sub>i</sub>]&#8201;/&#8201;"
                      "K<sub>d,i</sub>"),
               label="occupancy, module type B", where=[
        ("θ", "fraction of the binding site occupied, which replaces "
                   "f<sub>OxyR</sub> above"),
        ("[A<sub>i</sub>], K<sub>d,i</sub>",
         "each analyte this very protein is published as binding, with its own "
         "dissociation constant. Only analytes with a measured K<sub>d</sub> "
         "for this protein appear; nothing is assumed by analogy."),
    ]))
    doc.aside("The competitive sum is exact only at a Hill coefficient of 1, "
              "and the platform assumes 1 because no source reports a Hill "
              "coefficient for any sensor in the library. Where that matters "
              "for a verdict, the candidate's row says so.")

    doc.sub("model-params", "The constants, and what fixed each one")
    doc.p("The parameters over-determine the system, which is what makes it "
          "falsifiable rather than merely plausible. Three measurements in one "
          "paper%s fix the peroxide half of it: a production rate of %s "
          "&#181;M/s, a resting cytoplasmic level of %s &#181;M, which together "
          "force k<sub>scav</sub> &asymp; %s s&#8315;&#185;, and a membrane "
          "permeability that gives k<sub>mem</sub> &asymp; %s s&#8315;&#185;. "
          "OxyR's half-activation point comes from an in-vitro titration%s. "
          "The check is that these reproduce a quantity none of them was set "
          "from - the medium-to-cytoplasm gradient, which comes out at "
          "<code>%s&times;</code> against a measured value of about nine."
          % (C(SEAVER), num(a["P_endo"]), num(a["resting_h2o2"]),
             num(a["k_scav"]), num(a["k_mem"]), C(ASLUND),
             num(a["gradient"], 2)))
    doc.table(parameters_table(d, page_parts.PHYSICAL, doc.refs),
              "Every constant the model runs on, with what fixed it. Two are "
              "measurements, two are derived from those measurements, and eight "
              "are assumptions - which is the honest shape of this "
              "chassis and the reason section&nbsp;7 varies all of them.", name="constants")
    doc.raw(kind_key())
    doc.table(scenario_table(d),
              "The operating point. These are choices about how the assay is "
              "run, not properties of the biology, and the sensitivity analysis "
              "treats them separately for exactly that reason.")

    doc.sub("model-knockout", "Where OxyR sits before the sample arrives")
    doc.p("Resting cytoplasmic peroxide is P<sub>endo</sub>&#8201;/&#8201;"
          "k<sub>scav</sub>, so deleting the scavengers moves the strain along "
          "the activation curve rather than making it more sensitive. At the "
          "wild-type rate the reporter sits %s activated, leaving %s of its "
          "range for the analyte to use. In a catalase and peroxidase triple "
          "knockout it starts at %s, with %s left (%s)."
          % (pct(a["activation_wt"]), pct(a["headroom_wt"]),
             pct(a["activation_knockout"]), pct(a["headroom_knockout"]),
             doc.ref("oxyr", "see below")))
    doc.figure(figures.oxyr(d),
               "OxyR activation against resting cytoplasmic peroxide, with each "
               "strain's starting point marked. The knockout is not more "
               "sensitive but less: it begins the assay with the reporter "
               "almost fully on and nowhere left to go. This is the one result "
               "in the project that reverses a conclusion from the H₂O₂ "
               "biosensor literature, where scavenger-deficient strains are "
               "used to detect a bolus applied from outside against a "
               "background the experimenter controls.",
               missing="The OxyR curve needs the chassis constants, which are "
                       "absent from the exported data.", name="oxyr")
    doc.adopt(mechanism_figure(a))

    doc.sub("model-closedform", "What the closed form gets right, and what it does not")
    doc.p("An earlier draft of this project reduced the design to one "
          "expression for signal over background, and then turned it into "
          "advice. It is worth checking, because a closed form is only as good "
          "as the regime it was derived in.")
    doc.raw(eq("S/B &asymp; %s"
               % frac("S<sub>0</sub>",
                      "φ&#8201;P<sub>endo</sub>&#8201;T"),
               label="the closed form", where=[
        ("S<sub>0</sub>", "analyte delivered into the assay"),
        ("T", "read window, s"),
        ("S/B", "signal over the blank - not the fold between a healthy "
                "and a cancer sample, which is what every verdict on this page "
                "uses"),
    ]))
    doc.p("Read as exponents, it predicts that S/B falls as "
          "1&#8201;/&#8201;&#966;, as 1&#8201;/&#8201;P<sub>endo</sub> and as "
          "1&#8201;/&#8201;T, and that the scavenging rate cancels out "
          "entirely. Each of those is a number the full model can be asked for "
          "directly, by moving one parameter and measuring the slope (%s)."
          % doc.ref("scaling", "see below"))
    doc.figure(figures.scaling(d),
               "The exponent the closed form predicts against the exponent the "
               "full model actually obeys, measured as a central difference in "
               "log space with each parameter halved and doubled. A square is "
               "the prediction, a circle is the measurement, and the two "
               "scenarios are the screen's own operating point and the "
               "periplasmic diacetylspermine reference the expression was first "
               "derived for.",
               missing="The scaling check needs the model re-run, and no result "
                       "is present in the exported data.", name="scaling")

    scal = _scaling_verdict(an)
    if scal:
        doc.flag("a result that contradicts this project's own advice", *scal)

    doc.sub("model-window", "The pulse, and how long to wait")
    tc = an.get("time_course")
    if tc:
        doc.p("The read window only decides where the integration stops, so one "
              "run gives the fold every possible window would have delivered. "
              "At the %s&#8201;s this screen uses, the best module reaches "
              "%s&times;. It is still climbing there: the maximum is "
              "%s&times; at %s&#8201;s, which is %.1f&times; the configured "
              "window (%s)."
              % (num(tc["T_read"]), num(tc["fold_at_T"], 3),
                 num(tc["fold_peak"], 3), num(tc["t_peak"]),
                 tc["peak_over_T"], doc.ref("window", "see below")))
    doc.figure(figures.time_course(d),
               "Above: the peroxide pulse in the cytoplasm for a cancer "
               "sample, a healthy sample and a blank, against the OxyR "
               "half-activation point. Below: the fold between the two samples "
               "at every instant, which is the fold a read window ending there "
               "would report. The dotted line is the window this screen uses.",
               note="The fold rises while the analyte is being turned over and "
                    "falls once the pulse is spent and the reporter is "
                    "accumulating in both arms alike, which is why there is a "
                    "maximum at all.",
               missing="The time course needs a type A module with a clinical "
                       "level, and none is present in the exported data.", name="window")

    # ========================================================= 3. the screen
    doc.section("screen", "The screen",
                "Two gates, in order, and every rejection published")
    doc.sub("screen-gates", "Two gates")
    doc.p("<b>Stage&nbsp;1</b> asks whether the published cohorts separate at "
          "all - from the reported AUC where one exists, otherwise from "
          "Welch's t and Cohen's d rebuilt from the summary statistics. A "
          "biomarker that fails here is not worth a module however good the "
          "protein. <b>Stage&nbsp;2</b> asks whether a module could read that "
          "difference, and runs only on what survived. Rejections are listed "
          "with the stage that produced them: a screen that reports only its "
          "successes is not a screen.")
    doc.table(parameters_table(d, page_parts.RULES, doc.refs),
              "The decision rules. None of these is a measurement; they are "
              "where the screen draws its lines, and moving any of them moves "
              "which candidates pass.")

    doc.sub("screen-stage1", "Stage 1: do the cohorts separate")
    doc.p("%d published cohorts, %d of which report an effect size this "
          "pipeline can place on a common scale. The interval matters as much "
          "as the point: several of these studies are small enough that a "
          "large effect and no effect are both inside it (%s)."
          % (len(d["studies"]), len(an.get("effect_sizes") or []),
             doc.ref("forest", "see below")))
    doc.figure(figures.effect_sizes(d),
               "Effect size with its 95%% interval for every cohort that reports "
               "enough to compute one, grouped by biomarker and coloured by "
               "stage&nbsp;1 verdict. The shaded band is the effect too small "
               "for this screen to act on; a marker inside it may still be "
               "real, and is not something this platform can build on. %s"
               % _interval_note(an),
               missing="No cohort in clinical.csv reports an effect size this "
                       "pipeline can compute.", name="forest")

    doc.sub("screen-check", "Can the summary-statistics route be trusted")
    rec = an.get("reconstruction") or {}
    if rec.get("rows"):
        doc.p("Most of clinical.csv gives a mean, a spread and two group sizes "
              "and no ROC analysis, so the screen has to rebuild the "
              "separation on the assumption that each cohort is log-normal. "
              "%d studies report both their own AUC and enough statistics to "
              "rebuild it, which makes the assumption testable on them. The "
              "rebuilt value runs %s AUC points high on average, and %s at "
              "worst (%s)."
              % (rec["n"], _dec(abs(rec["mean_bias"])),
                 _dec(abs(rec["worst"])), doc.ref("recon", "see below")))
    doc.figure(figures.reconstruction(d),
               "The AUC this pipeline rebuilds from summary statistics against "
               "the AUC the same paper reports from its own ROC analysis. "
               "Points above the dashed line are cases where the pipeline is "
               "more optimistic than the study it came from.",
               note=_recon_note(rec),
               missing="No study reports both an AUC and a usable spread, so "
                       "the statistical route cannot be checked against "
                       "anything.", name="recon")
    if rec.get("rows"):
        doc.flag("what this means for every AUC on this page",
                 "The screen's separations are <b>upper bounds</b>, not "
                 "estimates. A log-normal fitted through a mean and a spread "
                 "has thinner tails than the cohorts actually have, and thin "
                 "tails flatter the classifier. Read every AUC below as "
                 "roughly %s too high, and the ranking between modules as more "
                 "trustworthy than the levels."
                 % _dec(abs(rec["mean_bias"]), 2))

    doc.sub("screen-positioning", "Where each module's constant falls")
    doc.p("A module reads a patient difference best when its Michaelis or "
          "dissociation constant sits inside the clinical range. The distance "
          "between the two predicts the verdict better than anything else in "
          "the screen (%s), and it is what sends most of %s to the rejected "
          "pile." % (doc.ref("positioning", "see below"),
                     doc.ref("library", "the screen table")))
    doc.figure(figures.positioning(d),
               "Each module's constant against the clinical range of its "
               "analyte. The diamond is the constant, the bar is the published "
               "healthy-to-cancer span. Sitting far below the constant is "
               "survivable - the branch is simply first order there "
               "- but it costs enzyme loading and signal; sitting far "
               "above means saturation, which no amount of sample preparation "
               "recovers.",
               note=positioning_legend(d["positioning"]), name="positioning")
    doc.raw(positioning_table(d["positioning"]))

    doc.sub("screen-library", "The library")
    doc.table(library_table(d), scroll=False, name="library", caption=
              "Every module against every clinical study it could be measured "
              "against: %d pairs, of which %d pass outright and %d pass once "
              "the sample is concentrated. Each row carries the reason for its "
              "verdict underneath it, and the %d rejections are one click away "
              "rather than deleted - they are the result, not the leftovers."
              % (len(d["candidates"]), d["counts"].get("green", 0),
                 d["counts"].get("yellow", 0), d["counts"].get("red", 0)))

    # ============================================== 4. fold to a diagnosis
    doc.section("performance", "From a fold change to a diagnosis",
                "A fold is not a test")
    doc.sub("perf-why", "Compression, and the noise underneath it")
    doc.p("Two things stand between a fold change and a diagnostic. The device "
          "does not report the analyte, it reports fluorescence, and the chain "
          "between them is sublinear - so the clinical difference arrives "
          "squeezed. The biological spread is squeezed by exactly the same "
          "factor, which is why the squeeze cannot be undone by rescaling "
          "afterwards. Underneath sits the reader's own error.")
    doc.raw(eq([
        "c = %s" % frac("ln&#8201;(device fold)", "ln&#8201;(clinical fold)"),
        "σ<sub>reader</sub> = CV&#8201;/&#8201;√n&nbsp;&nbsp;&nbsp;"
        "σ<sub>tot</sub> = √((c&#8201;σ<sub>bio</sub>)² + "
        "σ<sub>reader</sub>²)",
        "d = %s&nbsp;&nbsp;&nbsp;AUC = Φ(d&#8201;/&#8201;√2)"
        % frac("c&#8201;|ln&#8201;(cancer&#8201;/&#8201;healthy)|",
               "σ<sub>pooled</sub>"),
    ], label="propagation to sensitivity and specificity", where=[
        ("c", "the fraction of the log difference that survives to the reader, "
              "measured by running the module at both clinical levels"),
        ("σ<sub>bio</sub>",
         "the cohort's own spread on the log scale, from the published mean and "
         "spread"),
        ("CV, n",
         "the reader's relative error per measurement and the number of "
         "replicates - %s and %d here, giving a limit of detection of "
         "%s&times;" % (pct(t["cv_reader"]), int(t["n_rep"]),
                        num(t["fold_needed"], 4))),
        ("Φ", "the standard normal distribution function"),
    ]))
    doc.aside("Everything is done on the log scale, because concentrations of "
              "urinary metabolites are roughly log-normal and because a reader "
              "CV is multiplicative. At the cut-off where the two error rates "
              "are equal, sensitivity and specificity coincide; choosing a "
              "cut-off anywhere else trades one against the other.")

    doc.sub("perf-transfer", "The transfer function")
    dr = an.get("dose_response")
    if dr:
        doc.p("Holding the healthy arm at the study's own value and sweeping "
              "the other gives the module's whole response. The two clinical "
              "levels are %s and %s &#181;M; the chord between them has slope "
              "%s in log-log, and that slope <i>is</i> the compression the "
              "propagation above uses (%s)."
              % (num(dr["healthy_uM"], 3), num(dr["sick_uM"], 3),
                 num(dr["slope_chord"], 3),
                 doc.ref("transfer", "see below")))
    doc.figure(figures.dose_response(d),
               "The best module's reporter output against analyte "
               "concentration, relative to the healthy sample. The shaded band "
               "is the span between the two clinical medians, the dashed red "
               "line is the chord whose slope is the compression factor, and "
               "the horizontal line is the smallest fold the reader can "
               "resolve. Both axes are logarithmic, so a straight line is a "
               "power law.",
               missing="The transfer function needs a module with two clinical "
                       "levels, and none is present in the exported data.", name="transfer")

    doc.sub("perf-cohorts", "What the reader can tell apart")
    doc.figure(figures.distributions(d),
               "The two cohorts as the reader sees them, after the clinical "
               "spread has been compressed and the reader's own noise added. "
               "The shaded tails are the two ways of being wrong at the "
               "equal-error cut-off: healthy patients reading above it and "
               "cancer patients reading below. The overlap between the curves "
               "is what an AUC summarises in one number.",
               missing="No module has both a device fold and a published "
                       "spread, so no distribution can be drawn.", name="cohorts")
    doc.figure(figures.roc(d),
               "ROC curves before and after the device. The dashed curve is "
               "what the published cohorts separate on their own; the solid "
               "curve is what survives to the reader. These are binormal "
               "curves computed from two spreads and a separation, not fitted "
               "to patient-level data, because patient-level data is not what "
               "these papers publish.",
               missing="No module reaches the performance stage, so there is "
                       "no ROC curve to draw.", name="roc")
    doc.sub("perf-cost", "What the device costs, and what it cannot buy")
    doc.p(_compression_cancels(an)
          or "Not enough modules reach the performance stage to compare the "
             "clinic with the reader.")
    doc.figure(figures.auc_ladder(d),
               "The cohorts' own separation against the device's, module by "
               "module. The two markers nearly coincide, and that is the "
               "result: compression moves the signal and the spread together, "
               "so it cancels, and only the reader's noise is left to cost "
               "anything. c is the fraction of the log difference that "
               "survives to the reader.",
               missing="Fewer than two modules reach the performance stage.", name="ladder")

    # ============================================================= 5. panels
    doc.section("panels", "Panels",
                "One marker rarely gives usable specificity")
    doc.p("Urinary polyamines rise in colorectal cancer - and also in "
          "benign gastrointestinal disease, which is exactly what costs the "
          "published assays their specificity. Reading several modules at once "
          "is the way out, and against a fixed skeleton that is a cloning job "
          "rather than a redesign.")
    doc.raw(eq([
        "d<sub>panel</sub> = √(dᵀ R⁻¹ d)&nbsp;&nbsp;&nbsp;"
        "R = (1−ρ)&#8201;I + ρ&#8201;J",
        "d<sub>panel</sub>² = %s"
        % frac("∑ d<sub>i</sub>² − ρ&#8201;"
               "(∑ d<sub>i</sub>)² &#8201;/&#8201; "
               "(1 + (k−1)ρ)", "1 − ρ"),
    ], label="combining modules", where=[
        ("d<sub>i</sub>", "each module's separation at the reader"),
        ("R, ρ",
         "the correlation matrix of the markers in the same patient, assumed "
         "equal across every pair"),
        ("k", "how many modules are in the panel"),
    ]))
    doc.aside("How much a panel gains depends on how its markers co-vary, and "
              "that needs them measured in the same patients. Not one source in "
              "this library reports it. So each panel is given as a range over "
              "every correlation from 0 to %s, never as a single number, and "
              "the verdict is taken from the worst point of that range. "
              "Correlation is not simply bad, either: with unequal effect sizes "
              "the curve turns back up as &#961; approaches 1, because "
              "correlated markers that respond by different amounts let their "
              "difference cancel the shared variation. That gain is real "
              "statistics and worthless here, because it exists only if &#961; "
              "is known exactly." % num(t["rho_max"], 2))
    doc.figure(figures.panel_rho(d),
               "Panel AUC across every correlation its two markers could have. "
               "The verdict is read from the worst point, which for this pair "
               "is indistinguishable from the better marker on its own: at that "
               "correlation the weaker module contributes nothing. The upturn "
               "to the right is the suppressor effect, and it is not something "
               "to design around.",
               missing="No cancer has two modules that both clear the screen, "
                       "so there is no panel curve to draw.", name="panelrho")
    doc.table(panels_section(d),
              "Every panel the screen can form, with the range its unmeasured "
              "correlation allows and the verdict taken from the worst end.")

    # ======================================================== 6. the enzyme
    enz = enzymes_section(d)
    if enz:
        doc.section("enzymes", "Choosing the enzyme",
                    "Catalytic efficiency is not the lever it looks like")
        doc.figure(figures.enzyme_charts(d, "DiAcSpm"),
                   "Left: the oxidases published for diacetylspermine, against "
                   "the fold each one delivers. Right: every type A enzyme in "
                   "the library, against the loading each needs to turn over "
                   "95% of its analyte inside the read. The x axis is the same "
                   "on both. A better enzyme costs less enzyme - the "
                   "dashed line is the inverse proportionality it should follow "
                   "- and it does not produce more signal, because the "
                   "ceiling is the cell&rsquo;s own peroxide flux and no enzyme "
                   "moves that.",
                   missing="Fewer than two type A enzymes in the library have a "
                           "catalytic efficiency.", name="enzymes")
        doc.table(enz, "The published oxidases for each analyte that has more "
                       "than one, with the efficiency spread between them.")

    # =============================================== 7. sensitivity analysis
    doc.section("sensitivity", "Sensitivity analysis",
                "Which inputs the answer actually depends on")
    tor = an.get("tornado")
    if tor:
        doc.p("Every input halved and doubled in turn, with the whole chain "
              "re-run each time - fold, compression, propagation - "
              "so the bars are movements in the quantity the verdict rests on "
              "rather than in an intermediate. The baseline is AUC %s for %s "
              "read by %s."
              % (num(tor["base_auc"], 3), e(tor["biomarker"]),
                 e(tor["protein"])))
    doc.figure(figures.tornado(d),
               "One input at a time, each divided and multiplied by two, with "
               "the screen's AUC recomputed from scratch. Bars are coloured by "
               "who gets to choose the parameter, because that is what decides "
               "whether a sensitivity is a risk or an opportunity: the "
               "operator's choices can be optimised, the chassis constants are "
               "what they are, and the module's own kinetics are already "
               "measured.",
               note=_tornado_note(tor, t),
               missing="The sensitivity analysis needs a module that reaches "
                       "the performance stage.", name="tornado")
    if tor:
        doc.aside(_tornado_prose(tor))

    # ============================================================= 8. limits
    doc.section("gaps", "Honest limits",
                "What is missing, and what was left out deliberately")
    doc.raw(limits_callout(d))
    doc.raw(gaps_section(d))
    if rec.get("skipped"):
        doc.aside("%d studies report an AUC that this pipeline deliberately "
                  "does not rebuild. %s"
                  % (len(rec["skipped"]),
                     " ".join("<b>%s</b> (%s): %s.%s"
                              % (e(s["biomarker"]), e(s["cancer"] or "\u2014"),
                                 e(s["reason"]), doc.cite(s["doi"]))
                              for s in rec["skipped"])))
    doc.aside("The platform covers small molecules recognised by an oxidase or "
              "by a metabolite-binding transcription factor; protein markers do "
              "not fit it at all. Every module shares one ceiling on "
              "sensitivity, set by the host's own peroxide flux rather than by "
              "any module. And the worked example, with every parameter "
              "exposed, is <a href='simulator.html'>the diacetylspermine "
              "simulator</a>.")

    # ========================================================= 9. references
    doc.refs.collect(d)
    doc.section("references", "References",
                "Every number traces to one of these")
    doc.aside("Numbered in the order the text first points at them, then "
              "everything else the data files use. Each entry lists what it "
              "supplies. A constant with no source here does not have one: "
              "missing provenance is reported as missing, never filled in by "
              "analogy.")
    doc.raw(doc.refs.html())

    footer = (
        "<footer>\nBuilt from the data files; the page itself computes nothing. "
        "Scenario <code>%s</code>: %s enzyme, OD %s, %s sample by volume, %s s "
        "read, assumed urine creatinine %s g/L. Reader floor %s&times; at CV %s "
        "across %d replicates. %d figures and %d tables, all generated.\n"
        "</footer>"
        % (e(d["scenario"]["name"]), e(d["scenario"]["mode"]),
           num(d["scenario"]["OD"]), pct(d["scenario"]["sample_frac"]),
           num(d["scenario"]["T_read"]), num(d["scenario"]["creatinine"]),
           num(t["fold_needed"], 4), pct(t["cv_reader"]), int(t["n_rep"]),
           doc.num.fig, doc.num.tab))

    return (HEAD % (FONTS, PALETTE, PALETTE_DARK, PALETTE_DARK, CSS, doc.rail())
            + header + "\n" + doc.body() + "\n" + footer
            + "\n</main>\n</div>\n<script>%s</script>\n</body>\n</html>\n" % JS)


# ------------------------------------------------------------------ findings

def _scaling_verdict(an):
    """State which of the closed form's predictions the full model refutes."""
    sc = [s for s in (an.get("scaling") or []) if s.get("rows")]
    if not sc:
        return None
    broke, held = [], []
    for r in sc[0]["rows"]:
        others = [next((q for q in s["rows"] if q["param"] == r["param"]), None)
                  for s in sc[1:]]
        all_rows = [r] + [o for o in others if o]
        name = r["meaning"]
        got = ", ".join("%+.2f" % q["measured"] for q in all_rows)
        pred = ("%+.0f" % r["predicted"]) if r["predicted"] else "0"
        line = "%s (predicted %s, measured %s)" % (name, pred, got)
        (held if all(q["holds"] for q in all_rows) else broke).append(line)
    if not broke:
        return ["Every exponent the closed form predicts is confirmed by the "
                "full model: %s." % "; ".join(held)]
    # The counts are read off the result rather than written into the sentence.
    # They were hard-coded as "two and two" at first, and the figure beside the
    # sentence already said three.
    words = {1: "One", 2: "Two", 3: "Three", 4: "Four"}
    total = len(held) + len(broke)
    out = ["%s of the %s predictions %s and %s %s not. %sonfirmed: <b>%s</b>. "
           "Refuted: <b>%s</b>."
           % (words.get(len(held), str(len(held))),
              words.get(total, str(total)).lower(),
              "holds" if len(held) == 1 else "hold",
              words.get(len(broke), str(len(broke))).lower(),
              "does" if len(broke) == 1 else "do",
              "C" if held else "Nothing c",
              "; ".join(held) or "nothing", "; ".join(broke))]
    out.append(
        "Among the failures are the two this project turned into advice. An "
        "earlier write-up recommended running at a low cell density and "
        "reading early, on the strength of the &#966; and T terms above. "
        "Neither term survives contact with the full model: cell density "
        "barely moves signal over background at all, and read time moves it "
        "the other way. Section&nbsp;7 agrees independently - a longer "
        "read and a higher density both <i>raise</i> the screen's AUC. The "
        "recommendation to lower P<sub>endo</sub> by assaying non-growing "
        "cells is untouched by this, and remains the one lever the algebra and "
        "the model agree on.")
    return out


def _compression_cancels(an):
    """State the result the AUC comparison actually shows.

    The figure beside this was captioned as if the device gave something up at
    every module. It does not, and the reason is worth a paragraph: the
    compression factor multiplies the clinical difference and the clinical
    spread alike, so it cancels out of their ratio. Only the reader's own noise
    is left, added in quadrature to an already-squeezed spread.
    """
    sep = an.get("separation") or []
    rows = [s for s in sep if s.get("clinical") and s.get("device")]
    if len(rows) < 2:
        return None
    shares, gaps = [], []
    for s in rows:
        bio = s["device"]["compression"] * s["clinical"]["sd_healthy"]
        if bio > 0:
            shares.append(s["device"]["reader_log_sd"] / bio)
        gaps.append(abs(s["clinical"]["auc"] - s["device"]["auc"]))
    if not shares:
        return None
    return ("Compression is not the loss it looks like. It multiplies the "
            "clinical difference and the clinical spread by the same factor, "
            "so it cancels out of the ratio between them, and what the device "
            "actually adds is the reader's own noise alone. Across these "
            "modules that noise is %s to %s of the already-squeezed biological "
            "spread, and the AUC at the reader lands within <b>%s</b> of the "
            "cohorts' own. The consequence runs both ways: a module gives up "
            "almost nothing in translation, and it can never be better than "
            "the biomarker it reads. Everything that decides this screen was "
            "decided in the clinic, before any module existed."
            % (pct(min(shares)), pct(max(shares)), _dec(max(gaps))))


def _interval_note(an):
    """Say whether any point lacks an interval, instead of assuming one does."""
    rows = an.get("effect_sizes") or []
    bare = [r for r in rows if r.get("lo") is None]
    if not bare:
        return ("Every cohort drawn here reports both group sizes, so every "
                "point carries an interval.")
    return ("%d of these studies do not report their group sizes, so their "
            "points carry no interval \u2014 drawn that way on purpose, because "
            "a study whose precision cannot be known is not the same thing as "
            "a study with a wide one." % len(bare))


def _recon_note(rec):
    if not rec or not rec.get("rows"):
        return None
    return ("Mean disagreement %.3f AUC points, mean signed bias %+.3f, worst "
            "case %+.3f. %d further studies report an AUC but are not rebuilt "
            "here, each for a stated reason."
            % (rec["mean_abs"], rec["mean_bias"], rec["worst"],
               len(rec.get("skipped") or [])))


def _tornado_note(tor, t):
    if not tor:
        return None
    note = ("Baseline AUC %s, at a concentration factor of %s."
            % (num(tor["base_auc"], 3), num(tor["conc_factor"], 3)))
    if tor.get("skipped"):
        note += (" Not varied: %s, which this module's parameter set does not "
                 "contain." % ", ".join(tor["skipped"]))
    return note


def _tornado_prose(tor):
    rows = tor["rows"]
    top = rows[0]
    least = rows[-1]
    kin = [r for r in rows if r["chosen_by"] == "module"]
    out = ("The widest bar is <b>%s</b>, worth %s AUC points across a "
           "four-fold range, and the narrowest is <b>%s</b> at %s. "
           % (e(top["meaning"]), _dec(top["swing"]),
              e(least["meaning"]), _dec(least["swing"])))
    if kin:
        out += ("The module's own measured kinetics are at the bottom of the "
                "list: %s. That is the same conclusion the enzyme comparison "
                "reaches from the other direction - a hundred-fold spread "
                "in catalytic efficiency buys almost nothing, because the "
                "ceiling is the cell's own peroxide flux and no enzyme moves "
                "it. "
                % " and ".join("%s at %s" % (e(r["meaning"]), _dec(r["swing"]))
                               for r in kin))
    ko = next((r for r in rows if r["param"] == "k_scav"), None)
    if ko:
        out += ("Scavenging is worth %s here, which is the same result as "
                "section&nbsp;2.5 from a different angle: it moves the resting "
                "point on the OxyR curve, and the fold between two samples "
                "depends on where that point sits." % _dec(ko["swing"]))
    return out
