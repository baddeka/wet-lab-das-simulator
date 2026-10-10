import das_model as D, itertools
OP = dict(D.DEFAULTS, OD=0.05, k_scav=700., conc_factor=12., sample_frac=0.50,
          E=1.5e-3, T_read=1800., P_endo=4.0, mu=1e-6, V_das=250.)
GRID = dict(K_oxyr=[0.02,0.10,0.20], n_hill=[1.0,2.0], P_endo=[4.0,14.0], Km=[83.0,310.0])
keys = list(GRID)
print("combinations where MORE enzyme still helps (claim fails):")
for v in itertools.product(*[GRID[k] for k in keys]):
    c = dict(zip(keys, v)); q = dict(OP); q.update(c)
    lo = D.discriminate(dict(q, E=1.5e-3), "free")["ratio"]
    hi = D.discriminate(dict(q, E=1.0), "free")["ratio"]
    conv = D.response(dict(q, E=1.5e-3), "free")
    if hi > lo*1.02:
        print("   Km=%3.0f K=%.2f n=%.0f P=%4.1f | fold %.3f -> %.3f | DAS converted at low E: %.0f%%"
              % (c["Km"], c["K_oxyr"], c["n_hill"], c["P_endo"], lo, hi,
                 100*(1-conv["das_left"]/conv["das_assay"])))
