"""Checks on the generated platform page, index.html.

Each of these exists because the corresponding mistake was already made and
found by looking at the page rather than by any test:

  - the chart legend described a module type that had no row on the chart, so a
    reader went hunting for a colour that was not there;
  - both figures shrank at phone width until their 11px labels were a few
    pixels tall, with no fallback;
  - wide tables ran off the side of the screen instead of scrolling;
  - a chart narrower than the column was stretched to fill it, taking its 11px
    tick labels to 21px with it;
  - one log axis read 0.001, 0.010, 0.100, 1.00, 10.0 and another mixed
    0.0001 with 10^-5: two number formats on one ruler;
  - a sentence pointed the reader at "section 2.6" for an argument that is in
    2.5;
  - stroke-dasharray='None' reached four rules, which browsers quietly draw
    solid.

    python tests/test_page.py            fast checks, against the built page
    python tests/test_page.py --full     also rebuild and compare (minutes)

The rebuild is opt-in because the screen integrates a few hundred stiff ODEs -
the sensitivity analysis and the scaling check each re-run the whole chain once
per parameter - and a test nobody waits for is a test nobody runs.
"""
import collections
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import build_platform                                    # noqa: E402
import render_page                                       # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    line = "  %-4s %s%s" % ("ok" if cond else "FAIL", name,
                            "" if cond else "\n         -> " + str(detail))
    # Windows consoles here are cp1251, and a failure detail quoting a tick
    # label killed the run on the multiplication sign before it could report
    # the failure it had found.
    enc = getattr(sys.stdout, "encoding", None) or "ascii"
    print(line.encode(enc, "backslashreplace").decode(enc))
    if not cond:
        FAILURES.append(name)


def main(argv=()):
    page = os.path.join(ROOT, "index.html")
    jsonf = os.path.join(ROOT, "platform.json")
    for f in (page, jsonf):
        if not os.path.exists(f):
            print("missing %s; run: python build_platform.py" % f)
            return 1
    html = io.open(page, encoding="utf-8").read()
    # The renderer emits single-quoted attributes and HTML-escapes its text, so
    # compare against a normalised copy rather than the raw markup. The first
    # version of this test did not, and reported eight failures that were all
    # its own.
    import html as _h
    # Two separate normalisations, because mixing them corrupts the text. The
    # first version of this test rewrote quote characters across the whole
    # document, mangled every apostrophe in the prose, and then reported the
    # damage it had just done as failures of the page.
    plain = _h.unescape(html)           # for prose: entities resolved only

    def attr(name, value):              # for attributes: either quote style
        return re.search(r"%s=['\"]%s['\"]" % (name, re.escape(value)),
                         html) is not None
    data = json.load(io.open(jsonf, encoding="utf-8"))

    if "--full" in argv:
        print("the page is current")
        fresh = build_platform.build()
        check("platform.json is reproducible from the data files", fresh == data,
              "run: python build_platform.py")

    print()
    print("the page says what the data says")
    types_drawn = sorted({r["module_type"] for r in data["positioning"]})
    check("the chart legend names only the types it draws",
          not (types_drawn == ["A"] and "type B constant is K" in html),
          "legend describes type B but no type B row is drawn")
    if types_drawn == ["A"]:
        check("the legend says why type B is absent",
              "No type B module appears at all" in html)

    for c in data["candidates"]:
        if c["light"] == "red" and c["reason"] not in plain:
            check("rejection reason is printed for %s" % c["protein"], False,
                  c["reason"][:70])
    check("every rejection reason reaches the page", True)

    n_rows = len(re.findall(r'class="r-main"', html))
    check("every candidate has a row", n_rows == len(data["candidates"]),
          (n_rows, len(data["candidates"])))

    refs = set(re.findall(r'href="https://doi\.org/([^"]+)"', html))
    refs = {r.replace('%3C', '<').replace('%3E', '>') for r in refs}
    used = {s["doi"] for s in data["sensors"] if s["doi"]}
    used |= {s["doi"] for s in data["studies"] if s["doi"]}
    used |= {r.get("source_doi") for r in data.get("parameters", [])}
    used.discard(None)
    used.discard("")
    missing = {d for d in used if d not in refs and not d.startswith("http")}
    check("every source in the data is in the reference list", not missing, missing)

    print()
    print("nothing leaked into the markup")
    found = render_page.leaks(html)
    check("no Python value or unfilled format slot in the page", not found,
          found[:3])

    print()
    print("the document is numbered and cross-referenced")
    figs = [int(n) for n in re.findall(r"<b>Figure&nbsp;(\d+)\.</b>", html)]
    check("figures are numbered 1..n with no gaps and no repeats",
          figs == list(range(1, len(figs) + 1)), figs)
    check("there are figures at all", len(figs) >= 8, len(figs))
    tabs = [int(n) for n in re.findall(r"<b>Table&nbsp;(\d+)\.</b>", html)]
    check("tables are numbered 1..n with no gaps and no repeats",
          tabs == list(range(1, len(tabs) + 1)), tabs)

    # every figure carries a caption, not just a number
    bare = re.findall(r"<figcaption>(?!<b>(?:Figure|Table)&nbsp;)", html)
    check("every figure and table caption starts with its number", not bare,
          "%d caption(s) without one" % len(bare))

    # citations have to land somewhere
    cited = set(re.findall(r"class='cite' href='#(r\d+)'", html))
    targets = set(re.findall(r'<li id="(r\d+)"', html))
    check("every citation points at a reference that exists",
          cited <= targets, sorted(cited - targets))
    check("the page cites at least one source in its prose", cited, cited)

    # a sentence that sends the reader to a section number it invented
    heads = set(re.findall(r"<span class='secno'>([\d.]+)</span>", html))
    refd = set(re.findall(r"[Ss]ection(?:&nbsp;|\s)([\d]+(?:\.[\d]+)?)", plain))
    check("every section a sentence points at exists", refd <= heads,
          "pointed at %s, page has %s" % (sorted(refd - heads), sorted(heads)))

    # a reference token that never found its figure would print as control
    # characters in the middle of a sentence
    check("no unresolved figure reference is left in the text",
          "\x01" not in html, html.count("\x01"))
    xrefs = set(re.findall(r"class='xref' href='#([\w-]+)'", html))
    check("every figure reference in the prose points at something that exists",
          xrefs <= set(re.findall(r"id='([\w-]+)'", html))
          | set(re.findall(r'id="([\w-]+)"', html)), sorted(xrefs))
    check("the prose cites figures by number", len(xrefs) >= 5, len(xrefs))

    print()
    print("the figures can be read, not just looked at")
    tips = re.findall(r"data-tip='", html)
    titles = re.findall(r"<title>", html)
    check("the charts carry hover readouts", len(tips) >= 40, len(tips))
    check("every readout is also a native title, for print and screen readers",
          len(titles) >= len(tips), (len(titles), len(tips)))
    charted = set(re.findall(r"<svg class=['\"]chart['\"].*?</svg>", html, re.S))
    without = [i for i, svg in enumerate(charted) if "data-tip" not in svg]
    check("every chart has at least one readout on it", not without,
          "%d chart(s) with none" % len(without))
    check("there is a print stylesheet", "@media print" in html)

    print()
    print("every equation defines its symbols")
    eqs = len(re.findall(r"<div class='eq'>", html))
    wheres = len(re.findall(r"<dl class='where'>", html))
    check("there is a 'where' list for every display equation", eqs == wheres,
          "%d equations, %d symbol lists" % (eqs, wheres))
    check("the model section carries its equations", eqs >= 5, eqs)

    print()
    print("every constant says what fixed it")
    prows = data.get("parameters") or []
    check("the data file carries provenance for every constant",
          all(r.get("source_kind") for r in prows),
          [r["name"] for r in prows if not r.get("source_kind")])
    kinds = len(re.findall(r"class=\"kind ", html))
    check("the page prints a provenance chip for every constant shown",
          kinds >= len(prows), "%d chips, %d constants" % (kinds, len(prows)))
    measured = [r for r in prows if r.get("source_kind") in ("measured", "derived")]
    check("every measured or derived constant carries a DOI",
          all(r.get("source_doi") for r in measured),
          [r["name"] for r in measured if not r.get("source_doi")])

    print()
    print("it survives a phone")
    tables = [m.group(1) for m in re.finditer(r'<table class="(\w+)"', html)]
    unscrolled = []
    for m in re.finditer(r'<table class="(\w+)"', html):
        pre = html[max(0, m.start() - 260):m.start()]
        if "figscroll" not in pre and "class='scroll'" not in pre \
                and 'class="scroll"' not in pre:
            unscrolled.append(m.group(1))
    check("every table can scroll sideways", not unscrolled, unscrolled)
    check("the page has more than one table", len(tables) > 1,
          collections.Counter(tables))

    # every figure, not just the two that had the problem first
    drawn = set(re.findall(r"<svg class=['\"](\w+)['\"]", html))
    guarded = set(re.findall(r"svg\.(\w+)\{min-width", html))
    check("every figure stops shrinking before it becomes illegible",
          drawn <= guarded, "unguarded: %s" % (drawn - guarded))
    unscrolled = [m.group(1) for m in re.finditer(r"<svg class=['\"](\w+)['\"]", html)
                  if "figscroll" not in html[max(0, m.start() - 260):m.start()]]
    check("every figure can scroll sideways", not unscrolled, unscrolled)
    check("there is a narrow-screen breakpoint", "@media (max-width:" in html)
    check("the chart has a table fallback", 'class="posdata"' in html)

    print()
    print("the charts keep their own scale")
    svgs = re.findall(r"<svg class=['\"]chart['\"][^>]*>", html)
    nocap = [s for s in svgs if "max-width" not in s]
    check("no chart is stretched past its natural width", not nocap,
          "%d chart(s) without a max-width" % len(nocap))

    # One number format per axis. Grouped by the axis a tick belongs to, not by
    # the figure it is in: two panels of one figure may legitimately count in
    # different units, and the first version of this check reported that as a
    # failure. The ruler is the unit of consistency, not the picture.
    by_axis = collections.defaultdict(list)
    for m in re.finditer(r"class='tick' data-ax='(\d+[xy])'[^>]*>([^<]+)</text>",
                         html):
        by_axis[m.group(1)].append(_h.unescape(m.group(2)))
    mixed = []
    for ax, ticks in sorted(by_axis.items()):
        sci = [t for t in ticks
               if re.search(r"10[⁰-⁹¹²³⁻]", t)]
        dec = [t for t in ticks
               if re.match(r"^-?[\d ]+(\.\d+)?[×%]?$", t)]
        if sci and dec:
            mixed.append((ax, sci[:2], dec[:2]))
    check("no axis mixes powers of ten with plain decimals", not mixed,
          mixed[:2])
    check("the charts label their axes", len(by_axis) >= 10, len(by_axis))

    print()
    print("structure")
    for sec in ("architecture", "model", "screen", "performance", "panels",
                "sensitivity", "gaps", "references"):
        check("section %s is present" % sec, attr("id", sec))
    opened = html.count("<section")
    closed = html.count("</section>")
    check("every section is closed", opened == closed, (opened, closed))
    rail = set(re.findall(r"data-sec='([\w-]+)'", html))
    ids = set(re.findall(r"id='([\w-]+)'", html)) | set(re.findall(r'id="([\w-]+)"', html))
    check("every contents entry points at a heading that exists",
          rail <= ids, sorted(rail - ids))
    check("the contents rail has two levels", len(rail) >= 12, len(rail))
    check("the worked example is linked", attr("href", "simulator.html"))
    check("dark mode is defined for both scopes",
          "prefers-color-scheme:dark" in html and '[data-theme="dark"]' in html)

    print()
    if FAILURES:
        print("%d check(s) failed: %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
