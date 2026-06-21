# VAE & Latent Space Study
Stable Diffusion thinks in small compressed code instead of raw pixels. The VAE handles compressing pixels into latent space, then decompressingback into pixels. The UNet generates every feature in between that process of compressing and decompressing.

VAE handles compression and rendering. Kind of like the eyes.
> VAE Encoding = light to compressed code
> VAE Decoding = compressed code to image

UNet handles the generation. Kind of like the mind.
> UNet Sequence = working on the code (priors, inference, guidance, hallucination, ect)

## What is a latent?
VAE compresses internal data into latents. Raw pixels store the appearance, but latents store the meaning.
> Example 512x512 image has 3 layers/channels (RGB) amounting to 786,432 values (3x512x512)
> While a latent has 4 layers amounting to 16384 values (4x64x64).
> Latent locations are single cells inside the 64x64 grid holding a vector of 4 layers. The single cells correspond to a 8x8 patch of the orginal image so the cell represents like a summarizaiton of the patch
> The latent location doesnt store colors like raw pixels but features like edges, surfaces, textures, etc.
> This way UNet works on smaller loads (latents) rather than large amounts of raw pixels which would be more expensive to process.

## Brain Relationship
Our cortex doesnt use raw data from our retina, instead it builds a squeezed down percept of compressed internal code (edges, surfaces, textures, etc).
> Latent space is compressed internal code. A DMT doesnt edit the internal data, it skews the internal code which renders a DMT like visual.