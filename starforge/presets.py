from __future__ import annotations

from dataclasses import dataclass


Color = tuple[float, float, float]
Stops = tuple[tuple[float, Color], ...]


@dataclass(frozen=True)
class VisualPreset:
    name: str
    title: str
    background_stops: Stops
    disk_stops: Stops
    jet_color: Color
    jet_core: Color
    photon_color: Color
    accent: tuple[int, int, int]
    metadata: tuple[int, int, int]
    bloom_strength: float
    disk_power: float
    jet_power: float
    lensing_strength: float
    star_density: float
    grain: float


PRESETS: dict[str, VisualPreset] = {
    "event-horizon": VisualPreset(
        name="event-horizon",
        title="EVENT HORIZON",
        background_stops=(
            (0.00, (0.004, 0.004, 0.014)),
            (0.32, (0.020, 0.024, 0.060)),
            (0.58, (0.050, 0.040, 0.105)),
            (0.82, (0.150, 0.070, 0.050)),
            (1.00, (0.600, 0.230, 0.070)),
        ),
        disk_stops=(
            (0.00, (0.000, 0.000, 0.000)),
            (0.20, (0.150, 0.040, 0.030)),
            (0.44, (0.950, 0.170, 0.050)),
            (0.70, (1.000, 0.680, 0.200)),
            (1.00, (1.000, 0.980, 0.780)),
        ),
        jet_color=(0.380, 0.820, 0.950),
        jet_core=(0.920, 0.980, 1.000),
        photon_color=(1.000, 0.760, 0.430),
        accent=(255, 112, 58),
        metadata=(159, 216, 228),
        bloom_strength=1.00,
        disk_power=1.05,
        jet_power=0.92,
        lensing_strength=0.155,
        star_density=1.00,
        grain=3.2,
    ),
    "neon-collapse": VisualPreset(
        name="neon-collapse",
        title="STARFORGE",
        background_stops=(
            (0.00, (0.005, 0.006, 0.020)),
            (0.26, (0.015, 0.025, 0.060)),
            (0.48, (0.055, 0.030, 0.115)),
            (0.72, (0.020, 0.115, 0.175)),
            (1.00, (0.500, 0.190, 0.360)),
        ),
        disk_stops=(
            (0.00, (0.000, 0.000, 0.000)),
            (0.18, (0.090, 0.030, 0.150)),
            (0.38, (0.900, 0.120, 0.340)),
            (0.62, (1.000, 0.450, 0.130)),
            (0.82, (1.000, 0.850, 0.420)),
            (1.00, (0.860, 1.000, 1.000)),
        ),
        jet_color=(0.200, 0.850, 1.000),
        jet_core=(0.950, 0.960, 1.000),
        photon_color=(1.000, 0.720, 0.420),
        accent=(255, 126, 72),
        metadata=(164, 212, 230),
        bloom_strength=1.08,
        disk_power=1.12,
        jet_power=1.00,
        lensing_strength=0.175,
        star_density=1.08,
        grain=3.2,
    ),
    "cold-singularity": VisualPreset(
        name="cold-singularity",
        title="COLD SINGULARITY",
        background_stops=(
            (0.00, (0.002, 0.006, 0.016)),
            (0.30, (0.006, 0.030, 0.060)),
            (0.54, (0.020, 0.090, 0.130)),
            (0.78, (0.080, 0.190, 0.240)),
            (1.00, (0.420, 0.800, 0.920)),
        ),
        disk_stops=(
            (0.00, (0.000, 0.000, 0.000)),
            (0.28, (0.020, 0.110, 0.150)),
            (0.52, (0.080, 0.620, 0.860)),
            (0.76, (0.570, 0.940, 1.000)),
            (1.00, (0.960, 1.000, 1.000)),
        ),
        jet_color=(0.400, 0.920, 1.000),
        jet_core=(0.940, 1.000, 1.000),
        photon_color=(0.650, 0.950, 1.000),
        accent=(108, 223, 255),
        metadata=(180, 236, 245),
        bloom_strength=0.90,
        disk_power=0.95,
        jet_power=1.15,
        lensing_strength=0.190,
        star_density=1.22,
        grain=2.7,
    ),
    "solar-wound": VisualPreset(
        name="solar-wound",
        title="SOLAR WOUND",
        background_stops=(
            (0.00, (0.014, 0.004, 0.010)),
            (0.30, (0.080, 0.018, 0.025)),
            (0.54, (0.180, 0.050, 0.035)),
            (0.78, (0.440, 0.130, 0.040)),
            (1.00, (0.900, 0.330, 0.060)),
        ),
        disk_stops=(
            (0.00, (0.000, 0.000, 0.000)),
            (0.20, (0.240, 0.030, 0.020)),
            (0.46, (1.000, 0.170, 0.040)),
            (0.70, (1.000, 0.650, 0.080)),
            (1.00, (1.000, 0.960, 0.540)),
        ),
        jet_color=(1.000, 0.530, 0.180),
        jet_core=(1.000, 0.930, 0.700),
        photon_color=(1.000, 0.600, 0.230),
        accent=(255, 82, 40),
        metadata=(244, 187, 136),
        bloom_strength=1.18,
        disk_power=1.28,
        jet_power=0.72,
        lensing_strength=0.145,
        star_density=0.88,
        grain=3.8,
    ),
    "deep-field": VisualPreset(
        name="deep-field",
        title="DEEP FIELD",
        background_stops=(
            (0.00, (0.004, 0.004, 0.018)),
            (0.25, (0.020, 0.018, 0.052)),
            (0.50, (0.030, 0.044, 0.098)),
            (0.75, (0.070, 0.050, 0.150)),
            (1.00, (0.240, 0.180, 0.380)),
        ),
        disk_stops=(
            (0.00, (0.000, 0.000, 0.000)),
            (0.22, (0.060, 0.030, 0.130)),
            (0.46, (0.420, 0.190, 0.880)),
            (0.72, (0.860, 0.620, 1.000)),
            (1.00, (0.980, 0.920, 1.000)),
        ),
        jet_color=(0.430, 0.540, 1.000),
        jet_core=(0.960, 0.940, 1.000),
        photon_color=(0.900, 0.700, 1.000),
        accent=(174, 116, 255),
        metadata=(198, 188, 240),
        bloom_strength=0.86,
        disk_power=0.90,
        jet_power=0.82,
        lensing_strength=0.215,
        star_density=1.55,
        grain=2.4,
    ),
}

PRESET_NAMES: tuple[str, ...] = tuple(PRESETS)


def get_preset(name: str) -> VisualPreset:
    try:
        return PRESETS[name]
    except KeyError as exc:
        choices = ", ".join(PRESET_NAMES)
        raise ValueError(f"unknown preset '{name}'; choose one of: {choices}") from exc

