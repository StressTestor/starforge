from __future__ import annotations

import numpy as np


def clamp01(values: np.ndarray) -> np.ndarray:
    return np.clip(values, 0.0, 1.0)


def gradient(values: np.ndarray, stops: tuple[tuple[float, tuple[float, float, float]], ...]) -> np.ndarray:
    """Map a scalar field to RGB using linear color stops."""

    source = clamp01(values)
    result = np.zeros((*source.shape, 3), dtype=np.float32)

    for index, (left_pos, left_color) in enumerate(stops[:-1]):
        right_pos, right_color = stops[index + 1]
        span = max(right_pos - left_pos, 1e-6)
        mask = (source >= left_pos) & (source <= right_pos)
        t = ((source - left_pos) / span)[..., None]
        left = np.asarray(left_color, dtype=np.float32)
        right = np.asarray(right_color, dtype=np.float32)
        result = np.where(mask[..., None], left * (1.0 - t) + right * t, result)

    result = np.where((source >= stops[-1][0])[..., None], np.asarray(stops[-1][1], dtype=np.float32), result)
    return result


BACKGROUND_STOPS: tuple[tuple[float, tuple[float, float, float]], ...] = (
    (0.00, (0.005, 0.006, 0.020)),
    (0.26, (0.015, 0.025, 0.060)),
    (0.48, (0.055, 0.030, 0.115)),
    (0.72, (0.020, 0.115, 0.175)),
    (1.00, (0.500, 0.190, 0.360)),
)

DISK_STOPS: tuple[tuple[float, tuple[float, float, float]], ...] = (
    (0.00, (0.000, 0.000, 0.000)),
    (0.18, (0.090, 0.030, 0.150)),
    (0.38, (0.900, 0.120, 0.340)),
    (0.62, (1.000, 0.450, 0.130)),
    (0.82, (1.000, 0.850, 0.420)),
    (1.00, (0.860, 1.000, 1.000)),
)

JET_COLOR = np.asarray((0.200, 0.850, 1.000), dtype=np.float32)
JET_CORE = np.asarray((0.950, 0.960, 1.000), dtype=np.float32)
PHOTON_COLOR = np.asarray((1.000, 0.720, 0.420), dtype=np.float32)

