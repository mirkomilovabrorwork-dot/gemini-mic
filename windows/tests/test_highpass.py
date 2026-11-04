"""Rumble high-pass in front of the model (quiet speech fix 2026-11-05)."""
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("GEMINI_MIC_LOG_PATH", os.path.join(tempfile.gettempdir(), "gemini_mic_test.log"))
import gemini_mic  # noqa: E402

SR = gemini_mic.SAMPLE_RATE


def tone(freq, sec, amp):
    t = np.arange(int(SR * sec)) / SR
    return amp * np.sin(2 * np.pi * freq * t)


def rms(a):
    return float(np.sqrt(np.mean(a.astype(np.float64) ** 2)))


class HighpassTest(unittest.TestCase):
    def test_rumble_cut_voice_kept(self):
        rumble = tone(50, 2.0, 3000)
        voice = tone(1000, 2.0, 1000)
        out = gemini_mic.highpass(np.round(rumble + voice).astype(np.int16))
        self.assertEqual(out.dtype, np.int16)
        self.assertEqual(out.size, rumble.size)
        # 50 Hz drops ~15 dB (2nd order at 120 Hz), 1 kHz passes within 1 %
        self.assertLess(rms(gemini_mic.highpass(np.round(rumble).astype(np.int16))), rms(rumble) * 0.25)
        self.assertLess(rms(out), rms(rumble + voice) * 0.5)
        self.assertAlmostEqual(rms(gemini_mic.highpass(np.round(voice).astype(np.int16))), rms(voice), delta=rms(voice) * 0.01)

    def test_loud_input_never_wraps(self):
        a = np.full(SR, 32767, np.int16)
        a[::2] = -32768
        out = gemini_mic.highpass(a)
        self.assertLessEqual(int(out.max()), 32767)
        self.assertGreaterEqual(int(out.min()), -32768)

    def test_tiny_input_passes_through(self):
        for a in (np.zeros(0, np.int16), np.array([5], np.int16)):
            self.assertTrue(np.array_equal(gemini_mic.highpass(a), a))


if __name__ == "__main__":
    unittest.main()
