from __future__ import annotations

import numpy as np

from starforge.lensing import (
    build_deflection_lut,
    build_disk_fold_map,
    sample_emergent_ring,
)


def test_deflection_diverges_near_photon_sphere_and_is_zero_inside() -> None:
    b_ph = 0.22
    bb, alpha, ring, wt = build_deflection_lut(b_ph, lensing_strength=0.18, n=4096, b_max=1.8)

    just_outside = np.argmin(np.abs(bb - b_ph * 1.02))
    far = np.argmin(np.abs(bb - b_ph * 4.0))

    # bending is strong just outside the photon sphere and weak far away
    assert alpha[just_outside] > alpha[far] * 3.0
    # the emergent ring peaks just outside the photon sphere ...
    assert ring[just_outside] > ring[far]
    # ... and is exactly zero inside it, so the captured shadow stays dark
    assert float(ring[bb < b_ph].max()) == 0.0
    assert np.isfinite(alpha).all() and np.isfinite(ring).all()


def test_emergent_ring_peaks_outside_photon_sphere() -> None:
    b_ph = 0.2
    luts = build_deflection_lut(b_ph, 0.18, b_max=1.8)
    bb = luts[0]
    radius = bb.copy()
    ring = sample_emergent_ring(radius, luts, b_max=1.8)
    peak_b = bb[int(np.argmax(ring))]
    assert peak_b >= b_ph


def test_fold_map_is_deterministic() -> None:
    a = build_disk_fold_map(
        120, 160, center_x=0.1, center_y=-0.05, orientation=0.2,
        disk_radius=0.44, disk_thickness=0.3, horizon_radius=0.18, photon_radius=0.24,
    )
    b = build_disk_fold_map(
        120, 160, center_x=0.1, center_y=-0.05, orientation=0.2,
        disk_radius=0.44, disk_thickness=0.3, horizon_radius=0.18, photon_radius=0.24,
    )
    assert np.array_equal(a.w_top, b.w_top)
    assert np.array_equal(a.src_top[0], b.src_top[0])


def test_over_arc_sits_in_top_half_and_windows_are_disjoint() -> None:
    # the load-bearing "over the shadow" invariant: the top-arc window's
    # intensity-weighted centroid row must land in the TOP half of the image,
    # for both tilt signs, with no overlap against the under-curl window.
    for orientation in (0.3, -0.3, 0.05):
        fold = build_disk_fold_map(
            200, 260, center_x=0.0, center_y=0.0, orientation=orientation,
            disk_radius=0.45, disk_thickness=0.3, horizon_radius=0.18, photon_radius=0.24,
        )
        w_top = fold.w_top
        w_bot = fold.w_bot
        rows = np.indices(w_top.shape)[0]
        top_centroid = float((rows * w_top).sum() / max(w_top.sum(), 1e-6)) / w_top.shape[0]
        bot_centroid = float((rows * w_bot).sum() / max(w_bot.sum(), 1e-6)) / w_bot.shape[0]
        assert top_centroid < 0.5, f"top arc not over shadow (centroid {top_centroid})"
        assert bot_centroid > 0.5, f"under-curl not beneath shadow (centroid {bot_centroid})"
        # disjoint hemispheres
        assert float((w_top * w_bot).max()) < 1e-3
