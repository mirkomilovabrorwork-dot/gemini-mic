"""Raw-capture self-heal probe: a WASAPI raw stream that delivers digital zero
must be reopened on the same device in shared mode, with the gain OFF.
sd.InputStream is faked - no real mic is opened.

Run (from windows/): .venv\Scripts\python -m unittest tests.test_raw_fallback -v
"""

import collections
import os
import sys
import threading
import time
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gemini_mic  # noqa: E402

sd = gemini_mic.sd
DEV = 7


class FakeStream:
    """Delivers a block every 0.1 s on its own thread, the FIRST one 0.1 s
    after start() (a real AMD array: 0.56 s). raw_level = what a raw stream
    carries; raw_zero_blocks = leading zero blocks before it (measured: the
    first ~0.2 s are digital zero even on a healthy raw device)."""
    opened = []  # (device, raw) per open
    raw_level = 0  # sample value a raw stream delivers
    raw_zero_blocks = 0
    first_delay = 0.1

    def __init__(self, device=None, callback=None, extra_settings=None, **kw):
        self.device = device
        self.callback = callback
        self.raw = extra_settings is not None and extra_settings._streaminfo.streamOption == 1
        self.active = False
        self.closed = False
        FakeStream.opened.append((device, self.raw))

    def start(self):
        self.active = True
        threading.Thread(target=self._feed, daemon=True).start()

    def _feed(self):
        n = 0
        time.sleep(FakeStream.first_delay - 0.1)
        while True:
            time.sleep(0.1)
            if self.closed:
                return
            if self.raw:
                level = 0 if n < FakeStream.raw_zero_blocks else FakeStream.raw_level
            else:
                level = 400
            block = np.full((gemini_mic.STREAM_BLOCK, 1), level, dtype=np.int16)
            self.callback(block, gemini_mic.STREAM_BLOCK, None, None)
            n += 1

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
        FakeStream.raw_zero_blocks = 0
        FakeStream.first_delay = 0.1
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
        if self.app.stream is not None:
            self.app.stream.close()
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
        time.sleep(0.3)
        self.assertEqual(int(self.app.ring[-1].max()), 400)

    def test_live_raw_stays_raw(self):
        FakeStream.raw_level = 50
        self.assertTrue(self.app.ensure_stream())
        self.assertEqual(FakeStream.opened, [(DEV, True)])
        self.assertTrue(self.app.stream_raw)
        self.assertFalse(any("digital zero" in l for l in self.logged))

    def test_raw_with_zero_lead_in_stays_raw(self):
        # the measured AMD case: first ~0.2 s digital zero, then real audio
        FakeStream.raw_level = 150
        FakeStream.raw_zero_blocks = 2
        FakeStream.first_delay = 0.56
        self.assertTrue(self.app.ensure_stream())
        self.assertEqual(FakeStream.opened, [(DEV, True)])
        self.assertTrue(self.app.stream_raw)
        self.assertFalse(any("digital zero" in l for l in self.logged))

    def test_no_block_keeps_stream(self):
        # a stream that never calls back is left to the dead-stream watch
        self.assertFalse(self.app._raw_is_digital_zero(first_wait=0.2))

    def test_zero_limit_is_two_ungained(self):
        # ring blocks are un-gained now: |sample| <= 2 is digital zero, 3 is audio
        FakeStream.raw_level = 2
        self.assertTrue(self.app.ensure_stream())
        self.assertEqual(FakeStream.opened, [(DEV, True), (DEV, False)])
        self.app.stream.close()
        FakeStream.opened = []
        FakeStream.raw_level = 3
        self.assertTrue(self.app.ensure_stream())
        self.assertEqual(FakeStream.opened, [(DEV, True)])
        self.assertTrue(self.app.stream_raw)

    def test_raw_blocks_reach_ring_ungained(self):
        FakeStream.raw_level = 50
        self.assertTrue(self.app.ensure_stream())
        time.sleep(0.3)
        self.assertEqual(int(self.app.ring[-1].max()), 50)


def tone(peak, blocks, hz=250):
    """int16 sine blocks (250 Hz: whole cycles per 0.1 s block, peak exact)."""
    t = np.arange(gemini_mic.STREAM_BLOCK) / gemini_mic.SAMPLE_RATE
    b = np.round(peak * np.sin(2 * np.pi * hz * t)).astype(np.int16)
    return [b.copy() for _ in range(blocks)]


class ClipSafeGainTest(unittest.TestCase):
    """A.2: one clip-safe gain per recording, applied in stop_recording_and_transcribe."""

    def setUp(self):
        self.logged = []
        self.saved_wavs = []
        self._saved = (gemini_mic.log, gemini_mic.save_clip)
        gemini_mic.log = self.logged.append
        gemini_mic.save_clip = self.saved_wavs.append
        app = object.__new__(gemini_mic.GeminiMicApp)
        app.lock = threading.Lock()
        app.stream_raw = True
        app.recording = True
        app.record_start = time.monotonic() - 3.0
        app.last_dictation = 0.0
        app.room_floor = None
        app.jobs = __import__("queue").Queue()
        app.set_state = lambda s: None
        app._tooltip = lambda t: None
        self.app = app

    def tearDown(self):
        gemini_mic.log, gemini_mic.save_clip = self._saved

    def run_clip(self, frames, room_floor=None):
        self.app.frames = frames
        self.app.recording = True
        self.app.room_floor = room_floor
        self.app.stop_recording_and_transcribe()
        import io, wave
        with wave.open(io.BytesIO(self.saved_wavs[-1])) as wf:
            return np.frombuffer(wf.readframes(wf.getnframes()), np.int16)

    def test_quiet_clip_gets_full_gain(self):
        self.assertEqual(self.app.gain_for(tone(300, 10)), gemini_mic.RAW_GAIN)
        audio = self.run_clip(tone(300, 10))
        self.assertGreaterEqual(int(np.abs(audio.astype(np.int32)).max()), 1790)
        self.assertTrue(any("gain=6.0x" in l and "clip: rms=" in l for l in self.logged))

    def test_loud_clip_is_not_clipped(self):
        self.assertAlmostEqual(self.app.gain_for(tone(20000, 10)), 1.4)
        audio = self.run_clip(tone(20000, 10))
        self.assertLessEqual(int(np.abs(audio.astype(np.int32)).max()), 28000)
        self.assertEqual(int((np.abs(audio.astype(np.int32)) >= 32000).sum()), 0)
        self.assertTrue(any("gain=1.4x" in l for l in self.logged))

    def test_shared_stream_is_not_gained(self):
        self.app.stream_raw = False
        self.assertEqual(self.app.gain_for(tone(300, 10)), 1.0)

    def test_quiet_speech_verdict_unchanged(self):
        # raw room tone rms 20 then speech rms 150 (sine peak 212) -> accepted,
        # clip AND room floor gained by the same 6x
        room = tone(28, 5)
        speech = tone(212, 15)
        self.run_clip(room + speech, room_floor=20.0)
        self.assertEqual(self.app.jobs.qsize(), 1)
        self.assertFalse(any("no sustained speech" in l for l in self.logged))


if __name__ == "__main__":
    unittest.main()
