"""Raw-capture self-heal probe: a WASAPI raw stream that delivers digital zero
must be reopened on the same device in shared mode, with the gain OFF.
sd.InputStream is faked - no real mic is opened.

Run (from windows/): .venv\Scripts\python -m unittest tests.test_raw_fallback -v
"""

import collections
import os
import sys
import threading
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gemini_mic  # noqa: E402

sd = gemini_mic.sd
DEV = 7


class FakeStream:
    opened = []  # (device, raw) per open
    raw_level = 0  # sample value a raw stream delivers

    def __init__(self, device=None, callback=None, extra_settings=None, **kw):
        self.device = device
        self.callback = callback
        self.raw = extra_settings is not None and extra_settings._streaminfo.streamOption == 1
        self.active = False
        self.closed = False
        FakeStream.opened.append((device, self.raw))

    def start(self):
        self.active = True
        level = FakeStream.raw_level if self.raw else 400
        block = np.full((gemini_mic.STREAM_BLOCK, 1), level, dtype=np.int16)
        for _ in range(3):
            self.callback(block, gemini_mic.STREAM_BLOCK, None, None)

    def close(self):
        self.active = False
        self.closed = True


class RawFallbackTest(unittest.TestCase):
    def setUp(self):
        self.logged = []
        self._saved = (gemini_mic.log, sd.InputStream, sd.query_devices, sd.query_hostapis)
        gemini_mic.log = self.logged.append
        sd.InputStream = FakeStream
        sd.query_devices = lambda dev=None: {"name": "Microphone Array (AMD Audio Device)", "hostapi": 0}
        sd.query_hostapis = lambda idx=None: {"name": "Windows WASAPI"}
        FakeStream.opened = []
        app = object.__new__(gemini_mic.GeminiMicApp)
        app.cfg = {"raw_capture": True}
        app.stream_lock = threading.Lock()
        app.stream = None
        app.ring = collections.deque(maxlen=64)
        app.recording = False
        app.frames = []
        app.last_block = 0.0
        app.stream_raw = False
        app.resolve_input_device = lambda: [DEV]
        self.app = app

    def tearDown(self):
        gemini_mic.log, sd.InputStream, sd.query_devices, sd.query_hostapis = self._saved

    def test_digital_zero_raw_reopens_shared_without_gain(self):
        FakeStream.raw_level = 0
        self.assertTrue(self.app.ensure_stream())
        self.assertEqual(FakeStream.opened, [(DEV, True), (DEV, False)])
        self.assertFalse(self.app.stream_raw)
        self.assertFalse(self.app.stream.raw)
        self.assertTrue(self.app.stream.active)
        self.assertTrue(any("digital zero" in l and "reopening shared" in l for l in self.logged))
        self.assertTrue(any("(WASAPI shared after raw was silent, " in l for l in self.logged))
        # shared blocks reach the ring un-gained
        self.assertEqual(int(self.app.ring[-1].max()), 400)

    def test_live_raw_stays_raw(self):
        FakeStream.raw_level = 50
        self.assertTrue(self.app.ensure_stream())
        self.assertEqual(FakeStream.opened, [(DEV, True)])
        self.assertTrue(self.app.stream_raw)
        self.assertFalse(any("digital zero" in l for l in self.logged))


if __name__ == "__main__":
    unittest.main()
