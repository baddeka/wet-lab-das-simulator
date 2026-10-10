"""
das_model.py - two-compartment model of the analyte -> H2O2 -> OxyR -> GFP branch.

Compartments : bulk medium (volume fraction ~1) and cytoplasm (fraction phi).
Units        : uM for concentration, s for time.
Cytoplasmic rates are per litre of cytoplasm, medium rates per litre of medium.

The point of the two compartments is that the endogenous H2O2 flux of E. coli
lives in the cytoplasm and is the dominant competing source; a single-compartment
model cannot express that competition.

This is the module type A branch of the platform. The ODE below is unchanged
from the single-case version; what changed is where its constants come from.
DEFAULTS is now assembled from data/platform.csv, the das_reference scenario in
data/scenarios.csv and one enzyme row of data/sensors.csv, so no constant
belonging to a particular biomarker, enzyme or disease is written here. The
scenario names the enzyme row it wants, so repointing it edits no code.
"""
import numpy as np
from scipy.integrate import solve_ivp

from sensorlab import data as _data

LN2 = np.log(2)


def load_defaults(scenario="das_reference"):
    """Assemble the parameter dict for one scenario out of the data files."""
    platform = _data.load_platform()
    scenarios = _data.load_scenarios()
    if scenario not in scenarios:
        raise KeyError("scenario %r is not in data/scenarios.csv" % scenario)
    sc = scenarios[scenario]

    sensor = None
    if "sensor_protein" in sc:
        wanted = (sc.get("sensor_biomarker"), sc["sensor_protein"])
        matches = [s for s in _data.load_sensors()
                   if (s.biomarker, s.protein_name) == wanted]
        if not matches:
            raise KeyError("scenario %r asks for sensor %s / %s, which is not in "
                           "data/sensors.csv" % (scenario, wanted[0], wanted[1]))
        sensor = matches[0]
        for field in sensor.missing():
            raise ValueError("sensor %s is missing %s, so scenario %r cannot be "
                             "built; add the constant to sensors.csv rather than "
                             "assuming one" % (sensor.label, field, scenario))

    return _data.build_params(platform, sc, sensor)


DEFAULTS = load_defaults()


def analyte_in_biofluid(p):
    """uM of analyte in the raw biofluid.

    Takes C_raw_uM when the caller has already converted the clinical value,
    which is what the screening stages do: they resolve units through
    data/units.csv at load time, so no conversion happens inside a calculation.

    The second branch is the one deliberate exception to that rule. It is the
    original nmol/g-creatinine conversion, kept verbatim so the seventeen
    analysis scripts frozen as the regression fixture reproduce their numbers
    bit for bit. Rewriting it to route through units.csv would reorder two
    floating-point multiplications and could move the last digit of every
    frozen result, which is a bad trade for removing one factor of 1000. New
    code should pass C_raw_uM and leave this branch alone.
    """
    if p.get("C_raw_uM") is not None:
        return p["C_raw_uM"]
    return p["V_das"] * p["creatinine"] / 1000.0

def analyte_in_assay(p):
    """uM analyte presented to the assay after concentration and dilution."""
    return analyte_in_biofluid(p) * p["conc_factor"] * p["sample_frac"]

# Names used by the existing analysis scripts.
das_in_urine = analyte_in_biofluid
das_in_assay = analyte_in_assay

def interferent_in_assay(p):
    """Cross-reactive polyamines ride through the same prep, undiluted relative
    to DAS. Their level is set by the patient, not by the DAS level."""
    return p["interferent"] * p["conc_factor"] * p["sample_frac"]

def phi(p):
    return p["phi_per_OD"] * p["OD"]

def enzyme_in_medium(p, mode):
    """Effective enzyme concentration per litre of assay for medium-side modes."""
    if mode == "peri":
        return p["E"] * p["peri_frac"] * phi(p)   # limited by periplasm volume
    return p["E"]                                  # cell-free: added directly

def _rhs(t, Y, p, mode):
    S, I, x, y, m, g = np.maximum(Y, 0.0)
    f = phi(p)
    kcat, Km = p["kcat"], p["Km"]
    kI = kcat / p["selectivity"]

    if mode == "cyto":
        Sc, Ic = p["alpha"] * S, p["alpha"] * I
        den = Km + Sc + Ic
        v_cyt = (kcat * p["E"] * Sc + kI * p["E"] * Ic) / den
        v_med = 0.0
        dS = -f * kcat * p["E"] * Sc / den
        dI = -f * kI   * p["E"] * Ic / den
    else:
        Em = enzyme_in_medium(p, mode)
        den = Km + S + I
        v_cyt = 0.0
        v_med = (kcat * Em * S + kI * Em * I) / den
        dS = -kcat * Em * S / den
        dI = -kI   * Em * I / den

    dx = p["P_endo"] + v_cyt + p["k_mem"] * (y - x) - p["k_scav"] * x
    dy = v_med + f * p["k_mem"] * (x - y) - p["k_chem"] * y

    n, K = p["n_hill"], p["K_oxyr"]
    fo = x**n / (K**n + x**n)
    dm = p["beta"] * fo + p["leak"] - (p["k_mat"] + p["mu"]) * m
    dg = p["k_mat"] * m - p["mu"] * g
    return [dS, dI, dx, dy, dm, dg]

def rest_state(p):
    """Pre-assay steady state of a growing culture with no DAS present.

    Cytoplasm is quasi-steady on a millisecond timescale, so it follows the
    medium; the medium itself is slow at low cell density and must be solved."""
    f, kmem, ksc = phi(p), p["k_mem"], p["k_scav"]
    ktot = kmem + ksc
    b = f * kmem * ksc / ktot + p["k_chem"]
    y = (f * kmem * p["P_endo"] / ktot) / b
    x = (p["P_endo"] + kmem * y) / ktot
    n, K = p["n_hill"], p["K_oxyr"]
    fo = x**n / (K**n + x**n)
    m = (p["beta"] * fo + p["leak"]) / (p["k_mat"] + p["mu_pre"])
    g = p["k_mat"] * m / p["mu_pre"]
    return x, y, m, g

def simulate(p, mode="peri", with_das=True, npts=400):
    x0, y0, m0, g0 = rest_state(p)
    S0 = das_in_assay(p) if with_das else 0.0
    I0 = interferent_in_assay(p) if with_das else 0.0
    T  = p["T_read"]
    return solve_ivp(_rhs, (0.0, T), [S0, I0, x0, y0, m0, g0], args=(p, mode),
                     method="LSODA", t_eval=np.linspace(0.0, T, npts),
                     rtol=1e-9, atol=1e-14)

def response(p, mode="peri"):
    a = simulate(p, mode, True)
    b = simulate(p, mode, False)
    g_sig, g_bg = a.y[5][-1], b.y[5][-1]
    return dict(
        gfp_signal=g_sig, gfp_blank=g_bg,
        fold=g_sig / g_bg, sb=(g_sig - g_bg) / g_bg,
        h2o2_cyt_peak=a.y[2].max(), h2o2_cyt_rest=b.y[2][-1],
        h2o2_med_peak=a.y[3].max(),
        das_assay=das_in_assay(p), das_left=a.y[0][-1],
        brightness=phi(p) * g_sig, sol_signal=a, sol_blank=b,
    )

def occupancy(conc, kd, n=1.0):
    """Fraction of binding sites occupied at a given analyte concentration."""
    return conc**n / (kd**n + conc**n)

def reporter_response(p, activation, T=None):
    """GFP at the read time for a constant promoter activation fraction.

    The H2O2 stage of the type A branch above ends by handing OxyR an
    activation fraction. Module types that drive the promoter directly - a
    ligand-binding transcription factor, with no oxidase and no peroxide - enter
    here instead, with the same reporter and the same growth dilution. The
    analyte is not consumed by a transcription factor, so the activation is
    constant over the read and only the reporter has to be integrated.
    """
    k_mat, mu, mu_pre = p["k_mat"], p["mu"], p["mu_pre"]
    beta, leak = p["beta"], p["leak"]
    T = p["T_read"] if T is None else T

    m0 = leak / (k_mat + mu_pre)      # pre-assay rest state: promoter off
    g0 = k_mat * m0 / mu_pre

    def rhs(t, Y):
        m, g = np.maximum(Y, 0.0)
        return [beta * activation + leak - (k_mat + mu) * m, k_mat * m - mu * g]

    sol = solve_ivp(rhs, (0.0, T), [m0, g0], method="LSODA",
                    rtol=1e-9, atol=1e-14)
    return sol.y[1][-1]

def discriminate(p, mode="peri", v_healthy=None, v_cutoff=None):
    """Can the reader separate a healthy sample from one at the clinical cutoff?

    The two levels default to the scenario's own v_healthy and v_cutoff rather
    than to numbers written here, so this function carries no disease-specific
    constant.
    """
    v_healthy = p["v_healthy"] if v_healthy is None else v_healthy
    v_cutoff  = p["v_cutoff"]  if v_cutoff  is None else v_cutoff
    fh = response(dict(p, V_das=v_healthy), mode)["gfp_signal"]
    fc = response(dict(p, V_das=v_cutoff),  mode)["gfp_signal"]
    ratio = fc / fh
    sd = p["cv_reader"] * np.sqrt(2.0 / p["n_rep"])
    z  = np.log(ratio) / sd if sd > 0 else np.inf
    cv_max = np.log(ratio) / (2.8 * np.sqrt(2.0 / p["n_rep"])) if ratio > 1 else 0.0
    return dict(ratio=ratio, z=z, cv_max=cv_max, separable=bool(z >= 2.8),
                f_healthy=fh, f_cutoff=fc)
