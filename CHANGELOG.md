# changelog

## v7.0.1 - 2026-06-19

three real bugs, surfaced by an external integration consuming the engine contract.

- **`--studio --curator studio` no longer crashes.** The studio curator emits a different reason set (`subject_focus`, `detail`, …) than the heuristic, but the selection frontier + studio bars hardcoded the heuristic's `METRIC_KEYS` and `KeyError`'d on `tonal_range`. The metric set is now **data-driven** (`selection.metric_keys` derives it from the candidate rows), so any curator's reasons rank and render. Studio metric labels gained `focus`/`detail`, with a fallback for unknown keys.
- **plain releases pass `inspect_outputs.py`.** The validator required `seed_gallery.png` / `collection_gallery.png` (and a non-empty collection) unconditionally, so a plain render — no `--seed-gallery`/`--batch` — failed validation. It now reads the manifest first and validates each release against its OWN declared `assets`.
- **the lab page stops referencing assets it doesn't have.** `index.html` always emitted a `seed_gallery.png` `<img>`; a plain release had a broken image. The seed-sweep panel is now conditional on the asset being present, like the collection/studio/video panels.

Renders are byte-identical to v7.0.0 (these are read-only/tooling paths). semver 7.0.1.

## v7.0.0 - 2026-06-19

starforge stopped pretending one number knows what's good.

- **the selection studio.** `--studio` writes a self-contained, offline `studio.html`: a compare grid over the whole sweep with a **Pareto frontier** (the non-dominated set, which no scalar can surface), a **per-subject de-biased ranking**, the metrics exposed as bars, a raw-vs-de-biased sort toggle, and pin/reject with an exportable pins manifest. Read-only over the rendered artifacts, so it changes nothing about how a render is made.
- **the bug it fixes.** the v6 scalar is mostly a contrast meter, so on a cross-subject sweep it ranked *every* black hole above *every* lensed galaxy — a black-hole-picker wearing a quality costume (confirmed by experiment: the four black holes took ranks 1-4, the five galaxies the bottom five). The studio's per-subject normalization scores each candidate against others of its own subject, so the standout wormhole stops losing to a mediocre black hole.
- **new modules.** `starforge.selection` (pure, deterministic frontier + de-biased ranking) and `starforge.studio` (the HTML). `CollectionResult` now carries the full ranked sweep (`all_entries`) so the studio sees everything, not just the kept top-k. The manifest records the frontier ranking under `studio`.
- **determinism untouched.** the studio is a read-only observer: zero pixel change, the pixel golden and RNG-order lock are unchanged, every existing render is byte-identical to v6. semver 7.0.0.

deferred (a separate, pixel-changing decision): the dither / 16-bit floor and a blackbody spectral pass. those re-bless the golden; the studio does not. See ROADMAP.md.

## v6.0.0 - 2026-06-19

starforge grew two more subjects and a second way to judge them.

- **neutron-star subject.** a compact, limb-darkened hot surface with two magnetic-pole hotspots and twin lighthouse beams that sweep as the star spins. the sweep is periodic on `phase`, so the loop stays seamless. it reuses the single-center lensing to bend the background; all of its structure is drawn from a separate rng stream.
- **wormhole subject.** a strong throat lens (the singular-isothermal-sphere gather, pushed harder) pulls a distinct far-universe field into the mouth, ringed by a bright Einstein ring. no new physics, just the existing gather aimed at a different background.
- **studio curator.** a second deterministic, offline curator (`--curator studio`) that ranks for a clear, well-placed focal subject and real structure instead of raw contrast. the seam shipped in v4; this is the honest stepping stone toward a learned ranker without touching reproducibility.
- **cross-subject collection.** `--cross-subject` makes the `--batch` sweep cross subjects too and rank a mixed gallery. a single-subject sweep stays byte-identical to before.
- **determinism held.** the black-hole path is still byte-identical, the rng-order lock is green, and every new subject ships determinism, finiteness, and frame-stability tests. a new `test_rng_isolation` pins that no subject perturbs the locked genome. the pixel golden now covers all four subjects. semver 6.0.0, single-sourced from `starforge.__version__`.

still deferred: a timeline / merger mode (would break the seamless-loop identity) and a true binary-merger subject (needs two-center lensing / ray-tracing, out of the single-center architecture). See ROADMAP.md.

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
