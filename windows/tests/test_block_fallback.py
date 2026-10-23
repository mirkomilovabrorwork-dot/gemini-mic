"""promptFeedback.blockReason with no candidates -> fall back to the other
model (2026-10-23: 3.7-flash blocked two long takes with OTHER; 3.5 was fine)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GEMINI_MIC_LOG_PATH", os.path.join(tempfile.gettempdir(), "gemini_mic_test.log"))
import gemini_mic  # noqa: E402


class FakeResp:
    status_code = 200

    def __init__(self, data):
        self._d = data

    def json(self):
        return self._d


class BlockFallbackTest(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self._saved = (gemini_mic.requests.post, gemini_mic.log)
        gemini_mic.log = lambda *a: None

        def post(url, **k):
            self.calls.append(url)
            if gemini_mic.FALLBACK_MODEL in url:
                return FakeResp({"candidates": [{"finishReason": "STOP",
                                                 "content": {"parts": [{"text": "Salom dunyo."}]}}]})
            return FakeResp({"promptFeedback": {"blockReason": "OTHER"}})
        gemini_mic.requests.post = post

    def tearDown(self):
        gemini_mic.requests.post, gemini_mic.log = self._saved

    def test_blocked_primary_falls_back(self):
        text = gemini_mic.gemini_transcribe("k", "gemini-3.7-flash", "uz_en", b"RIFF" + b"\0" * 100)
        self.assertEqual(text, "Salom dunyo.")
        self.assertEqual(len(self.calls), 2)
        self.assertIn(gemini_mic.FALLBACK_MODEL, self.calls[1])


if __name__ == "__main__":
    unittest.main()
