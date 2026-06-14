# starforge lab architecture

## project overview

Starforge Lab v3 is a deterministic procedural visual generator. It creates a structural black-hole genome from the seed, renders a poster and animation, scores candidates with analytic composition metrics, emits a ranked collection, and packages a static HTML lab page with PNG/GIF/MP4/WebM assets.

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
│   ├── gallery.py
│   ├── genome.py
│   ├── lensing.py
│   ├── palette.py
│   ├── presets.py
│   ├── renderer.py
│   ├── scoring.py
│   └── video.py
├── tests
│   ├── test_cli.py
│   ├── test_genome_scoring_collection.py
│   ├── test_presets_gallery_video.py
│   └── test_renderer.py
└── tools
    └── inspect_outputs.py
```

## key patterns

- `Genome.from_seed(seed, preset)` is the source of macro structure. The renderer should not add new hardcoded composition constants without routing them through the genome.
- `StarforgeRenderer` returns Pillow images and does not write files.
- `starforge.cli` owns output orchestration, manifest writing, lab-page writing, video export, and copied release files.
- `starforge.scoring` keeps scoring deterministic and inspectable. No neural aesthetic model, no network dependency.
- Lensing uses bilinear sampling to avoid nearest-neighbor ring artifacts.
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
- The poster can be high-resolution; animation and video generation are intentionally scaled by `--scale-preview`.
- Pillow font availability differs by machine. The renderer uses macOS fonts when available and falls back to Pillow defaults.

## commands

| command | purpose |
| --- | --- |
| `python3 -m pip install -e ".[test]"` | install package and test extras |
| `starforge --output ../../outputs/starforge --width 1600 --height 2200 --frames 60 --seed 260613 --preset neon-collapse --seed-gallery 16 --batch 30 --top-k 9 --supersample 2 --video --scale-preview` | generate v3 release after install |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -p no:cacheprovider -v` | run tests without install |
| `python3 tools/inspect_outputs.py ../../outputs/starforge` | inspect generated release |

## last-updated

2026-06-13

