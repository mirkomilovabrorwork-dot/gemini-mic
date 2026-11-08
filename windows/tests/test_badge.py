"""RecordingBadge (2026-11-08): the on-screen "Yozilyapti" pill must show
without stealing focus, switch text, and hide; and the local start beep +
remove_start_beep are gone from the source."""
import ctypes
import inspect
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GEMINI_MIC_LOG_PATH", os.path.join(tempfile.gettempdir(), "gemini_mic_test.log"))
import gemini_mic  # noqa: E402

user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000


def _wait(cond, timeout=2.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return cond()


def _display_available():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


class TestRecordingBadge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not _display_available():
            raise unittest.SkipTest("no display available")

    def test_show_switch_and_hide(self):
        badge = gemini_mic.RecordingBadge()
        badge.start()
        self.addCleanup(badge.close)
        self.assertTrue(_wait(lambda: badge._hwnd is not None), "badge window never came up")

        hwnd = badge._hwnd
        fg_before = user32.GetForegroundWindow()

        badge.show("recording")
        self.assertTrue(_wait(lambda: user32.IsWindowVisible(hwnd)), "badge not visible after show")
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        self.assertNotEqual(style & WS_EX_NOACTIVATE, 0, "WS_EX_NOACTIVATE not set")
        self.assertEqual(user32.GetForegroundWindow(), fg_before, "badge stole the focus")

        badge.show("transcribing")
        self.assertTrue(
            _wait(lambda: badge.current_text == "… Matnga aylanmoqda"),
            "label text did not switch, got %r" % badge.current_text,
        )
        self.assertEqual(user32.GetForegroundWindow(), fg_before, "badge stole the focus on switch")

        badge.hide()
        self.assertTrue(_wait(lambda: not user32.IsWindowVisible(hwnd)), "badge still visible after hide")

        # give the Tk thread a moment to exit cleanly before process teardown
        _wait(lambda: not badge._thread.is_alive(), timeout=2.0)


class TestBeepRemoved(unittest.TestCase):
    def test_start_recording_has_no_beep(self):
        src = inspect.getsource(gemini_mic.GeminiMicApp.start_recording)
        self.assertNotIn("beep(", src)

    def test_frames_to_wav_bytes_has_no_notch(self):
        src = inspect.getsource(gemini_mic.frames_to_wav_bytes)
        self.assertNotIn("remove_start_beep", src)


if __name__ == "__main__":
    unittest.main()
