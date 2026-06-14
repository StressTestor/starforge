from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image


def apply_gravitational_lensing(
    image: Image.Image,
    *,
    strength: float,
    event_horizon: float,
    spin: float = 0.18,
    center_x: float = 0.0,
    center_y: float = 0.0,
) -> Image.Image:
    """Warp an RGB image around the center to fake gravitational lensing."""

    source = np.asarray(image.convert("RGB"), dtype=np.uint8)
    height, width = source.shape[:2]
    scale = min(width, height) / 2.0
    pixel_center_x = (width - 1) / 2.0 + center_x * scale
    pixel_center_y = (height - 1) / 2.0 + center_y * scale

    yy, xx = np.indices((height, width), dtype=np.float32)
    dx = (xx - pixel_center_x) / scale
    dy = (yy - pixel_center_y) / scale
    radius = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dy, dx)

    ring_pull = strength * np.exp(-((radius - event_horizon * 1.55) ** 2) / 0.035)
    core_shear = strength * 0.38 / np.maximum(radius + 0.08, 0.08)
    theta_source = theta + spin * np.exp(-(radius**2) / 0.34)
    radius_source = radius + ring_pull + core_shear

    src_x = pixel_center_x + np.cos(theta_source) * radius_source * scale
    src_y = pixel_center_y + np.sin(theta_source) * radius_source * scale

    warped = _bilinear_sample(source, src_x, src_y)

    caustic = np.exp(-((radius - event_horizon * 1.40) ** 2) / 0.0018)
    warped = np.clip(warped.astype(np.float32) * (1.0 + caustic[..., None] * 0.18), 0, 255).astype(np.uint8)
    return Image.fromarray(warped, mode="RGB")


def _bilinear_sample(source: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    height, width = source.shape[:2]
    x = np.clip(x, 0, width - 1)
    y = np.clip(y, 0, height - 1)

    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    x1 = np.clip(x0 + 1, 0, width - 1)
    y1 = np.clip(y0 + 1, 0, height - 1)

    wx = (x - x0)[..., None]
    wy = (y - y0)[..., None]
    top = source[y0, x0].astype(np.float32) * (1.0 - wx) + source[y0, x1].astype(np.float32) * wx
    bottom = source[y1, x0].astype(np.float32) * (1.0 - wx) + source[y1, x1].astype(np.float32) * wx
    return np.clip(top * (1.0 - wy) + bottom * wy, 0, 255).astype(np.uint8)


def lensing_spin_for_phase(phase: float) -> float:
    return 0.16 + 0.045 * math.sin(phase * math.tau)


def build_deflection_lut(
    b_ph: float,
    lensing_strength: float,
    *,
    n: int = 4096,
    b_max: float = 1.8,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Tabulate light bending angle vs impact parameter.

    ``alpha(b)`` blends the strong-deflection limit (a logarithmic divergence as
    ``b`` approaches the photon-sphere radius ``b_ph``) with the weak-field
    ``1/b`` tail. The raw divergence ``ring`` is the emergent photon-ring
    brightness. Everything is a closed-form 1D table, so the per-pixel cost is a
    single vectorized gather.
    """

    bb = np.linspace(0.0, b_max, n, dtype=np.float32)
    b_ph = max(b_ph, 1e-4)
    outside = bb > b_ph  # inside the photon sphere is captured (shadow), not a ring
    u = np.clip(bb / b_ph - 1.0, 1e-4, None)
    sdl = np.clip(-np.log(u), 0.0, 8.0)
    # the raw divergence is the emergent photon ring; it is ZERO inside b_ph so
    # the captured shadow stays dark instead of filling with light.
    ring = np.where(outside, np.clip(-np.log(u), 0.0, 12.0), 0.0)
    weak = b_ph / np.clip(bb, 1e-4, None)
    wt = np.exp(-(((bb - b_ph) / (0.6 * b_ph)) ** 2))
    alpha = lensing_strength * (wt * sdl + (1.0 - wt) * weak)
    return bb, alpha.astype(np.float32), ring.astype(np.float32), wt.astype(np.float32)


def sample_emergent_ring(
    radius: np.ndarray,
    luts: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    *,
    b_max: float = 1.8,
) -> np.ndarray:
    """Gather the emergent photon-ring field from the deflection LUT.

    ``radius`` is the black-hole-centered image radius (the apparent impact
    parameter). The ring brightness is the raw log-divergence that piles up just
    outside the photon sphere and is zero inside it.
    """
    _, _, ring_lut, _ = luts
    n = ring_lut.shape[0]
    idx = np.clip((radius / b_max * (n - 1)).astype(np.int32), 0, n - 1)
    return ring_lut[idx].astype(np.float32)


def _bilinear_sample_f(source: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Bilinear gather on a float (H, W, C) buffer — no lossy uint8 round-trip,
    so disk emission brighter than 1.0 survives the fold."""
    height, width = source.shape[:2]
    x = np.clip(x, 0, width - 1)
    y = np.clip(y, 0, height - 1)
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    x1 = np.clip(x0 + 1, 0, width - 1)
    y1 = np.clip(y0 + 1, 0, height - 1)
    wx = (x - x0)[..., None]
    wy = (y - y0)[..., None]
    top = source[y0, x0] * (1.0 - wx) + source[y0, x1] * wx
    bottom = source[y1, x0] * (1.0 - wx) + source[y1, x1] * wx
    return (top * (1.0 - wy) + bottom * wy).astype(np.float32)


@dataclass(frozen=True)
class DiskFold:
    """Precomputed gravitational fold: per-pixel source coordinates (pixels) and
    the brightness window for the over-shadow arc (top) and under-curl (bottom).
    """

    src_top: tuple[np.ndarray, np.ndarray]
    w_top: np.ndarray
    src_bot: tuple[np.ndarray, np.ndarray]
    w_bot: np.ndarray


# the secondary image samples the disk's bright ring just inside its outer edge
_RING_SAMPLE_FRACTION = 0.97


def build_disk_fold_map(
    width: int,
    height: int,
    *,
    center_x: float,
    center_y: float,
    orientation: float,
    disk_radius: float,
    disk_thickness: float,
    horizon_radius: float,
    photon_radius: float,
    arc_band: float = 0.07,
) -> DiskFold:
    """Precompute the gravitational "fold" that lays the disk's far side as an
    arc over the top of the shadow (and a dimmer curl beneath it).

    The destination is a circular band hugging the shadow; the source is the
    inclined disk's own bright ring. Because the disk is squashed vertically by
    ``disk_thickness`` (its inclination), the source must be sampled on that
    ellipse, not on a circle, or the gather lands in empty space above the disk.
    Frame-invariant: depends only on genome geometry. Image +y is DOWN, so the
    toward-the-top vector is ``-sin(theta)``.
    """
    scale = min(width, height) / 2.0
    cx = (width - 1) / 2.0 + center_x * scale
    cy = (height - 1) / 2.0 + center_y * scale
    yy, xx = np.indices((height, width), dtype=np.float32)
    dx = (xx - cx) / scale
    dy = (yy - cy) / scale
    r = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dy, dx)
    theta_t = theta - orientation
    up = -np.sin(theta_t)  # +y is DOWN -> toward image top is -sin

    cos_o = math.cos(orientation)
    sin_o = math.sin(orientation)
    thick = max(disk_thickness, 0.05)
    sig = 0.011 + horizon_radius * 0.035
    # the source radius is fixed at the disk's bright ring so the arc reads clean,
    # not as a radial spray; the window bounds only position the destination band.
    r_src = disk_radius * _RING_SAMPLE_FRACTION

    def fold(
        window_inner: float, window_outer: float, mirror: float, hemisphere: np.ndarray, sig_scale: float
    ) -> tuple[tuple[np.ndarray, np.ndarray], np.ndarray]:
        a = mirror - theta_t  # mirror to the far side, in the tilt-rotated frame
        # sample the inclined disk ellipse (vertical squash = thickness), then
        # rotate back into image space and convert to pixels
        xr = np.cos(a) * r_src
        yr = np.sin(a) * r_src * thick
        gx = xr * cos_o - yr * sin_o
        gy = xr * sin_o + yr * cos_o
        src = ((cx + gx * scale).astype(np.float32), (cy + gy * scale).astype(np.float32))
        window = (
            np.exp(-((r - 0.5 * (window_inner + window_outer)) ** 2) / (sig * sig_scale))
            * np.clip(hemisphere, 0.0, 1.0) ** 2
        ).astype(np.float32)
        return src, window

    top_src, w_top = fold(horizon_radius * 1.02, photon_radius + arc_band, math.pi, up, 1.0)
    bot_src, w_bot = fold(horizon_radius, photon_radius + arc_band * 0.55, -math.pi, -up, 0.6)
    return DiskFold(src_top=top_src, w_top=w_top, src_bot=bot_src, w_bot=w_bot)
