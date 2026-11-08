r"""capture/idea_processor.py: schema/code check, move-then-update order,
crash recovery (no second move, no second Claude call), bot inbox
idempotence per item, single-instance lock. Everything is stubbed - no
real TickTick API, no real `claude`, no %APPDATA% writes.

Run (repo root): windows\.venv\Scripts\python.exe -m pytest windows\tests\test_idea_processor.py -q
"""

import datetime
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from capture import ticktick as tt            # noqa: E402
from capture import idea_processor as ip      # noqa: E402

NOW = datetime.datetime(2026, 11, 8, 20, 0, tzinfo=datetime.timezone.utc)


def good_ai(**over):
    res = {"kind": "idea", "title": "G'oya — bir satrda",
           "description": "To'liq matn", "priority": "low",
           "due": None, "reminder_minutes_before": None}
    res.update(over)
    return res


class FakeTickTick:
    """Records every call in order; the TickTick API fully faked."""

    TickTickError = tt.TickTickError
    KIRUVCHI, GOYALAR, VAZIFALAR = tt.KIRUVCHI, tt.GOYALAR, tt.VAZIFALAR

    def __init__(self):
        self.calls = []
        self.projects = {}
        self.tasks = {}          # project_id -> [task dict]
        self.update_raises = False
        self.move_raises_after = False   # server applied the move, reply lost
        self.move_already = False        # later moves answer "already moved"
        self.stale_ids = set()           # ids that now answer 404
        self.project_tasks_hides = False  # target listing never shows the task
        self.create_fail_title = None

    def find_or_create_project(self, name):
        self.calls.append(("find_or_create_project", name))
        if name not in self.projects:
            self.projects[name] = "pid-" + {"📥 Kiruvchi": "kiruvchi",
                                            "G'oyalar": "goyalar",
                                            "✅ Vazifalar": "vazifalar"}[name]
        return self.projects[name]

    def project_tasks(self, pid):
        self.calls.append(("project_tasks", pid))
        if pid in self.stale_ids:
            raise tt.TickTickError(404)
        if self.project_tasks_hides and pid != "pid-kiruvchi":
            return []
        return [dict(t) for t in self.tasks.get(pid, [])]

    def create_task(self, pid, title, content):
        if title == self.create_fail_title:
            raise tt.TickTickError(500)  # failed post: nothing was created
        self.calls.append(("create_task", pid, title, content))
        tid = "task-%d" % len(self.calls)
        self.tasks.setdefault(pid, []).append(
            {"id": tid, "title": title, "content": content})
        return {"id": tid}

    def move_task(self, tid, from_id, to_id):
        self.calls.append(("move_task", tid, from_id, to_id))
        if self.move_already:
            raise tt.TickTickError(400)
        self.tasks[from_id] = [t for t in self.tasks.get(from_id, [])
                               if t["id"] != tid]
        self.tasks.setdefault(to_id, []).append(
            {"id": tid, "title": "raw", "content": "raw"})
        if self.move_raises_after:
            self.move_raises_after = False
            self.move_already = True
            raise tt.TickTickError(500)

    def update_task(self, tid, pid, fields):
        self.calls.append(("update_task", tid, pid, dict(fields)))
        if self.update_raises:
            raise tt.TickTickError(500)
        for t in self.tasks.get(pid, []):
            if t["id"] == tid:
                t.update(fields)

    def complete_task(self, pid, tid):
        self.calls.append(("complete_task", pid, tid))


class ProcessorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.saved_paths = (ip.STATE_PATH, ip.LOG_PATH, ip.LOCK_PATH, ip.APP_DIR)
        ip.APP_DIR = self.tmp.name
        ip.STATE_PATH = os.path.join(self.tmp.name, "idea-state.json")
        ip.LOG_PATH = os.path.join(self.tmp.name, "idea-processor.log")
        ip.LOCK_PATH = os.path.join(self.tmp.name, "idea-processor.lock")
        self.fake = FakeTickTick()
        self._saved_tt = ip.ticktick
        ip.ticktick = self.fake
        self.claude_calls = []
        self.next_ai = good_ai()

        def fake_claude(prompt):
            self.claude_calls.append(prompt)
            return self.next_ai

        self._saved_call = ip.call_claude
        ip.call_claude = fake_claude

    def tearDown(self):
        ip.ticktick = self._saved_tt
        ip.call_claude = self._saved_call
        (ip.STATE_PATH, ip.LOG_PATH, ip.LOCK_PATH, ip.APP_DIR) = self.saved_paths

    # -- code check ---------------------------------------------------------

    def test_check_rejects_bad_kind(self):
        ok, why = ip.validate_ai(good_ai(kind="project"), NOW)
        self.assertFalse(ok)
        self.assertEqual(why, "kind")

    def test_check_rejects_71_char_title(self):
        ok, why = ip.validate_ai(good_ai(title="x" * 71), NOW)
        self.assertFalse(ok)
        self.assertEqual(why, "title")
        self.assertTrue(ip.validate_ai(good_ai(title="x" * 70), NOW)[0])

    def test_check_rejects_past_due_and_bad_due(self):
        old = (NOW - datetime.timedelta(days=2)).isoformat()
        self.assertEqual(ip.validate_ai(good_ai(due=old), NOW), (False, "due-past"))
        # within the 1-day grace window is accepted (clock/timezone slack)
        recent = (NOW - datetime.timedelta(hours=20)).isoformat()
        self.assertTrue(ip.validate_ai(good_ai(due=recent), NOW)[0])
        self.assertFalse(ip.validate_ai(good_ai(due="ertaga"), NOW)[0])

    # -- noise / idea / task routing ------------------------------------------

    def test_noise_completed_not_moved(self):
        self.fake.tasks["pid-kiruvchi"] = [{"id": "n1", "title": "/start",
                                            "content": "/start"}]
        self.next_ai = good_ai(kind="noise")
        ip.process_tasks(ip.load_state(), now=NOW)
        names = [c[0] for c in self.fake.calls]
        self.assertIn("complete_task", names)
        self.assertNotIn("move_task", names)
        self.assertNotIn("update_task", names)
        self.assertEqual(ip.load_state()["done"], {"n1": "done"})

    def test_idea_moves_first_then_updates(self):
        self.fake.tasks["pid-kiruvchi"] = [{"id": "i1", "title": "raw t",
                                            "content": "raw c"}]
        self.next_ai = good_ai(kind="idea", priority="low")
        ip.process_tasks(ip.load_state(), now=NOW)
        names = [c[0] for c in self.fake.calls]
        self.assertLess(names.index("move_task"), names.index("update_task"),
                        "move must happen BEFORE update")
        upd = [c for c in self.fake.calls if c[0] == "update_task"][0]
        self.assertEqual(upd[2], "pid-goyalar")          # idea -> G'oyalar
        self.assertEqual(upd[3]["priority"], 1)          # low unless "high"
        self.assertIn("\n\n---\nAsl matn: raw c", upd[3]["content"])
        self.assertEqual(ip.load_state()["done"], {"i1": "done"})

    def test_task_due_gets_ticktick_duedate_and_reminder(self):
        self.fake.tasks["pid-kiruvchi"] = [{"id": "t1", "title": "r",
                                            "content": "c"}]
        self.next_ai = good_ai(kind="task", priority="high",
                               due="2026-11-09T15:00:00+05:00",  # 10:00 UTC
                               reminder_minutes_before=30)
        ip.process_tasks(ip.load_state(), now=NOW)
        upd = [c for c in self.fake.calls if c[0] == "update_task"][0]
        f = upd[3]
        self.assertEqual(f["priority"], 5)
        self.assertEqual(f["dueDate"], "2026-11-09T10:00:00+0000")
        self.assertEqual(f["timeZone"], "Asia/Tashkent")
        self.assertFalse(f["isAllDay"])
        self.assertEqual(f["reminders"], ["TRIGGER:-PT30M"])
        mv = [c for c in self.fake.calls if c[0] == "move_task"][0]
        self.assertEqual(mv[3], "pid-vazifalar")

    def test_bad_answer_counts_fails_and_never_touches_the_task(self):
        self.fake.tasks["pid-kiruvchi"] = [{"id": "b1", "title": "r",
                                            "content": "c"}]
        self.next_ai = good_ai(title="x" * 71)
        for _ in range(3):
            ip.process_tasks(ip.load_state(), now=NOW)
        st = ip.load_state()
        self.assertEqual(st["fails"], {"b1": 3})
        self.assertNotIn("b1", st["done"])
        self.assertEqual([c[0] for c in self.fake.calls].count("move_task"), 0)
        n = len(self.claude_calls)
        ip.process_tasks(ip.load_state(), now=NOW)  # 4th run: skipped
        self.assertEqual(len(self.claude_calls), n)
        self.assertIn("ai-xato",
                      open(ip.LOG_PATH, encoding="utf-8").read())

    # -- crash recovery --------------------------------------------------------

    def test_crash_after_move_updated_next_run_without_new_move_or_call(self):
        self.fake.tasks["pid-kiruvchi"] = [{"id": "c1", "title": "raw t",
                                            "content": "raw c"}]
        self.fake.update_raises = True  # crash AFTER the move, IN the update
        ip.process_tasks(ip.load_state(), now=NOW)
        self.assertEqual(ip.load_state()["done"], {"c1": "moved"})
        self.assertEqual(len(self.claude_calls), 1)
        self.assertEqual([c[0] for c in self.fake.calls].count("move_task"), 1)

        self.fake.update_raises = False  # network is back
        self.fake.tasks["pid-goyalar"] = [{"id": "c1", "title": "raw t",
                                           "content": "raw c"}]
        ip.retry_moved(ip.load_state(), now=NOW)
        self.assertEqual(ip.load_state()["done"], {"c1": "done"})
        # no second move, no second Claude call
        self.assertEqual(len(self.claude_calls), 1)
        self.assertEqual([c[0] for c in self.fake.calls].count("move_task"), 1)
        upd = [c for c in self.fake.calls if c[0] == "update_task"]
        self.assertEqual(len(upd), 2)  # attempt 1 (crashed) + the retry
        self.assertEqual(upd[1][3]["title"], "G'oya — bir satrda")

    def test_crash_between_move_and_save_is_finished_next_run(self):
        # the answer is saved as "moving" BEFORE the move; the move lands on
        # the server but the reply is lost -> next run: move tolerated as
        # "already moved", straight update (no project_tasks listing, which
        # may hide the task), no second Claude call
        self.fake.tasks["pid-kiruvchi"] = [{"id": "m1", "title": "raw t",
                                            "content": "raw c"}]
        self.fake.move_raises_after = True
        self.fake.project_tasks_hides = True
        ip.process_tasks(ip.load_state(), now=NOW)
        st = ip.load_state()
        self.assertEqual(st["done"], {"m1": "moving"})
        self.assertEqual(st["results"]["m1"]["target"], "pid-goyalar")
        n = len(self.fake.calls)
        ip.retry_moved(ip.load_state(), now=NOW)
        self.assertEqual(ip.load_state()["done"], {"m1": "done"})
        self.assertEqual(len(self.claude_calls), 1)
        after = self.fake.calls[n:]
        self.assertEqual([c[0] for c in after], ["move_task", "update_task"])
        self.assertNotIn("project_tasks", [c[0] for c in after])
        # a third run does nothing for it
        ip.process_tasks(ip.load_state(), now=NOW)
        self.assertEqual(len(self.claude_calls), 1)

    def test_update_404_after_clean_move_marks_gone(self):
        self.fake.tasks["pid-kiruvchi"] = [{"id": "g1", "title": "r", "content": "c"}]
        self.fake.update_raises = True
        ip.process_tasks(ip.load_state(), now=NOW)
        self.assertEqual(ip.load_state()["done"], {"g1": "moved"})
        orig = self.fake.update_task

        def gone(tid, pid, fields):
            raise tt.TickTickError(404)
        self.fake.update_task = gone
        ip.retry_moved(ip.load_state(), now=NOW)
        self.assertEqual(ip.load_state()["done"], {"g1": "done"})

    # -- telegram bot inbox -----------------------------------------------------

    def _write_bot_file(self, inbox, name, text,
                        header_time="2026-11-08T12:00:00+05:00"):
        with open(os.path.join(inbox, name), "w", encoding="utf-8") as f:
            f.write("%s message_id=1 audio=? type=text\n%s"
                    % (header_time, text))

    def test_bot_first_run_marks_existing_files_seen(self):
        inbox = os.path.join(self.tmp.name, "inbox")
        os.makedirs(inbox)
        self._write_bot_file(inbox, "a.txt", "eski test")
        with mock.patch.dict(os.environ, {"IDEA_BOT_INBOX": inbox}):
            ip.run_bot_inbox(ip.load_state(), now=NOW)
        st = ip.load_state()
        self.assertEqual(st["bot_seen"], ["a.txt"])
        self.assertIsNotNone(st["bot_since"])
        self.assertNotIn("create_task", [c[0] for c in self.fake.calls])

    def test_bot_new_file_posts_once_despite_crash_right_after_a_post(self):
        inbox = os.path.join(self.tmp.name, "inbox")
        os.makedirs(inbox)
        self._write_bot_file(inbox, "a.txt", "eski test")
        with mock.patch.dict(os.environ, {"IDEA_BOT_INBOX": inbox}):
            ip.run_bot_inbox(ip.load_state(), now=NOW)  # first run: seen only
            # two NEW files; the crash happens right after "b"'s post - the
            # per-item save means "b" is never posted again on the rerun,
            # only "c" (whose post never happened) goes out once
            self._write_bot_file(inbox, "b.txt", "ikki matn")
            self._write_bot_file(inbox, "c.txt", "uch matn")
            self.fake.create_fail_title = "uch matn"
            with self.assertRaises(tt.TickTickError):
                ip.run_bot_inbox(ip.load_state(), now=NOW)  # b saved, c died
            self.fake.create_fail_title = None
            ip.run_bot_inbox(ip.load_state(), now=NOW)  # rerun after crash
        posts = [c for c in self.fake.calls if c[0] == "create_task"]
        self.assertEqual([p[2] for p in posts], ["ikki matn", "uch matn"])
        self.assertIn("[manba: Telegram 2026-11-08T12:00:00+05:00]",
                      posts[0][3])
        # the inbox folder was never modified or cleaned
        self.assertEqual(sorted(os.listdir(inbox)),
                         ["a.txt", "b.txt", "c.txt"])

    # -- single-instance lock ------------------------------------------------------

    def test_lock_held_second_acquire_fails_and_main_exits_0(self):
        lock = ip.acquire_lock()
        self.assertIsNotNone(lock)
        self.addCleanup(lock.close)
        self.assertIsNone(ip.acquire_lock())
        ran = []
        saved = ip.run_once
        ip.run_once = lambda: ran.append(1)
        try:
            self.assertEqual(ip.main([]), 0)
        finally:
            ip.run_once = saved
        self.assertEqual(ran, [])  # the second instance did no work

    # -- claude CLI call ----------------------------------------------------------

    def test_claude_runs_with_clean_env(self):
        ip.call_claude = self._saved_call  # exercise the REAL call_claude
        seen = {}

        def fake_run(cmd, **kw):
            seen["cmd"], seen["env"] = cmd, kw.get("env")
            out = json.dumps({"structured_output": good_ai()})
            return mock.Mock(returncode=0, stdout=out, stderr="")

        dirty = {"ANTHROPIC_API_KEY": "sk-test", "anthropic_api_key": "sk2",
                 "ANTHROPIC_BASE_URL": "http://x", "ANTHROPIC_AUTH_TOKEN": "t",
                 "CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "desktop",
                 "CLAUDE_CODE_OAUTH_TOKEN": "keep-me"}
        with mock.patch.dict(os.environ, dirty), \
                mock.patch.object(ip, "claude_exe", return_value="claude"), \
                mock.patch.object(ip.subprocess, "run", fake_run):
            res = ip.call_claude("prompt")
        self.assertEqual(res["kind"], "idea")
        env = seen["env"]
        bad = [k for k in env if (k.upper().startswith("ANTHROPIC_")
                                  or k.upper().startswith("CLAUDE"))
               and k.upper() != "CLAUDE_CODE_OAUTH_TOKEN"]
        self.assertEqual(bad, [])
        self.assertEqual(env.get("CLAUDE_CODE_OAUTH_TOKEN"), "keep-me")
        self.assertIn("PATH", {k.upper() for k in env})
        self.assertEqual(seen["cmd"][:5], ["claude", "-p", "--model", "sonnet", "--effort"])

    def test_stale_cached_project_id_is_dropped_and_resolved_once(self):
        ip.save_state({**ip.new_state(), "project_ids": {
            "kiruvchi": "old-k", "goyalar": "old-g", "vazifalar": "old-v"}})
        self.fake.stale_ids = {"old-k"}
        self.fake.tasks["pid-kiruvchi"] = [{"id": "s1", "title": "r", "content": "c"}]
        ip.process_tasks(ip.load_state(), now=NOW)
        st = ip.load_state()
        self.assertEqual(st["done"], {"s1": "done"})
        self.assertEqual(st["project_ids"]["kiruvchi"], "pid-kiruvchi")
        fetches = [c for c in self.fake.calls if c[0] == "project_tasks"]
        self.assertEqual([c[1] for c in fetches], ["old-k", "pid-kiruvchi"])

    # -- claude CLI envelope ----------------------------------------------------------

    def test_parse_cli_json_prefers_structured_output(self):
        env = json.dumps({"result": json.dumps({"kind": "task"}),
                          "structured_output": {"kind": "idea"}})
        self.assertEqual(ip.parse_cli_json(env), {"kind": "idea"})
        env2 = json.dumps({"result": json.dumps({"kind": "task"})})
        self.assertEqual(ip.parse_cli_json(env2), {"kind": "task"})
        with self.assertRaises(ip.AiError):
            ip.parse_cli_json("not json")


if __name__ == "__main__":
    unittest.main()
