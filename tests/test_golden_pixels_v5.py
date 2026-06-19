from __future__ import annotations

import json
from pathlib import Path

import pytest

# the test renders through the exact same helper the regen tool uses, so the
# committed golden and this check can never drift apart.
from tools.regen_pixel_golden import environment_signature, render_hash, spec_key

GOLDEN_PATH = Path(__file__).resolve().parent / "_pixel_golden_v5.json"


def _golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text())


def test_golden_covers_every_subject() -> None:
    from starforge.genome import SUBJECT_NAMES

    subjects = {spec["subject"] for spec in _golden()["specs"]}
    assert set(SUBJECT_NAMES) <= subjects, f"pixel golden missing subjects: {set(SUBJECT_NAMES) - subjects}"


def test_rendered_pixels_match_committed_golden() -> None:
    # pins byte-exact output so a deterministic-but-wrong visual change is caught.
    # hashes are per-environment (platform/numpy/Pillow affect the low bits); when
    # the running environment has no committed golden we skip rather than red CI.
    data = _golden()
    signature = environment_signature()
    environments = data["environments"]
    if signature not in environments:
        pytest.skip(
            f"no pixel golden for {signature}; "
            "regenerate with `PYTHONPATH=. python3 tools/regen_pixel_golden.py`"
        )

    expected = environments[signature]
    for spec in data["specs"]:
        key = spec_key(spec)
        assert key in expected, f"golden for {signature} is missing {key}; regenerate it"
        assert render_hash(spec) == expected[key], f"pixel regression for {key}"
