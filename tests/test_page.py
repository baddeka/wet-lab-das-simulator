"""Checks on the generated platform page, index.html.

Each of these exists because the corresponding mistake was already made and
found by looking at the page rather than by any test:

  - the chart legend described a module type that had no row on the chart, so a
    reader went hunting for a colour that was not there;
  - both figures shrank at phone width until their 11px labels were a few
    pixels tall, with no fallback;
  - wide tables ran off the side of the screen instead of scrolling.

    python tests/test_page.py
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

FAILURES = []


def check(name, cond, detail=""):
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name,
                           "" if cond else "\n         -> " + str(detail)))
    if not cond:
        FAILURES.append(name)


def main():
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
    missing = {d for d in used if d not in refs and not d.startswith("http")}
    check("every source in the data is in the reference list", not missing, missing)

    print()
    print("nothing leaked into the markup")
    for tok in ("None", "nan", "NaN", "undefined", "%s", "{}"):
        n = len(re.findall(re.escape(tok), html))
        check("no %r in the page" % tok, n == 0, "%d occurrence(s)" % n)

    print()
    print("it survives a phone")
    tables = [m.group(1) for m in re.finditer(r'<table class="(\w+)"', html)]
    unscrolled = []
    for m in re.finditer(r'<table class="(\w+)"', html):
        pre = html[max(0, m.start() - 220):m.start()]
        if "figscroll" not in pre and 'class="scroll"' not in pre:
            unscrolled.append(m.group(1))
    check("every table can scroll sideways", not unscrolled, unscrolled)
    check("the page has more than one table", len(tables) > 1,
          collections.Counter(tables))

    # every figure, not just the two that had the problem first
    import re as _re
    drawn = set(_re.findall(r'<svg class="(\w+)"', html))
    guarded = set(_re.findall(r'svg\.(\w+)\{min-width', html))
    check("every figure stops shrinking before it becomes illegible",
          drawn <= guarded, "unguarded: %s" % (drawn - guarded))
    unscrolled = [m.group(1) for m in _re.finditer(r'<svg class="(\w+)"', html)
                  if "figscroll" not in html[max(0, m.start() - 220):m.start()]]
    check("every figure can scroll sideways", not unscrolled, unscrolled)
    check("there is a narrow-screen breakpoint", "@media (max-width:" in html)
    check("the chart has a table fallback", 'class="posdata"' in html)

    print()
    print("structure")
    for sec in ("architecture", "positioning", "library", "panels", "model",
                "gaps", "references"):
        check("section %s is present" % sec, attr("id", sec))
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
    sys.exit(main())
