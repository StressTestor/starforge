from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from starforge.presets import get_preset


@dataclass(frozen=True)
class Genome:
    """Deterministic macro-composition sampled from seed and preset."""

    seed: int
    preset: str
    center_x: float
    center_y: float
    disk_tilt: float
    disk_band_count: int
    disk_thickness: float
    disk_radius: float
    disk_gap: float
    disk_turbulence: float
    jet_angle: float
    jet_width: float
    jet_length: float
    jet_asymmetry: float
    horizon_radius: float
    photon_radius: float
    photon_tightness: float
    lensing_strength: float
    color_temperature: float
    beaming_strength: float
    rotation_direction: int
    background_twist: float

    @classmethod
    def from_seed(cls, seed: int, preset: str) -> "Genome":
        visual = get_preset(preset)
        rng = np.random.default_rng(seed ^ _stable_preset_salt(preset))

        x_sign = -1 if rng.random() < 0.5 else 1
        y_sign = -1 if rng.random() < 0.5 else 1
        center_x = x_sign * float(rng.uniform(0.12, 0.32))
        center_y = y_sign * float(rng.uniform(0.04, 0.24))

        disk_tilt = float(rng.uniform(-0.44, 0.44))
        horizon_radius = float(rng.uniform(0.145, 0.235))
        photon_radius = horizon_radius * float(rng.uniform(1.16, 1.45))
        lensing_strength = float(np.clip(visual.lensing_strength + rng.uniform(-0.045, 0.055), 0.10, 0.30))

        return cls(
            seed=seed,
            preset=preset,
            center_x=center_x,
            center_y=center_y,
            disk_tilt=disk_tilt,
            disk_band_count=int(rng.integers(5, 15)),
            disk_thickness=float(rng.uniform(0.22, 0.42)),
            disk_radius=float(rng.uniform(0.36, 0.56)),
            disk_gap=float(rng.uniform(0.085, 0.155)),
            disk_turbulence=float(rng.uniform(0.65, 1.35)),
            jet_angle=disk_tilt + float(rng.uniform(-0.20, 0.20)),
            jet_width=float(rng.uniform(0.030, 0.060)),
            jet_length=float(rng.uniform(0.74, 1.24)),
            jet_asymmetry=float(rng.uniform(-0.34, 0.34)),
            horizon_radius=horizon_radius,
            photon_radius=photon_radius,
            photon_tightness=float(rng.uniform(0.00022, 0.00072)),
            lensing_strength=lensing_strength,
            color_temperature=float(rng.uniform(-0.18, 0.18)),
            beaming_strength=float(rng.uniform(0.42, 0.92)),
            rotation_direction=-1 if rng.random() < 0.5 else 1,
            background_twist=float(rng.uniform(-1.8, 1.8)),
        )

    def to_manifest(self) -> dict[str, float | int | str]:
        data = asdict(self)
        for key, value in list(data.items()):
            if isinstance(value, float):
                data[key] = round(value, 6)
        return data


def _stable_preset_salt(preset: str) -> int:
    value = 0
    for char in preset.encode("utf-8"):
        value = (value * 131 + char) & 0xFFFFFFFF
    return value

