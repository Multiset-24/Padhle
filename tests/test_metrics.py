"""EAR and closure-timer tests. No webcam and no model."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from eye.metrics import LEFT_EYE, RIGHT_EYE, ClosureTimer, average_ear, eye_aspect_ratio

# Vertical span 3 on a width of 10 -> EAR 0.30.
OPEN_EYE = ((0, 0), (3, 1.5), (7, 1.5), (10, 0), (7, -1.5), (3, -1.5))
# Vertical span 0.5 on a width of 10 -> EAR 0.05.
CLOSED_EYE = ((0, 0), (3, 0.25), (7, 0.25), (10, 0), (7, -0.25), (3, -0.25))


class FakeClock:
    """Stand-in for time.monotonic()."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def advance(self, seconds: float) -> float:
        self.now += seconds
        return self.now


def _face(left: tuple, right: tuple, count: int = 478) -> list[SimpleNamespace]:
    points = [SimpleNamespace(x=0.0, y=0.0) for _ in range(count)]
    for index, (x, y) in zip(LEFT_EYE, left, strict=True):
        points[index] = SimpleNamespace(x=x, y=y)
    for index, (x, y) in zip(RIGHT_EYE, right, strict=True):
        points[index] = SimpleNamespace(x=x, y=y)
    return points


def test_landmark_indices_match_the_plan():
    assert LEFT_EYE == (33, 160, 158, 133, 153, 144)
    assert RIGHT_EYE == (362, 385, 387, 263, 373, 380)


def test_open_eye_ear():
    assert eye_aspect_ratio(OPEN_EYE) == pytest.approx(0.3)


def test_closed_eye_ear():
    assert eye_aspect_ratio(CLOSED_EYE) == pytest.approx(0.05)


def test_flat_eye_ear_is_zero():
    flat = ((0, 0), (3, 0), (7, 0), (10, 0), (7, 0), (3, 0))
    assert eye_aspect_ratio(flat) == 0.0


def test_average_ear_uses_both_eyes():
    face = _face(OPEN_EYE, CLOSED_EYE)
    assert average_ear(face, width=1, height=1) == pytest.approx((0.3 + 0.05) / 2)


def test_pixel_size_keeps_ear_on_a_640_by_480_frame():
    pixels = (
        (100, 200),
        (120, 191),
        (140, 191),
        (160, 200),
        (140, 209),
        (120, 209),
    )
    assert eye_aspect_ratio(pixels) == pytest.approx(0.3)
    normalized = tuple((x / 640, y / 480) for x, y in pixels)
    face = _face(normalized, normalized)
    assert average_ear(face, width=640, height=480) == pytest.approx(0.3)


def test_short_blink_does_not_beep():
    clock = FakeClock()
    timer = ClosureTimer(threshold=0.2, min_duration_s=2.0)
    frame_dt = 1 / 30
    while clock.now <= 0.3:
        assert timer.update(0.08, clock.now) is False
        clock.advance(frame_dt)
    assert timer.update(0.35, clock.now) is False


def test_two_and_a_half_second_closure_beeps():
    clock = FakeClock()
    timer = ClosureTimer(threshold=0.2, min_duration_s=2.0)
    frame_dt = 1 / 30
    beeped_at = None
    while clock.now <= 2.5:
        if timer.update(0.08, clock.now):
            beeped_at = clock.now
            break
        clock.advance(frame_dt)
    assert beeped_at is not None
    assert beeped_at > 2.0
    assert beeped_at <= 2.5


def test_closure_must_be_longer_than_the_limit():
    timer = ClosureTimer(threshold=0.2, min_duration_s=2.0)
    assert timer.update(0.1, 0.0) is False
    assert timer.update(0.1, 2.0) is False
    assert timer.update(0.1, 2.5) is True


def test_opening_the_eyes_resets_the_timer():
    clock = FakeClock()
    timer = ClosureTimer(threshold=0.2, min_duration_s=2.0)
    assert timer.update(0.1, clock.now) is False
    clock.advance(1.9)
    assert timer.update(0.1, clock.now) is False
    clock.advance(0.2)
    assert timer.update(0.35, clock.now) is False
    clock.advance(0.3)
    assert timer.update(0.1, clock.now) is False


def test_no_face_resets_the_timer():
    timer = ClosureTimer(threshold=0.2, min_duration_s=2.0)
    assert timer.update(0.1, 0.0) is False
    assert timer.update(None, 3.0) is False
    assert timer.update(0.1, 3.1) is False
    assert timer.update(0.1, 5.0) is False
    assert timer.update(0.1, 5.2) is True


def test_ear_equal_to_the_threshold_does_not_count_as_closed():
    timer = ClosureTimer(threshold=0.2, min_duration_s=2.0)
    assert timer.update(0.2, 0.0) is False
    assert timer.update(0.2, 3.0) is False
