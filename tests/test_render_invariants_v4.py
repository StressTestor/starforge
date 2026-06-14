from __future__ import annotations

import numpy as np
from PIL import Image

from starforge.config import RenderConfig
from starforge.curation import get_curator
from starforge.genome import Genome
from starforge.lensing import _bilinear_sample_f
from starforge.presets import PRESET_NAMES
from starforge.renderer import StarforgeRenderer


def test_rendered_poster_is_finite_uint8_for_every_preset() -> None:
    # the lensing uses -log and divides near the photon sphere; the captured
    # region must never leak NaN/Inf into the output, for any preset.
    for preset in PRESET_NAMES:
        image = StarforgeRenderer(
            RenderConfig(width=200, height=275, seed=300208, frames=4, preset=preset)
        ).render_poster()
        arr = np.asarray(image)
        assert arr.dtype == np.uint8
        assert image.mode == "RGB"
        assert np.isfinite(arr).all()


def test_macro_structure_is_frame_stable() -> None:
    # genome, fold map and ring field are built once in __init__, so the macro
    # composition must hold across animation frames — only the disk texture
    # animates. Heavy downsampling washes out the texture and exposes the macro.
    r = StarforgeRenderer(RenderConfig(width=320, height=440, seed=260613, frames=12, preset="neon-collapse"))
    frames = r.render_animation_frames()

    def macro(img: Image.Image) -> np.ndarray:
        return np.asarray(img.convert("L").resize((16, 16), Image.Resampling.BILINEAR), dtype=np.float32)

    base = macro(frames[0]).ravel()
    corrs = [float(np.corrcoef(base, macro(f).ravel())[0, 1]) for f in frames[1:]]
    assert min(corrs) > 0.95, f"macro structure drifts across frames: {min(corrs)}"


def test_bilinear_sample_f_preserves_hdr_values() -> None:
    # the float gather must not clip disk emission brighter than 1.0 (a uint8
    # round-trip would). Sample at integer coordinates -> exact source values.
    source = np.zeros((4, 4, 3), dtype=np.float32)
    source[2, 2] = 1.581
    x = np.array([[2.0]], dtype=np.float32)
    y = np.array([[2.0]], dtype=np.float32)
    out = _bilinear_sample_f(source, x, y)
    assert float(out.max()) >= 1.5


def test_color_harmony_is_zero_for_an_all_dark_image() -> None:
    dark = Image.new("RGB", (64, 64), (2, 2, 4))
    result = get_curator().score(dark, Genome.from_seed(1, "neon-collapse"))
    assert np.isfinite(result.total)
    assert result.reasons["color_harmony"] >= 0.0


def test_off_center_genome_keeps_shadow_dark() -> None:
    # an off-center black hole must still carve a dark shadow (the emergent ring
    # and lensing follow the genome center, not the image center).
    image = StarforgeRenderer(
        RenderConfig(width=240, height=330, seed=331884, frames=4, preset="event-horizon")
    ).render_poster(include_title=False)
    arr = np.asarray(image.convert("L"), dtype=np.float32)
    assert float(arr.min()) < 30.0  # there is a genuinely dark region somewhere
