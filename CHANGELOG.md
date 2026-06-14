# changelog

## v5.0.0 - 2026-06-14

starforge isn't only black holes now.

- **subjects.** a `subject` axis on the genome (`--subject`), with the black-hole render path unchanged from v4 and a new **`lensed-galaxy`** subject. The renderer dispatches on `genome.subject`; the seam lives in the genome, not the curator or config.
- **lensed-galaxy.** a singular-isothermal-sphere lens (reusing the single-center machinery) bends a deterministic background galaxy field into Einstein rings and arcs around a warm foreground elliptical, the Hubble gravitational-lens look. Stays deterministic numpy, stays a seamless loop.
- **RNG-order lock.** the black-hole genome draw sequence is now pinned by a byte-identity golden test (`test_rng_order_lock_v5`) against fixed v4 seeds, so any future genome field that re-rolled the gallery is caught immediately. New fields must be drawn after the existing sequence.
- semver 5.0.0; subject-aware title strip; `subject` recorded in the manifest.

deferred to a future release: a timeline / merger mode (would break the seamless-loop identity) and a binary-merger subject (needs real two-center lensing / ray-tracing, out of the single-center architecture). See ROADMAP.md.

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
