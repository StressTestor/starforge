from __future__ import annotations

import hashlib

import pytest

from starforge.config import RenderConfig
from starforge.renderer import StarforgeRenderer


def digest_image(image) -> str:
    return hashlib.sha256(image.tobytes()).hexdigest()


def test_poster_is_deterministic_for_fixed_seed() -> None:
    config = RenderConfig(width=180, height=240, seed=777, frames=5)

    first = StarforgeRenderer(config).render_poster()
    second = StarforgeRenderer(config).render_poster()

    assert first.size == (180, 240)
    assert first.mode == "RGB"
    assert digest_image(first) == digest_image(second)


def test_different_seeds_change_poster() -> None:
    first = StarforgeRenderer(RenderConfig(width=180, height=240, seed=777, frames=5)).render_poster()
    second = StarforgeRenderer(RenderConfig(width=180, height=240, seed=778, frames=5)).render_poster()

    assert digest_image(first) != digest_image(second)


def test_animation_frame_count_and_dimensions() -> None:
    config = RenderConfig(width=160, height=120, seed=111, frames=7)

    frames = StarforgeRenderer(config).render_animation_frames()

    assert len(frames) == 7
    assert {frame.size for frame in frames} == {(160, 120)}
    assert {frame.mode for frame in frames} == {"RGB"}
    assert digest_image(frames[0]) != digest_image(frames[-1])


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("width", 63, "width must be at least 64"),
        ("height", 63, "height must be at least 64"),
        ("frames", 1, "frames must be at least 2"),
    ],
)
def test_config_rejects_invalid_render_settings(field: str, value: int, message: str) -> None:
    kwargs = {"width": 128, "height": 128, "seed": 1, "frames": 3}
    kwargs[field] = value

    with pytest.raises(ValueError, match=message):
        RenderConfig(**kwargs)
