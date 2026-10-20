"""Eye aspect ratio and the phase-1 eye-closure timer."""

from __future__ import annotations

import math
from collections.abc import Sequence

# p1..p6 order from the plan. p1 and p4 are the eye corners, p2/p3 the upper
# lid, and p6/p5 the lower lid.
LEFT_EYE = (33, 160, 158, 133, 153, 144)
RIGHT_EYE = (362, 385, 387, 263, 373, 380)


def _coordinates(point: object) -> tuple[float, float]:
    if hasattr(point, "x") and hasattr(point, "y"):
        return float(point.x), float(point.y)
    x, y = point  # type: ignore[misc]
    return float(x), float(y)


def _distance(first: object, second: object) -> float:
    ax, ay = _coordinates(first)
    bx, by = _coordinates(second)
    return math.hypot(ax - bx, ay - by)


def eye_aspect_ratio(points: Sequence[object]) -> float:
    """Return the eye aspect ratio for six points in p1..p6 order.

    EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
    """
    if len(points) != 6:
        raise ValueError("EAR expects 6 points in p1..p6 order")
    p1, p2, p3, p4, p5, p6 = points
    horizontal = _distance(p1, p4)
    if horizontal <= 1e-6:
        return 0.0
    vertical = _distance(p2, p6) + _distance(p3, p5)
    return vertical / (2.0 * horizontal)


def average_ear(landmarks: Sequence[object], width: float, height: float) -> float:
    """Average EAR of both eyes.

    Face Landmarker points are normalized. ``width`` and ``height`` convert
    them to pixels first, so a 640x480 frame does not stretch the ratio.
    """

    def pixel(index: int) -> tuple[float, float]:
        x, y = _coordinates(landmarks[index])
        return (x * width, y * height)

    left = eye_aspect_ratio([pixel(index) for index in LEFT_EYE])
    right = eye_aspect_ratio([pixel(index) for index in RIGHT_EYE])
    return (left + right) / 2.0


class ClosureTimer:
    """True once EAR has stayed under the threshold for longer than the limit.

    ``update`` takes the current time, so tests can drive it with a fake clock.
    ``ear is None`` means no face and resets the timer.
    """

    def __init__(self, threshold: float, min_duration_s: float) -> None:
        if threshold <= 0:
            raise ValueError("threshold must be positive")
        if min_duration_s <= 0:
            raise ValueError("min_duration_s must be positive")
        self.threshold = float(threshold)
        self.min_duration_s = float(min_duration_s)
        self._closed_since: float | None = None

    def update(self, ear: float | None, now_s: float) -> bool:
        if ear is None or ear >= self.threshold:
            self._closed_since = None
            return False
        if self._closed_since is None:
            self._closed_since = now_s
        return (now_s - self._closed_since) > self.min_duration_s
