from __future__ import annotations

import numpy as np
from PIL import Image

from starforge.config import RenderConfig
from starforge.genome import SUBJECT_NAMES
from starforge.renderer import StarforgeRenderer


def macro(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("L").resize((16, 16), Image.Resampling.BILINEAR), dtype=np.float32).ravel()


def test_neutron_star_is_a_registered_subject() -> None:
    assert "neutron-star" in SUBJECT_NAMES


def test_pulsar_differs_from_black_hole_for_same_seed() -> None:
    cfg = dict(width=200, height=275, seed=331884, frames=4, preset="event-horizon")
    bh = np.asarray(StarforgeRenderer(RenderConfig(**cfg, subject="black-hole")).render_poster(include_title=False), dtype=np.float32)
    ns = np.asarray(StarforgeRenderer(RenderConfig(**cfg, subject="neutron-star")).render_poster(include_title=False), dtype=np.float32)
    # the hot surface where the black hole has a shadow makes these wholly different
    assert float(np.abs(bh - ns).mean()) > 5.0


def test_pulsar_renders_finite_uint8_every_preset() -> None:
    for preset in ("event-horizon", "neon-collapse", "cold-singularity", "solar-wound", "deep-field"):
        image = StarforgeRenderer(
            RenderConfig(width=200, height=275, seed=331884, frames=4, preset=preset, subject="neutron-star")
        ).render_poster()
        arr = np.asarray(image)
        assert arr.dtype == np.uint8 and image.mode == "RGB"
        assert np.isfinite(arr).all()


def test_pulsar_is_deterministic_and_seamless() -> None:
    cfg = RenderConfig(width=200, height=275, seed=260613, frames=42, preset="neon-collapse", subject="neutron-star")
    a = np.asarray(StarforgeRenderer(cfg).render_poster())
    b = np.asarray(StarforgeRenderer(cfg).render_poster())
    assert np.array_equal(a, b)

    frames = StarforgeRenderer(cfg).render_animation_frames()
    m = [macro(f) for f in frames]
    # include the wrap-around (last -> first) so the loop seam is held to the same
    # smoothness as every interior step. The beam sweeps, so this is a moving
    # subject — held to a smooth-motion bar, not the near-static galaxy's 0.95.
    corrs = [float(np.corrcoef(m[i], m[(i + 1) % len(m)])[0, 1]) for i in range(len(m))]
    assert min(corrs) > 0.85
