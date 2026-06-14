"""Curation layer — ranks candidate renders, separate from generation.

The generator (``StarforgeRenderer``) is deterministic and is the single source
of truth: seed -> genome -> pixels, recorded in the manifest. Curation only
*ranks* those candidates and picks a winner, so a smarter curator (a learned or
CLIP-based aesthetic ranker) can drop in here later without touching
reproducibility — the chosen seed still re-renders byte-identically.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from PIL import Image

from starforge.genome import Genome
from starforge.scoring import ScoreResult, score_composition


@runtime_checkable
class Curator(Protocol):
    """Scores a rendered candidate. Implementations must be pure functions of
    the image (and its genome) so a render's ranking is reproducible."""

    name: str

    def score(self, image: Image.Image, genome: Genome) -> ScoreResult: ...


class HeuristicCurator:
    """Deterministic, dependency-free aesthetic curator.

    Ranks candidates on composition: tonal range, rule of thirds, focal balance,
    a penalty for busy frames, photon-ring separation, and colour harmony. No
    network, no model weights — it runs on your machine and gives the same answer
    every time.
    """

    name = "heuristic"

    def score(self, image: Image.Image, genome: Genome) -> ScoreResult:
        return score_composition(image, genome)


_CURATORS: dict[str, type] = {
    "heuristic": HeuristicCurator,
}


def get_curator(name: str = "heuristic") -> Curator:
    try:
        return _CURATORS[name]()
    except KeyError as exc:
        choices = ", ".join(_CURATORS)
        raise ValueError(f"unknown curator '{name}'; choose one of: {choices}") from exc
