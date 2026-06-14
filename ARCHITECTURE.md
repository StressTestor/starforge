# starforge lab architecture

## project overview

Starforge Lab v5 is a deterministic procedural gravitational-lensing art generator. From a seed it builds a structural genome and renders one of two subjects: a `black-hole` (an accretion disk whose far side lenses over the shadow, with an emergent photon ring) or a `lensed-galaxy` (a foreground elliptical that bends a background galaxy field into Einstein rings and arcs). It ranks candidates through a pluggable curator, emits a ranked collection, and packages a static HTML lab page with PNG/GIF/MP4/WebM assets.

## stack and dependencies

| dependency | use |
| --- | --- |
| Python 3.14 | local runtime |
| Python 3.12 | CI runtime |
| NumPy | seeded genomes, coordinate fields, scoring, image math |
| Pillow | PNG/GIF writing, bloom, typography, galleries |
| ffmpeg | optional MP4 and WebM export |
| pytest | regression tests |
| GitHub Actions | CI test and smoke render |

## directory structure

```text
.
├── .github
│   └── workflows
│       └── ci.yml
├── ARCHITECTURE.md
├── README.md
├── pyproject.toml
├── starforge
│   ├── __init__.py
│   ├── cli.py
│   ├── collection.py
│   ├── config.py
│   ├── curation.py
│   ├── gallery.py
│   ├── genome.py
│   ├── lensing.py
│   ├── palette.py
│   ├── presets.py
│   ├── renderer.py
│   ├── scoring.py
│   └── video.py
├── tests
│   ├── _genome_golden_v4.json
│   ├── test_cli.py
│   ├── test_curation.py
│   ├── test_genome_scoring_collection.py
│   ├── test_lensing_v4.py
│   ├── test_presets_gallery_video.py
│   ├── test_render_invariants_v4.py
│   ├── test_renderer.py
│   ├── test_rng_order_lock_v5.py
│   └── test_subject_v5.py
└── tools
    └── inspect_outputs.py
```

## key patterns

- `Genome.from_seed(seed, preset, subject)` is the source of macro structure. The renderer should not add new hardcoded composition constants without routing them through the genome.
- Subjects (`SUBJECT_NAMES` in `genome.py`) are the seam for render variety. `subject` is a genome field (not RenderConfig-only, not the curator); `StarforgeRenderer.__init__` dispatches to `_build_lensing` / `_build_galaxy` and `_render_frame` dispatches to `_render_blackhole_frame` / `_render_galaxy_frame`. The black-hole path is byte-identical to v4.
- The black-hole genome draw order is LOCKED. `subject` does not consume the RNG, and any new genome field must be drawn AFTER the existing sequence. `test_rng_order_lock_v5` pins it with a golden so a re-roll is caught immediately.
- `lensed-galaxy` reuses the single-center lensing: `build_einstein_lens_map` is a singular-isothermal-sphere lens (`beta = theta - theta_E * theta_hat`) that gathers a deterministic background galaxy field built from a SEPARATE rng (so it never touches the black-hole draw order).
- `StarforgeRenderer` returns Pillow images and does not write files. Generation is the single source of truth and stays byte-identical for a given (seed, preset, size).
- Disk lensing lives in `starforge.lensing`: `build_deflection_lut` tabulates the bending angle (strong-deflection log divergence at the photon sphere, blended to a weak-field tail); `sample_emergent_ring` gathers the photon ring from that divergence; `build_disk_fold_map` precomputes the gravitational fold that lays the disk's far side as an arc over the shadow. All frame-invariant, built once in `StarforgeRenderer.__init__`.
- `disk_emission(r, theta, phase)` is the pure disk texture; the renderer feeds it the flat inclined-disk coordinates for the primary image and re-gathers a smoothed copy through the fold for the secondary arc.
- Curation is split from generation. `starforge.curation` exposes a `Curator` protocol and a default `HeuristicCurator`; the renderer never imports it. A learned/CLIP curator can be added to `_CURATORS` without touching reproducibility, since the curator only ranks.
- `starforge.scoring` keeps scoring deterministic and inspectable (tonal range, thirds, focal balance, busy penalty, ring separation, colour harmony). No neural aesthetic model, no network dependency.
- The background star field uses bilinear sampling; image +y is DOWN, so the over-the-shadow "up" vector is `-sin(theta)`.
- Poster supersampling is poster-only. Animation/video stay preview-scaled when `--scale-preview` is used.
- Batch mode sweeps seeds across all presets and lets the ranked collection choose the final selected seed and preset.

## database schema

None.

## environment variables

None.

## deployment and infrastructure

GitHub Actions runs tests and a smoke render on push and pull request.

## external services and integrations

| integration | purpose |
| --- | --- |
| `ffmpeg` binary | optional MP4/WebM loop export when `--video` is passed |

## gotchas

- With `--batch`, the final poster uses the top collection entry, so `selected_seed` and `selected_preset` may differ from the requested seed/preset.
- `seed_gallery.png` is a focused sweep for the requested preset; `collection_gallery.png` is the broader cross-preset artifact.
- The disk fold samples the inclined disk *ellipse* (vertical squash = `disk_thickness`), not a circle. Sampling a circle at the disk radius lands in empty space above the squashed disk and the arc comes out black.
- The emergent ring LUT is zero inside the photon sphere; otherwise `-ln(b/b_ph - 1)` blows up and fills the captured shadow with light.
- The poster can be high-resolution; animation and video generation are intentionally scaled by `--scale-preview`.
- Pillow font availability differs by machine. The renderer uses macOS fonts when available and falls back to Pillow defaults.

## commands

| command | purpose |
| --- | --- |
| `python3 -m pip install -e ".[test]"` | install package and test extras |
| `starforge --output ../../outputs/starforge --width 1600 --height 2200 --frames 48 --seed 260613 --preset neon-collapse --batch 10 --top-k 6 --supersample 2 --video --scale-preview` | generate the black-hole release after install |
| `starforge --output ../../outputs/starforge-galaxy --seed 323965 --preset deep-field --subject lensed-galaxy --batch 10 --top-k 6 --supersample 2 --video --scale-preview` | generate a lensed-galaxy release |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -p no:cacheprovider -v` | run tests without install |
| `python3 tools/inspect_outputs.py ../../outputs/starforge` | inspect generated release |

## last-updated

2026-06-14

