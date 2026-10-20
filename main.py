"""Project Eye phase 1: live EAR, and a beep when the eyes stay closed."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2
import numpy as np
import yaml

from eye.alarm import Alarm
from eye.camera import Camera
from eye.landmarks import EyeLandmarker, ensure_model
from eye.metrics import ClosureTimer, average_ear

ROOT = Path(__file__).resolve().parent
WINDOW = "Project Eye"


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return loaded


class FpsCounter:
    def __init__(self) -> None:
        self._frames = 0
        self._window_start = time.monotonic()
        self.value = 0.0

    def tick(self) -> float:
        self._frames += 1
        now = time.monotonic()
        elapsed = now - self._window_start
        if elapsed >= 0.5:
            self.value = self._frames / elapsed
            self._frames = 0
            self._window_start = now
        return self.value

    def reset(self) -> None:
        self._frames = 0
        self._window_start = time.monotonic()
        self.value = 0.0


def blank_frame(width: int, height: int) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def draw_status(frame: np.ndarray, lines: list[str], kind: str) -> None:
    colors = {
        "ok": (0, 255, 0),
        "warn": (0, 200, 255),
        "alert": (0, 0, 255),
    }
    color = colors[kind]
    if kind == "alert":
        height, width = frame.shape[:2]
        cv2.rectangle(frame, (0, 0), (width - 1, height - 1), color, 6)
    y = 32
    for line in lines:
        origin = (12, y)
        cv2.putText(frame, line, origin, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(frame, line, origin, cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
        y += 32


def _positive(name: str, value: float) -> float:
    number = float(value)
    if number <= 0:
        raise ValueError(f"{name} must be positive")
    return number


def main() -> int:
    config_path = ROOT / "config.yaml"
    try:
        config = load_config(config_path)
        threshold = _positive("ear.closed_threshold", config["ear"]["closed_threshold"])
        closed_seconds = _positive("ear.closed_seconds", config["ear"]["closed_seconds"])
        width = int(config["camera"]["width"])
        height = int(config["camera"]["height"])
        frequency_hz = _positive("alarm.frequency_hz", config["alarm"]["frequency_hz"])
        beep_seconds = _positive("alarm.duration_s", config["alarm"]["duration_s"])
        retry_seconds = _positive("camera.retry_seconds", config["camera"]["retry_seconds"])
        camera_index = int(config["camera"]["index"])
        model_url = str(config["model"]["url"])
        model_path = ROOT / config["model"]["path"]
    except (OSError, yaml.YAMLError, ValueError, KeyError, TypeError) as exc:
        print(f"Could not read {config_path}: {exc}", file=sys.stderr)
        return 1

    try:
        if not (model_path.is_file() and model_path.stat().st_size > 0):
            print(f"Downloading the face landmarker model to {model_path}")
        model_path = ensure_model(model_path, model_url)
    except (OSError, RuntimeError) as exc:
        print(f"Could not download the face landmarker model: {exc}", file=sys.stderr)
        print("Try: python scripts/download_model.py", file=sys.stderr)
        return 1

    landmarker = None
    alarm = None
    camera = None
    try:
        try:
            landmarker = EyeLandmarker(model_path)
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"Could not start the face landmarker: {exc}", file=sys.stderr)
            return 1

        alarm = Alarm(frequency_hz=frequency_hz, duration_s=beep_seconds)
        camera = Camera(
            index=camera_index,
            width=width,
            height=height,
            retry_seconds=retry_seconds,
        )
        timer = ClosureTimer(threshold=threshold, min_duration_s=closed_seconds)
        fps = FpsCounter()

        print("Project Eye is running. Press q to quit.")
        camera.start()
        while True:
            camera_state = camera.state
            frame = camera.read()
            now = time.monotonic()
            if frame is None or camera_state != "live":
                timer.update(None, now)
                alarm.stop()
                fps.reset()
                frame = blank_frame(width, height)
                lines = ["EAR: --", "FPS: --"]
                if camera_state == "unavailable":
                    lines.append("camera unavailable")
                    lines.append("allow Camera for Terminal, or free the camera")
                else:
                    lines.append("opening camera")
                kind = "warn"
                wait_ms = 100
            else:
                landmarks = landmarker.detect(frame)
                if landmarks is None:
                    ear = None
                    status = "no face"
                    ear_line = "EAR: --"
                    kind = "warn"
                else:
                    ear = average_ear(landmarks, frame.shape[1], frame.shape[0])
                    ear_line = f"EAR: {ear:.2f}"
                    status = "eyes closed" if ear < threshold else "eyes open"
                    kind = "ok"
                alert = timer.update(ear, now)
                if alert:
                    alarm.beep()
                    kind = "alert"
                else:
                    alarm.stop()
                lines = [ear_line, f"FPS: {fps.tick():.1f}", status]
                if alert:
                    lines.append("beep")
                wait_ms = 1

            draw_status(frame, lines, kind)
            cv2.imshow(WINDOW, frame)
            key = cv2.waitKey(wait_ms) & 0xFF
            if key in (ord("q"), ord("Q")):
                break
    except KeyboardInterrupt:
        pass
    finally:
        if camera is not None:
            camera.stop()
        if landmarker is not None:
            landmarker.close()
        if alarm is not None:
            alarm.close()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
