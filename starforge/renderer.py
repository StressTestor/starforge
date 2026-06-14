from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from starforge.config import RenderConfig
from starforge.genome import Genome
from starforge.lensing import apply_gravitational_lensing, lensing_spin_for_phase
from starforge.palette import (
    clamp01,
    gradient,
)
from starforge.presets import get_preset


class StarforgeRenderer:
    """Render deterministic black-hole poster and animation frames."""

    def __init__(self, config: RenderConfig) -> None:
        self.config = config
        self.preset = get_preset(config.preset)
        self.genome = Genome.from_seed(config.seed, config.preset)
        self._x, self._y = self._coordinate_grid(config.width, config.height, config.aspect)
        self._gx = self._x - self.genome.center_x
        self._gy = self._y - self.genome.center_y
        self._radius = np.sqrt(self._gx**2 + self._gy**2)
        self._theta = np.arctan2(self._gy, self._gx)

    def render_poster(self, *, include_title: bool = True) -> Image.Image:
        if self.config.supersample > 1:
            high_config = RenderConfig(
                width=self.config.width * self.config.supersample,
                height=self.config.height * self.config.supersample,
                seed=self.config.seed,
                frames=self.config.frames,
                title=self.config.title,
                preset=self.config.preset,
                supersample=1,
            )
            high = StarforgeRenderer(high_config).render_poster(include_title=False)
            downsampled = high.resize((self.config.width, self.config.height), Image.Resampling.LANCZOS)
            return self._add_title(downsampled) if include_title else downsampled

        image = self._render_frame(phase=0.12, frame_index=0, include_title=include_title)
        return image

    def render_animation_frames(self) -> list[Image.Image]:
        frames: list[Image.Image] = []
        for index in range(self.config.frames):
            phase = index / self.config.frames
            frames.append(self._render_frame(phase=phase, frame_index=index, include_title=False))
        return frames

    def _render_frame(self, phase: float, frame_index: int, include_title: bool) -> Image.Image:
        rng = np.random.default_rng(self.config.seed + frame_index * 1009)
        background = self._background_field(phase) + self._star_field(rng)
        background = self._add_vignette(background)
        lensed = apply_gravitational_lensing(
            self._to_image(background),
            strength=self.genome.lensing_strength,
            event_horizon=self.genome.horizon_radius,
            spin=lensing_spin_for_phase(phase) * self.genome.rotation_direction,
            center_x=self.genome.center_x,
            center_y=self.genome.center_y,
        )
        lensed_background = np.asarray(lensed, dtype=np.float32) / 255.0

        disk = self._accretion_disk(phase)
        jets = self._relativistic_jets(phase)
        photon = self._photon_ring()

        rgb = lensed_background + disk + jets + photon
        rgb = self._carve_event_horizon(rgb)
        rgb = self._add_vignette(rgb)
        image = self._to_image(rgb)
        image = self._add_bloom(image)
        image = self._add_pinprick_stars(image, rng)
        image = self._add_grain(image, rng)

        if include_title:
            image = self._add_title(image)

        return image

    @staticmethod
    def _coordinate_grid(width: int, height: int, aspect: float) -> tuple[np.ndarray, np.ndarray]:
        x = np.linspace(-1.0, 1.0, width, dtype=np.float32) * aspect
        y = np.linspace(-1.0, 1.0, height, dtype=np.float32)
        return np.meshgrid(x, y)

    def _background_field(self, phase: float) -> np.ndarray:
        wave_a = np.sin(3.2 * self._x - 1.8 * self._y + phase * math.tau + self.genome.background_twist)
        wave_b = np.cos(2.5 * self._x + 3.8 * self._y - phase * math.tau * 0.7 - self.genome.center_x * 2.4)
        spiral = np.sin(self._theta * 3.0 + self._radius * (8.0 + self.genome.disk_turbulence * 2.5) - phase * math.tau)
        field = 0.42 + 0.18 * wave_a + 0.13 * wave_b + 0.22 * spiral
        field *= np.exp(-self._radius * 0.85)
        field += 0.16 * np.exp(-((self._x + 0.52 + self.genome.center_x * 0.8) ** 2 + (self._y - 0.22) ** 2) / 0.16)
        field += 0.11 * np.exp(-((self._x - 0.55) ** 2 + (self._y + 0.34 - self.genome.center_y * 0.7) ** 2) / 0.22)
        return self._temperature_shift(gradient(clamp01(field), self.preset.background_stops), amount=0.45)

    def _accretion_disk(self, phase: float) -> np.ndarray:
        xr, yr = self._rotated(self.genome.disk_tilt)
        disk_y = yr / self.genome.disk_thickness
        disk_radius = np.sqrt(xr**2 + disk_y**2)
        disk_theta = np.arctan2(disk_y, xr)

        main = np.exp(-((disk_radius - self.genome.disk_radius) ** 2) / (0.008 + self.genome.disk_thickness * 0.010))
        outer = 0.55 * np.exp(-((disk_radius - (self.genome.disk_radius + self.genome.disk_gap)) ** 2) / 0.030)
        inner = 0.90 * np.exp(-((disk_radius - max(0.18, self.genome.disk_radius - self.genome.disk_gap)) ** 2) / 0.006)

        braided = 0.62 + 0.38 * np.sin(
            disk_theta * self.genome.disk_band_count
            - disk_radius * (18.0 + 8.0 * self.genome.disk_turbulence)
            + phase * math.tau * 2.0
        )
        wake = 0.70 + 0.30 * np.sin(
            xr * (30.0 + 10.0 * self.genome.disk_turbulence)
            + yr * 16.0
            - phase * math.tau * 1.6
        )
        velocity = self.genome.rotation_direction * np.cos(disk_theta)
        approaching = np.clip(velocity, 0.0, 1.0)
        receding = np.clip(-velocity, 0.0, 1.0)
        beaming = 1.0 + self.genome.beaming_strength * approaching**1.7 - 0.18 * receding
        intensity = clamp01((main + outer + inner) * braided * wake * beaming)

        disk = self._temperature_shift(gradient(intensity, self.preset.disk_stops), amount=1.0) * intensity[..., None] * 1.75 * self.preset.disk_power
        shadow = np.exp(-(self._radius**2) / (self.genome.horizon_radius * 1.28))
        return disk * (1.0 - shadow[..., None] * 0.72)

    def _relativistic_jets(self, phase: float) -> np.ndarray:
        xj, yj = self._rotated(self.genome.jet_angle + math.pi / 2.0)
        wavering_x = xj + 0.020 * np.sin(yj * 11.0 + phase * math.tau + self.genome.background_twist)
        side_gain = np.where(yj >= 0.0, 1.0 + self.genome.jet_asymmetry, 1.0 - self.genome.jet_asymmetry * 0.65)
        side_length = np.where(yj >= 0.0, self.genome.jet_length, self.genome.jet_length * (1.0 - self.genome.jet_asymmetry * 0.35))
        shaft = np.exp(-(wavering_x**2) / (self.genome.jet_width**2)) * np.exp(-np.abs(yj) / side_length)
        core = np.exp(-(wavering_x**2) / max(self.genome.jet_width**2 * 0.18, 0.00008)) * np.exp(-np.abs(yj) / (side_length * 0.72))
        taper = clamp01((np.abs(yj) - self.genome.horizon_radius * 0.32) * 2.6)
        flicker = 0.72 + 0.28 * np.sin(np.abs(self._y) * 26.0 - phase * math.tau * 2.5)
        jet_color = np.asarray(self.preset.jet_color, dtype=np.float32)
        jet_core = np.asarray(self.preset.jet_core, dtype=np.float32)
        return ((shaft * flicker * taper * side_gain)[..., None] * jet_color + (core * taper * side_gain)[..., None] * jet_core) * 0.75 * self.preset.jet_power

    def _photon_ring(self) -> np.ndarray:
        ring = np.exp(-((self._radius - self.genome.photon_radius) ** 2) / self.genome.photon_tightness)
        halo = 0.50 * np.exp(-((self._radius - (self.genome.photon_radius + 0.045)) ** 2) / 0.0033)
        return (ring + halo)[..., None] * np.asarray(self.preset.photon_color, dtype=np.float32)

    def _star_field(self, rng: np.random.Generator) -> np.ndarray:
        random_field = rng.random((self.config.height, self.config.width), dtype=np.float32)
        threshold = 1.0 - 0.0025 * self.preset.star_density
        sparse = random_field > threshold
        bright = np.zeros_like(random_field)
        bright[sparse] = (random_field[sparse] - threshold) / max(1.0 - threshold, 1e-6)
        bright *= 0.55 + 0.45 * rng.random((self.config.height, self.config.width), dtype=np.float32)

        color_jitter = rng.random((self.config.height, self.config.width, 3), dtype=np.float32)
        colors = np.asarray((0.72, 0.84, 1.00), dtype=np.float32) + color_jitter * np.asarray((0.28, 0.18, 0.06), dtype=np.float32)
        xr, yr = self._rotated(self.genome.disk_tilt)
        dust_lane = clamp01(1.0 - np.exp(-((yr * 4.0 + 0.24 * np.sin(xr * 4.0)) ** 2) / 0.50))
        return bright[..., None] * colors * dust_lane[..., None]

    def _carve_event_horizon(self, rgb: np.ndarray) -> np.ndarray:
        horizon = clamp01(1.0 - np.exp(-((self._radius / self.genome.horizon_radius) ** 8)))
        gravity_well = clamp01(0.35 + 0.65 * horizon)
        return rgb * gravity_well[..., None]

    def _add_vignette(self, rgb: np.ndarray) -> np.ndarray:
        vignette = clamp01(1.18 - self._radius * 0.55)
        floor = np.asarray((0.004, 0.004, 0.016), dtype=np.float32)
        return rgb * vignette[..., None] + floor

    @staticmethod
    def _to_image(rgb: np.ndarray) -> Image.Image:
        tonemapped = 1.0 - np.exp(-clamp01(rgb) * 1.45)
        arr = np.asarray(clamp01(tonemapped) * 255.0, dtype=np.uint8)
        return Image.fromarray(arr, mode="RGB")

    def _add_bloom(self, image: Image.Image) -> Image.Image:
        bright = image.point(lambda value: max(0, value - 135) * 2)
        bloom_large = bright.filter(ImageFilter.GaussianBlur(radius=max(2, image.size[0] // 85)))
        bloom_small = bright.filter(ImageFilter.GaussianBlur(radius=max(1, image.size[0] // 220)))
        combined = Image.blend(image, ImageChops.screen(image, bloom_large), 0.34 * self.preset.bloom_strength)
        return Image.blend(combined, ImageChops.screen(combined, bloom_small), 0.20 * self.preset.bloom_strength)

    def _add_pinprick_stars(self, image: Image.Image, rng: np.random.Generator) -> Image.Image:
        draw = ImageDraw.Draw(image)
        width, height = image.size
        count = max(32, (width * height) // 18500)

        for _ in range(count):
            x = int(rng.integers(0, width))
            y = int(rng.integers(0, height))
            if abs(x - width / 2) < width * 0.11 and abs(y - height / 2) < height * 0.11:
                continue
            radius = int(rng.choice([1, 1, 1, 2]))
            color = tuple(int(v) for v in rng.integers(180, 256, size=3))
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
            if rng.random() > 0.82:
                draw.line((x - radius * 3, y, x + radius * 3, y), fill=color)
                draw.line((x, y - radius * 3, x, y + radius * 3), fill=color)

        return image

    def _add_grain(self, image: Image.Image, rng: np.random.Generator) -> Image.Image:
        arr = np.asarray(image, dtype=np.int16)
        grain = rng.normal(0.0, self.preset.grain, size=arr.shape)
        arr = np.clip(arr + grain, 0, 255).astype(np.uint8)
        return Image.fromarray(arr, mode="RGB")

    def _add_title(self, image: Image.Image) -> Image.Image:
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        width, height = image.size

        title_font = self._font(size=max(24, width // 13), bold=True)
        small_font = self._font(size=max(12, width // 48), bold=False)
        micro_font = self._font(size=max(10, width // 70), bold=False)
        margin = max(28, width // 22)
        title = self.preset.title if self.config.title == "STARFORGE" else self.config.title
        subtitle = f"seed {self.config.seed} // preset {self.config.preset} // tilt {self.genome.disk_tilt:+.2f} // lensing {self.genome.lensing_strength:.3f}"
        strip = "STARFORGE LAB V3  /  SEEDED STRUCTURAL GENOME  /  BILINEAR LENSING  /  FFMPEG LOOP READY"

        title_box = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_box[2] - title_box[0]
        title_y = height - margin - max(84, width // 12)
        draw.text((margin, title_y), title, font=title_font, fill=(235, 248, 255, 230))
        draw.rectangle((margin, title_y - 12, margin + title_width, title_y - 8), fill=(*self.preset.accent, 220))
        draw.text((margin + 3, title_y + max(36, width // 15)), subtitle, font=small_font, fill=(*self.preset.metadata, 215))

        strip_y = margin
        draw.line((margin, strip_y, width - margin, strip_y), fill=(*self.preset.accent, 160), width=max(1, width // 700))
        draw.text((margin, strip_y + 11), strip, font=micro_font, fill=(190, 218, 226, 178))
        draw.text(
            (width - margin - max(170, width // 7), strip_y + 11),
            f"{width}x{height}",
            font=micro_font,
            fill=(*self.preset.metadata, 178),
        )

        return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

    def _rotated(self, angle: float) -> tuple[np.ndarray, np.ndarray]:
        c = math.cos(angle)
        s = math.sin(angle)
        return self._gx * c + self._gy * s, -self._gx * s + self._gy * c

    def _temperature_shift(self, rgb: np.ndarray, *, amount: float) -> np.ndarray:
        temp = self.genome.color_temperature * amount
        factors = np.asarray((1.0 + temp * 0.48, 1.0 + abs(temp) * 0.10, 1.0 - temp * 0.42), dtype=np.float32)
        return clamp01(rgb * factors)

    @staticmethod
    def _font(size: int, bold: bool) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        candidates = (
            "/System/Library/Fonts/Supplemental/Avenir Next.ttc",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
        )
        for path in candidates:
            if Path(path).exists():
                try:
                    return ImageFont.truetype(path, size=size)
                except OSError:
                    continue
        return ImageFont.load_default(size=size)
