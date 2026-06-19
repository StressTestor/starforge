#!/usr/bin/env python3
"""Regenerate the pixel-golden hashes for the CURRENT environment.

The golden pins the byte-exact output of a few small, title-free renders so a
deterministic-but-wrong visual change (a constant retune that touches no genome
field) is caught — the rest of the suite only checks self-consistency and
seed-sensitivity, never a fixed expected value.

Pixel bytes are sensitive to the platform / numpy / Pillow build (transcendental
math, BLAS), so hashes are stored per-environment. Running this on a new
environment ADDS that environment's hashes; it never deletes another's. The test
(tests/test_golden_pixels_v5.py) skips cleanly when the running environment has
no committed golden, so it never reds CI on an unseen platform.

usage: PYTHONPATH=. python3 tools/regen_pixel_golden.py
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from starforge.config import RenderConfig  # noqa: E402
from starforge.renderer import StarforgeRenderer  # noqa: E402

GOLDEN_PATH = ROOT / "tests" / "_pixel_golden_v5.json"

# small, title-free renders covering every subject across several presets.
DEFAULT_SPECS = [
    {"seed": 260613, "preset": "neon-collapse", "subject": "black-hole", "width": 160, "height": 220},
    {"seed": 331884, "preset": "event-horizon", "subject": "black-hole", "width": 160, "height": 220},
    {"seed": 379398, "preset": "deep-field", "subject": "black-hole", "width": 160, "height": 220},
    {"seed": 260613, "preset": "neon-collapse", "subject": "lensed-galaxy", "width": 160, "height": 220},
    {"seed": 323965, "preset": "cold-singularity", "subject": "lensed-galaxy", "width": 160, "height": 220},
    {"seed": 300208, "preset": "solar-wound", "subject": "lensed-galaxy", "width": 160, "height": 220},
    {"seed": 260613, "preset": "neon-collapse", "subject": "neutron-star", "width": 160, "height": 220},
    {"seed": 331884, "preset": "cold-singularity", "subject": "neutron-star", "width": 160, "height": 220},
    {"seed": 323965, "preset": "deep-field", "subject": "wormhole", "width": 160, "height": 220},
    {"seed": 379398, "preset": "event-horizon", "subject": "wormhole", "width": 160, "height": 220},
]


def environment_signature() -> str:
    return (
        f"{platform.system()}-{platform.machine()}"
        f"-py{sys.version_info.major}.{sys.version_info.minor}"
        f"-numpy{np.__version__}-pillow{Image.__version__}"
    )


def spec_key(spec: dict[str, object]) -> str:
    return f"{spec['seed']}:{spec['preset']}:{spec['subject']}:{spec['width']}x{spec['height']}"


def render_hash(spec: dict[str, object]) -> str:
    config = RenderConfig(
        width=int(spec["width"]),
        height=int(spec["height"]),
        frames=2,
        seed=int(spec["seed"]),
        preset=str(spec["preset"]),
        subject=str(spec["subject"]),
    )
    poster = StarforgeRenderer(config).render_poster(include_title=False)
    return hashlib.sha256(poster.tobytes()).hexdigest()


def _merge_specs(existing: list[dict[str, object]]) -> list[dict[str, object]]:
    # DEFAULT_SPECS is the source of truth; any extra specs already committed to
    # the file are preserved. Editing DEFAULT_SPECS is honored, never silently
    # ignored just because the golden file already exists.
    by_key = {spec_key(spec): spec for spec in DEFAULT_SPECS}
    order = [spec_key(spec) for spec in DEFAULT_SPECS]
    for spec in existing:
        key = spec_key(spec)
        if key not in by_key:
            by_key[key] = spec
            order.append(key)
    return [by_key[key] for key in order]


def main() -> int:
    data = json.loads(GOLDEN_PATH.read_text()) if GOLDEN_PATH.exists() else {}
    data["specs"] = _merge_specs(data.get("specs", []))
    data.setdefault("environments", {})

    signature = environment_signature()
    hashes = {spec_key(spec): render_hash(spec) for spec in data["specs"]}
    data["environments"][signature] = hashes

    GOLDEN_PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"wrote {len(hashes)} pixel-golden hashes for {signature}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
