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
    return "\n".join(out)


# --------------------------------------------------------------- sections
def stat_tiles(d):
    c = d["counts"]
    t = d["thresholds"]
    tiles = [
        ("modules in the library", len(d["sensors"]), "two types, one skeleton"),
        ("clinical studies", len(d["studies"]), "%d biomarkers, %d cancers"
         % (len(d["biomarkers"]), len(d["cancers"]))),
        ("module × study pairs", len(d["candidates"]),
         "%d pass, %d with concentration, %d fail"
         % (c.get("green", 0), c.get("yellow", 0), c.get("red", 0))),
        ("reader floor", "%.3f×" % t["fold_needed"],
         "smallest fold resolvable at CV %s, n=%d"
         % (pct(t["cv_reader"]), int(t["n_rep"]))),
    ]
    out = ['<div class="tiles">']
    for label, value, sub in tiles:
        out.append('<div class="tile"><div class="tile-v">%s</div>'
                   '<div class="tile-k">%s</div><div class="tile-s">%s</div></div>'
                   % (value, e(label), e(sub)))
    out.append("</div>")
    return "\n".join(out)


def library_table(d):
    rows = sorted(d["candidates"],
                  key=lambda c: ({"green": 0, "yellow": 1, "red": 2}[c["light"]],
                                 -(c.get("auc_device") or 0),
                                 c["biomarker"], c["protein"]))
    out = ['<div class="filters" data-js-only>',
           '<label>Show <select id="f-light">'
           '<option value="">every verdict</option>'
           '<option value="green">passes only</option>'
           '<option value="yellow">needs concentration</option>'
           '<option value="red">fails only</option></select></label>',
           '<label>Biomarker <select id="f-bm"><option value="">all</option>'
           + "".join('<option>%s</option>' % e(b) for b in d["biomarkers"])
           + '</select></label>',
           '<span class="count" id="f-count"></span></div>']
    out.append('<div class="scroll"><table class="lib"><thead><tr>'
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
    return "\n".join(out)


def panels_section(d):
    if not d["panels"]:
        return "<p class='empty'>No cancer has two modules that both clear the screen.</p>"
    out = []
    for cancer, plist in sorted(d["panels"].items()):
        out.append('<h3>%s</h3>' % e(cancer))
        out.append('<table class="panels"><thead><tr><th>panel</th>'
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
        out.append('<table class="enz"><thead><tr><th>enzyme</th><th>organism</th>'
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
        out.append("</tbody></table>")
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
        out.append('<li><a href="%s" rel="noreferrer">%s</a><span class="use">%s</span></li>'
                   % (e(href), e(doi), e(uses)))
    out.append("</ol>")
    return "\n".join(out)


# --------------------------------------------------------------- the skeleton
SKELETON_SVG = """
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
"""


CSS = """
*{box-sizing:border-box}
html{color-scheme:light dark}
body{margin:0;background:var(--plane);color:var(--ink-1);
     font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;
     -webkit-text-size-adjust:100%}
.wrap{max-width:980px;margin:0 auto;padding:0 20px 96px}
header{padding:72px 0 40px}
h1{font-size:clamp(30px,5vw,44px);line-height:1.1;margin:0 0 14px;letter-spacing:-.02em}
.lede{font-size:clamp(17px,2.4vw,20px);color:var(--ink-2);margin:0 0 10px;max-width:70ch}
.sub{color:var(--ink-3);font-size:14px;margin:18px 0 0}
section{margin:52px 0 0;scroll-margin-top:16px}
h2{font-size:13px;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-3);
   margin:0 0 6px;font-weight:600}
.h2sub{font-size:clamp(20px,3vw,26px);margin:0 0 16px;letter-spacing:-.01em;line-height:1.25}
h3{font-size:15px;margin:26px 0 8px}
p{max-width:72ch}
.aside{color:var(--ink-2);font-size:14px}
.empty{color:var(--ink-3);font-style:italic}
.card{background:var(--surface-1);border:1px solid var(--ring);border-radius:14px;
      padding:18px 20px;margin:14px 0}

.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:22px 0}
.tile{background:var(--surface-1);border:1px solid var(--ring);border-radius:14px;padding:16px 18px}
.tile-v{font-size:30px;line-height:1.1;letter-spacing:-.02em}
.tile-k{font-size:13px;color:var(--ink-2);margin-top:6px}
.tile-s{font-size:12px;color:var(--ink-3);margin-top:3px}

svg.chart,svg.arch{width:100%;height:auto;display:block}
.grid{stroke:var(--grid);stroke-width:1}
.tick,.axis-title,.rowsub,.rownote,.ps,.ms{fill:var(--ink-3);font-size:11px}
.axis-title{font-size:12px}
.rowlab,.pl,.mt{fill:var(--ink-1);font-size:13px;font-weight:600}
.mb{fill:var(--ink-1);font-size:13px}
.pl{font-size:14px}
.range{opacity:.9}

table{border-collapse:collapse;width:100%;font-size:13.5px}
th{text-align:left;font-weight:600;color:var(--ink-3);font-size:11.5px;
   letter-spacing:.05em;text-transform:uppercase;padding:0 10px 8px;
   border-bottom:1px solid var(--axis);white-space:nowrap}
th .u{text-transform:none;letter-spacing:0}
td{padding:9px 10px;border-bottom:1px solid var(--grid);vertical-align:top}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.bm{font-weight:600;white-space:nowrap}
td.ctx{color:var(--ink-2);font-size:12.5px}
td.why{color:var(--ink-2);font-size:12.5px;min-width:22ch}
.org{color:var(--ink-3);font-size:11.5px;font-style:italic}
.scroll{overflow-x:auto;margin:0 -20px;padding:0 20px}
tr.hid{display:none}

.chip{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;
      font-size:12px;font-weight:600}
.chip .dot{font-size:13px;line-height:1}
.chip.green{color:var(--good)} .chip.yellow{color:#8a6100} .chip.red{color:var(--critical)}
.tt{display:inline-grid;place-items:center;width:20px;height:20px;border-radius:6px;
    font-size:11.5px;font-weight:700;color:#fff}
.tt.A{background:var(--series-a)} .tt.B{background:var(--series-b)}
tr.v-holds td.bm{color:var(--good)}
tr.v-fails td.bm{color:var(--critical)}

.filters{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin:0 0 14px;
         font-size:13px;color:var(--ink-2)}
select{font:inherit;padding:5px 8px;border-radius:8px;border:1px solid var(--axis);
       background:var(--surface-1);color:var(--ink-1)}
.count{color:var(--ink-3);font-size:12.5px}
[data-js-only]{display:none}

.cols{display:grid;grid-template-columns:1fr 1fr;gap:28px}
ul.gap{padding-left:18px;margin:8px 0;font-size:13.5px;color:var(--ink-2)}
ul.gap li{margin:7px 0}
ol.refs{padding-left:22px;font-size:13px;color:var(--ink-2)}
ol.refs li{margin:9px 0}
ol.refs a{color:var(--series-a);text-decoration:none;font-variant-numeric:tabular-nums}
ol.refs a:hover{text-decoration:underline}
.use{display:block;color:var(--ink-3);font-size:12px;margin-top:2px}
footer{margin:72px 0 0;padding-top:22px;border-top:1px solid var(--grid);
       color:var(--ink-3);font-size:12.5px}
footer a{color:var(--series-a)}
@media (max-width:720px){.cols{grid-template-columns:1fr}header{padding:44px 0 28px}}
"""

JS = """
(function(){
  document.querySelectorAll('[data-js-only]').forEach(function(n){n.style.display='flex'});
  var L=document.getElementById('f-light'), B=document.getElementById('f-bm'),
      C=document.getElementById('f-count'),
      rows=[].slice.call(document.querySelectorAll('table.lib tbody tr'));
  if(!L||!B) return;
  function apply(){
    var l=L.value, b=B.value, n=0;
    rows.forEach(function(r){
      var ok=(!l||r.dataset.light===l)&&(!b||r.dataset.bm===b);
      r.classList.toggle('hid',!ok); if(ok)n++;
    });
    C.textContent=n+' of '+rows.length+' shown';
  }
  L.addEventListener('change',apply); B.addEventListener('change',apply); apply();
})();
"""
