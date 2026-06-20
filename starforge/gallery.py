from __future__ import annotations

from dataclasses import asdict, dataclass, field
from html import escape
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from starforge.config import RenderConfig
from starforge.curation import Curator, get_curator
from starforge.genome import Genome


@dataclass(frozen=True)
class SeedCandidate:
    seed: int
    score: float
    reasons: dict[str, float] = field(default_factory=dict)

    def to_manifest(self) -> dict[str, object]:
        data = asdict(self)
        data["score"] = round(float(self.score), 4)
        data["reasons"] = {key: round(value, 4) for key, value in self.reasons.items()}
        return data


@dataclass(frozen=True)
class SeedGalleryResult:
    selected_seed: int
    candidates: list[SeedCandidate]
    image: Image.Image


def candidate_seeds(base_seed: int, count: int) -> list[int]:
    if count < 1:
        raise ValueError("seed gallery count must be at least 1")
    return [base_seed + index * 7919 for index in range(count)]


def build_seed_gallery(
    config: RenderConfig, *, count: int, thumb_width: int = 220, curator: Curator | None = None
) -> SeedGalleryResult:
    from starforge.renderer import StarforgeRenderer

    if curator is None:
        curator = get_curator()
    seeds = candidate_seeds(config.seed, count)
    thumb_height = max(64, round(thumb_width * config.height / config.width))
    gutter = 12
    label_height = 46
    columns = min(4, count)
    rows = int(np.ceil(count / columns))
    sheet = Image.new(
        "RGB",
        (columns * thumb_width + (columns + 1) * gutter, rows * thumb_height + (rows + 1) * gutter + label_height),
        (4, 5, 16),
    )
    draw = ImageDraw.Draw(sheet)
    font = _font(16)
    small = _font(12)
    draw.text((gutter, 13), f"seed sweep // {config.preset}", font=font, fill=(220, 236, 245))

    candidates: list[SeedCandidate] = []
    thumbnails: list[Image.Image] = []
    for seed in seeds:
        thumb_config = RenderConfig(
            width=thumb_width,
            height=thumb_height,
            seed=seed,
            frames=max(2, min(config.frames, 8)),
            preset=config.preset,
            subject=config.subject,
        )
        thumb = StarforgeRenderer(thumb_config).render_poster(include_title=False)
        score = curator.score(thumb, Genome.from_seed(seed, config.preset, config.subject))
        candidates.append(SeedCandidate(seed=seed, score=score.total, reasons=score.reasons))
        thumbnails.append(thumb)

    selected = max(candidates, key=lambda candidate: candidate.score)
    for index, (candidate, thumb) in enumerate(zip(candidates, thumbnails, strict=True)):
        row, col = divmod(index, columns)
        x = gutter + col * (thumb_width + gutter)
        y = label_height + gutter + row * (thumb_height + gutter)
        sheet.paste(thumb, (x, y))
        outline = (255, 156, 74) if candidate.seed == selected.seed else (78, 136, 158)
        draw.rectangle((x, y, x + thumb_width - 1, y + thumb_height - 1), outline=outline, width=2)
        draw.text((x + 7, y + 7), str(candidate.seed), font=small, fill=(235, 244, 247))
        draw.text((x + 7, y + 23), f"{candidate.score:.1f}", font=small, fill=(180, 218, 226))

    return SeedGalleryResult(selected_seed=selected.seed, candidates=candidates, image=sheet)


def write_lab_page(output: Path, manifest: dict[str, object]) -> Path:
    path = output / "index.html"
    assets = set(manifest.get("assets", []))
    video_markup = ""
    if "starforge.mp4" in assets:
        video_markup = """
        <section class="panel wide">
          <h2>cinematic loop</h2>
          <video src="starforge.mp4" controls autoplay muted loop playsinline></video>
        </section>
        """
    collection_markup = ""
    if "collection_gallery.png" in assets:
        collection_markup = """
      <section class="panel wide">
        <h2>ranked collection</h2>
        <img src="collection_gallery.png" alt="Ranked top collection">
      </section>
        """
    seed_gallery_markup = ""
    if "seed_gallery.png" in assets:
        seed_gallery_markup = """
      <section class="panel">
        <h2>seed sweep</h2>
        <img src="seed_gallery.png" alt="Seed gallery">
      </section>
        """
    studio_markup = ""
    if "studio.html" in assets:
        studio_markup = """
      <section class="panel wide">
        <h2>selection studio</h2>
        <p style="margin:0;color:var(--muted)"><a href="studio.html" style="color:var(--accent);font-weight:700">open the studio &rarr;</a> &mdash; compare the whole sweep on the Pareto frontier and a per-subject de-biased ranking, then pin your picks.</p>
      </section>
        """

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Starforge Lab</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #050713;
      --panel: #101522;
      --line: #344a5f;
      --text: #e9f6fb;
      --muted: #9ac7d4;
      --accent: #ff8e48;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at 50% 18%, #18243b 0, var(--bg) 48%, #02030a 100%);
      color: var(--text);
      font: 15px/1.45 -apple-system, BlinkMacSystemFont, "Avenir Next", Inter, sans-serif;
    }}
    main {{ width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0 44px; }}
    header {{ display: grid; grid-template-columns: 1fr auto; gap: 18px; align-items: end; margin-bottom: 22px; }}
    h1, h2 {{ margin: 0; letter-spacing: 0; }}
    h1 {{ font-size: clamp(36px, 7vw, 86px); line-height: 0.9; }}
    h2 {{ font-size: 17px; color: var(--muted); font-weight: 700; }}
    .meta {{ display: grid; grid-template-columns: repeat(2, minmax(120px, 1fr)); gap: 8px 18px; color: var(--muted); }}
    .meta b {{ color: var(--text); }}
    .grid {{ display: grid; grid-template-columns: minmax(260px, 0.86fr) minmax(300px, 1fr); gap: 18px; align-items: start; }}
    .panel {{ border: 1px solid var(--line); background: color-mix(in srgb, var(--panel) 82%, transparent); border-radius: 8px; padding: 14px; }}
    .wide {{ grid-column: 1 / -1; }}
    img, video {{ display: block; width: 100%; border-radius: 6px; background: #02030a; }}
    .poster {{ max-height: 84vh; object-fit: contain; }}
    code {{ display: block; white-space: pre-wrap; color: #d7f5ff; background: #050814; border: 1px solid #22384a; border-radius: 6px; padding: 12px; }}
    @media (max-width: 820px) {{
      header, .grid {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 44px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Starforge Lab</h1>
        <h2>procedural gravity engine</h2>
      </div>
      <div class="meta">
        <span>preset <b>{escape(str(manifest.get("selected_preset", manifest["preset"])))}</b></span>
        <span>selected seed <b>{manifest["selected_seed"]}</b></span>
        <span>frames <b>{manifest["frames"]}</b></span>
        <span>poster <b>{manifest["width"]}x{manifest["height"]}</b></span>
      </div>
    </header>
    <div class="grid">
      <section class="panel">
        <img class="poster" src="starforge_poster.png" alt="Starforge poster">
      </section>
      {seed_gallery_markup}
      {collection_markup}
      {studio_markup}
      <section class="panel">
        <h2>animation samples</h2>
        <img src="starforge_contact_sheet.png" alt="Animation contact sheet">
      </section>
      <section class="panel">
        <h2>gif loop</h2>
        <img src="starforge.gif" alt="Animated Starforge GIF">
      </section>
      {video_markup}
      <section class="panel wide">
        <h2>rerun command</h2>
        <code>starforge --output ../../outputs/starforge --width {manifest["width"]} --height {manifest["height"]} --frames {manifest["frames"]} --seed {manifest["seed"]} --preset {escape(str(manifest["preset"]))} --seed-gallery {len(manifest["seed_candidates"])} --batch {manifest.get("batch", 0)} --top-k {manifest.get("top_k", 0)} --supersample {manifest.get("supersample", 1)} --video --scale-preview</code>
      </section>
    </div>
  </main>
</body>
</html>
"""
    path.write_text(html)
    return path


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Avenir Next.ttc", size=size)
    except OSError:
        return ImageFont.load_default(size=size)
