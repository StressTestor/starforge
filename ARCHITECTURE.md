# starforge lab architecture

## project overview

Starforge Lab v7 is a deterministic procedural gravitational-lensing art generator. From a seed it builds a structural genome and renders one of four subjects: a `black-hole` (an accretion disk whose far side lenses over the shadow, with an emergent photon ring), a `lensed-galaxy` (a foreground elliptical that bends a background galaxy field into Einstein rings and arcs), a `neutron-star` (a compact hot surface with two magnetic-pole hotspots and twin lighthouse beams that sweep as the star spins), or a `wormhole` (a strong throat lens that gathers a distinct far-universe field into the mouth, ringed by an Einstein ring). It ranks candidates through a pluggable curator (`heuristic` or `studio`), emits a ranked collection (optionally cross-subject), writes an offline selection studio (`--studio`: a `studio.html` with a Pareto frontier and per-subject de-biased ranking that fixes the v6 scalar's cross-subject contrast bias), and packages a static HTML lab page with PNG/GIF/MP4/WebM assets.

The repository now also contains the first native macOS wrapper scaffold. The Swift app is a driver and viewer: it builds an argument vector, launches `python3 -m starforge.cli` as a subprocess, decodes the engine-owned `manifest.json`, and displays the written poster. It can fall back to the checkout's Python package for development, but the real bundle path is generated under `StarforgeLab/Resources`: BeeWare's relocatable `Python.xcframework`, a tiny `bin/python3` launcher, the upstream `engine/` copy, and a private `pysite/` with pinned NumPy/Pillow wheels.

## stack and dependencies

| dependency | use |
| --- | --- |
| Python 3.14 | local runtime |
| Python 3.12 | CI runtime |
| NumPy (pinned `==2.4.2`) | seeded genomes, coordinate fields, scoring, image math |
| Pillow (pinned `==12.1.0`) | PNG/GIF writing, bloom, typography, galleries |
| ffmpeg | optional MP4 and WebM export |
| pytest | regression tests |
| Swift 6 / SwiftPM | native macOS app scaffold and headless verification executable |
| SwiftUI + Observation | macOS window, controls, and render state |
| BeeWare Python-Apple-support 3.12-b9 | relocatable macOS `Python.xcframework` runtime for the app bundle |
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
├── Package.swift
├── script
│   └── build_and_run.sh
├── scripts
│   ├── parity_selftest.sh
│   └── vendor_python.sh
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
│   ├── selection.py
│   ├── studio.py
│   └── video.py
├── tests
│   ├── _genome_golden_v4.json
│   ├── _pixel_golden_v5.json
│   ├── test_cli.py
│   ├── test_coverage_gaps_c6.py
│   ├── test_curation.py
│   ├── test_genome_scoring_collection.py
│   ├── test_golden_pixels_v5.py
│   ├── test_inspect_outputs.py
│   ├── test_lensing_v4.py
│   ├── test_presets_gallery_video.py
│   ├── test_render_invariants_v4.py
│   ├── test_renderer.py
│   ├── test_rng_isolation_v5.py
│   ├── test_rng_order_lock_v5.py
│   ├── test_selection_v7.py
│   ├── test_studio_v7.py
│   ├── test_subject_pulsar_v6.py
│   ├── test_subject_v5.py
│   └── test_subject_wormhole_v6.py
└── tools
    ├── inspect_outputs.py
    └── regen_pixel_golden.py
├── StarforgeLab
│   ├── App
│   │   ├── StarforgeLab.entitlements
│   │   └── Sources
│   │       └── StarforgeLabApp.swift
│   ├── Checks
│   │   ├── Fixtures
│   │   │   ├── full_manifest.json
│   │   │   ├── plain_manifest.json
│   │   │   └── studio_curator_manifest.json
│   │   └── Sources
│   │       └── main.swift
│   ├── Parity
│   │   └── Sources
│   │       └── main.swift
│   └── Packages
│       ├── StarforgeCore
│       │   └── Sources
│       │       ├── Manifest.swift
│       │       └── RenderRequest.swift
│       ├── StarforgeEngine
│       │   └── Sources
│       │       ├── ArgumentBuilder.swift
│       │       ├── EngineError.swift
│       │       ├── EngineLocator.swift
│       │       ├── RenderEvent.swift
│       │       └── RenderService.swift
│       └── StarforgePersistence
│           └── Sources
│               ├── HistoryStore.swift
│               └── OutputLayout.swift
│   ├── Resources
│   │   └── README.md
│   └── Support
│       └── python_launcher.c
```

## key patterns

- `Genome.from_seed(seed, preset, subject)` is the source of macro structure. The renderer should not add new hardcoded composition constants without routing them through the genome.
- Subjects (`SUBJECT_NAMES` in `genome.py`: `black-hole`, `lensed-galaxy`, `neutron-star`, `wormhole`) are the seam for render variety. `subject` is a genome field (not RenderConfig-only, not the curator); `StarforgeRenderer.__init__` dispatches via a builder table (`_build_lensing` / `_build_galaxy` / `_build_pulsar` / `_build_wormhole`, default = black-hole) and `_render_frame` dispatches via a renderer table (`_render_blackhole_frame` / `_render_galaxy_frame` / `_render_pulsar_frame` / `_render_wormhole_frame`). The black-hole path is byte-identical to v4.
- Every non-black-hole subject draws its structure from a SEPARATE seeded rng stream (`_GALAXY_RNG_STREAM`, `_PULSAR_RNG_STREAM`, `_WORMHOLE_RNG_STREAM`) keyed `default_rng([seed, salt])`, so it never advances the locked black-hole genome order and adds no genome fields. `test_rng_isolation_v5` pins that every subject yields byte-identical RNG-derived genome fields. New subjects MUST follow this pattern (separate stream, no inserted genome draws).
- `neutron-star` is a moving subject (the beam sweeps once per loop), so it carries its own frame-stability test at the real frame count with a smooth-motion bar plus an explicit loop-seam (wrap-around) check, not the near-static galaxy's 0.95. `wormhole`'s mouth is frame-invariant, so it holds galaxy-grade 0.95.
- Curation has two members in `_CURATORS`: `heuristic` (contrast-led) and `studio` (rewards a clear focal subject + structure over raw contrast). Both are pure, offline, deterministic; a learned/CLIP ranker is the intended next drop-in. `collection.build_collection(..., subjects=[...])` sweeps multiple subjects (CLI `--cross-subject`); a single-subject sweep is byte-identical to the original preset-only sweep.
- Selection is a THIRD layer, read-only over rendered candidates and separate from both generation and curation. `starforge.selection` (pure, deterministic) computes the Pareto frontier over the metric vector and a per-subject min-max normalized score — because the v6 scalar is a contrast meter (`tonal_range`-dominated) that buckets a cross-subject sweep by subject (all black holes outrank all galaxies regardless of quality). Per-subject normalization scores each candidate against others of its own subject; the frontier surfaces the non-dominated set no scalar can. `starforge.studio` renders a self-contained `studio.html` (embedded base64 thumbnails + client-side sort/filter/pin/export). `--studio` writes it from `CollectionResult.all_entries` (the FULL ranked sweep, not just top-k) and records the frontier ranking in the manifest under `studio`. Zero pixel change, zero RNG — determinism is untouched, so the pixel golden does not move.
- The black-hole genome draw order is LOCKED. `subject` does not consume the RNG, and any new genome field must be drawn AFTER the existing sequence. `test_rng_order_lock_v5` pins it with a golden so a re-roll is caught immediately. `test_rng_isolation_v5` additionally pins that every `subject` yields byte-identical RNG-derived genome fields, so a new subject can never perturb the locked draw order.
- Two regression nets guard byte-identity at different layers. `test_rng_order_lock_v5` pins the genome *macro params* (`tests/_genome_golden_v4.json`); `test_golden_pixels_v5` pins the rendered *pixels* (`tests/_pixel_golden_v5.json`, sha256 of small title-free renders for every subject). Pixel hashes are stored per-environment (platform/numpy/Pillow affect the low bits) and the test skips cleanly when the running environment has no committed golden, so it never reds CI on an unseen platform. Regenerate with `tools/regen_pixel_golden.py` after an intended visual change.
- The package version is single-sourced as `starforge.__version__`; the CLI manifest reads it, and `test_cli` asserts it matches `pyproject.toml` so the two cannot drift.
- `StarforgeCore.Manifest` mirrors `manifest.json` with `Codable` and `convertFromSnakeCase`; `SeedCandidate.score` intentionally re-encodes as JSON `null` so the plain-render fallback round-trips without dropping the key.
- `StarforgeCore.RenderRequest.validated()` mirrors the Python bounds (`width`/`height` 64...5000, `frames` 2...180, `supersample` 1...3, preset/subject/curator membership) before the app shells out.
- `StarforgeEngine.ArgumentBuilder` returns an argv array (`-m starforge.cli`, never a shell string). `RenderService` uses `EngineLocator`, which prefers bundled resources (`STARFORGE_BUNDLE_RESOURCES` or `Bundle.main.resourceURL`) before falling back to the checkout Python path.
- `scripts/vendor_python.sh` regenerates the local runtime payload. The binary payload is ignored by git; the script downloads BeeWare Python-Apple-support 3.12-b9, compiles a universal launcher, downloads pinned architecture-specific wheels, copies the unmodified upstream engine, and writes `StarforgeLab/Resources/BUILDINFO`.
- `StarforgeLabParity` is the §9.1 parity harness: render once through `RenderService`, render once through the same bundled CLI, then compare poster SHA-256 and `selected_genome`.
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

| variable | purpose |
| --- | --- |
| `PYTHONPATH` | set by the macOS development runner/checks so `python3 -m starforge.cli` imports this checkout |
| `PYTHONDONTWRITEBYTECODE` | avoids writing `__pycache__` during deterministic checks and app-driven renders |
| `PYTHONHASHSEED` | set by the Swift engine locator as a belt-and-suspenders deterministic default |
| `STARFORGE_ENGINE_ROOT` | optional Swift app development override for the checkout that contains `starforge/cli.py` |
| `STARFORGE_BUNDLE_RESOURCES` | optional override pointing `EngineLocator` at generated app resources for parity and local bundle tests |

## deployment and infrastructure

GitHub Actions runs tests and a smoke render on push and pull request.

## external services and integrations

| integration | purpose |
| --- | --- |
| `ffmpeg` binary | optional MP4/WebM loop export when `--video` is passed |
| BeeWare Python-Apple-support | source for the generated app `Python.xcframework`; upstream docs describe the macOS package as relocatable and macOS as x86_64/arm64-capable |

## gotchas

- With `--batch`, the final poster uses the top collection entry, so `selected_seed` and `selected_preset` may differ from the requested seed/preset.
- `seed_gallery.png` is a focused sweep for the requested preset; `collection_gallery.png` is the broader cross-preset artifact.
- The disk fold samples the inclined disk *ellipse* (vertical squash = `disk_thickness`), not a circle. Sampling a circle at the disk radius lands in empty space above the squashed disk and the arc comes out black.
- The emergent ring LUT is zero inside the photon sphere; otherwise `-ln(b/b_ph - 1)` blows up and fills the captured shadow with light.
- The poster can be high-resolution; animation and video generation are intentionally scaled by `--scale-preview`.
- Pillow font availability differs by machine. The renderer uses macOS fonts when available and falls back to Pillow defaults.
- `copy_project_files` refuses to run when `--output` resolves onto the running source tree (it would `rmtree` the live `starforge/`, `tests/`, `tools/`, `.github/`). Point `--output` at a dedicated release directory. The function takes an optional `root` so the guard is testable without touching the real repo.
- `tools/inspect_outputs.py` and `index.html` are upstream v7.0.1 behavior: optional assets are validated and rendered from `manifest.assets`, so plain releases do not require or reference `seed_gallery.png`.
- `--studio --curator studio` is valid in v7.0.1. The selector and studio bars are data-driven over the curator's reason keys; `StarforgeLab/Checks/Fixtures/studio_curator_manifest.json` pins this schema path.
- PyPI does not publish universal2 `numpy==2.4.2` / `pillow==12.1.0` wheels for CPython 3.12. `scripts/vendor_python.sh` currently vendors the pinned wheel for the host architecture (arm64 here). The launcher and Python framework are universal, but the wheel payload still needs a wheel-merge/build step before M5 universal2 can be marked green.
- The current Swift app scaffold is not the final signed product. It does not yet have app icons, WKWebView studio bridging, notarization scripts, Developer ID signing, or an Xcode project.

## commands

| command | purpose |
| --- | --- |
| `python3 -m pip install -e ".[test]"` | install package and test extras |
| `starforge --output ../../outputs/starforge --width 1600 --height 2200 --frames 48 --seed 260613 --preset neon-collapse --batch 10 --top-k 6 --supersample 2 --video --scale-preview` | generate the black-hole release after install |
| `starforge --output ../../outputs/starforge-galaxy --seed 323965 --preset deep-field --subject lensed-galaxy --batch 10 --top-k 6 --supersample 2 --video --scale-preview` | generate a lensed-galaxy release |
| `starforge --output ../../outputs/starforge-pulsar --seed 260613 --preset cold-singularity --subject neutron-star --batch 10 --top-k 6` | generate a neutron-star release (`--subject wormhole` for a wormhole) |
| `starforge --output ../../outputs/starforge-mixed --seed 260613 --batch 12 --top-k 6 --cross-subject --curator studio` | sweep every subject and rank a mixed collection with the studio curator |
| `starforge --output ../../outputs/starforge-studio --seed 260613 --batch 16 --cross-subject --studio` | write `studio.html` — the offline frontier + de-biased compare grid over the whole sweep |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -p no:cacheprovider -v` | run tests without install |
| `python3 tools/inspect_outputs.py ../../outputs/starforge` | inspect generated release |
| `PYTHONPATH=. python3 tools/regen_pixel_golden.py` | regenerate the per-environment pixel golden after an intended visual change |
| `swift build` | build the SwiftPM macOS app scaffold and support modules |
| `swift run StarforgeLabChecks` | run headless Swift schema and argument-builder checks against real CLI-generated manifests |
| `./scripts/vendor_python.sh` | regenerate the local bundled Python 3.12 runtime, app launcher, pinned wheels, and upstream engine copy |
| `./scripts/parity_selftest.sh` | run the bundled-interpreter app-vs-CLI parity check |
| `./script/build_and_run.sh` | build and launch the SwiftPM-staged macOS app bundle |
| `./script/build_and_run.sh --verify` | build, stage `StarforgeLab.app`, copy generated resources when present, launch the app executable, and verify the process exists |

## last-updated

2026-06-20
