"""Do the headline conclusions survive the parameter uncertainty?"""
import das_model as D, itertools, numpy as np

OP = dict(D.DEFAULTS, OD=0.05, k_scav=700., conc_factor=12., sample_frac=0.50,
          E=1.5e-3, T_read=1800., P_endo=4.0, mu=1e-6, V_das=250.)

GRID = dict(
    K_oxyr=[0.02, 0.10, 0.20],     # literature spread for OxyR half-activation
    n_hill=[1.0, 2.0],             # transfer function shape, unmeasured
    P_endo=[4.0, 14.0],            # resting vs growing endogenous flux
    Km=[83.0, 310.0],              # two published buffers
)
keys = list(GRID)
combos = [dict(zip(keys, v)) for v in itertools.product(*[GRID[k] for k in keys])]
print("parameter combinations tested:", len(combos))

def claim_knockout_harmful(q):
    wt = D.response(dict(q, k_scav=700.), "free")
    ko = D.response(dict(q, k_scav=5.),   "free")
    return ko["sb"] < wt["sb"], wt["sb"]/max(ko["sb"], 1e-12)

def claim_enzyme_not_limiting(q):
    lo = D.discriminate(dict(q, E=1.5e-3), "free")["ratio"]
    hi = D.discriminate(dict(q, E=1.0),    "free")["ratio"]
    return hi <= lo*1.02, lo, hi

def claim_density_dominates(q):
    hi = D.response(dict(q, OD=1.0),  "free")["sb"]
    lo = D.response(dict(q, OD=0.05), "free")["sb"]
    return lo > hi*5, lo/max(hi, 1e-12)

res = {"knockout harmful":[], "enzyme not limiting":[], "density dominates":[]}
gains, folds = [], []
for c in combos:
    q = dict(OP); q.update(c)
    ok1, r1 = claim_knockout_harmful(q);   res["knockout harmful"].append(ok1); gains.append(r1)
    ok2, _, _ = claim_enzyme_not_limiting(q); res["enzyme not limiting"].append(ok2)
    ok3, r3 = claim_density_dominates(q);  res["density dominates"].append(ok3)
    folds.append(D.discriminate(q, "free")["ratio"])

print()
for k, v in res.items():
    print("  %-22s holds in %d / %d combinations" % (k, sum(v), len(v)))
print()
print("  knockout penalty (WT S/B over Hpx- S/B): %.0f to %.0f fold" % (min(gains), max(gains)))
print("  density gain OD 1 -> 0.05             : %.0f to %.0f fold" % (
      min(claim_density_dominates(dict(OP, **c))[1] for c in combos),
      max(claim_density_dominates(dict(OP, **c))[1] for c in combos)))
print("  fold F(250)/F(150) across the grid    : %.3f to %.3f" % (min(folds), max(folds)))
print()
print("=== which single parameter moves the answer most? ===")
base = D.discriminate(OP, "free")["ratio"]
for k, vals in GRID.items():
    fs = [D.discriminate(dict(OP, **{k:v}), "free")["ratio"] for v in vals]
    print("  %-8s %s -> fold %s  (spread %.3f)" % (
        k, vals, ["%.3f" % f for f in fs], max(fs)-min(fs)))
print()
print("=== does the optimum delivery factor move with K_oxyr? ===")
for K in GRID["K_oxyr"]:
    best = max([(D.discriminate(dict(OP, K_oxyr=K, conc_factor=F, E=1.5e-3*max(1,F/12)), "free")["ratio"], F)
                for F in [4,6,8,12,16,24,40,60]])
    print("  K_oxyr=%.2f uM -> best concentration factor %2dx (fold %.3f)" % (K, best[1], best[0]))
