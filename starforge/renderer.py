from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from starforge.config import RenderConfig
from starforge.genome import Genome
from starforge.lensing import (
    _bilinear_sample_f,
    apply_gravitational_lensing,
    build_deflection_lut,
    build_disk_fold_map,
    build_einstein_lens_map,
    lensing_spin_for_phase,
    sample_emergent_ring,
)
from starforge.palette import (
    clamp01,
    gradient,
)
from starforge.presets import get_preset


@dataclass(frozen=True)
class _SourceGalaxy:
    """A background source galaxy for the lensed-galaxy subject. The gaussian
    ``blob`` profile is frame-invariant (precomputed once); only ``twinkle_phase``
    drives the per-frame brightness so the animation stays a seamless loop."""

    blob: np.ndarray
    color: np.ndarray  # (3,) rgb already scaled by brightness
    twinkle_phase: float


class StarforgeRenderer:
    """Render deterministic poster and animation frames for a gravitational-
    lensing subject (black-hole or lensed-galaxy)."""

    def __init__(self, config: RenderConfig) -> None:
        self.config = config
        self.preset = get_preset(config.preset)
        self.genome = Genome.from_seed(config.seed, config.preset, config.subject)
        self._x, self._y = self._coordinate_grid(config.width, config.height, config.aspect)
        self._gx = self._x - self.genome.center_x
        self._gy = self._y - self.genome.center_y
        self._radius = np.sqrt(self._gx**2 + self._gy**2)
        self._theta = np.arctan2(self._gy, self._gx)
        # frame-centered radius drives the vignette so the frame darkens at the
        # image edges regardless of where the (off-center) subject sits — a
        # deliberate framing choice, not a side effect of the subject radius.
        self._frame_radius = np.sqrt(self._x**2 + self._y**2)
        self._vignette_mul = clamp01(1.18 - self._frame_radius * 0.55)[..., None].astype(np.float32)
        if self.genome.subject == "lensed-galaxy":
            self._build_galaxy()
        else:
            self._build_lensing()

    # The disk's secondary image (over-shadow arc + under-curl) is the disk's own
    # emission re-gathered through a precomputed gravitational fold; the photon
    # ring emerges from the deflection divergence. All frame-invariant.
    _B_MAX = 1.8
    _ARC_BAND = 0.07
    _TOP_ARC_BRIGHTNESS = 1.7
    _BOTTOM_ARC_BRIGHTNESS = 0.7
    # photon-ring sharpening: exponent = base + gain / photon_tightness. With the
    # genome's tightness range (~0.0002..0.0007) this gives a ~1.7..3.0 exponent —
    # tighter rings get a crisper falloff.
    _RING_SHARPEN_BASE = 1.15
    _RING_SHARPEN_GAIN = 0.0004
    _RING_BRIGHTNESS = 1.55

    def _build_lensing(self) -> None:
        g = self.genome
        # primary disk: inclined projected ellipse (disk_thickness == cos i),
        # in the tilt-rotated frame. Frame-invariant coordinates.
        xr, yr = self._rotated(g.disk_tilt)
        disk_y = yr / g.disk_thickness
        self._flat_disk_radius = np.sqrt(xr**2 + disk_y**2).astype(np.float32)
        self._flat_disk_theta = np.arctan2(disk_y, xr).astype(np.float32)

        # emergent photon ring from the strong-deflection divergence
        self._luts = build_deflection_lut(g.photon_radius, g.lensing_strength, b_max=self._B_MAX)
        self._ring_field = sample_emergent_ring(self._radius, self._luts, b_max=self._B_MAX)

        # gravitational fold: far side -> arc over the top, dim curl beneath
        self._fold = build_disk_fold_map(
            self.config.width,
            self.config.height,
            center_x=g.center_x,
            center_y=g.center_y,
            orientation=g.disk_tilt,
            disk_radius=g.disk_radius,
            disk_thickness=g.disk_thickness,
            horizon_radius=g.horizon_radius,
            photon_radius=g.photon_radius,
            arc_band=self._ARC_BAND,
        )

        # frame-invariant masks — depend only on geometry, so cache them once
        # rather than recomputing every animation frame.
        beam = 1.0 + 0.25 * g.beaming_strength * g.rotation_direction * np.cos(self._theta - g.disk_tilt)
        self._arc_beam = beam[..., None].astype(np.float32)
        disk_shadow = np.exp(-(self._radius**2) / (g.horizon_radius * 0.5))
        self._disk_shadow_mul = (1.0 - disk_shadow * 0.82)[..., None].astype(np.float32)
        horizon = clamp01(1.0 - np.exp(-((self._radius / g.horizon_radius) ** 8)))
        self._gravity_well = clamp01(0.35 + 0.65 * horizon)[..., None].astype(np.float32)

        # the smoothed disk (braids flattened) is the gather source for the
        # secondary arc; it has no phase dependence, so build it once here.
        self._smooth_disk = self._disk_emission(self._flat_disk_radius, self._flat_disk_theta, 0.0, smooth=True)

    # ---- lensed-galaxy subject ----------------------------------------------
    _EINSTEIN_BASE = 0.27  # baseline Einstein radius, nudged by lensing_strength
    _BG_GALAXY_COUNT = 8  # background source galaxies beyond the main lensed one
    # separate RNG stream for galaxy structure, so it never advances the locked
    # black-hole draw order (the genome stays byte-identical across subjects).
    _GALAXY_RNG_STREAM = 0x6A17

    def _build_galaxy(self) -> None:
        """Frame-invariant setup for the lensed-galaxy subject: a singular-
        isothermal-sphere lens (reusing the single-center machinery) plus a
        deterministic set of background source galaxies with precomputed gaussian
        profiles."""
        g = self.genome
        rng = np.random.default_rng([self.config.seed, self._GALAXY_RNG_STREAM])
        self._einstein_radius = float(
            np.clip(self._EINSTEIN_BASE + g.lensing_strength * 0.5 + rng.uniform(-0.03, 0.05), 0.20, 0.42)
        )
        ellipticity = float(rng.uniform(0.06, 0.24))
        ellipticity_angle = float(g.disk_tilt * 2.0 + rng.uniform(-0.4, 0.4))
        self._lens_map = build_einstein_lens_map(
            self.config.width,
            self.config.height,
            center_x=g.center_x,
            center_y=g.center_y,
            einstein_radius=self._einstein_radius,
            ellipticity=ellipticity,
            ellipticity_angle=ellipticity_angle,
        )

        # all galaxy RNG draws happen here, in one visible order, so the field is
        # reproducible and a reader can see exactly what consumes the stream.
        source_tint = np.asarray(self.preset.photon_color, dtype=np.float32)
        galaxies: list[_SourceGalaxy] = []

        # main source: just behind the lens (small offset -> arcs, not a ring)
        off_angle = float(rng.uniform(0.0, math.tau))
        off_r = float(rng.uniform(0.02, 0.08))
        main_size = float(rng.uniform(0.038, 0.060))
        main_q = float(rng.uniform(0.4, 0.95))
        main_angle = float(rng.uniform(0.0, math.tau))
        main_twinkle = float(rng.uniform(0.0, math.tau))
        galaxies.append(
            self._make_source_galaxy(
                nx=off_r * math.cos(off_angle), ny=off_r * math.sin(off_angle),
                size=main_size, q=main_q, angle=main_angle,
                color=np.asarray(0.5 + 0.5 * source_tint, dtype=np.float32) * 1.5,
                twinkle_phase=main_twinkle,
            )
        )

        # scattered background sources, lensed into weaker arcs
        for _ in range(self._BG_GALAXY_COUNT):
            ang = float(rng.uniform(0.0, math.tau))
            rad = float(rng.uniform(0.45, 1.25))
            hue = float(rng.uniform(0.0, 1.0))
            size = float(rng.uniform(0.03, 0.07))
            bright = float(rng.uniform(0.28, 0.65))
            q = float(rng.uniform(0.4, 0.95))
            angle = float(rng.uniform(0.0, math.tau))
            twinkle = float(rng.uniform(0.0, math.tau))
            galaxies.append(
                self._make_source_galaxy(
                    nx=rad * math.cos(ang), ny=rad * math.sin(ang),
                    size=size, q=q, angle=angle,
                    color=np.asarray((0.62 + 0.32 * hue, 0.70, 1.0 - 0.28 * hue), dtype=np.float32) * bright,
                    twinkle_phase=twinkle,
                )
            )
        self._galaxies = galaxies
        self._lens_glow_color = np.asarray((1.0, 0.80, 0.52), dtype=np.float32)

    def _make_source_galaxy(
        self, *, nx: float, ny: float, size: float, q: float, angle: float, color: np.ndarray, twinkle_phase: float
    ) -> _SourceGalaxy:
        # pure: no RNG. builds the frame-invariant elliptical gaussian profile.
        ca, sa = math.cos(angle), math.sin(angle)
        rx = (self._gx - nx) * ca + (self._gy - ny) * sa
        ry = -(self._gx - nx) * sa + (self._gy - ny) * ca
        d2 = rx**2 + (ry / max(q, 0.2)) ** 2
        blob = np.exp(-d2 / (size**2)).astype(np.float32)
        return _SourceGalaxy(blob=blob, color=np.asarray(color, dtype=np.float32), twinkle_phase=twinkle_phase)

    def _galaxy_source_plane(self, phase: float) -> np.ndarray:
        # the blobs are frame-invariant; only the scalar twinkle animates.
        src = np.zeros((self.config.height, self.config.width, 3), dtype=np.float32)
        for gal in self._galaxies:
            twinkle = 0.82 + 0.18 * math.sin(phase * math.tau + gal.twinkle_phase)
            src += gal.blob[..., None] * gal.color * twinkle
        return src

    def _lens_galaxy_glow(self) -> np.ndarray:
        # foreground lens galaxy: a warm elliptical glow at the lens center
        e = self._einstein_radius
        core = np.exp(-(self._radius**2) / (0.45 * e**2))
        halo = 0.35 * np.exp(-self._radius / (0.7 * e))
        return (core + halo)[..., None] * self._lens_glow_color * 0.45

    def _render_galaxy_frame(self, phase: float, frame_index: int, include_title: bool) -> Image.Image:
        rng = np.random.default_rng(self.config.seed + frame_index * 1009)
        source = self._galaxy_source_plane(phase)
        sx, sy = self._lens_map.src
        mag = self._lens_map.magnification[..., None]
        lensed = _bilinear_sample_f(source, sx, sy) * (0.45 + 0.55 * mag)

        backdrop = self._background_field(phase) * 0.45
        glow = self._lens_galaxy_glow()
        stars = self._star_field(rng)

        rgb = backdrop + lensed + glow + stars
        rgb = self._temperature_shift(rgb, amount=0.3)
        rgb = self._add_vignette(rgb)
        return self._finish_frame(self._to_image(rgb), rng, include_title)

    def _finish_frame(self, image: Image.Image, rng: np.random.Generator, include_title: bool) -> Image.Image:
        """Shared post-processing tail for both subjects: bloom, pinprick stars,
        film grain, and the optional title overlay."""
        image = self._add_bloom(image)
        image = self._add_pinprick_stars(image, rng)
        image = self._add_grain(image, rng)
        if include_title:
            image = self._add_title(image)
        return image

    def render_poster(self, *, include_title: bool = True) -> Image.Image:
        if self.config.supersample > 1:
            high_config = RenderConfig(
                width=self.config.width * self.config.supersample,
                height=self.config.height * self.config.supersample,
                seed=self.config.seed,
                frames=self.config.frames,
                title=self.config.title,
                preset=self.config.preset,
                subject=self.config.subject,
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
        if self.genome.subject == "lensed-galaxy":
            return self._render_galaxy_frame(phase, frame_index, include_title)
        return self._render_blackhole_frame(phase, frame_index, include_title)

    def _render_blackhole_frame(self, phase: float, frame_index: int, include_title: bool) -> Image.Image:
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
        return self._finish_frame(self._to_image(rgb), rng, include_title)

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

    def _disk_emission(
        self, disk_radius: np.ndarray, disk_theta: np.ndarray, phase: float, *, smooth: bool = False
    ) -> np.ndarray:
        """Pure accretion-disk texture as a function of plane radius and azimuth.

        Shared by the primary disk and the lensed secondary arc. ``smooth=True``
        flattens the braided/wake spokes so the secondary reads as a clean
        wrapped arc instead of a radial spray of the disk's braids.
        """
        g = self.genome
        main = np.exp(-((disk_radius - g.disk_radius) ** 2) / (0.008 + g.disk_thickness * 0.010))
        outer = 0.55 * np.exp(-((disk_radius - (g.disk_radius + g.disk_gap)) ** 2) / 0.030)
        inner = 0.90 * np.exp(-((disk_radius - max(0.18, g.disk_radius - g.disk_gap)) ** 2) / 0.006)

        if smooth:
            braided = 1.0
            wake = 1.0
        else:
            braided = 0.62 + 0.38 * np.sin(
                disk_theta * g.disk_band_count
                - disk_radius * (18.0 + 8.0 * g.disk_turbulence)
                + phase * math.tau * 2.0
            )
            xr = disk_radius * np.cos(disk_theta)
            yr = disk_radius * np.sin(disk_theta) * g.disk_thickness
            wake = 0.70 + 0.30 * np.sin(
                xr * (30.0 + 10.0 * g.disk_turbulence) + yr * 16.0 - phase * math.tau * 1.6
            )
        velocity = g.rotation_direction * np.cos(disk_theta)
        approaching = np.clip(velocity, 0.0, 1.0)
        receding = np.clip(-velocity, 0.0, 1.0)
        beaming = 1.0 + g.beaming_strength * approaching**1.7 - 0.18 * receding
        intensity = clamp01((main + outer + inner) * braided * wake * beaming)

        return (
            self._temperature_shift(gradient(intensity, self.preset.disk_stops), amount=1.0)
            * intensity[..., None]
            * 1.75
            * self.preset.disk_power
        )

    def _accretion_disk(self, phase: float) -> np.ndarray:
        """Inclined accretion disk plus its gravitationally lensed secondary
        image. The far side, re-gathered through the precomputed fold, arcs over
        the top of the shadow; a dimmer copy curls beneath. The arcs are the
        disk's own emission, so colour and texture stay consistent."""
        primary = self._disk_emission(self._flat_disk_radius, self._flat_disk_theta, phase)

        sx_top, sy_top = self._fold.src_top
        sx_bot, sy_bot = self._fold.src_bot
        arc_top = _bilinear_sample_f(self._smooth_disk, sx_top, sy_top) * self._fold.w_top[..., None]
        arc_bot = _bilinear_sample_f(self._smooth_disk, sx_bot, sy_bot) * self._fold.w_bot[..., None]
        # the gathered arc already carries the disk-frame Doppler beaming baked
        # into _smooth_disk; _arc_beam is a SECOND, image-space highlight applied
        # only to the top arc so its bright side lines up with the approaching
        # rim. Two intentional, distinct weightings, not an accident.
        secondary = arc_top * self._TOP_ARC_BRIGHTNESS * self._arc_beam + arc_bot * self._BOTTOM_ARC_BRIGHTNESS

        # _disk_shadow_mul keeps the darkening confined to the captured shadow so
        # it does not bleed into and dim the over-shadow arc that hugs the rim.
        return (primary + secondary) * self._disk_shadow_mul

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
        """Photon ring that EMERGES from the deflection piling up at the photon
        sphere, rather than a hand-drawn gaussian. The raw log-divergence from
        the LUT is normalized and sharpened; photon_tightness trims its width."""
        ring = self._ring_field
        ring = ring / max(float(ring.max()), 1e-6)
        sharpen = self._RING_SHARPEN_BASE + self._RING_SHARPEN_GAIN / max(self.genome.photon_tightness, 1e-5)
        ring = np.clip(ring, 0.0, 1.0) ** sharpen
        return ring[..., None] * np.asarray(self.preset.photon_color, dtype=np.float32) * self._RING_BRIGHTNESS

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
        return rgb * self._gravity_well

    def _add_vignette(self, rgb: np.ndarray) -> np.ndarray:
        floor = np.asarray((0.004, 0.004, 0.016), dtype=np.float32)
        return rgb * self._vignette_mul + floor

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
        descriptor = (
            "GRAVITATIONAL LENSING  /  EINSTEIN RING"
            if self.genome.subject == "lensed-galaxy"
            else "GRAVITATIONAL DISK LENSING"
        )
        strip = f"STARFORGE LAB V5  /  {descriptor}"

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
