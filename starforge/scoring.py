from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

from starforge.genome import Genome


@dataclass(frozen=True)
class ScoreResult:
    total: float
    reasons: dict[str, float]

    def to_manifest(self) -> dict[str, object]:
        return {
            "total": round(self.total, 4),
            "reasons": {key: round(value, 4) for key, value in self.reasons.items()},
        }


def prepare_score_array(image: Image.Image) -> np.ndarray:
    """The 128x128 float RGB array every scorer works from. Exposed so a curator
    that needs its own pixel measures can compute it once and hand it to
    ``score_composition`` instead of resizing the image twice."""
    return np.asarray(image.convert("RGB").resize((128, 128), Image.Resampling.BILINEAR), dtype=np.float32)


def score_composition(image: Image.Image, genome: Genome, *, arr: np.ndarray | None = None) -> ScoreResult:
    if arr is None:
        arr = prepare_score_array(image)
    luminance = arr[..., 0] * 0.2126 + arr[..., 1] * 0.7152 + arr[..., 2] * 0.0722

    tonal_range = float(np.percentile(luminance, 98) - np.percentile(luminance, 8))
    threshold = np.percentile(luminance, 88)
    weights = np.clip(luminance - threshold, 0, None)
    if float(weights.sum()) <= 1e-6:
        focal_x = focal_y = 0.5
    else:
        yy, xx = np.indices(luminance.shape, dtype=np.float32)
        focal_x = float((xx * weights).sum() / weights.sum() / (luminance.shape[1] - 1))
        focal_y = float((yy * weights).sum() / weights.sum() / (luminance.shape[0] - 1))

    thirds_points = ((1 / 3, 1 / 3), (2 / 3, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 2 / 3))
    nearest_third = min(((focal_x - x) ** 2 + (focal_y - y) ** 2) ** 0.5 for x, y in thirds_points)
    thirds = max(0.0, 100.0 * (1.0 - nearest_third / 0.48))

    center_distance = ((focal_x - 0.5) ** 2 + (focal_y - 0.5) ** 2) ** 0.5
    focal_balance = max(0.0, 100.0 * (1.0 - abs(center_distance - 0.25) / 0.35))

    bright_fraction = float((luminance > np.percentile(luminance, 82)).mean())
    busy_penalty = -max(0.0, (bright_fraction - 0.24) * 180.0)

    h, w = luminance.shape
    yy, xx = np.indices((h, w), dtype=np.float32)
    cx = (0.5 + genome.center_x * 0.42) * (w - 1)
    cy = (0.5 + genome.center_y * 0.42) * (h - 1)
    radius = np.sqrt(((xx - cx) / w) ** 2 + ((yy - cy) / h) ** 2)
    ring = (radius > 0.075) & (radius < 0.24)
    core = radius < 0.065
    ring_separation = 0.0
    if ring.any() and core.any():
        ring_separation = max(0.0, float(luminance[ring].mean() - luminance[core].mean()))

    # colour harmony: the bright subject should read as saturated and vivid, not
    # a muddy grey — a perceptual proxy that rewards a coherent, rich palette.
    rgb = arr / 255.0
    chroma_max = rgb.max(axis=-1)
    chroma_min = rgb.min(axis=-1)
    saturation = (chroma_max - chroma_min) / np.clip(chroma_max, 1e-6, None)
    bright = luminance > np.percentile(luminance, 80)
    color_harmony = float(saturation[bright].mean()) * 100.0 if bright.any() else 0.0

    reasons = {
        "tonal_range": tonal_range,
        "thirds": thirds,
        "focal_balance": focal_balance,
        "busy_penalty": busy_penalty,
        "ring_separation": ring_separation,
        "color_harmony": color_harmony,
    }
    total = (
        tonal_range * 0.42
        + thirds * 0.55
        + focal_balance * 0.24
        + ring_separation * 0.34
        + color_harmony * 0.18
        + busy_penalty
    )
    return ScoreResult(total=float(total), reasons=reasons)

