from __future__ import annotations

import re
import tomllib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from starforge.collection import build_collection
from starforge.config import RenderConfig
from starforge.genome import Genome
from starforge.renderer import StarforgeRenderer
from starforge.scoring import score_composition


ROOT = Path(__file__).resolve().parents[1]


def luminance(image: Image.Image) -> np.ndarray:
    arr = np.asarray(image.convert("RGB").resize((120, 160), Image.Resampling.BILINEAR), dtype=np.float32)
    return arr[..., 0] * 0.2126 + arr[..., 1] * 0.7152 + arr[..., 2] * 0.0722


def correlation(first: Image.Image, second: Image.Image) -> float:
    a = luminance(first).ravel()
    b = luminance(second).ravel()
    return float(np.corrcoef(a, b)[0, 1])


def test_genome_is_deterministic_and_seed_drives_macro_fields() -> None:
    first = Genome.from_seed(260613, "neon-collapse")
    second = Genome.from_seed(260613, "neon-collapse")
    other = Genome.from_seed(300208, "neon-collapse")

    assert first == second
    assert first != other
    assert first.disk_band_count in range(5, 15)
    assert -0.34 <= first.center_x <= 0.34
    assert -0.28 <= first.center_y <= 0.28
    assert 0.12 <= first.horizon_radius <= 0.26
    assert 0.10 <= first.lensing_strength <= 0.30

    changed = [
        first.disk_tilt != other.disk_tilt,
        first.jet_angle != other.jet_angle,
        first.horizon_radius != other.horizon_radius,
        first.center_x != other.center_x,
        first.color_temperature != other.color_temperature,
    ]
    assert sum(changed) >= 4


def test_different_seeds_change_black_hole_structure_not_only_stars() -> None:
    seeds = [260613, 268532, 276451, 284370]
    images = [
        StarforgeRenderer(RenderConfig(width=220, height=300, seed=seed, frames=3, preset="neon-collapse")).render_poster(
            include_title=False
        )
        for seed in seeds
    ]

    base = images[0]
    correlations = [correlation(base, image) for image in images[1:]]

    assert max(correlations) < 0.84


def test_composition_score_has_reasons_and_prefers_rule_of_thirds() -> None:
    centered = Image.new("RGB", (180, 180), (8, 10, 24))
    thirds = Image.new("RGB", (180, 180), (8, 10, 24))
    draw_centered = ImageDraw.Draw(centered)
    draw_thirds = ImageDraw.Draw(thirds)
    draw_centered.ellipse((62, 62, 118, 118), fill=(245, 190, 90))
    draw_thirds.ellipse((104, 48, 160, 104), fill=(245, 190, 90))

    centered_score = score_composition(centered, Genome.from_seed(1, "neon-collapse"))
    thirds_score = score_composition(thirds, Genome.from_seed(2, "neon-collapse"))

    assert thirds_score.total > centered_score.total
    assert {"tonal_range", "thirds", "focal_balance", "busy_penalty", "ring_separation", "color_harmony"} <= set(
        thirds_score.reasons
    )


def test_collection_sweeps_presets_and_returns_ranked_top_k() -> None:
    config = RenderConfig(width=120, height=160, frames=3, seed=260613, preset="neon-collapse")

    result = build_collection(config, batch_count=10, top_k=5, thumb_width=90)

    assert len(result.entries) == 5
    assert len({entry.preset for entry in result.entries}) >= 2
    assert result.entries == sorted(result.entries, key=lambda entry: entry.score.total, reverse=True)
    assert result.image.width == 3 * 90 + 4 * 12
    assert all(entry.genome.seed == entry.seed for entry in result.entries)
    assert all(entry.score.reasons for entry in result.entries)


def test_single_subject_collection_unchanged_and_cross_subject_mixes() -> None:
    config = RenderConfig(width=96, height=132, frames=3, seed=260613, preset="neon-collapse", subject="black-hole")

    default = build_collection(config, batch_count=6, top_k=6, thumb_width=72)
    explicit = build_collection(config, batch_count=6, top_k=6, thumb_width=72, subjects=["black-hole"])
    # a one-subject sweep is byte-identical to the original preset-only sweep
    assert [(e.seed, e.preset) for e in default.entries] == [(e.seed, e.preset) for e in explicit.entries]
    assert [e.score.total for e in default.entries] == [e.score.total for e in explicit.entries]

    mixed = build_collection(
        config, batch_count=6, top_k=6, thumb_width=72, subjects=["black-hole", "lensed-galaxy"]
    )
    assert {e.genome.subject for e in mixed.entries} == {"black-hole", "lensed-galaxy"}
    assert all(e.genome.seed == e.seed for e in mixed.entries)


def test_package_has_console_script_and_ci_smoke_render() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert project["project"]["scripts"]["starforge"] == "starforge.cli:main"

    workflow = ROOT / ".github" / "workflows" / "ci.yml"
    text = workflow.read_text()
    assert "pytest" in text
    assert "starforge" in text
    assert "--width 320" in text
    assert "--height 440" in text

    # third-party actions are pinned to full commit SHAs, never mutable tags.
    assert not re.findall(r"uses:\s*\S+@v\d", text), "ci actions must be pinned to commit SHAs"
    assert re.search(r"uses:\s*actions/checkout@[0-9a-f]{40}", text)
    assert re.search(r"uses:\s*actions/setup-python@[0-9a-f]{40}", text)
