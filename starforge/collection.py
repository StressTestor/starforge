from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from starforge.config import RenderConfig
from starforge.curation import Curator, get_curator
from starforge.genome import Genome
from starforge.presets import PRESET_NAMES
from starforge.scoring import ScoreResult


@dataclass(frozen=True)
class CollectionEntry:
    seed: int
    preset: str
    score: ScoreResult
    genome: Genome
    image: Image.Image

    def to_manifest(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "preset": self.preset,
            "score": self.score.to_manifest(),
            "genome": self.genome.to_manifest(),
        }


@dataclass(frozen=True)
class CollectionResult:
    entries: list[CollectionEntry]
    image: Image.Image


def build_collection(
    config: RenderConfig,
    *,
    batch_count: int,
    top_k: int,
    thumb_width: int = 220,
    curator: Curator | None = None,
    subjects: list[str] | None = None,
) -> CollectionResult:
    if batch_count < 1:
        raise ValueError("batch count must be at least 1")
    if top_k < 1:
        raise ValueError("top-k must be at least 1")

    from starforge.renderer import StarforgeRenderer

    if curator is None:
        curator = get_curator()
    # default is the single-subject sweep. With one subject the (subject, preset,
    # seed) sequence below is byte-identical to the original preset-only sweep, so
    # existing single-subject collections are unchanged. A multi-subject list
    # interleaves subjects (preset advances once per full subject cycle) to rank a
    # mixed gallery.
    subject_cycle = subjects if subjects else [config.subject]
    thumb_height = max(64, round(thumb_width * config.height / config.width))
    entries: list[CollectionEntry] = []

    for index in range(batch_count):
        subject = subject_cycle[index % len(subject_cycle)]
        preset = PRESET_NAMES[(index // len(subject_cycle)) % len(PRESET_NAMES)]
        seed = config.seed + index * 7919
        thumb_config = RenderConfig(
            width=thumb_width,
            height=thumb_height,
            seed=seed,
            frames=max(2, min(config.frames, 8)),
            preset=preset,
            subject=subject,
        )
        image = StarforgeRenderer(thumb_config).render_poster(include_title=False)
        genome = Genome.from_seed(seed, preset, subject)
        score = curator.score(image, genome)
        entries.append(CollectionEntry(seed=seed, preset=preset, score=score, genome=genome, image=image))

    top_entries = sorted(entries, key=lambda entry: entry.score.total, reverse=True)[:top_k]
    return CollectionResult(entries=top_entries, image=_contact_sheet(top_entries, thumb_width, thumb_height))


def _contact_sheet(entries: list[CollectionEntry], thumb_width: int, thumb_height: int) -> Image.Image:
    gutter = 12
    label_height = 52
    columns = min(3, len(entries))
    rows = int(np.ceil(len(entries) / columns))
    sheet = Image.new(
        "RGB",
        (columns * thumb_width + (columns + 1) * gutter, rows * thumb_height + (rows + 1) * gutter + label_height),
        (5, 6, 18),
    )
    draw = ImageDraw.Draw(sheet)
    font = _font(16)
    small = _font(11)
    draw.text((gutter, 15), "ranked collection // top structural candidates", font=font, fill=(220, 236, 245))

    for index, entry in enumerate(entries):
        row, col = divmod(index, columns)
        x = gutter + col * (thumb_width + gutter)
        y = label_height + gutter + row * (thumb_height + gutter)
        sheet.paste(entry.image, (x, y))
        draw.rectangle((x, y, x + thumb_width - 1, y + thumb_height - 1), outline=(255, 156, 74), width=2)
        draw.text((x + 7, y + 7), f"#{index + 1} {entry.seed}", font=small, fill=(240, 246, 248))
        # show the subject too, so a cross-subject ranked gallery is readable
        draw.text((x + 7, y + 21), f"{entry.genome.subject} // {entry.preset}", font=small, fill=(184, 222, 230))
        draw.text((x + 7, y + 35), f"{entry.score.total:.1f}", font=small, fill=(255, 198, 120))

    return sheet


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Avenir Next.ttc", size=size)
    except OSError:
        return ImageFont.load_default(size=size)

