import das_model as D, numpy as np
base = dict(D.DEFAULTS)
base.update(dict(OD=0.01, k_scav=700., sample_frac=0.50, E=1e-3,
                 T_read=1800., P_endo=4.0, mu=1e-6))

print("=== optimum concentration factor (fold F250/F150 is what classifies) ===")
print("  Fx    DAS in assay   rest H2O2   peak cyt H2O2   S/B     fold    max CV")
best = (0, None)
for F in [5, 10, 15, 20, 30, 40, 60, 100, 200]:
    q = dict(base, conc_factor=float(F), E=1e-3*max(1., F/15.))
    r = D.response(q, "free"); d = D.discriminate(q, "free")
    if d["ratio"] > best[0]: best = (d["ratio"], F)
    print("  %4d   %8.3f uM   %7.3f uM   %8.3f uM   %6.3f  %6.4f  %5.1f%%"
          % (F, D.das_in_assay(q), q["P_endo"]/q["k_scav"], r["h2o2_cyt_peak"],
             r["sb"], d["ratio"], 100*d["cv_max"]))
print("  -> best fold at %dx concentration" % best[1])

print()
print("=== optimum cell density (fold vs brightness) ===")
print("   OD     phi      fold    max CV   brightness (rel.)")
for OD in [0.3, 0.1, 0.03, 0.01, 0.003, 0.001]:
    q = dict(base, OD=OD, conc_factor=30.)
    r = D.response(q, "free"); d = D.discriminate(q, "free")
    print("  %6.3f %.1e  %6.4f  %5.1f%%   %.2e" % (OD, D.phi(q), d["ratio"], 100*d["cv_max"], r["brightness"]))

print()
print("=== cross-reactive polyamines (urine has 5-20x more than DAS) ===")
print("  selectivity  interferent/DAS   fold F250/F150   verdict")
for sel in [10., 100., 1000.]:
    for ratio in [5., 20.]:
        q = dict(base, conc_factor=30., selectivity=sel, interferent_ratio=ratio)
        d = D.discriminate(q, "free")
        ok = "usable" if d["ratio"] > 1.12 else "swamped"
        print("  %8.0f    %8.0f x        %8.4f       %s" % (sel, ratio, d["ratio"], ok))

print()
print("=== matrix H2O2 sink (urate/ascorbate carried over from urine) ===")
for kc in [0.0, 0.001, 0.01, 0.1]:
    q = dict(base, conc_factor=30., k_chem=kc)
    d = D.discriminate(q, "free")
    print("  k_chem=%6.3f s^-1 -> fold=%.4f" % (kc, d["ratio"]))
