# DAS Branch Simulator

Interactive two-compartment model of a whole-cell biosensor for **N1,N12-diacetylspermine
(DAS)**, a urinary biomarker for colorectal cancer.

The signal chain is `DAS → DAS oxidase → H₂O₂ → OxyR → GFP → phone reader`. The page lets
you set the reagents, the culture and the reader, and reports the one number that decides
whether the device works: the fold change between a healthy sample and one at the clinical
cutoff, against the noise the reader can actually resolve.

**[Open the simulator →](https://baddeka.github.io/wet-lab-das-simulator/)**

## What the model says

The intuitive design fails, and it fails for a different reason than it first appears.

- **The competitor is a flux, not a threshold.** *E. coli* produces about 14 µM/s of H₂O₂
  in its own cytoplasm. At a conventional working density of OD₆₀₀ = 1, the biomarker
  contributes under 1 % of that. The OxyR trigger point was never the binding constraint.
- **Signal-to-background is governed by `S₀ / (φ · P_endo · T)`.** The scavenging rate
  constant cancels — it divides signal and background identically. So does the enzyme,
  provided conversion completes within the incubation.
- **Deleting the scavengers makes it worse.** A `ΔkatG ΔkatE ΔahpCF` background raises
  resting cytoplasmic H₂O₂ from 0.02 µM to ~2.8 µM, against an OxyR half-activation point
  of 0.1 µM. The reporter starts the assay switched on; S/B falls about 30-fold.
- **Overexpressing the oxidase is unnecessary and mildly harmful.** ~1 nM converts the
  delivered DAS in half an hour. 1 µM converts it in 0.4 s, and that spike is then diluted
  out by growth before the read.
- **Cell density is the strongest lever and it is free.** φ sits in the denominator and
  spans two decades. OD₆₀₀ 1 → 0.05 is worth about 20×.
- **Hydration can invert the classes.** The diagnostic difference is 1.67×; urine
  creatinine spans 4×. A cancer-positive sample in dilute urine presents *less* DAS than a
  healthy sample in concentrated urine. Creatinine has to be measured in parallel.

Delivering a properly quoted net 6–8× of cleaned-up sample, at OD₆₀₀ ≈ 0.05, on non-growing
cells, read at 30 min recovers roughly 500× and brings the fold change to ≈ 1.20 — resolvable
by a reader with a 5 % CV in triplicate.

## Parameters and their anchors

| Quantity | Value | Source |
|---|---|---|
| Endogenous cytoplasmic H₂O₂ production `P_endo` | ≈ 14 µM/s | Seaver & Imlay, *J. Bacteriol.* 2001 |
| Resting cytoplasmic H₂O₂ | ≈ 0.02 µM | same |
| Scavenging `k_scav` (wild type) | ≈ 700 s⁻¹ | forced by the two above |
| Membrane exchange `k_mem` | ≈ 90 s⁻¹ | permeability 1.6×10⁻³ cm/s × S/V ≈ 6 µm⁻¹ |
| Cytoplasm volume fraction `φ` | 8×10⁻⁴ per OD₆₀₀ | 8×10⁸ cells/mL at OD 1, ~1 fL each |
| OxyR half-activation | ≈ 0.1 µM cytoplasmic | Åslund et al. *PNAS* 1999; Imlay reviews |
| DAS oxidase `kcat` / `Km` | 158 s⁻¹ / 310 µM | Bakke, Shimoji & Kajiyama 2007, *BBA* 1774:1395 |

That paper reports two values of `Km`, 83 and 310 µM, for different buffers. The page now uses 310; `data/sensors.csv` carries both, and the robustness sweeps still run over the pair. The assay sits far below `Km` either way, so the choice changes the minimum enzyme loading and not the verdict: the fold at the recommended operating point moves from 1.198 to 1.174 and stays separable.


Nothing is fitted. The parameters over-determine the system, and the check is that they
reproduce a fifth, independently measured quantity: the ~9-fold medium-to-cytoplasm H₂O₂
gradient in wild-type cells. The model gives 8.8.

## Where the numbers live

No constant is written into the page any more. `build_site.py` reads `data/platform.csv`,
`data/scenarios.csv`, `data/sensors.csv` and `data/web_presets.csv` and injects them into
`index.html` as a single JSON block; the page reads its starting state from that block and
nothing else. To change what the published page computes, edit a CSV and rebuild — never a
number in `site.html`. `tests/test_site.py` fails if the two disagree, which is how the
`Km` of 83 µM was able to outlive its own correction before.

The same data files drive a separate screening tool that asks which sensing module is worth
building at all, across biomarkers and across module types. See [SCREEN.md](SCREEN.md).

```bash
pip install -r requirements.txt
python build_site.py --sync     # rebuild index.html from the data files
python tests/test_site.py       # page and data agree
python tests/test_branches.py   # the model's own unit checks
python tests/test_regression.py # 17 legacy scripts still reproduce their baseline
python screen.py                # the module screen
```

## Read it as a design tool, not a prediction

Three quantities are unmeasured and any of them can close the branch:

1. whether DAS crosses the inner membrane at all — native Pot transporters handle
   N-acetylated polyamines poorly, and the cytoplasmic architecture fails outright without it;
2. how selective the oxidase is against the more abundant urinary acetylpolyamines — a
   selectivity of 10 destroys the measurement, 100 is workable, 1000 is comfortable;
3. whether creatinine can be measured in parallel.

## Numerics

Cytoplasm is quasi-steady on a millisecond timescale and is eliminated adiabatically. The
medium is integrated explicitly with an exponential integrator, because at low cell density
it equilibrates over minutes rather than instantly. Substrate depletion is stepped
exponentially, so the scheme is stable for any enzyme loading. It agrees with a stiff
reference solver (`scipy` LSODA) to within 0.12 % across nine scenarios spanning four
decades of signal.

## Running it

It is a single static file with no build step and no dependencies. Open `index.html`, or
serve the directory:

```bash
python -m http.server 8000
```

---

Built for the iGEM colorectal-cancer detection project, NU-Kazakhstan.
