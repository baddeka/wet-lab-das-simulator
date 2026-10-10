"""If we swap DAS for another urinary marker, what actually improves?"""
import das_model as D, numpy as np

BASE = dict(D.DEFAULTS, OD=0.05, k_scav=700., sample_frac=0.50,
            T_read=1800., P_endo=4.0, mu=1e-6)

def evaluate(C_uM, R, conc=12.):
    """C_uM = healthy level in urine; R = sick/healthy clinical ratio."""
    q = dict(BASE, conc_factor=conc, E=1.5e-3*max(1., conc/12.))
    h = D.response(dict(q, V_das=C_uM*1000.), "free")["gfp_signal"]
    s = D.response(dict(q, V_das=C_uM*1000.*R), "free")["gfp_signal"]
    fold = s/h
    cv3 = np.log(fold)/(2.8*np.sqrt(2/3)) if fold > 1 else 0
    return fold, cv3

print("=== fold on the instrument, for a marker at concentration C with clinical ratio R ===")
print("   (same plasmid, same cells, same operating point, concentration factor tuned)")
print()
print("%-12s %s" % ("healthy", "  clinical ratio healthy -> sick"))
print("%-12s %-13s %-13s %-13s %-13s" % ("in urine", "R = 1.67 (DAS)", "R = 3", "R = 5", "R = 10"))
for C in [0.15, 0.5, 2.0, 10.0, 100.0]:
    row = []
    for R in [1.67, 3., 5., 10.]:
        best = max(evaluate(C, R, c) for c in [2.,4.,6.,12.,20.,40.])
        row.append("%.2fx / %.0f%%" % (best[0], 100*best[1]))
    print("%-12s %-13s %-13s %-13s %-13s" % ("%.2f uM" % C, *row))
print()
print("   cell = fold on the instrument / reader CV it tolerates at n=3")
print("   a reader CV under about 10 % is realistic; under 5 % is not")
print()
print("=== which matters more, concentration or clinical ratio? ===")
f_conc, _ = evaluate(0.15*10, 1.67)     # 10x more of the same marker
f_ratio, _ = evaluate(0.15, 1.67*10/1.67*1.67)
print("   DAS as is                      : fold %.3f" % evaluate(0.15, 1.67)[0])
print("   same marker but 10x more of it : fold %.3f" % f_conc)
print("   same amount but ratio 3 not 1.67: fold %.3f" % evaluate(0.15, 3.0)[0])
print("   same amount but ratio 5 not 1.67: fold %.3f" % evaluate(0.15, 5.0)[0])
