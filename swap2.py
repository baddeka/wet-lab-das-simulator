import das_model as D, numpy as np
BASE = dict(D.DEFAULTS, OD=0.05, k_scav=700., sample_frac=0.50,
            T_read=1800., P_endo=4.0, mu=1e-6)
def evaluate(C_uM, R):
    """Concentration factor free to go below 1, i.e. dilution is allowed."""
    best = (0, None)
    for c in [0.02, 0.05, 0.1, 0.3, 1., 2., 4., 6., 12., 20., 40.]:
        q = dict(BASE, conc_factor=c, E=1.5e-3*max(1., c/12.))
        h = D.response(dict(q, V_das=C_uM*1000.), "free")["gfp_signal"]
        s = D.response(dict(q, V_das=C_uM*1000.*R), "free")["gfp_signal"]
        if s/h > best[0]: best = (s/h, c)
    cv3 = np.log(best[0])/(2.8*np.sqrt(2/3))
    return best[0], cv3, best[1]

print("=== with dilution allowed, does absolute concentration matter at all? ===")
print("%-12s %-16s %-16s %-16s" % ("healthy", "R=1.67 (DAS)", "R=3", "R=5"))
for C in [0.15, 0.5, 2.0, 10.0, 100.0]:
    cells = []
    for R in [1.67, 3., 5.]:
        f, cv, c = evaluate(C, R)
        cells.append("%.2fx  CV %2.0f%%" % (f, 100*cv))
    print("%-12s %-16s %-16s %-16s" % ("%.2f uM" % C, *cells))
print()
print("  -> the columns are flat. concentration is a free knob, so it cancels.")
print("     only the clinical ratio R changes the answer.")
print()
print("=== so the whole question reduces to one number ===")
for R in [1.5, 1.67, 2., 3., 5., 10.]:
    f, cv, _ = evaluate(0.15, R)
    verdict = "hopeless" if cv < 0.06 else ("tight" if cv < 0.12 else ("workable" if cv < 0.20 else "easy"))
    print("  clinical ratio %5.2f -> fold %.2f on the reader, tolerates CV %4.0f%%   %s" % (R, f, 100*cv, verdict))
