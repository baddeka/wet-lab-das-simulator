import das_model as D, numpy as np
p = dict(D.DEFAULTS)
# enzyme concentration is expressed in its OWN compartment, so the sensible
# default differs per architecture:
E_DEF = {"cyto": 10.0, "peri": 30.0, "free": 1e-3}   # uM in cytoplasm / periplasm / assay

def R(mode, **kw):
    q = dict(p, E=E_DEF[mode]); q.update(kw)
    return q, D.response(q, mode)

print("=== 2. master equation:  S/B = [S0/(phi*P_endo*T)] * (log-sensitivity) * (timing) ===")
for OD in [1.0, 0.3, 0.1, 0.03, 0.01]:
    q, r = R("free", OD=OD)
    budget = D.das_in_assay(q) / (D.phi(q)*q["P_endo"]*q["T_read"])
    print("  OD=%5.2f | S/B=%8.4f | budget=%8.4f | ratio=%.3f" % (OD, r["sb"], budget, r["sb"]/budget))
print()
print("=== 3. localization at realistic per-compartment [E] ===")
for mode in ["cyto", "peri", "free"]:
    q, r = R(mode)
    print("  %-5s E=%6.1f uM in own compartment | DAS converted=%5.1f%% | S/B=%.4f"
          % (mode, E_DEF[mode], 100*(1-r["das_left"]/r["das_assay"]), r["sb"]))
print("  cyto with no DAS uptake (alpha=0.01):", "%.5f" % R("cyto", alpha=0.01)[1]["sb"])
print()
print("=== 4. Lever B: knocking out the scavengers ===")
print("  k_scav   rest H2O2   S/B        fold(F/F0)   verdict")
for ks in [700., 400., 200., 50., 20., 5.]:
    q, r = R("free", k_scav=ks)
    v = "OxyR saturated" if q["P_endo"]/ks > 3*q["K_oxyr"] else ("near K_oxyr" if q["P_endo"]/ks > 0.5*q["K_oxyr"] else "linear regime")
    print("  %6.1f   %7.3f uM  %.5f    %.4f      %s" % (ks, q["P_endo"]/ks, r["sb"], r["fold"], v))
print()
print("=== 5. Lever C: more enzyme ===")
for E in [1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1.0]:
    q, r = R("free", E=E)
    print("  E=%8.1e uM | DAS converted=%5.1f%% | S/B=%.4f" % (E, 100*(1-r["das_left"]/r["das_assay"]), r["sb"]))
print()
print("=== 6. periplasmic capacity vs OD (the real trade-off) ===")
for OD in [1.0, 0.3, 0.1, 0.03]:
    for Ep in [10., 100.]:
        q, r = R("peri", OD=OD, E=Ep)
        print("  OD=%5.2f E_peri=%5.0f uM | converted=%5.1f%% | S/B=%.4f" % (OD, Ep, 100*(1-r["das_left"]/r["das_assay"]), r["sb"]))
