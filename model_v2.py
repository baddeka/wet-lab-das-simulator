"""
Two-compartment model of the DAS -> H2O2 -> OxyR -> GFP branch.
Units: concentrations in uM, time in s. Cytoplasmic quantities are per litre of
cytoplasm; medium quantities are per litre of medium.
"""
import numpy as np
from scipy.integrate import solve_ivp

P = dict(
    # --- geometry / culture -------------------------------------------------
    phi_per_OD = 8e-4,     # cell volume fraction at OD600 = 1
    OD         = 1.0,
    peri_frac  = 0.16,     # periplasm as fraction of cell volume

    # --- H2O2 physics -------------------------------------------------------
    k_mem   = 90.0,        # s^-1, cytoplasm <-> medium exchange (P*S/V)
    k_scav  = 700.0,       # s^-1, intracellular scavenging (KatG/KatE/AhpCF)
    P_endo  = 14.0,        # uM/s, endogenous intracellular H2O2 production
    k_chem  = 0.0,         # s^-1, chemical H2O2 loss in the medium (matrix)

    # --- enzyme -------------------------------------------------------------
    kcat = 158.0,          # s^-1     Bakke 2007
    Km   = 83.0,           # uM       colorimetric assay buffer
    E    = 1.0,            # uM, in whichever compartment the enzyme sits
    alpha= 1.0,            # DAS accumulation ratio cytoplasm/medium

    # --- OxyR ---------------------------------------------------------------
    K_oxyr = 0.10,         # uM intracellular H2O2 at half activation
    n_hill = 1.0,

    # --- reporter -----------------------------------------------------------
    beta   = 5e-3,         # uM/s max promoter output
    leak   = 2e-5,         # uM/s basal
    k_mat  = np.log(2)/360,# s^-1  sfGFP maturation, t1/2 = 6 min
    mu     = np.log(2)/2400,# s^-1 growth dilution, td = 40 min
)

def phi(p):  return p["phi_per_OD"] * p["OD"]

def rhs(t, Y, S0, p, mode):
    S, x, y, m, g = np.maximum(Y, 0.0)
    f = phi(p)
    if mode == "cyto":
        Sc = p["alpha"] * S
        v  = p["kcat"] * p["E"] * Sc / (p["Km"] + Sc)   # per L cytoplasm
        v_cyt, v_med = v, 0.0
        dS = -f * v                                     # drawn from medium pool
    else:
        # periplasmic / surface / cell-free: enzyme sees the medium directly.
        # For "peri" the effective enzyme per litre of assay is limited by what
        # the periplasm can hold; the caller passes that already scaled.
        v  = p["kcat"] * p["E"] * S / (p["Km"] + S)     # per L medium
        v_cyt, v_med = 0.0, v
        dS = -v
    dx = p["P_endo"] + v_cyt + p["k_mem"]*(y - x) - p["k_scav"]*x
    dy = v_med + f*p["k_mem"]*(x - y) - p["k_chem"]*y
    fo = x**p["n_hill"] / (p["K_oxyr"]**p["n_hill"] + x**p["n_hill"])
    dm = p["beta"]*fo + p["leak"] - (p["k_mat"] + p["mu"])*m
    dg = p["k_mat"]*m - p["mu"]*g
    return [dS, dx, dy, dm, dg]

def baseline_state(p):
    """Cytoplasmic/medium H2O2 and reporter with no DAS present."""
    f = phi(p)
    # steady state of dx,dy with v=0
    # x = (P + k_mem y)/(k_mem+k_scav); y = phi k_mem x/(phi k_mem + k_chem)
    if p["k_chem"] == 0:
        # no medium sink -> y = x
        x = p["P_endo"] / p["k_scav"]; y = x
    else:
        a = p["k_mem"] + p["k_scav"]; b = f*p["k_mem"] + p["k_chem"]
        x = p["P_endo"] * b / (a*b - f*p["k_mem"]**2)
        y = f*p["k_mem"]*x / b
    fo = x**p["n_hill"]/(p["K_oxyr"]**p["n_hill"] + x**p["n_hill"])
    m  = (p["beta"]*fo + p["leak"])/(p["k_mat"]+p["mu"])
    g  = p["k_mat"]*m/p["mu"]
    return x, y, m, g

def run(S0, p, mode="peri", T=3600.0, npts=600):
    x0, y0, m0, g0 = baseline_state(p)
    sol = solve_ivp(rhs, (0, T), [S0, x0, y0, m0, g0], args=(S0, p, mode),
                    method="LSODA", t_eval=np.linspace(0, T, npts),
                    rtol=1e-9, atol=1e-14)
    return sol

def readout(S0, p, mode="peri", T=3600.0):
    """Fluorescence signal-to-background at time T (phi cancels in the ratio)."""
    _, _, _, g_bg_ss = baseline_state(p)
    s_sig = run(S0, p, mode, T); s_bg = run(0.0, p, mode, T)
    g_sig, g_bg = s_sig.y[4][-1], s_bg.y[4][-1]
    return dict(g_sig=g_sig, g_bg=g_bg, ratio=g_sig/g_bg,
                x_peak=s_sig.y[1].max(), x_bg=s_bg.y[1][-1],
                y_peak=s_sig.y[2].max(), S_left=s_sig.y[0][-1])
