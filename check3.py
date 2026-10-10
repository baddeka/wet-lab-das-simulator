import das_model as D, numpy as np
base = dict(D.DEFAULTS)

LADDER = [
    ("A. document as written (WT, OD 1, 15x, growing)",
     dict(OD=1.0, k_scav=700., conc_factor=15., sample_frac=0.10, E=1e-3, T_read=3600.)),
    ("B. + Lever B as written (Hpx- knockout)",
     dict(OD=1.0, k_scav=5.,   conc_factor=15., sample_frac=0.10, E=1e-3, T_read=3600.)),
    ("C. keep scavengers, drop cell density to OD 0.1",
     dict(OD=0.1, k_scav=700., conc_factor=15., sample_frac=0.10, E=1e-3, T_read=3600.)),
    ("D. + more of the sample in the well (50% v/v)",
     dict(OD=0.1, k_scav=700., conc_factor=15., sample_frac=0.50, E=1e-3, T_read=3600.)),
    ("E. + OD 0.01 and a 30 min read",
     dict(OD=0.01, k_scav=700., conc_factor=15., sample_frac=0.50, E=1e-3, T_read=1800.)),
    ("F. + non-growing, carbon-limited cells (P_endo 14 -> 4)",
     dict(OD=0.01, k_scav=700., conc_factor=15., sample_frac=0.50, E=1e-3, T_read=1800.,
          P_endo=4.0, mu=1e-6)),
    ("G. + 40x concentration instead of 15x",
     dict(OD=0.01, k_scav=700., conc_factor=40., sample_frac=0.50, E=3e-3, T_read=1800.,
          P_endo=4.0, mu=1e-6)),
]

print("%-52s %10s %8s %9s %10s" % ("scenario", "S/B", "F250/F150", "max CV", "brightness"))
print("-"*95)
for name, kw in LADDER:
    q = dict(base); q.update(kw)
    r = D.response(q, "free")
    d = D.discriminate(q, "free")
    print("%-52s %10.4f %8.4f %8.1f%% %10.2e" % (name, r["sb"], d["ratio"], 100*d["cv_max"], r["brightness"]))

print()
print("required: F250/F150 must beat reader CV.  With n=3 and z=2.8,")
print("a reader at CV=5%% needs fold >= %.3f ; at CV=10%% needs fold >= %.3f"
      % (np.exp(2.8*0.05*np.sqrt(2/3)), np.exp(2.8*0.10*np.sqrt(2/3))))
print()
print("=== how far does the hydration confounder swamp the signal? ===")
q = dict(base); q.update(LADDER[-1][1])
for cr in [0.5, 1.0, 2.0]:
    fh = D.response(dict(q, V_das=150., creatinine=cr), "free")["gfp_signal"]
    fc = D.response(dict(q, V_das=250., creatinine=cr), "free")["gfp_signal"]
    print("  Cr=%.1f g/L : F(healthy)=%.4f  F(cutoff)=%.4f" % (cr, fh, fc))
fh_dilute = D.response(dict(q, V_das=250., creatinine=0.5), "free")["gfp_signal"]
fc_conc   = D.response(dict(q, V_das=150., creatinine=2.0), "free")["gfp_signal"]
print("  -> a CRC patient at Cr=0.5 gives %.4f, a healthy one at Cr=2.0 gives %.4f" % (fh_dilute, fc_conc))
print("     i.e. the classes INVERT unless creatinine is measured separately.")
