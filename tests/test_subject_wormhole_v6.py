from __future__ import annotations

import numpy as np
from PIL import Image

from starforge.config import RenderConfig
from starforge.genome import SUBJECT_NAMES
from starforge.renderer import StarforgeRenderer


def macro(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("L").resize((16, 16), Image.Resampling.BILINEAR), dtype=np.float32).ravel()


def test_wormhole_is_a_registered_subject() -> None:
    assert "wormhole" in SUBJECT_NAMES


def test_wormhole_differs_from_black_hole_for_same_seed() -> None:
    cfg = dict(width=200, height=275, seed=331884, frames=4, preset="deep-field")
    bh = np.asarray(StarforgeRenderer(RenderConfig(**cfg, subject="black-hole")).render_poster(include_title=False), dtype=np.float32)
    wh = np.asarray(StarforgeRenderer(RenderConfig(**cfg, subject="wormhole")).render_poster(include_title=False), dtype=np.float32)
    assert float(np.abs(bh - wh).mean()) > 5.0


def test_wormhole_renders_finite_uint8_every_preset() -> None:
    for preset in ("event-horizon", "neon-collapse", "cold-singularity", "solar-wound", "deep-field"):
        image = StarforgeRenderer(
            RenderConfig(width=200, height=275, seed=323965, frames=4, preset=preset, subject="wormhole")
        ).render_poster()
        arr = np.asarray(image)
        assert arr.dtype == np.uint8 and image.mode == "RGB"
        assert np.isfinite(arr).all()


def test_wormhole_is_deterministic_and_frame_stable() -> None:
    cfg = RenderConfig(width=240, height=330, seed=260613, frames=10, preset="deep-field", subject="wormhole")
    a = np.asarray(StarforgeRenderer(cfg).render_poster())
    b = np.asarray(StarforgeRenderer(cfg).render_poster())
    assert np.array_equal(a, b)

    frames = StarforgeRenderer(cfg).render_animation_frames()
    m = [macro(f) for f in frames]
    # the throat lens and far universe are frame-invariant; only the near sky
    # eases and the rim pulses, so the mouth holds to galaxy-grade stability.
    corrs = [float(np.corrcoef(m[i], m[(i + 1) % len(m)])[0, 1]) for i in range(len(m))]
    assert min(corrs) > 0.95
