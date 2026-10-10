"""What is the best fold change this architecture can ever give?"""
import das_model as D, itertools, numpy as np

BASE = dict(D.DEFAULTS, sample_frac=0.60, mu=1e-6, k_chem=0., interferent=0.,
            cr_norm=True if False else None)
BASE.pop("cr_norm", None)

best = None
grid = list(itertools.product(
    [0.003, 0.01, 0.03, 0.05, 0.1, 0.3],            # OD
    [2, 4, 6, 8, 12, 16, 24, 40],                    # concentration factor
    [900, 1800, 3600],                               # read time
    [2.0, 4.0, 14.0],                                # P_endo (metabolic state)
    [300., 700., 2000.],                             # k_scav (incl. overexpressed)
))
for OD, F, T, Pe, ks in grid:
    q = dict(BASE, OD=OD, conc_factor=F, T_read=T, P_endo=Pe, k_scav=ks,
             E=1.5e-3*max(1., F/12.)*max(1., 1800./T))
    r = D.discriminate(q, "free")
    if r["ratio"] > 1 and (best is None or r["ratio"] > best[0]):
        best = (r["ratio"], dict(OD=OD, F=F, T=T, P_endo=Pe, k_scav=ks), r["cv_max"])

print("=== absolute best fold over %d configurations (clean sample, no interferents) ===" % len(grid))
print("   fold = %.3f  at %s" % (best[0], best[1]))
print("   required reader CV at n=3: %.1f %%" % (100*best[2]))
for n in [3, 6, 12]:
    cv = np.log(best[0])/(2.8*np.sqrt(2/n))
    print("     n=%2d -> CV must be under %.1f %%" % (n, 100*cv))

print()
print("=== why the ceiling exists: fold vs signal-to-background ===")
print("   the clinical difference is 250/150 = 1.667x. fluorescence = blank + signal,")
print("   so fold = (1+SB_cutoff)/(1+SB_healthy) and only reaches 1.667 as SB -> infinity")
for OD in [0.3, 0.1, 0.03, 0.01, 0.003, 0.001]:
    q = dict(BASE, OD=OD, conc_factor=12., T_read=1800., P_endo=4., k_scav=700., E=1.5e-3)
    sb_h = D.response(dict(q, V_das=150.), "free")["sb"]
    sb_c = D.response(dict(q, V_das=250.), "free")["sb"]
    print("   OD %6.3f | S/B healthy %8.2f  cutoff %8.2f | ratio of S/B %.3f | fold %.3f"
          % (OD, sb_h, sb_c, sb_c/sb_h, (1+sb_c)/(1+sb_h)))

print()
print("=== what a cell-free chemical peroxide readout would give instead ===")
print("   no endogenous background, no compartment, no OxyR compression:")
print("   fold = 1.667 exactly, and Amplex Red resolves ~0.05 uM H2O2 against 1.5 uM delivered.")
