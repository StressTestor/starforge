"""Curation layer — ranks candidate renders, separate from generation.

The generator (``StarforgeRenderer``) is deterministic and is the single source
of truth: seed -> genome -> pixels, recorded in the manifest. Curation only
*ranks* those candidates and picks a winner, so a smarter curator (a learned or
CLIP-based aesthetic ranker) can drop in here later without touching
reproducibility — the chosen seed still re-renders byte-identically.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
from PIL import Image

from starforge.genome import Genome
from starforge.scoring import ScoreResult, prepare_score_array, score_composition


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


class StudioCurator:
    """A second, still-deterministic curator that ranks for a clear, well-placed
    focal subject and real structure rather than raw contrast.

    The heuristic curator is dominated by tonal range, so it tends to pick the
    *contrastiest* frame. StudioCurator keeps the same guarantees — a pure
    function of image + genome, no network, no model weights, identical answer
    every run — but reweights toward subject focus and structural detail. It is
    the honest stepping stone toward a learned/CLIP ranker: the seam stays the
    same, only the judgement gets better.
    """

    name = "studio"

    def score(self, image: Image.Image, genome: Genome) -> ScoreResult:
        # compute the scoring array once and share it with score_composition so
        # the 128x128 resize is not paid for twice.
        arr = prepare_score_array(image)
        base = score_composition(image, genome, arr=arr)
        luminance = arr[..., 0] * 0.2126 + arr[..., 1] * 0.7152 + arr[..., 2] * 0.0722
        h, w = luminance.shape
        yy, xx = np.indices((h, w), dtype=np.float32)
        cx = (0.5 + genome.center_x * 0.42) * (w - 1)
        cy = (0.5 + genome.center_y * 0.42) * (h - 1)
        radius = np.sqrt(((xx - cx) / w) ** 2 + ((yy - cy) / h) ** 2)

        # subject focus: the subject region should clearly outshine the field
        subject_region = radius < 0.18
        field_region = radius >= 0.30
        subject_focus = 0.0
        if subject_region.any() and field_region.any():
            subject_focus = max(0.0, float(luminance[subject_region].mean() - luminance[field_region].mean()))

        # structural detail: gradient energy rewards real structure, capped so a
        # noisy/busy frame cannot win on detail alone.
        grad_y, grad_x = np.gradient(luminance)
        detail = min(float(np.sqrt(grad_x**2 + grad_y**2).mean()), 18.0) * 2.2

        r = base.reasons
        reasons = {
            "subject_focus": subject_focus,
            "detail": detail,
            "thirds": r["thirds"],
            "focal_balance": r["focal_balance"],
            "color_harmony": r["color_harmony"],
            "busy_penalty": r["busy_penalty"],
        }
        total = (
            subject_focus * 0.90
            + detail * 0.50
            + r["thirds"] * 0.35
            + r["focal_balance"] * 0.30
            + r["color_harmony"] * 0.20
            + r["tonal_range"] * 0.12  # contrast still counts, just no longer dominates
            + r["busy_penalty"]
        )
        return ScoreResult(total=float(total), reasons=reasons)


_CURATORS: dict[str, type] = {
    "heuristic": HeuristicCurator,
    "studio": StudioCurator,
}


def get_curator(name: str = "heuristic") -> Curator:
    try:
        return _CURATORS[name]()
    except KeyError as exc:
        choices = ", ".join(_CURATORS)
        raise ValueError(f"unknown curator '{name}'; choose one of: {choices}") from exc
