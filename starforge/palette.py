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

