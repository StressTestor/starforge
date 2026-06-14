from __future__ import annotations

import argparse
import json
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from starforge.collection import CollectionResult, build_collection
from starforge.config import RenderConfig
from starforge.curation import get_curator
from starforge.gallery import SeedGalleryResult, build_seed_gallery, write_lab_page
from starforge.genome import SUBJECT_NAMES, Genome
from starforge.presets import PRESET_NAMES
from starforge.renderer import StarforgeRenderer
from starforge.video import export_videos


BASE_ASSETS = ["starforge_poster.png", "starforge.gif", "starforge_contact_sheet.png"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the Starforge black-hole poster and animation.")
    parser.add_argument("--output", type=Path, required=True, help="Directory for generated assets.")
    parser.add_argument("--width", type=int, default=1600, help="Poster width in pixels.")
    parser.add_argument("--height", type=int, default=2200, help="Poster height in pixels.")
    parser.add_argument("--frames", type=int, default=42, help="Animation frame count.")
    parser.add_argument("--seed", type=int, default=260613, help="Deterministic render seed.")
    parser.add_argument("--preset", choices=PRESET_NAMES, default="neon-collapse", help="Named visual preset.")
    parser.add_argument("--subject", choices=SUBJECT_NAMES, default="black-hole", help="Rendered subject (black-hole or lensed-galaxy).")
    parser.add_argument("--seed-gallery", type=int, default=0, help="Render this many candidate seeds and select the best.")
    parser.add_argument("--batch", type=int, default=0, help="Sweep this many seeds across all presets for a ranked collection.")
    parser.add_argument("--top-k", type=int, default=0, help="Keep this many ranked collection entries.")
    parser.add_argument("--curator", default="heuristic", help="Curator that ranks candidates (default: heuristic).")
    parser.add_argument("--supersample", type=int, default=1, help="Poster supersampling factor, 1-3.")
    parser.add_argument("--video", action="store_true", help="Export MP4 and WebM loops with ffmpeg when available.")
    parser.add_argument(
        "--scale-preview",
        action="store_true",
        help="Render GIF and contact sheet at preview scale while keeping the poster full size.",
    )
    args = parser.parse_args(argv)

    output = args.output
    output.mkdir(parents=True, exist_ok=True)

    curator = get_curator(args.curator)

    seed_gallery: SeedGalleryResult | None = None
    selected_seed = args.seed
    selected_preset = args.preset
    if args.seed_gallery:
        gallery_config = RenderConfig(width=320, height=440, seed=args.seed, frames=min(args.frames, 8), preset=args.preset, subject=args.subject)
        seed_gallery = build_seed_gallery(gallery_config, count=args.seed_gallery, thumb_width=220, curator=curator)
        selected_seed = seed_gallery.selected_seed
        seed_gallery.image.save(output / "seed_gallery.png", optimize=True)

    collection: CollectionResult | None = None
    top_k = args.top_k or min(9, args.batch or 0)
    if args.batch:
        collection_config = RenderConfig(width=320, height=440, seed=args.seed, frames=min(args.frames, 8), preset=args.preset, subject=args.subject)
        collection = build_collection(collection_config, batch_count=args.batch, top_k=top_k, thumb_width=220, curator=curator)
        collection.image.save(output / "collection_gallery.png", optimize=True)
        winner = collection.entries[0]
        selected_seed = winner.seed
        selected_preset = winner.preset

    poster_config = RenderConfig(
        width=args.width,
        height=args.height,
        seed=selected_seed,
        frames=args.frames,
        preset=selected_preset,
        subject=args.subject,
        supersample=args.supersample,
    )
    poster = StarforgeRenderer(poster_config).render_poster()
    poster_path = output / "starforge_poster.png"
    poster.save(poster_path, optimize=True)

    anim_width, anim_height = preview_dimensions(args.width, args.height, args.scale_preview)
    animation_config = RenderConfig(width=anim_width, height=anim_height, seed=selected_seed, frames=args.frames, preset=selected_preset, subject=args.subject)
    frames = StarforgeRenderer(animation_config).render_animation_frames()

    gif_path = output / "starforge.gif"
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=70,
        loop=0,
        optimize=True,
    )

    contact_path = output / "starforge_contact_sheet.png"
    contact = make_contact_sheet(frames, seed=selected_seed, preset=selected_preset)
    contact.save(contact_path, optimize=True)

    video_status = {"mp4": "not requested", "webm": "not requested"}
    if args.video:
        video_status = export_videos(frames, output, fps=24)

    assets = list(BASE_ASSETS)
    if seed_gallery is not None:
        assets.append("seed_gallery.png")
    if collection is not None:
        assets.append("collection_gallery.png")
    if video_status.get("mp4") == "written":
        assets.append("starforge.mp4")
    if video_status.get("webm") == "written":
        assets.append("starforge.webm")
    assets.append("index.html")

    seed_candidates = (
        [candidate.to_manifest() for candidate in seed_gallery.candidates]
        if seed_gallery is not None
        else [{"seed": selected_seed, "score": None}]
    )
    manifest = {
        "project": "starforge-lab",
        "version": "5.0.0",
        "subject": args.subject,
        "seed": args.seed,
        "selected_seed": selected_seed,
        "preset": args.preset,
        "selected_preset": selected_preset,
        "selected_genome": Genome.from_seed(selected_seed, selected_preset, args.subject).to_manifest(),
        "width": args.width,
        "height": args.height,
        "frames": args.frames,
        "supersample": args.supersample,
        "preview_width": anim_width,
        "preview_height": anim_height,
        "seed_candidates": seed_candidates,
        "collection": [entry.to_manifest() for entry in collection.entries] if collection is not None else [],
        "batch": args.batch,
        "top_k": top_k,
        "curator": args.curator,
        "video": video_status,
        "assets": assets,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "dependencies": {
            "numpy": np.__version__,
            "pillow": Image.__version__,
            "ffmpeg": shutil.which("ffmpeg") or "not found",
        },
    }

    write_lab_page(output, manifest)
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    copy_project_files(output)
    print(f"wrote Starforge release to {output}")
    return 0


def preview_dimensions(width: int, height: int, scale_preview: bool) -> tuple[int, int]:
    if not scale_preview:
        return width, height

    max_side = 900
    longest = max(width, height)
    if longest <= max_side:
        return width, height

    scale = max_side / longest
    return max(64, int(round(width * scale))), max(64, int(round(height * scale)))


def make_contact_sheet(frames: list[Image.Image], seed: int, preset: str) -> Image.Image:
    samples = [frames[index] for index in np.linspace(0, len(frames) - 1, num=min(8, len(frames)), dtype=int)]
    thumb_width = 220
    thumb_height = max(64, round(thumb_width * samples[0].height / samples[0].width))
    gutter = 16
    columns = min(4, len(samples))
    rows = int(np.ceil(len(samples) / columns))
    label_height = 50

    sheet = Image.new(
        "RGB",
        (columns * thumb_width + (columns + 1) * gutter, rows * thumb_height + (rows + 1) * gutter + label_height),
        (5, 6, 18),
    )
    draw = ImageDraw.Draw(sheet)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Avenir Next.ttc", size=22)
    except OSError:
        font = ImageFont.load_default(size=22)

    draw.text((gutter, 13), f"STARFORGE LAB // {preset} // seed {seed}", font=font, fill=(220, 240, 248))
    for index, frame in enumerate(samples):
        row, col = divmod(index, columns)
        x = gutter + col * (thumb_width + gutter)
        y = label_height + gutter + row * (thumb_height + gutter)
        thumb = frame.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x, y))
        draw.rectangle((x, y, x + thumb_width - 1, y + thumb_height - 1), outline=(93, 148, 172))

    return sheet


def copy_project_files(output: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("README.md", "ARCHITECTURE.md", "pyproject.toml"):
        source = root / name
        if source.exists():
            shutil.copy2(source, output / name)

    package_dir = output / "starforge"
    tests_dir = output / "tests"
    tools_dir = output / "tools"

    for destination in (package_dir, tests_dir, tools_dir):
        if destination.exists():
            shutil.rmtree(destination)

    shutil.copytree(root / "starforge", package_dir)
    shutil.copytree(root / "tests", tests_dir)
    shutil.copytree(root / "tools", tools_dir)
    github_dir = root / ".github"
    if github_dir.exists():
        destination = output / ".github"
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(github_dir, destination)


if __name__ == "__main__":
    raise SystemExit(main())
