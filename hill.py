import das_model as D, numpy as np
OP = dict(D.DEFAULTS, OD=0.05, k_scav=700., conc_factor=12., sample_frac=0.50,
          E=1.5e-3, T_read=1800., P_endo=4.0, mu=1e-6)
K = OP["K_oxyr"]

print("=== how much of a 1.667x input difference reaches the output ===")
print("  f(x) = x^n / (K^n + x^n),  K = %.2f uM" % K)
print()
print("  %-8s %-12s %-12s %-10s" % ("x/K", "n=1: f", "n=2: f", ""))
for r in [0.1, 0.3, 1.0, 3.0]:
    x = r*K
    f1 = x/(K+x); f2 = x**2/(K**2+x**2)
    print("  %-8.1f %-12.3f %-12.3f" % (r, f1, f2))
print()
print("  local log-log slope  dlnf/dlnx = n*(1-f):")
for r, lbl in [(0.1,"far below K"), (1.0,"at K"), (3.0,"above K")]:
    x = r*K
    f1 = x/(K+x); f2 = x**2/(K**2+x**2)
    print("    %-12s n=1 -> %.2f   n=2 -> %.2f" % (lbl, 1*(1-f1), 2*(1-f2)))
print()
print("  so a 1.667x change in H2O2 becomes, in reporter output:")
for r, lbl in [(0.1,"far below K"), (1.0,"at K")]:
    x = r*K
    f1 = x/(K+x); f2 = x**2/(K**2+x**2)
    print("    %-12s n=1 -> %.2fx   n=2 -> %.2fx" % (lbl, 1.667**(1*(1-f1)), 1.667**(2*(1-f2))))
print()
print("=== end to end, through the whole model at the operating point ===")
for n in [1.0, 1.5, 2.0, 3.0]:
    q = dict(OP, n_hill=n)
    d = D.discriminate(q, "free")
    print("  n = %.1f  ->  fold %.3f  |  reader CV must be under %.1f %% at n_rep=3"
          % (n, d["ratio"], 100*d["cv_max"]))
