from __future__ import annotations

from starforge.selection import METRIC_KEYS, pareto_frontier, rank


def _row(tonal, thirds, focal, ring, color, busy) -> dict[str, float]:
    return {
        "tonal_range": tonal,
        "thirds": thirds,
        "focal_balance": focal,
        "ring_separation": ring,
        "color_harmony": color,
        "busy_penalty": busy,
    }


# three black holes (high raw contrast) + two galaxies (low raw contrast). this
# mirrors the real sweep where the scalar buckets by subject.
BH1 = _row(200, 70, 78, 50, 33, 0)
BH2 = _row(195, 68, 60, 20, 30, 0)
BH3 = _row(190, 60, 45, 10, 28, -5)
G1 = _row(85, 76, 74, 40, 44, 0)  # clearly the best galaxy
G2 = _row(70, 55, 50, 12, 30, -8)
ROWS = [BH1, BH2, BH3, G1, G2]
SUBJECTS = ["black-hole", "black-hole", "black-hole", "lensed-galaxy", "lensed-galaxy"]
RAW = [165.0, 160.0, 150.0, 128.0, 118.0]  # tonal-dominated, so raw ranks every BH over every galaxy


def test_pareto_frontier_flags_dominated() -> None:
    flags = pareto_frontier(ROWS)
    # BH1 dominates BH3 on every metric -> BH3 is off the frontier
    assert flags[2] is False
    # BH1 (top tonal) and G1 (top thirds) are each non-dominated
    assert flags[0] is True
    assert flags[3] is True


def test_per_subject_normalization_debiases_subject_contrast() -> None:
    ranked = rank(ROWS, SUBJECTS, raw_totals=RAW)

    # raw scalar buckets by subject: every black hole outranks every galaxy
    raw_order = sorted(range(len(ROWS)), key=lambda i: -RAW[i])
    raw_subjects = [SUBJECTS[i] for i in raw_order]
    assert raw_subjects == ["black-hole", "black-hole", "black-hole", "lensed-galaxy", "lensed-galaxy"]

    # de-biased: the best galaxy (G1) now beats the mediocre black holes
    by_index = {r.index: r for r in ranked}
    assert by_index[3].norm_total > by_index[1].norm_total  # G1 > BH2
    assert by_index[3].norm_total > by_index[2].norm_total  # G1 > BH3

    # and globally by norm_total, a galaxy lands above at least one black hole
    norm_order = sorted(ranked, key=lambda r: (-r.norm_total, r.index))
    norm_subjects = [r.subject for r in norm_order]
    first_galaxy = norm_subjects.index("lensed-galaxy")
    last_black_hole = len(norm_subjects) - 1 - norm_subjects[::-1].index("black-hole")
    assert first_galaxy < last_black_hole  # the buckets interleave now


def test_subject_rank_and_why_are_meaningful() -> None:
    ranked = rank(ROWS, SUBJECTS, raw_totals=RAW)
    by_index = {r.index: r for r in ranked}

    # BH1 is the best black hole, G1 the best galaxy
    assert by_index[0].subject_rank == 1
    assert by_index[3].subject_rank == 1
    assert by_index[2].subject_rank == 3  # BH3 worst of its subject

    # "why" names virtues, never busy_penalty, and at most two
    for r in ranked:
        assert len(r.why) == 2
        assert "busy_penalty" not in r.why
        assert all(k in METRIC_KEYS for k in r.why)


def test_rank_validates_lengths() -> None:
    import pytest

    with pytest.raises(ValueError):
        rank([BH1, BH2], ["black-hole"], raw_totals=[1.0, 2.0])


def test_metrics_are_data_driven_for_any_curator() -> None:
    # the studio curator emits a DIFFERENT reason set than the heuristic; selection
    # must derive the metrics from the rows, not assume tonal_range/ring_separation
    # (regression: --studio --curator studio used to KeyError on 'tonal_range').
    from starforge.selection import metric_keys

    studio_keys = ("subject_focus", "detail", "thirds", "focal_balance", "color_harmony", "busy_penalty")
    rows = [
        {"subject_focus": 80, "detail": 30, "thirds": 70, "focal_balance": 60, "color_harmony": 40, "busy_penalty": 0},
        {"subject_focus": 40, "detail": 20, "thirds": 50, "focal_balance": 45, "color_harmony": 35, "busy_penalty": -5},
        {"subject_focus": 60, "detail": 25, "thirds": 76, "focal_balance": 50, "color_harmony": 44, "busy_penalty": 0},
    ]
    subjects = ["black-hole", "black-hole", "lensed-galaxy"]

    assert metric_keys(rows) == studio_keys  # derived from the data, in row order
    ranked = rank(rows, subjects, raw_totals=[1.0, 2.0, 3.0])  # no keys arg -> derive, must not KeyError
    assert len(ranked) == 3
    assert any(r.frontier for r in ranked)
    assert all("tonal_range" not in r.why for r in ranked)  # the heuristic set is not assumed
