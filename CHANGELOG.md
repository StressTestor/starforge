# changelog

## v4.0.0 - 2026-06-13

the black hole actually lenses now.

- **gravitational disk lensing.** the accretion disk's far side bends up over the top of the shadow and curls beneath it (the Interstellar / EHT look). the disk's own emission is re-gathered through a precomputed, frame-invariant fold map. stays deterministic numpy, no ray tracer.
- **emergent photon ring.** the ring now comes from the light-bending divergence piling up at the photon sphere (`build_deflection_lut` / `sample_emergent_ring`), not a hand-drawn gaussian. it's zero inside the shadow so the captured region stays dark.
- **curator / generator split.** generation stays the deterministic source of truth; a pluggable `Curator` (default `HeuristicCurator`) only ranks candidates. new `--curator` flag, recorded in the manifest. a learned ranker can drop in without touching reproducibility.
- **colour-harmony scoring.** the heuristic curator gained a saturation-based colour-harmony term alongside tonal range, thirds, focal balance, busy penalty, and ring separation.
- **deliberate vignette.** the frame vignette is now image-centered, so it darkens the frame edges regardless of where the off-center black hole sits, instead of being a side effect of the subject radius.
- **housekeeping.** version scheme reconciled to semver (`4.0.0`), project id `starforge-lab`; dead colour-stop constants dropped from `palette.py`; `work/starforge` is now the canonical git repo with generated media gitignored.

## v3.0.0

- seeded structural genome: the seed drives macro structure (position, tilt, banding, jet angle/asymmetry, horizon, lensing strength, beaming, palette temperature), not just star/grain noise.
- composition scoring with inspectable reasons; ranked cross-preset collection.
- bilinear background lensing, poster supersampling, console script, CI.

## v2.0.0

- seed sweep + selection, GIF/MP4/WebM export, static lab page, manifest.
