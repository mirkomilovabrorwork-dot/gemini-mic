"""Speech gate on the owner's MICUSB1 levels (2026-11-05): a quiet real take
(~1.8x the room floor) must pass; steady room noise must still be rejected."""
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GEMINI_MIC_LOG_PATH", os.path.join(tempfile.gettempdir(), "gemini_mic_test.log"))
import gemini_mic  # noqa: E402

SR = gemini_mic.SAMPLE_RATE


def noise(sec, rms, seed=0):
    return np.random.default_rng(seed).normal(0, rms, int(sec * SR))


class SpeechGateTest(unittest.TestCase):
    def test_quiet_real_take_passes(self):
        # like 20261105-005947 "Ya'ni natija nima bo'ldi?": floor 500, voice ~900
        a = np.concatenate([noise(1.0, 500), noise(1.0, 900, 1), noise(1.0, 500, 2)])
        self.assertTrue(gemini_mic.has_speech(a, room_floor=500.0))

    def test_very_quiet_long_take_passes(self):
        # like 20261105-011220 (45 s, real speech only ~1.35x the floor)
        a = np.concatenate([noise(2.0, 500), noise(2.0, 680, 1)])
        self.assertTrue(gemini_mic.has_speech(a, room_floor=500.0))

    def test_steady_room_noise_rejected(self):
        # room tone wobbling up to 1.2x its floor is still nothing
        a = np.concatenate([noise(2.0, 500), noise(1.0, 600, 1)])
        self.assertFalse(gemini_mic.has_speech(a, room_floor=500.0))


if __name__ == "__main__":
    unittest.main()
