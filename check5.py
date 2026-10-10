import das_model as D, numpy as np
op = dict(D.DEFAULTS, OD=0.05, k_scav=700., conc_factor=12., sample_frac=0.50,
          E=1.5e-3, T_read=1800., P_endo=4.0, mu=1e-6)
print("DAS in assay at cutoff : %.2f uM" % D.das_in_assay(dict(op, V_das=250.)))
print()
print("=== SELECTIVITY SPEC (interferent is an absolute urinary level) ===")
print("  interferent   in assay   selectivity   fold F250/F150   verdict")
for I in [0.0, 1.0, 2.0, 5.0]:
    for sel in [10., 100., 1000.]:
        q = dict(op, interferent=I, selectivity=sel)
        f = D.discriminate(q, "free")["ratio"]
        if I == 0.0 and sel != 10.: continue
        v = "ok" if f >= 1.15 else ("marginal" if f >= 1.10 else "swamped")
        print("  %5.1f uM    %6.1f uM   %8.0f      %8.4f       %s"
              % (I, D.interferent_in_assay(q), sel, f, v))
