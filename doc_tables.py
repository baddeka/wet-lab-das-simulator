import das_model as D, numpy as np
B = dict(D.DEFAULTS)
OP = dict(B, OD=0.05, k_scav=700., conc_factor=12., sample_frac=0.50,
          E=1.5e-3, T_read=1800., P_endo=4.0, mu=1e-6, V_das=250.)

print("### TABLE 4  lever ladder, evaluated at the CRC cutoff (250 nmol/g, Cr 1 g/L)")
cur = dict(B, V_das=250., OD=1.0, conc_factor=1., sample_frac=1.0, E=1e-2,
           T_read=3600., P_endo=14., mu=D.LN2/2400)
print("  %-46s %8s %10s" % ("step", "factor", "S/B"))
r = D.response(cur, "free"); print("  %-46s %8s %10.4f" % ("raw urine, OD 1.0, growing cells, 60 min read", "-", r["sb"]))
for name, kw, fac in [
    ("concentrate 12x, sample at 50% v/v",  dict(conc_factor=12., sample_frac=0.5, E=1.5e-3), "x6"),
    ("cell density OD 1.0 -> 0.05",          dict(OD=0.05),                                    "x20"),
    ("read at 30 min instead of 60",         dict(T_read=1800.),                               "x2"),
    ("non-growing, carbon-limited cells",    dict(P_endo=4.0, mu=1e-6),                        "x3.5")]:
    cur.update(kw); r = D.response(cur, "free")
    print("  + %-44s %8s %10.4f" % (name, fac, r["sb"]))

print()
print("### TABLE 5  net delivery factor: the optimum is not the maximum")
print("  %-8s %-10s %-14s %-10s %-8s" % ("conc x", "net x", "DAS in assay", "peak cyt", "fold"))
for F in [4., 8., 12., 16., 24., 40., 80.]:
    q = dict(OP, conc_factor=F, E=1.5e-3*max(1., F/12.))
    r = D.response(dict(q, V_das=250.), "free"); d = D.discriminate(q, "free")
    print("  %-8.0f %-10.1f %-14.2f %-10.3f %-8.3f" % (F, F*q["sample_frac"], D.das_in_assay(dict(q, V_das=250.)), r["h2o2_cyt_peak"], d["ratio"]))

print()
print("### TABLE 6  where the enzyme sits")
E_OWN = {"cyto": 10.0, "peri": 30.0, "free": 1.0e-3}
for mode in ["cyto", "peri", "free"]:
    q = dict(OP, E=E_OWN[mode])
    r = D.response(dict(q, V_das=250.), "free" if mode == "free" else mode)
    d = D.discriminate(q, mode)
    conv = 100*(1 - r["das_left"]/r["das_assay"])
    print("  %-5s [E]=%7.3f uM own compartment | converted %5.1f%% | fold %.3f" % (mode, E_OWN[mode], conv, d["ratio"]))
q = dict(OP, E=10.0)
print("  cyto with 100x poorer DAS uptake (alpha=0.01): fold %.3f" % D.discriminate(dict(q, alpha=0.01), "cyto")["ratio"])
q = dict(OP, E=10.0, OD=0.05)
print("  peri needs [E]_peri >= %.0f uM at OD 0.05 to convert in 30 min" % 30.)
for Ep in [3., 10., 30., 100.]:
    r = D.response(dict(OP, E=Ep, V_das=250.), "peri")
    print("     [E]_peri=%6.1f uM -> converted %5.1f%%" % (Ep, 100*(1-r["das_left"]/r["das_assay"])))

print()
print("### TABLE 8  reader requirement")
d = D.discriminate(OP, "free")
print("  fold F(250)/F(150) at the operating point = %.3f" % d["ratio"])
for n in [1, 3, 6]:
    for cv in [0.03, 0.05, 0.10, 0.15]:
        z = np.log(d["ratio"])/(cv*np.sqrt(2/n))
        print("     n=%d CV=%3.0f%% -> z=%.2f  %s" % (n, 100*cv, z, "separable" if z >= 2.8 else "not separable"))
