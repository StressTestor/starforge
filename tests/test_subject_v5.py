from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from starforge.config import RenderConfig
from starforge.genome import SUBJECT_NAMES, Genome
from starforge.lensing import _bilinear_sample_f, build_einstein_lens_map
from starforge.presets import PRESET_NAMES
from starforge.renderer import StarforgeRenderer


def test_subject_validation() -> None:
    assert "black-hole" in SUBJECT_NAMES and "lensed-galaxy" in SUBJECT_NAMES
    with pytest.raises(ValueError):
        Genome.from_seed(1, "neon-collapse", subject="quasar")
    with pytest.raises(ValueError):
        RenderConfig(subject="quasar")


def test_default_subject_is_black_hole_and_explicit_matches() -> None:
    default = StarforgeRenderer(RenderConfig(width=160, height=220, seed=260613, frames=4)).render_poster(include_title=False)
    explicit = StarforgeRenderer(
        RenderConfig(width=160, height=220, seed=260613, frames=4, subject="black-hole")
    ).render_poster(include_title=False)
    assert np.array_equal(np.asarray(default), np.asarray(explicit))


def test_galaxy_differs_from_black_hole_for_same_seed() -> None:
    cfg = dict(width=200, height=275, seed=323965, frames=4, preset="solar-wound")
    bh = np.asarray(StarforgeRenderer(RenderConfig(**cfg, subject="black-hole")).render_poster(include_title=False), dtype=np.float32)
    gal = np.asarray(StarforgeRenderer(RenderConfig(**cfg, subject="lensed-galaxy")).render_poster(include_title=False), dtype=np.float32)
    # genuinely different renders, not a relabel
    assert float(np.abs(bh - gal).mean()) > 5.0


def test_galaxy_renders_finite_uint8_every_preset() -> None:
    for preset in PRESET_NAMES:
        image = StarforgeRenderer(
            RenderConfig(width=200, height=275, seed=331884, frames=4, preset=preset, subject="lensed-galaxy")
        ).render_poster()
        arr = np.asarray(image)
        assert arr.dtype == np.uint8 and image.mode == "RGB"
        assert np.isfinite(arr).all()


def test_galaxy_is_deterministic_and_frame_stable() -> None:
    cfg = RenderConfig(width=240, height=330, seed=260613, frames=10, preset="deep-field", subject="lensed-galaxy")
    a = np.asarray(StarforgeRenderer(cfg).render_poster())
    b = np.asarray(StarforgeRenderer(cfg).render_poster())
    assert np.array_equal(a, b)

    frames = StarforgeRenderer(cfg).render_animation_frames()

    def macro(img: Image.Image) -> np.ndarray:
        return np.asarray(img.convert("L").resize((16, 16), Image.Resampling.BILINEAR), dtype=np.float32)

    base = macro(frames[0]).ravel()
    corrs = [float(np.corrcoef(base, macro(f).ravel())[0, 1]) for f in frames[1:]]
    assert min(corrs) > 0.95  # the lens + galaxies are frame-invariant; only twinkle animates


def test_einstein_lens_map_is_well_formed() -> None:
    lens = build_einstein_lens_map(200, 260, center_x=0.0, center_y=0.0, einstein_radius=0.3)
    sx, sy = lens.src
    mag = lens.magnification
    image_radius = lens.image_radius
    assert np.isfinite(sx).all() and np.isfinite(sy).all()
    assert np.isfinite(mag).all() and float(mag.max()) <= 9.0
    # magnification is strongest near the critical curve (image radius ~ einstein radius)
    near = np.abs(image_radius - 0.3) < 0.03
    far = image_radius > 0.7
    assert float(mag[near].mean()) > float(mag[far].mean())


def test_bilinear_gather_through_lens_is_finite() -> None:
    src = np.zeros((120, 100, 3), dtype=np.float32)
    src[60, 50] = (1.0, 0.8, 0.6)
    lens = build_einstein_lens_map(100, 120, center_x=0.0, center_y=0.0, einstein_radius=0.3)
    sx, sy = lens.src
    out = _bilinear_sample_f(src, sx, sy)
    assert np.isfinite(out).all()
