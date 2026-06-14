from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from starforge.config import RenderConfig
from starforge.genome import Genome
from starforge.renderer import StarforgeRenderer

GOLDEN = json.loads((Path(__file__).resolve().parent / "_genome_golden_v4.json").read_text())


def test_genome_rng_order_is_locked_to_v4() -> None:
    """Every v4 genome field must stay byte-identical. Any new field added to
    the genome must be drawn AFTER the existing black-hole sequence (or not from
    the RNG at all), or these goldens shift and the whole curated gallery
    silently re-rolls. New non-RNG keys (e.g. ``subject``) are allowed; existing
    values are not."""
    for key, expected in GOLDEN.items():
        seed_str, preset = key.split(":", 1)
        manifest = Genome.from_seed(int(seed_str), preset).to_manifest()
        for field, value in expected.items():
            assert manifest[field] == value, f"{key}: field '{field}' drifted {value} -> {manifest.get(field)}"
        # subject exists on the genome but must NOT be in the locked draw (it is
        # not RNG-sampled), so it is absent from the golden yet present here.
        assert "subject" not in expected
        assert manifest["subject"] == "black-hole"


def test_v4_seeds_still_render_byte_identical() -> None:
    # the genome lock plus a render check: the canonical seeds reproduce exactly.
    for key in list(GOLDEN)[:3]:
        seed_str, preset = key.split(":", 1)
        cfg = RenderConfig(width=200, height=275, seed=int(seed_str), frames=4, preset=preset)
        a = np.asarray(StarforgeRenderer(cfg).render_poster(include_title=False))
        b = np.asarray(StarforgeRenderer(cfg).render_poster(include_title=False))
        assert np.array_equal(a, b)
