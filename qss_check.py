"""The fast scheme that the web page will use, checked against LSODA."""
import math, das_model as D

def sim_qss(p, mode, with_das, N=900):
    kmem, ksc, kch = p["k_mem"], p["k_scav"], p["k_chem"]
    phi = D.phi(p); P = p["P_endo"]; T = p["T_read"]
    kcat, Km, sel = p["kcat"], p["Km"], p["selectivity"]
    Kx, n = p["K_oxyr"], p["n_hill"]
    kmat, mu, mup = p["k_mat"], p["mu"], p["mu_pre"]
    A = phi*kmem + kch
    den = kmem + ksc - kmem*kmem*phi/A

    def xq(v_cyt, v_med):
        return (P + v_cyt + kmem*v_med/A) / den
    def fox(x):
        xn = x**n
        return xn/(Kx**n + xn)

    x0 = xq(0.0, 0.0)
    m = (p["beta"]*fox(x0) + p["leak"])/(kmat + mup)
    g = kmat*m/mup
    S = D.das_in_assay(p) if with_das else 0.0
    I = D.interferent_in_assay(p) if with_das else 0.0

    if mode == "cyto":
        Ecap = phi*kcat*p["E"]*p["alpha"]
    elif mode == "peri":
        Ecap = kcat*p["E"]*p["peri_frac"]*phi
    else:
        Ecap = kcat*p["E"]
    scale = p["alpha"] if mode == "cyto" else 1.0

    dt = T/N; xpk = x0
    for _ in range(N):
        kS = Ecap/(Km + scale*(S+I))
        nsub = max(1, int(kS*dt/0.2) + 1)
        h = dt/nsub; facc = 0.0
        for _ in range(nsub):
            kS = Ecap/(Km + scale*(S+I))
            kI = kS/sel
            Sn = S*math.exp(-kS*h); In = I*math.exp(-kI*h)
            prod = ((S-Sn) + (I-In))/h
            S, I = Sn, In
            v_cyt, v_med = (prod/phi, 0.0) if mode == "cyto" else (0.0, prod)
            x = xq(v_cyt, v_med); xpk = max(xpk, x)
            facc += fox(x)*h
        f = facc/dt
        km_ = kmat + mu
        e = math.exp(-km_*dt)
        m_new = m*e + (p["beta"]*f + p["leak"])/km_*(1-e)
        if mu < 1e-9:
            g = g + kmat*0.5*(m+m_new)*dt
        else:
            eg = math.exp(-mu*dt)
            g = g*eg + (kmat*0.5*(m+m_new)/mu)*(1-eg)
        m = m_new
    return dict(gfp=g, xpk=xpk, S=S)

def fold_qss(p, mode):
    a = sim_qss(dict(p, V_das=250.), mode, True)["gfp"]
    b = sim_qss(dict(p, V_das=150.), mode, True)["gfp"]
    return a/b

OP = dict(D.DEFAULTS, OD=0.05, k_scav=700., conc_factor=12., sample_frac=0.50,
          E=1.5e-3, T_read=1800., P_endo=4.0, mu=1e-6, V_das=250.)
CASES = [("operating point, free",      OP,                                   "free"),
         ("original draft, OD 1",       dict(OP, OD=1.0, conc_factor=1., sample_frac=1.0, E=1e-2, T_read=3600., P_endo=14., mu=D.LN2/2400), "free"),
         ("Hpx- knockout",              dict(OP, k_scav=5.),                  "free"),
         ("cytoplasmic, poor uptake",   dict(OP, E=10., alpha=0.01),          "cyto"),
         ("periplasmic",                dict(OP, E=100.),                     "peri"),
         ("with interferents",          dict(OP, interferent=2., selectivity=100.), "free")]

print("%-28s %12s %12s %8s | %10s %10s" % ("case", "S/B LSODA", "S/B fast", "err", "fold exact", "fold fast"))
for name, q, mode in CASES:
    r = D.response(q, mode); qq = sim_qss(q, mode, True); bb = sim_qss(q, mode, False)
    sb_fast = (qq["gfp"] - bb["gfp"])/bb["gfp"]
    fe = D.discriminate(q, mode)["ratio"]; ff = fold_qss(q, mode)
    err = abs(sb_fast - r["sb"])/max(abs(r["sb"]), 1e-9)
    print("%-28s %12.5f %12.5f %7.2f%% | %10.4f %10.4f" % (name, r["sb"], sb_fast, 100*err, fe, ff))
