from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_ASSET_FILES = (
    "starforge_poster.png",
    "starforge.gif",
    "starforge_contact_sheet.png",
    "seed_gallery.png",
    "collection_gallery.png",
    "index.html",
)


def _load_inspect():
    spec = importlib.util.spec_from_file_location(
        "inspect_outputs", ROOT / "tools" / "inspect_outputs.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _full_manifest() -> dict[str, object]:
    return {
        "project": "starforge-lab",
        "version": "5.0.0",
        "selected_seed": 1,
        "selected_preset": "neon-collapse",
        "selected_genome": {},
        "preset": "neon-collapse",
        "seed": 1,
        "width": 100,
        "height": 100,
        "frames": 4,
        "seed_candidates": [],
        "collection": [],
        "video": {},
        "assets": [],
        "supersample": 1,
    }


def _write_release(release: Path, manifest: dict[str, object]) -> None:
    # the file-existence gate runs before the manifest-key check, so the asset
    # files only need to exist (they are not opened until after the key check).
    for name in _ASSET_FILES:
        (release / name).write_bytes(b"placeholder")
    (release / "manifest.json").write_text(json.dumps(manifest))


@pytest.mark.parametrize("missing", ["width", "height", "frames", "seed"])
def test_inspect_reports_missing_manifest_key_cleanly(tmp_path, capsys, missing) -> None:
    inspect = _load_inspect()
    manifest = _full_manifest()
    del manifest[missing]
    _write_release(tmp_path, manifest)

    code = inspect.main([str(tmp_path)])

    assert code == 1
    err = capsys.readouterr().err
    assert "manifest missing keys" in err
    assert missing in err
