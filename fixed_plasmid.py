"""Plasmid is frozen. Reporter brightness sets an OD floor, the OD floor sets the fold."""
import das_model as D, numpy as np
NA, CELLS = 6.022e23, 8e8

def gfp_nM(OD, per_cell):
    return CELLS*OD*1e3*per_cell/NA*1e9

BASE = dict(D.DEFAULTS, sample_frac=0.60, mu=1e-6, k_chem=0., interferent=0.,
            P_endo=4.0, k_scav=700., T_read=1800.)
def best_fold(OD):
    b = None
    for F in [2,3,4,6,8,12,16,24,40]:
        q = dict(BASE, OD=OD, conc_factor=float(F), E=1.5e-3*max(1., F/12.))
        r = D.discriminate(q, "free")
        if b is None or r["ratio"] > b[0]: b = (r["ratio"], F, r["cv_max"])
    return b

print("=== OD floor forced by reporter brightness, and the fold it allows ===")
print("%-14s %-13s %-9s %-8s %-9s %-9s" % ("GFP/cell", "reader LOD", "OD floor", "fold", "CV n=3", "CV n=6"))
for per_cell in [1e3, 1e4, 1e5]:
    for lod, lab in [(10.0,"phone, typ"), (1.0,"phone, good"), (0.05,"plate reader")]:
        od = lod/(gfp_nM(1.0, per_cell))
        od_use = min(max(od, 0.003), 3.0)
        f, F, cv = best_fold(od_use)
        cv6 = np.log(f)/(2.8*np.sqrt(2/6))
        flag = "" if od <= 0.3 else "  <- OD too high to work at all"
        print("%-14s %-13s %-9s %-8.3f %-9s %-9s%s" % (
            "%.0e" % per_cell, lab, "%.3f" % od, f, "%.1f%%" % (100*cv), "%.1f%%" % (100*cv6), flag))

print()
print("=== what a whole-cell dose response should show at NON-clinical DAS ===")
print("   (this is what is actually demonstrable in an iGEM season)")
for V in [250., 2500., 25000., 250000.]:
    q = dict(BASE, OD=0.1, conc_factor=1., sample_frac=1.0, E=1.5e-3, V_das=V)
    r = D.response(q, "free")
    print("   DAS %8.1f uM in the well -> S/B %7.3f  (%s)" % (
        D.das_in_assay(q), r["sb"], "clinical" if V < 1000 else "spiked"))
