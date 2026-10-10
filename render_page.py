# -*- coding: utf-8 -*-
"""Turn platform.json into index.html, server-side.

Every number, every table row and the chart are written into the markup here,
at build time. The page is readable with JavaScript switched off; JS only adds
filtering and tooltips on top of markup that already says everything.

That is deliberate. The previous version of this site moved its constants into
JS-filled spans and then served a page whose entire Model section was blank
whenever the script did not finish. Rendering on the server removes the whole
class of failure: if a number is missing from the HTML, it is missing from the
data, and the page says so in words.
"""
import html
import math

PALETTE = """
  --sans: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --serif: "IBM Plex Serif", Georgia, "Times New Roman", serif;
  --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
  --surface-1: #fcfcfb;
  --plane: #f9f9f7;
  --ink-1: #0b0b0b;
  --ink-2: #52514e;
  --ink-3: #898781;
  --grid: #e1e0d9;
  --axis: #c3c2b7;
  --ring: rgba(11,11,11,.10);
  --series-a: #2a78d6;
  --series-b: #eb6834;
  --good: #0ca30c;
  --warning: #fab219;
  --critical: #d03b3b;
"""

PALETTE_DARK = """
  --surface-1: #1a1a19;
  --plane: #0d0d0d;
  --ink-1: #ffffff;
  --ink-2: #c3c2b7;
  --ink-3: #898781;
  --grid: #2c2c2a;
  --axis: #383835;
  --ring: rgba(255,255,255,.10);
  --series-a: #3987e5;
  --series-b: #d95926;
  --good: #0ca30c;
  --warning: #fab219;
  --critical: #d03b3b;
"""

LIGHT_WORD = {"green": "passes", "yellow": "needs concentration", "red": "fails"}
LIGHT_ICON = {"green": "●", "yellow": "◐", "red": "○"}


def e(x):
    return html.escape("" if x is None else str(x), quote=True)


def num(x, nd=3, dash="—"):
    if x is None:
        return dash
    if x == 0:
        return "0"
    a = abs(x)
    if a >= 1e4 or a < 1e-3:
        m = math.floor(math.log10(a))
        return "%.1f×10<sup>%d</sup>" % (x / 10 ** m, m)
    if a >= 100:
        return "%.0f" % x
    if a >= 10:
        return "%.1f" % x
    return ("%." + str(nd) + "g") % x


def pct(x, dash="—"):
    return dash if x is None else "%.0f%%" % (100 * x)


def chip(light):
    return ('<span class="chip %s"><span class="dot" aria-hidden="true">%s</span>%s</span>'
            % (light, LIGHT_ICON[light], LIGHT_WORD[light]))


# --------------------------------------------------------------- the chart
def positioning_chart(rows):
    """Log axis: each module's constant against its analyte's clinical range.

    One row per module. The bar is the published healthy-to-sick span, the
    diamond is Km or Kd. A module whose diamond sits inside its bar is reading
    the patient difference where it is most sensitive; one three decades away is
    not, and the picture says which is which faster than the table does.
    """
    if not rows:
        return "<p class='empty'>No module has both a constant and a convertible clinical range.</p>"

    vals = []
    for r in rows:
        vals += [r["anchor_uM"], r["healthy_uM"], r["sick_uM"]]
    lo = 10 ** math.floor(math.log10(min(vals)) - 0.25)
    hi = 10 ** math.ceil(math.log10(max(vals)) + 0.25)

    W, L, R = 820, 196, 112
    row_h, top, bot = 34, 34, 42
    H = top + row_h * len(rows) + bot
    plot = W - L - R

    def x(v):
        return L + plot * (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))

    out = ['<svg class="chart" viewBox="0 0 %d %d" role="img" '
           'aria-label="Module constant against clinical range, logarithmic axis">' % (W, H)]

    d = int(math.log10(lo))
    while 10 ** d <= hi:
        gx = x(10 ** d)
        out.append('<line class="grid" x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>'
                   % (gx, top - 12, gx, H - bot + 6))
        lab = "10<tspan dy='-5' font-size='9'>%d</tspan>" % d if d not in (0, 1, 2, 3) else \
              ("1" if d == 0 else "%d" % 10 ** d)
        out.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">%s</text>'
                   % (gx, H - bot + 20, lab))
        d += 1
    out.append('<text class="axis-title" x="%.1f" y="%d" text-anchor="middle">'
               'concentration, µM (log)</text>' % (L + plot / 2, H - 6))

    for i, r in enumerate(rows):
        y = top + row_h * i + row_h / 2
        col = "var(--series-a)" if r["module_type"] == "A" else "var(--series-b)"
        x0, x1 = x(r["healthy_uM"]), x(r["sick_uM"])
        if x1 - x0 < 3:
            x1 = x0 + 3
        # right-aligned against the axis, or a long protein name runs into
        # its own data bar
        out.append('<text class="rowlab" x="%d" y="%.1f" text-anchor="end">%s</text>'
                   % (L - 12, y + 4, e(r["protein"][:26])))
        out.append('<text class="rowsub" x="%d" y="%.1f" text-anchor="end">%s</text>'
                   % (L - 12, y - 7, e(r["biomarker"])))
        out.append('<rect class="range" x="%.1f" y="%.1f" width="%.1f" height="7" rx="3.5" '
                   'fill="%s"><title>%s: clinical %s to %s µM</title></rect>'
                   % (x0, y - 3.5, x1 - x0, col, e(r["biomarker"]),
                      num(r["healthy_uM"]), num(r["sick_uM"])))
        ax = x(r["anchor_uM"])
        out.append('<g class="anchor" transform="translate(%.1f,%.1f)">'
                   '<path d="M0,-7 L7,0 L0,7 L-7,0 Z" fill="var(--surface-1)" '
                   'stroke="%s" stroke-width="2"/><title>%s = %s µM</title></g>'
                   % (ax, y, col, r["anchor_name"], num(r["anchor_uM"])))
        ratio = r["ratio_to_anchor"]
        note = ("inside" if 0.1 <= ratio <= 10 else
                ("%s× below" % num(1 / ratio, 2) if ratio < 1 else
                 "%s× above" % num(ratio, 2)))
        out.append('<text class="rownote" x="%d" y="%.1f">%s</text>'
                   % (W - R + 6, y + 4, e(note)))

    out.append("</svg>")
    svg = "\n".join(out)

    # The same numbers as a table. Two jobs: the accessibility fallback the
    # chart needs, and the readable version on a phone, where the figure stops
    # shrinking and scrolls sideways instead.
    tab = ['<table class="posdata"><thead><tr><th>module</th><th>biomarker</th>'
           '<th class="n">constant</th><th class="n">clinical range</th>'
           '<th class="n">analyte / constant</th></tr></thead><tbody>']
    for r in rows:
        tab.append('<tr><td class="bm">%s</td><td>%s</td>'
                   '<td class="n">%s = %s <span class="u">µM</span></td>'
                   '<td class="n">%s – %s <span class="u">µM</span></td>'
                   '<td class="n">%s</td></tr>'
                   % (e(r["protein"]), e(r["biomarker"]), r["anchor_name"],
                      num(r["anchor_uM"]), num(r["healthy_uM"]),
                      num(r["sick_uM"]), num(r["ratio_to_anchor"], 2)))
    tab.append("</tbody></table>")

    return ('<div class="figscroll">%s</div>'
            '<p class="swipe">Swipe the chart sideways, or read the same '
            'numbers below.</p><div class="figscroll">%s</div>'
            % (svg, "".join(tab)))


SECTIONS = [("architecture", "Architecture"),
            ("positioning", "Why most fail"),
            ("library", "The screen"),
            ("panels", "Panels"),
            ("enzymes", "Swapping enzymes"),
            ("model", "The model"),
            ("gaps", "Honest limits"),
            ("references", "References")]


def rail():
    """Sticky contents. A 15000px page without one is not a design, it is a dump."""
    out = ['<nav class="rail" aria-label="Contents"><p class="railhead">Contents</p><ol>']
    for sid, label in SECTIONS:
        out.append('<li><a href="#%s" data-sec="%s">%s</a></li>' % (sid, sid, e(label)))
    out.append("</ol></nav>")
    return "".join(out)


def hero_strip(d):
    """One mark per candidate pair, in verdict order.

    The hero was pure type, and the page's hardest finding - that most of the
    library does not work - arrived only a thousand pixels later. This puts it
    under the opening paragraph, at the granularity of real pairs rather than a
    summary bar: 52 marks, each one a module measured against one study.
    """
    order = {"green": 0, "yellow": 1, "red": 2}
    cands = sorted(d["candidates"], key=lambda c: order[c["light"]])
    counts = d["counts"]
    n = len(cands)

    mw, gap, h = 11.0, 3.0, 26.0
    W = n * (mw + gap) - gap
    H = h + 30

    out = ['<svg class="strip" viewBox="0 0 %.0f %.0f" role="img" '
           'aria-label="%d candidate pairs: %d pass, %d pass with sample '
           'concentration, %d fail">'
           % (W, H, n, counts.get("green", 0), counts.get("yellow", 0),
              counts.get("red", 0))]

    x = 0.0
    spans = {}
    for c in cands:
        fill = {"green": "var(--good)", "yellow": "var(--warning)",
                "red": "var(--critical)"}[c["light"]]
        op = ".32" if c["light"] == "red" else "1"
        label = "%s / %s — %s" % (c["biomarker"], c["protein"], c["reason"])
        out.append('<rect x="%.1f" y="0" width="%.1f" height="%.0f" rx="2.5" '
                   'fill="%s" fill-opacity="%s"><title>%s</title></rect>'
                   % (x, mw, h, fill, op, e(label[:150])))
        s = spans.setdefault(c["light"], [x, x])
        s[1] = x + mw
        x += mw + gap

    # Place the group labels, dropping to a second row when two would collide.
    # The passing groups are only two and five marks wide, so at this scale
    # their labels are far wider than the bars they name.
    CHAR, ROW = 6.4, 16.0
    placed = []
    for light, text in (("green", "pass"), ("yellow", "with concentration"),
                        ("red", "fail")):
        if light not in spans:
            continue
        lo, hi = spans[light]
        label = "%d %s" % (counts.get(light, 0), text)
        wide = len(label) * CHAR
        # anchor on whichever end of the group is nearer its own side of the
        # strip, so a long run is labelled at its far edge rather than butting
        # against the group before it
        anchor = "start" if hi < W * 0.5 else "end"
        tx = lo if anchor == "start" else hi
        x0 = tx if anchor == "start" else tx - wide
        x1 = x0 + wide
        row = 0
        while any(row == r and not (x1 < a or x0 > b) for r, a, b in placed):
            row += 1
        placed.append((row, x0 - 6, x1 + 6))
        out.append('<text class="striplab" x="%.1f" y="%.1f" text-anchor="%s">'
                   '%s</text>' % (tx, h + 18 + row * ROW, anchor, e(label)))
    rows_used = max((r for r, _, _ in placed), default=0) + 1
    out[0] = out[0].replace('viewBox="0 0 %.0f %.0f"' % (W, H),
                            'viewBox="0 0 %.0f %.0f"' % (W, h + 14 + rows_used * ROW))
    out.append("</svg>")
    return ('<figure class="herofig"><div class="figscroll">%s</div>'
            '<p class="swipe">Swipe sideways to see the whole library.</p>'
            '<figcaption>Every module in the library measured against every '
            'clinical study it could be measured against. Each mark is one '
            'pair; hover for the verdict. The rejections are the result, not '
            'the leftovers.</figcaption></figure>' % "".join(out))


def light_key(counts):
    """The verdict split as a line of numbers, for a reader who jumped here.

    The hero strip already draws this at the granularity of individual pairs.
    Drawing the same proportions a second time would be decoration, so the
    section that details the pairs gets the count and nothing more.
    """
    order = [("green", "pass outright"), ("yellow", "pass with concentration"),
             ("red", "fail")]
    key = ['<span><span class="chip %s"><span class="dot" aria-hidden="true">%s'
           '</span></span><i>%d</i> %s</span>'
           % (light, LIGHT_ICON[light], counts.get(light, 0), e(label))
           for light, label in order]
    return '<div class="lightkey">%s</div>' % "".join(key)


def positioning_legend(rows):
    """Describe only the module types the chart actually draws.

    The first version of this legend named both types and both constants. No
    type B row has ever been drawn - the only type B protein in the library with
    a published Kd is BetI, and choline has no clinical distribution to plot it
    against - so a reader was sent hunting for a colour that is not on the page.
    The absence is itself the finding, so it gets said rather than papered over.
    """
    present = sorted({r["module_type"] for r in rows})
    if present == ["A"]:
        return ("Every constant plotted here is a K<sub>m</sub>: all of these are "
                "type A modules. <b>No type B module appears at all</b> &mdash; "
                "the only one in the library with a published K<sub>d</sub> is "
                "BetI, and choline has no clinical distribution to plot it "
                "against. That gap in the data, not the chemistry, is what "
                "currently limits the second module type.")
    if present == ["B"]:
        return ("Every constant plotted here is a K<sub>d</sub>: all of these are "
                "type B modules.")
    return ("The type A constant is K<sub>m</sub>, the type B constant is "
            "K<sub>d</sub>.")


# --------------------------------------------------------------- sections
def stat_tiles(d):
    """What the library is made of.

    The pair count moved out of here and into the hero strip, where it is drawn
    rather than asserted; these three carry the scope and the one threshold
    everything else is judged against.
    """
    t = d["thresholds"]
    tiles = [
        (len(d["sensors"]), "modules in the library",
         "across %d biomarkers, two module types, one skeleton"
         % len({s["biomarker"] for s in d["sensors"]})),
        (len(d["studies"]), "published clinical studies",
         "%d biomarkers, %d cancers, every one with a DOI"
         % (len(d["biomarkers"]), len(d["cancers"]))),
        ("%.3f×" % t["fold_needed"], "the reader floor",
         "the smallest fold a phone camera resolves at CV %s across %d "
         "replicates. Everything below this line is invisible however real it is."
         % (pct(t["cv_reader"]), int(t["n_rep"]))),
    ]
    out = ['<div class="tiles">']
    for value, label, sub in tiles:
        out.append('<div class="tile"><div class="tile-v">%s</div>'
                   '<div class="tile-k">%s</div><div class="tile-s">%s</div></div>'
                   % (value, e(label), e(sub)))
    out.append("</div>")
    return "\n".join(out)


def library_table(d):
    """The full matrix, with the rejections folded away by default.

    All 52 rows used to be open, and the table alone was about three quarters of
    the page - ten thousand pixels of mostly-identical rejections between the
    chart and the panels. The rejections stay (they are the result), but the
    seven rows that pass lead, and the rest sit one click away. With JavaScript
    off every row is visible, because the fold is applied by script.
    """
    rows = sorted(d["candidates"],
                  key=lambda c: ({"green": 0, "yellow": 1, "red": 2}[c["light"]],
                                 -(c.get("auc_device") or 0),
                                 c["biomarker"], c["protein"]))
    out = [light_key(d["counts"])]
    out.append('<div class="filters" data-js-only>')
    out += [
           '<label>Show <select id="f-light">'
           '<option value="">every verdict</option>'
           '<option value="green">passes only</option>'
           '<option value="yellow">needs concentration</option>'
           '<option value="red">fails only</option></select></label>',
           '<label>Biomarker <select id="f-bm"><option value="">all</option>'
           + "".join('<option>%s</option>' % e(b) for b in d["biomarkers"])
           + '</select></label>',
           '<span class="count" id="f-count"></span></div>']
    out.append('<div class="figscroll"><table class="lib"><thead><tr>'
               '<th>verdict</th><th>biomarker</th><th>module</th><th>type</th>'
               '<th>cancer / fluid</th><th class="n">clinical</th>'
               '<th class="n">device</th><th class="n">conc.</th>'
               '<th class="n">AUC</th><th class="n">sens=spec</th>'
               '<th>why</th></tr></thead><tbody>')
    for c in rows:
        ctx = (("%s / %s" % (c["cancer"], c["biofluid"]))
               if c["cancer"] else "no clinical row")
        out.append(
            '<tr data-light="%s" data-bm="%s">'
            '<td>%s</td><td class="bm">%s</td><td>%s<div class="org">%s</div></td>'
            '<td><span class="tt %s">%s</span></td><td class="ctx">%s</td>'
            '<td class="n">%s</td><td class="n">%s</td><td class="n">%s</td>'
            '<td class="n">%s</td><td class="n">%s</td><td class="why">%s</td></tr>'
            % (c["light"], e(c["biomarker"]), chip(c["light"]), e(c["biomarker"]),
               e(c["protein"]), e(c["organism"] or ""),
               c["module_type"], c["module_type"], e(ctx),
               (num(c["clinical_fold"], 3) + "×") if c["clinical_fold"] else "—",
               (num(c["device_fold"], 3) + "×") if c["device_fold"] else "—",
               (num(c["required_conc"], 2) + "×") if c["required_conc"] else "—",
               num(c.get("auc_device"), 3), pct(c.get("sensitivity")),
               e(c["reason"])))
    out.append("</tbody></table></div>")
    n_pass = sum(1 for c in rows if c["light"] != "red")
    out.append('<button class="more" id="f-more" data-js-only aria-expanded="false">Show the %d rejected pairs</button>'
               % (len(rows) - n_pass))
    return "\n".join(out)


def panels_section(d):
    if not d["panels"]:
        return "<p class='empty'>No cancer has two modules that both clear the screen.</p>"
    out = []
    for cancer, plist in sorted(d["panels"].items()):
        out.append('<h3>%s</h3>' % e(cancer))
        out.append('<div class="figscroll"><table class="panels"><thead><tr><th>panel</th>'
                   '<th class="n">AUC range</th><th class="n">sens=spec</th>'
                   '<th>verdict</th></tr></thead><tbody>')
        for p in plist:
            band = ("%s – %s" % (num(p["auc_worst"], 3), num(p["auc_best"], 3))
                    if p["size"] > 1 else num(p["auc_worst"], 3))
            sens = ("%s – %s" % (pct(p["sens_worst"]), pct(p["sens_best"]))
                    if p["size"] > 1 else pct(p["sens_worst"]))
            out.append('<tr class="v-%s"><td class="bm">%s</td><td class="n">%s</td>'
                       '<td class="n">%s</td><td class="why">%s</td></tr>'
                       % (p["verdict"], e(" + ".join(p["biomarkers"])), band, sens,
                          e(p["verdict_why"])))
        out.append("</tbody></table>")
    return "\n".join(out)


def enzymes_section(d):
    groups = {}
    for s in d["sensors"]:
        if s["module_type"] == "A" and s["efficiency"]:
            groups.setdefault(s["biomarker"], []).append(s)
    groups = {k: v for k, v in groups.items() if len(v) > 1}
    if not groups:
        return ""
    out = []
    for bm, items in sorted(groups.items()):
        items.sort(key=lambda s: -s["efficiency"])
        lo = items[-1]["efficiency"]
        out.append('<h3>%s</h3>' % e(bm))
        out.append('<div class="figscroll"><table class="enz"><thead><tr><th>enzyme</th><th>organism</th>'
                   '<th class="n">kcat <span class="u">s⁻¹</span></th><th class="n">Km <span class="u">µM</span></th>'
                   '<th class="n">kcat/Km <span class="u">µM⁻¹s⁻¹</span></th>'
                   '<th class="n">relative</th></tr>'
                   '</thead><tbody>')
        for s in items:
            out.append('<tr><td class="bm">%s</td><td>%s</td><td class="n">%s</td>'
                       '<td class="n">%s</td><td class="n">%s</td>'
                       '<td class="n">%s×</td></tr>'
                       % (e(s["protein"]), e(s["organism"] or "—"),
                          num(s["kcat_s"]), num(s["km_uM"]),
                          num(s["efficiency"], 3), num(s["efficiency"] / lo, 3)))
        out.append("</tbody></table></div>")
        spread = items[0]["efficiency"] / lo
        folds = [c["device_fold"] for c in d["candidates"]
                 if c["biomarker"] == bm and c["device_fold"]]
        if folds and spread > 1:
            out.append('<p class="aside">Catalytic efficiency spans %s× across '
                       'these enzymes; the device fold spans %s×. Below Km the '
                       'branch is first order in kcat/Km, so efficiency buys lower '
                       'enzyme loading, not signal — the ceiling is set by the '
                       'cell’s own peroxide flux, which no enzyme moves.</p>'
                       % (num(spread, 3), num(max(folds) / min(folds), 3)))
    return "\n".join(out)


def limits_callout(d):
    """The hardest sentence, set as the statement it is.

    This used to be the last line of a grey aside under two columns of lists,
    reading as a footnote. It is the most load-bearing claim on the page: a
    reader who takes nothing else away should take this.
    """
    n_pass = d["counts"].get("green", 0) + d["counts"].get("yellow", 0)
    return ('<aside class="callout"><p class="callout-lead">No module here has '
            'been validated experimentally.</p><p class="callout-body">This is a '
            'designed and modelled platform, not a working one. The %d pairs '
            'that clear both gates have cleared them <i>on paper</i>: against '
            'published kinetics, published cohorts and a model whose only '
            'external check is that it reproduces a peroxide gradient it was not '
            'fitted to. Nothing here has met a patient sample.</p></aside>'
            % n_pass)


def gaps_section(d):
    g = d["gaps"]
    out = ['<div class="cols">']
    out.append('<div><h3>Needed and missing</h3><ul class="gap">')
    for m in g["missing_constants"]:
        need = ", ".join(m["missing"])
        out.append('<li><b>%s</b> — %s (type %s) has no %s, so no response '
                   'can be computed. Not estimated from a similar protein.</li>'
                   % (e(m["biomarker"]), e(m["protein"]), m["module_type"], e(need)))
    for b in g["no_clinical"]:
        out.append('<li><b>%s</b> — a module exists but clinical.csv has no '
                   'usable distribution, so stage 1 cannot run.</li>' % e(b))
    for b in g["no_sensor"]:
        out.append('<li><b>%s</b> — clinical data exists but no module in the '
                   'library recognises it.</li>' % e(b))
    out.append("</ul></div>")

    out.append('<div><h3>Deliberately out of scope</h3>'
               '<p class="aside">These are real, published, well-characterised '
               'sensors. They are excluded because they carry their own '
               'fluorophore: binding changes their fluorescence directly, with no '
               'transcription and no reporter gene, so they replace the fixed '
               'skeleton instead of plugging into it. A different architecture, '
               'not a module.</p><ul class="gap">')
    for r in d["out_of_scope"]:
        out.append('<li><b>%s</b> — %s, Kd %s µM</li>'
                   % (e(r["protein_name"]), e(r["biomarker"]), e(r["kd_uM"])))
    out.append("</ul></div></div>")
    return "\n".join(out)


def references(d):
    refs = {}
    for s in d["sensors"]:
        if s["doi"]:
            refs.setdefault(s["doi"], set()).add("module: %s (%s)"
                                                 % (s["protein"], s["biomarker"]))
    for s in d["studies"]:
        if s["doi"]:
            refs.setdefault(s["doi"], set()).add(
                "clinical: %s in %s" % (s["biomarker"], s["cancer"] or "?"))
    for r in d["out_of_scope"]:
        if r["source_doi"]:
            refs.setdefault(r["source_doi"], set()).add(
                "out of scope: %s" % r["protein_name"])

    out = ['<ol class="refs">']
    for doi in sorted(refs):
        uses = "; ".join(sorted(refs[doi]))
        href = doi if doi.startswith("http") else "https://doi.org/" + doi
        # One DOI in the library contains angle brackets. They are not legal in
        # a URI unencoded (RFC 3986), so encode them in the href while the link
        # text keeps the DOI as published.
        href = href.replace("<", "%3C").replace(">", "%3E")
        out.append('<li><a href="%s" rel="noreferrer">%s</a><span class="use">%s</span></li>'
                   % (e(href), e(doi), e(uses)))
    out.append("</ol>")
    return "\n".join(out)


# --------------------------------------------------------------- the skeleton
SKELETON_SVG = """
<div class="figscroll">
<svg class="arch" viewBox="0 0 760 236" role="img"
     aria-label="A fixed plasmid skeleton with two insertion sites; a module of
                 either type sits between them and hands its signal to the
                 skeleton's reporter.">
  <circle cx="126" cy="108" r="66" fill="none" stroke="var(--axis)" stroke-width="12"/>
  <path d="M126 42 A66 66 0 0 1 182 74" fill="none" stroke="var(--series-a)"
        stroke-width="12" stroke-linecap="round"/>
  <text class="pl" x="126" y="104" text-anchor="middle">fixed</text>
  <text class="pl" x="126" y="122" text-anchor="middle">skeleton</text>
  <text class="ps" x="126" y="22" text-anchor="middle">ori · resistance · reporter</text>
  <circle cx="126" cy="42" r="6" fill="var(--surface-1)" stroke="var(--ink-2)" stroke-width="2"/>
  <circle cx="182" cy="74" r="6" fill="var(--surface-1)" stroke="var(--ink-2)" stroke-width="2"/>
  <text class="ps" x="126" y="196" text-anchor="middle">two fixed insertion sites</text>
  <text class="ps" x="126" y="210" text-anchor="middle">— everything else never changes</text>

  <line x1="206" y1="108" x2="262" y2="108" stroke="var(--axis)" stroke-width="2"/>
  <path d="M262 108 l-9 -4.5 v9 z" fill="var(--axis)"/>

  <rect x="276" y="26" width="456" height="80" rx="10" fill="none"
        stroke="var(--series-a)" stroke-width="2"/>
  <text class="mt" x="294" y="50" fill="var(--series-a)">type A</text>
  <text class="mb" x="294" y="74">analyte → oxidase → H₂O₂ → OxyR → promoter → GFP</text>
  <text class="ms" x="294" y="93">amplifies, and competes with the cell’s own peroxide</text>

  <rect x="276" y="122" width="456" height="80" rx="10" fill="none"
        stroke="var(--series-b)" stroke-width="2"/>
  <text class="mt" x="294" y="146" fill="var(--series-b)">type B</text>
  <text class="mb" x="294" y="170">analyte → transcription factor → promoter → GFP</text>
  <text class="ms" x="294" y="189">no peroxide stage; needed because oxidases are scarce</text>
</svg>
</div>
"""


from page_css import CSS, FONTS  # noqa: E402  (stylesheet lives next door)

JS = """
(function(){
  document.querySelectorAll('[data-js-only]').forEach(function(n){
    n.style.display = n.tagName === 'BUTTON' ? 'inline-block' : 'flex';
  });

  var rows = [].slice.call(document.querySelectorAll('table.lib tbody tr')),
      L = document.getElementById('f-light'), B = document.getElementById('f-bm'),
      C = document.getElementById('f-count'), M = document.getElementById('f-more'),
      open = false;

  function apply(){
    var l = L ? L.value : '', b = B ? B.value : '', n = 0, hidden = 0;
    rows.forEach(function(r){
      var match = (!l || r.dataset.light === l) && (!b || r.dataset.bm === b);
      // the fold only applies when no filter is asking for the rejections
      var folded = !open && !l && r.dataset.light === 'red';
      if (match && folded) hidden++;
      r.classList.toggle('hid', !match || folded);
      if (match && !folded) n++;
    });
    if (C) C.textContent = n + ' shown';
    if (M) {
      M.hidden = hidden === 0 && !open;
      M.textContent = open ? 'Hide the rejected pairs'
                           : 'Show the ' + hidden + ' rejected pairs';
      M.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
  }
  if (L) L.addEventListener('change', function(){ open = !!L.value; apply(); });
  if (B) B.addEventListener('change', apply);
  if (M) M.addEventListener('click', function(){ open = !open; apply(); });
  apply();

  // mark the section the reader is in
  var links = [].slice.call(document.querySelectorAll('.rail a')),
      secs = links.map(function(a){ return document.getElementById(a.dataset.sec); });
  function spy(){
    var y = window.scrollY + 120, cur = 0;
    secs.forEach(function(s, i){ if (s && s.offsetTop <= y) cur = i; });
    links.forEach(function(a, i){ a.classList.toggle('on', i === cur); });
  }
  if (links.length) {
    addEventListener('scroll', spy, {passive:true});
    addEventListener('resize', spy);
    spy();
  }
})();
"""
