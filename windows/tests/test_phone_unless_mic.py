"""phone_unless_mic: a live stream on the named local mic beats the phone
(owner 2026-10-23: external mic first, the phone only when it is absent)."""
import os
import sys
import tempfile
import threading
import time
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GEMINI_MIC_LOG_PATH", os.path.join(tempfile.gettempdir(), "gemini_mic_test.log"))
import gemini_mic  # noqa: E402

NAMES = {15: "Microphone (MICUSB1)", 14: "Microphone Array (AMD Audio Device)"}


class PhoneUnlessMicTest(unittest.TestCase):
    def setUp(self):
        self._saved = (gemini_mic.sd.query_devices, gemini_mic.log)
        gemini_mic.sd.query_devices = lambda i=None, *a, **k: {"name": NAMES[i]}
        gemini_mic.log = lambda *a: None
        app = object.__new__(gemini_mic.GeminiMicApp)
        app.cfg = {"phone_unless_mic": "MICUSB1", "phone_trigger": True}
        app.get_config = lambda: app.cfg
        app.stream = types.SimpleNamespace(device=15)
        app.last_block = time.monotonic()
        app.hotkey_target = None
        app.hotkey_down = False
        app.recording = False
        app.phone_recording = False
        app.phone_falling_back = False
        app.phone_connected = lambda: True
        self.started = threading.Event()
        app.start_recording = self.started.set
        app.set_state = lambda s: None
        self.app = app
        self._km = gemini_mic.key_matches
        gemini_mic.key_matches = lambda k, t: True

    def tearDown(self):
        gemini_mic.sd.query_devices, gemini_mic.log = self._saved
        gemini_mic.key_matches = self._km

    def test_live_external_mic_beats_phone(self):
        self.assertTrue(self.app.preferred_mic_live())
        self.app._on_press("ctrl")
        self.assertTrue(self.started.wait(1))
        self.assertFalse(self.app.phone_recording)

    def test_other_mic_open_uses_phone(self):
        self.app.stream = types.SimpleNamespace(device=14)
        self.assertFalse(self.app.preferred_mic_live())

    def test_dead_external_stream_uses_phone(self):
        self.app.last_block = time.monotonic() - 5
        self.assertFalse(self.app.preferred_mic_live())

    def test_no_stream_or_empty_setting_uses_phone(self):
        self.app.stream = None
        self.assertFalse(self.app.preferred_mic_live())
        self.app.stream = types.SimpleNamespace(device=15)
        self.app.cfg["phone_unless_mic"] = ""
        self.assertFalse(self.app.preferred_mic_live())


if __name__ == "__main__":
    unittest.main()
