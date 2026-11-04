"""Only-my-voice (owner 2026-11-05): audio far quieter than the speaker's own
voice is muted before the model hears it; his own speech is left untouched."""
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GEMINI_MIC_LOG_PATH", os.path.join(tempfile.gettempdir(), "gemini_mic_test.log"))
import gemini_mic  # noqa: E402

SR = gemini_mic.SAMPLE_RATE


def tone(sec, amp):
    t = np.arange(int(sec * SR)) / SR
    return (amp * np.sin(2 * np.pi * 220 * t)).astype(np.int16)


class NearVoiceGateTest(unittest.TestCase):
    def test_far_voice_after_speech_is_muted(self):
        near, far = tone(1.0, 10000), tone(1.5, 1600)  # far ~16 dB under him
        out = gemini_mic.near_voice_gate(np.concatenate([near, far]))
        self.assertTrue(np.array_equal(out[:int(0.9 * SR)], near[:int(0.9 * SR)]))
        self.assertEqual(int(np.abs(out[-int(0.8 * SR):]).max()), 0)

    def test_soft_word_end_inside_hold_is_kept(self):
        near, soft = tone(1.0, 10000), tone(0.2, 1600)
        out = gemini_mic.near_voice_gate(np.concatenate([near, soft, tone(1.0, 10000)]))
        self.assertGreater(int(np.abs(out[SR:SR + int(0.2 * SR)]).max()), 1000)

    def test_steady_speech_untouched(self):
        a = tone(2.0, 8000)
        self.assertTrue(np.array_equal(gemini_mic.near_voice_gate(a), a))


if __name__ == "__main__":
    unittest.main()
