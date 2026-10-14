"""Phone -> PC relay server probe: runs the app's real RelayHandler standalone
on a free port with a fake FIFO + token. No tray, no mic, no paste.

Run: windows\\.venv\\Scripts\\python.exe -m unittest windows\\tests\\test_relay.py -v
"""

import http.client
import json
import os
import queue
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GEMINI_MIC_LOG_PATH", os.path.join(tempfile.gettempdir(), "gemini_mic_test.log"))
import gemini_mic  # noqa: E402

TOKEN = "3F9A1C7B"


class RelayServerTest(unittest.TestCase):
    def setUp(self):
        # Capture log() instead of writing to the live %APPDATA% log.
        self.logged = []
        self._orig_log = gemini_mic.log
        gemini_mic.log = self.logged.append
        self.jobs = queue.Queue()
        self.server = gemini_mic.make_relay_server(0, self.jobs, lambda: TOKEN)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        gemini_mic.log = self._orig_log
        for line in self.logged:  # never the token, never the text
            self.assertNotIn(TOKEN, line)
            self.assertNotIn("salom", line)

    def request(self, method, path, payload=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {} if body is None else {"Content-Type": "application/json; charset=utf-8"}
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        data = json.loads(resp.read().decode("utf-8"))
        conn.close()
        return resp.status, data

    def test_binds_loopback_only(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_wrong_token_403_and_queue_empty(self):
        status, data = self.request("POST", "/", {"token": "DEADBEEF", "text": "salom"})
        self.assertEqual(status, 403)
        self.assertEqual(data, {"ok": False, "error": "token"})
        self.assertTrue(self.jobs.empty())

    def test_missing_token_403(self):
        status, _ = self.request("POST", "/", {"text": "salom"})
        self.assertEqual(status, 403)
        self.assertTrue(self.jobs.empty())

    def test_right_token_200_and_job_queued(self):
        status, data = self.request("POST", "/", {"token": TOKEN, "text": "salom dunyo"})
        self.assertEqual(status, 200)
        self.assertEqual(data, {"ok": True})
        self.assertEqual(self.jobs.get_nowait(), ("relay", "salom dunyo"))

    def test_query_token_accepted(self):
        status, _ = self.request("POST", "/?token=" + TOKEN, {"text": "salom"})
        self.assertEqual(status, 200)
        self.assertEqual(self.jobs.get_nowait(), ("relay", "salom"))

    def test_mic_prefix_post_accepted(self):
        status, _ = self.request("POST", "/mic/anything", {"token": TOKEN, "text": "matn"})
        self.assertEqual(status, 200)
        self.assertEqual(self.jobs.get_nowait(), ("relay", "matn"))

    def test_ping_200_without_token(self):
        for path in ("/", "/ping", "/mic"):
            status, data = self.request("GET", path)
            self.assertEqual(status, 200, path)
            self.assertEqual(data, {"ok": True, "app": "gemini-mic"})

    def test_empty_text_400(self):
        status, _ = self.request("POST", "/", {"token": TOKEN, "text": "   "})
        self.assertEqual(status, 400)
        self.assertTrue(self.jobs.empty())

    def test_25k_chars_413(self):
        status, _ = self.request("POST", "/", {"token": TOKEN, "text": "a" * 25000})
        self.assertEqual(status, 413)
        self.assertTrue(self.jobs.empty())

    # -- PC hotkey -> phone recording: /cmd desired-state long-poll + /ack ----

    def test_cmd_unchanged_state_after_wait(self):
        t0 = time.monotonic()
        status, data = self.request("GET", "/cmd?token=%s&wait=1&have=0" % TOKEN)
        elapsed = time.monotonic() - t0
        self.assertEqual(status, 200)
        self.assertEqual(data, {"ok": True, "state": "idle", "seq": 0})
        self.assertGreaterEqual(elapsed, 0.9)
        self.assertLess(elapsed, 3.0)
        self.assertGreaterEqual(self.server.phone_seen, t0)  # Windows' 15.6 ms tick (F4)
        self.assertEqual(self.server.parked, 0)
        self.assertFalse(any("-> phone" in line for line in self.logged))

    def test_cmd_without_have_returns_state_at_once(self):
        t0 = time.monotonic()
        _, data = self.request("GET", "/cmd?token=%s&wait=5" % TOKEN)
        self.assertLess(time.monotonic() - t0, 1.0)
        self.assertEqual(data, {"ok": True, "state": "idle", "seq": 0})

    def test_cmd_desired_state_survives_repeat_polls(self):
        seq = gemini_mic.relay_set_state(self.server, "recording")
        self.assertEqual(seq, 1)
        status, data = self.request("GET", "/cmd?token=%s&wait=1&have=0" % TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(data, {"ok": True, "state": "recording", "seq": 1})
        self.assertIn("relay: state recording #1 -> phone", self.logged)
        # the phone already has seq 1: the poll parks, then repeats the state
        _, data = self.request("GET", "/cmd?token=%s&wait=1&have=1" % TOKEN)
        self.assertEqual(data, {"ok": True, "state": "recording", "seq": 1})
        seq = gemini_mic.relay_set_state(self.server, "idle", discard=True)
        _, data = self.request("GET", "/cmd?token=%s&wait=1&have=1" % TOKEN)
        self.assertEqual(data, {"ok": True, "state": "idle", "seq": 2, "discard": True})

    def test_dead_parked_poll_does_not_swallow_the_change(self):
        """F2: a poll whose client vanished still gets the change - and so
        does the live poll, within one round-trip."""
        results = {}

        def poll(name):
            t0 = time.monotonic()
            _, data = self.request("GET", "/cmd?token=%s&wait=5&have=0" % TOKEN)
            results[name] = (data, time.monotonic() - t0)

        dead = threading.Thread(target=poll, args=("dead",))
        dead.start()
        time.sleep(0.2)
        live = threading.Thread(target=poll, args=("live",))
        live.start()
        time.sleep(0.2)
        self.assertEqual(self.server.parked, 2)
        t_set = time.monotonic()
        gemini_mic.relay_set_state(self.server, "recording")
        live.join(3)
        dead.join(3)
        self.assertEqual(results["live"][0], {"ok": True, "state": "recording", "seq": 1})
        self.assertEqual(results["dead"][0], {"ok": True, "state": "recording", "seq": 1})
        self.assertLess(time.monotonic() - t_set, 1.0)
        # stop never acked: desired stays idle, a later poll still gets it
        stop_seq = gemini_mic.relay_set_state(self.server, "idle")
        time.sleep(0.3)
        _, data = self.request("GET", "/cmd?token=%s&wait=5&have=1" % TOKEN)
        self.assertEqual(data, {"ok": True, "state": "idle", "seq": stop_seq})
        self.assertEqual(self.server.ack, (None, 0))

    def test_ack_sets_event_state_seq(self):
        self.assertFalse(self.server.ack_event.is_set())
        seen = []
        self.server.on_ack = lambda *a: seen.append(a)
        status, data = self.request("POST", "/ack", {"token": TOKEN, "state": "recording", "seq": 3})
        self.assertEqual(status, 200)
        self.assertEqual(data, {"ok": True})
        self.assertTrue(self.server.ack_event.is_set())
        self.assertEqual(self.server.ack, ("recording", 3))
        self.request("POST", "/ack", {"token": TOKEN, "state": "stopped", "seq": 4, "reason": "short"})
        self.assertEqual(self.server.ack, ("stopped", 4))
        # the handler replies BEFORE it calls on_ack: wait for the callback
        end = time.monotonic() + 2
        while len(seen) < 2 and time.monotonic() < end:
            time.sleep(0.01)
        self.assertEqual(seen, [("recording", 3, ""), ("stopped", 4, "short")])
        self.assertTrue(self.jobs.empty())  # an ack is never pasted

    def test_cmd_wrong_token_403_counts_toward_lockout(self):
        for _ in range(gemini_mic.RELAY_LOCK_AFTER):
            status, data = self.request("GET", "/cmd?token=WRONG&wait=1")
            self.assertEqual(status, 403)
            self.assertEqual(data, {"ok": False, "error": "token"})
        self.assertEqual(self.server.phone_seen, float("-inf"))
        status, _ = self.request("GET", "/cmd?token=%s&wait=1" % TOKEN)
        self.assertEqual(status, 429)

    def test_mic_prefix_cmd_and_ack_accepted(self):
        status, data = self.request("GET", "/mic/cmd?token=%s&wait=0" % TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(data, {"ok": True, "state": "idle", "seq": 0})
        status, _ = self.request("POST", "/mic/ack", {"token": TOKEN, "state": "stopped", "seq": 1})
        self.assertEqual(status, 200)
        self.assertEqual(self.server.ack[0], "stopped")

    def test_phone_connected_parked_or_recent(self):
        """F7: false at boot, true while a poll is parked, false 3 s after."""
        app = object.__new__(gemini_mic.GeminiMicApp)
        app.relay_server = self.server
        self.assertFalse(app.phone_connected())
        th = threading.Thread(target=self.request,
                              args=("GET", "/cmd?token=%s&wait=1&have=0" % TOKEN))
        th.start()
        time.sleep(0.3)
        self.assertTrue(app.phone_connected())
        th.join(3)
        self.assertTrue(app.phone_connected())  # replied < 3 s ago
        self.server.phone_seen -= gemini_mic.PHONE_SEEN_SEC + 0.1
        self.assertFalse(app.phone_connected())

    def test_text_post_sets_last_text_at(self):
        self.assertEqual(self.server.last_text_at, 0.0)
        self.request("POST", "/", {"token": TOKEN, "text": "salom"})
        self.assertGreater(self.server.last_text_at, 0.0)


if __name__ == "__main__":
    unittest.main()


class LockoutTest(unittest.TestCase):
    def test_five_wrong_tokens_lock_for_a_minute(self):
        import queue as _q, gemini_mic as gm
        jobs = _q.Queue()
        srv = gm.make_relay_server(0, jobs, lambda: "ABCDEF123456")
        port = srv.server_address[1]
        th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
        try:
            def post(payload):
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                conn.request("POST", "/", body=json.dumps(payload).encode(),
                             headers={"Content-Type": "application/json"})
                return conn.getresponse().status
            codes = [post({"token": "WRONG", "text": "x"}) for _ in range(6)]
            self.assertEqual(codes[:5], [403] * 5)
            self.assertEqual(codes[5], 429)
            # the right token is refused too while locked
            self.assertEqual(post({"token": "ABCDEF123456", "text": "x"}), 429)
            self.assertTrue(jobs.empty())
            self.assertEqual(len(gm.new_relay_token()), 12)
        finally:
            srv.shutdown()
