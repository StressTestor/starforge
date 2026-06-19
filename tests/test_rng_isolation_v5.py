from __future__ import annotations

from starforge.genome import SUBJECT_NAMES, Genome
from starforge.presets import PRESET_NAMES


def _rng_derived_fields(genome: Genome) -> dict[str, object]:
    data = genome.to_manifest()
    data.pop("subject", None)
    return data


def test_subject_does_not_consume_rng_or_perturb_genome() -> None:
    # the genome draw order is locked and `subject` must never consume the RNG,
    # so every subject must yield byte-identical RNG-derived fields for a given
    # (seed, preset). this pins the seam that lets lensed-galaxy share the
    # black-hole draw sequence. (architecture: genome.py NOTE at from_seed)
    for preset in PRESET_NAMES:
        for seed in (1, 260613, 323965, 999983):
            black_hole = _rng_derived_fields(Genome.from_seed(seed, preset, "black-hole"))
            for subject in SUBJECT_NAMES:
                genome = Genome.from_seed(seed, preset, subject)
                assert _rng_derived_fields(genome) == black_hole, (seed, preset, subject)
                assert genome.subject == subject
