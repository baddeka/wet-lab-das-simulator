"""Checks on the platform layer: diagnostic performance and panels.

The panel formula is checked against the closed form rather than against
itself, and separately for the sign: with equal effect sizes, correlation must
make a panel worse, never better. An error in the quadratic form shows up in
that monotonicity check first.

    python tests/test_platform.py
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import sensorlab                                          # noqa: E402
from sensorlab import data, panels, performance, report, stage2   # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", name,
                           "" if cond else "\n         -> " + str(detail)))
    if not cond:
        FAILURES.append(name)


def close(a, b, tol=1e-9):
    return a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(a))


def test_panel_maths():
    print("panel combination")
    # k = 2, equal effect: the closed form is sqrt(2/(1+rho))
    for rho in (0.0, 0.3, 0.5, 0.7, 0.9):
        got = performance.panel([1.0, 1.0], rho)
        want = math.sqrt(2.0 / (1.0 + rho))
        check("k=2 equal d at rho=%.1f matches the closed form" % rho,
              close(got, want), (got, want))

    # k = 3, equal effect: sqrt(3/(1+2rho))
    for rho in (0.0, 0.4, 0.8):
        got = performance.panel([1.0] * 3, rho)
        want = math.sqrt(3.0 / (1.0 + 2.0 * rho))
        check("k=3 equal d at rho=%.1f matches the closed form" % rho,
              close(got, want), (got, want))

    # Equal effects: correlation degrades the panel monotonically.
    eq = [performance.panel([1.0] * 3, r) for r in (0.0, 0.2, 0.4, 0.6, 0.8)]
    check("with equal effects, correlation only degrades the panel",
          all(a > b for a, b in zip(eq, eq[1:])), eq)

    # Unequal effects: it does NOT. The curve is U-shaped and diverges as
    # rho -> 1, because the markers' difference cancels shared variation. This
    # is why panels.py scans the range instead of treating a high rho as the
    # pessimistic end.
    un = [performance.panel([1.2, 0.9, 1.5], r) for r in (0.0, 0.4, 0.6, 0.8, 0.95)]
    check("with unequal effects the curve turns back up (suppressor effect)",
          un[-1] > un[-2] and min(un) < un[0], un)
    check("the worst case is in the interior, not at an end",
          un.index(min(un)) not in (0, len(un) - 1), un)

    check("a one-module panel is just that module",
          close(performance.panel([1.3], 0.7), 1.3))
    check("an empty panel is None", performance.panel([], 0.0) is None)
    check("equal effects at rho=0 give the sum in quadrature",
          close(performance.panel([1.0, 1.0], 0.0), math.sqrt(2.0)))
    check("rho at the singular point returns None",
          performance.panel([1.0, 1.0], 1.0) is None)


def test_performance_maths():
    print("diagnostic performance")
    pf = data.load_platform()

    check("log_sd of a tight distribution is about cv",
          close(performance.log_sd(10.0, 1.0), math.sqrt(math.log(1.01)), 1e-12))
    check("log_sd refuses a non-positive mean",
          performance.log_sd(0.0, 1.0) is None)
    check("log_sd refuses a missing spread",
          performance.log_sd(10.0, None) is None)

    # compression: a device fold equal to the clinical fold loses nothing
    check("no compression when the device reproduces the clinical fold",
          close(performance.compression(2.0, 2.0), 1.0))
    check("compression is the ratio of logs",
          close(performance.compression(4.0, 2.0), 0.5))
    check("compression of a flat device is zero",
          close(performance.compression(2.0, 1.0), 0.0))

    rdr = performance.reader_log_sd(pf)
    check("reader spread falls with replicates",
          rdr > 0 and rdr < pf["cv_reader"], rdr)

    check("AUC of zero separation is one half",
          close(performance.auc_from_d(0.0), 0.5))
    check("AUC rises with separation",
          performance.auc_from_d(2.0) > performance.auc_from_d(1.0))


def test_against_real_data():
    print("on the real library")
    b = sensorlab.load("screen_default")
    res = report.build(b)

    types = {c["sensor"].module_type for c in res["candidates"]}
    check("only two module types reach the screen", types <= {"A", "B"}, types)

    passing = [c for c in res["candidates"]
               if c["light"] in (stage2.GREEN, stage2.YELLOW)]
    check("something passes both stages", len(passing) > 0)

    with_perf = [c for c in passing if c.get("performance")]
    check("passing candidates carry a performance estimate", len(with_perf) > 0)
    for c in with_perf:
        p = c["performance"]
        ok = (0.0 < p["compression"] <= 1.0
              and 0.5 <= p["auc_at_reader"] <= 1.0
              and 0.5 <= p["sensitivity_youden"] <= 1.0)
        if not ok:
            check("%s has a sane performance block" % c["sensor"].label, False, p)
    check("every performance block is in range", True)

    for c in passing:
        if not c.get("performance"):
            check("%s says why performance is missing" % c["sensor"].label,
                  bool(c.get("performance_missing")))
    check("a missing performance always has a reason", True)

    # a panel of one must equal that module exactly
    allp = panels.all_cancers(res["candidates"], b["platform"])
    for cancer, plist in allp.items():
        singles = [p for p in plist if p["size"] == 1]
        for p in singles:
            d = p["modules"][0]["performance"]["d_at_reader"]
            check("single-module panel for %s equals its module" % p["biomarkers"][0],
                  close(p["d_worst"], d) and close(p["d_best"], d),
                  (p["d_worst"], d))
        for p in plist:
            if p["size"] > 1:
                check("panel %s brackets its own scan" % "+".join(p["biomarkers"]),
                      p["auc_worst"] <= p["auc_independent"] + 1e-12
                      and p["auc_independent"] <= p["auc_best"] + 1e-12,
                      (p["auc_worst"], p["auc_independent"], p["auc_best"]))
    check("panels are internally consistent", True)


def test_out_of_scope_is_documented():
    print("excluded sensors are recorded, not dropped")
    from sensorlab import tables
    rows = tables.read("out_of_scope.csv")
    check("out_of_scope.csv is populated", len(rows) > 0)
    check("every excluded row gives a reason",
          all(r["reason_excluded"] for r in rows))
    check("every excluded row keeps its DOI", all(r["source_doi"] for r in rows))
    names = {r["protein_name"] for r in rows}
    live = {s.protein_name for s in data.load_sensors()}
    check("nothing is in both files", not (names & live), names & live)


def main():
    for fn in (test_panel_maths, test_performance_maths,
               test_against_real_data, test_out_of_scope_is_documented):
        fn()
        print()
    if FAILURES:
        print("%d check(s) failed: %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
