"""PC hotkey -> phone session: desired state never stays "recording" after the
session ends (NEW-2), and the 60 s handover keeps paste order [head, tail]
(NEW-1). The relay server is real (loopback, port 0); nothing is pasted.

Run (from windows/): .venv\\Scripts\\python -m unittest tests.test_phone_session -v
"""

import http.client
import json
import os
import queue
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gemini_mic  # noqa: E402

TOKEN = "TESTTOKEN123"


class PhoneSessionTest(unittest.TestCase):
    def setUp(self):
        self.logged = []
        self.pasted = []
        self._saved = (gemini_mic.log, gemini_mic.beep, gemini_mic.key_matches,
                       gemini_mic.PHONE_TEXT_SEC)
        gemini_mic.log = self.logged.append
        gemini_mic.beep = lambda *a: None
        gemini_mic.key_matches = lambda key, target: True
        self.jobs = queue.Queue()
        self.server = gemini_mic.make_relay_server(0, self.jobs, lambda: TOKEN)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        app = object.__new__(gemini_mic.GeminiMicApp)
        app.relay_server = self.server
        app.jobs = self.jobs
        app.phone_lock = threading.Lock()
        app.recording = False
        app.hotkey_down = True
        app.hotkey_target = None
        app.chunk_chain = 0
        app.phone_recording = True
        app.phone_acked = True
        app.phone_falling_back = False
        app.phone_stopped_seq = 0
        app.phone_start_seq = gemini_mic.relay_set_state(self.server, "recording")
        app.set_state = lambda s: None
        app.paste_text = self.pasted.append
        app.start_recording = lambda: None
        self.app = app

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        (gemini_mic.log, gemini_mic.beep, gemini_mic.key_matches,
         gemini_mic.PHONE_TEXT_SEC) = self._saved

    def post_text(self, text):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=5)
        conn.request("POST", "/", body=json.dumps({"token": TOKEN, "text": text}).encode(),
                     headers={"Content-Type": "application/json"})
        try:
            return conn.getresponse().status
        finally:
            conn.close()

    def wait_for(self, cond, cap=5.0):
        end = time.monotonic() + cap
        while time.monotonic() < end and not cond():
            time.sleep(0.02)
        return cond()

    # -- NEW-2 ---------------------------------------------------------------

    def test_set_state_raising_still_sends_stop(self):
        def boom(state):
            raise OSError("WinError 1402")
        self.app.set_state = boom
        self.app.phone_recording = False  # _on_release already cleared it
        self.app._phone_release(True, True)
        self.assertEqual(self.server.desired_state, "idle")
        self.assertTrue(any("tray update failed" in l for l in self.logged))

    def test_stopped_ack_racing_release_sets_idle(self):
        # the key is already up (hotkey_down=False) but _on_release has not
        # taken the phone lock yet when the phone's "stopped" lands
        self.app.hotkey_down = False
        self.app._phone_ack("stopped", self.app.phone_start_seq, "")
        self.assertFalse(self.app.phone_recording)
        self.assertEqual(self.server.desired_state, "idle")

    def test_release_after_session_ended_sets_idle(self):
        # session ended elsewhere while desired is still "recording"
        self.app.phone_recording = False
        self.app._on_release(object())
        self.assertEqual(self.server.desired_state, "idle")

    # -- NEW-1 ---------------------------------------------------------------

    def handover_then_release(self):
        threading.Thread(target=self.app._job_worker, daemon=True).start()
        self.app._phone_ack("stopped", self.app.phone_start_seq, "cap")  # key held
        self.assertEqual(self.server.desired_state, "idle")
        # released: the local tail is ready BEFORE the phone's head text
        self.jobs.put(("relay", "tail"))

    def test_late_head_pastes_before_tail(self):
        self.handover_then_release()
        time.sleep(0.4)
        self.assertEqual(self.pasted, [])  # the tail waits behind the head slot
        self.assertEqual(self.post_text("head"), 200)
        self.assertTrue(self.wait_for(lambda: len(self.pasted) == 2))
        self.assertEqual(self.pasted, ["head", "tail"])

    def test_missing_head_skipped_after_cap(self):
        gemini_mic.PHONE_TEXT_SEC = 0.3
        self.handover_then_release()
        self.assertTrue(self.wait_for(lambda: self.pasted == ["tail"]))
        self.assertTrue(any("phone: head missing" in l for l in self.logged))
        # a text after the cap is no longer captured by the stale slot
        self.assertIsNone(self.server.pending_head)
        self.assertEqual(self.post_text("late"), 200)
        self.assertTrue(self.wait_for(lambda: self.pasted == ["tail", "late"]))

    def test_no_text_reason_parks_no_head(self):
        self.app._phone_ack("stopped", self.app.phone_start_seq, "silent")
        self.assertTrue(self.jobs.empty())
        self.assertIsNone(self.server.pending_head)


if __name__ == "__main__":
    unittest.main()
