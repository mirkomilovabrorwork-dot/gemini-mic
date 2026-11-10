"""Owner 11-10: "klipbordga tushadigan bo'lsa, klipbordga tushdi deb turib
chiqaradigan qilib qo'y" - paste_text must VERIFY the Ctrl+V landed in the
focused field; when it did not, keep the transcript in the clipboard and show
the blue "clipboard" badge. Nothing real is pasted here - focus, UIA reads,
clipboard, keyboard and the badge timer are all stubbed.

Run (from windows/): .venv/Scripts/python -m pytest tests/test_paste_verify.py -v
"""

import os
import sys
import tempfile
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GEMINI_MIC_LOG_PATH", os.path.join(tempfile.gettempdir(), "gemini_mic_test.log"))
import gemini_mic  # noqa: E402

TEXT = "salom dunyo, bu yozuv maydonga tushishi kerak"


class FakeTimer:
    """threading.Timer stand-in: records the delay, never fires."""
    started = []

    def __init__(self, delay, func):
        self.delay, self.func = delay, func

    def start(self):
        FakeTimer.started.append(self)


def make_app(badge=None):
    app = gemini_mic.GeminiMicApp.__new__(gemini_mic.GeminiMicApp)
    app.kb_controller = mock.Mock()
    app.badge = badge
    app.notify = lambda m: None
    app.recording = False
    return app


def run_paste(target, reads, badge):
    """One paste_text call with everything stubbed. `reads` is the sequence
    read_focused_text returns (before, after). Returns the copy calls."""
    app = make_app(badge)
    copies = []
    hist = tempfile.mkdtemp()
    with mock.patch.object(gemini_mic, "HISTORY_PATH", os.path.join(hist, "h.jsonl")), \
            mock.patch.object(gemini_mic, "focus_foreground_editable", return_value=target), \
            mock.patch.object(gemini_mic, "read_focused_text", side_effect=list(reads)), \
            mock.patch.object(gemini_mic.pyperclip, "paste", return_value="old clip"), \
            mock.patch.object(gemini_mic.pyperclip, "copy", side_effect=copies.append), \
            mock.patch.object(gemini_mic.time, "sleep"), \
            mock.patch.object(gemini_mic.threading, "Timer", FakeTimer):
        app.paste_text(TEXT)
    return copies


def test_landed_restores_old_clipboard_no_badge():
    badge = mock.Mock()
    copies = run_paste(True, ["eski", "eski " + TEXT], badge)
    assert copies == [TEXT, "old clip"]          # paste, then restore
    badge.show.assert_not_called()


def test_not_landed_keeps_transcript_and_shows_clipboard_badge():
    badge = mock.Mock()
    copies = run_paste(True, ["eski matn", "eski matn", "eski matn"], badge)  # readable, unchanged
    assert copies == [TEXT]                      # transcript kept, NO restore
    badge.show.assert_called_once_with("clipboard")
    assert FakeTimer.started[-1].delay == gemini_mic.CLIPBOARD_BADGE_SEC


def test_unreadable_field_restores_no_badge():
    badge = mock.Mock()
    copies = run_paste(True, [None, None], badge)
    assert copies == [TEXT, "old clip"]          # today's calm behaviour
    badge.show.assert_not_called()


def test_no_target_badge_as_before():
    badge = mock.Mock()
    copies = run_paste(False, [], badge)         # read_focused_text never called
    assert copies == [TEXT]                      # clipboard kept, no restore
    badge.show.assert_called_once_with("clipboard")
    assert FakeTimer.started[-1].delay == gemini_mic.CLIPBOARD_BADGE_SEC


def test_tail_match_with_different_whitespace_counts_as_landed():
    badge = mock.Mock()
    # the field re-wraps the text: same non-space tail, different whitespace
    after = "  salom   dunyo,\n\nbu yozuv  maydonga tushishi kerak  "
    copies = run_paste(True, ["", after], badge)
    assert copies == [TEXT, "old clip"]
    badge.show.assert_not_called()
