import das_model as D, numpy as np
p = dict(D.DEFAULTS)

print("=== 1. literature anchors ===")
x, _, _, _ = D.rest_state(p)
print("  WT cytoplasmic H2O2 at rest      : %.4f uM   (Seaver & Imlay ~0.02)" % x)
print("  medium/cytoplasm gradient        : %.1f x    (Seaver & Imlay ~9x)" % (1 + p["k_scav"]/p["k_mem"]))
print("  DAS in raw urine, 200 nmol/g, Cr=1: %.3f uM" % D.das_in_urine(p))
print("  DAS presented to assay, 15x, 10%% : %.3f uM" % D.das_in_assay(p))
print()

print("=== 2. does the master equation hold?  S/B = S0/(phi*P_endo*T) * dlnF/dlnH ===")
for OD in [1.0, 0.3, 0.1, 0.03, 0.01]:
    q = dict(p, OD=OD)
    r = D.response(q, "peri")
    budget = D.das_in_assay(q) / (D.phi(q) * q["P_endo"] * q["T_read"])
    print("  OD=%5.2f phi=%.1e | S/B=%8.4f | budget=%8.4f | S/B per budget=%.3f"
          % (OD, D.phi(q), r["sb"], budget, r["sb"]/budget))
print()

print("=== 3. localization: does it change the integrated signal? ===")
for mode in ["peri", "free", "cyto"]:
    q = dict(p, E=1.0 if mode == "peri" else 1e-3)
    r = D.response(q, mode)
    print("  %-5s | S/B=%.4f | DAS left=%.2e uM | peak cyt H2O2=%.4f uM"
          % (mode, r["sb"], r["das_left"], r["h2o2_cyt_peak"]))
print()

print("=== 4. Lever B: is knocking out scavengers good? ===")
for ks in [700., 400., 200., 50., 20., 5.]:
    q = dict(p, k_scav=ks)
    r = D.response(q, "peri")
    print("  k_scav=%6.1f | rest cyt H2O2=%6.3f uM (K_oxyr=%.2f) | S/B=%.4f | blank GFP=%.3f"
          % (ks, q["P_endo"]/ks, q["K_oxyr"], r["sb"], r["gfp_blank"]))
print()

print("=== 5. Lever C: does more enzyme help? ===")
for E in [1e-5, 1e-4, 1e-3, 1e-2, 1.0]:
    q = dict(p, E=E)
    r = D.response(q, "peri")
    print("  E=%8.1e uM | DAS left=%8.2e uM | S/B=%.4f" % (E, r["das_left"], r["sb"]))
