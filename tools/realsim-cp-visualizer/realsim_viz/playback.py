"""Small playback state machine shared by UI surfaces."""

from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass
class Playback:
    frame_count: int
    fps: float = 10.0
    speed: float = 1.0
    index: int = 0
    playing: bool = False
    _last_tick: float = time.monotonic()

    def toggle(self) -> None:
        self.playing = not self.playing
        self._last_tick = time.monotonic()

    def set_index(self, index: int) -> None:
        self.index = max(0, min(self.frame_count - 1, index))
        self._last_tick = time.monotonic()

    def step(self, delta: int) -> None:
        self.set_index((self.index + delta) % self.frame_count)

    def tick(self) -> bool:
        if not self.playing:
            return False
        now = time.monotonic()
        frame_period = 1.0 / max(self.fps * self.speed, 1e-6)
        if now - self._last_tick < frame_period:
            return False
        frames = int((now - self._last_tick) / frame_period)
        self._last_tick += frames * frame_period
        self.index = (self.index + frames) % self.frame_count
        return True
