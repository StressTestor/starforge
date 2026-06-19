from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from PIL import Image, ImageSequence

from starforge import __version__
from starforge.cli import copy_project_files, make_contact_sheet


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
            "--studio",
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
    assert (output / "studio.html").is_file()
    assert (output / "manifest.json").is_file()

    poster = Image.open(output / "starforge_poster.png")
    assert poster.size == (192, 256)

    gif = Image.open(output / "starforge.gif")
    assert sum(1 for _ in ImageSequence.Iterator(gif)) == 6

    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["seed"] == 4242
    assert manifest["selected_seed"] in [entry["seed"] for entry in manifest["collection"]]
    assert manifest["project"] == "starforge-lab"
    assert manifest["version"] == __version__
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

    # the studio ranks the FULL sweep (all 8 batch candidates, not just top-k)
    assert "studio.html" in manifest["assets"]
    assert len(manifest["studio"]) == 8
    assert any(row["frontier"] for row in manifest["studio"])
    assert all("norm_total" in row and "subject_rank" in row and "why" in row for row in manifest["studio"])
    studio_html = (output / "studio.html").read_text()
    assert studio_html.startswith("<!doctype html>")
    assert "data:image/png;base64," in studio_html  # self-contained

    html = (output / "index.html").read_text()
    assert "cold-singularity" in html
    assert "starforge_poster.png" in html
    assert "seed_gallery.png" in html
    assert "collection_gallery.png" in html
    assert "starforge.mp4" in html


def _make_source_tree(root: Path) -> None:
    for name in ("starforge", "tests", "tools", ".github"):
        (root / name).mkdir(parents=True)
        (root / name / "sentinel.py").write_text("# keep me\n")
    for name in ("README.md", "ARCHITECTURE.md", "pyproject.toml"):
        (root / name).write_text(name)


def test_copy_project_files_refuses_to_overwrite_source(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _make_source_tree(src)

    with pytest.raises(ValueError, match="refusing to write release into the source tree"):
        copy_project_files(src, root=src)

    # the guard must fire before any rmtree, so the source is untouched.
    for name in ("starforge", "tests", "tools", ".github"):
        assert (src / name / "sentinel.py").read_text() == "# keep me\n"


def test_copy_project_files_writes_into_separate_dir(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _make_source_tree(src)
    dest = tmp_path / "release"
    dest.mkdir()

    copy_project_files(dest, root=src)

    assert (dest / "starforge" / "sentinel.py").exists()
    assert (dest / "tests" / "sentinel.py").exists()
    assert (dest / "tools" / "sentinel.py").exists()
    assert (dest / ".github" / "sentinel.py").exists()
    assert (dest / "README.md").read_text() == "README.md"


def test_make_contact_sheet_rejects_empty_frames() -> None:
    with pytest.raises(ValueError, match="at least one frame"):
        make_contact_sheet([], seed=1, preset="neon-collapse")


def test_package_version_is_single_sourced_with_pyproject() -> None:
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    assert project["project"]["version"] == __version__
