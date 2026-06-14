from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


def build_ffmpeg_command(frame_pattern: Path, output_path: Path, *, fps: int, kind: str) -> list[str]:
    base = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-framerate",
        str(fps),
        "-i",
        str(frame_pattern),
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
    ]
    if kind == "mp4":
        return [*base, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path)]
    if kind == "webm":
        return [*base, "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "34", "-pix_fmt", "yuv420p", str(output_path)]
    raise ValueError(f"unknown video kind: {kind}")


def export_videos(frames: list[Image.Image], output: Path, *, fps: int = 24) -> dict[str, str]:
    if shutil.which("ffmpeg") is None:
        return {"mp4": "skipped: ffmpeg not found", "webm": "skipped: ffmpeg not found"}

    statuses: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="starforge_frames_") as temp:
        temp_dir = Path(temp)
        for index, frame in enumerate(frames):
            frame.save(temp_dir / f"frame_{index:05d}.png")

        pattern = temp_dir / "frame_%05d.png"
        for kind, filename in (("mp4", "starforge.mp4"), ("webm", "starforge.webm")):
            target = output / filename
            command = build_ffmpeg_command(pattern, target, fps=fps, kind=kind)
            result = subprocess.run(command, check=False, text=True, capture_output=True)
            if result.returncode == 0 and target.is_file() and target.stat().st_size > 0:
                statuses[kind] = "written"
            else:
                message = (result.stderr or result.stdout or "ffmpeg failed").strip().splitlines()
                statuses[kind] = f"failed: {message[-1] if message else 'ffmpeg failed'}"

    return statuses

