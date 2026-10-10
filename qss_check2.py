"""Cytoplasm in QSS (relaxes in ~1 ms), medium integrated exactly as a linear ODE."""
import math, das_model as D

def sim(p, mode, with_das, N=600):
    kmem, ksc, kch = p["k_mem"], p["k_scav"], p["k_chem"]
    phi = D.phi(p); P = p["P_endo"]; T = p["T_read"]
    kcat, Km, sel = p["kcat"], p["Km"], p["selectivity"]
    Kx, n = p["K_oxyr"], p["n_hill"]
    kmat, mu, mup, beta, leak = p["k_mat"], p["mu"], p["mu_pre"], p["beta"], p["leak"]
    ktot = kmem + ksc
    b = phi*kmem*ksc/ktot + kch                       # medium decay constant

    xf = lambda y, v_cyt: (P + v_cyt + kmem*y)/ktot   # cytoplasm, quasi-steady
    fox = lambda x: x**n/(Kx**n + x**n)

    y = (phi*kmem*P/ktot)/b
    x0 = xf(y, 0.0)
    m = (beta*fox(x0) + leak)/(kmat + mup)
    g = kmat*m/mup
    S = D.das_in_assay(p) if with_das else 0.0
    I = D.interferent_in_assay(p) if with_das else 0.0

    if mode == "cyto":   Ecap, scale = phi*kcat*p["E"]*p["alpha"], p["alpha"]
    elif mode == "peri": Ecap, scale = kcat*p["E"]*p["peri_frac"]*phi, 1.0
    else:                Ecap, scale = kcat*p["E"], 1.0

    dt = T/N; xpk = x0; series = []
    for step in range(N):
        kS0 = Ecap/(Km + scale*(S+I))
        nsub = max(1, int(kS0*dt/0.05) + 1, int(b*dt/0.25) + 1)
        h = dt/nsub; facc = 0.0
        for _ in range(nsub):
            kS = Ecap/(Km + scale*(S+I)); kI = kS/sel
            Sn = S*math.exp(-kS*h); In = I*math.exp(-kI*h)
            prod = ((S-Sn) + (I-In))/h
            S, I = Sn, In
            v_cyt, v_med = (prod/phi, 0.0) if mode == "cyto" else (0.0, prod)
            a = v_med + phi*kmem*(P + v_cyt)/ktot
            yss = a/b
            y = yss + (y - yss)*math.exp(-b*h)
            x = xf(y, v_cyt); xpk = max(xpk, x)
            facc += fox(x)*h
        f = facc/dt
        kt = kmat + mu; e = math.exp(-kt*dt)
        m2 = m*e + (beta*f + leak)/kt*(1 - e)
        if mu < 1e-9: g += kmat*0.5*(m + m2)*dt
        else:
            eg = math.exp(-mu*dt); g = g*eg + (kmat*0.5*(m+m2)/mu)*(1 - eg)
        m = m2
        series.append((dt*(step+1), x, g))
    return dict(gfp=g, xpk=xpk, S=S, series=series)

def sb(p, mode, N=600):
    a = sim(p, mode, True, N)["gfp"]; b_ = sim(p, mode, False, N)["gfp"]
    return (a - b_)/b_
def fold(p, mode, N=600):
    return sim(dict(p, V_das=250.), mode, True, N)["gfp"]/sim(dict(p, V_das=150.), mode, True, N)["gfp"]

OP = dict(D.DEFAULTS, OD=0.05, k_scav=700., conc_factor=12., sample_frac=0.50,
          E=1.5e-3, T_read=1800., P_endo=4.0, mu=1e-6, V_das=250.)
CASES = [("operating point, free",    OP, "free"),
         ("original draft, OD 1",     dict(OP, OD=1.0, conc_factor=1., sample_frac=1.0, E=1e-2, T_read=3600., P_endo=14., mu=D.LN2/2400), "free"),
         ("Hpx- knockout",            dict(OP, k_scav=5.), "free"),
         ("very low density OD 0.005",dict(OP, OD=0.005), "free"),
         ("cytoplasmic, poor uptake", dict(OP, E=10., alpha=0.01), "cyto"),
         ("periplasmic",              dict(OP, E=100.), "peri"),
         ("with interferents",        dict(OP, interferent=2., selectivity=100.), "free"),
         ("matrix sink k_chem 0.01",  dict(OP, k_chem=0.01), "free"),
         ("fast enzyme E = 1 uM",     dict(OP, E=1.0), "free")]
print("%-28s %11s %11s %7s | %9s %9s %6s" % ("case","S/B exact","S/B fast","err","fold ex","fold fast","err"))
for name, q, mode in CASES:
    r = D.response(q, mode); fe = D.discriminate(q, mode)["ratio"]
    sf = sb(q, mode); ff = fold(q, mode)
    e1 = 100*abs(sf-r["sb"])/max(abs(r["sb"]),1e-9)
    e2 = 100*abs(ff-fe)/max(abs(fe-1),1e-9)
    print("%-28s %11.5f %11.5f %6.2f%% | %9.4f %9.4f %5.2f%%" % (name, r["sb"], sf, e1, fe, ff, e2))
