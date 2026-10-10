"""What does a better reader actually buy?  Brightness sets the lowest usable OD;
the lowest usable OD sets the best achievable fold."""
import das_model as D, numpy as np

CELLS_PER_ML_OD1 = 8e8
NA = 6.022e23

def gfp_nM(OD, per_cell):
    """GFP concentration in the well, nM."""
    mol_per_L = CELLS_PER_ML_OD1*OD*1e3*per_cell/NA
    return mol_per_L*1e9

print("=== brightness: GFP concentration in the well ===")
print("  %-10s %-14s %-14s" % ("OD600", "1e4 GFP/cell", "1e5 GFP/cell"))
for OD in [0.3, 0.1, 0.03, 0.01, 0.003]:
    print("  %-10.3f %-14s %-14s" % (OD, "%.2f nM" % gfp_nM(OD,1e4), "%.2f nM" % gfp_nM(OD,1e5)))

print()
print("=== best fold reachable if the reader forces you to stay above some OD ===")
BASE = dict(D.DEFAULTS, sample_frac=0.60, mu=1e-6, k_chem=0., interferent=0.,
            P_endo=4.0, k_scav=700., T_read=1800.)
for ODfloor in [0.3, 0.1, 0.05, 0.03, 0.01, 0.003]:
    best = None
    for F in [2,3,4,6,8,12,16,24,40]:
        q = dict(BASE, OD=ODfloor, conc_factor=float(F), E=1.5e-3*max(1., F/12.))
        r = D.discriminate(q, "free")
        if best is None or r["ratio"] > best[0]:
            best = (r["ratio"], F, r["cv_max"])
    cv6 = np.log(best[0])/(2.8*np.sqrt(2/6))
    print("  OD %6.3f | best delivery %2dx | fold %.3f | CV needed: %4.1f%% (n=3)  %4.1f%% (n=6)"
          % (ODfloor, best[1], best[0], 100*best[2], 100*cv6))

print()
print("=== does a stronger reporter help? (beta x10 = 1e5 GFP/cell) ===")
a = D.discriminate(dict(BASE, OD=0.03, conc_factor=6., E=1.5e-3), "free")["ratio"]
b = D.discriminate(dict(BASE, OD=0.03, conc_factor=6., E=1.5e-3, beta=5e-2, leak=2e-4), "free")["ratio"]
print("  fold at beta x1  : %.4f" % a)
print("  fold at beta x10 : %.4f   (identical: it lifts signal and blank together)" % b)
print("  but it lifts brightness 10x, which lets you drop OD by 10x, and THAT lifts fold.")
