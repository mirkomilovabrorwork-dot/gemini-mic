r"""Boosted mic monitor in gemini_mic.py (stub sounddevice, no real audio).

  * off (default): nothing starts, the mic callback feeds nothing
  * on: output stream opens on the matching device; blocks come out gained + tanh-limited
  * full queue drops the oldest block and never blocks the mic callback
  * missing device logs "device not found" once, dictation path unaffected

Run: windows\.venv\Scripts\python.exe -m pytest windows\tests\test_boost_monitor.py -q
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GEMINI_MIC_LOG_PATH", os.path.join(tempfile.gettempdir(), "gemini_mic_test.log"))
import gemini_mic  # noqa: E402

DEVICES = [
    {"name": "Microphone (EarPods)", "max_input_channels": 1, "max_output_channels": 0},
    {"name": "Speakers", "max_input_channels": 0, "max_output_channels": 2},
    {"name": "CABLE Input (VB-Audio Virtual Cable)", "max_input_channels": 0, "max_output_channels": 2},
]


class BoostBase(unittest.TestCase):
    cfg = {}
    devices = DEVICES

    def setUp(self):
        self.logs = []
        self._saved_log = gemini_mic.log
        gemini_mic.log = lambda m, *a: self.logs.append(m)
        self.sd = mock.MagicMock()
        self.sd.query_devices.side_effect = lambda i=None: self.devices if i is None else self.devices[i]
        patcher = mock.patch.object(gemini_mic, "sd", self.sd)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(setattr, gemini_mic, "log", self._saved_log)
        app = object.__new__(gemini_mic.GeminiMicApp)
        app.cfg = dict(self.cfg)
        app.boost_q = None
        app.boost_out = None
        app._boost_missing_logged = False
        app.ring = []
        app.frames = []
        app.recording = True
        app.last_block = 0.0
        self.app = app

    def mic_block(self, v=1000):
        return np.full((gemini_mic.STREAM_BLOCK, 1), v, dtype=np.int16)


class OffTest(BoostBase):
    cfg = {"boost_monitor": False}

    def test_off_starts_nothing(self):
        self.app._boost_start()
        self.sd.OutputStream.assert_not_called()
        self.assertIsNone(self.app.boost_q)
        self.app._audio_callback(self.mic_block(), 1600, None, None)
        self.assertEqual(len(self.app.frames), 1)


class OnTest(BoostBase):
    cfg = {"boost_monitor": True, "boost_monitor_gain": 4.0, "boost_monitor_device": "CABLE Input"}

    def test_on_opens_cable_and_feeds_gained_limited(self):
        self.app._boost_start()
        kw = self.sd.OutputStream.call_args.kwargs
        self.assertEqual(kw["device"], 2)
        self.assertEqual(kw["samplerate"], gemini_mic.SAMPLE_RATE)
        self.assertEqual(kw["channels"], 1)
        self.assertTrue(any(m.startswith("boost monitor: on -> CABLE Input") and "4.0x" in m for m in self.logs))
        self.app._audio_callback(self.mic_block(1000), 1600, None, None)
        self.app._audio_callback(self.mic_block(30000), 1600, None, None)
        out = np.zeros((gemini_mic.STREAM_BLOCK, 1), dtype=np.int16)
        kw["callback"](out, 1600, None, None)
        expect = int(np.tanh(1000 / 32768 * 4.0) * 32767)
        self.assertEqual(int(out[0, 0]), expect)
        self.assertGreater(int(out[0, 0]), 1000 * 3)  # clearly louder than raw
        kw["callback"](out, 1600, None, None)
        self.assertLess(int(out[0, 0]), 32767)  # soft limit, no hard clip
        self.assertGreater(int(out[0, 0]), 30000)
        kw["callback"](out, 1600, None, None)  # starved -> silence
        self.assertEqual(int(np.abs(out).max()), 0)

    def test_recording_frames_untouched(self):
        self.app._boost_start()
        self.app._audio_callback(self.mic_block(1234), 1600, None, None)
        self.assertEqual(int(self.app.frames[0].max()), 1234)

    def test_full_queue_drops_oldest_never_blocks(self):
        self.app._boost_start()
        for v in range(1, 20):
            self.app._audio_callback(self.mic_block(v), 1600, None, None)  # would hang if it blocked
        q = self.app.boost_q
        self.assertEqual(q.qsize(), 8)
        self.assertEqual(int(q.get_nowait()[0]), 12)  # oldest 11 dropped

    def test_reopen_and_stop(self):
        self.app._boost_start()
        first = self.app.boost_out
        self.app._boost_start()
        first.stop.assert_called_once()
        self.app._boost_stop()
        self.assertIsNone(self.app.boost_q)
        self.assertIn("boost monitor: off", self.logs)


class MissingDeviceTest(BoostBase):
    cfg = {"boost_monitor": True, "boost_monitor_device": "CABLE Input"}
    devices = DEVICES[:2]

    def test_missing_logs_once(self):
        self.app._boost_start()
        self.app._boost_start()
        self.assertEqual(self.logs.count("boost monitor: device not found"), 1)
        self.sd.OutputStream.assert_not_called()
        self.app._audio_callback(self.mic_block(), 1600, None, None)
        self.assertEqual(len(self.app.frames), 1)


if __name__ == "__main__":
    unittest.main()
