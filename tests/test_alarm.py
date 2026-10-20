"""The beep is generated as signed 16-bit mono samples. No audio device needed."""

import numpy as np

from eye.alarm import SAMPLE_RATE, make_beep


def test_beep_samples_match_the_mixer_format():
    duration_s = 0.4
    samples = make_beep(880, duration_s)
    assert samples.dtype == np.int16
    assert samples.ndim == 1
    assert len(samples) == int(SAMPLE_RATE * duration_s)
    assert int(samples.max()) > 0
    assert int(samples.min()) < 0
