# -*- coding: utf-8 -*-
"""One function per figure, drawn with charts.py from the exported analysis.

Each function takes the platform payload and returns markup, or None when the
data it needs is absent - a figure that would have to invent a point is not
drawn at all, and the section that wanted it says what was missing instead.

The division of labour: sensorlab/analysis.py decides what is true, this module
decides what it looks like, charts.py decides where the ticks go. None of the
three is allowed to do another's job, which is why no number is computed below.
"""
import math

import charts
from charts import Axes, compose

A = "var(--series-a)"
B = "var(--series-b)"
C = "var(--series-c)"
INK = "var(--ink-1)"
INK2 = "var(--ink-2)"
INK3 = "var(--ink-3)"
AXIS = "var(--axis)"
GOOD = "var(--good)"
WARN = "var(--warning)"
BAD = "var(--critical)"

GROUP_COLOR = {"operator": A, "module": B, "chassis": C}

# stage 1 returns three verdicts, not two. The first version of the forest plot
# tested for "holds", which is the panel vocabulary, so all 27 points came out
# red - including the ten that passed.
VERDICT_COLOR = {"pass": GOOD, "fail": BAD, "insufficient": WARN}
VERDICT_WORD = {"pass": "passed stage 1", "fail": "failed stage 1",
                "insufficient": "not enough reported to judge"}


def _f3(v, _=None):
    return charts.tick_text(v)


def _auc(v, _=None):
    return "%.2f" % v


def _pct(v, _=None):
    return "%.0f%%" % (100.0 * v)


def _fold(v, _=None):
    return ("%.2f" % v).rstrip("0").rstrip(".") + "×"


def _signed(v, _=None):
    return ("%+.1f" % v) if v else "0"


# ------------------------------------------------------- stage 1: effect sizes

def effect_sizes(d):
    """Every cohort's effect size with its interval, grouped by biomarker.

    A forest plot, because stage 1 is a meta-analysis in miniature: the question
    is not only how large each separation is but how well each is pinned down,
    and a table of point estimates hides the second half of that.
    """
    rows = d["analysis"]["effect_sizes"]
    if not rows:
        return None
    thr = d["thresholds"]["cohens_d_pass_min"]

    order, seen = [], set()
    for r in rows:
        if r["biomarker"] not in seen:
            seen.add(r["biomarker"])
            order.append(r["biomarker"])

    # one slot per row plus one per group heading
    slots, items = [], []
    for bm in order:
        slots.append(("head", bm))
        for r in rows:
            if r["biomarker"] == bm:
                slots.append(("row", r))
    n = len(slots)

    lo = min([r["lo"] for r in rows if r["lo"] is not None]
             + [r["d"] for r in rows] + [-thr]) - 0.35
    hi = max([r["hi"] for r in rows if r["hi"] is not None]
             + [r["d"] for r in rows] + [thr]) + 0.35

    ax = Axes(w=900, h=78 + 21 * n, left=330, right=92, top=50, bottom=62)
    ax.xlim(lo, hi).ylim(n - 0.5, -0.5)
    ax.band(-thr, thr, INK3, 0.07)
    ax.frame(xlabel="Cohen’s d  (negative: the marker falls in disease)",
             ygrid=False, xgrid=True, yticks=[])
    ax.vline(0, color=AXIS, dash=None, width=1.5)
    for s in (-thr, thr):
        ax.vline(s, color=INK3, dash="3 3", width=1)
    ax.text((ax.x(-thr) + ax.x(thr)) / 2.0, ax.y1 - 9,
            "too small to screen on", cls="note", anchor="middle", px=True)
    ax.legend([(VERDICT_WORD[k], VERDICT_COLOR[k])
               for k in ("pass", "fail", "insufficient")],
              x=ax.x0 - 322, y=ax.y1 - 28, swatch="dot")

    for i, (kind, payload) in enumerate(slots):
        if kind == "head":
            ax.text(ax.x0 - 322, ax.y(i) + 4, payload, cls="grphd", px=True)
            continue
        r = payload
        col = VERDICT_COLOR.get(r["verdict"], INK3)
        y = ax.y(i)
        if r["lo"] is not None:
            ax.marks.append(
                "<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='%s' "
                "stroke-width='1.6' opacity='.55' stroke-linecap='round'/>"
                % (ax.x(max(r["lo"], lo)), y, ax.x(min(r["hi"], hi)), y, col))
            for v in (r["lo"], r["hi"]):
                if lo <= v <= hi:
                    ax.marks.append(
                        "<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' "
                        "stroke='%s' stroke-width='1.6' opacity='.55'/>"
                        % (ax.x(v), y - 3.5, ax.x(v), y + 3.5, col))
        ax.dot(r["d"], i, r=4.0, color=col)
        label = "%s · %s" % (r["cancer"] or "—", r["biofluid"] or "—")
        ax.over.append("<text class='rowlab2' x='%.1f' y='%.1f'>%s</text>"
                       % (ax.x0 - 308, y + 4, charts.esc(label)))
        right = ("n = %d" % r["n_total"]) if r["n_total"] else "n not given"
        ax.over.append("<text class='rownote2' x='%.1f' y='%.1f'>%s</text>"
                       % (ax.x1 + 8, y + 4, charts.esc(right)))
    return ax.svg(title="Effect size with 95% interval for every cohort")


# ------------------------------------------------- the statistical route check

def reconstruction(d):
    """Rebuilt AUC against the AUC the paper reported for the same cohort."""
    rec = d["analysis"]["reconstruction"]
    rows = rec["rows"]
    if len(rows) < 3:
        return None
    vals = [r["reported"] for r in rows] + [r["rebuilt"] for r in rows]
    lo = min(0.55, min(vals) - 0.04)
    hi = max(1.0, max(vals) + 0.04)

    ax = Axes(w=620, h=440, left=70, right=28, top=30, bottom=60)
    ax.xlim(lo, hi).ylim(lo, hi)
    ax.frame(xlabel="AUC the study reports from its own ROC analysis",
             ylabel="AUC rebuilt from mean, spread and group sizes",
             xgrid=True, yfmt=_auc, xfmt=_auc)
    ax.line([(lo, lo), (hi, hi)], color=AXIS, width=1.5, dash="5 4")
    ax.text(ax.x(hi) - 6, ax.y(hi) + 16, "perfect agreement", cls="note",
            anchor="end", px=True)
    for r in rows:
        over = r["rebuilt"] > r["reported"]
        ax.marks.append(
            "<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='%s' "
            "stroke-width='1.4' opacity='.45'/>"
            % (ax.x(r["reported"]), ax.y(r["reported"]),
               ax.x(r["reported"]), ax.y(r["rebuilt"]), BAD if over else A))
        ax.dot(r["reported"], r["rebuilt"], r=4.5,
               color=BAD if over else A)
        ax.label_point(r["reported"], r["rebuilt"],
                       "%s" % r["biomarker"],
                       color=INK2, dx=9, dy=-5)
    ax.text(ax.x0 + 10, ax.y0 - 14,
            "above the line: this pipeline is optimistic", cls="note", px=True)
    return ax.svg(title="Rebuilt against reported AUC")


# ------------------------------------------------------------ transfer function

def dose_response(d):
    """Device fold against analyte level, with the compression drawn as a chord."""
    dr = d["analysis"].get("dose_response")
    if not dr or not dr.get("curve"):
        return None
    xs = [p[0] for p in dr["curve"]]
    ys = [p[1] for p in dr["curve"]]
    ylo, yhi = min(ys + [1.0]) * 0.93, max(ys + [dr["fold_needed"]]) * 1.10

    ax = Axes(w=720, h=400, left=72, right=132, top=40, bottom=62,
              xlog=True, ylog=True)
    ax.xlim(min(xs), max(xs)).ylim(ylo, yhi)
    ax.band(dr["healthy_uM"], dr["sick_uM"], A, 0.09)
    ax.frame(xlabel="%s in the biofluid  (µM)" % dr["biomarker"],
             ylabel="reporter, relative to the healthy sample",
             yticks=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6, 2.0],
             yfmt=_fold, xgrid=False)
    ax.hline(1.0, color=AXIS, dash=None, width=1.2)
    ax.hline(dr["fold_needed"], color=INK3, dash="4 3")
    ax.text(ax.x1 - 4, ax.y(dr["fold_needed"]) - 7,
            "smallest fold the reader resolves", cls="note", anchor="end",
            px=True)

    if dr.get("anchor_on_axis") and min(xs) < dr["anchor_on_axis"] < max(xs):
        ax.vline(dr["anchor_on_axis"], color=B, dash="5 4", width=1.5,
                 label="%s" % dr["anchor_name"], at=ax.y1 + 12)

    ax.line(dr["curve"], color=A, width=2.4)
    # the chord between the two clinical levels: its slope is the compression
    ax.line([(dr["healthy_uM"], 1.0), (dr["sick_uM"], dr["fold_at_sick"])],
            color=BAD, width=1.8, dash="6 4")
    ax.dot(dr["healthy_uM"], 1.0, r=5, color=A)
    ax.dot(dr["sick_uM"], dr["fold_at_sick"], r=5, color=A)
    ax.label_point(dr["healthy_uM"], 1.0, "healthy median",
                   sub="%s µM" % charts.log_tick_text(dr["healthy_uM"]),
                   color=INK, dx=-13, dy=28, anchor="end")
    ax.label_point(dr["sick_uM"], dr["fold_at_sick"],
                   "cancer median", color=INK, dx=10, dy=-6,
                   sub="%s µM → %s"
                       % (charts.log_tick_text(dr["sick_uM"]),
                          _fold(dr["fold_at_sick"])))
    mx = math.sqrt(dr["healthy_uM"] * dr["sick_uM"])
    my = math.sqrt(1.0 * dr["fold_at_sick"])
    ax.text(mx, my, "chord slope %.3f = compression"
            % (dr.get("slope_chord") or 0.0),
            cls="chord", anchor="middle", dy=-13)
    return ax.svg(title="Device fold against analyte concentration")


def time_course(d):
    """The peroxide pulse, and the fold every possible read window would give."""
    tc = d["analysis"].get("time_course")
    if not tc or not tc.get("fold"):
        return None
    t_end = tc["fold"][-1][0]
    W, PH = 740, 212

    top = Axes(w=W, h=PH, left=72, right=108, top=34, bottom=26)
    cy = [p[1] for p in tc["h2o2_cyt_sick"]] + [p[1] for p in tc["h2o2_cyt_blank"]]
    top.xlim(0, t_end).ylim(0, max(cy) * 1.22)
    top.frame(ylabel="cytoplasmic H₂O₂ (µM)", xticks=[])
    top.hline(tc["K_oxyr"], color=INK3, dash="4 3")
    top.text(top.x1 - 4, top.y(tc["K_oxyr"]) - 7, "OxyR half-activation",
             cls="note", anchor="end", px=True)
    top.line(tc["h2o2_cyt_sick"], color=A, width=2.2)
    top.line(tc["h2o2_cyt_healthy"], color=A, width=1.6, dash="5 3")
    top.line(tc["h2o2_cyt_blank"], color=INK3, width=1.6)
    top.vline(tc["T_read"], color=INK2, dash="3 3", width=1.4)
    top.legend([("cancer sample", A), ("healthy sample", A, "5 3"),
                ("no sample", INK3)], y=top.y1 - 10)

    bot = Axes(w=W, h=PH + 36, left=72, right=108, top=30, bottom=58)
    fy = [p[1] for p in tc["fold"]]
    bot.xlim(0, t_end).ylim(min(fy) * 0.995, max(fy) * 1.06)
    bot.frame(xlabel="time since the sample was added  (s)",
              ylabel="fold, cancer over healthy", yfmt=_fold)
    bot.vline(tc["T_read"], color=INK2, dash="3 3", width=1.4,
              label="the window this screen uses", at=bot.y1 + 13)
    bot.line(tc["fold"], color=A, width=2.4)
    bot.dot(tc["T_read"], tc["fold_at_T"], r=5, color=A)
    bot.label_point(tc["T_read"], tc["fold_at_T"], _fold(tc["fold_at_T"]),
                    color=INK, dx=-9, dy=16, anchor="end")
    bot.dot(tc["t_peak"], tc["fold_peak"], r=5, color=BAD)
    bot.label_point(tc["t_peak"], tc["fold_peak"],
                    "best: %s" % _fold(tc["fold_peak"]),
                    sub="at %.1f× the window" % tc["peak_over_T"],
                    color=BAD, dx=-11, dy=24, anchor="end")
    return compose(W, PH + PH + 36,
                   [top.group(0, 0), bot.group(0, PH)],
                   title="Peroxide pulse and the fold at every read window")


# --------------------------------------------------- what the reader can tell

def distributions(d):
    """The two cohorts at the reader, with both error tails shaded."""
    sep = [s for s in d["analysis"]["separation"] if s.get("distributions")]
    if not sep:
        return None
    s = sep[0]
    di = s["distributions"]
    cut = s["cutoff_fold"]
    xs = [p[0] for p in di["healthy"]]
    ymax = max([p[1] for p in di["healthy"]] + [p[1] for p in di["sick"]])

    ax = Axes(w=720, h=398, left=64, right=44, top=70, bottom=62, xlog=True)
    ax.xlim(min(xs), max(xs)).ylim(0, ymax * 1.16)
    ax.frame(xlabel="what the reader sees, relative to the healthy median",
             ylabel="share of patients", yticks=[], xfmt=_fold)

    hi_tail = [p for p in di["healthy"] if p[0] >= cut]
    lo_tail = [p for p in di["sick"] if p[0] <= cut]
    ax.area(di["healthy"], 0, A, 0.13)
    ax.area(di["sick"], 0, B, 0.13)
    if hi_tail:
        ax.area(hi_tail, 0, A, 0.42)
    if lo_tail:
        ax.area(lo_tail, 0, B, 0.42)
    ax.line(di["healthy"], color=A, width=2.2)
    ax.line(di["sick"], color=B, width=2.2)
    ax.vline(cut, color=INK, dash="4 3", width=1.6)

    ax.text(ax.x(cut), ax.y1 - 26, "cut-off %s" % _fold(cut), cls="ptlab",
            anchor="middle", px=True)
    ax.text(ax.x(cut), ax.y1 - 12,
            "sensitivity = specificity = %.0f%%" % (100 * s["equal_error"]),
            cls="note", anchor="middle", px=True)
    ax.legend([("healthy cohort", A), ("cancer cohort", B)], y=ax.y1 - 44)
    ax.text(ax.x(cut) + 7, ax.y0 - 34, "false positives", cls="note", px=True)
    ax.text(ax.x(cut) - 7, ax.y0 - 34, "missed cancers", cls="note",
            anchor="end", px=True)
    return ax.svg(title="The two cohorts as the reader sees them")


def roc(d):
    """ROC before and after the device, for the best module of each biomarker."""
    sep = d["analysis"]["separation"]
    if not sep:
        return None
    # one entry per biomarker: four oxidases within 0.001 of each other are one
    # curve, not four, and drawing them four times says the opposite
    pick, seen = [], set()
    for s in sep:
        if s["biomarker"] in seen:
            continue
        seen.add(s["biomarker"])
        pick.append(s)
    pick = pick[:3]
    hues = [A, B, C]

    ax = Axes(w=560, h=584, left=66, right=24, top=34, bottom=156)
    ax.xlim(0, 1).ylim(0, 1)
    ax.frame(ylabel="true positives  (sensitivity)",
             xgrid=True, xfmt=_pct, yfmt=_pct)
    ax.text((ax.x0 + ax.x1) / 2.0, ax.y0 + 38,
            "false positives  (1 − specificity)", cls="axt",
            anchor="middle", px=True)
    ax.line([(0, 0), (1, 1)], color=AXIS, width=1.5, dash="5 4")
    ax.text(ax.x(0.62), ax.y(0.56), "no better than chance", cls="note",
            anchor="start", dy=-4)

    legend, y = [], ax.y0 + 88
    for s, col in zip(pick, hues):
        if s["clinical"].get("roc"):
            ax.line(s["clinical"]["roc"], color=col, width=1.6, dash="5 3",
                    opacity=0.85)
        if s["device"].get("roc"):
            ax.line(s["device"]["roc"], color=col, width=2.4)
        yd = s["equal_error"]
        if yd:
            ax.dot(1.0 - yd, yd, r=4.5, color=col)
        ax.over.append(
            "<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='%s' "
            "stroke-width='2.6' stroke-linecap='round'/>"
            % (ax.x0, y - 4, ax.x0 + 16, y - 4, col))
        ax.over.append(
            "<text class='lgd' x='%.1f' y='%.1f'>%s · %s</text>"
            % (ax.x0 + 23, y, charts.esc(s["biomarker"]),
               charts.esc(s["protein"])))
        ax.over.append(
            "<text class='lgdsub' x='%.1f' y='%.1f'>AUC %.3f at the reader, "
            "%.3f in the clinic</text>"
            % (ax.x0 + 23, y + 14, s["device"]["auc"], s["clinical"]["auc"]))
        y += 34
    ax.over.append(
        "<text class='note' x='%.1f' y='%.1f'>solid: at the reader · "
        "dashed: the cohorts themselves · dot: equal error rate</text>"
        % (ax.x0, ax.y0 + 66))
    return ax.svg(title="ROC curves before and after the device")


def auc_ladder(d):
    """What each module gives up between the cohort and the reader."""
    sep = d["analysis"]["separation"]
    if len(sep) < 2:
        return None
    thr = d["thresholds"]["auc_pass_min"]
    vals = [s["clinical"]["auc"] for s in sep] + \
           [s["device"]["auc"] for s in sep] + [thr]
    lo, hi = min(vals) - 0.03, max(vals) + 0.03
    n = len(sep)

    ax = Axes(w=720, h=66 + 40 * n, left=238, right=92, top=40, bottom=52)
    ax.xlim(lo, hi).ylim(n - 0.5, -0.5)
    ax.frame(xlabel="AUC", ygrid=False, xgrid=True, xfmt=_auc, yticks=[])
    ax.vline(thr, color=INK3, dash="4 3", width=1.4,
             label="screen’s pass mark", at=ax.y1 - 14)
    for i, s in enumerate(sep):
        c, v = s["clinical"]["auc"], s["device"]["auc"]
        y = ax.y(i)
        ax.marks.append(
            "<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='%s' "
            "stroke-width='2.4' opacity='.4' stroke-linecap='round'/>"
            % (ax.x(min(c, v)), y, ax.x(max(c, v)), y, INK3))
        ax.dot(c, i, r=4.5, color=INK3, shape="diamond")
        ax.dot(v, i, r=4.5, color=GOOD if v >= thr else BAD)
        ax.over.append("<text class='rowlab2' x='%.1f' y='%.1f'>%s</text>"
                       % (ax.x0 - 226, y, charts.esc(s["biomarker"])))
        ax.over.append("<text class='rownote2' x='%.1f' y='%.1f'>%s</text>"
                       % (ax.x0 - 226, y + 13, charts.esc(s["protein"])))
        ax.over.append("<text class='rownote2' x='%.1f' y='%.1f'>c = "
                       "%.2f</text>" % (ax.x1 + 8, y + 4,
                                        s["device"]["compression"]))
    ax.over.append("<text class='note' x='%.1f' y='%.1f'>◇ the cohorts "
                   "themselves · ● what the reader achieves · "
                   "c: fraction of the log difference that survives</text>"
                   % (ax.x0 - 226, ax.y1 - 16))
    return ax.svg(title="AUC in the clinic against AUC at the reader")


# --------------------------------------------------------------------- panels

def panel_rho(d):
    """Panel AUC across every correlation its markers could have."""
    curves = d["analysis"].get("panel_rho") or []
    if not curves:
        return None
    p = curves[0]
    xs = [q[0] for q in p["curve"]]
    ys = [q[1] for q in p["curve"]]
    lo = min(ys + [p["best_single"]]) - 0.006
    hi = max(ys + [p["best_single"]]) + 0.006

    ax = Axes(w=700, h=360, left=72, right=150, top=40, bottom=60)
    ax.xlim(min(xs), max(xs)).ylim(lo, hi)
    ax.frame(xlabel="correlation between the two markers in the same patient "
                    "(ρ, never measured)",
             ylabel="panel AUC", yfmt=lambda v, _=None: "%.3f" % v, xgrid=True)
    ax.line(p["curve"], color=A, width=2.4)
    ax.hline(p["best_single"], color=B, dash="5 4",
             label="best single marker alone", anchor="start")
    ax.dot(p["rho_worst"], p["auc_worst"], r=5.5, color=BAD)
    ax.label_point(p["rho_worst"], p["auc_worst"],
                   "worst case %.3f" % p["auc_worst"],
                   sub="the verdict is read here", color=BAD, dx=10, dy=18)
    ax.dot(xs[0], ys[0], r=5, color=A)
    ax.label_point(xs[0], ys[0], "%.3f if independent" % ys[0],
                   color=INK2, dx=10, dy=-6)
    return ax.svg(title="Panel AUC against the unmeasured correlation")


# -------------------------------------------------------------------- chassis

def oxyr(d):
    """Where each strain sits on the OxyR curve before the sample arrives."""
    o = d["analysis"].get("oxyr")
    if not o or not o.get("curve"):
        return None
    xs = [p[0] for p in o["curve"]]

    ax = Axes(w=700, h=360, left=72, right=118, top=38, bottom=62, xlog=True)
    ax.xlim(min(xs), max(xs)).ylim(0, 1.08)
    ax.frame(xlabel="resting cytoplasmic H₂O₂  (µM)",
             ylabel="OxyR activated", yfmt=_pct,
             yticks=[0, .25, .5, .75, 1.0])
    ax.line(o["curve"], color=A, width=2.4)
    ax.vline(o["K_oxyr"], color=INK3, dash="4 3", width=1.4,
             label="K = %s µM" % charts.log_tick_text(o["K_oxyr"]),
             at=ax.y(0.55), anchor="end")
    for key, col, dx, anchor in (("wildtype", GOOD, 12, "start"),
                                 ("knockout", BAD, -12, "end")):
        s = o[key]
        ax.dot(s["h2o2"], s["activation"], r=5.5, color=col)
        ax.label_point(s["h2o2"], s["activation"], s["label"],
                       sub="%.0f%% on, %.0f%% of the range left"
                           % (100 * s["activation"], 100 * s["headroom"]),
                       color=col, dx=dx, dy=-8, anchor=anchor)
    return ax.svg(title="OxyR activation against resting peroxide")


# --------------------------------------------------------- sensitivity analysis

def tornado(d):
    """How far the verdict moves when one input is halved or doubled."""
    t = d["analysis"].get("tornado")
    if not t or not t.get("rows"):
        return None
    rows = t["rows"]
    n = len(rows)
    base = t["base_auc"]
    vals = [base] + [r["auc_low"] for r in rows] + [r["auc_high"] for r in rows]
    lo, hi = min(vals) - 0.004, max(vals) + 0.004

    ax = Axes(w=760, h=112 + 27 * n, left=252, right=96, top=52, bottom=96)
    ax.xlim(lo, hi).ylim(n - 0.5, -0.5)
    ax.frame(xlabel="AUC of the whole screen, recomputed", ygrid=False,
             xgrid=True, xfmt=lambda v, _=None: "%.3f" % v, yticks=[])
    ax.vline(base, color=INK, dash=None, width=1.4)
    ax.text(ax.x(base), ax.y1 - 16, "as configured: %.3f" % base,
            cls="ptlab", anchor="middle", px=True)

    for i, r in enumerate(rows):
        y = ax.y(i)
        col = GROUP_COLOR.get(r["chosen_by"], A)
        a, b = sorted((r["auc_low"], r["auc_high"]))
        ax.marks.append("<rect x='%.1f' y='%.1f' width='%.1f' height='11' "
                        "rx='2.5' fill='%s' opacity='.72'/>"
                        % (ax.x(a), y - 5.5, max(ax.x(b) - ax.x(a), 1.2), col))
        ax.over.append("<text class='rowlab2' x='%.1f' y='%.1f'>%s</text>"
                       % (ax.x0 - 240, y + 4, charts.esc(r["meaning"])))
        unit = (" " + r["unit"]) if r["unit"] else ""
        ax.over.append("<text class='rownote2' x='%.1f' y='%.1f'>%s%s</text>"
                       % (ax.x1 + 8, y + 4,
                          charts.esc(charts.compact(r["value"])),
                          charts.esc(unit)))
    ax.legend([("the operator chooses", A), ("the module’s own kinetics", B),
               ("the chassis", C)], x=ax.x0 - 240, y=ax.y0 + 80, swatch="dot")
    ax.over.append("<text class='note' x='%.1f' y='%.1f'>each bar spans the "
                   "result with that one input divided and multiplied by "
                   "%g</text>" % (ax.x0 - 240, ax.y0 + 56, t["factor"]))
    return ax.svg(title="One-at-a-time sensitivity of the screen's AUC")


def scaling(d):
    """Measured scaling exponents against the ones the closed form predicts."""
    sc = d["analysis"].get("scaling") or []
    sc = [s for s in sc if s.get("rows")]
    if not sc:
        return None
    params = [r["param"] for r in sc[0]["rows"]]
    meaning = {r["param"]: r["meaning"] for r in sc[0]["rows"]}
    predicted = {r["param"]: r["predicted"] for r in sc[0]["rows"]}
    n = len(params)
    got = [[next((r for r in s["rows"] if r["param"] == p), None) for p in params]
           for s in sc]
    flat = [r["measured"] for g in got for r in g if r] + \
           list(predicted.values())
    lo, hi = min(flat) - 0.4, max(flat) + 0.5

    ax = Axes(w=740, h=150 + 42 * n, left=236, right=120, top=54, bottom=116)
    ax.xlim(lo, hi).ylim(n - 0.5, -0.5)
    ax.frame(ygrid=False, xgrid=True, xfmt=_signed, yticks=[])
    ax.text((ax.x0 + ax.x1) / 2.0, ax.y0 + 36,
            "exponent: how S/B scales with that parameter", cls="axt",
            anchor="middle", px=True)
    ax.vline(0, color=AXIS, dash=None, width=1.4)
    hues = [A, B, C]
    for i, p in enumerate(params):
        y = ax.y(i)
        ax.dot(predicted[p], i, r=5.5, color=INK, shape="square", ring=False)
        agree = True
        for s, g, col in zip(sc, got, hues):
            r = g[i]
            if not r:
                continue
            ax.marks.append(
                "<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='%s' "
                "stroke-width='1.4' opacity='.4' stroke-dasharray='3 3'/>"
                % (ax.x(predicted[p]), y, ax.x(r["measured"]), y, col))
            ax.dot(r["measured"], i, r=4.5, color=col)
            agree = agree and r["holds"]
        ax.over.append("<text class='rowlab2' x='%.1f' y='%.1f'>%s</text>"
                       % (ax.x0 - 224, y, charts.esc(meaning[p])))
        ax.over.append("<text class='rownote2' x='%.1f' y='%.1f'>%s</text>"
                       % (ax.x0 - 224, y + 13, charts.esc(p)))
        ax.over.append("<text class='%s' x='%.1f' y='%.1f'>%s</text>"
                       % ("holds" if agree else "breaks", ax.x1 + 8, y + 4,
                          "confirmed" if agree else "not confirmed"))
    # stacked, not in a row: three labels of this length ran past the right
    # edge of the figure and the third one disappeared entirely
    items = [("predicted by the closed form", INK)]
    items += [(s["label"], c) for s, c in zip(sc, hues)]
    for i, item in enumerate(items):
        ax.legend([item], x=ax.x0 - 224, y=ax.y0 + 56 + i * 17, swatch="dot")
    return ax.svg(title="Predicted against measured scaling exponents")


# ------------------------------------------------------- choosing the enzyme

def enzyme_charts(d, biomarker):
    """Efficiency against what it buys, and against what it saves.

    These two were the last charts on the page drawn by hand, and they showed
    it: one axis in powers of ten while its neighbour counted in decimals, no
    axis titles, a y scale with three ticks on it. The argument they carry is
    worth making properly, because it is the one a wet lab is most likely to
    get backwards - a better enzyme looks like more signal and is not.
    """
    rows = [r for r in d.get("enzyme_loading", []) if r.get("efficiency")]
    if len(rows) < 2:
        return None
    mine = [r for r in rows if r["biomarker"] == biomarker and r.get("device_fold")]
    W, H, PW = 900, 320, 416

    def effs(items):
        return [r["efficiency"] for r in items]

    left = None
    if len(mine) > 1:
        folds = [r["device_fold"] for r in mine]
        lo, hi = min(folds), max(folds)
        pad = max((hi - lo) * 0.45, hi * 0.004)
        left = Axes(w=PW, h=H, left=72, right=22, top=38, bottom=64, xlog=True)
        left.xlim(min(effs(mine)), max(effs(mine)), pad=0.22)
        left.ylim(lo - pad, hi + pad)
        left.frame(xlabel=EFF_AXIS, ylabel="fold this module delivers",
                   yfmt=_fold)
        left.band(lo, hi, A, 0.10, axis="y")
        for i, r in enumerate(sorted(mine, key=lambda x: x["efficiency"])):
            left.dot(r["efficiency"], r["device_fold"], r=5, color=A)
            left.label_point(r["efficiency"], r["device_fold"], r["protein"],
                             color=INK2, dx=0, dy=-13 if i % 2 == 0 else 22,
                             anchor="middle")

    right = Axes(w=PW, h=H, left=76, right=22, top=38, bottom=64,
                 xlog=True, ylog=True)
    es = effs(rows)
    ms = [r["min_enzyme_uM"] for r in rows if r.get("min_enzyme_uM")]
    right.xlim(min(es), max(es), pad=0.22).ylim(min(ms), max(ms), pad=0.22)
    right.frame(xlabel=EFF_AXIS, ylabel="enzyme needed  (\u00b5M)")
    # the 1/efficiency line the points should lie on, anchored at the first
    ref = sorted([r for r in rows if r.get("min_enzyme_uM")],
                 key=lambda x: x["efficiency"])
    if len(ref) > 1:
        k = ref[0]["efficiency"] * ref[0]["min_enzyme_uM"]
        xs = [ref[0]["efficiency"], ref[-1]["efficiency"]]
        right.line([(x, k / x) for x in xs], color=INK3, width=1.4, dash="5 4")
        right.text(xs[-1], k / xs[-1], "slope \u22121", cls="note",
                   anchor="end", dx=-6, dy=-8)
    for r in ref:
        right.dot(r["efficiency"], r["min_enzyme_uM"], r=4.5, color=B)

    groups = []
    if left is not None:
        groups.append(left.group(0, 0, label="what it buys in signal"))
    groups.append(right.group(W - PW if left is not None else 0, 0,
                              label="what it saves in enzyme"))
    return compose(W, H, groups,
                   title="Catalytic efficiency against signal and against cost")


# Written out rather than set with subscripts: there is no markup inside an SVG
# text node here, and Unicode has no subscript c, so "kcat" set that way would
# have read "keat".
EFF_AXIS = "catalytic efficiency, kcat/Km  (\u00b5M\u207b\u00b9 s\u207b\u00b9)"
