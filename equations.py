# -*- coding: utf-8 -*-
"""The page's equations, in TeX, with the symbols each one uses.

Kept in one file so an equation and its "where:" list cannot drift apart, and
so the TeX is somewhere a reader of this repository can check it against the
code that implements it. The rendering is done once by KaTeX at build time
(see tools/render_math.js and build_math.py) and cached in data/katex.json.

The names are referenced from page_layout.py. Adding one here and forgetting
to re-run build_math.py fails the build loudly rather than shipping a blank.
"""

# name -> (label above the block, TeX, [(symbol TeX, meaning), ...])
EQUATIONS = {
    "compartments": (
        "the two compartments",
        r"""\begin{aligned}
\frac{d[\mathrm{H_2O_2}]_{\text{cyt}}}{dt} &= P_{\text{endo}} + v_{\text{cyt}}
  + k_{\text{mem}}\bigl([\mathrm{H_2O_2}]_{\text{med}}
  - [\mathrm{H_2O_2}]_{\text{cyt}}\bigr)
  - k_{\text{scav}}\,[\mathrm{H_2O_2}]_{\text{cyt}} \\[2pt]
\frac{d[\mathrm{H_2O_2}]_{\text{med}}}{dt} &= v_{\text{med}}
  + \varphi\,k_{\text{mem}}\bigl([\mathrm{H_2O_2}]_{\text{cyt}}
  - [\mathrm{H_2O_2}]_{\text{med}}\bigr)
  - k_{\text{chem}}\,[\mathrm{H_2O_2}]_{\text{med}}
\end{aligned}""",
        [
            (r"[\mathrm{H_2O_2}]_{\text{cyt}},\ [\mathrm{H_2O_2}]_{\text{med}}",
             "peroxide in the cytoplasm and in the medium, &micro;M"),
            (r"P_{\text{endo}}",
             "the cell's own cytoplasmic peroxide production, &micro;M/s "
             "- the competitor, and the denominator of the whole design"),
            (r"v_{\text{cyt}},\ v_{\text{med}}",
             "enzymatic production, in whichever compartment the oxidase sits"),
            (r"k_{\text{mem}}",
             "first-order exchange across the membrane, s&#8315;&#185;"),
            (r"k_{\text{scav}}",
             "intracellular scavenging by KatG, KatE and AhpCF, s&#8315;&#185;"),
            (r"k_{\text{chem}}",
             "chemical loss of peroxide in the medium, s&#8315;&#185;; zero "
             "unless the sample matrix contributes"),
            (r"\varphi",
             "fraction of the assay volume that is cell"),
        ],
    ),
    "michaelis": (
        "production by the oxidase",
        r"v = \frac{k_{\text{cat}}\,[E]\,[S]}{K_m + [S]}",
        [
            (r"[S]", "analyte in the compartment the enzyme occupies, &micro;M"),
            (r"[E]", "enzyme concentration, &micro;M"),
            (r"k_{\text{cat}},\ K_m",
             "the module's own published constants, from data/sensors.csv"),
        ],
    ),
    "oxyr": (
        "activation, transcription, maturation",
        r"""\begin{aligned}
f_{\text{OxyR}} &= \frac{[\mathrm{H_2O_2}]_{\text{cyt}}^{\,n}}
  {K^{n} + [\mathrm{H_2O_2}]_{\text{cyt}}^{\,n}} \\[2pt]
\frac{dm}{dt} &= \beta\,f_{\text{OxyR}} + \text{leak}
  - (k_{\text{mat}} + \mu)\,m \\[2pt]
\frac{dg}{dt} &= k_{\text{mat}}\,m - \mu\,g
\end{aligned}""",
        [
            (r"f_{\text{OxyR}}", "fraction of OxyR in its activated form"),
            (r"K,\ n", "half-activation point and Hill coefficient of OxyR"),
            (r"m,\ g", "immature and mature reporter, &micro;M"),
            (r"\beta,\ \text{leak}",
             "promoter output when fully activated, and at rest"),
            (r"k_{\text{mat}}",
             "reporter maturation rate, ln2 over its half-life"),
            (r"\mu", "growth rate; the reporter is diluted, not degraded"),
        ],
    ),
    "occupancy": (
        "occupancy, module type B",
        r"\theta = \frac{\sum_i [A_i]\,/\,K_{d,i}}{1 + \sum_i [A_i]\,/\,K_{d,i}}",
        [
            (r"\theta",
             "fraction of the binding site occupied, which replaces "
             "<i>f</i><sub>OxyR</sub> above"),
            (r"[A_i],\ K_{d,i}",
             "each analyte this very protein is published as binding, with its "
             "own dissociation constant. Only analytes with a measured "
             "K<sub>d</sub> for this protein appear; nothing is assumed by "
             "analogy."),
        ],
    ),
    "closedform": (
        "the closed form",
        r"S/B \;\approx\; \frac{S_0}{\varphi\,P_{\text{endo}}\,T}",
        [
            (r"S_0", "analyte delivered into the assay"),
            (r"T", "read window, s"),
            (r"S/B",
             "signal over the blank - not the fold between a healthy and a "
             "cancer sample, which is what every verdict on this page uses"),
        ],
    ),
    "propagation": (
        "propagation to sensitivity and specificity",
        r"""\begin{aligned}
c &= \frac{\ln(\text{device fold})}{\ln(\text{clinical fold})} \\[4pt]
\sigma_{\text{reader}} &= \frac{\mathrm{CV}}{\sqrt{n}}
  \qquad
\sigma_{\text{tot}} = \sqrt{(c\,\sigma_{\text{bio}})^{2}
  + \sigma_{\text{reader}}^{2}} \\[4pt]
d &= \frac{c\,\bigl|\ln(\text{cancer}/\text{healthy})\bigr|}
  {\sigma_{\text{pooled}}}
  \qquad
\mathrm{AUC} = \Phi\!\left(\frac{d}{\sqrt{2}}\right)
\end{aligned}""",
        [
            (r"c",
             "the fraction of the log difference that survives to the reader, "
             "measured by running the module at both clinical levels"),
            (r"\sigma_{\text{bio}}",
             "the cohort's own spread on the log scale, from the published "
             "mean and spread"),
            (r"\mathrm{CV},\ n",
             "the reader's relative error per measurement and the number of "
             "replicates"),
            (r"\Phi", "the standard normal distribution function"),
        ],
    ),
    "panel": (
        "combining modules",
        r"""\begin{aligned}
d_{\text{panel}} &= \sqrt{d^{\mathsf{T}} R^{-1} d}
  \qquad R = (1-\rho)\,I + \rho\,J \\[4pt]
d_{\text{panel}}^{2} &= \frac{\sum_i d_i^{2}
  - \rho\left(\sum_i d_i\right)^{2} \big/ \bigl(1 + (k-1)\rho\bigr)}{1 - \rho}
\end{aligned}""",
        [
            (r"d_i", "each module's separation at the reader"),
            (r"R,\ \rho",
             "the correlation matrix of the markers in the same patient, "
             "assumed equal across every pair"),
            (r"k", "how many modules are in the panel"),
        ],
    ),
}


def tex_payload():
    """Everything that needs rendering, with how to set it.

    The blocks are display maths; the symbols in the "where:" list sit inside a
    sentence and have to be set inline, or each one would be centred on a line
    of its own.
    """
    out = {}
    for name, (_label, tex, where) in EQUATIONS.items():
        out[name] = {"tex": tex, "display": True}
        for i, (sym, _mean) in enumerate(where):
            out["%s.sym%d" % (name, i)] = {"tex": sym, "display": False}
    return out
