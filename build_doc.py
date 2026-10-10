# -*- coding: utf-8 -*-
"""Rebuild the wet-lab document, reusing the original paragraph and table XML
so that every new element carries exactly the original formatting."""
import copy, os
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC = r'C:\Users\mi\Downloads\wet lab das calculations.docx'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wet lab das calculations.docx')

doc  = Document(SRC)
body = doc.element.body
kids = [c for c in body if c.tag.split('}')[1] in ('p', 'tbl')]

T = dict(h=kids[0], p=kids[1], bul=kids[2], eq=kids[12], blank=kids[15],
         cap=kids[16], sub=kids[29], num=kids[41], tbl4=kids[14], tbl3=kids[20])

def _protos(el):
    out = {}
    for r in el.findall(qn('w:r')):
        rPr = r.find(qn('w:rPr'))
        bold = rPr is not None and rPr.find(qn('w:b')) is not None
        out.setdefault(bool(bold), copy.deepcopy(r))
    return out

def _set_run(r, text, bold):
    rPr = r.find(qn('w:rPr'))
    if rPr is None:
        rPr = OxmlElement('w:rPr'); r.insert(0, rPr)
    for tag in ('w:b', 'w:bCs'):
        el = rPr.find(qn(tag))
        if bold and el is None:
            rPr.append(OxmlElement(tag))
        elif not bold and el is not None:
            rPr.remove(el)
    for child in list(r):
        if child.tag != qn('w:rPr'):
            r.remove(child)
    t = OxmlElement('w:t'); t.set(qn('xml:space'), 'preserve'); t.text = text
    r.append(t)
    return r

def para(kind, segments):
    """segments: str, or list of (text, bold)."""
    if isinstance(segments, str):
        segments = [(segments, kind in ('h', 'sub'))]
    tpl = T[kind]
    p = copy.deepcopy(tpl)
    pr = _protos(p)
    if not pr:
        pr = {False: copy.deepcopy(_protos(T['p'])[False])}
    for r in p.findall(qn('w:r')):
        p.remove(r)
    for text, bold in segments:
        base = pr.get(bold)
        if base is None:
            base = pr.get(not bold)
        p.append(_set_run(copy.deepcopy(base), text, bold))
    return p

def blank():
    b = copy.deepcopy(T['blank'])
    for r in b.findall(qn('w:r')):
        b.remove(r)
    return b

def table(rows):
    ncol = len(rows[0])
    tbl = copy.deepcopy(T['tbl4'] if ncol == 4 else T['tbl3'])
    trs = tbl.findall(qn('w:tr'))
    head_tpl, body_tpl = copy.deepcopy(trs[0]), copy.deepcopy(trs[1])
    for tr in trs:
        tbl.remove(tr)
    for i, row in enumerate(rows):
        tr = copy.deepcopy(head_tpl if i == 0 else body_tpl)
        tcs = tr.findall(qn('w:tc'))
        for tc, text in zip(tcs, row):
            ps = tc.findall(qn('w:p'))
            for extra in ps[1:]:
                tc.remove(extra)
            cp = ps[0]
            pr = _protos(cp)
            for r in cp.findall(qn('w:r')):
                cp.remove(r)
            base = pr.get(i == 0)
            if base is None:
                base = pr.get(i != 0)
            if base is None:
                base = copy.deepcopy(_protos(T['p'])[False])
            cp.append(_set_run(copy.deepcopy(base), text, i == 0))
        tbl.append(tr)
    return tbl

OUT_EL = []
def H(t):   OUT_EL.append(para('h', t))
def S(t):   OUT_EL.append(para('sub', t))
def P(x):   OUT_EL.append(para('p', x if isinstance(x, list) else [(x, False)]))
def EQ(t):  OUT_EL.append(para('eq', [(t, False)]))
def B(lead, rest): OUT_EL.append(para('bul', [(lead, True), (rest, False)]))
def BP(t):  OUT_EL.append(para('bul', [(t, False)]))
def N(lead, rest): OUT_EL.append(para('num', [(lead, True), (rest, False)]))
def TBL(rows, caption):
    OUT_EL.append(table(rows)); OUT_EL.append(blank())
    OUT_EL.append(para('cap', [(caption.split('|')[0], True), (caption.split('|')[1], False)]))

# ===========================================================================
H("1. The signal chain and what each part is for")
P("The DAS branch converts a biomarker that the cell cannot sense directly into a fluorescent output through a four-step chain. Each element has a defined job:")
B("DAS (target). ", "N1,N12-diacetylspermine, molar mass 286.42 g/mol (C14H30N4O2). The urinary biomarker to be measured.")
B("DAS oxidase (transducer). ", "The recombinant enzyme from D. hansenii. It oxidizes DAS and, in doing so, generates hydrogen peroxide. Its job is to turn a chemically silent polyamine into H2O2, a molecule the cell already has machinery to detect. The yeast enzyme is chosen over the native E. coli activity because it is far more DAS-specific and about 630 times more active. That 630-fold figure compares enzyme against enzyme on the same substrate; it says nothing about how well either one discriminates DAS from the other polyamines present in urine, which is a separate specification and is treated in Section 8.")
B("H2O2 (intracellular messenger). ", "The one-to-one product of the reaction. It is the quantity that actually drives the reporter. It is also produced continuously by the cell's own metabolism, and that competing source, rather than any threshold, turns out to be the quantity the design has to beat.")
B("OxyR (switch). ", "A native E. coli transcription factor that is oxidized by H2O2, forming a disulfide bond that activates it. Once activated, it turns on its target promoter. It is oxidized at a rate proportional to peroxide concentration and re-reduced continuously by glutaredoxin, so its activation reports a steady state rather than a cumulative dose.")
B("Reporter (readout). ", "A fluorescent protein (GFP) placed under an OxyR-responsive promoter. Fluorescence is proportional to OxyR activation, which is proportional to H2O2, which is proportional to DAS.")
B("Enzyme location (the open design choice). ", "The chain as drawn does not say where the oxidase sits: in the cytoplasm, in the periplasm or displayed on the surface, or free in the sample alongside the cells. The chemistry is identical in all three. The substrate access, the achievable enzyme loading and the losses are not, and Section 7 shows that this single unstated choice decides whether the branch works at all.")
P("The reaction and its stoichiometry, which set the ceiling on how much messenger can be produced, are:")
EQ("DAS + O2  →  N-acetylspermidine + 3-acetamidopropanal + H2O2")
P([("The key fact for everything below: ", False), ("one molecule of DAS yields at most one molecule of H2O2.", True), (" That is a hard ceiling on the total amount of messenger, and no part of the design can exceed it. It is not, however, a statement about the concentration the reporter sees. H2O2 is never stored; it is made and destroyed continuously, so what reaches OxyR is a steady state between rates. Sections 3 to 5 work with that steady state rather than with the ceiling, because the ceiling turns out not to be the binding constraint.", False)])

H("2. What the sensor must detect (the target window)")
P("Urinary DAS is reported normalized to creatinine, in nmol per gram of creatinine, because raw concentration depends heavily on hydration. Reported reference points are: a healthy median of roughly 147 to 162 nmol/g creatinine, clinical cutoffs of about 200 (male) and 250 (female) nmol/g creatinine, and, for colorectal cancer, a cutoff of about 0.25 umol/g creatinine (mean of healthy plus 2 standard deviations). To turn these into a molar concentration the sensor actually sees, they are multiplied by the urine creatinine concentration:")
EQ("CDAS (µM) = [ V (nmol/g cr) × Cr (g/L) ] / 1000")
P("Taking a representative spot-urine creatinine of Cr ≈ 1 g/L (typical range 0.5 to 2 g/L), and converting to mass with the molar mass 286.42 g/mol, gives the working window:")
TBL([["Group", "DAS (nmol/g cr)", "C_DAS (µM)", "Mass (µg/L)"],
     ["Healthy median", "~150", "~0.15", "~43"],
     ["Cutoff (male)", "200", "0.20", "57"],
     ["Cutoff (female)", "250", "0.25", "72"],
     ["CRC positive", "> cutoff, often 0.25 to ~1", "0.25 to ~1", "72 to ~286"]],
    "Table 1. |Urinary DAS reference values converted to molarity at Cr = 1 g/L. Because concentration scales with creatinine, the same nmol/g value maps to roughly 0.5 to 2 times these molarities across normal hydration, which is exactly why creatinine normalization is needed.")
P("Two conclusions follow. First, the whole diagnostic window sits in the sub-micromolar range, roughly 0.15 uM (healthy) versus 0.25 uM and above (CRC). Second, detection is not enough: to call a result the sensor must resolve the difference between about 0.15 and 0.25 uM, a factor of 1.67. This is a demanding specification and is the reason the summary calls DAS extremely low and hard to quantify.")
P("A third conclusion follows from the same arithmetic and dominates the other two. The diagnostic quantity is the ratio V, in nmol per gram of creatinine, but the sensor responds to the molarity C_DAS, and the two are joined by the creatinine concentration. Across the normal hydration range Cr spans 0.5 to 2 g/L, a factor of four. The pre-analytical confounder is therefore larger than the diagnostic difference it has to be measured against, and the two are not merely comparable in size, they overlap:")
TBL([["Sample", "V (nmol/g cr)", "Cr (g/L)", "C_DAS the sensor sees (µM)"],
     ["CRC at the cutoff, dilute urine", "250", "0.5", "0.125"],
     ["Healthy median, typical urine", "150", "1.0", "0.15"],
     ["CRC at the cutoff, typical urine", "250", "1.0", "0.25"],
     ["Healthy median, concentrated urine", "150", "2.0", "0.30"]],
    "Table 2. |The same two clinical categories ordered by the molarity that reaches the sensor. A CRC-positive sample in dilute urine presents less DAS than a healthy sample in concentrated urine: the classes invert. No amount of downstream sensitivity repairs this, because the information needed to correct it is not present in the fluorescence channel at all.")
P("The consequence is a requirement on the device rather than on the biology: creatinine has to be measured on the same sample, in parallel, and the reported result has to be the ratio. The cheapest route is a second colorimetric channel using the Jaffe reaction, read from the same photograph as the fluorescence channel. The alternative uses machinery the design already contains: make the concentration step of Section 6 sample-specific, concentrating each sample by a factor Cr_target / Cr so that every sample arrives at the assay already normalized to the same creatinine. Either route is acceptable. A single-channel fluorescence device is not.")

H("3. What the reporter actually responds to (the crux)")
P("OxyR does not respond to arbitrarily small amounts of H2O2. The figure usually quoted is that the response is triggered above about 2 uM H2O2 added to the medium, with growth impaired above about 5 uM. Both numbers are sound, but they are properties of a particular experiment rather than constants of the protein, and they cannot be set directly against the DAS budget without two conversions.")
P("The first conversion is across the membrane. Wild-type E. coli destroys peroxide fast enough that its cytoplasm sits roughly nine times below the medium, so an external 2 uM corresponds to about 0.2 uM inside. What OxyR senses is the inside value, and the half-activation point of the regulon is about 0.1 uM cytoplasmic H2O2, with full induction approached near 1 uM. The second conversion is from an amount to a rate. OxyR is not titrated by a stock of peroxide; it is oxidized at a rate proportional to concentration and reduced again on a timescale of minutes, so the activation it reports is set by a balance of fluxes and not by a cumulative dose.")
P("Making both conversions changes what the central comparison is. The competitor to the DAS signal is not a threshold at all. It is the cell's own peroxide production: E. coli generates about 14 uM/s of H2O2 in its cytoplasm from the autoxidation of flavoenzymes, every second, with or without a sample present. Over a one-hour assay that is roughly 50 000 uM of peroxide per litre of cytoplasm. The biomarker, spread from the medium into the very much smaller volume the cells occupy, contributes the following against it:")
TBL([["Assay condition", "H2O2 from DAS, per litre of cytoplasm (µM)", "Share of the cell's own output"],
     ["0.25 µM DAS, OD600 = 1.0", "313", "0.6 %"],
     ["0.25 µM DAS, OD600 = 0.1", "3 130", "6.2 %"],
     ["0.25 µM DAS, OD600 = 0.01", "31 300", "62 %"],
     ["endogenous, any density", "50 400", "100 %"]],
    "Table 3. |The two sources of cytoplasmic H2O2 over a one-hour assay, both expressed per litre of cytoplasm. The DAS contribution is fixed by the patient sample; the endogenous contribution is fixed by metabolism. Their ratio depends only on how much cytoplasm the sample has to be shared among, which is to say on the cell density.")
P("This is the make-or-break result, and it is a different one from the version in Table 2 of the earlier draft. The branch does not fail because 0.25 uM of DAS cannot climb to a 2 uM threshold. It fails, at the conventional working density of OD600 = 1, because the biomarker contributes well under one percent of the peroxide the cell is already making, so the reporter cannot tell the sample from the blank. The threshold was never the binding constraint. The competing flux is. The encouraging part is that the competing flux appears divided by a quantity the experimenter sets directly with a pipette.")

H("4. The two-compartment balance and where its numbers come from")
P("H2O2 inside the cell is not a static pool. It is produced by the enzyme, produced again by the cell's own metabolism, exchanged across the membrane with the medium, and consumed by the native catalases (KatG, KatE) and by alkyl hydroperoxide reductase (AhpCF). The earlier draft wrote this as [H2O2]ss = vproduction / kscavenging. That is correct as far as it goes, but it describes a single well-mixed box, and the two facts that matter most are the ones a single box cannot express: that the endogenous source is inside while the biomarker is outside, and that the membrane is a finite resistance between them. Writing one balance per compartment:")
EQ("d[H2O2]cyt/dt = P_endo + v_cyt + k_mem·([H2O2]med − [H2O2]cyt) − k_scav·[H2O2]cyt")
EQ("d[H2O2]med/dt = v_med + φ·k_mem·([H2O2]cyt − [H2O2]med) − k_chem·[H2O2]med")
P("Here φ is the fraction of the assay volume occupied by cytoplasm, k_mem is the first-order rate of exchange across the membrane, k_chem is any chemical loss of peroxide in the medium, and v_cyt and v_med are the enzymatic production rates in whichever compartment the oxidase actually sits. The parameters are not free; three published measurements fix them:")
B("P_endo ≈ 14 µM/s. ", "Endogenous cytoplasmic H2O2 formation in aerobically growing E. coli (Seaver & Imlay 2001).")
B("k_scav ≈ 700 s⁻¹ in wild type. ", "Not measured directly but forced by the two numbers above and below it: the same work measures a resting cytoplasmic level of about 0.02 µM, and 14 / 0.02 = 700.")
B("k_mem ≈ 90 s⁻¹. ", "The membrane permeability to H2O2, about 1.6 × 10⁻³ cm/s, multiplied by the surface-to-volume ratio of an E. coli cell, about 6 µm⁻¹.")
B("φ ≈ 8 × 10⁻⁴ per OD600 unit. ", "From roughly 8 × 10⁸ cells per mL at OD600 = 1 and a cell volume near 1 fL.")
P("These four numbers over-determine the system, which is what makes the model falsifiable rather than merely plausible. The check is that they must reproduce a fifth quantity measured independently: the roughly nine-fold gradient between medium and cytoplasm seen in wild-type cells at low density. The model gives 1 + k_scav/k_mem = 8.8. Nothing was fitted to obtain that, and if the team's own measurements disagree with it, one of the four inputs is wrong and the rest of this document has to be recomputed.")
P("The practical reading of the balance also differs from the earlier draft. It remains true that a wild-type strain keeps the messenger near baseline. It is not true that the baseline is what limits the measurement, and Section 6 shows that removing the scavengers makes the measurement worse rather than better.")

H("5. The one expression that governs the design")
P("Both the biomarker peroxide and the endogenous peroxide are consumed by the same scavengers and read by the same reporter, so each contributes to the cytoplasmic pool in proportion to how much of it is made. Integrating the two balances over the assay and taking the fluorescence above blank divided by the blank gives, in the regime where the reporter is not saturated:")
EQ("S/B  =  S0 / ( φ · P_endo · T )  ×  s")
P("S0 is the DAS concentration presented to the assay, φ the cytoplasmic volume fraction, T the incubation time, and s a factor below one that collects the local slope of the OxyR dose-response and the dilution of reporter protein by growth. Across a hundred-fold range of cell density the numerical model gives s = 0.40 ± 0.02, so this is a working formula rather than a hand-waving proportionality.")
P("What is absent from it matters as much as what is present.")
P([("The scavenging rate constant does not appear. ", True), ("It divides signal and background identically and cancels. Deleting katG, katE and ahpCF therefore cannot improve signal-to-background. What it does do is raise the resting cytoplasmic peroxide from 0.02 uM towards several uM, which pushes the reporter past its half-activation point and spends the dynamic range on the blank.", False)])
P([("The enzyme does not appear either. ", True), ("Neither kcat, nor Km, nor the expression level enters, provided only that the enzyme converts the available DAS inside the incubation time. At the published kcat of 158 s-1 and Km of 83 uM, about 1 nM of oxidase consumes the DAS in half an hour, and 1 uM consumes it in under a second. The 630-fold activity advantage of the D. hansenii enzyme is real, but it is spent long before it is needed.", False)])
P([("Three quantities do appear, and all three are set by the operator rather than by the biology: ", False), ("how much biomarker is delivered, how much cytoplasm it is shared among, and how long the background is allowed to accumulate.", True), (" Applying them in turn to the CRC cutoff sample:", False)])
TBL([["Step", "Factor", "Signal-to-background at the cutoff"],
     ["raw urine, OD600 = 1.0, growing cells, 60 min read", "none", "0.002"],
     ["+ concentrate 12x, sample at 50 % v/v", "x 6", "0.014"],
     ["+ cell density OD600 1.0 to 0.05", "x 20", "0.24"],
     ["+ read at 30 min instead of 60", "x 2", "0.32"],
     ["+ non-growing, carbon-limited cells", "x 3.5", "1.04"]],
    "Table 4. |Signal-to-background at the CRC cutoff (250 nmol/g creatinine, Cr = 1 g/L), computed from the two-compartment model rather than from the formula, so the two agree only because the model behaves as the formula predicts. The cumulative gain is about 500-fold, and none of it comes from the enzyme or from a knockout.")

H("6. Design levers, with numbers")
S("Lever A. Deliver more of the biomarker")
P("The reference colorimetric DAS assay concentrated urine about 15 times before detection, and the earlier draft carried that factor straight through. It cannot be carried straight through, because a concentrated urine sample still has to be put into an assay that contains cells. What reaches the cells is the concentration factor multiplied by the volume fraction of the sample in the final well. Concentrating 15-fold and then adding the sample at 10 percent v/v is a net delivery factor of 1.5, not 15. The two steps have to be quoted together or the number means nothing.")
P("The second correction is that more is not better. The delivery factor decides where the sample lands on the OxyR dose-response, and once the cutoff sample pushes cytoplasmic peroxide past the half-activation point of about 0.1 uM the curve flattens and the two clinical classes converge again. Signal-to-background keeps rising while the ability to tell them apart falls:")
TBL([["Concentration factor", "Net delivery at 50 % v/v", "Peak cytoplasmic H2O2 (uM)", "Fold F(250)/F(150)"],
     ["4x", "2x", "0.025", "1.124"],
     ["8x", "4x", "0.045", "1.175"],
     ["12x", "6x", "0.065", "1.198"],
     ["16x", "8x", "0.097", "1.201"],
     ["24x", "12x", "0.168", "1.191"],
     ["40x", "20x", "0.332", "1.166"],
     ["80x", "40x", "0.794", "1.135"]],
    "Table 5. |The delivery factor has an optimum, not a maximum. It lies near a net 6 to 8x, which places the cutoff sample just below the OxyR half-activation point where the dose-response is steepest. Beyond about 20x the assay becomes more sensitive and less diagnostic at the same time, which is the failure mode the earlier draft was reaching for when it warned against overshooting into the toxic range.")
P("How the concentration is done matters as much as how much. Lyophilizing and resuspending concentrates the salts, the urea and the urate along with the analyte, and 12-fold concentrated urine is not a medium cells survive in. Solid-phase extraction on a strong cation exchanger does the same job better: polyamines are protonated and retained at acidic pH while urate, ascorbate and most of the salt pass through, and elution into a small volume delivers concentration and clean-up in one step. That second function is not cosmetic. Urate is present in urine at 1.5 to 4.5 mM and ascorbate at up to 2 mM, and both consume peroxide in the medium, which is the k_chem term of Section 4. The model tolerates k_chem up to about 0.01 s-1 and loses the measurement entirely at 0.1 s-1. Cation-exchange clean-up also strips the creatinine, which is why Section 2 asks for creatinine to be measured on the raw sample before this step rather than after it.")
S("Lever B. Keep the scavengers (this reverses the earlier recommendation)")
P("The earlier draft proposed deleting katG, katE and ahpCF, on the argument that collapsing k_scav raises the steady state for the same production rate. The first half of that is true and the conclusion does not follow, because the same collapse raises the endogenous baseline by exactly the same factor. Running the model across the range gives a resting cytoplasmic level of 0.02 uM at the wild-type k_scav of 700 s-1, 0.28 uM at 50 s-1, and 2.8 uM in a full Hpx- background. The half-activation point of OxyR is 0.1 uM, so the knockout strain begins the assay with its reporter already switched on. Signal-to-background at the cutoff falls from 0.030 in wild type to 0.001 in Hpx-, a thirty-fold loss, and the cells are carrying a peroxide load high enough to impair growth while they do it.")
P("This is a case where the intuition from the H2O2 biosensor literature does not transfer. Scavenger-deficient strains are used to detect a small bolus applied from outside against a background the experimenter controls. Here the background is generated inside the same compartment as the signal, and no manipulation that acts on both can separate them. The quantity worth lowering is P_endo, not k_scav, and the two are not interchangeable: endogenous peroxide comes from flavoenzyme autoxidation and scales with metabolic flux, so assaying non-growing cells resuspended in a carbon-limited buffer lowers the background without touching the machinery that keeps the reporter in its linear range. A factor of three to four is a reasonable expectation, which is worth as much as the entire concentration step.")
S("Lever C. Use just enough enzyme (this also reverses the earlier recommendation)")
P("Overexpression was proposed in order to push conversion toward completion. Conversion does need to complete, but the bar is far lower than it looks and overshooting it costs signal. About 1 nM of oxidase converts the delivered DAS within half an hour; 1 uM converts it in 0.4 seconds. Delivering the whole peroxide budget as a spike at the start is worse than delivering it steadily, because reporter made in the first minute is then diluted by growth for the rest of the hour, and because a spike overshoots the linear range while the time-average stays low. In the model, signal-to-background peaks near 1 nM and falls by about a fifth on the way to 1 uM. The design target for expression is therefore an upper bound as well as a lower one, which is an easier specification to hit than the one it replaces.")
S("Lever D. Lower the cell density (the largest single lever, and it is free)")
P("The volume fraction phi sits in the denominator of the master expression and spans two decades of accessible values. Moving from OD600 = 1 to OD600 = 0.05 is a twenty-fold gain in signal-to-background and costs nothing but a dilution. It is not unbounded: total fluorescence scales with phi, so the floor is set by how little GFP the reader can see, and below about OD600 = 0.01 the cutoff sample begins to saturate its own smaller cytoplasm, which flattens the discrimination again. The optimum in the model lies between OD600 = 0.03 and 0.1. The structural point matters more than the number: cell density is the strongest term in the entire design and it did not appear anywhere in the earlier draft.")
S("Lever E. Read early")
P("Reporter accumulates from both sources, but the biomarker is delivered once while the background is delivered continuously, so the ratio between them degrades with time. Reading at 30 minutes rather than 60 is worth a factor of two. The floor is set by GFP maturation, about 6 minutes for sfGFP, and by the time transcription and translation need to respond at all, so 20 to 40 minutes is the usable window. Overnight incubation, which is the natural habit, is the worst available choice here.")

H("7. Where the enzyme should sit")
P("The chain in Section 1 is silent about localization, and the three options are not equivalent. It is worth being precise about what does and does not change between them, because the intuitive answer is wrong in one direction and right in another.")
P("What does not change is the integrated signal. In a closed assay the only sink for peroxide is intracellular scavenging, so every molecule made anywhere eventually passes through a cytoplasm and is counted. Provided the DAS is fully converted within the incubation, the model gives essentially the same signal-to-background for a cytoplasmic, a periplasmic and a free enzyme. Localization is not a sensitivity multiplier.")
P("What does change is whether conversion happens at all, and what it costs to make it happen:")
TBL([["Architecture", "What limits it", "Fold F(250)/F(150) at the operating point"],
     ["Cytoplasmic", "transport of DAS across the inner membrane", "1.19, falling to 1.01 if uptake is 100x poorer"],
     ["Periplasmic or surface-displayed", "periplasm is only 1.3 x 10-5 of the assay volume at OD600 = 0.05", "1.13 at 30 uM enzyme, 1.19 at 100 uM"],
     ["Free enzyme in the sample", "nothing, but it is a two-step assay", "1.20"]],
    "Table 6. |The three architectures at the recommended operating point. The differences are entirely about delivering the substrate to the enzyme, not about delivering the product to the reporter.")
P("The cytoplasmic route carries the one genuinely unquantified risk in the whole design. DAS is a doubly acetylated polyamine of 286 Da: it crosses the outer membrane through porins without difficulty, but the inner membrane requires a transporter, and the native polyamine systems of E. coli, PotABCD and PotFGHI, are specific for free putrescine and spermidine and handle N-acetylated polyamines poorly. If uptake is a hundred-fold worse than free equilibration, the discrimination collapses from 1.19 to 1.01, which is to say the device stops working. Nothing else in this document has that property of failing completely rather than degrading, and no number in the literature currently settles it. It should be measured before anything else is built on top of it.")
P("The periplasmic route removes that risk, because porins pass the substrate freely, and it keeps the device a single organism, which is worth a great deal for a whole-cell diagnostic. Its cost is that the periplasm is a very small compartment. At the low cell densities Lever D calls for, the periplasm is about one part in 10^5 of the assay volume, so the periplasmic enzyme concentration has to reach roughly 100 uM for conversion to complete within half an hour. That is high but not unreasonable for a well-expressed periplasmic protein, and it interacts directly with Lever D: the lower the density, the higher the required loading. This is the trade-off the design should be tuned against.")
P("The free-enzyme route is the most robust and the least elegant. It converts a whole-cell biosensor into a two-step assay in which the biology contributes amplification and integration rather than recognition. That is a defensible position, but it should be a deliberate one, and it is worth noting the honest comparison: if the peroxide is going to be generated outside the cell anyway, a purely chemical peroxide readout such as Amplex Red has no endogenous background at all and is far easier to make sensitive. The case for keeping OxyR and GFP has to rest on amplification, on the integration of a transient signal, and on field-deployable lyophilized cells, not on raw detection limit.")

H("8. Specificity: the interference that is already in the sample")
P("Urine does not contain DAS alone. Free spermidine, N1-acetylspermidine, N8-acetylspermidine and N1-acetylspermine are all present, and at concentrations of roughly 1 to 5 uM they are five to twenty times more abundant than the 0.15 to 0.25 uM of DAS the assay is looking for. Any of them that the oxidase turns over produces peroxide that is chemically indistinguishable from the signal. This is a hard limit on the branch and it is independent of everything in Sections 3 to 7, because it corrupts the input rather than the transduction.")
P("The relevant quantity is the selectivity ratio, the specificity constant kcat/Km for DAS divided by that for the interfering substrate. The 630-fold figure quoted for the D. hansenii enzyme is not this number: it compares that enzyme against the native E. coli activity on the same substrate. The selectivity between substrates has not been measured for this enzyme and it is what the design actually depends on:")
TBL([["Interfering polyamines in urine", "Selectivity 10x", "Selectivity 100x", "Selectivity 1000x"],
     ["none", "1.198", "1.198", "1.198"],
     ["1 uM", "1.081", "1.173", "1.195"],
     ["2 uM", "1.048", "1.156", "1.193"],
     ["5 uM", "1.020", "1.123", "1.188"]],
    "Table 7. |Fold change between the healthy median and the CRC cutoff at the recommended operating point, as cross-reactive polyamines are added at realistic urinary levels. The interference is an additive offset that does not scale with DAS, so it compresses the ratio rather than shifting it. A selectivity of 10 destroys the measurement at any realistic interferent level; 100 is workable up to about 2 uM; 1000 is comfortable.")
P("Two consequences follow. The first is a measurement that belongs early in the experimental programme: run the purified oxidase against N1-acetylspermidine, N1-acetylspermine and spermidine at matched concentrations and report kcat/Km for each. That single panel decides whether the branch is viable, and it is cheap. The second is that if the selectivity turns out to be near 100 rather than 1000, the cation-exchange step of Lever A stops being a convenience and becomes the mechanism that makes the assay specific, which changes how it should be developed and validated.")

H("9. From OxyR to the phone reader")
P("The final output is fluorescence: DAS to H2O2 to oxidized OxyR to the OxyR promoter to GFP. The earlier draft stated the requirement correctly in words, that the biological fold-change across the DAS window must exceed the reader's own resolving limit, and the model now allows it to be stated as a number.")
P("At the recommended operating point the model gives a fold change of 1.198 between the healthy median and the female CRC cutoff. That is the entire signal the reader has to work with, and it is small because it has to be: the underlying clinical difference is only 1.67-fold and the transduction chain compresses rather than amplifies it. Whether it is enough depends on the reader's coefficient of variation and on the number of replicates, through the usual two-sample criterion that the log fold change must exceed z times the pooled relative standard deviation:")
EQ("z  =  ln(fold) / [ CV · sqrt(2/n) ]")
TBL([["Replicates", "CV = 3 %", "CV = 5 %", "CV = 10 %"],
     ["n = 1", "z = 4.2, separable", "z = 2.6, marginal", "z = 1.3, no"],
     ["n = 3", "z = 7.4, separable", "z = 4.4, separable", "z = 2.2, no"],
     ["n = 6", "z = 10.4, separable", "z = 6.3, separable", "z = 3.1, separable"]],
    "Table 8. |Whether the healthy and cutoff classes can be separated at the operating point, taking z = 2.8 as the threshold for roughly 95 percent sensitivity and specificity. The specification on the phone reader is therefore a CV of 5 percent or better with three replicates, or 10 percent with six. This is a demanding but not unreasonable requirement, and it is the number the Part I fluorimeter characterization should be measured against.")
P("Two cautions attach to this. First, the CV that matters is the total assay CV and not the reader's optical repeatability alone: pipetting, cell density between wells and incubation timing all enter it, and cell density enters it strongly because signal-to-background scales as 1/phi. Normalizing every reading to OD600 measured in the same well is therefore not optional. Second, all of the above concerns technical replicates of one sample. Biological variation between patients at the same disease state is wider than any of it, and the numbers here bound the analytical performance of the device, not its clinical performance.")

H("10. Limitations of this model")
P("Everything above is a model, and the recommendations in Section 6 are only as good as the assumptions under them. We have separated the limitations that could change the conclusions from the ones that only change the numbers, because those need very different responses from us.")
S("What could change the conclusions")
B("The shape of the OxyR transfer function is our largest single uncertainty. ", "We assumed a hyperbolic response, that is, a Hill coefficient of one. If the true response is cooperative with n = 2, the fold change at the recommended operating point rises from 1.20 to 1.81, and our conclusion that enzyme loading does not matter stops holding, because a sharper peak is then rewarded more than a steady average. Nothing we found in the literature settles this for the OxyR regulon in the sub-micromolar range. Experiment 1 measures it directly, which makes it the highest-value experiment we have.")
B("The half-activation point carries the operating point with it. ", "We used 0.1 uM cytoplasmic H2O2. Published estimates span roughly 0.02 to 0.2 uM, and that range moves the optimum concentration factor from 8x to 24x and the achievable fold change from 1.08 to 1.24. Our recommendation of a net 6 to 8-fold delivery is therefore conditional on the middle of that range, and we should treat it as the starting point of a titration rather than as a setting.")
B("We assumed the endogenous flux falls with metabolic state. ", "The recommendation to assay non-growing, carbon-limited cells assumes P_endo drops from about 14 to about 4 uM/s. That factor of three and a half is worth as much as our entire concentration step, so it is the least-supported number carrying the most weight in this document. It is also the cheapest thing on the list to check, which is why we put it second.")
B("Interference is treated as one lumped substrate whose level is independent of disease. ", "Neither half of that is safe. Urine carries at least four relevant acetylpolyamines with different specificity constants, and polyamine excretion rises in cancer generally, so the interferents partly co-vary with DAS. If they do, the effect is not added noise but a bias toward false positives, which is worse than noise and which our single selectivity number cannot express.")
S("What only changes the numbers")
B("The reporter layer is uncalibrated. ", "Promoter strength, basal leak and the fluorescence scale are estimates, not measurements. This is why we state every result as a ratio to a blank and never as an absolute fluorescence: the ratios survive a recalibration, the absolute values do not.")
B("Scavenging is a single first-order constant. ", "In the cell, AhpCF dominates below about 20 uM and saturates, and the catalases take over above it. One constant is adequate in the sub-micromolar range this design lives in, but it is not adequate for Experiment 1, where we add exogenous H2O2 at 0 to 10 uM. We have to fit that experiment with the two terms separated, or it will return a k_scav that applies nowhere else.")
B("The two published values of Km, 83 and 310 uM, differ by close to four-fold. ", "Because the assay runs far below Km, only kcat/Km matters, and the ambiguity changes the minimum enzyme requirement without changing any conclusion. We kept both values inside the sensitivity range rather than picking one.")
B("The chemical sink in the medium has a derived tolerance but no measured value. ", "We know the design survives k_chem up to about 0.01 s-1 and fails at 0.1 s-1. Where cleaned-up urine actually falls between those two is something we have not measured.")
S("Structural simplifications we accepted")
B("The assay is treated as closed, well mixed and uniform. ", "There is no headspace exchange, no oxygen gradient and no cell-to-cell variability. The last of those matters most: heterogeneity in enzyme expression broadens the population response and lowers the effective fold change, so the number we report is a population mean and is optimistic by an amount we cannot currently bound.")
B("DAS transport is a single equilibrium ratio, not a transporter. ", "There is no saturation, no energetics and no competition with the native polyamines. If uptake turns out to be carrier-mediated it will saturate somewhere in the working range, and the cytoplasmic architecture would then carry a nonlinearity this model does not show at all.")
B("The statistics bound analytical performance only. ", "Our separability criterion assumes independent replicates with equal relative variation, and it answers whether the device can tell two known concentrations apart. It says nothing about clinical sensitivity or specificity, for which we would need between-patient variation at the same disease state, and we do not have that data.")
S("What survives all of it")
P("We tested the three central claims across 24 combinations of the four most uncertain parameters, taking each across its full published range. Two of them held in every combination:")
TBL([["Claim", "Holds in", "Size of the effect across the grid"],
     ["Removing the scavengers is harmful", "24 of 24", "35 to 43 000-fold penalty"],
     ["Lowering cell density is the dominant lever", "24 of 24", "8 to 62-fold gain"],
     ["Enzyme loading does not matter", "19 of 24", "fails only where conversion is incomplete"]],
    "Table 9. |Robustness of the three claims that depart from the earlier draft, over a grid of the OxyR half-activation point (0.02 to 0.2 uM), the Hill coefficient (1 or 2), the endogenous flux (4 or 14 uM/s) and Km (83 or 310 uM). The fold change itself varies from 1.03 to 1.81 across that grid, so the numbers in this document are far less certain than the directions.")
P("The two recommendations that reverse the earlier draft, keep the scavengers and lower the cell density, hold everywhere we looked. The third, that enzyme loading does not matter, held in 19 of 24 combinations and failed only where the transfer function was cooperative or where Km sat at its upper published value, in both cases because the enzyme then stops finishing the conversion inside the incubation. So we are confident about the two reversals and conditional about the third, and the measurement that would settle it is the same one that resolves our largest uncertainty.")

H("11. Recommended order of experiments (decouple, then combine)")
N("Reporter dose-response to exogenous H2O2. ", "Add known H2O2 (0 to 10 uM) to the OxyR-reporter strain and record fluorescence. This gives the reporter's own threshold and dynamic range independent of the enzyme. Run it at two cell densities at least a decade apart: the apparent threshold should shift with density, and if it does not, the two-compartment picture of Section 4 is wrong.")
N("Resting background and its metabolic dependence. ", "Measure blank fluorescence for growing cells and for non-growing cells resuspended in carbon-limited buffer. This is a direct read on P_endo, which is the denominator of the whole design, and it is the cheapest experiment on this list.")
N("Enzyme selectivity panel. ", "Measure kcat/Km of the purified oxidase for DAS, N1-acetylspermidine, N1-acetylspermine and spermidine. Section 8 shows this can invalidate the branch on its own, so it should not wait.")
N("DAS uptake, if the enzyme is to be cytoplasmic. ", "Determine whether DAS reaches the cytoplasm at all, by radiolabel, by LC-MS on lysates, or by comparing whole-cell against lysate activity. This is the only failure mode in the document that is total rather than gradual.")
N("Enzyme output in vitro. ", "React purified or lysate DAS oxidase with known DAS and measure H2O2 produced per uM DAS per unit time, confirming that conversion completes inside the incubation window at the intended enzyme loading. Note that the aim is to confirm sufficiency, not to maximize it.")
N("Whole-cell DAS dose-response, as a two-dimensional titration. ", "Feed known DAS to the full strain across a grid of cell density and delivery factor, and build the calibration curve exactly as in the Part I protocol (green channel, OD normalization, background subtraction, replicates, LOD and LOQ). The prediction to test is that signal-to-background scales as 1/phi and that the fold change has an interior optimum in delivery factor.")
N("Close the loop on real samples. ", "Confirm that the fluorescence difference across 0.15 versus 0.25 uM urinary DAS is resolvable on the phone reader, with creatinine measured in parallel and the result reported as the ratio.")

H("12. Key numbers and sources")
BP("DAS molar mass 286.42 g/mol (C14H30N4O2); reaction stoichiometry 1 DAS to 1 H2O2 (project reaction scheme).")
BP("Urinary DAS: healthy medians ~147 (male) and ~162 (female) nmol/g creatinine; cutoffs ~200 and ~250 nmol/g creatinine; CRC cutoff ~0.25 umol/g creatinine. Colorimetric DAS assay detected <1 uM after ~15x concentration, LOD ~0.25 uM (Wishart group, Anal. Biochem. 2025; Hiramatsu 2014; BJC 2015).")
BP("Representative spot-urine creatinine ~1 g/L (range ~0.5 to 2 g/L) used for the nmol/g to uM conversion. Urinary urate 1.5 to 4.5 mM and ascorbate up to 2 mM, both peroxide-consuming and both removed by cation-exchange clean-up.")
BP("Endogenous cytoplasmic H2O2 production in E. coli ~14 uM/s, resting cytoplasmic level ~0.02 uM, medium-to-cytoplasm gradient ~9-fold in wild type (Seaver & Imlay, J. Bacteriol. 2001). These three fix P_endo, k_scav ~700 s-1 and, with the membrane permeability, k_mem ~90 s-1.")
BP("OxyR half-activation at ~0.1 uM cytoplasmic H2O2, full induction approached near 1 uM; reduction by glutaredoxin on a timescale of minutes (Aslund et al., PNAS 1999; Imlay, Annu. Rev. Biochem. 2008 and later reviews). The commonly quoted 2 uM trigger and 5 uM growth limit are extracellular values in wild-type cells and correspond to roughly 0.2 and 0.6 uM inside.")
BP("Cell volume fraction ~8 x 10-4 per OD600 unit (8 x 10^8 cells/mL at OD600 = 1, cell volume ~1 fL). Periplasm ~16 percent of cell volume.")
BP("DAS oxidase from D. hansenii: kcat 158 s-1, Km 83 to 310 uM depending on buffer, and ~630x more active than the native E. coli activity (Bakke, Shimoji & Kajiyama 2007, Biochim. Biophys. Acta 1774:1395). The 630x figure is an enzyme-versus-enzyme comparison and is not a selectivity between substrates; the selectivity has not been measured and Section 8 shows it is decisive.")
BP("sfGFP maturation half-time ~6 min; reporter dilution set by growth rate, which is why the assay should be run on non-growing cells and read early.")
P([("Bottom line: ", True), ("the earlier conclusion, that the branch falls short of the OxyR trigger by about an order of magnitude and needs concentration plus scavenger knockouts, is right about the difficulty and wrong about its cause and its remedy. The binding constraint is not a threshold but a competing flux: E. coli makes about 14 uM/s of H2O2 of its own, and at a conventional OD600 of 1 the biomarker contributes under one percent of it. Signal-to-background is governed by S0 / (phi x P_endo x T), in which the scavenging rate constant and the enzyme both cancel. The remedy is therefore not to delete katG, katE and ahpCF, which makes matters about thirty times worse, nor to overexpress the oxidase, which is already sufficient at 1 nM. It is to deliver a properly quoted net 6 to 8-fold of cleaned-up sample, to run at OD600 near 0.05 rather than 1, to use non-growing cells, and to read at 30 minutes. Together those recover roughly 500-fold and bring the fold change between healthy and cutoff samples to about 1.20, which a reader with a 5 percent CV can resolve in triplicate. Three things remain unmeasured and any of them can still close the branch: whether DAS enters the cytoplasm at all, how selective the oxidase is against the more abundant urinary polyamines, and whether creatinine can be measured in parallel, without which the two clinical classes overlap before the biology is even reached.", False)])

# ---------------------------------------------------------------------------
for el in list(body):
    if el.tag.split('}')[1] in ('p', 'tbl'):
        body.remove(el)
sectPr = body.find(qn('w:sectPr'))
for el in OUT_EL:
    if sectPr is not None:
        sectPr.addprevious(el)
    else:
        body.append(el)
doc.save(OUT)
print("saved:", OUT)
print("paragraphs:", len(Document(OUT).paragraphs), " tables:", len(Document(OUT).tables))
