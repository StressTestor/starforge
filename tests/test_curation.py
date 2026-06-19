from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from starforge.config import RenderConfig
from starforge.collection import build_collection
from starforge.curation import Curator, HeuristicCurator, StudioCurator, get_curator
from starforge.genome import Genome
from starforge.scoring import ScoreResult


def test_get_curator_returns_heuristic_and_rejects_unknown() -> None:
    curator = get_curator("heuristic")
    assert isinstance(curator, HeuristicCurator)
    assert isinstance(curator, Curator)  # satisfies the protocol
    with pytest.raises(ValueError):
        get_curator("does-not-exist")


def test_heuristic_curator_scores_with_color_harmony_reason() -> None:
    image = Image.new("RGB", (160, 160), (6, 8, 20))
    ImageDraw.Draw(image).ellipse((100, 44, 156, 100), fill=(245, 150, 60))
    result = get_curator().score(image, Genome.from_seed(1, "neon-collapse"))
    assert isinstance(result, ScoreResult)
    assert "color_harmony" in result.reasons


def test_studio_curator_is_registered_pure_and_focus_aware() -> None:
    studio = get_curator("studio")
    assert isinstance(studio, StudioCurator)
    assert isinstance(studio, Curator)  # satisfies the protocol structurally

    genome = Genome.from_seed(1, "neon-collapse")
    # a framed subject (bright blob near the genome center) vs a flat field
    focused = Image.new("RGB", (160, 160), (6, 8, 20))
    ImageDraw.Draw(focused).ellipse((58, 58, 102, 102), fill=(245, 180, 90))
    flat = Image.new("RGB", (160, 160), (40, 42, 58))

    first = studio.score(focused, genome)
    second = studio.score(focused, genome)
    assert isinstance(first, ScoreResult)
    assert first.total == second.total  # deterministic
    assert "subject_focus" in first.reasons and "detail" in first.reasons
    # the curator rewards a clear focal subject over a flat field
    assert studio.score(focused, genome).total > studio.score(flat, genome).total


def test_collection_accepts_a_custom_curator() -> None:
    # a pluggable curator that only ranks: generation stays untouched
    class ConstantCurator:
        name = "constant"

        def score(self, image, genome) -> ScoreResult:
            return ScoreResult(total=float(genome.seed % 1000), reasons={"seed_mod": float(genome.seed % 1000)})

    config = RenderConfig(width=110, height=150, frames=3, seed=260613, preset="neon-collapse")
    result = build_collection(config, batch_count=6, top_k=3, thumb_width=80, curator=ConstantCurator())

    assert len(result.entries) == 3
    # ranked by the custom curator's score, descending
    assert result.entries == sorted(result.entries, key=lambda e: e.score.total, reverse=True)
    assert all("seed_mod" in e.score.reasons for e in result.entries)
