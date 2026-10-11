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
import re

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
  --series-c: #1a9e76;
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
  --series-c: #21a97f;
  --good: #0ca30c;
  --warning: #fab219;
  --critical: #d03b3b;
"""


LEAK = re.compile(
    # a Python value that reached the markup: a bare text node, an attribute
    # value, or a number slot followed by its unit or multiplier
    r">(?:None|nan|NaN|undefined)<"
    r"|=['\"](?:None|nan|NaN|undefined)['\"]"
    r"|(?:None|nan|NaN|undefined)\s*(?:&times;|×|&#181;M|µM|s&#8315;| ?s⁻)"
    r"|\((?:None|nan|NaN|undefined)\)"
    r"|%[sdfgr]|\{\}")


def leaks(html):
    """Snippets where a Python value or an unfilled format slot reached the page.

    The first version of this check was `" None " not in html`, which is too
    blunt: it fails on the English word in a caption while still missing
    stroke-dasharray='None'. A leak is a value in a value position, so that is
    what is matched.
    """
    return [html[max(0, m.start() - 40):m.end() + 40]
            for m in LEAK.finditer(html)]

LIGHT_WORD = {"green": "passes", "yellow": "needs concentration", "red": "fails"}
LIGHT_ICON = {"green": "●", "yellow": "◐", "red": "○"}


def e(x):
    return html.escape("" if x is None else str(x), quote=True)


# The reader never sees a CSV column name. These are the only names for the
# constants that appear on the page.
FIELD = {"km_uM": "a Michaelis constant", "kcat_s": "a turnover number",
         "kd_uM": "a dissociation constant"}
SYMBOL = {"km_uM": "Km", "kcat_s": "kcat", "kd_uM": "Kd"}

THIN = " "  # narrow no-break space, for grouping digits


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
        return "%.0f" % x if float(x).is_integer() else "%.1f" % x
    return ("%." + str(nd) + "g") % x


def sig(x, n=3, dash="—"):
    """A concentration, to a fixed number of significant figures.

    One rule for a whole column, so 0.0744 and 0.17 do not sit next to each
    other at different precisions, and 17000 does not become 1.7x10^4 while the
    cell above it stays decimal. Digits are grouped rather than exponentiated:
    a reader comparing 8.2 against 17 000 should not have to parse two
    notations to do it.
    """
    if x is None:
        return dash
    if x == 0:
        return "0"
    a = abs(x)
    digits = max(0, n - 1 - int(math.floor(math.log10(a))))
    s = "%.*f" % (digits, x)
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    whole, _, frac = s.partition(".")
    if len(whole.lstrip("-")) > 4:
        sign = "-" if whole.startswith("-") else ""
        body = whole.lstrip("-")
        groups = []
        while len(body) > 3:
            groups.insert(0, body[-3:])
            body = body[:-3]
        groups.insert(0, body)
        whole = sign + THIN.join(groups)
    return whole + ("." + frac if frac else "")


def fold(x, dash="—"):
    """A fold change. Always two decimals and a multiplication sign."""
    return dash if x is None else "%.2f×" % x


def position_word(ratio):
    """Where the analyte sits relative to the constant, in words.

    The bare ratio runs from 0.34 down to 0.00055, which forces a column to mix
    decimal and scientific notation and tells the reader nothing either way.
    This is the same phrasing the chart uses.
    """
    if ratio is None:
        return "—"
    if 0.1 <= ratio <= 10:
        return "inside the range"
    # two significant figures, not two decimals: "1800x below" is the true
    # precision of a ratio built from a published median, "1818.18x" is not
    if ratio < 1:
        return "%s× below" % sig(1.0 / ratio, 2)
    return "%s× above" % sig(ratio, 2)


def pct(x, dash="—"):
    return dash if x is None else "%.0f%%" % (100 * x)


LIGHT_SHORT = {"green": "pass", "yellow": "conc.", "red": "fail"}

# "Urine (morning spot; total after hydrolysis)" wrapped to four lines in a
# table cell. The preparation still matters, so it is kept, just not spelled
# out at full length in a column forty pixels wide.
FLUID_SHORT = [
    ("morning spot; total after hydrolysis", "urine, total"),
    ("morning spot; free", "urine, free"),
    ("spot preoperative", "urine, pre-op"),
    ("supernatant after DRE", "urine, supernatant"),
    ("sediment after DRE", "urine, sediment"),
    ("pre-biopsy no DRE", "urine, pre-biopsy"),
    ("serum; total after hydrolysis", "serum, total"),
    ("morning spot", "urine, spot"),
    ("24-h", "urine, 24 h"),
]


def _fluid_short(biofluid):
    if not biofluid:
        return "—"
    for long, short in FLUID_SHORT:
        if long in biofluid:
            return short
    return biofluid.split("(")[0].strip().lower()


def chip(light, short=False):
    words = LIGHT_SHORT if short else LIGHT_WORD
    return ('<span class="chip %s" title="%s"><span class="dot" '
            'aria-hidden="true">%s</span>%s</span>'
            % (light, LIGHT_WORD[light], LIGHT_ICON[light], words[light]))


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

    out = ['<svg class="chart" style="max-width:%dpx" viewBox="0 0 %d %d" '
           'role="img" aria-label="Module constant against clinical range, '
           'logarithmic axis">' % (W, W, H)]

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
    anchors = sorted({r["anchor_name"] for r in rows})
    head = " / ".join(anchors) if len(anchors) > 1 else anchors[0]
    tab = ['<table class="posdata"><thead><tr><th>module</th><th>biomarker</th>'
           '<th class="n">%s<span class="u">, µM</span></th>'
           '<th class="n">clinical range<span class="u">, µM</span></th>'
           '<th>analyte sits</th></tr></thead><tbody>' % head]
    for r in rows:
        tab.append('<tr><td class="bm">%s</td><td>%s</td>'
                   '<td class="n">%s</td><td class="n">%s–%s</td>'
                   '<td class="pos">%s</td></tr>'
                   % (e(r["protein"]), e(r["biomarker"]),
                      sig(r["anchor_uM"]),
                      sig(r["healthy_uM"]), sig(r["sick_uM"]),
                      position_word(r["ratio_to_anchor"])))
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


def _logx(v, lo, hi, x0, w):
    return x0 + w * (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))


def mechanism_figure(a):
    """Why knocking out the scavengers makes it worse.

    The least intuitive result the model produces, and it was three sentences of
    prose. Two panels: the peroxide pool with both its inputs, and the OxyR
    curve with each strain's resting point on it. The knockout does not remove a
    competitor, it removes a drain - and the reporter then starts the assay with
    almost no headroom left.
    """
    W, H = 780, 268
    out = ['<svg class="mech" viewBox="0 0 %d %d" role="img" aria-label="The '
           'cytoplasmic peroxide pool has two inputs and one drain; removing '
           'the drain raises the resting level from %s to %s uM, above the OxyR '
           'half-activation point of %s uM."'
           '>' % (W, H, num(a["resting_h2o2"]), num(a["resting_knockout"]),
                  num(a["K_oxyr"]))]

    # ---- panel A: the pool ------------------------------------------------
    out.append('<text class="panlab" x="0" y="12">The pool</text>')
    px, py, pw, ph = 118, 74, 128, 74
    out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="10" '
               'fill="none" stroke="var(--axis)" stroke-width="2"/>'
               % (px, py, pw, ph))
    out.append('<text class="poolt" x="%d" y="%d" text-anchor="middle">'
               'cytoplasmic</text>' % (px + pw / 2, py + 30))
    out.append('<text class="poolt" x="%d" y="%d" text-anchor="middle">'
               'H₂O₂</text>' % (px + pw / 2, py + 50))

    # the analyte's contribution: thin
    out.append('<path d="M8 %d H%d" stroke="var(--series-a)" stroke-width="2" '
               'fill="none"/>' % (py + 16, px - 8))
    out.append('<path d="M%d %d l-7 -4 v8 z" fill="var(--series-a)"/>' % (px, py + 16))
    out.append('<text class="flow" x="8" y="%d" fill="var(--series-a)">'
               'from the biomarker</text>' % (py + 6))

    # the cell's own: thick
    out.append('<path d="M8 %d H%d" stroke="var(--ink-3)" stroke-width="9" '
               'fill="none" opacity=".45"/>' % (py + 54, px - 10))
    out.append('<path d="M%d %d l-10 -7 v14 z" fill="var(--ink-3)" opacity=".45"/>'
               % (px, py + 54))
    out.append('<text class="flow" x="8" y="%d">the cell’s own,</text>'
               % (py + 74,))
    out.append('<text class="flow" x="8" y="%d">P_endo %s µM/s</text>'
               % (py + 88, num(a["P_endo"])))

    # the drain
    out.append('<path d="M%d %d V%d" stroke="var(--ink-3)" stroke-width="6" '
               'opacity=".45" fill="none"/>' % (px + pw / 2, py + ph, py + ph + 26))
    out.append('<path d="M%d %d l-7 -10 h14 z" fill="var(--ink-3)" opacity=".45"/>'
               % (px + pw / 2, py + ph + 32))
    out.append('<text class="flow" x="%d" y="%d" text-anchor="middle">'
               'scavengers, k_scav %s s⁻¹</text>'
               % (px + pw / 2, py + ph + 50, num(a["k_scav"])))
    out.append('<text class="flow" x="%d" y="%d">→ OxyR</text>'
               % (px + pw + 12, py + ph / 2 + 4))

    # ---- panel B: the OxyR curve -----------------------------------------
    bx, by, bw, bh = 380, 40, 356, 150
    lo, hi = 0.002, 60.0
    out.append('<text class="panlab" x="%d" y="12">What OxyR does with it</text>' % bx)
    for frac, lab in ((0.0, "off"), (0.5, "half"), (1.0, "full")):
        y = by + bh - bh * frac
        out.append('<line class="grid" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>'
                   % (bx, y, bx + bw, y))
        out.append('<text class="tick" x="%d" y="%.1f" text-anchor="end">%s</text>'
                   % (bx - 8, y + 4, lab))

    d = int(math.floor(math.log10(lo)))
    while 10 ** d <= hi:
        gx = _logx(10 ** d, lo, hi, bx, bw)
        if bx <= gx <= bx + bw:
            out.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">'
                       '%s</text>' % (gx, by + bh + 18,
                                      "1" if d == 0 else "10<tspan dy='-4' "
                                      "font-size='8'>%d</tspan>" % d))
        d += 1
    out.append('<text class="axis-title" x="%.1f" y="%d" text-anchor="middle">'
               'resting cytoplasmic H₂O₂, µM</text>'
               % (bx + bw / 2, by + bh + 38))

    k, n = a["K_oxyr"], a["n_hill"] or 1.0
    pts = []
    for i in range(121):
        v = lo * (hi / lo) ** (i / 120.0)
        f = v ** n / (k ** n + v ** n)
        pts.append("%.1f,%.1f" % (_logx(v, lo, hi, bx, bw), by + bh - bh * f))
    out.append('<polyline class="curve" points="%s"/>' % " ".join(pts))

    kx = _logx(k, lo, hi, bx, bw)
    out.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="var(--axis)" '
               'stroke-dasharray="3 3"/>' % (kx, by, kx, by + bh))
    out.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">K_oxyr</text>'
               % (kx, by - 6))

    for key, act, col, lab in (
            ("resting_h2o2", "activation_wt", "var(--good)", "wild type"),
            ("resting_knockout", "activation_knockout", "var(--critical)", "Hpx⁻")):
        vx = _logx(a[key], lo, hi, bx, bw)
        vy = by + bh - bh * a[act]
        out.append('<circle cx="%.1f" cy="%.1f" r="5.5" fill="%s" '
                   'stroke="var(--surface-1)" stroke-width="2"><title>%s: resting '
                   '%s uM, OxyR %s activated</title></circle>'
                   % (vx, vy, col, lab, num(a[key]), pct(a[act])))
        anchor = "start" if a[key] < k else "end"
        dx = 10 if anchor == "start" else -10
        out.append('<text class="ptlab" x="%.1f" y="%.1f" text-anchor="%s" '
                   'fill="%s">%s</text>' % (vx + dx, vy + 4, anchor, col, e(lab)))
        out.append('<text class="ptsub" x="%.1f" y="%.1f" text-anchor="%s">'
                   '%s activated, %s headroom</text>'
                   % (vx + dx, vy + 19, anchor, pct(a[act]),
                      pct(a["headroom_wt" if key == "resting_h2o2"
                            else "headroom_knockout"])))
    out.append("</svg>")
    return ('<figure class="mechfig"><div class="figscroll">%s</div>'
            '<figcaption>Deleting the catalases and peroxidases does not remove '
            'a competitor for the signal — it removes the drain. Resting '
            'peroxide climbs from %s to %s µM, past the OxyR half-activation '
            'point, and the reporter begins the assay already %s switched on '
            'with %s of its range left. That is why the knockout makes the fold '
            'worse rather than better.</figcaption></figure>'
            % ("".join(out), num(a["resting_h2o2"]), num(a["resting_knockout"]),
               pct(a["activation_knockout"]), pct(a["headroom_knockout"])))


def enzyme_charts(d, biomarker):
    """Efficiency against what it buys, on one shared x axis.

    The section's conclusion - that two orders of catalytic efficiency buy
    enzyme loading and not signal - used to sit in a sentence under a table.
    Two panels over the same log axis make the argument directly: the fold is
    flat across the whole range, the loading falls as 1/x down it.

    The left panel is restricted to one biomarker, because comparing folds
    across analytes would compare clinical ranges rather than enzymes. The
    right panel takes every type A enzyme in the library, since the minimum
    loading depends only on kcat/Km and the read time.
    """
    rows = d.get("enzyme_loading") or []
    same = [r for r in rows if r["biomarker"] == biomarker and r["device_fold"]]
    loads = [r for r in rows if r["min_enzyme_uM"]]
    if len(same) < 2 or len(loads) < 2:
        return ""

    W, H = 780, 272
    pw, ph, top = 320, 150, 42
    ax, bx = 54, 440
    effs = [r["efficiency"] for r in rows]
    lo = 10 ** math.floor(math.log10(min(effs)))
    hi = 10 ** math.ceil(math.log10(max(effs)))

    out = ['<svg class="enzfig" viewBox="0 0 %d %d" role="img" aria-label="'
           'Catalytic efficiency against the fold it delivers and the enzyme '
           'loading it requires">' % (W, H)]

    def xaxis(x0, label):
        dd = int(math.log10(lo))
        while 10 ** dd <= hi:
            gx = _logx(10 ** dd, lo, hi, x0, pw)
            out.append('<line class="grid" x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>'
                       % (gx, top, gx, top + ph))
            out.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">'
                       '10<tspan dy="-4" font-size="8">%d</tspan></text>'
                       % (gx, top + ph + 17, dd))
            dd += 1
        out.append('<text class="axis-title" x="%.1f" y="%d" text-anchor="middle">'
                   '%s</text>' % (x0 + pw / 2, top + ph + 38, label))

    # ---- left: the fold, within one biomarker ----------------------------
    out.append('<text class="panlab" x="%d" y="14">What it buys in signal</text>' % ax)
    folds = [r["device_fold"] for r in same]
    fmin, fmax = min(folds), max(folds)
    pad = max((fmax - fmin) * 0.6, 0.04)
    ylo, yhi = fmin - pad, fmax + pad
    for frac in (0.0, 0.5, 1.0):
        v = ylo + (yhi - ylo) * frac
        y = top + ph - ph * frac
        out.append('<line class="grid" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>'
                   % (ax, y, ax + pw, y))
        out.append('<text class="tick" x="%d" y="%.1f" text-anchor="end">%s×'
                   '</text>' % (ax - 8, y + 4, num(v, 3)))
    xaxis(ax, "catalytic efficiency, kcat/Km")
    pts = sorted(same, key=lambda r: r["efficiency"])
    ytop = top + ph - ph * (fmax - ylo) / (yhi - ylo)
    ybot = top + ph - ph * (fmin - ylo) / (yhi - ylo)
    out.append('<rect class="band" x="%d" y="%.1f" width="%d" height="%.1f"/>'
               % (ax, ytop, pw, max(ybot - ytop, 1.5)))
    for r in pts:
        px_ = _logx(r["efficiency"], lo, hi, ax, pw)
        py_ = top + ph - ph * (r["device_fold"] - ylo) / (yhi - ylo)
        out.append('<circle cx="%.1f" cy="%.1f" r="5" fill="var(--series-a)" '
                   'stroke="var(--surface-1)" stroke-width="2"><title>%s: '
                   'kcat/Km %s, fold %s</title></circle>'
                   % (px_, py_, e(r["protein"]), num(r["efficiency"], 3),
                      num(r["device_fold"], 4)))
    spread_x = max(r["efficiency"] for r in same) / min(r["efficiency"] for r in same)
    out.append('<text class="note" x="%d" y="%d">%s× range in efficiency, '
               '%s× in fold</text>'
               % (ax, top + ph + 58, num(spread_x, 3), num(fmax / fmin, 3)))

    # ---- right: the loading, across the whole library --------------------
    out.append('<text class="panlab" x="%d" y="14">What it saves in enzyme</text>' % bx)
    mins = [r["min_enzyme_uM"] for r in loads]
    mlo = 10 ** math.floor(math.log10(min(mins)))
    mhi = 10 ** math.ceil(math.log10(max(mins)))
    dd = int(math.log10(mlo))
    while 10 ** dd <= mhi:
        y = top + ph - ph * (math.log10(10 ** dd) - math.log10(mlo)) / \
            (math.log10(mhi) - math.log10(mlo))
        out.append('<line class="grid" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>'
                   % (bx, y, bx + pw, y))
        out.append('<text class="tick" x="%d" y="%.1f" text-anchor="end">'
                   '10<tspan dy="-4" font-size="8">%d</tspan></text>'
                   % (bx - 8, y + 4, dd))
        dd += 1
    xaxis(bx, "catalytic efficiency, kcat/Km")
    for r in sorted(loads, key=lambda r: r["efficiency"]):
        px_ = _logx(r["efficiency"], lo, hi, bx, pw)
        py_ = top + ph - ph * (math.log10(r["min_enzyme_uM"]) - math.log10(mlo)) / \
            (math.log10(mhi) - math.log10(mlo))
        out.append('<circle cx="%.1f" cy="%.1f" r="5" fill="var(--series-b)" '
                   'stroke="var(--surface-1)" stroke-width="2"><title>%s: '
                   'kcat/Km %s, needs %s uM enzyme</title></circle>'
                   % (px_, py_, e(r["protein"]), num(r["efficiency"], 3),
                      num(r["min_enzyme_uM"], 3)))
    out.append('<text class="note" x="%d" y="%d">minimum enzyme, µM '
               '(falls as 1/efficiency)</text>' % (bx, top + ph + 58))
    out.append("</svg>")

    return ('<figure class="enzfigwrap"><div class="figscroll">%s</div>'
            '<figcaption>Left: the four enzymes published for %s, on the fold '
            'each delivers. Right: every type A enzyme in the library, on the '
            'loading each needs to turn over %s%% of its analyte inside the '
            'read. The axis is the same. A better enzyme costs less enzyme; it '
            'does not produce more signal, because the ceiling is set by the '
            'cell’s own peroxide flux and no enzyme moves that.</figcaption>'
            '</figure>' % ("".join(out), e(biomarker),
                           "95"))


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
               '<th class="c-v"></th><th>biomarker</th><th>module</th>'
               '<th class="c-t">type</th><th>study</th>'
               '<th class="n">clinical</th><th class="n">device</th>'
               '<th class="n">conc.</th><th class="n">AUC</th>'
               '<th class="n">sens<span class="u">=</span>spec</th>'
               '</tr></thead><tbody>')
    for c in rows:
        # One line, not four. The organism moved to the enzyme table and the
        # references, where it is stated once instead of under every row.
        study = (("%s · %s" % (c["cancer"], _fluid_short(c["biofluid"])))
                 if c["cancer"] else "no clinical study")
        out.append(
            '<tr data-light="%s" data-bm="%s" class="r-main">'
            '<td class="c-v">%s</td><td class="bm">%s</td><td>%s</td>'
            '<td class="c-t"><span class="tt %s" title="type %s">%s</span></td>'
            '<td class="ctx">%s</td>'
            '<td class="n">%s</td><td class="n">%s</td><td class="n">%s</td>'
            '<td class="n">%s</td><td class="n">%s</td></tr>'
            % (c["light"], e(c["biomarker"]), chip(c["light"], short=True),
               e(c["biomarker"]), e(c["protein"]),
               c["module_type"], c["module_type"], c["module_type"],
               e(study),
               fold(c["clinical_fold"]), fold(c["device_fold"]),
               fold(c["required_conc"]),
               num(c.get("auc_device"), 3), pct(c.get("sensitivity"))))
        # The reason gets the full width underneath rather than a column that
        # squeezes a sentence into twenty characters.
        out.append('<tr data-light="%s" data-bm="%s" class="r-why">'
                   '<td></td><td colspan="9">%s</td></tr>'
                   % (c["light"], e(c["biomarker"]), e(c["reason"])))
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
        # FIELD, not the CSV column name: the reader is owed "a dissociation
        # constant", not "kd_uM".
        need = " and ".join(FIELD.get(f, f) for f in m["missing"])
        syms = ", ".join(SYMBOL.get(f, f) for f in m["missing"])
        out.append('<li><b>%s</b> — no one has published %s (%s) for '
                   '<b>%s</b>, so its response cannot be computed. Not estimated '
                   'from a similar protein.</li>'
                   % (e(m["biomarker"]), e(need), e(syms), e(m["protein"])))
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

  var rows = [].slice.call(document.querySelectorAll('table.lib tbody tr.r-main')),
      whys = [].slice.call(document.querySelectorAll('table.lib tbody tr.r-why')),
      L = document.getElementById('f-light'), B = document.getElementById('f-bm'),
      C = document.getElementById('f-count'), M = document.getElementById('f-more'),
      open = false;

  function apply(){
    var l = L ? L.value : '', b = B ? B.value : '', n = 0, hidden = 0;
    rows.forEach(function(r, i){
      var match = (!l || r.dataset.light === l) && (!b || r.dataset.bm === b);
      // the fold only applies when no filter is asking for the rejections
      var folded = !open && !l && r.dataset.light === 'red';
      if (match && folded) hidden++;
      r.classList.toggle('hid', !match || folded);
      if (whys[i]) whys[i].classList.toggle('hid', !match || folded);
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
