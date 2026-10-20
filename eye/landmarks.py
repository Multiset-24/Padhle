"""MediaPipe Face Landmarker wrapper and the one-time model download."""

from __future__ import annotations

import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np


def ensure_model(path: str | Path, url: str) -> Path:
    """Return the local model path, downloading it once if it is missing."""
    destination = Path(path)
    if destination.is_file() and destination.stat().st_size > 0:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "project-eye/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as handle:
            shutil.copyfileobj(response, handle)
        temporary.replace(destination)
    except (OSError, urllib.error.URLError):
        if temporary.exists():
            temporary.unlink()
        raise
    if not destination.is_file() or destination.stat().st_size == 0:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded model was empty: {url}")
    return destination


class EyeLandmarker:
    """Detect one face per frame with the Tasks Face Landmarker.

    Video mode returns the landmarks for the frame just passed in, which the
    preview uses to print that frame's EAR. Each timestamp is greater than
    the previous one, as ``detect_for_video`` requires.
    """

    def __init__(self, model_path: str | Path) -> None:
        resolved = str(Path(model_path).resolve())
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=resolved),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
        )
        self._landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        self._started = time.monotonic()
        self._last_timestamp_ms = -1
        self._warned = False

    def detect(self, bgr_frame: np.ndarray) -> list | None:
        """Return the first face's landmarks, or None when no face is found."""
        if bgr_frame is None or bgr_frame.size == 0:
            return None
        # OpenCV frames are BGR. ImageFormat.SRGB is an RGB image.
        rgb = np.ascontiguousarray(cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB))
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        try:
            result = self._landmarker.detect_for_video(image, self._timestamp_ms())
        except (ValueError, RuntimeError) as exc:
            if not self._warned:
                print(f"Face landmarker error: {exc}", file=sys.stderr)
                self._warned = True
            return None
        faces = result.face_landmarks or []
        if not faces:
            return None
        return faces[0]

    def close(self) -> None:
        landmarker = self._landmarker
        self._landmarker = None
        if landmarker is not None:
            landmarker.close()

    def _timestamp_ms(self) -> int:
        timestamp_ms = int((time.monotonic() - self._started) * 1000)
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms
        return timestamp_ms
