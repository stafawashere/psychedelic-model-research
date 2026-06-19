from __future__ import annotations
import re
import warnings
import hooks
import numpy as np
import torch
from PIL import Image
from diffusers import DDIMScheduler, StableDiffusionPipeline
from knobs import Knobs


_DATATYPES = {
    "float32": torch.float32,
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
}

BLIP_MODEL = "Salesforce/blip-image-captioning-large"
DENOISE_STEPS = 30 
BIASED_WORDS = frozenset(
    {
        # geometry / form constants
        "fractal", "fractals", "tunnel", "tunnels", "spiral", "spirals",
        "lattice", "lattices", "grid", "grids", "honeycomb", "tessellation",
        "tessellated", "kaleidoscope", "kaleidoscopic", "mandala", "mandalas",
        "geometry", "geometric", "geometrical", "symmetry", "symmetrical",
        "symmetric", "web", "webs", "mesh", "swirl", "swirls", "swirling",
        "vortex", "vortices", "spiraling", "spiralling", "checkerboard",
        # entities / figures
        "being", "beings", "entity", "entities", "alien", "aliens", "creature",
        "creatures", "elf", "elves", "deity", "deities", "god", "gods", "angel",
        "angels", "demon", "demons", "spirit", "spirits", "figure", "figures",
        # psychedelic vocabulary
        "psychedelic", "psychedelics", "dmt", "lsd", "trippy", "trip", "tripping",
        "hallucination", "hallucinations", "hallucinatory", "hallucinate",
        "hallucinating", "sacred", "cosmic", "mystical", "visionary", "ethereal",
        "surreal", "surrealist", "dreamlike", "otherworldly", "psychotropic",
    }
)


def _empty_cache(device) -> None:
    """Return cached-but-unused blocks to the MPS allocator (no-op off MPS)."""
    name = getattr(device, "type", None) or str(device)
    if name == "mps" and torch.backends.mps.is_available():
        torch.mps.empty_cache()


def _compute_dtype(pipe) -> torch.dtype:
    """Dtype the diffusion loop runs in (the UNet's) — bf16 on a memory-tight box."""
    return next(pipe.unet.parameters()).dtype


def _vae_dtype(pipe) -> torch.dtype:
    """Dtype the VAE runs in; kept fp32 so half-precision frames don't decode to black."""
    return next(pipe.vae.parameters()).dtype


def _strip_bias(text: str) -> str:
    tokens = re.split(r"(\W+)", text)
    removed = [t for t in tokens if t.lower() in BIASED_WORDS]
    kept = [t for t in tokens if t.lower() not in BIASED_WORDS]
    cleaned = re.sub(r"\s+", " ", "".join(kept)).strip(" ,.;:-")

    if removed:
        warnings.warn(
            f"caption_scene stripped biased vocabulary {sorted(set(removed))} "
            f"from the caption (integrity rule #2)",
            stacklevel=2,
        )
    if not cleaned:
        raise ValueError(
            f"caption {text!r} contained only biased vocabulary; cannot build a "
            "neutral scene caption"
        )
    return cleaned


def load_pipeline(model_id: str, device: str, datatype: str, scheduler: str):
    if scheduler != "ddim":
        raise ValueError(f"only the deterministic ddim scheduler is supported, got {scheduler!r}")

    torch_datatype = _DATATYPES.get(datatype)
    if torch_datatype is None:
        raise ValueError(f"unsupported datatype {datatype!r}; expected one of {sorted(_DATATYPES)}")

    pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch_datatype)
    pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)
    pipe.safety_checker = None
    pipe.feature_extractor = None

    pipe = pipe.to(device)
    pipe.vae.to(torch.float32)
    pipe.enable_attention_slicing(1)
    pipe.vae.enable_slicing()
    return pipe


def caption_scene(scene_path: str) -> str:
    from transformers import BlipForConditionalGeneration, BlipProcessor

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    processor = BlipProcessor.from_pretrained(BLIP_MODEL)
    model = BlipForConditionalGeneration.from_pretrained(
        BLIP_MODEL, torch_dtype=torch.float32
    ).to(device)

    image = Image.open(scene_path).convert("RGB")
    inputs = processor(image, return_tensors="pt").to(device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=30)

    caption = processor.decode(out[0], skip_special_tokens=True)
    del model, processor, inputs, out, image
    _empty_cache(device)

    return _strip_bias(caption)


# preprocess pil then encode tensor for latent
def _preprocess(image: Image.Image, size: tuple[int, int]) -> torch.Tensor: # preprocess pil image into tensor
    image = image.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    arr = np.asarray(image, dtype=np.float32) / 255.0
    t = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    return t * 2.0 - 1.0

def _encode(pipe, image_t: torch.Tensor, generator: torch.Generator) -> torch.Tensor: # encode tensor into latent
    device = getattr(pipe, "device", torch.device("cpu"))
    image_t = image_t.to(device=device, dtype=_vae_dtype(pipe)) # match the fp32 VAE
    latent_dist = pipe.vae.encode(image_t).latent_dist
    z = latent_dist.sample(generator=generator)
    z = z * pipe.vae.config.scaling_factor
    return z.to(_compute_dtype(pipe)) # hand the latent back in the loop's dtype (bf16)

# decode latent then postprocess tensor into pil
def _postprocess(sample: torch.Tensor) -> Image.Image: # postprocess tensor into pil
    sample = (sample / 2.0 + 0.5).clamp(0.0, 1.0)
    arr = sample.squeeze(0).permute(1, 2, 0).float().cpu().numpy()
    return Image.fromarray((arr * 255.0).round().astype(np.uint8))

def _decode(pipe, latents: torch.Tensor) -> torch.Tensor: # decode latent into tensor
    latents = latents.to(_vae_dtype(pipe)) / pipe.vae.config.scaling_factor
    return pipe.vae.decode(latents).sample


@torch.no_grad()
def render_frame(
    pipe,
    x_scene: Image.Image,
    prev_frame: Image.Image,
    caption: str,
    knobs: Knobs,
    seed: int,
    *,
    steps: int = DENOISE_STEPS,
    logpolar: bool = False,
) -> Image.Image: # one frame: blend prev + scene in latent, denoise, decode to rgb
    device = getattr(pipe, "device", torch.device("cpu"))
    rng = torch.Generator(device="cpu").manual_seed(seed) # mps was being buggy so im gonna only use cpu for this change if ur device prefers it

    width, height = x_scene.size
    scene_pixels = _preprocess(x_scene, (width, height))
    prev_pixels = _preprocess(prev_frame, (width, height))
    scene_latent = _encode(pipe, scene_pixels, rng)
    prev_latent = _encode(pipe, prev_pixels, rng)

    scene_weight = knobs.scene_precision
    prev_weight = knobs.recurrence
    total_weight = scene_weight + prev_weight
    if total_weight <= 0:
        blended_latent = scene_latent
    else:
        scaled_scene = scene_weight * scene_latent
        scaled_prev = prev_weight * prev_latent
        blended_latent = (scaled_scene + scaled_prev) / total_weight

    # the pixel tensors and source latents are consumed; release the VAE-encode
    # scratch before the denoise loop so it starts with the most free memory.
    del scene_pixels, prev_pixels, scene_latent, prev_latent
    _empty_cache(device)

    denoise_strength = min(0.85, max(0.2, 0.2 + knobs.recurrence))

    pipe.scheduler.set_timesteps(steps, device=device)
    active_step_count = min(round(steps * denoise_strength), steps)
    first_step_index = max(steps - active_step_count, 0)
    denoise_timesteps = pipe.scheduler.timesteps[first_step_index:]
    if len(denoise_timesteps) == 0:
        denoise_timesteps = pipe.scheduler.timesteps[-1:]

    initial_noise = torch.randn(blended_latent.shape, generator=rng, dtype=blended_latent.dtype)
    initial_noise = initial_noise.to(device)
    latents = pipe.scheduler.add_noise(blended_latent, initial_noise, denoise_timesteps[:1])

    guidance_scale = knobs.prior_precision
    use_guidance = guidance_scale > 1.0
    prompt_encoding = pipe.encode_prompt(caption, device, 1, use_guidance, None)
    prompt_embeds, negative_embeds = (
        prompt_encoding if isinstance(prompt_encoding, tuple) else (prompt_encoding, None)
    )

    if use_guidance and negative_embeds is not None:
        text_embeddings = torch.cat([negative_embeds, prompt_embeds])
    else:
        text_embeddings = prompt_embeds
        use_guidance = use_guidance and negative_embeds is not None

    hook_handles: list = []
    if knobs.gain != 1.0:
        hook_handles = hooks.attach(pipe.unet, knobs.depth, knobs.gain, logpolar) or []

    try:
        for timestep in denoise_timesteps:
            unet_input = torch.cat([latents] * 2) if use_guidance else latents # cond + uncond
            unet_input = pipe.scheduler.scale_model_input(unet_input, timestep)
            noise_prediction = pipe.unet(
                unet_input, timestep, encoder_hidden_states=text_embeddings
            ).sample

            if use_guidance:
                unconditional_pred, conditional_pred = noise_prediction.chunk(2)
                guidance_direction = conditional_pred - unconditional_pred
                noise_prediction = unconditional_pred + guidance_scale * guidance_direction # base + distance * direction
                
            latents = pipe.scheduler.step(
                noise_prediction, timestep, latents, generator=rng
            ).prev_sample
            latents = torch.nan_to_num(latents, nan=0.0, posinf=4.0, neginf=-4.0) 
    finally:
        if hook_handles:
            hooks.detach(hook_handles)

    frame_pixels = _decode(pipe, latents)
    result = _postprocess(frame_pixels)
    _empty_cache(device)

    return result
