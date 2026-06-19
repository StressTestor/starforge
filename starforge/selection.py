"""Selection over a rendered candidate set — frontier + de-biased ranking.

The v6 collection ranks every candidate by one hand-weighted scalar (dominated by
``tonal_range``). Across subjects that scalar is really a CONTRAST meter: black
holes (bright braids on a black shadow) always out-score soft subjects like
lensed galaxies, so ``--cross-subject`` is a black-hole-picker, not a quality
picker. This module fixes that two ways, deterministically and offline:

- ``pareto_frontier``: the non-dominated set over the raw metric vector. No single
  scalar can surface this; it is the set of candidates that are best on *some*
  axis, which is exactly "the best of each kind on its own terms".
- ``rank``: a per-subject min-max normalized score, so a candidate is judged
  against others of ITS subject. The standout galaxy now beats a mediocre black
  hole instead of being structurally buried.

Pure functions of the metric rows — no rendering, no RNG, no I/O.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

# every scoring reason, all oriented "higher is better" (busy_penalty is already
# signed, so less-negative is better and it composes directly).
METRIC_KEYS: tuple[str, ...] = (
    "tonal_range",
    "thirds",
    "focal_balance",
    "ring_separation",
    "color_harmony",
    "busy_penalty",
)


@dataclass(frozen=True)
class Ranked:
    index: int
    subject: str
    raw_total: float
    norm_total: float  # per-subject de-biased quality (sum of within-subject min-max metrics)
    frontier: bool  # globally non-dominated over the raw metric vector
    subject_rank: int  # 1 = best of its own subject by norm_total
    why: list[str]  # the metrics this candidate leads on within its subject


def _dominates(a: dict[str, float], b: dict[str, float], keys: tuple[str, ...]) -> bool:
    """a Pareto-dominates b: a is >= b on every metric and strictly > on one."""
    return all(a[k] >= b[k] - 1e-9 for k in keys) and any(a[k] > b[k] + 1e-9 for k in keys)


def pareto_frontier(rows: list[dict[str, float]], keys: tuple[str, ...] = METRIC_KEYS) -> list[bool]:
    """Per-row flag: True if no other row dominates it (the non-dominated set)."""
    n = len(rows)
    return [not any(_dominates(rows[j], rows[i], keys) for j in range(n) if j != i) for i in range(n)]


def _minmax_within_subject(
    rows: list[dict[str, float]], subjects: list[str], keys: tuple[str, ...]
) -> list[dict[str, float]]:
    """Scale each metric to [0, 1] WITHIN its subject group. A subject with one
    member, or a metric with no spread, scales to a neutral 0.5."""
    groups: dict[str, list[int]] = defaultdict(list)
    for i, subject in enumerate(subjects):
        groups[subject].append(i)
    scaled: list[dict[str, float]] = [{} for _ in rows]
    for idxs in groups.values():
        for key in keys:
            values = [rows[i][key] for i in idxs]
            lo, hi = min(values), max(values)
            spread = hi - lo
            for i in idxs:
                scaled[i][key] = 0.5 if spread < 1e-12 else (rows[i][key] - lo) / spread
    return scaled


def subject_scaled(
    rows: list[dict[str, float]], subjects: list[str], keys: tuple[str, ...] = METRIC_KEYS
) -> list[dict[str, float]]:
    """Public view of each metric scaled to [0, 1] within its subject — the
    de-biased values the studio draws as bars."""
    return _minmax_within_subject(rows, subjects, keys)


def rank(
    rows: list[dict[str, float]],
    subjects: list[str],
    *,
    raw_totals: list[float],
    keys: tuple[str, ...] = METRIC_KEYS,
) -> list[Ranked]:
    """Rank a candidate set. ``rows`` are the per-metric reason dicts, ``subjects``
    the parallel subject list, ``raw_totals`` the v6 scalar per row (kept for
    reference). Returns one ``Ranked`` per input row, in input order."""
    if not (len(rows) == len(subjects) == len(raw_totals)):
        raise ValueError("rows, subjects, and raw_totals must be the same length")

    frontier = pareto_frontier(rows, keys)
    scaled = _minmax_within_subject(rows, subjects, keys)
    norm_totals = [sum(scaled[i][k] for k in keys) for i in range(len(rows))]

    # rank within each subject by the de-biased score (ties broken by raw total,
    # then index, so the ordering is deterministic).
    subject_rank: dict[int, int] = {}
    groups: dict[str, list[int]] = defaultdict(list)
    for i, subject in enumerate(subjects):
        groups[subject].append(i)
    for idxs in groups.values():
        ordered = sorted(idxs, key=lambda i: (-norm_totals[i], -raw_totals[i], i))
        for rk, i in enumerate(ordered, start=1):
            subject_rank[i] = rk

    # "why it won" reports the virtues it leads on; busy_penalty (usually 0, i.e.
    # "not busy") is a real axis for the frontier but not a selling point.
    why_keys = tuple(k for k in keys if k != "busy_penalty")
    out: list[Ranked] = []
    for i in range(len(rows)):
        why = sorted(why_keys, key=lambda k: (-scaled[i][k], k))[:2]
        out.append(
            Ranked(
                index=i,
                subject=subjects[i],
                raw_total=float(raw_totals[i]),
                norm_total=float(norm_totals[i]),
                frontier=frontier[i],
                subject_rank=subject_rank[i],
                why=why,
            )
        )
    return out
