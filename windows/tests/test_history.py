"""Owner 11-10: a long dictation must survive in full (log.txt cut it at 300 chars).
paste_text writes history.jsonl BEFORE pasting; nothing real is pasted here.

Run (from windows/): .venv\\Scripts\\python -m unittest tests.test_history -v
"""

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GEMINI_MIC_LOG_PATH", os.path.join(tempfile.gettempdir(), "gemini_mic_test.log"))
import gemini_mic  # noqa: E402

LONG = ("Bu uzun javob: " + "har bir so'z saqlanishi shart, " * 40).strip()


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "history.jsonl")
        self._p = mock.patch.object(gemini_mic, "HISTORY_PATH", self.path)
        self._p.start()

    def tearDown(self):
        self._p.stop()

    def rows(self):
        with open(self.path, encoding="utf-8") as f:
            return [json.loads(x) for x in f]

    def paste(self, confirmed):
        app = gemini_mic.GeminiMicApp.__new__(gemini_mic.GeminiMicApp)
        app.kb_controller = mock.Mock()
        app.badge = None
        app.notify = lambda m: None
        with mock.patch.object(gemini_mic, "focus_foreground_editable", return_value=confirmed), \
                mock.patch.object(gemini_mic.pyperclip, "paste", return_value="old"), \
                mock.patch.object(gemini_mic.pyperclip, "copy"), \
                mock.patch.object(gemini_mic.time, "sleep"):
            app.paste_text(LONG)

    def test_long_text_kept_in_full_with_target(self):
        self.assertGreater(len(LONG), 300)
        self.paste(True)
        self.paste(False)
        r = self.rows()
        self.assertEqual([x["text"] for x in r], [LONG, LONG])
        self.assertEqual(r[0]["chars"], len(LONG))
        self.assertTrue(r[0]["where"].startswith("field: "))
        self.assertTrue(r[1]["where"].startswith("no target -> clipboard: "))

    def test_rotates_past_5mb(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("x" * 5_000_001)
        gemini_mic.save_history("new", "field: t")
        self.assertTrue(os.path.exists(self.path + ".old"))
        self.assertEqual([x["text"] for x in self.rows()], ["new"])


if __name__ == "__main__":
    unittest.main()
