"""Threaded webcam capture at a fixed frame size."""

from __future__ import annotations

import sys
import threading
import time

import cv2
import numpy as np


class Camera:
    """Read the latest webcam frame on a background thread.

    ``state`` is ``opening``, ``live``, or ``unavailable``. A failed open or
    read waits ``retry_seconds`` and tries again. On macOS the first open uses
    the AVFoundation backend.
    """

    def __init__(self, index: int, width: int, height: int, retry_seconds: float) -> None:
        self.index = index
        self.width = width
        self.height = height
        self.retry_seconds = retry_seconds
        self._capture: cv2.VideoCapture | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._lock = threading.Lock()
        self._frame: np.ndarray | None = None
        self._state = "opening"

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="eye-camera", daemon=True)
        self._thread.start()

    def read(self) -> np.ndarray | None:
        """Return a copy of the latest frame, or None when the camera is down."""
        with self._lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    def stop(self) -> None:
        self._running = False
        thread = self._thread
        if thread is not None:
            thread.join(timeout=3.0)
        if thread is None or not thread.is_alive():
            self._release()
        self._thread = None

    def _loop(self) -> None:
        try:
            while self._running:
                capture = self._open()
                if capture is None:
                    self._publish(None, "unavailable")
                    self._wait(self.retry_seconds)
                    continue
                while self._running:
                    ok, frame = capture.read()
                    if not ok or frame is None:
                        self._release()
                        self._publish(None, "unavailable")
                        break
                    self._publish(frame.copy(), "live")
                if self._running:
                    self._wait(self.retry_seconds)
        finally:
            self._release()

    def _open(self) -> cv2.VideoCapture | None:
        capture = _open_capture(self.index)
        if not capture.isOpened():
            capture.release()
            return None
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        with self._lock:
            self._capture = capture
        return capture

    def _publish(self, frame: np.ndarray | None, state: str) -> None:
        with self._lock:
            previous = self._state
            self._frame = frame
            self._state = state
        if state == "unavailable" and previous != "unavailable":
            print(
                f"camera unavailable; retrying every {self.retry_seconds:g} s",
                file=sys.stderr,
            )

    def _release(self) -> None:
        with self._lock:
            capture = self._capture
            self._capture = None
        if capture is not None:
            capture.release()

    def _wait(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while self._running and time.monotonic() < deadline:
            time.sleep(0.05)


def _open_capture(index: int) -> cv2.VideoCapture:
    if sys.platform == "darwin":
        capture = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
        if capture.isOpened():
            return capture
        capture.release()
    return cv2.VideoCapture(index)
