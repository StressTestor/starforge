from __future__ import annotations

from dataclasses import dataclass

from starforge.presets import get_preset


@dataclass(frozen=True)
class RenderConfig:
    """Validated rendering options shared by the poster and animation."""

    width: int = 1600
    height: int = 2200
    seed: int = 260613
    frames: int = 42
    title: str = "STARFORGE"
    preset: str = "neon-collapse"
    supersample: int = 1

    def __post_init__(self) -> None:
        if self.width < 64:
            raise ValueError("width must be at least 64")
        if self.height < 64:
            raise ValueError("height must be at least 64")
        if self.frames < 2:
            raise ValueError("frames must be at least 2")
        if self.width > 5000 or self.height > 5000:
            raise ValueError("width and height must be 5000 or less")
        if self.frames > 180:
            raise ValueError("frames must be 180 or less")
        if self.supersample < 1 or self.supersample > 3:
            raise ValueError("supersample must be between 1 and 3")
        get_preset(self.preset)

    @property
    def aspect(self) -> float:
        return self.width / self.height
