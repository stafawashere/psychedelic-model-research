# UNet Study
UNet corresponds to our cortex and how we build a percept from internal data. Our cortex takes internal data and instead of painting a picture it spots errors/mismatches and clears it until its certain the internal data matches its interpitation/prediction. UNet simillarly predicts noise and which then scheduler subtracts from the noisy latent repeatedly.
> Predict the error, and subtract it

## UNet anatomy
The UNet is a U shape. Going DOWN the left = feedforward, like V1 -> higher visual areas. Resolution shrinks 64->32->16->8 and channels grow 320->1280. Im throwing away *where* stuff is to keep *what* it is. The MID block (bottleneck) is the deepest most abstract point, just the gist of the whole image. Going UP the right = feedback, rebuilding the image back to full res.
> down = throw away detail for meaning. up = rebuild. space turns into meaning then back.

skip connections = the down block saves a photocopy of its detailed feature map and hands it straight ACROSS to the matching up block, skipping over the bottleneck. So the up side gets the abstract gist (from below) PLUS the sharp detail (from the skip). Without it the rebuild is blurry guesswork.
> the summary tells WHAT, the skip tells WHERE

## Hooks = the gain/depth knob (cortical gain)
This is the 5-HT2A move. I pick one level of the hierarchy and crank how loud it fires. DeepDream style: amplify whatever that layer already sees. I dont rewrite the UNet, I clip a forward hook onto one block.

A forward hook is just a function I attach from outside. PyTorch calls it automatically the moment that block finishes its forward pass and hands me its output, so I can multiply it by gain. It FIRES when data flows out of the tapped block.
> a hook is something I do to the network. a skip is something the network does to its data. NOT the same thing.

- skip connection = the UNets OWN built in wiring (res_samples, down->up). Its there at gain=1, there with no hook at all. I didnt add it. It ROUTES data.
- forward hook = a camera I clip on from outside. fires when a block finishes, edits its output. remove it and the network runs exactly the same. its my intervention.

knobs:
- `depth` = just an index into hookable_blocks (flat list: down, mid, up = idx 0-8). picks WHICH level I poke. 0 = low level edges, 4 = the gist, 8 = back near full res.
- `gain` = how hard I multiply the activations at that level. louder firing.

`hookable_blocks` = `[*down_blocks, mid_block, *up_blocks]`. position in the list IS depth.

## Why the hook checks isinstance(output, tuple)
its about the SHAPE the block hands back, not about routing:
- down block hands back TWO things -> a tuple: `(summary, *res_samples)`. summary = output[0] keeps going down. res_samples = output[1:] are the skip photocopies going across.
- mid/up block hands back ONE bare tensor (no skip starts there), so nothing to unpack.

In a down block I amplify ONLY output[0] (the forward summary) and pass output[1:] (the skip copies) through untouched. If I amplified both, the disturbance hits the up path TWICE (once down the forward path, once across the skip) -> stronger, way more likely to blow up to NaN.
> poke the forward path once. leave the skip clean.

## Two arms (logpolar)
- arm A = pure emergence, NO warp. honest. does geometry show up from knobs alone? if not thats my negative result.
- arm B = `_logpolar_warp`, bakes in the retina->cortex (log-polar) map so straight cortical stripes become rings/spirals/rays = Kluver form constants. its a DECLARED assumption, I partly built the geometry in. never the headline, never mixed with A.
> arm A asks "does it emerge for free". arm B asks "if I grant the one real piece of wiring, does the rest follow".

