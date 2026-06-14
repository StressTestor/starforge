from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: python3 tools/inspect_outputs.py <release-dir>", file=sys.stderr)
        return 2

    release = Path(args[0])
    manifest_path = release / "manifest.json"
    poster_path = release / "starforge_poster.png"
    gif_path = release / "starforge.gif"
    contact_path = release / "starforge_contact_sheet.png"
    gallery_path = release / "seed_gallery.png"
    collection_path = release / "collection_gallery.png"
    html_path = release / "index.html"

    for path in (manifest_path, poster_path, gif_path, contact_path, gallery_path, collection_path, html_path):
        if not path.is_file():
            print(f"missing {path}", file=sys.stderr)
            return 1

    manifest = json.loads(manifest_path.read_text())
    if manifest.get("project") != "starforge-lab":
        print(f"unexpected project: {manifest.get('project')}", file=sys.stderr)
        return 1

    required_manifest = {
        "selected_seed",
        "selected_preset",
        "selected_genome",
        "preset",
        "seed_candidates",
        "collection",
        "video",
        "assets",
        "supersample",
    }
    missing = sorted(required_manifest - set(manifest))
    if missing:
        print(f"manifest missing keys: {missing}", file=sys.stderr)
        return 1

    for key in ("center_x", "center_y", "disk_tilt", "jet_angle", "horizon_radius", "lensing_strength"):
        if key not in manifest["selected_genome"]:
            print(f"selected genome missing key: {key}", file=sys.stderr)
            return 1

    if not manifest["collection"]:
        print("manifest collection is empty", file=sys.stderr)
        return 1
    for entry in manifest["collection"]:
        if "score" not in entry or "reasons" not in entry["score"] or not entry["score"]["reasons"]:
            print("collection entry missing score reasons", file=sys.stderr)
            return 1

    assets = set(manifest["assets"])
    for asset in (
        "starforge_poster.png",
        "starforge.gif",
        "starforge_contact_sheet.png",
        "seed_gallery.png",
        "collection_gallery.png",
        "index.html",
    ):
        if asset not in assets:
            print(f"manifest missing asset: {asset}", file=sys.stderr)
            return 1

    poster = Image.open(poster_path)
    if poster.size != (manifest["width"], manifest["height"]):
        print(f"poster size mismatch: {poster.size}", file=sys.stderr)
        return 1

    arr = np.asarray(poster.convert("RGB"), dtype=np.float32)
    if float(arr.std()) < 8.0:
        print("poster appears blank or too low-contrast", file=sys.stderr)
        return 1

    gif = Image.open(gif_path)
    frame_count = sum(1 for _ in ImageSequence.Iterator(gif))
    if frame_count != manifest["frames"]:
        print(f"gif frame mismatch: {frame_count} != {manifest['frames']}", file=sys.stderr)
        return 1

    contact = Image.open(contact_path)
    if contact.width < 400 or contact.height < 200:
        print(f"contact sheet too small: {contact.size}", file=sys.stderr)
        return 1

    gallery = Image.open(gallery_path)
    if gallery.width < 400 or gallery.height < 200:
        print(f"seed gallery too small: {gallery.size}", file=sys.stderr)
        return 1

    collection = Image.open(collection_path)
    if collection.width < 400 or collection.height < 200:
        print(f"collection gallery too small: {collection.size}", file=sys.stderr)
        return 1

    html = html_path.read_text()
    for reference in (
        "starforge_poster.png",
        "starforge.gif",
        "seed_gallery.png",
        "collection_gallery.png",
        "starforge_contact_sheet.png",
    ):
        if reference not in html:
            print(f"index.html missing reference: {reference}", file=sys.stderr)
            return 1

    video = manifest["video"]
    for kind, filename in (("mp4", "starforge.mp4"), ("webm", "starforge.webm")):
        if video.get(kind) == "written":
            path = release / filename
            if filename not in assets or not path.is_file() or path.stat().st_size == 0:
                print(f"{filename} marked written but missing or empty", file=sys.stderr)
                return 1

    print(
        json.dumps(
            {
                "poster": poster.size,
                "poster_std": round(float(arr.std()), 2),
                "gif_frames": frame_count,
                "contact_sheet": contact.size,
                "collection_gallery": collection.size,
                "seed_gallery": gallery.size,
                "preset": manifest["preset"],
                "seed": manifest["seed"],
                "selected_seed": manifest["selected_seed"],
                "selected_preset": manifest["selected_preset"],
                "top_collection": len(manifest["collection"]),
                "video": video,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
