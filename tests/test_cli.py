from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageSequence


def test_cli_writes_release_assets(tmp_path: Path) -> None:
    output = tmp_path / "release"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "starforge.cli",
            "--output",
            str(output),
            "--width",
            "192",
            "--height",
            "256",
            "--frames",
            "6",
            "--seed",
            "4242",
            "--preset",
            "cold-singularity",
            "--seed-gallery",
            "4",
            "--batch",
            "8",
            "--top-k",
            "4",
            "--supersample",
            "2",
            "--video",
            "--scale-preview",
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": ".", "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert (output / "starforge_poster.png").is_file()
    assert (output / "starforge.gif").is_file()
    assert (output / "starforge.mp4").is_file()
    assert (output / "starforge.webm").is_file()
    assert (output / "starforge_contact_sheet.png").is_file()
    assert (output / "seed_gallery.png").is_file()
    assert (output / "collection_gallery.png").is_file()
    assert (output / "index.html").is_file()
    assert (output / "manifest.json").is_file()

    poster = Image.open(output / "starforge_poster.png")
    assert poster.size == (192, 256)

    gif = Image.open(output / "starforge.gif")
    assert sum(1 for _ in ImageSequence.Iterator(gif)) == 6

    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["seed"] == 4242
    assert manifest["selected_seed"] in [entry["seed"] for entry in manifest["collection"]]
    assert manifest["project"] == "starforge-lab"
    assert manifest["preset"] == "cold-singularity"
    assert manifest["selected_preset"] in {"event-horizon", "neon-collapse", "cold-singularity", "solar-wound", "deep-field"}
    assert manifest["width"] == 192
    assert manifest["height"] == 256
    assert manifest["frames"] == 6
    assert manifest["supersample"] == 2
    assert "selected_genome" in manifest
    assert "center_x" in manifest["selected_genome"]
    assert "disk_tilt" in manifest["selected_genome"]
    assert len(manifest["collection"]) == 4
    assert all("reasons" in entry["score"] for entry in manifest["collection"])
    assert set(manifest["assets"]) >= {
        "starforge_poster.png",
        "starforge.gif",
        "starforge.mp4",
        "starforge.webm",
        "starforge_contact_sheet.png",
        "seed_gallery.png",
        "collection_gallery.png",
        "index.html",
    }
    assert len(manifest["seed_candidates"]) == 4
    assert manifest["video"]["mp4"] == "written"
    assert manifest["video"]["webm"] == "written"

    html = (output / "index.html").read_text()
    assert "cold-singularity" in html
    assert "starforge_poster.png" in html
    assert "seed_gallery.png" in html
    assert "collection_gallery.png" in html
    assert "starforge.mp4" in html
