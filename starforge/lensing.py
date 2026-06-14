from __future__ import annotations

import math

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
