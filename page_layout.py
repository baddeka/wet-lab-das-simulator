# -*- coding: utf-8 -*-
"""Assemble index.html from the exported platform data.

Split from render_page.py only for file size; the two belong together. All the
prose that frames the numbers lives here, next to the numbers it frames, so a
figure and the sentence around it cannot drift apart.
"""
from render_page import (CSS, FONTS, JS, PALETTE, PALETTE_DARK, SKELETON_SVG, e,
                         enzymes_section, gaps_section, library_table, num,
                         panels_section, pct, positioning_chart,
                         positioning_legend, rail, references, stat_tiles,
                         hero_strip, limits_callout)

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


def _best(d):
    cands = [x for x in d["candidates"] if x.get("auc_device")]
    return max(cands, key=lambda x: x["auc_device"]) if cands else None


def _das_best(d):
    vals = [x["auc_device"] for x in d["candidates"]
            if x["biomarker"] == "DiAcSpm" and x.get("auc_device")]
    return max(vals) if vals else None


def page(d):
    t, a = d["thresholds"], d["anchors"]
    best, das = _best(d), _das_best(d)

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

    out = [HEAD % (FONTS, PALETTE, PALETTE_DARK, PALETTE_DARK, CSS, rail())]

    out.append(
        "<header>\n<h1>A platform for biomarker detection,<br>not a sensor for "
        "one</h1>\n<p class='lede'>One plasmid skeleton that never changes "
        "&mdash; origin, resistance, reporter, and two fixed insertion sites. "
        "Between them sits a module that recognises one biomarker. Another "
        "biomarker, another module, same skeleton.</p>\n%s\n"
        "<p class='sub'>Colorectal cancer stays as the worked example, not as "
        "the project. Every figure on this page is computed from %s and written "
        "into the markup at build time.</p>\n</header>" % (lede2, e(d["generated_from"])))

    out.append(hero_strip(d))
    out.append(stat_tiles(d))

    out.append(
        "<section id='architecture'>\n<h2>Architecture</h2>\n"
        "<p class='h2sub'>Two module types, because one is not enough</p>\n"
        "<div class='card'>%s</div>\n"
        "<p class='aside'>Type A exists for only a handful of analytes, because "
        "oxidases are scarce. Type B is what the platform falls back on where no "
        "oxidase is published, and having both is what makes this an "
        "architecture rather than one device. A sensor that carries its own "
        "fluorophore is a third thing, and is left out on purpose: it would "
        "replace the skeleton instead of plugging into it.</p>\n</section>"
        % SKELETON_SVG)

    out.append(
        "<section id='positioning'>\n<h2>Why most candidates fail</h2>\n"
        "<p class='h2sub'>Where each module&rsquo;s constant falls against its "
        "analyte</p>\n<p>A module reads a patient difference best when its "
        "Michaelis or dissociation constant sits inside the clinical range. The "
        "diamond is that constant, the bar is the published healthy-to-sick "
        "span, and the distance between them predicts the verdict better than "
        "anything else in the screen.</p>\n<div class='card'>%s</div>\n"
        "<p class='aside'>%s Sitting far below the constant is survivable "
        "&mdash; the branch is simply first order there &mdash; but it costs "
        "enzyme loading and signal. Sitting far above means saturation, which "
        "no amount of sample preparation recovers.</p>\n</section>"
        % (positioning_chart(d["positioning"]),
           positioning_legend(d["positioning"])))

    out.append(
        "<section id='library'>\n<h2>The screen</h2>\n"
        "<p class='h2sub'>Every module against every study</p>\n"
        "<p>Two gates, in order. <b>Stage&nbsp;1</b> asks whether the published "
        "cohorts separate at all &mdash; from the reported AUC where one exists, "
        "otherwise from Welch&rsquo;s t and Cohen&rsquo;s d rebuilt from the "
        "summary statistics. A biomarker that fails here is not worth a module "
        "however good the protein. <b>Stage&nbsp;2</b> asks whether a module "
        "could read that difference, and runs only on what survived. Rejections "
        "are listed with the stage that produced them: a screen that reports "
        "only its successes is not a screen.</p>\n%s\n</section>"
        % library_table(d))

    out.append(
        "<section id='panels'>\n<h2>Panels</h2>\n"
        "<p class='h2sub'>One marker rarely gives usable specificity</p>\n"
        "<p>Urinary polyamines rise in colorectal cancer &mdash; and also in "
        "benign gastrointestinal disease, which is exactly what costs the "
        "published assays their specificity. Reading several modules at once is "
        "the way out, and against a fixed skeleton that is a cloning job rather "
        "than a redesign.</p>\n"
        "<p class='aside'>How much a panel gains depends on how its markers "
        "co-vary, and that needs them measured in the same patients. Not one "
        "source in this library reports it. So each panel is given as a "
        "<b>range</b> over every correlation from 0 to %s, never as a single "
        "number, and the verdict is taken from the worst point of that range. "
        "Where the upper end comes from a suppressor effect &mdash; correlated "
        "markers cancelling shared variation &mdash; the row says so, because "
        "that gain needs the correlation known exactly and does not survive "
        "estimating it.</p>\n%s\n</section>"
        % (num(t["rho_max"], 2), panels_section(d)))

    enz = enzymes_section(d)
    if enz:
        out.append(
            "<section id='enzymes'>\n<h2>Swapping the enzyme</h2>\n"
            "<p class='h2sub'>Catalytic efficiency is not the lever it looks "
            "like</p>\n%s\n</section>" % enz)

    out.append(
        "<section id='model'>\n<h2>The model underneath</h2>\n"
        "<p class='h2sub'>Two compartments, nothing fitted</p>\n"
        "<p>Cytoplasm and medium are separate compartments exchanging "
        "H<sub>2</sub>O<sub>2</sub> at <code>k_mem &asymp; %s s&#8315;&#185;</code>. "
        "The cytoplasm is quasi-steady on a millisecond timescale; the medium is "
        "integrated explicitly, because at low cell density it equilibrates over "
        "minutes. Anchors: endogenous production <code>P_endo &asymp; %s "
        "&micro;M/s</code> and resting cytoplasmic <code>%s &micro;M</code>, "
        "which together force <code>k_scav &asymp; %s s&#8315;&#185;</code>; "
        "OxyR half-activation at <code>%s &micro;M</code>. The parameters "
        "over-determine the system, and the check is that they reproduce a "
        "quantity none of them was set from: the medium-to-cytoplasm peroxide "
        "gradient, which comes out at <code>%s&times;</code> against a measured "
        "value of about nine.</p>\n"
        "<p class='aside'>The competitor is a flux, not a threshold. "
        "<i>E.&nbsp;coli</i> makes peroxide continuously, so the question was "
        "never whether the biomarker trips OxyR but whether its trickle is "
        "audible over the cell&rsquo;s own. That is why fewer cells and a "
        "shorter read both help &mdash; and why deleting the scavengers does "
        "not: it lifts resting peroxide above the OxyR set point, and the "
        "reporter starts switched on with nowhere to go.</p>\n"
        "<p class='sub'>The worked example, with every parameter exposed: "
        "<a href='simulator.html'>the diacetylspermine simulator</a>.</p>\n"
        "</section>"
        % (num(a["k_mem"]), num(a["P_endo"]), num(a["resting_h2o2"]),
           num(a["k_scav"]), num(a["K_oxyr"]), num(a["gradient"], 2)))

    out.append(
        "<section id='gaps'>\n<h2>Honest limits</h2>\n"
        "<p class='h2sub'>What is missing, and what was left out deliberately</p>\n"
        "%s\n%s\n<p class='aside'>The platform covers small molecules recognised "
        "by an oxidase or by a metabolite-binding transcription factor; protein "
        "markers do not fit it at all. Every module shares one ceiling on "
        "sensitivity, set by the host&rsquo;s own peroxide flux rather than by "
        "any module.</p>\n</section>"
        % (limits_callout(d), gaps_section(d)))

    out.append(
        "<section id='references'>\n<h2>References</h2>\n"
        "<p class='h2sub'>Every number traces to one of these</p>\n"
        "<p class='aside'>Each entry lists what it supplies. A constant with no "
        "source here does not exist in the library: missing data is reported as "
        "missing, never filled in by analogy.</p>\n%s\n</section>" % references(d))

    out.append(
        "<footer>\nBuilt from the data files; the page itself computes nothing. "
        "Scenario <code>%s</code>: %s enzyme, OD %s, %s sample by volume, %s s "
        "read, assumed urine creatinine %s g/L. Reader floor %s&times; at CV %s "
        "across %d replicates.\n</footer>"
        % (e(d["scenario"]["name"]), e(d["scenario"]["mode"]),
           num(d["scenario"]["OD"]), pct(d["scenario"]["sample_frac"]),
           num(d["scenario"]["T_read"]), num(d["scenario"]["creatinine"]),
           num(t["fold_needed"], 4), pct(t["cv_reader"]), int(t["n_rep"])))

    return "".join(out) + "\n</div>\n<script>%s</script>\n</body>\n</html>\n" % JS
