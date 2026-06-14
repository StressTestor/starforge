# starforge lab

The problem with most procedural art demos is that the seed is usually just noise.

Starforge Lab v3 is a deterministic Python art machine where the seed drives the structure: black-hole position, disk tilt, banding, jet angle and asymmetry, horizon size, lensing strength, ring tightness, Doppler beaming, and palette temperature. It sweeps seeds and presets, scores the results with inspectable composition metrics, exports a curated collection, and renders a final poster plus animation/video assets.

## output

- `index.html` - local gallery for the finished release
- `starforge_poster.png` - high-resolution poster render
- `starforge.gif` - animated accretion disk preview
- `starforge.mp4` - cinematic loop, written through `ffmpeg`
- `starforge.webm` - browser-friendly WebM loop, written through `ffmpeg`
- `seed_gallery.png` - scored candidate seed sweep for the requested preset
- `collection_gallery.png` - ranked top-K collection across presets
- `starforge_contact_sheet.png` - sampled animation frames
- `manifest.json` - source seed, selected seed/preset, selected genome, score reasons, video status, dependency versions, and asset list

## run it

After install:

```bash
starforge \
  --output ../../outputs/starforge \
  --width 1600 \
  --height 2200 \
  --frames 60 \
  --seed 260613 \
  --preset neon-collapse \
  --seed-gallery 16 \
  --batch 30 \
  --top-k 9 \
  --supersample 2 \
  --video \
  --scale-preview
```

Without install:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m starforge.cli \
  --output ../../outputs/starforge \
  --width 1600 \
  --height 2200 \
  --frames 60 \
  --seed 260613 \
  --preset neon-collapse \
  --seed-gallery 16 \
  --batch 30 \
  --top-k 9 \
  --supersample 2 \
  --video \
  --scale-preview
```

## install it

```bash
python3 -m pip install -e ".[test]"
starforge --help
```

## presets

| preset | feel |
| --- | --- |
| `event-horizon` | classic gold-black gravity well |
| `neon-collapse` | magenta, cyan, and hot accretion streaks |
| `cold-singularity` | blue-white, colder and sharper |
| `solar-wound` | aggressive orange solar tear |
| `deep-field` | purple deep-space survey plate |

## scoring

The scorer is deterministic and inspectable. It combines tonal range, rule-of-thirds focal placement, focal balance, ring/center separation, and a busy-image penalty. Each selected collection entry records its score reasons in `manifest.json`.

## test it

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -p no:cacheprovider -v
```

## inspect a release

```bash
python3 tools/inspect_outputs.py ../../outputs/starforge
```

## tweak points

| knob | effect |
| --- | --- |
| `--seed` | starting point for deterministic seed and collection sweeps |
| `--preset` | requested preset for the focused seed gallery |
| `--seed-gallery` | number of candidates to score for the requested preset |
| `--batch` | number of seeds to sweep across all presets |
| `--top-k` | number of ranked collection entries to keep |
| `--supersample` | poster-only supersampling factor |
| `--width`, `--height` | poster dimensions |
| `--frames` | animation length |
| `--video` | writes MP4/WebM when `ffmpeg` is available |
| `--scale-preview` | keeps animation/video/contact sheet smaller while preserving poster resolution |

The selected genome is recorded in `manifest.json`, so a good render is reproducible rather than a lucky accident.

