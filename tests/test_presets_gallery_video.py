from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import numpy as np
from PIL import Image

from starforge.config import RenderConfig
from starforge.gallery import build_seed_gallery, candidate_seeds, score_image
from starforge.lensing import apply_gravitational_lensing
from starforge.presets import PRESET_NAMES, get_preset
from starforge.video import build_ffmpeg_command


def digest_image(image: Image.Image) -> str:
    return hashlib.sha256(image.tobytes()).hexdigest()


def test_named_presets_are_available_and_validated() -> None:
    assert set(PRESET_NAMES) == {
        "event-horizon",
        "neon-collapse",
        "cold-singularity",
        "solar-wound",
        "deep-field",
    }
    assert get_preset("neon-collapse").name == "neon-collapse"

    with pytest.raises(ValueError, match="unknown preset"):
        RenderConfig(width=128, height=128, frames=3, preset="mud")


def test_lensing_changes_image_deterministically() -> None:
    image = Image.linear_gradient("L").resize((96, 96)).convert("RGB")

    first = apply_gravitational_lensing(image, strength=0.22, event_horizon=0.22)
    second = apply_gravitational_lensing(image, strength=0.22, event_horizon=0.22)

    assert first.size == image.size
    assert digest_image(first) == digest_image(second)
    assert digest_image(first) != digest_image(image)


def test_lensing_uses_bilinear_sampling_not_nearest_neighbor() -> None:
    image = Image.new("RGB", (48, 48), (0, 0, 0))
    pixels = image.load()
    for y in range(48):
        for x in range(48):
            if (x // 6 + y // 6) % 2:
                pixels[x, y] = (255, 255, 255)

    lensed = apply_gravitational_lensing(image, strength=0.28, event_horizon=0.22)
    values = set(np.asarray(lensed.convert("L")).ravel().tolist())

    assert len(values) > 2


def test_seed_gallery_selects_best_seed_deterministically() -> None:
    config = RenderConfig(width=96, height=128, frames=3, seed=1234, preset="deep-field")

    first = build_seed_gallery(config, count=5, thumb_width=80)
    second = build_seed_gallery(config, count=5, thumb_width=80)

    assert candidate_seeds(1234, 5) == [1234, 9153, 17072, 24991, 32910]
    assert [candidate.seed for candidate in first.candidates] == candidate_seeds(1234, 5)
    assert first.selected_seed in [candidate.seed for candidate in first.candidates]
    assert first.selected_seed == second.selected_seed
    assert first.image.size == (4 * 80 + 5 * 12, 2 * 107 + 3 * 12 + 46)
    assert digest_image(first.image) == digest_image(second.image)


def test_score_image_prefers_contrast_and_bright_ring() -> None:
    flat = Image.new("RGB", (96, 96), (20, 20, 20))
    contrast = Image.new("RGB", (96, 96), (20, 20, 20))
    pixels = contrast.load()
    for y in range(32, 64):
        for x in range(32, 64):
            pixels[x, y] = (240, 180, 90)

    assert score_image(contrast) > score_image(flat)


def test_ffmpeg_command_is_explicit_for_mp4_and_webm() -> None:
    mp4 = build_ffmpeg_command(Path("frames/frame_%05d.png"), Path("starforge.mp4"), fps=24, kind="mp4")
    webm = build_ffmpeg_command(Path("frames/frame_%05d.png"), Path("starforge.webm"), fps=24, kind="webm")

    assert "-framerate" in mp4
    assert "libx264" in mp4
    assert "yuv420p" in mp4
    assert "libvpx-vp9" in webm
    assert "starforge.webm" in webm[-1]
