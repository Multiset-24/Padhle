"""A short beep generated in memory and played with pygame.mixer."""

from __future__ import annotations

import sys

import numpy as np
import pygame


SAMPLE_RATE = 44100


def make_beep(frequency_hz: float, duration_s: float, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Return signed 16-bit mono PCM for a sine beep with a short fade."""
    count = max(1, int(sample_rate * duration_s))
    times = np.arange(count, dtype=np.float64) / sample_rate
    wave = np.sin(2.0 * np.pi * frequency_hz * times)
    fade = min(count // 4, int(sample_rate * 0.015))
    if fade > 0:
        ramp = np.linspace(0.0, 1.0, fade, endpoint=False)
        wave[:fade] *= ramp
        wave[-fade:] *= ramp[::-1]
    return (wave * 0.7 * 32767.0).astype(np.int16)


class Alarm:
    """Play the beep while the closure timer says the eyes have stayed shut.

    The mixer is opened at 44100 Hz, signed 16-bit, mono, which matches
    ``make_beep``. If the machine has no audio device, the preview still runs
    and the on-screen status still says ``beep``.
    """

    def __init__(self, frequency_hz: float, duration_s: float) -> None:
        self._sound: pygame.mixer.Sound | None = None
        self._channel: pygame.mixer.Channel | None = None
        self._ready = False
        started = False
        try:
            # pre_init then init is the documented way to set the format on
            # platforms that start audio together with the display modules.
            pygame.mixer.pre_init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
            pygame.init()
            started = True
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
            samples = make_beep(frequency_hz, duration_s)
            self._sound = pygame.mixer.Sound(buffer=samples.tobytes())
            self._ready = True
        except pygame.error as exc:
            if started:
                pygame.quit()
            print(
                f"Audio unavailable ({exc}). The window will still show a beep status.",
                file=sys.stderr,
            )

    def beep(self) -> None:
        if not self._ready or self._sound is None:
            return
        if self._channel is not None and self._channel.get_busy():
            return
        self._channel = self._sound.play()

    def stop(self) -> None:
        if self._channel is not None and self._channel.get_busy():
            self._channel.stop()

    def close(self) -> None:
        if not self._ready:
            return
        if pygame.mixer.get_init() is not None:
            pygame.mixer.stop()
            pygame.mixer.quit()
        pygame.quit()
        self._ready = False
