from __future__ import annotations

import pytest
from PIL import Image

from starforge.studio import StudioCandidate, build_studio_page


def _cand(subject, preset, seed, tonal, thirds, focal, ring, color, busy, rgb) -> StudioCandidate:
    return StudioCandidate(
        subject=subject,
        preset=preset,
        seed=seed,
        raw_total=tonal * 0.42 + thirds * 0.55 + focal * 0.24 + ring * 0.34 + color * 0.18 + busy,
        reasons={
            "tonal_range": tonal,
            "thirds": thirds,
            "focal_balance": focal,
            "ring_separation": ring,
            "color_harmony": color,
            "busy_penalty": busy,
        },
        image=Image.new("RGB", (24, 33), rgb),
    )


CANDIDATES = [
    _cand("black-hole", "event-horizon", 1, 200, 70, 78, 50, 33, 0, (200, 120, 40)),
    _cand("black-hole", "neon-collapse", 2, 195, 68, 60, 20, 30, 0, (180, 40, 120)),
    _cand("black-hole", "cold-singularity", 3, 190, 60, 45, 10, 28, -5, (120, 160, 220)),
    _cand("lensed-galaxy", "deep-field", 4, 85, 76, 74, 40, 44, 0, (150, 120, 200)),
    _cand("lensed-galaxy", "solar-wound", 5, 70, 55, 50, 12, 30, -8, (200, 90, 60)),
]


def test_build_studio_page_has_structure_and_embedded_images() -> None:
    html = build_studio_page(CANDIDATES)
    assert html.startswith("<!doctype html>")
    assert "data:image/png;base64," in html  # images embedded, self-contained
    # one card per candidate, each carrying its key
    for c in CANDIDATES:
        assert f'data-key="{c.key}"' in html
    assert html.count('class="card"') == len(CANDIDATES)
    # the interaction surface exists
    assert 'id="export"' in html and 'id="sort"' in html and 'id="frontier"' in html
    assert "★ frontier" in html  # at least one non-dominated candidate is flagged


def test_studio_is_deterministic() -> None:
    assert build_studio_page(CANDIDATES) == build_studio_page(CANDIDATES)


def test_studio_default_order_is_debiased_not_subject_bucketed() -> None:
    html = build_studio_page(CANDIDATES)
    # the best galaxy (seed 4) should appear before the weakest black hole (seed 3)
    # in document order — the raw scalar would bucket all black holes first.
    pos_galaxy = html.index('data-key="lensed-galaxy:deep-field:4"')
    pos_weak_bh = html.index('data-key="black-hole:cold-singularity:3"')
    assert pos_galaxy < pos_weak_bh


def test_studio_rejects_empty() -> None:
    with pytest.raises(ValueError):
        build_studio_page([])


def test_studio_page_renders_studio_curator_metrics() -> None:
    # regression: the studio curator's reasons (subject_focus/detail) used to crash
    # the bars (which hardcoded the heuristic metric set). They must render now.
    def cand(subject, preset, seed, sf, det, th, fb, ch, bp, rgb) -> StudioCandidate:
        return StudioCandidate(
            subject=subject, preset=preset, seed=seed, raw_total=sf + det + th,
            reasons={"subject_focus": sf, "detail": det, "thirds": th, "focal_balance": fb, "color_harmony": ch, "busy_penalty": bp},
            image=Image.new("RGB", (20, 28), rgb),
        )

    cands = [
        cand("black-hole", "event-horizon", 1, 80, 30, 70, 60, 40, 0, (200, 120, 40)),
        cand("wormhole", "solar-wound", 2, 55, 20, 60, 50, 44, 0, (200, 90, 60)),
    ]
    html = build_studio_page(cands)  # must not KeyError on tonal_range
    assert html.startswith("<!doctype html>")
    assert html.count('class="card"') == 2
    assert "focus" in html and "detail" in html  # studio metric labels rendered, not the heuristic set
