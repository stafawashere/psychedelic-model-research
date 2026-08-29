# Conclusion, what the experiment established

**Subject run:** `output/past/2026-08-29_05-31-15` (40 frames, arm A, `resources/scene.jpg` forest
road, seed 0). Config snapshot lives in that directory. This document treats that run as the
result and states what it does and does not establish.

**Written 2026-08-29.** Evidence labels: VERIFIED (measured or read off source this session),
REASONED (inference from verified facts), ASSUMED (neither). Neuroscience citations are collected
in [neuro-reference.md](neuro-reference.md) and were gathered by literature search, not re-read
paper by paper, so they carry that document's own labels.

---

## 0. The headline

**The run reproduced the DYNAMICS of the canonical DMT arc and did not reproduce the CONTENT of any
of its phases. The boundary between the two is dimensional, not empirical.**

Every knob in this engine is a scalar. Every phase the run produced is one whose brain mechanism is
also essentially scalar: a global change in gain, a reweighting of precision, a fall in receptor
occupancy over time. Every phase it failed is one whose brain mechanism is spatial (an interaction
kernel with a length constant, a retinocortical coordinate map) or architectural (a generative model
of another agent).

A scalar can push a system across a bifurcation. It cannot specify which pattern lies on the other
side, because the pattern is set by a kernel wavelength and a coordinate map, and a scalar has
neither. That is the finding, and it is sharper than either "geometry emerged" or "the experiment
failed".

---

## 1. Scoreboard

| Phase | Produced | What was produced | What was missing |
|---|---|---|---|
| Come-up | **partial** | monotone graded onset | detail-preserving shimmer; got defocus instead |
| Geometry | **no** | elevated periodicity only | wavelength selection, symmetry, radial organisation |
| Breakthrough | **partial** | total loss of the veridical scene | a self-consistent space with autonomous motion |
| Entities | **no** | nothing | closed by architecture, not by evidence (§6) |
| Return | **yes** | exact return to the source scene | nothing, but see the construction caveat (§5) |

---

## 2. The measured arc (VERIFIED)

RMSE of each frame against frame 00, RGB, [0,1]:

```
f00 0.000   f04 0.043   f07 0.079   f11 0.189   f13 0.274 (peak)
f16 0.220   f20 0.126   f24 0.076   f30 0.028   f39 0.025
```

Clean asymmetric pulse: fast rise over 13 frames, slower tail over 26. Frame 13 sits at t = 4.000
min exactly, where `D = dmax = 1.0`, which `run.py`'s apex assertion requires.

Consecutive-frame RMSE, i.e. how fast the image is changing:

```
rest       f30->f39   0.003 - 0.012
come-up    f09->f11   0.102 - 0.122
apex       f13->f16   0.036 - 0.066
transitions f11->f12, f19->f20   0.116
```

The apex is a local MINIMUM of change rate between the two fastest transitions in the run, but it is
still moving about ten times faster than rest. An earlier claim in session that the apex frames were
"near-interchangeable" was wrong and is corrected here.

Apex texture structure, whitened against the natural 1/f spectrum, with synthetic positive controls
(`tests/probe_apex_structure.py`):

| | dominant wavelength | periodic bump over 1/f | orientation anisotropy | mirror LR | rot 60 | rot 90 |
|---|---|---|---|---|---|---|
| CONTROL hex lattice 24px | 24.4 px | 14.5 | very high | - | - | - |
| CONTROL concentric rings | 23.3 px | 10.9 | 2.08 | 0.983 | 0.991 | 0.983 |
| CONTROL 6-arm log spiral | 15.5 px | 0.40 | 1.84 | -0.033 | 0.992 | -0.983 |
| scene f00 | - | 0.44 (1.6x) | 13.53 | 0.082 | 0.118 | 0.007 |
| **apex f13** | **19.0 px** | **1.10 (3.0x)** | **9.27** | **0.049** | **-0.015** | **0.036** |
| apex f15 | 19.0 px | 1.17 (3.1x) | 10.35 | 0.064 | 0.004 | 0.014 |

Read: periodicity genuinely rose (3.0x excess power at 19 px against the source photo's 1.6x), the
field became MORE isotropic than the forest (9.27 vs 13.53), and rotational and mirror symmetry sit
at the floor while the controls score 0.98 to 0.99 on the same tests. **Periodicity without
symmetry, measured, with a positive control.**

---

## 3. Come-up, partial, and the failure is diagnostic

**Brain.** Occipital alpha suppression, shown causal by ketanserin blockade of both the alpha
reduction and the hallucinations together. Underneath it, 5-HT2A on proximal apical dendrites of
layer 5 pyramidals drives a late asynchronous glutamate EPSC increase, i.e. gain on the LATE and
RECURRENT input. The feedforward stream is untouched, which is why detail survives while surfaces
start to shimmer and breathe.

**Engine equivalent.** Raise the internal, prior-driven contribution relative to the encoded scene
without destroying the encoded scene.

**What the engine did.** `gain` rises correctly, 1.195 at rest to 2.800 at apex, and the hook fires
every frame. But the visible character of the come-up is set by `ds`, which rises 0.490 to 0.713
over frames 00 to 11.

> **MECHANISM (VERIFIED arithmetic, REASONED spectral step).** Rising `ds` causes progressive
> defocus because `add_noise` scales the blended latent by sqrt(alpha_bar) (0.57 down to 0.33 over
> the come-up) against unit-variance WHITE noise, while the VAE latent spectrum is RED. Per-frequency
> SNR therefore collapses fastest at high spatial frequencies, and DDIM must resynthesise fine detail
> generically rather than recover it.

**Why it produced a come-up at all:** the envelope mechanism, a monotone rise in internal influence,
is scalar and the engine has it.

**Why it produced the WRONG come-up:** the engine implements "raise the prior" by DESTROYING THE
EVIDENCE. The brain raises the prior while leaving the evidence intact. Those are different
operations and this engine conflates them.

**Full implementation.** Get the internal-influence rise from `gain` alone, holding `ds` low and
roughly flat, so the encoded scene survives at high frequency and the amplified block shows up as
structured modulation of preserved detail. Config change only, no new machinery. See §7 E-1.

---

## 4. Breakthrough, the negative half only

**Brain.** REBUS: the precision weighting of high-level priors relaxes via 5-HT2A sensitisation of
deep-layer pyramidals. Measured signature is global hyperconnectivity, network desegregation and
compression of the principal cortical gradient, i.e. the hierarchy itself flattens.

**Why `scene_min = 0.4` was enough to break through (VERIFIED arithmetic).** At frame 13:

```
scene_precision 0.400   recurrence 0.120   prior_precision 6.0   gain 2.800   depth 0   ds 0.820

blend share of enc(scene)          = 0.400 / 0.520          = 0.769
amplitude after add_noise at t~793 = 0.769 x ~0.20          ~ 0.15
power share of the veridical scene                          ~ 0.02
```

> **MECHANISM.** `scene_min = 0.4` holds the BLEND, not the IMAGE, because `ds = 0.82` then
> attenuates the whole blended latent to roughly 20 percent amplitude under full-power noise. The
> denoiser has to reinvent about 98 percent of the signal, which is why a 0.4 floor on
> `scene_precision` still permits total scene loss.

**Why the result is a texture and not a new coherent scene.** All 25 active denoising steps run
with the idx0 hook multiplying the highest-resolution down-block output by 2.8 and soft-clipping.
CFG at 6 on a neutral caption is too weak a semantic pull to organise a scene against a per-step
perturbation of the low-level feature path, so the trajectory converges to the amplified filters'
fixed-point texture. The source palette survives because the residual ~15 percent scene amplitude
sits in the low frequencies where SNR is best, and `_match_contrast` re-imposes the scene's
per-channel mean and std on the fed-back frame each iteration.

**Why the apex has motion but not dynamics (VERIFIED).** `cfg.seed` is passed unchanged every frame
(`run.py:98`) and the generator is reseeded per frame (`engine.py:162`), so `initial_noise` is
**byte-identical across the entire run**. The apex is ONE FROZEN NOISE REALISATION rendered under
slowly drifting `gain` (2.80 to 2.32) and `ds` (0.820 to 0.722). Nothing in the system holds state of
its own. `recurrence` is a scalar blend coefficient, not a dynamical system: it can produce drift,
never a limit cycle or a travelling wave.

**Full implementation.** Give the hooked activation field state that persists across frames and
evolve it under a two-population Wilson-Cowan step. That is substrate rather than content, it rides
`D(t)` like everything else, and it stays arm A. It depends on the lateral kernel in §5.

---

## 5. Return, produced, with a construction caveat

**Brain.** Two facts, and the second carries it. DMT clears in minutes via MAO-A, so occupancy falls
and gain returns to baseline, more slowly than onset because clearance is slower than distribution.
And **the retina never stopped transducing the room.** Precision weighting collapsed; the signal did
not.

**Engine (VERIFIED).** `scene` is loaded once (`run.py:75`) and passed by name every iteration
(`run.py:94`). The only variable that mutates is `prev` (`run.py:106`). Inside `render_frame`,
`x_scene` is read-only and re-encoded fresh from the pristine image each frame
(`engine.py:165-167`); there is no assignment to it anywhere. Frame 39 therefore renders from an
identical pristine latent, under identical noise, with knobs near frame 00's (D 0.070 vs 0.108,
`scene_precision` 0.819 vs 0.801, `ds` 0.476 vs 0.490). RMSE 0.025.

**Is the pristine copy cheating? No, with one caveat that belongs in the writeup.** Re-encoding the
source every frame is the correct analogue of an undegraded sensory stream: the anchor is the INPUT,
not a stored memory of the output. The honest objection is narrower. The photo is bit-identical every
frame, so the engine's sensory stream has zero noise, zero eye movement and zero viewpoint change.
Real return is re-convergence onto a noisy, ever-changing stream. **This return is guaranteed by
construction rather than demonstrated as a dynamical property.** See §7 E-2, which would settle it
and strengthen the result if it passes.

---

## 6. Geometry, not reachable by these knobs

**Brain.** Ermentrout and Cowan derive the form constants from a Turing-type instability in a
Wilson-Cowan field with Mexican-hat connectivity. Four requirements, all spatial:

1. a within-layer interaction kernel (short-range excitation, longer-range inhibition);
2. a **critical wavelength set by that kernel**, which is what makes the bifurcation select a BAND of
   spatial frequencies rather than amplifying everything;
3. the approximately complex-logarithmic retinocortical map, which turns cortical plane waves into
   spirals, tunnels and rings;
4. orientation-selective long-range horizontal connections (Bressloff's shift-twist symmetry), which
   is what yields CONTOURED planforms such as lattices and cobwebs rather than plain blobs.

**What a pointwise gain provides:** the control parameter that pushes past a bifurcation. **None of
1 to 4.**

> **MECHANISM (VERIFIED).** A uniform multiply is annihilated by the GroupNorm at the head of every
> ResNet, so the only surviving operator is the tanh soft-clip (`hooks.py:44-48`), which is a smooth
> AMPLITUDE SATURATION. Saturation makes blobs at whatever scale the block already prefers. Block
> idx0 runs 320 channels at 32x32, one cell per 16 image px; the measured apex wavelength is 19 px.
> **The wavelength was INHERITED from the architecture, not SELECTED by a kernel.**

> **MECHANISM (REASONED).** Convolutions and GroupNorm are translation-equivariant, not
> rotation-equivariant, and define no origin. The attractor of an amplified feedforward denoiser is
> therefore a statistically stationary texture: periodicity with random phase, no centre, no mirror
> or rotational order. Measurement agrees at the floor (§2) while controls score 0.98 to 0.99.
> **Arm A cannot produce radial form constants for structural reasons, not for want of tuning.**

**E-DEPTH needs rereading.** The receptor anatomy is **bimodal, not a shallow-to-deep ramp**: 5-HT2A
is dense in high-level association cortex AND rich in V1, with the trough in unimodal non-primary
cortex. E-DEPTH tested a MONOTONE sweep and found nothing beyond idx0. The correct conclusion is that
the monotone parameterisation was never anatomically right, not that deep blocks are inert. This
supports rather than undermines the idx0 choice, and it agrees with
[geometry-gap-analysis.md](geometry-gap-analysis.md)'s existing argument that multi-block gain is the
more faithful model and single-block is the simplification requiring justification. This run used
single-block idx0.

**Full implementation, in dependency order.**

- **(a) Difference-of-Gaussians lateral kernel** applied to the hooked activation, both sigmas
  DERIVED from the block's native resolution and fixed before any render. The only route to a
  band-selected wavelength. Substrate, not content: cortical lateral connectivity exists sober. Rides
  `D(t)` as gain does. Stays **arm A** provided the sigmas are derived rather than tuned and the full
  sweep is reported.
- **(b) Log-polar readout.** Already built (`hooks._logpolar_warp`), already labelled **arm B**.
  Note the ordering: without (a) there is no banded field for the map to act on, which is a plausible
  reason arm B produced speckle.
- **(c) Orientation-selective coupling** for spirals and lattices specifically. Needs an orientation
  dimension SD1.5 activations do not have. **Declared modeling assumption.**

---

## 7. Entities, closed by architecture, not by evidence

**Brain.** The leading account is two-dimensional: high epistemic richness and counterfactual depth
in an intentional model, plus reduced sensory attenuation, so self-generated content fails its
corollary-discharge tag and is attributed externally. Implicated systems are DMN, TPJ, STS and medial
temporal theory-of-mind circuitry, i.e. agent-detection machinery running with priors dominant and
the self-generation flag missing.

**Engine.** SD1.5 has no agent-detection subsystem, no self/other attribution, and no generative
model of another mind. Its only path to a figure is the text-conditioning stream, and `_strip_bias`
with `BIASED_WORDS` exists precisely to keep figure vocabulary out of that stream. There is no third
route: the U-Net's figure prior is reachable only through cross-attention, and cross-attention is
driven only by the caption.

> **This is a stronger statement than E-DEPTH's and should replace it in any writeup. E-DEPTH closed
> a ROUTE; this closes the CATEGORY.** The consequence is that **the absence of entities is not
> evidence about DMT at all.** It is a determined property of the architecture, and the experiment
> has no power over that question. There is no admissible addition, because anything that would
> produce figures would be prompting for them.

This is consistent with, and the mechanistic explanation for, the owner stance in CLAUDE.md §0.

---

## 8. Next experiments, ranked

| id | experiment | cost | needs approval | what it decides |
|---|---|---|---|---|
| **E-1** | come-up with `ds` held low and flat, `gain` doing all the work | one render | no | whether detail-preserving shimmer is reachable with today's engine |
| **E-2** | fixed-seed per-frame jitter (small translation + noise) on `x_scene` | one render | no | whether the return is a dynamical property or a construction artifact |
| **E-3** | derived-sigma DoG lateral kernel inside `_amplify` | new code + sweep | **yes** | whether a selected wavelength (and therefore any form constant) is reachable at all |
| **E-4** | scale `res_samples` / cross-attention instead of `output[0]` in `_make_hook` | one-line + render | **yes** | tests a specific anatomical claim (see below) |

**E-4's claim.** 5-HT2A sits on APICAL DENDRITES, which is where feedback and long-range lateral
input terminate. The faithful U-Net analogue of 5-HT2A gain is therefore amplifying the
**skip/residual and cross-attention streams**, not the forward-path hidden state. `_make_hook`
currently amplifies `output[0]` and passes `res_samples` through untouched (`hooks.py:57-62`). That
choice is deliberate per CLAUDE.md §8 (one clean forward-path intervention) but it is anatomically
INVERTED. REASONED, cheap to test, and it changes what the `gain` knob means, hence owner approval.

**CORRECTION, added after this section was first written.** E-3 as stated above is a re-proposal of
**D-4**, a band-selective DoG gain inside `_amplify` that was owner-approved on 2026-08-28,
implemented, swept over sigma {0.6, 1.0, 1.5, 2.5}, and refuted: wavelength stayed 24.4 px at every
sigma but the last, and the frames looked like a sharpened photograph
([autonomous-log.md](autonomous-log.md) lines 322-346). Re-opening it requires new evidence, and
there is some: D-4's own note records the DoG band carrying only 2 to 8 percent of activation power,
so the additive term was a small perturbation on an activation that still carried its inherited
scale. **D-4's failure is attributable to amplitude, not to the kernel being unable to select.**
Std-normalising the DoG before mixing, plus a predicted-versus-measured wavelength regression that
D-4 never had, is a materially different experiment. See
[development-plan.md](development-plan.md) §0 and §5 for the full design and the approval argument.
Do not run E-3 without that argument on the record.

E-3 is the highest-value change in the project. Everything in §6 and the second half of §4 depends
on it.

---

## 9. What may and may not be claimed

**May be claimed.**

- Monotone motion of neurally-grounded scalar parameters over a dose curve produces a reversible
  transition between veridical rendering and a non-veridical, spatially periodic, scene-independent
  regime, with exact return to the source scene. VERIFIED, 0.025 vs 0.274 RMSE.
- Periodicity at the apex rose measurably above the source photo's natural spectrum (3.0x vs 1.6x
  excess at 19 px) while rotational and mirror symmetry stayed at the floor. VERIFIED with positive
  controls.
- The failure to produce form constants has a structural explanation (saturation inherits a scale
  and cannot select one; convolutions define no origin), not a tuning explanation. REASONED from
  VERIFIED mechanics.
- The absence of entities is a property of the architecture and carries no evidential weight about
  DMT. REASONED, and airtight given `_strip_bias`.

**May NOT be claimed.**

- That SD1.5 produced Kluver form constants. It produced periodicity without symmetry.
- That five neurally-mapped knobs produced this. `depth_shallow = depth_deep = 0` in this config, so
  **four** knobs moved and `depth` was frozen. The freeze is justified by E-DEPTH but must be stated.
- That the apex frames evolve. They are one fixed noise tensor under drifting parameters.
- That the return demonstrates dynamical re-convergence. It is currently guaranteed by construction.
- Anything about qualia. This is a computational signature.
