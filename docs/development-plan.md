# Development plan, from arc dynamics to arc content

Companion to [conclusion.md](conclusion.md), which is the brief this plan answers, and to
[neuro-reference.md](neuro-reference.md), which supplies the biology each step stands in for.

**Design only. Nothing here has been implemented.** The session that produced this plan had no
shell, so `scripts/verify.sh` was not run and no test output is quoted. Every "verify" line below is
an instruction to a future builder, not a result. The MPS timing figures in E-3 are the exception:
those were measured on this box by the coordinating session and are labelled VERIFIED.

---

## 0. State of play, and the one correction that reshapes the brief

**VERIFIED (`docs/autonomous-log.md` lines 314-367, 549-577).** Two of the mechanisms this plan is
asked to design were already built once, swept, and then removed:

- **D-4, band-selective DoG gain inside `_amplify`** (`_gaussian_blur` / `_band_select`, composition
  `activation + (gain-1)*DoG(activation)`). Owner-approved 2026-08-28, implemented, swept over sigma
  {0.6, 1.0, 1.5, 2.5}, **negative**: measured wavelength stayed 24.4 px at every sigma except 23.3
  at 2.5, band_sharp collapsed 2052 to 426, and the frames looked like a sharpened photograph.
  Removed in the 2026-08-28 revert.
- **D-5, slerp noise drift across the plateau** (`_slerp` / `_drifting_noise`, `noise_anchors`).
  Owner-approved, implemented, **positive**: plateau frame-to-frame change 29.80 sustained versus
  22.30 decaying, consecutive frames correlated 0.95 while anchors were orthogonal at 0.009. Also
  removed in the revert.

`conclusion.md` §8 proposes E-3 without referencing D-4. **E-3 as written is a re-proposal of a
refuted direction**, and CLAUDE.md requires new evidence before that is legitimate. There is new
evidence, and it is specific:

> **MECHANISM (REASONED, from the D-4 sweep table plus the coordinator's timing measurement).** D-4
> failed to move the wavelength because the DoG output is roughly 5x smaller in std than its input
> (VERIFIED on this box at sigma 1.0/2.0), and D-4's own note records the DoG band carrying only 2 to
> 8 percent of activation power. The additive term was therefore a small perturbation on an
> unfiltered activation that still carried its architecture-inherited 24 px scale, so the composite
> retained the inherited scale. **The failure is attributable to amplitude, not to the kernel being
> unable to select.** A composition in which the DoG term is std-normalised before mixing makes the
> banded term carry the majority of the variance at apex gain, which is a materially different
> experiment.

That distinction is what E-3 below is built on, and it is why E-3 must ship with a
**predicted-versus-measured wavelength regression**, which D-4 never had. D-4 varied sigma and
reported the measured wavelength; it never stated what wavelength each sigma pair *should* produce.
Without that, a flat 24.4 px column is uninterpretable: it is equally consistent with "the kernel
does not select" and with "the swept sigmas all predict about 24 px anyway".

**D-5 is not refuted and should be reinstated**, not redesigned. It is the answer to the fixed-seed
question in §7.

---

## 1. Phase structure and gates

| Phase | Contents | Gate to proceed |
|---|---|---|
| **P0 Measurement** | M-1 to M-4 | All four metrics pass their positive **and** negative controls, on synthetics, with the control rows printed. No render experiment starts before this. |
| **P1 Free experiments** | E-1, E-2 | Both reported as run, whatever the result. No approvals consumed. |
| **P2 Anatomy of gain** | E-4, E-5, E-6 | At least one changes a P0 metric beyond its control-established noise floor, or all three are logged negative and P3 proceeds on idx0 alone. |
| **P3 The kernel** | E-3 | **Hard gate.** Predicted-vs-measured wavelength slope above 0.5 with the full declared sweep reported. Below that, P4 and P5 are cancelled and the project's conclusion stands as written. |
| **P4 Dynamics** | E-7, E-8 | M-3 separates field-on from field-off at the same knob values, and the arc still closes on M-4. |
| **P5 Coordinate map** | E-9 arm B | Only after P3 passes. |

The P3 gate is the programme's pivot. Everything in `conclusion.md` §6 and the second half of §4 is
downstream of it.

---

## 2. Phase 0, measurement, built before anything it judges

The engine currently scores two things (`tests/geometry_score.py` gated clarity,
`src/measure/metrics.py` `clarity_ungated` and `scene_fidelity`) and both are known-blind on most of
what this plan targets. `scene_fidelity` is blind on texture (granite 0.473 versus hedge 0.453).
`tests/probe_apex_structure.py` is a one-off script, not an importable metric.

Rule for all of P0: **new metrics go in `src/measure/metrics.py` as importable functions.
`tests/geometry_score.py` is not touched**, so every historical run stays comparable. Gates are added,
never relaxed.

### M-1, form-constant score
**Goal.** One function that answers "is this a Kluver planform" rather than "is this periodic".

**Files.** New `form_constant_score(img)` in `src/measure/metrics.py`, generalising
`tests/probe_apex_structure.py:50-98` (`whitened_peak`, `angular_anisotropy`,
`rotational_symmetry`, `_correlate`). `probe_apex_structure.py` becomes a thin caller so its
published numbers stay reproducible.

**Adds beyond the probe:** (a) a **radial versus angular power split**, computed by resampling onto a
log-polar grid *for measurement only* and taking the fraction of whitened band power in pure-radial
versus pure-angular modes, so rings score radial, spirals score mixed, and a stationary texture
scores neither; (b) a **predicted-wavelength field** so E-3 can regress against it; (c) the existing
mirror-LR, rot60 and rot90 correlations unchanged.

**Controls.** The three synthetics already in `_controls()`, plus flat gray, plus the source photo.
Reported every time in the same table. **A run of the metric with no control rows is not evidence.**

**Falsification of the metric itself.** If the hex-lattice control does not score bump above 10, or
the log-spiral control does not score radial/angular mixed above the forest photo, the metric is
wrong and must be fixed before use.

**Cost.** No renders. About an hour of work. **Admissibility.** ADMISSIBLE-ARM-A.

### M-2, detail preservation (come-up diagnostic)
**Goal.** Distinguish "internal structure added on top of preserved detail" from "detail destroyed
and resynthesised".

**Hypothesis it serves.** Rising `ds` causes high-frequency detail loss because `add_noise` scales
the latent by sqrt(alpha_bar) against white noise while the latent spectrum is red (`conclusion.md`
§3). A metric sensitive to that must live **above** the 1/8-Nyquist band, which is exactly where
`scene_fidelity`'s 4x box-downsample throws information away.

**Definition.** Band-pass both frame and source above 1/8 Nyquist, then correlate gradient
*orientation*, not intensity, so a contrast or colour shift does not register as detail loss.

**Controls, all required in the output.** `M2(scene, scene) = 1`. `M2(blur(scene, sigma=2), scene)`
near zero. `M2(contrast_shifted(scene), scene)` near 1. `M2(other_photo, scene)` near zero. If the
blur control does not separate from the contrast control, the metric is measuring luminance and is
unusable.

**Cost.** No renders. **Admissibility.** ADMISSIBLE-ARM-A.

### M-3, autonomy versus parameter drift
**Goal.** Answer the question `conclusion.md` §4 says the engine cannot currently answer: does the
apex move because the system has dynamics, or because the knobs drift under a frozen noise tensor.

**Design.** Score a **hold segment** (`hold_min > 0`, so D is pinned at dmax and every knob is
constant). Three numbers per segment: (1) mean consecutive-frame RMSE; (2) the **sign of its slope**
across the segment, where decaying means converging to a fixed point and flat or rising means
sustained; (3) the **cross-correlation peak offset** between consecutive frames, reusing the offset
machinery in `tests/probe_seed_positions.py`. A consistently signed non-zero offset with high peak
correlation is a travelling wave; zero offset with high correlation is a standing pattern; low peak
correlation is churn, not dynamics.

**Calibration already in hand (VERIFIED).** Frozen noise plus constant knobs gives 22.30 decaying
monotonically from 28.10 to 21.46. Independent per-frame seed gives 56.20 with the geometry
destroyed. Those are the two poles the metric must place any new result between.

**Cost.** Metric free; needs a 12-frame hold segment, about 6 minutes.
**Admissibility.** ADMISSIBLE-ARM-A.

### M-4, arc closure, not `scene_fidelity`
**Goal.** A closure measure that works on texture scenes.

**Definition.** Two numbers against frame 00: RGB RMSE (the measure `conclusion.md` §2 already used,
0.025 at f39 versus 0.274 at peak) and M-2 high-frequency agreement. Closure is claimed only when
both pass.

**Negative control, mandatory.** The same pair computed between frame 00 and a *different* source
photo, printed in the same table. This is the control `scene_fidelity` never had, and its absence is
why the granite-versus-hedge blindness went uncaught.

**Threshold, pre-registered now, before any new run.** Closure means RMSE(f_last, f00) below 0.05 and
M-2 above 0.8, with the different-photo control below 0.3 on M-2. Set from the existing 0.025
measurement plus margin.

**Cost.** No renders. **Admissibility.** ADMISSIBLE-ARM-A. Strengthens the closure claim; weakens no
gate.

**Gate G0.** All four metrics print their controls and the controls separate. Then, and only then,
P1 starts.

---

## 3. Phase 1, the two experiments that need no approval

### E-1, come-up carried by `gain`, with `ds` held flat
**Goal.** Test whether detail-preserving shimmer is reachable with today's engine.

**HYPOTHESIS.** Holding `ds` low and flat while `gain` rises causes the come-up to preserve
high-frequency scene detail while gaining internal structured modulation, because the come-up's
detail loss is produced by `add_noise` attenuating the blended latent against white noise (a `ds`
effect) and not by the gain hook, which is a per-step perturbation inside a denoise trajectory that
still starts near the scene.

**Files.** New `configs/comeup_flat_ds.yaml` only. Copy `configs/crisp_trip.yaml`, set
`ds_min: 0.45` and `ds_max: 0.45`. Nothing else changes. `crisp_trip.yaml` is untouched. No code
edits.

**Mechanics being used.** `run.py:84` already computes `ds = lerp(ds_min, ds_max, d)`; equal
endpoints make it constant. `decouple_ds` at `run.py:79` stays true because `ds_max > 0`.

**Verification.** M-2 over come-up frames 00 to 13 for both the new run and the archived
`output/past/2026-08-29_05-31-15`. Controls: scene against itself, and blurred scene, printed
alongside. Then M-1 at f13 for both, to see what was traded away. Then **look at the frames**.

**Falsification.** If M-2 across frames 00 to 11 does not rise materially above the archived run's,
the come-up defocus is not `ds`-driven and `conclusion.md` §3's mechanism sentence is wrong. If M-2
rises but M-1's periodicity excess at f13 falls to the source photo's 1.6x, then `ds` was carrying
the geometry too, and the two goals are in direct conflict. That is itself a reportable result.

**Cost.** 40 frames, about 20 minutes, backgrounded.
**Admissibility.** ADMISSIBLE-ARM-A, config only. **Depends on.** M-1, M-2.

### E-2, jittered `x_scene`, so the return is demonstrated
**Goal.** Convert the return from a construction guarantee into a measured dynamical property.

**HYPOTHESIS.** Per-frame sub-pixel translation plus low-amplitude additive noise on the source image
causes the return to remain exact because the return is driven by the undegraded *statistics* of the
input stream rather than by bit-identity, and DDIM re-convergence is stable to input perturbations
far larger than the jitter.

**Files.** `run.py` only, where the scene is passed into the loop (`run.py:92-94`). The pristine
`scene` object stays the reference for `_match_contrast` (`run.py:106`) and for the saved
`scene.png`; a jittered *copy* goes into `render_frame`. Do not touch `engine.py`: the
"re-encode a pristine input each frame" property at `engine.py:165-167` is what makes the analogue
correct, and jitter belongs to the sensor, not the encoder.

**Determinism.** Offsets and noise come from a generator seeded with `cfg.seed` and advanced by frame
index, so the run stays exactly reproducible from the config. Amplitude declared before running:
translation uniform in +/- 1.0 px with bilinear resampling, additive Gaussian sigma 2/255.

**Verification.** M-4 on the jittered run. **Positive control, required:** three frames at rest knobs
with jitter on and `gain_slope: 0.0`, establishing the RMSE floor that jitter alone contributes. The
closure number is only interpretable against that floor.

**Falsification.** If RMSE(f_last, f00) exceeds 0.05 while the jitter-only floor is below 0.03, the
return depended on bit-identical input and `conclusion.md` §5's caveat becomes a finding rather than
a caveat. Report either way.

**Cost.** 40 frames plus 3 control frames, about 22 minutes.

**Admissibility.** ADMISSIBLE-ARM-A, with a flag: this **degrades the input**, so it makes the test
strictly harder, which the gate rules permit unilaterally. It must run as a separate config and must
not replace the deliverable run, because every RMSE in `conclusion.md` §2 is defined against the
un-jittered stream. **Depends on.** M-4.

**Gate G1.** E-1 and E-2 both reported as run, results whatever they are, before any approval is
spent.

---

## 4. Phase 2, what the gain knob is attached to

### E-4, amplify the residual and cross-attention streams, not `output[0]`
**Goal.** Test the apical-dendrite claim.

**HYPOTHESIS.** Amplifying the skip/residual stream instead of the forward-path hidden state causes a
larger and qualitatively different effect at the same nominal gain, because 5-HT2A sits on proximal
apical dendrites where feedback and long-range lateral input terminate (VERIFIED, Jakab and
Goldman-Rakic 1998 via `neuro-reference.md` §1), and the U-Net's analogue of that termination zone is
the skip tensors and the cross-attention path, not the feedforward hidden state.

**Files.** `hooks.py:53-63` `_make_hook`, plus a new selector threaded through `hooks.attach`
(`hooks.py:66-79`), `engine.render_frame` (`engine.py:216-218`), and `RunConfig` / `KnobShaping`
(`config.py:27-41`). Three modes, one config string: `forward` (today's behaviour, the default, so
archived results are unaffected), `residual` (amplify `output[1:]`, leave `output[0]` alone), `both`.

**Known hazard, stated in advance (CLAUDE.md §8, VERIFIED).** A down block's `output[0]` is *also*
stored as the last residual. In `residual` mode the perturbation reaches the up path only; in `both`
mode it hits twice and is NaN-riskier. `both` runs last and only if `residual` is stable.

**Cross-attention is deliberately NOT bundled here.** The only content reachable through
cross-attention is the caption, so amplifying it amplifies caption influence. That is CFG by another
name and it competes with `prior_precision` for the same interpretation. Design it as E-4b only if
E-4 passes, labelled NEEDS-OWNER-APPROVAL on the additional ground that it duplicates a declared
knob.

**Verification.** Flat-field single-frame probe first, in the pattern of `tests/sweep_*.py`, at apex
gain, all three modes, checking NaN and clip fraction. Then one 40-frame run in the winning mode.
M-1 at apex, M-4 at the end.

**Falsification.** If the residual mode's flat-field frame is indistinguishable from the forward
mode's at the same gain (M-1 within control noise), the anatomical distinction has no computational
expression here and the claim is closed as untestable in this architecture.

**Cost.** 3 probe frames plus 40 render frames, about 22 minutes.
**Admissibility.** **NEEDS-OWNER-APPROVAL.** It changes what the `gain` knob means, which is a
declared knob mapping. **Depends on.** M-1, G1.

### E-5, bimodal multi-block gain, idx0 and idx8 high, mid low
**Goal.** Replace the refuted monotone depth sweep with the anatomically correct parameterisation.

**HYPOTHESIS.** Gain applied at idx0 and idx8 together causes a stronger effect than idx0 alone
because 5-HT2A density is bimodal across the hierarchy, dense in transmodal cortex and also rich in
V1 with the trough in unimodal non-primary cortex (VERIFIED, Luppi et al. 2023 and Froudist-Walsh et
al. 2023 via `neuro-reference.md` §1), and because the surviving effect of a flat gain is itself
U-shaped over depth, strongest at high-resolution shallow-down and late-up blocks (VERIFIED,
CLAUDE.md §8).

**Refuted-direction flag.** Multi-block gain is on the playbook's refuted list and the E-DEPTH
monotone sweep is closed. This is admissible to re-propose only on the specific new evidence in
`neuro-reference.md` §1: the receptor map is bimodal, and the previous multi-block attempt paired
idx0 with idx7 or idx8 **at equal gain**, whereas the anatomy specifies a *profile*, high at both ends
and low in the middle. Any builder must state that difference in the run log. If the sweep reproduces
the earlier degradation, it is closed for good.

**Files.** No code change needed for the first pass. `hooks.attach` (`hooks.py:66-79`) already accepts
matching lists of depths and gains; only a config path is missing. **Prefer a probe script**, so no
production surface changes before the mechanism earns it. Promotion would mean `depth_profile` and
`gain_weights` in `KnobShaping` (`config.py:27-41`) built in `knobs_from_dose` (`knobs.py:19-28`).

**Verification.** Flat-field probe across the declared profile set, then M-1 at apex. Declared set,
fixed before running: idx0 alone (control), [0,8] at 1.0/0.6, [0,8] at 1.0/1.0, [0,4,8] at
1.0/0.3/0.6. Every row reported.

**Falsification.** If every bimodal row scores below the idx0 control on M-1, or reproduces the
earlier multi-block collapse, the direction is closed permanently and must not be raised again.

**Cost.** 4 probe frames, about 2 minutes, plus one 40-frame confirmation only if a row wins.
**Admissibility.** ADMISSIBLE-ARM-A for the probe (it uses only the existing `depth` knob at more
than one value). **NEEDS-OWNER-APPROVAL** to promote into `knobs.py`, because it turns `depth` from a
scalar into a profile. **Depends on.** M-1.

### E-6, non-monotone `prior_precision` under ALBUS
**Goal.** Make the CFG mapping match the pharmacology rather than the simplest lerp.

**HYPOTHESIS.** A `prior_precision` that rises through the come-up and collapses only near apex causes
both a better-organised come-up and a cleaner breakthrough, because REBUS describes only the
high-agonism regime while lower occupancy can strengthen priors (VERIFIED that the ALBUS critique
exists, Safron and Juliani et al. 2025), and because this repo has independently observed that
lowering CFG degrades structure and scene adherence together (E-PRIOR).

**Files.** `knobs.py:24`, the single `prior_precision` line, plus two new `KnobShaping` fields
(`config.py:27-41`) for the rise peak and the dose at which collapse begins. Shape: rise from
`prior_w_base` to a declared `prior_w_peak` over D in [0, d_turn], then fall to `prior_w_min` over
[d_turn, 1]. `d_turn` declared before running, not tuned.

**Verification.** The knob-direction integrity check in `scripts/verify.sh --quick` must be
**extended, not relaxed**, to assert the new shape: monotone up below `d_turn`, monotone down above,
still ending at `prior_w_min`. Then one 40-frame run, M-1 at apex and M-4 at the end.

**Falsification.** If the non-monotone run scores no better on M-1 at apex and no better on M-2
through the come-up, the monotone mapping stays and ALBUS is recorded as having no expression in this
engine.

**Adjacent problem, flagged not fixed.** `prior_w_min: 6.0` means CFG never approaches 1, so
`prior_precision` currently spans 12 to 6 and never reaches the regime where guidance is off. Whether
that is intended is an owner question, not something to change inside this step.

**Cost.** 40 frames, about 20 minutes.
**Admissibility.** **NEEDS-OWNER-APPROVAL.** It alters a declared knob mapping.
**Depends on.** M-1, M-2.

**Gate G2.** One of E-4, E-5, E-6 moves a P0 metric beyond its control noise floor, or all three are
logged negative. Either way P3 proceeds; the point of the gate is that P3 runs on a known gain
configuration rather than an assumed one.

---

## 5. Phase 3, E-3, the lateral kernel

The highest-value step in the programme and the only route to a *selected* wavelength.

### E-3a, the operator, on flat field, before any trip
**Goal.** Determine whether a DoG lateral kernel inside `_amplify` can move the apex wavelength off
its architecture-inherited value.

**HYPOTHESIS.** Convolving the hooked activation with a std-normalised difference of Gaussians and
mixing it in at strength `gain - 1` before the tanh soft-clip causes the emergent pattern's
wavelength to track the kernel's analytically predicted wavelength, because a DoG is a band-pass
operator whose Fourier transform peaks at a frequency set by its two sigmas, because a spatially
structured zero-mean term is **not** annihilated by the downstream GroupNorm the way a uniform scalar
is, and because std-normalising the DoG term makes it carry the majority of the composite's variance
at apex gain rather than the 2 to 8 percent of power that made D-4's additive form ineffective.

**Where it goes, exactly.** Inside `_amplify` (`hooks.py:39-50`), between the gain multiply on line 40
and the soft-clip on lines 44-49:

1. Line 40 stays: `out = activation * gain`.
2. New: compute `band = dog(activation)` on the **unamplified** activation, normalise
   `band = band / band.std(dim=(2,3), keepdim=True).clamp_min(1e-6)`, then rescale to the
   activation's own per-channel std. Normalising against the *unamplified* input keeps the mix
   strength independent of both the sigmas and the gain, which is what stops a sixth free knob being
   smuggled in.
3. New: `out = out + (gain - 1.0) * band_matched`. The mix strength is `gain - 1`, so it is zero at
   rest, rides `D(t)` exactly as gain does, and introduces no new schedule.
4. Lines 44-49 unchanged, so the tanh saturation still bounds the result at `CLAMP_STD * std(activation)`.
   **Saturation applied to a band-passed field is the Turing-type composition; saturation applied to a
   broadband field is what produced the current inherited-scale texture.**
5. Line 50 `nan_to_num` unchanged.
6. The arm-B `_logpolar_warp` call on line 42 stays where it is, after the gain and before the clip,
   so E-3 and arm B compose without reordering.

**How the sigmas are derived, not tuned.** This is what keeps the step arm A.

- The activation grid at idx0 is 32x32 for a 512 px image, so **one activation cell is 16 image px**;
  at idx8 it is 64x64, so one cell is 8 image px. CLAUDE.md §8, VERIFIED.
- `sigma_e` is fixed at 1.0 activation cell for every configuration. It is the smallest kernel that
  is not the identity on the block's own sampling lattice, so it is determined by the block, not
  chosen.
- `sigma_i` is then the **only** remaining degree of freedom, and it is not chosen by eye either. The
  DoG's radial transfer function `exp(-sigma_e^2 k^2 / 2) - exp(-sigma_i^2 k^2 / 2)` peaks at
  `k_peak^2 = 2 ln(sigma_i/sigma_e) / (sigma_i^2 - sigma_e^2)`, giving predicted wavelength
  `lambda_cells = 2*pi/k_peak` and `lambda_px = lambda_cells * cell_size_px`. The sweep is defined by
  **inverting that formula** for a declared list of target wavelengths.

**The pre-registered sweep, declared here before any render.** Target wavelengths in image pixels:
**8, 12, 19, 24, 40, 64**, plus a `dog_off` control row. 19 and 24 are included deliberately because
they are the inherited values, so a kernel that does nothing still produces two correct-looking rows
and the regression exposes it. Each target is inverted to a `sigma_i` at `sigma_e = 1.0`, and both
the sigma pair and the predicted wavelength are printed in the table.

**The headline number is a regression, not a row.** Report the slope of measured wavelength (M-1's
whitened peak) against predicted wavelength across the seven rows, with the intercept. Slope near 1
means the kernel selects. Slope near 0 with an intercept near 24 means the scale is inherited and
E-3 is dead. **Every row reported, none dropped, no sigma selected on the basis of appearance.** That
is the discipline arm-A status rests on.

**Implementation on MPS, no new dependencies.** Separable depthwise Gaussian via
`torch.nn.functional.conv2d` with `groups=C`, fp32, reflect padding, kernel radius `ceil(3*sigma)`,
two passes per Gaussian and two Gaussians per DoG. Kernels built once per
(sigma, channels, device, dtype) and cached in a module-level dict keyed on that tuple, so they are
not rebuilt on all 30 denoise steps. Build in fp32; float64 is unsupported on MPS.

**Measured cost on this box (VERIFIED, coordinating session):** 1.36 ms at idx0
`(2, 320, 32, 32)` and 2.46 ms at idx8 `(2, 320, 64, 64)`, all finite, no fallback warning. Thirty
steps across two hooked blocks is about 230 ms per frame against 25 to 30 s, under 1 percent. **Do
not design around a compute cost that does not exist, and do not use that headroom as licence to add
anything else.**

**Verification.** Flat-field single frame per row, at apex knobs, on flat gray. Then M-1 on each,
then the regression. **Note (VERIFIED, log V-3): CFG is a mathematical no-op on no-caption flat-gray
probes**, because with an empty caption the conditional and unconditional embeddings are identical
and the guidance direction is exactly zero (`engine.py:226-229`). The flat-gray sweep therefore tests
the kernel and the gain only, which is what is wanted here, but **no `prior_precision` conclusion may
be drawn from it**.

**Falsification, stated sharply.** Regression slope below 0.5, or measured wavelength staying inside
18 to 32 px for the 8 px and 64 px target rows, kills E-3. That outcome would confirm
`conclusion.md` §6's structural claim at a much higher standard than it currently rests on, would be
a stronger publishable negative than D-4's, and would cancel P4 and P5.

**Cost.** 7 flat-field frames, about 4 minutes, plus metric time.
**Admissibility.** **NEEDS-OWNER-APPROVAL**, on two counts: it adds a spatial operator inside the
hook, and it re-opens a direction D-4 refuted. The approval request must carry the §0 amplitude
argument as the new evidence, or it is a relitigation. **Depends on.** M-1, G2.

### E-3b, the kernel on the scene, in a trip
Runs **only** if the E-3a regression passes. One 40-frame run at the single sigma pair whose predicted
wavelength is furthest from 24 px among the passing rows, chosen by the regression and not by
appearance. Verification: M-1 at apex including the symmetry columns, M-2 through the come-up, M-4 at
the end. Falsification: if the wavelength selection that appeared on flat gray disappears once the
scene and CFG are present, the kernel is being overridden by scene content, and the result is that
selection exists but is not scene-robust. Cost 40 frames, about 20 minutes.

**Gate G3.** Regression slope above 0.5 on flat field **and** the selected wavelength survives into
the scene run. Below that, stop: P4 and P5 are cancelled and the programme's deliverable is the
sharpened negative result.

---

## 6. Phase 4, persistent field state and autonomous motion

### E-7, an Amari/Wilson-Cowan field carried between frames
**Goal.** Give the breakthrough motion that is a property of the system rather than of the parameter
schedule.

**HYPOTHESIS.** Carrying a single-channel field tensor across frames and updating it under a
Mexican-hat recurrent step causes sustained, spatially propagating change at constant knobs and
constant noise, because the current apex is one frozen noise realisation under drifting parameters
(VERIFIED, `conclusion.md` §4) and `recurrence` is a scalar blend coefficient which can produce drift
but never a limit cycle or a travelling wave, whereas a field with lateral coupling and saturation
supports both.

**State design, deliberately minimal.** One tensor per hooked block, shape `(1, 1, H, W)` at the
block's native resolution. Single-channel so the state cannot become a stored memory of image content
and so the return cannot be smuggled in through it. Updated once **per frame**, not per denoise step,
so the DDIM trajectory inside a frame stays a clean deterministic function of its inputs:

```
drive   = channel-mean of the hooked activation at the first denoise step of this frame
u_next  = u + dt * (-u + w * DoG(tanh(u)) + drive)
```

`DoG` is the same operator and the same derived sigmas as E-3, which is why this step depends on E-3
and must not be attempted before it. `dt` and `w` are declared before running and swept as a
pre-registered pair, reported in full.

**Exact signature changes.**
- `hooks.attach` (`hooks.py:66-79`) gains a `field: dict[int, Tensor] | None` argument.
  `_make_hook` (`hooks.py:53-63`) closes over the field slot for its block index, reads it, adds
  `(gain - 1) * D * u_normalised` broadcast across channels, and writes the updated `u` back on the
  **first** invocation of each frame only, via a per-frame call counter reset by `attach`.
- `engine.render_frame` (`engine.py:147-160`) gains `field_state: dict[int, Tensor] | None = None`
  and returns `tuple[Image.Image, dict[int, Tensor]]` instead of a bare image. **This is a breaking
  signature change**; every caller in `tests/` must be updated in the same commit or the compile gate
  in `verify.sh --quick` will catch it.
- The `run.py` loop (`run.py:82-106`) carries `field` alongside `prev` across iterations and
  initialises it to `None`, which reproduces today's behaviour exactly when the feature is off.

**Determinism.** The field update is deterministic given the seed and the previous field, and the
field starts at zeros. The run stays reproducible from the config alone. No RNG is added.

**The return is protected by construction.** The field's contribution is multiplied by
`(gain - 1) * D`, both of which fall to near zero by t = 12, so the field cannot hold the image away
from the scene during come-down. **This must be asserted in the integrity check, not merely
intended.**

**Adjacent problem, flagged not fixed.** `render_frame` attaches hooks only when `knobs.gain != 1.0`
(`engine.py:217`). With a field, the hook is also the field's update site, so at exactly gain 1.0 the
field would silently stop evolving. Do not quietly change that condition; raise it as a decision,
because the same condition is what keeps the rest frames hook-free.

**Verification.** A 12-frame hold segment at apex knobs, field on versus field off, scored with M-3.
The two calibration poles are already known: 22.30 decaying (frozen, no field) and 56.20 with the
geometry destroyed (per-frame reseed).

**Falsification.** If the field-on hold shows the same decaying slope as field-off, the field is not
sustaining anything and is decoration. If it shows churn-level change with lag-1 peak correlation
below about 0.5, it has destroyed continuity and is no better than reseeding.

**Cost.** 24 frames for the paired hold segments, about 12 minutes, plus one 40-frame arc run if it
passes.
**Admissibility.** **NEEDS-OWNER-APPROVAL.** New persistent state is well outside the 5 knobs. Argue
it as substrate, not content: cortical recurrent dynamics exist sober, the field carries no image and
no semantics, and its influence rides `D(t)`. **Depends on.** E-3 (shares the operator), M-3, G3.

### E-8, reinstate D-5 slerp noise drift
**Goal.** Unfreeze the noise without destroying continuity.

**HYPOTHESIS.** Interpolating the initial noise spherically between a small number of fixed anchor
draws causes sustained mutation with preserved continuity, because frozen noise plus constant knobs
makes each frame the same map applied to the last and converges to a fixed point, while independent
per-frame draws destroy the correlation continuity depends on.

**Status.** **Not a new design.** Implemented, measured and owner-approved 2026-08-28, then removed in
the paper-codebase revert. Numbers already in hand (VERIFIED): slerp std 1.0035 versus naive lerp
0.7127, consecutive-frame correlation 0.95, anchor correlation 0.009, plateau change 29.80 sustained
versus 22.30 decaying. Restore `engine._slerp` / `_drifting_noise` and the `noise_anchors` /
`noise_phase` config fields from the parked backup rather than rewriting them.

**Verification.** M-3 on the same paired hold segments as E-7, so the two mechanisms are attributable
separately. Run E-7-off/E-8-on, E-7-on/E-8-off, and both, before either goes in the deliverable.

**Falsification.** If E-8 alone reproduces E-7's M-3 signature, the field adds nothing and E-7 should
be dropped as unnecessary machinery. That is the cheaper explanation and it must be tested before the
field is kept.

**Cost.** 24 frames, about 12 minutes.
**Admissibility.** **NEEDS-OWNER-APPROVAL to reinstate**, though it carries prior approval in
principle. Note honestly: the previous verdict was that it delivers motion and regime change, **not a
new kind of geometry**. **Depends on.** M-3.

---

## 7. The fixed-seed question

**Recommendation: do not introduce per-frame seed variation. Use E-8's anchored slerp drift instead.**

The evidence is already decisive (VERIFIED, E-PLATEAU). Independent per-frame seeds give
change-per-frame 56.20 with consecutive frames that are essentially unrelated images and the cell
structure lost, which is churn rather than motion. Anchored slerp gives 29.80 sustained with 0.95
consecutive correlation.

The cost accounting matters because it is small, and that is the point. Slerp between K anchors
derived from `cfg.seed` keeps the run a pure function of the config, so reproducibility is untouched
and `output/past` comparisons stay valid. Free per-frame seeds would make the run reproducible only if
the seed sequence itself is recorded, and would break the byte-identical re-render check used to
verify the 2026-08-28 revert. **Anchored drift preserves that check; free seeds do not. Keep the
check.**

---

## 8. Phase 5, arm B, and why it comes last

### E-9, log-polar readout on a banded field
**Goal.** Turn a wavelength-selected planar pattern into radial form constants.

**HYPOTHESIS.** The log-polar warp produces spirals, tunnels and rings only when the field it acts on
already has a selected spatial frequency band, because the complex-log retinocortical map converts
cortical **plane waves** into radial planforms, and a map applied to a broadband texture produces a
warped broadband texture. That is a plausible mechanistic account of why the earlier arm-B attempt
yielded speckle that scored out of band.

**Ordering, non-negotiable.** E-9 after E-3. Running arm B before the kernel repeats the previous null
and teaches nothing.

**Files.** None. `hooks._logpolar_warp` (`hooks.py:17-36`) exists and is already positioned after the
gain multiply and before the clip, which composes correctly with the E-3 insertion above. A config
with `geometry_arm: B_logpolar_bias` plus the winning E-3 sigmas is the whole experiment.

**Verification.** M-1's radial-versus-angular split is the metric that matters, since
`tests/geometry_score.py`'s gated clarity reads approximately zero on arm B because arm B falls out
of the 18 to 32 px band. **Do not read that zero as failure and do not widen the band to accommodate
arm B; that would be gate-weakening.** Report the gated score and M-1 side by side.

**Falsification.** If the radial/angular split with the kernel on is no better than without it, the
ordering hypothesis is wrong and arm B's failure has some other cause.

**Cost.** 3 flat-field frames plus one 40-frame run, about 22 minutes.
**Admissibility.** **ARM-B-DECLARED-ASSUMPTION**, already declared in the codebase. Never mixed into
an arm-A result. **Depends on.** G3, M-1.

**Orientation-selective coupling (Bressloff's shift-twist) is out of scope for this plan.** It
requires an orientation dimension SD1.5 activations do not have, so implementing it means inventing a
representation and then imposing structure on it. That is a declared modeling assumption of a much
heavier kind than the log-polar map, and it belongs in a separate proposal with its own approval.

---

## 9. Do not do this

Each fails an admissibility test or has already been refuted. Recorded so a future session does not
spend renders relitigating them.

1. **Render at 640 or 768.** Refuted (`tests/sweep_resolution.py`): wavelength locked near 24 px at
   every resolution, clarity dropped, cost tripled.
2. **Tighten `CLAMP_STD` below 6.** Refuted (`tests/sweep_clamp.py`): geometry collapses to flat.
3. **Monotone shallow-to-deep depth sweep.** Refuted (E-DEPTH) and, per `neuro-reference.md` §1,
   anatomically wrong from the start. E-5's bimodal profile supersedes it; it is not the same
   experiment.
4. **Renormalise to the original norm inside `_amplify`.** Exact identity for a uniform gain,
   probe-verified at 0.0000 change. It nulls the knob while looking responsible.
5. **Decay gain across frames to stop deepfrying.** Refuted, made it worse. `_match_contrast` is the
   approved mechanism.
6. **Any image-space or activation-space sharpening, unsharp masking, or compositing the photo back
   in pixel space.** It manufactures exactly the detail the experiment claims emerges.
   `_match_contrast` is the one approved post-process and it stays labelled an assumption.
7. **Weakening `BIASED_WORDS` or hand-writing a caption with scene adjectives.** The filter raising is
   correct behaviour. Only a neutral literal description, or a different photo.
8. **`scene_min` to 0.** Owner decisions D-1 and D-2 remain unapproved. `scene_min` stays above 0, and
   `conclusion.md` §4 shows a 0.4 floor already permits total scene loss, so the breakthrough does not
   need it.
9. **Widening `geometry_score.py`'s 18 to 32 px band** to accommodate arm B or a new wavelength.
   Gate-weakening. If E-3 selects a genuinely different wavelength, report it against M-1 and leave
   the historical gate alone.
10. **Anything aimed at producing entities**, including deep-block semantic intervention, agent
    prefixes, or figure-adjacent captions. `conclusion.md` §7 closes the category, not merely a route.
11. **Reading flat-gray probes as evidence about `prior_precision`.** CFG is a mathematical no-op with
    an empty caption; that column is meaningless in every existing `tests/sweep_*.py` flat-gray table.
12. **Calling the flat-gray output a lattice.** V-3 looked at it: chromatic speckle with a
    characteristic spacing. The scale is seed-robust; the regularity is not there.

---

## 10. Risk register

| Failure mode | Where it bites | Guard |
|---|---|---|
| **NaN or black frames** | E-3 adds an operator before the clip; E-4 `both` mode hits the up path twice | fp32 only; the tanh clip at `CLAMP_STD * std` stays after every new operator; `nan_to_num` at `hooks.py:50` and `engine.py:232` unchanged; every new mode gets a flat-field single frame before any trip. If `nan_to_num` fires every step, that is upstream numerical trouble, not a knob to lower. |
| **Deepfried frames** | E-3's normalised DoG raises the composite's effective amplitude relative to D-4's weak additive form, which is the intended change and also the risk | clip fraction is a reported column on every sweep row, threshold under about 10 percent; a row above it is reported, not silently dropped. Recall gain 1.7 fried worse than 3.2, so raw gain is not the diagnostic; feedback compounding is. |
| **Feedback runaway over long plateaus** | E-7 and E-8 both operate on hold segments | `_match_contrast` stays on; the field's influence is gated by `(gain - 1) * D`; hold segments capped at 12 frames until M-3 shows a bounded change rate. Do not decay gain in-loop. |
| **CFG replacing the subject on texture scenes** | E-6 raises CFG through the come-up | keep `resources/scene.jpg` as the reference throughout; any scene change is a separate experiment. Report M-4 on every E-6 run so subject replacement shows up as closure failure. |
| **A tuned parameter smuggled in as derived** | E-3's mix strength, E-7's `dt` and `w` | mix strength fixed at `gain - 1` and the DoG std-normalised, so no strength parameter exists; sigmas inverted from declared target wavelengths; `dt` and `w` declared and swept in full. Any row selected on appearance voids arm A. |
| **Metric blindness repeating the `scene_fidelity` mistake** | all of P0 | every metric ships with a negative control in the same output, and M-4's different-photo control is mandatory. |
| **Signature change breaking callers** | E-7 changes `render_frame`'s return type | update every `tests/` caller in the same commit; `verify.sh --quick` compiles them, so a missed caller fails the gate rather than a run. |
| **Re-running a refuted direction** | E-3 versus D-4, E-5 versus multi-block | both steps must state the specific new evidence in the run log before the render starts. |
| **Losing byte-identical reproducibility** | E-2's jitter, E-8's drift | both seeded from `cfg.seed` and advanced deterministically by frame index; the re-render-and-compare check stays available. |

---

## 11. Definition of done, as measurements

Done when a single run, from one pre-registered config, produces all of the following, each with its
control printed:

1. **Come-up.** M-2 above 0.6 through frames 00 to 11 while `gain` rises, with the blurred-scene
   control below 0.2. Detail preserved, not resynthesised.
2. **Geometry.** M-1 at apex: whitened bump above 5 (against the hex-lattice control's 14.5 and the
   current run's 1.10) **and** measured wavelength within 25 percent of the E-3 kernel's predicted
   wavelength **and** at least one of mirror-LR or rot60 above 0.5 (against the current run's 0.049
   and -0.015, and controls at 0.98 to 0.99).
3. **Breakthrough.** On a hold segment at apex, M-3 shows a non-decaying consecutive-frame change rate
   with lag-1 peak correlation above 0.7 and a consistently signed cross-correlation offset. Motion
   that is a property of the system, distinguishable from both the 22.30-decaying frozen pole and the
   56.20 churn pole.
4. **Return.** M-4 with RMSE below 0.05 and M-2 above 0.8 against frame 00, with the different-photo
   control below 0.3, **on the jittered-input config**, so closure is demonstrated rather than
   constructed.
5. **Integrity.** `scripts/verify.sh` full passes, quoted, from a run executed in the reporting
   session. Every sweep reported in full with no dropped rows. Arm labelled on every figure.

Item 2 is the one that can fail on structural grounds. If the P3 gate fails, the definition of done
reduces to items 1, 3, 4 and 5 plus the E-3 regression reported as a negative, and that is a complete
and publishable outcome.

---

## 12. What none of this would establish

Stated plainly so nobody later reads more into a green definition of done than it carries.

- **Not qualia, and not phenomenology.** Every result here is a computational signature in an image
  sequence. Nothing in this engine has an experience, and "the model is tripping" is never an
  available sentence.
- **Not a model of the visual system.** SD1.5's U-Net is not cortex. A DoG in a convolutional feature
  map is a mathematical analogue of Mexican-hat connectivity, not an implementation of it, and the
  "block index equals cortical level" mapping is a convenience with no anatomical warrant beyond
  ordering.
- **Even a perfect form-constant score would not show that DMT geometry arises this way.** It would
  show that a Turing-type instability produces form-constant-like patterns in *this* system, which
  Ermentrout and Cowan already established analytically in 1979. The engine would be reproducing a
  known mathematical result in a new substrate, and any bridge from that to human phenomenology is an
  argument, not a measurement.
- **The kernel is an addition, not an emergence.** If E-3 passes, the honest sentence is that the
  wavelength was selected by a kernel we installed with sigmas derived from the architecture, not
  that the wavelength emerged from parameter motion. The scalar-knobs-alone claim stays limited to
  what has already been shown: a reversible transition into a periodic, scene-independent regime,
  with periodicity and without symmetry.
- **Entities remain outside the experiment's power entirely**, and their absence carries no
  evidential weight about DMT. That is a determined property of the architecture and does not change
  no matter what any phase returns.
- **The dose curve is a stipulation.** `D(t)` is a shape we chose, and the DMTx pilot's finding that
  effects plateau while plasma keeps rising is already an argument against a straight lerp anywhere in
  `knobs.py`. Nothing in this plan tests the dose mapping itself.

---

## 13. Total cost

| Phase | Renders | Wall clock |
|---|---|---|
| P0 metrics | 12 frames of hold segment for M-3 calibration | about 6 min render, plus development |
| P1 (E-1, E-2) | 83 frames | about 42 min |
| P2 (E-4, E-5, E-6) | 47 probe + 120 trip frames | about 85 min |
| P3 (E-3a, E-3b) | 7 probe + 40 trip frames | about 24 min |
| P4 (E-7, E-8) | 48 hold + 40 trip frames | about 44 min |
| P5 (E-9) | 43 frames | about 22 min |
| **Total if every gate passes** | **about 440 frames** | **about 3 h 45 min of render**, backgrounded |

Renders are not the constraint. The P0 metrics and the approval decisions on E-3, E-4, E-6 and E-7
are.

**Files this plan touches:** `src/measure/metrics.py`, `src/render/hooks.py`, `src/render/engine.py`,
`src/core/knobs.py`, `src/core/config.py`, `run.py`, plus new configs under `configs/`.

**Do-not-touch list, unchanged throughout:** `engine._strip_bias` and `BIASED_WORDS`
(`engine.py:20-36`, `57-74`), the DDIM lock (`engine.py:78-79`), the fp32 rule, `scene_min > 0`,
`CLAMP_STD = 6`, `tests/geometry_score.py`, and `output/past`.

---

## 14. Owner decisions this plan requires

Nothing in P0 or P1 needs a decision. Everything below does, and each is independent.

| id | decision | new evidence offered |
|---|---|---|
| **A-E4** | may `gain` amplify the residual stream instead of the forward path | 5-HT2A is on apical dendrites, where feedback terminates (`neuro-reference.md` §1) |
| **A-E5** | may `depth` become a profile rather than a scalar | receptor density is bimodal, not a shallow-to-deep ramp |
| **A-E6** | may `prior_precision` be non-monotone in dose | ALBUS: low occupancy can strengthen priors |
| **A-E3** | may a derived-sigma DoG kernel re-enter `_amplify` after D-4 | D-4's failure is attributable to amplitude (2 to 8 percent of power), not to the kernel; std-normalisation plus a predicted-vs-measured regression is a different experiment |
| **A-E7** | may the engine carry persistent field state across frames | the apex is currently one frozen noise realisation under drifting parameters, so no dynamics exist to measure |
| **A-E8** | may D-5 slerp drift be reinstated | already approved once and measured positive; removed only by the codebase revert |
