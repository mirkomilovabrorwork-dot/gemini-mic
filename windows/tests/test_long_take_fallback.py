"""2026-11-08 handoff: one text up to 5 min, 429 cooldown skips Google, an
ordered fallback chain never loses a take. All network calls are faked
(monkeypatch gemini_mic.requests.post) - no real traffic."""
import os
import sys
import tempfile
import unittest

import requests as real_requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GEMINI_MIC_LOG_PATH", os.path.join(tempfile.gettempdir(), "gemini_mic_test.log"))
import gemini_mic  # noqa: E402


class FakeResp:
    def __init__(self, data, status_code=200):
        self.status_code = status_code
        self.text = "err"
        self._d = data

    def json(self):
        return self._d


def google_ok(text):
    return FakeResp({"candidates": [{"finishReason": "STOP",
                                     "content": {"parts": [{"text": text}]}}]})


WAV = b"RIFF" + b"\0" * 100  # tiny clip: ~0.002 s -> read timeout ~30.0


class LongTakeFallbackTest(unittest.TestCase):
    """google_first cooldown + ordered chain (items 2 and 3 of the handoff)."""

    MODEL = "gemini-3-flash-preview"

    def setUp(self):
        self.calls = []  # (url, model, timeout)
        self._saved = (gemini_mic.requests.post, gemini_mic.log, gemini_mic._google_cooldown_until)
        gemini_mic.log = lambda *a: None
        gemini_mic._google_cooldown_until = 0.0
        gemini_mic.requests.post = self._post

    def tearDown(self):
        gemini_mic.requests.post, gemini_mic.log, gemini_mic._google_cooldown_until = self._saved

    def _post(self, url, **k):
        model = k.get("json", {}).get("model")
        self.calls.append((url, model, k.get("timeout")))
        if "openrouter.ai" in url:
            return self._openrouter(model)
        return self._google()

    # per-test behaviour, overridden in subclasses/tests
    def _google(self):
        r = FakeResp({"error": {"code": 429}}, status_code=429)
        return r

    def _openrouter(self, model):
        return FakeResp({"choices": [{"message": {"content": "Salom dunyo."}}]})

    def _transcribe(self, openrouter_key="or", model=MODEL):
        return gemini_mic.gemini_transcribe("k", model, "uz_en", WAV,
                                            openrouter_key=openrouter_key)

    def google_urls(self):
        return [c for c in self.calls if "openrouter.ai" not in c[0]]

    def test_429_then_openrouter_and_cooldown_skips_google(self):
        # first call: Google 429 -> cooldown armed -> OpenRouter answers
        self.assertEqual(self._transcribe(), "Salom dunyo.")
        self.assertEqual(len(self.google_urls()), 1)
        # second call INSIDE the 600s cooldown: no Google request at all
        self.calls = []
        self.assertEqual(self._transcribe(), "Salom dunyo.")
        self.assertEqual(len(self.google_urls()), 0)
        self.assertEqual(len(self.calls), 1)  # openrouter only
        self.assertEqual(self.calls[0][1], "google/" + self.MODEL)
        # cooldown in the past -> Google is tried again
        self.calls = []
        gemini_mic._google_cooldown_until = 0.0
        self.assertEqual(self._transcribe(), "Salom dunyo.")
        self.assertEqual(len(self.google_urls()), 1)

    def test_openrouter_ssl_then_openrouter_flash(self):
        def _openrouter(model):
            if model == "google/" + self.MODEL:
                raise real_requests.exceptions.SSLError("SSL: WRONG_VERSION_NUMBER")
            return FakeResp({"choices": [{"message": {"content": "Zanjir ishladi."}}]})
        self._openrouter_real = self._openrouter
        self._openrouter = _openrouter
        self.assertEqual(self._transcribe(), "Zanjir ishladi.")
        # chain: google (429), openrouter model (SSL) -> openrouter gemini-2.5-flash
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(self.calls[2][1], "google/gemini-2.5-flash")

    def test_all_steps_fail_raises_last_error(self):
        def _google():
            return FakeResp({"error": {"code": 500}}, status_code=500)

        def _openrouter(model):
            raise real_requests.exceptions.SSLError("boom")
        self._google = _google
        self._openrouter = _openrouter
        with self.assertRaises(gemini_mic.GeminiError):
            self._transcribe()
        # chain = google model, openrouter model, openrouter 2.5-flash, google 2.5-flash
        self.assertEqual(len(self.calls), 4)

    def test_no_key_google_500_still_uses_fallback_model(self):
        def _google():
            if gemini_mic.FALLBACK_MODEL in self.calls[-1][0]:
                return google_ok("Model zanjiri.")
            return FakeResp({"error": {"code": 500}}, status_code=500)
        self._google = _google
        text = self._transcribe(openrouter_key="")
        self.assertEqual(text, "Model zanjiri.")
        self.assertEqual(len(self.calls), 2)
        self.assertIn(gemini_mic.FALLBACK_MODEL, self.calls[1][0])

    def test_no_speech_is_an_answer_not_a_failure(self):
        self._google = lambda: google_ok("NO_SPEECH")
        with self.assertRaises(gemini_mic.GeminiError) as ctx:
            self._transcribe()
        self.assertEqual(str(ctx.exception), "Ovoz eshitilmadi")
        self.assertEqual(len(self.calls), 1)


class LongTakeTimeoutTest(unittest.TestCase):
    """Item 1: AUTO_STOP_SEC 300 and a read timeout that scales with length."""

    def test_auto_stop_sec_is_300(self):
        self.assertEqual(gemini_mic.AUTO_STOP_SEC, 300)

    def test_read_timeout_for_300s_wav(self):
        wav = b"\0" * (44 + 300 * gemini_mic.SAMPLE_RATE * 2)
        self.assertEqual(gemini_mic.read_timeout_for(wav), 105.0)

    def test_timeout_passed_to_post_for_300s_wav(self):
        wav = b"\0" * (44 + 300 * gemini_mic.SAMPLE_RATE * 2)
        seen = []
        saved = (gemini_mic.requests.post, gemini_mic.log, gemini_mic._google_cooldown_until)
        gemini_mic.log = lambda *a: None
        gemini_mic._google_cooldown_until = 0.0

        def post(url, **k):
            seen.append(k.get("timeout"))
            return google_ok("Salom.")
        gemini_mic.requests.post = post
        try:
            gemini_mic.gemini_transcribe("k", "gemini-3-flash-preview", "uz_en", wav)
        finally:
            gemini_mic.requests.post, gemini_mic.log, gemini_mic._google_cooldown_until = saved
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][1], 105.0)  # read part of (connect, read)


if __name__ == "__main__":
    unittest.main()
