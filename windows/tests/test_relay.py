"""Phone -> PC relay server probe: runs the app's real RelayHandler standalone
on a free port with a fake FIFO + token. No tray, no mic, no paste.

Run: windows\\.venv\\Scripts\\python.exe -m unittest windows\\tests\\test_relay.py -v
"""

import http.client
import json
import os
import queue
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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


if __name__ == "__main__":
    unittest.main()
