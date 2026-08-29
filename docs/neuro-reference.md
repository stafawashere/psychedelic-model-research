# Neuroscience reference, mechanisms, citations, and what each one demands of the engine

Companion to [conclusion.md](conclusion.md). Purpose: stop future sessions from re-deriving the
biology from memory, and record which mechanism each engine choice is standing in for.

**Provenance.** Gathered 2026-08-29 by literature search. Findings are labelled VERIFIED where a
source was located and its claim read, REASONED where the inference to the engine is ours. **Nobody
in this project has read these papers end to end.** Before any claim from here goes into a public
writeup, read the paper.

---

## 1. Receptor anatomy, where the drug enters the hierarchy

**Laminar. VERIFIED.** 5-HT2A is densest on layer 5 pyramidal cells and concentrated on the
**proximal apical dendrite**, giving peak binding in laminae III and V (Jakab and Goldman-Rakic 1998,
PNAS 95:735; Willins et al. 1997). Functional consequence (Aghajanian and Marek 1997, 1999): 5-HT2A
agonism drives a late, **asynchronous** glutamate EPSC increase onto layer 5 apical dendrites. That
is gain on the **late and recurrent** input, not on the feedforward drive.

**Regional, and this corrects a common assumption. VERIFIED.** Luppi et al. 2023 (Brain 147:56) find
5-HT2AR density tracks the unimodal-to-transmodal gradient with the apex highest, but state
explicitly that primary visual cortex is a notable exception and is **also rich in 5-HT2AR**.
Macaque autoradiography (Froudist-Walsh, Palomero-Gallagher et al. 2023) puts 5-HT2A **highest in
V1**. Human PET atlas: Beliveau et al. 2017 (J Neurosci 37:120).

**Two consequences for this engine, both REASONED.**

1. The receptor map is **BIMODAL**, not a shallow-to-deep ramp. Gain enters at both ends of the
   hierarchy and is thinnest in the middle. So `depth` as a monotone `lerp(shallow, deep, D)` was
   never the anatomically right parameterisation, the idx0 choice is **supported** rather than a
   compromise, and E-DEPTH's negative result should be read as refuting the monotone sweep, not the
   deep blocks. A bimodal gain (idx0 and idx8 high, mid low) is expressible today with the existing
   multi-block hook.
2. Because the receptor is on **apical dendrites**, where feedback and long-range lateral input
   terminate, the faithful U-Net analogue of 5-HT2A gain is amplifying the **skip/residual and
   cross-attention streams**. `hooks._make_hook` currently amplifies `output[0]` and passes
   `res_samples` through untouched (`hooks.py:57-62`), which is the anatomically inverted choice.
   This is experiment E-4 in conclusion.md §8.

---

## 2. Come-up

**VERIFIED.** Kometer, Schmidt, Jancke and Vollenweider 2013 (J Neurosci 33:10544) blocked
psilocybin's alpha reduction, N170 attenuation **and visual hallucinations** with ketanserin, making
occipital alpha suppression a causal correlate rather than a bystander. Timmermann et al. 2019 show
DMT fully suppresses alpha and raises Lempel-Ziv signal diversity, with minute-by-minute subjective
intensity tracking delta power and diversity.

**Mechanism.** Layer 5 gain increases the weight of spontaneous and recurrent activity relative to
stimulus-evoked activity while the feedforward stream stays intact. **Detail is preserved. That is
the diagnostic feature.**

**Engine demand. REASONED.** Raise the internal term relative to the encoded-scene term WITHOUT
attenuating the encoded scene. Expressible with `gain` alone. The current configs instead ride `ds`,
which attenuates the evidence, and that is why the rendered come-up defocuses instead of shimmering.

---

## 3. Geometry / Kluver form constants

**VERIFIED.** Ermentrout and Cowan 1979 (Biol Cybern 34:137) derive the form constants from a
**Turing-type instability in a Wilson-Cowan field with Mexican-hat connectivity**: short-range
excitation, longer-range inhibition. Bressloff, Cowan, Golubitsky, Thomas and Wiener 2001 (Phil Trans
R Soc B 356:299) add **anisotropic, orientation-selective long-range horizontal connections** linking
cells of like orientation preference, the shift-twist action of E(2), which is what produces
CONTOURED planforms (lattices, cobwebs, filigrees) as distinct from Ermentrout-Cowan's non-contoured
blobs and rolls. Their own caveat: the results are sensitive to the detailed specification of the
lateral connectivity.

**Four requirements, all spatial:**

| # | requirement | what it does | does a pointwise gain provide it? |
|---|---|---|---|
| 1 | within-layer excitation/inhibition kernel | the pattern-forming substrate | **no** |
| 2 | critical wavelength set by that kernel | selects a BAND, not all frequencies | **no** |
| 3 | complex-log retinocortical map | turns cortical plane waves into spirals/tunnels/rings | **no** (arm B only) |
| 4 | orientation-selective lateral coupling | contoured planforms vs plain blobs | **no** |
| 0 | a control parameter past a bifurcation | triggers the instability | **yes** |

**Engine demand.** See conclusion.md §6 (a)/(b)/(c). The load-bearing point: **a scalar cannot
express a wavelength.** The soft-clip inherits idx0's native ~16 px cell scale (measured 19 px); it
does not select one.

---

## 4. Breakthrough, and the REBUS caveat

**VERIFIED.** REBUS (Carhart-Harris and Friston 2019, Pharmacol Rev 71:316): the **precision
weighting of high-level priors** relaxes via 5-HT2A sensitisation of deep-layer pyramidals, flattening
the free-energy landscape. Measured signature, Timmermann et al. 2023 (PNAS 120:e2218949120): global
hyperconnectivity, network **desegregation**, and **compression of the principal cortical gradient**,
largest where PET-measured 5-HT2A is densest. The hierarchy itself flattens.

**The critique matters for our knob mapping. VERIFIED that it exists.** ALBUS (Safron, Juliani et al.
2025, Neurosci Conscious 2025:niae038) argues REBUS describes only the **high-agonism regime**, and
that lower occupancy can *strengthen* priors (SEBUS). Spotlight commentaries (Noorani and
Alderson-Day 2020) press the same point.

> **Consequence, REASONED, and it contradicts current code.** `knobs.py` maps
> `prior_precision = lerp(base, min, D)`, monotone decreasing. Under ALBUS the honest mapping is
> **non-monotone**: CFG rises through the come-up and collapses only at apex. This also matches the
> repo's own observation that lowering CFG degrades structure and scene-adherence together. Changing
> it is an owner decision (it alters a declared knob mapping), not a silent edit.

**Also relevant. VERIFIED.** The DMTx extended-infusion pilot (Luan, Timmermann et al. 2024, J
Psychopharmacol) found psychological effects **plateaued while plasma DMT kept rising**. Effect is
not a monotone function of concentration, which is an argument against `D(t) -> knobs` being a
straight lerp anywhere.

**What the engine categorically lacks for this phase.** A self-consistent alternative space needs
persistent internal state with its own dynamics. `recurrence` is a scalar blend coefficient over one
previous latent, so it yields drift and never a limit cycle or travelling wave. Bressloff's analysis
yields DRIFTING planforms as well as stationary ones, and drift is where phenomenological autonomy
lives.

---

## 5. Entities

**VERIFIED.** Current leading account, Sandved-Smith, Juliani et al. 2026 (Neurosci Conscious
niaf069, "Computational spirits"): two dimensions, **high epistemic richness / counterfactual depth**
in an intentional model, plus **reduced sensory attenuation** (failed corollary discharge, so
self-generated content is attributed externally). Implicated systems: DMN, TPJ, STS, medial temporal
theory-of-mind circuitry. Entities appear in roughly 45 to 50 percent of DMT reports.

**Why this engine cannot produce them. REASONED, and treat it as closed.** SD1.5 has no
agent-detection subsystem, no self/other attribution, and no generative model of another mind. Its
only path to a figure is the text-conditioning stream, and `_strip_bias` / `BIASED_WORDS` exists to
keep figure vocabulary out of that stream. There is no third route. **The absence of entities is
therefore a determined property of the architecture and carries no evidential weight about DMT.**

---

## 6. Return

**VERIFIED / REASONED.** Two facts. (i) DMT clears fast, minutes, via MAO-A metabolism, so occupancy
falls and gain returns to baseline; return is slower than onset because it is clearance-limited
rather than distribution-limited, and because the hierarchy has to re-converge. (ii) **The retina
never stopped transducing the room.** Precision weighting collapsed; the signal did not.

**Engine demand.** An input stream that is never degraded. `run.py` satisfies this: `scene` is loaded
once and re-encoded fresh every frame, only `prev` mutates. That is the correct analogue and not
cheating, because the anchor is the INPUT and not a stored memory of the output.

**The caveat worth publishing rather than defending.** The photo is bit-identical every frame: zero
sensor noise, zero eye movement, zero viewpoint change. Real return is re-convergence onto a noisy,
ever-changing stream. Adding fixed-seed per-frame jitter would turn a construction guarantee into a
demonstrated dynamical property. Experiment E-2.

---

## 7. Reachability summary

| Phase | Reachable with the 5 scalar knobs? | Categorically missing | Minimal honest addition | Arm |
|---|---|---|---|---|
| Come-up | **yes** | none | hold `ds` flat; scale skips not forward path | A |
| Geometry | **no** | lateral kernel, wavelength selection, retinocortical map, orientation coupling | DoG kernel with derived sigmas, then log-polar | A for the kernel, B for the map |
| Breakthrough | **partly** | persistent field state with own dynamics | Wilson-Cowan step between frames | A |
| Entities | **no, by architecture** | agent model, self/other attribution | none admissible | n/a |
| Return | **yes** | none | jitter `x_scene` so the return is non-trivial | A |

---

## Sources

- Jakab and Goldman-Rakic 1998, PNAS 95:735, https://www.pnas.org/doi/10.1073/pnas.95.2.735
- Willins et al. 1997, https://pubmed.ncbi.nlm.nih.gov/9268067/
- Aghajanian and Marek, 5-HT2A EPSCs in layer V, https://www.sciencedirect.com/science/article/pii/S000689939901224X
- Luppi et al. 2023, Brain 147:56, https://academic.oup.com/brain/article/147/1/56/7273051
- Froudist-Walsh, Palomero-Gallagher et al. 2023, https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10322721/
- Beliveau et al. 2017, J Neurosci 37:120, https://pubmed.ncbi.nlm.nih.gov/28053035/
- Ermentrout and Cowan 1979, Biol Cybern 34:137, https://link.springer.com/article/10.1007/BF00336965
- Bressloff et al. 2001, Phil Trans R Soc B 356:299, https://royalsocietypublishing.org/doi/10.1098/rstb.2000.0769
- Bressloff and Cowan 2002, Neural Computation, https://dl.acm.org/doi/10.1162/089976602317250861
- Kometer et al. 2013, J Neurosci 33:10544, https://www.jneurosci.org/content/33/25/10544.short
- Timmermann et al. 2019, DMT EEG, https://www.biorxiv.org/content/10.1101/706283v1.full.pdf
- Timmermann et al. 2023, PNAS 120:e2218949120, https://www.pnas.org/doi/10.1073/pnas.2218949120
- Carhart-Harris et al. 2016, PNAS, LSD, https://www.pnas.org/doi/10.1073/pnas.1518377113
- Carhart-Harris and Friston 2019, REBUS, https://pubmed.ncbi.nlm.nih.gov/31221820/
- Safron, Juliani et al. 2025, ALBUS, https://pmc.ncbi.nlm.nih.gov/articles/PMC11823823/
- Noorani and Alderson-Day 2020, REBUS spotlight, https://academic.oup.com/nc/article/2020/1/niaa007/5856367
- Sandved-Smith, Juliani et al. 2026, Computational spirits, https://pmc.ncbi.nlm.nih.gov/articles/PMC13240852/
- Luan, Timmermann et al. 2024, extended DMT, https://journals.sagepub.com/doi/10.1177/02698811231196877
