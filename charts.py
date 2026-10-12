# -*- coding: utf-8 -*-
"""A small plotting kit in SVG: scales, ticks, frames, marks, legends.

Every chart on the page goes through here rather than being drawn by hand. The
first version of this page drew each figure inline, and the figures diverged:
one had gridlines and another did not, two used different label sizes, one
mixed decimal and scientific notation down a single axis, and a chart of four
discrete enzymes got a connecting line that implied interpolation. None of that
is a drawing mistake, it is the absence of a shared axis.

So the parts a reader checks a number against - where the ticks fall, how they
are written, which way the labels sit, what the units are - are decided once,
here, and every figure inherits them.

Colour comes from CSS custom properties, not from literals, so the same figure
serves light and dark mode and the palette stays in one file. Nothing in here
knows what a biosensor is.
"""
import math
import re

THIN = " "          # narrow no-break space, for digit grouping


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def tip(text):
    """Markup for a hover readout: a native title and a styled one.

    The <title> works with no JavaScript, in print preview and for a screen
    reader; the data attribute is what the page's own tooltip reads, because the
    native one waits a second and arrives in the operating system's styling.
    Both carry the same string, so they cannot disagree.
    """
    if not text:
        return "", ""
    return " data-tip='%s'" % esc(text), "<title>%s</title>" % esc(text)


def _dash(d):
    """A dash pattern, or nothing at all - never the string 'None'.

    A solid rule is requested as dash=None, and formatting that straight into
    the attribute produced stroke-dasharray='None' on four rules across the
    page. Browsers ignore an invalid pattern and draw the line solid, so it
    looked right and was wrong, which is the kind of mistake only a test for
    the word None in the markup catches.
    """
    return " stroke-dasharray='%s'" % d if d else ""


# ------------------------------------------------------------------ numbers

def tick_text(v, step=None):
    """A tick label: short, consistent down one axis, and never exponential.

    Digits are grouped with a thin space rather than pushed into 10^n, because
    an axis that mixes 0.34 with 5.6x10^-4 makes two neighbouring ticks
    impossible to compare at a glance. Below a thousandth the exponent is
    unavoidable and is written out properly.
    """
    if v is None:
        return ""
    a = abs(v)
    if a == 0:
        return "0"
    if a < 1e-4:
        m, ex = ("%.0e" % v).split("e")
        return "%s×10%s" % (m, _sup(int(ex)))
    if a >= 1000:
        s = "%.0f" % v
        out, n = "", len(s.lstrip("-"))
        neg = s.startswith("-")
        s = s.lstrip("-")
        for i, ch in enumerate(s):
            if i and (n - i) % 3 == 0:
                out += THIN
            out += ch
        return ("-" if neg else "") + out
    # decimals: enough places for the step, never more
    if step:
        nd = max(0, int(math.ceil(-math.log10(abs(step)) + 0.3)))
    else:
        nd = 0 if a >= 100 else (1 if a >= 10 else (2 if a >= 1 else 3))
    return ("%." + str(nd) + "f") % v


_SUPS = {"-": "⁻", "0": "⁰", "1": "¹", "2": "²",
         "3": "³", "4": "⁴", "5": "⁵", "6": "⁶",
         "7": "⁷", "8": "⁸", "9": "⁹"}


def _sup(n):
    return "".join(_SUPS[c] for c in str(n))


def log_tick_text(v, _=None):
    """A tick on a logarithmic axis, written with the digits it needs and no more.

    tick_text picks its decimals from the step, which a log axis does not have,
    and the result was an axis reading 0.001, 0.010, 0.100, 1.00, 10.0 - five
    different formats for five ticks of one scale. Here each tick is written at
    its own magnitude, so the axis reads 0.001, 0.01, 0.1, 1, 10.
    """
    if v is None or v == 0:
        return "0"
    a = abs(v)
    if a < 1e-4 or a >= 1e5:
        m, ex = ("%.0e" % v).split("e")
        m = m.rstrip("0").rstrip(".")
        return ("%s×10%s" % (m, _sup(int(ex)))) if m != "1" \
            else "10%s" % _sup(int(ex))
    if a >= 1000:
        return tick_text(v)
    nd = max(0, int(math.ceil(-math.log10(a) + 1e-9)))
    s = ("%." + str(nd) + "f") % v
    return s.rstrip("0").rstrip(".") if "." in s else s


def compact(v, n=3):
    """Three significant figures with no trailing zeros, for a column of values.

    A column listing 1 800 s, 1.00, 700 s-1, 0.100 uM, 0.050 OD600 and 26.0 s-1
    is six formats for six numbers. Stripping the zeros that carry no precision
    leaves 1 800, 1, 700, 0.1, 0.05, 26, which can be read down.
    """
    if v is None:
        return "-"
    if v == 0:
        return "0"
    a = abs(v)
    if a >= 1e5 or a < 1e-4:
        return tick_text(v)
    if a >= 1000:
        return tick_text(round(v))
    s = ("%." + str(n) + "g") % v
    if "e" in s or "E" in s:
        return tick_text(v)
    return s


def sci_tick_text(v, _=None):
    """A power of ten, for an axis that spans too many decades to spell out."""
    if v is None or v == 0:
        return "0"
    ex = int(round(math.log10(abs(v))))
    m = v / (10.0 ** ex)
    head = "" if abs(m - 1.0) < 1e-6 else ("%g×" % m)
    return "%s10%s" % (head, _sup(ex))


def _log_fmt(ticks):
    """Spelled-out decimals where they stay short, powers of ten otherwise."""
    vals = [abs(v) for v in ticks if v]
    if vals and (min(vals) < 1e-3 or max(vals) >= 1e5):
        return sci_tick_text
    return log_tick_text


def nice_linear(lo, hi, target=5):
    """Ticks at a round step covering [lo, hi], between 3 and 8 of them.

    An empty list for an inverted range, not a single tick at the bottom. The
    row-based figures set ylim backwards on purpose - row 0 at the top - and a
    lone tick labelled "31.5" turned up on the axis of the forest plot because
    this used to return [lo] for that case.
    """
    if hi <= lo:
        return []
    raw = (hi - lo) / float(target)
    mag = 10.0 ** math.floor(math.log10(raw))
    for m in (1.0, 2.0, 2.5, 5.0, 10.0):
        if raw <= m * mag:
            step = m * mag
            break
    else:
        step = 10.0 * mag
    first = math.ceil(lo / step - 1e-9) * step
    out, v = [], first
    while v <= hi + 1e-9 * max(1.0, abs(hi)):
        out.append(round(v, 12))
        v += step
    return out or [lo, hi]


def log_ticks(lo, hi):
    """Decade ticks, thinned or subdivided so a short axis is still labelled."""
    if lo <= 0 or hi <= lo:
        return [], []
    a, b = math.floor(math.log10(lo)), math.ceil(math.log10(hi))
    span = math.log10(hi) - math.log10(lo)
    decades = b - a
    mantissas = [1.0]
    if span <= 0.8:
        # under a decade, 1-2-5 can leave an axis with two labels on it; the
        # distribution figure came out with only "1x" and "2x" across its whole
        # width, which is not an axis a reader can place a curve against
        mantissas = [1.0, 1.2, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    elif decades <= 2:
        mantissas = [1.0, 2.0, 5.0]
    elif decades <= 4:
        mantissas = [1.0, 3.0]
    candidates = sorted(set(mantissas)
                        | {1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0})
    major, minor = [], []
    k = a
    while k <= b:
        for m in candidates:
            v = m * 10.0 ** k
            if v < lo * 0.999 or v > hi * 1.001:
                continue
            (major if m in mantissas else minor).append(v)
        k += 1
    major.sort()
    minor.sort()
    step = max(1, int(math.ceil(len(major) / 9.0)))
    return major[::step], minor


# -------------------------------------------------------------------- axes

class Axes(object):
    """One plot area: two scales, a frame, and a stack of marks over it."""

    _serial = 0

    def __init__(self, w=700, h=320, left=66, right=20, top=16, bottom=48,
                 xlog=False, ylog=False, cls="chart"):
        # Each axis gets an id so a tick can be traced back to the one ruler it
        # belongs to. Two panels of one figure may legitimately use different
        # number formats; one axis may not, and that is the thing to test.
        Axes._serial += 1
        self.uid = Axes._serial
        self.w, self.h, self.cls = w, h, cls
        self.l, self.r, self.t, self.b = left, right, top, bottom
        self.xlog, self.ylog = xlog, ylog
        self._x = (0.0, 1.0)
        self._y = (0.0, 1.0)
        self.under, self.marks, self.over = [], [], []

    # ---- geometry
    @property
    def x0(self):
        return self.l

    @property
    def x1(self):
        return self.w - self.r

    @property
    def y0(self):
        return self.h - self.b          # bottom of the plot area

    @property
    def y1(self):
        return self.t                   # top

    def xlim(self, lo, hi, pad=0.0):
        self._x = self._padded(lo, hi, pad, self.xlog)
        return self

    def ylim(self, lo, hi, pad=0.0):
        self._y = self._padded(lo, hi, pad, self.ylog)
        return self

    @staticmethod
    def _padded(lo, hi, pad, log):
        lo, hi = float(lo), float(hi)
        if hi == lo:
            hi = lo + (abs(lo) or 1.0) * 0.1
        if not pad:
            return lo, hi
        if log:
            f = (hi / lo) ** pad
            return lo / f, hi * f
        d = (hi - lo) * pad
        return lo - d, hi + d

    def x(self, v):
        lo, hi = self._x
        if self.xlog:
            v = max(float(v), 1e-300)
            f = (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
        else:
            f = (float(v) - lo) / (hi - lo)
        return self.x0 + f * (self.x1 - self.x0)

    def y(self, v):
        lo, hi = self._y
        if self.ylog:
            v = max(float(v), 1e-300)
            f = (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
        else:
            f = (float(v) - lo) / (hi - lo)
        return self.y0 - f * (self.y0 - self.y1)

    def inside(self, px, py):
        return self.x0 - .5 <= px <= self.x1 + .5 and \
               self.y1 - .5 <= py <= self.y0 + .5

    # ---- structure
    def frame(self, xlabel=None, ylabel=None, xticks=None, yticks=None,
              xfmt=None, yfmt=None, xgrid=False, ygrid=True, xminor=True,
              ytickside="left", xrotate=False):
        """Gridlines, baselines, ticks and axis titles, all at once."""
        g = []
        xt, xmin = self._ticks(self._x, self.xlog, xticks)
        yt, ymin = self._ticks(self._y, self.ylog, yticks)
        xstep = (xt[1] - xt[0]) if len(xt) > 1 and not self.xlog else None
        ystep = (yt[1] - yt[0]) if len(yt) > 1 and not self.ylog else None

        if self.xlog and xminor:
            for v in xmin:
                px = self.x(v)
                g.append("<line class='gridmin' x1='%.1f' y1='%.1f' x2='%.1f' "
                         "y2='%.1f'/>" % (px, self.y1, px, self.y0))
        if ygrid:
            for v in yt:
                py = self.y(v)
                g.append("<line class='grid' x1='%.1f' y1='%.1f' x2='%.1f' "
                         "y2='%.1f'/>" % (self.x0, py, self.x1, py))
        if xgrid:
            for v in xt:
                px = self.x(v)
                g.append("<line class='grid' x1='%.1f' y1='%.1f' x2='%.1f' "
                         "y2='%.1f'/>" % (px, self.y1, px, self.y0))

        g.append("<line class='spine' x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f'/>"
                 % (self.x0, self.y0, self.x1, self.y0))
        g.append("<line class='spine' x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f'/>"
                 % (self.x0, self.y1, self.x0, self.y0))

        # One format per axis, chosen from the whole tick set. Deciding per
        # tick let a single axis read 10, 1, 0.1, 0.01, 0.001, 0.0001, 10^-5:
        # six decimals and one exponent, which is two scales on one ruler.
        xdef = _log_fmt(xt) if self.xlog else tick_text
        ydef = _log_fmt(yt) if self.ylog else tick_text
        for v in xt:
            px = self.x(v)
            lab = xdef(v, xstep) if xfmt is None else xfmt(v)
            g.append("<line class='tickmark' x1='%.1f' y1='%.1f' x2='%.1f' "
                     "y2='%.1f'/>" % (px, self.y0, px, self.y0 + 4))
            if xrotate:
                g.append("<text class='tick' data-ax='%dx' "
                         "transform='translate(%.1f,%.1f) rotate(-38)' "
                         "text-anchor='end'>%s</text>"
                         % (self.uid, px, self.y0 + 16, esc(lab)))
            else:
                g.append("<text class='tick' data-ax='%dx' x='%.1f' y='%.1f' "
                         "text-anchor='middle'>%s</text>"
                         % (self.uid, px, self.y0 + 18, esc(lab)))
        for v in yt:
            py = self.y(v)
            lab = ydef(v, ystep) if yfmt is None else yfmt(v)
            if ytickside == "left":
                g.append("<text class='tick' data-ax='%dy' x='%.1f' y='%.1f' "
                         "text-anchor='end'>%s</text>"
                         % (self.uid, self.x0 - 9, py + 4, esc(lab)))
            else:
                g.append("<text class='tick' data-ax='%dy' x='%.1f' "
                         "y='%.1f'>%s</text>"
                         % (self.uid, self.x1 + 9, py + 4, esc(lab)))

        if xlabel:
            g.append("<text class='axt' x='%.1f' y='%.1f' text-anchor='middle'>"
                     "%s</text>" % ((self.x0 + self.x1) / 2.0,
                                    self.h - 6, esc(xlabel)))
        if ylabel:
            g.append("<text class='axt' transform='translate(13,%.1f) "
                     "rotate(-90)' text-anchor='middle'>%s</text>"
                     % ((self.y0 + self.y1) / 2.0, esc(ylabel)))
        self.under = g + self.under
        return self

    def _ticks(self, lim, log, given):
        lo, hi = lim
        if given is not None:
            return list(given), []
        if log:
            return log_ticks(lo, hi)
        return nice_linear(lo, hi), []

    # ---- marks
    def line(self, pts, color="var(--series-a)", width=2.0, dash=None,
             opacity=None, clip=True, tip=None):
        d = self._d(pts, clip)
        if not d:
            return self
        at, ti = globals()["tip"](tip)
        self.marks.append(
            "<path d='%s' fill='none' stroke='%s' stroke-width='%g' "
            "stroke-linecap='round' stroke-linejoin='round'%s%s%s>%s</path>"
            % (d, color, width,
               " stroke-dasharray='%s'" % dash if dash else "",
               " opacity='%g'" % opacity if opacity is not None else "",
               at, ti))
        return self

    def hover_along(self, pts, label, every=None, r=9):
        """Invisible targets along a curve, so a value can be read off it.

        A drawn line is two pixels wide and a curve is not a thing anyone can
        point at. These are transparent circles on the path - wide enough to
        hit, sampled rather than one per point, each carrying the reading at
        that place.
        """
        usable = [(vx, vy) for vx, vy in pts if vx is not None and vy is not None]
        if not usable:
            return self
        every = every or max(1, len(usable) // 18)
        for vx, vy in usable[::every]:
            px, py = self.x(vx), self.y(vy)
            if not self.inside(px, py):
                continue
            at, ti = globals()["tip"](label(vx, vy))
            self.marks.append("<circle cx='%.1f' cy='%.1f' r='%g' fill='none' "
                              "pointer-events='all'%s>%s</circle>"
                              % (px, py, r, at, ti))
        return self

    def area(self, pts, base, color="var(--series-a)", opacity=0.13, clip=True):
        d = self._d(pts, clip)
        if not d:
            return self
        xs = [p[0] for p in pts]
        d += " L%.1f,%.1f L%.1f,%.1f Z" % (self.x(xs[-1]), self.y(base),
                                           self.x(xs[0]), self.y(base))
        self.marks.append("<path d='%s' fill='%s' opacity='%g' stroke='none'/>"
                          % (d, color, opacity))
        return self

    def _d(self, pts, clip):
        out, pen = [], False
        for vx, vy in pts:
            if vy is None or vx is None:
                pen = False
                continue
            px, py = self.x(vx), self.y(vy)
            if clip and not self.inside(px, py):
                pen = False
                continue
            out.append("%s%.1f,%.1f" % ("L" if pen else "M", px, py))
            pen = True
        return "".join(out)

    def dot(self, vx, vy, r=4.0, color="var(--series-a)", ring=True,
            shape="circle", tip=None):
        px, py = self.x(vx), self.y(vy)
        ringattr = (" stroke='var(--surface-1)' stroke-width='2'" if ring else "")
        at, ti = globals()["tip"](tip)
        if shape == "diamond":
            s = r * 1.25
            self.marks.append(
                "<path d='M%.1f,%.1f L%.1f,%.1f L%.1f,%.1f L%.1f,%.1f Z' "
                "fill='%s'%s%s>%s</path>"
                % (px, py - s, px + s, py, px, py + s, px - s, py, color,
                   ringattr, at, ti))
        elif shape == "square":
            self.marks.append("<rect x='%.1f' y='%.1f' width='%.1f' "
                              "height='%.1f' rx='1.5' fill='%s'%s%s>%s</rect>"
                              % (px - r, py - r, 2 * r, 2 * r, color, ringattr,
                                 at, ti))
        else:
            self.marks.append("<circle cx='%.1f' cy='%.1f' r='%g' fill='%s'%s%s>"
                              "%s</circle>"
                              % (px, py, r, color, ringattr, at, ti))
        return self

    def vline(self, vx, color="var(--ink-3)", dash="4 3", width=1.5,
              label=None, at=None, anchor="start", cls="note"):
        px = self.x(vx)
        self.marks.append(
            "<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='%s' "
            "stroke-width='%g'%s/>"
            % (px, self.y1, px, self.y0, color, width, _dash(dash)))
        if label:
            dx = 5 if anchor == "start" else -5
            self.over.append("<text class='%s' x='%.1f' y='%.1f' "
                             "text-anchor='%s'>%s</text>"
                             % (cls, px + dx,
                                self.y1 + 12 if at is None else at,
                                anchor, esc(label)))
        return self

    def hline(self, vy, color="var(--ink-3)", dash="4 3", width=1.5,
              label=None, anchor="end", cls="note"):
        py = self.y(vy)
        self.marks.append(
            "<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='%s' "
            "stroke-width='%g'%s/>"
            % (self.x0, py, self.x1, py, color, width, _dash(dash)))
        if label:
            x = self.x1 - 4 if anchor == "end" else self.x0 + 4
            self.over.append("<text class='%s' x='%.1f' y='%.1f' "
                             "text-anchor='%s'>%s</text>"
                             % (cls, x, py - 6, anchor, esc(label)))
        return self

    def band(self, lo, hi, color="var(--series-a)", opacity=0.10, axis="x"):
        if axis == "x":
            a, b = self.x(lo), self.x(hi)
            self.under.append("<rect x='%.1f' y='%.1f' width='%.1f' "
                              "height='%.1f' fill='%s' opacity='%g'/>"
                              % (min(a, b), self.y1, abs(b - a),
                                 self.y0 - self.y1, color, opacity))
        else:
            a, b = self.y(lo), self.y(hi)
            self.under.append("<rect x='%.1f' y='%.1f' width='%.1f' "
                              "height='%.1f' fill='%s' opacity='%g'/>"
                              % (self.x0, min(a, b), self.x1 - self.x0,
                                 abs(b - a), color, opacity))
        return self

    def text(self, vx, vy, s, cls="note", anchor="start", dx=0, dy=0,
             px=False):
        X, Y = (vx, vy) if px else (self.x(vx), self.y(vy))
        self.over.append("<text class='%s' x='%.1f' y='%.1f' text-anchor='%s'>"
                         "%s</text>" % (cls, X + dx, Y + dy, anchor, esc(s)))
        return self

    def label_point(self, vx, vy, s, color=None, anchor="start", dx=8, dy=4,
                    sub=None):
        """A direct label on a mark, which is how identity survives in print."""
        px, py = self.x(vx) + dx, self.y(vy) + dy
        style = " fill='%s'" % color if color else ""
        self.over.append("<text class='ptlab' x='%.1f' y='%.1f' "
                         "text-anchor='%s'%s>%s</text>"
                         % (px, py, anchor, style, esc(s)))
        if sub:
            self.over.append("<text class='ptsub' x='%.1f' y='%.1f' "
                             "text-anchor='%s'>%s</text>"
                             % (px, py + 14, anchor, esc(sub)))
        return self

    def legend(self, items, x=None, y=None, gap=17, swatch="line"):
        """A key above the plot. Always present once there are two series.

        An item may carry its own dash pattern as a third element. Without it,
        the time course drew a solid swatch for a series that is dashed on the
        plot, which is a legend that misidentifies its own curve.
        """
        px = self.x0 if x is None else x
        py = (self.y1 - 8) if y is None else y
        for item in items:
            label, color = item[0], item[1]
            dash = item[2] if len(item) > 2 else None
            if swatch == "dot":
                self.over.append("<circle cx='%.1f' cy='%.1f' r='4' "
                                 "fill='%s'/>" % (px + 5, py - 4, color))
            else:
                self.over.append(
                    "<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='%s' "
                    "stroke-width='2.5' stroke-linecap='round'%s/>"
                    % (px, py - 4, px + 16, py - 4, color, _dash(dash)))
            self.over.append("<text class='lgd' x='%.1f' y='%.1f'>%s</text>"
                             % (px + 22, py, esc(label)))
            px += 22 + 7.2 * len(label) + gap
        return self

    # ---- output
    def group(self, dx=0, dy=0, label=None):
        """This plot as a positioned group, for stacking panels in one figure.

        Panels that belong to one argument - a peroxide pulse and the fold it
        produces, say - share an x axis and have to be read together, so they
        belong in one figure with one caption rather than in two.
        """
        parts = ["<g transform='translate(%g,%g)'>" % (dx, dy)]
        if label:
            parts.append("<text class='panlab' x='%.1f' y='%.1f'>%s</text>"
                         % (self.x0, self.y1 - 14, esc(label)))
        parts += self.under + self.marks + self.over
        parts.append("</g>")
        return "".join(parts)

    def svg(self, title=None, desc=None):
        # max-width at the natural width, so a chart narrower than the column
        # is not scaled up. Without it a 560px ROC plot stretched to 1060px and
        # took its 11px tick labels to 21px with it: the figure looked enlarged
        # rather than designed, and every label on the page was a different
        # size depending on how wide its chart happened to be.
        head = ("<svg class='%s' viewBox='0 0 %g %g' role='img' "
                "style='max-width:%gpx' "
                "preserveAspectRatio='xMinYMin meet'"
                % (self.cls, self.w, self.h, self.w))
        head += (" aria-label='%s'" % esc(title)) if title else ""
        parts = [head + ">"]
        if desc:
            parts.append("<desc>%s</desc>" % esc(desc))
        parts += self.under + self.marks + self.over
        parts.append("</svg>")
        return "".join(parts)


def compose(w, h, groups, cls="chart", title=None):
    """One SVG holding several positioned plots."""
    head = ("<svg class='%s' viewBox='0 0 %g %g' role='img' "
            "style='max-width:%gpx' preserveAspectRatio='xMinYMin meet'"
            % (cls, w, h, w))
    head += (" aria-label='%s'" % esc(title)) if title else ""
    return head + ">" + "".join(groups) + "</svg>"


# ----------------------------------------------------------------- figures

class Numbering(object):
    """Continuous figure and table numbers, assigned in the order drawn.

    Peking's model page runs Figure 1 to Figure 35 across the whole document and
    that is the right convention: a caption that says "Figure 9" is a reference a
    reader can use, and one that says "the chart above" is not.
    """

    def __init__(self):
        self.fig = 0
        self.tab = 0
        self.figs = []
        self.tabs = []

    def figure(self, svg, caption, cls="chart", fallback=None, scroll=True,
               note=None, anchor=None):
        self.fig += 1
        n = self.fig
        aid = anchor or "fig%d" % n
        self.figs.append((n, caption, aid))
        body = svg
        if scroll:
            body = ("<div class='figscroll'>%s</div>"
                    "<p class='swipe'>Scroll the figure sideways to see all of "
                    "it.</p>" % svg)
        cap = ("<figcaption><b>Figure&nbsp;%d.</b> %s</figcaption>" % (n, caption))
        extra = ("<p class='fignote'>%s</p>" % note) if note else ""
        fb = fallback or ""
        return ("<figure class='fig %s' id='%s'>%s%s%s%s</figure>"
                % (cls, aid, body, cap, extra, fb))

    def adopt(self, html, anchor=None):
        """Give a number to a figure that already built its own caption.

        Three figures on this page predate the numbering and write their own
        captions. Rewriting them to hand their caption back would be the
        cleaner shape, but it would also mean editing three hand-drawn SVGs for
        no gain to the reader, so the number is spliced into the caption they
        already have and the contents list takes the text from there.
        """
        self.fig += 1
        n = self.fig
        aid = anchor or "fig%d" % n
        m = re.search(r"<figcaption>(.*?)</figcaption>", html, re.S)
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip() \
            if m else ""
        self.figs.append((n, text, aid))
        html = html.replace("<figcaption>",
                            "<figcaption><b>Figure&nbsp;%d.</b> " % n, 1)
        html = html.replace("<figure class=", "<figure id='%s' class=" % aid, 1)
        return html

    def table(self, html, caption, anchor=None, scroll=True):
        self.tab += 1
        n = self.tab
        aid = anchor or "tab%d" % n
        self.tabs.append((n, caption, aid))
        body = ("<div class='scroll'>%s</div>" % html) if scroll else html
        return ("<figure class='tbl' id='%s'><figcaption><b>Table&nbsp;%d.</b> "
                "%s</figcaption>%s</figure>" % (aid, n, caption, body))
