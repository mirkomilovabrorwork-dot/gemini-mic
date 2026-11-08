r"""Idea-capture hotkey guard + outbox in gemini_mic.py. Pure logic: no mic,
no keyboard hook, no real TickTick (capture.ticktick is stubbed), no clipboard.

  * Right Alt (default) held ALONE past the hold time -> idea take starts, the
    menu-mask tap is sent once; any other key while it is held -> silent discard
  * Right Alt tapped short, or pressed with another key already down -> nothing
  * our own mask tap (VK 0xE8) is ignored by the guard
  * "ctrl+alt" config keeps working (Ctrl+Alt alone engages, Ctrl+Alt+K discards)
  * Right Ctrl alone keeps the old paste path (start_recording(), not idea)
  * outbox: TickTick error -> line appended; retry 2xx -> line removed

Run (repo root): windows\.venv\Scripts\python.exe -m pytest windows\tests\test_idea_hotkey.py -q
"""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GEMINI_MIC_LOG_PATH", os.path.join(tempfile.gettempdir(), "gemini_mic_test.log"))
import gemini_mic  # noqa: E402
from pynput.keyboard import Key, KeyCode  # noqa: E402

HOLD = 0.05  # shortened IDEA_HOLD_SEC for the tests


def settle(pred, timeout=1.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(0.01)
    return pred()


class HotkeyBase(unittest.TestCase):
    mode = "right_alt"

    def setUp(self):
        self._saved = (gemini_mic.log, gemini_mic.IDEA_HOLD_SEC)
        gemini_mic.log = lambda *a: None
        gemini_mic.IDEA_HOLD_SEC = HOLD
        app = object.__new__(gemini_mic.GeminiMicApp)
        app.cfg = {"idea_hotkey": self.mode}
        app.get_config = lambda: {"phone_trigger": False}
        app.idea_enabled = True
        app._idea_ctrl, app._idea_alt, app._idea_others = set(), set(), set()
        app._idea_ctrl_l_at = 0.0
        app._idea_clean = True
        app._idea_timer = None
        app._idea_engaged = False
        app.idea_active = False
        app.hotkey_target = gemini_mic.parse_hotkey("right ctrl")
        app.hotkey_down = False
        app.chunk_chain = 0
        app.recording = False
        app.record_gen = 0
        app.frames = []
        app.lock = threading.Lock()
        app.phone_lock = threading.Lock()
        app.phone_recording = False
        app.phone_falling_back = False
        app.phone_acked = False
        app.phone_gen = 0
        app.phone_start_seq = 0
        app.relay_server = None
        app.set_state = lambda s: None
        self.starts = []   # start_recording(idea) calls
        self.stops = []    # _stop_after_tail(gen, idea) calls
        self.masks = []

        def start(idea=False):
            self.starts.append(idea)
            app.recording = True

        app.start_recording = start
        app._stop_after_tail = lambda gen, idea=False: self.stops.append(idea)
        app._idea_send_mask = lambda: self.masks.append(1)
        app.preferred_mic_live = lambda: True
        app.phone_connected = lambda: False
        self.app = app

    def tearDown(self):
        self.app._idea_cancel_timer()
        gemini_mic.log, gemini_mic.IDEA_HOLD_SEC = self._saved

    def down(self, *keys):
        for k in keys:
            self.app._on_press(k)

    def up(self, *keys):
        for k in keys:
            self.app._on_release(k)


class RightAltTest(HotkeyBase):
    K = KeyCode.from_char("k")

    def test_default_config_is_right_alt(self):
        self.assertEqual(gemini_mic.DEFAULT_CONFIG["idea_hotkey"], "right_alt")

    def test_alone_past_hold_starts_idea_take_and_masks_menu(self):
        self.down(Key.alt_r)
        self.assertTrue(settle(lambda: self.starts == [True]))
        self.assertEqual(self.masks, [1])  # one neutral tap while Alt is down
        self.up(Key.alt_r)                 # release -> stop (transcribe)
        self.assertTrue(settle(lambda: self.stops == [True]))

    def test_auto_repeat_does_not_restart(self):
        self.down(Key.alt_r, Key.alt_r, Key.alt_r)
        self.assertTrue(settle(lambda: self.starts == [True]))
        time.sleep(HOLD * 2)
        self.assertEqual(self.starts, [True])

    def test_short_tap_does_nothing(self):
        self.down(Key.alt_r)
        self.up(Key.alt_r)
        time.sleep(HOLD * 3)
        self.assertEqual(self.starts, [])
        self.assertEqual(self.stops, [])
        self.assertEqual(self.masks, [])  # plain tap keeps normal Windows menu behaviour

    def test_other_key_before_timer_blocks_engage(self):
        self.down(Key.alt_r, self.K)
        time.sleep(HOLD * 3)
        self.assertEqual(self.starts, [])
        self.up(self.K, Key.alt_r)

    def test_other_key_already_down_blocks_engage(self):
        self.down(Key.shift)
        self.down(Key.alt_r)
        time.sleep(HOLD * 3)
        self.assertEqual(self.starts, [])
        self.up(Key.alt_r, Key.shift)

    def test_other_key_after_engage_discards_silently(self):
        self.down(Key.alt_r)
        self.assertTrue(settle(lambda: self.starts == [True]))
        self.down(self.K)
        self.assertFalse(self.app.recording)       # take dropped
        self.assertFalse(self.app.idea_active)
        self.up(self.K, Key.alt_r)
        time.sleep(0.1)
        self.assertEqual(self.stops, [])           # nothing transcribed

    def test_own_mask_tap_is_ignored_by_the_guard(self):
        self.down(Key.alt_r)
        self.assertTrue(settle(lambda: self.starts == [True]))
        mask = KeyCode.from_vk(gemini_mic.IDEA_MASK_VK)
        self.down(mask)
        self.up(mask)
        self.assertTrue(self.app.recording)        # still alive
        self.up(Key.alt_r)
        self.assertTrue(settle(lambda: self.stops == [True]))

    def test_altgr_fake_left_ctrl_is_not_another_key(self):
        self.down(Key.ctrl_l)       # Windows sends this just before AltGr
        self.down(Key.alt_gr)
        self.assertTrue(settle(lambda: self.starts == [True]))
        self.up(Key.alt_gr, Key.ctrl_l)

    def test_altgr_as_ctrl_l_plus_alt_r_engages(self):
        # Windows reports AltGr as synthetic LCtrl + alt_r (not alt_gr)
        self.down(Key.ctrl_l)
        self.down(Key.alt_r)
        self.assertTrue(settle(lambda: self.starts == [True]))
        self.assertNotIn(Key.ctrl_l, self.app._idea_others)
        self.up(Key.alt_r, Key.ctrl_l)
        self.assertTrue(settle(lambda: self.stops == [True]))

    def test_idea_timer_never_takes_over_a_running_paste_take(self):
        # Right Ctrl dictation is running; a late Alt must not flip it to TickTick
        self.app.idea_enabled = True
        self.app.cfg = {"idea_hotkey": "ctrl+alt"}
        self.down(Key.ctrl_r)
        self.assertTrue(settle(lambda: self.starts == [False]))
        self.down(Key.alt_l)
        time.sleep(HOLD * 4)
        self.assertEqual(self.starts, [False])       # no second start
        self.assertFalse(self.app.idea_active)
        self.assertFalse(self.app._idea_engaged)
        self.assertEqual(self.masks, [])
        self.up(Key.alt_l, Key.ctrl_r)
        time.sleep(0.1)
        self.assertNotIn(True, self.stops)           # idea stop path never used

    def test_left_ctrl_pressed_well_before_alt_blocks(self):
        self.down(Key.ctrl_l)
        time.sleep(0.1)
        self.down(Key.alt_r)
        time.sleep(HOLD * 3)
        self.assertEqual(self.starts, [])

    def test_right_ctrl_alone_keeps_the_paste_path(self):
        self.down(Key.ctrl_r)
        self.assertTrue(settle(lambda: self.starts == [False]))  # idea=False
        time.sleep(HOLD * 3)
        self.assertEqual(self.starts, [False])     # the guard never engaged
        self.assertEqual(self.masks, [])
        self.assertFalse(self.app._idea_engaged)

    def test_off_when_idea_hotkey_empty(self):
        self.app.idea_enabled = False
        self.down(Key.alt_r)
        time.sleep(HOLD * 3)
        self.assertEqual(self.starts, [])


class CtrlAltModeTest(HotkeyBase):
    mode = "ctrl+alt"
    K = KeyCode.from_char("k")

    def test_ctrl_alt_alone_engages_and_release_stops(self):
        self.down(Key.ctrl_l, Key.alt_l)
        self.assertTrue(settle(lambda: self.starts == [True]))
        self.assertEqual(self.masks, [])  # mask is a right_alt-mode thing
        self.up(Key.alt_l)
        self.assertTrue(settle(lambda: self.stops == [True]))

    def test_ctrl_alt_plus_key_discards(self):
        self.down(Key.ctrl_l, Key.alt_l)
        self.assertTrue(settle(lambda: self.starts == [True]))
        self.down(self.K)
        self.assertFalse(self.app.recording)
        self.up(self.K, Key.alt_l, Key.ctrl_l)
        time.sleep(0.1)
        self.assertEqual(self.stops, [])

    def test_ctrl_alt_k_pressed_before_timer_never_starts(self):
        self.down(Key.ctrl_l, Key.alt_l, self.K)
        time.sleep(HOLD * 3)
        self.assertEqual(self.starts, [])


class OutboxTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._saved = (gemini_mic.log, gemini_mic.IDEA_OUTBOX_PATH, gemini_mic.CONFIG_DIR)
        gemini_mic.log = lambda *a: None
        gemini_mic.CONFIG_DIR = self.tmp.name
        gemini_mic.IDEA_OUTBOX_PATH = os.path.join(self.tmp.name, "idea-outbox.jsonl")
        app = object.__new__(gemini_mic.GeminiMicApp)
        app._idea_kiruvchi_id = None
        app._idea_outbox_thread = object()  # pretend the retry thread runs
        app.badge = mock.Mock()
        app.recording = False
        app.pasted = []
        app.paste_text = app.pasted.append  # must never be called in idea mode
        self.app = app
        self.posts = []
        self.fail = True

        class FakeTT:
            KIRUVCHI = "kiruvchi"

            class TickTickError(Exception):
                status = 500

            @staticmethod
            def find_or_create_project(name):
                return "pid-k"

            @staticmethod
            def create_task(pid, title, content):
                if outer.fail:
                    raise FakeTT.TickTickError()
                outer.posts.append((pid, title, content))

        outer = self
        self.patch = mock.patch.dict(sys.modules, {"capture.ticktick": FakeTT})
        self.patch.start()
        self.addCleanup(self.patch.stop)
        # `import capture.ticktick as ticktick` reads the attribute of the
        # package when it is already imported, so patch that too
        import capture
        self._cap_tt = getattr(capture, "ticktick", None)
        capture.ticktick = FakeTT
        self.addCleanup(lambda: setattr(capture, "ticktick", self._cap_tt))

    def tearDown(self):
        gemini_mic.log, gemini_mic.IDEA_OUTBOX_PATH, gemini_mic.CONFIG_DIR = self._saved

    def _lines(self):
        with open(gemini_mic.IDEA_OUTBOX_PATH, encoding="utf-8") as f:
            return [json.loads(x) for x in f.read().splitlines() if x.strip()]

    def test_error_appends_line_and_never_pastes(self):
        with mock.patch.object(gemini_mic.threading, "Timer"):
            self.app.idea_capture("yangi g'oya matni")
        lines = self._lines()
        self.assertEqual(len(lines), 1)
        self.assertIn("yangi g'oya matni", lines[0]["text"])
        self.assertIn("at", lines[0])
        self.assertEqual(self.app.pasted, [])               # never pasted
        self.app.badge.show.assert_called_with("saved")     # "Saqlandi" anyway

    def test_retry_removes_line_only_after_success(self):
        with mock.patch.object(gemini_mic.threading, "Timer"):
            self.app.idea_capture("birinchi")
        self.app._idea_outbox_flush()          # still failing
        self.assertEqual(len(self._lines()), 1)
        self.assertEqual(self.posts, [])
        self.fail = False
        self.app._idea_outbox_flush()          # 2xx
        self.assertEqual(self._lines(), [])
        self.assertEqual(len(self.posts), 1)
        self.assertEqual(self.posts[0][0], "pid-k")

    def test_append_during_flush_does_not_block_and_is_not_lost(self):
        with mock.patch.object(gemini_mic.threading, "Timer"):
            self.app.idea_capture("eski")
        self.fail = False
        done = []
        orig = sys.modules["capture.ticktick"].create_task

        def slow_create(pid, title, content):
            if not done:  # first delivery: a new idea arrives mid-HTTP
                t = threading.Thread(target=self.app._idea_outbox_append,
                                     args=({"text": "yangi", "at": "x"},))
                t.start()
                t.join(2)
                done.append(not t.is_alive())  # lock NOT held during HTTP
            return orig(pid, title, content)

        sys.modules["capture.ticktick"].create_task = slow_create
        self.app._idea_outbox_flush()
        self.assertEqual(done, [True])
        self.assertEqual([l["text"] for l in self._lines()], ["yangi"])

    def test_delivered_line_removed_right_after_its_2xx(self):
        self.app._idea_outbox_append({"text": "bir", "at": "x"})
        self.app._idea_outbox_append({"text": "ikki", "at": "x"})
        orig = sys.modules["capture.ticktick"].create_task
        self.fail = False

        def second_fails(pid, title, content):
            if title == "ikki":
                raise sys.modules["capture.ticktick"].TickTickError()
            return orig(pid, title, content)

        sys.modules["capture.ticktick"].create_task = second_fails
        self.app._idea_outbox_flush()
        # "bir" is gone although the batch did not finish: no duplicate later
        self.assertEqual([l["text"] for l in self._lines()], ["ikki"])

    def test_resume_starts_retry_loop_when_outbox_not_empty(self):
        self.app._idea_outbox_thread = None
        started = []
        self.app._idea_outbox_start = lambda: started.append(1)
        self.app._idea_outbox_resume()           # no file yet
        self.assertEqual(started, [])
        with open(gemini_mic.IDEA_OUTBOX_PATH, "w", encoding="utf-8") as f:
            f.write(json.dumps({"text": "t", "at": "x"}) + "\n")
        self.app._idea_outbox_resume()
        self.assertEqual(started, [1])

    def test_ticktick_error_clears_cached_project_id(self):
        self.app._idea_kiruvchi_id = "stale"
        with self.assertRaises(Exception):
            self.app._idea_post("t", "c")        # create_task fails (self.fail)
        self.assertIsNone(self.app._idea_kiruvchi_id)

    def test_success_posts_directly_without_outbox(self):
        self.fail = False
        with mock.patch.object(gemini_mic.threading, "Timer"):
            self.app.idea_capture("to'g'ridan-to'g'ri")
        self.assertEqual(len(self.posts), 1)
        self.assertTrue(self.posts[0][2].startswith("to'g'ridan-to'g'ri"))
        self.assertIn("[manba: PC ", self.posts[0][2])
        self.assertFalse(os.path.exists(gemini_mic.IDEA_OUTBOX_PATH))


if __name__ == "__main__":
    unittest.main()
