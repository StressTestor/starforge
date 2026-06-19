from __future__ import annotations

import pytest

from starforge import video
from starforge.config import RenderConfig
from starforge.renderer import StarforgeRenderer


def test_default_render_config_is_canonical() -> None:
    # the shipped defaults (1600x2200 / seed 260613 / 42 frames) are never
    # exercised by the rest of the suite, which uses tiny explicit dims.
    config = RenderConfig()
    assert config.width == 1600
    assert config.height == 2200
    assert config.seed == 260613
    assert config.frames == 42
    assert config.title == "STARFORGE"
    assert config.preset == "neon-collapse"
    assert config.subject == "black-hole"
    assert config.supersample == 1
    assert config.aspect == pytest.approx(1600 / 2200)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"width": 5001}, "5000 or less"),
        ({"height": 5001}, "5000 or less"),
        ({"frames": 181}, "180 or less"),
        ({"supersample": 0}, "between 1 and 3"),
        ({"supersample": 4}, "between 1 and 3"),
        ({"subject": "quasar"}, "subject must be one of"),
    ],
)
def test_render_config_rejects_out_of_range(kwargs: dict[str, object], message: str) -> None:
    base: dict[str, object] = {"width": 128, "height": 128, "frames": 4}
    base.update(kwargs)
    with pytest.raises(ValueError, match=message):
        RenderConfig(**base)


def test_export_videos_skips_when_ffmpeg_missing(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(video.shutil, "which", lambda _name: None)

    status = video.export_videos([], tmp_path, fps=24)

    assert status == {
        "mp4": "skipped: ffmpeg not found",
        "webm": "skipped: ffmpeg not found",
    }
    assert list(tmp_path.iterdir()) == []


def test_supersample_branch_downsamples_to_target_size() -> None:
    config = RenderConfig(width=64, height=64, frames=2, seed=1, supersample=2)

    poster = StarforgeRenderer(config).render_poster(include_title=False)

    assert poster.size == (64, 64)
    assert poster.mode == "RGB"
