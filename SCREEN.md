# Biosensor module screen

Started as a simulator of one biosensor - diacetylspermine → DAS oxidase → H₂O₂
→ OxyR → GFP → phone camera - and is now a tool for deciding which sensing
module is worth building, for any biomarker with data in the two data files.

The kinetic core is unchanged. Two compartments, the cytoplasm quasi-steady,
the medium integrated explicitly, validated by reproducing the measured
ninefold medium/cytoplasm peroxide gradient with no fitting. What changed is
that no constant lives in the code any more, and that a candidate now has to
clear a clinical gate before anyone asks whether a sensor could read it.

## Running it

```bash
python screen.py                         # the traffic-light table
python screen.py --full                  # every sensor against every study
python enzymes.py                        # swap enzymes on one biomarker
python enzymes.py --biomarker DiAcSpm
python tests/test_regression.py          # prove the refactor changed no physics
```

## The two-stage filter

**Stage 1, clinical separation.** Can the published data tell sick from healthy
at all, given the spread and the sample size. A reported AUC decides when one
exists, because that is a ROC on the real patient-level data and beats anything
reconstructible from a summary table. Otherwise Welch's *t* and Cohen's *d* are
rebuilt from the central values, the spreads and the group sizes, and both must
clear their thresholds so a negligible effect measured at large *n* does not
pass. With neither available the verdict is `insufficient`, which is not a pass.

Stage 1 works on ratios and standardised differences, so it is unit-free. Rows
whose units cannot become µM still get a clinical verdict here; they die at
stage 2 instead.

One guard worth knowing about: when an SD had to be reconstructed from a
published range and comes out larger than the central value, a strictly
positive quantity cannot be anywhere near normal, so *d* and *p* describe
nothing. Those rows are called `insufficient`, not `fail` - the evidence is
missing, which is a different statement from the biomarker not separating. This
is what happens to the headline DAS row (CCR-04-2275): its sick range spans
0.035-24.6 µmol/g, a 700× spread, and DAS survives stage 1 on a different study
that does report an AUC.

**Stage 2, sensor feasibility.** Only for candidates that cleared stage 1.
Compares the clinical range with Km or Kd, computes the response, the sample
concentration factor required, and for type A whether the scavenger knockout is
needed.

## Three module types, three branches

| | mechanism | needs | amplifies | read time matters |
|---|---|---|---|---|
| **A** | analyte → oxidase → H₂O₂ → OxyR → promoter → GFP | `km_uM`, `kcat_s` | yes, catalytic | yes |
| **B** | analyte → TF → repression relieved → promoter → GFP | `kd_uM` | yes, transcriptional | yes |
| **C** | analyte → binding protein → conformation → fluorescence | `kd_uM` | no | no |

Type A is the original branch, the two-compartment ODE untouched. Type B enters
the same reporter through a Hill occupancy instead of through OxyR, with no
peroxide stage; the analyte is not consumed by a transcription factor, so the
activation is constant across the read. Type C has no transcription and no
reporter gene, so its response is the fold change in occupancy - converting
that to a measured fluorescence fold would need each protein's dynamic range,
which the sensor schema does not carry, so it is not estimated.

## Cross-reactivity

Cross-reactivity is not a parameter you set - it is read out of `sensors.csv`.
If the same `protein_name` appears against two different biomarkers and both
have the constant their type needs, that is published evidence the protein
binds both, and they compete. The competitor's concentration comes from
`clinical.csv` **restricted to the same study** - same DOI, same cancer, same
biofluid - because levels from another cohort would mix populations and assays.

For types B and C the readout is total occupancy over every binder:

&nbsp;&nbsp;&nbsp;&nbsp;θ = Σᵢ (Aᵢ/Kdᵢ) / (1 + Σᵢ (Aᵢ/Kdᵢ))

which reduces to A/(Kd+A) for a single binder, so nothing changes for a
specific sensor. Exact only at Hill n = 1, and the report says so if n ever
moves. For type A, cross-reactivity is competition for catalysis rather than
for a site, so it goes through the ODE's existing `interferent` and
`selectivity`, with selectivity derived as the ratio of kcat/Km when the data
supports it.

This matters: iPASnFR-H has **the same Kd of 15 µM for spermine and for
spermidine**, so a spermine sensor in urine also reads spermidine. Across the
eight type-C candidates that clear both stages, competition costs between 2% and
49% of the fold, depending on how much of the competitor that particular cohort
carries:

| sensor | study | alone | with competition | cost |
|---|---|---|---|---|
| Spermine / iPASnFR-H | pone.0162217 urine | 6.285 | 4.680 | 26% |
| Spermine / iPASnFR-L | pone.0162217 urine | 7.254 | 7.106 | 2% |
| Spermidine / iPASnFR-H | urine, total | 2.444 | 2.370 | 3% |
| Spermidine / iPASnFR-H | urine, free | 2.953 | 2.157 | 27% |
| Spermidine / iPASnFR-H | serum, total | 2.212 | 1.758 | 21% |
| Spermidine / iPASnFR-L | urine, total | 3.426 | 2.989 | 13% |
| Spermidine / iPASnFR-L | urine, free | 3.000 | 1.753 | 42% |
| Spermidine / iPASnFR-L | serum, total | 2.238 | 1.131 | 49% |

Note that competition can change which study is a sensor's best option: for
iPASnFR-H on spermidine the free-urine cohort looks better alone (2.953 vs
2.444) and worse once spermidine's competitor is included (2.157 vs 2.370). Any
before/after comparison therefore has to be made **within one study**, not
between a sensor's best row before and its best row after.

If a competitor binds but has no level in that study, the candidate is flagged
"interference could not be evaluated" rather than passed as if the competitor
were absent.

For DAS the screen states plainly that selectivity was never measured: DhaPAO is
listed against DiAcSpm only, so the scenario's selectivity of 100 is an
assumption, and the verdict says so instead of quietly relying on it.

## Traffic light

- **green** - passes at the scenario's own concentration factor
- **yellow** - passes with the sample concentrated, up to `conc_factor_max`
- **red** - fails; the reason and the stage that rejected it are always printed

Red reasons: no clinical separation, clinical data insufficient, no sensor data
(naming the missing constant), units not convertible to µM, analyte below Kd and
in the dead zone, analyte above Kd and saturated, or fold below what the reader
resolves.

Negative results are printed in full. `python screen.py` currently rejects 61
of 73 candidate pairs, and those rejections are the result.

## Data files

Nothing is configured in code. Every number belonging to a biomarker, an
enzyme or a disease is in `data/`.

| file | holds |
|---|---|
| `sensors.csv` | sensing elements: the 13 columns of the agreed schema. An empty cell means no data, which is a legal state |
| `clinical.csv` | clinical distributions: 18 columns, one row per biomarker × cancer × biofluid × study |
| `platform.csv` | chassis, reporter, reader and thresholds - nothing biomarker-specific |
| `scenarios.csv` | assay design and sample assumptions, by scenario name |
| `units.csv` | how each unit becomes µM, and which ones cannot |
| `spread.csv` | how each kind of published spread becomes an SD |

Units are resolved once, at load. Everything downstream is µM, s and s⁻¹.
Ten unit systems appear in `clinical.csv`; four of them (per mg tissue, per mg
DNA, log₂ ratios, and "units not stated") cannot reach µM at all and say so.
Creatinine-normalised units can, but only given an assumed urine creatinine,
which is a property of the sample and therefore lives in `scenarios.csv`.

**No invented numbers.** A missing constant stops the calculation for that
candidate and prints which parameter is absent. Nothing is defaulted and
nothing is estimated from a similar protein.

## Two data corrections

**Km of DhaPAO.** The code carried 83 µM. `build_doc.py:249` documents 83 and
310 µM as two values published in the same paper for different buffers, with
310 kept in the robustness grids - so 83 was a deliberate point estimate, not
an oversight. Both are now rows in `sensors.csv`: 310 µM is the working value
and 83 µM is marked as the alternative buffer and still used by the robustness
sweeps. This matters because kcat/Km moves 1.90 → 0.51 µM⁻¹s⁻¹ between them,
and that is the quantity the enzyme comparison ranks on.

**Module types.** Five of the nine rows in the source spreadsheet carried a
letter that contradicts the mechanism: both iPASnFR variants and both lactate
sensors are fluorescent binding proteins (C) rather than enzymes or TFs, and
BetI is a repressor (B). They are classified by mechanism here, with the
original letter recorded in each row's `notes`.

## Regression

`tests/baseline_km83_pre_refactor.txt` is the verbatim output of all seventeen
analysis scripts from before this refactor, at git `637ca14`, with Km at 83 µM.

`tests/test_regression.py` re-runs those scripts against the refactored model
with Km pinned back to the alternative-buffer row of `sensors.csv` and requires
byte-identical output. It passes for all seventeen, which is what licenses the
claim that pulling the constants out of the code moved no physics. The only
number that moves in normal operation is the Km itself.

Those seventeen scripts still contain DAS-specific numbers inline, and
deliberately so: they are the fixture that proves the refactor was behaviour
preserving, and stripping their constants would destroy the evidence. The
platform code - `das_model.py`, `sensorlab/`, `screen.py`, `enzymes.py` -
contains none. The one exception is marked in `das_model.analyte_in_biofluid`
and explained there.

## What the enzyme comparison shows

For DAS, catalytic efficiency spans 142× across the three enzymes (OpaPAO1
72.2, OpaPAO3 1.63, DhaPAO 0.51 µM⁻¹s⁻¹) and the fold change spans 1.06×.
Below Km the branch is first order in kcat/Km, so efficiency sets how little
enzyme you must load - OpaPAO1 needs 23 pM against DhaPAO's 3.3 nM for the same
95% turnover - while the fold is capped by how much peroxide the analyte can
make against the cell's own flux, a ceiling the enzyme does not move. Two orders
of catalytic efficiency buy enzyme loading, not signal.
