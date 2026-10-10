import das_model as D, numpy as np
b = dict(D.DEFAULTS)

print("### TABLE 2 REPLACEMENT: the two H2O2 sources, per litre of cytoplasm, over a 1 h assay")
T, P = 3600., 14.
for OD in [1.0, 0.1, 0.01]:
    phi = 8e-4*OD
    print("  OD %.2f (phi=%.1e): endogenous = %8.0f uM" % (OD, phi, P*T), end="")
    for S in [0.15, 0.25, 1.0]:
        print(" | DAS %.2f -> %7.1f uM (%.2f%%)" % (S, S/phi, 100*(S/phi)/(P*T)), end="")
    print()

print()
print("### RECOMMENDED OPERATING POINT")
op = dict(b, OD=0.05, k_scav=700., conc_factor=12., sample_frac=0.50,
          E=1.5e-3, T_read=1800., P_endo=4.0, mu=1e-6)
for v, lbl in [(150., "healthy"), (200., "cutoff M"), (250., "cutoff F"), (400., "high CRC")]:
    q = dict(op, V_das=v); r = D.response(q, "free")
    print("  %-9s %3.0f nmol/g -> %.3f uM in assay | peak cyt H2O2 %.3f uM | S/B %.2f | F %.3f"
          % (lbl, v, D.das_in_assay(q), r["h2o2_cyt_peak"], r["sb"], r["gfp_signal"]))
d = D.discriminate(op, "free")
print("  fold F(250)/F(150) = %.3f   -> requires reader CV <= %.1f%% at n=3" % (d["ratio"], 100*d["cv_max"]))
print("  resting cytoplasmic H2O2 = %.4f uM (K_oxyr = %.2f uM) -> linear regime" % (op["P_endo"]/op["k_scav"], op["K_oxyr"]))

print()
print("### LEVER TABLE: each term of  S/B = S0 / (phi * P_endo * T)")
ref = dict(b, OD=1.0, conc_factor=1., sample_frac=1.0, E=1e-2, T_read=3600., P_endo=14.)
r0 = D.response(ref, "free")
print("  starting point (raw urine, OD 1, growing, 1 h): S/B = %.5f" % r0["sb"])
steps = [("concentrate urine 12x and use 50%% v/v", dict(conc_factor=12., sample_frac=0.5), 6.0),
         ("drop cell density OD 1 -> 0.05",          dict(OD=0.05),                        20.0),
         ("read at 30 min instead of 60",            dict(T_read=1800.),                    2.0),
         ("non-growing, carbon-limited cells",       dict(P_endo=4.0, mu=1e-6),             3.5)]
cur = dict(ref); cum = 1.0
for name, kw, factor in steps:
    cur.update(kw); cum *= factor
    r = D.response(dict(cur, E=1.5e-3), "free")
    print("  + %-38s x%-5.1f  cumulative x%-7.0f  S/B = %.3f" % (name, factor, cum, r["sb"]))

print()
print("### SELECTIVITY SPEC")
for ratio in [5., 20.]:
    for sel in [10., 100., 1000., 10000.]:
        q = dict(op, selectivity=sel, interferent_ratio=ratio)
        print("  interferent %2.0fx DAS, selectivity %6.0f -> fold %.3f" % (ratio, sel, D.discriminate(q,"free")["ratio"]))

print()
print("### HYDRATION INVERSION at the recommended operating point")
for v, cr, lbl in [(250., 0.5, "CRC, dilute urine"), (150., 2.0, "healthy, concentrated urine"),
                   (250., 1.0, "CRC, typical"), (150., 1.0, "healthy, typical")]:
    f = D.response(dict(op, V_das=v, creatinine=cr), "free")["gfp_signal"]
    print("  %-30s V=%3.0f nmol/g, Cr=%.1f g/L -> F = %.3f" % (lbl, v, cr, f))
