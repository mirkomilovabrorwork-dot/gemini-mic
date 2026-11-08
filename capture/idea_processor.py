r"""Kiruvchi queue processor: raw notes in "📥 Kiruvchi" -> tidy tasks in
"G'oyalar" / "✅ Vazifalar", noise completed. Decisions come from Claude
Sonnet via the local `claude` CLI (--json-schema), never from here.

Run (scheduled task, hidden): python capture\idea_processor.py --once

Never loses a note: a task is only completed after a good answer, and the
state file (%APPDATA%\GeminiMic\idea-state.json) is rewritten atomically
after EVERY item, so a crash mid-run resumes exactly where it stopped.
The parsed AI answer is stored in the state file together with the "moved"
marker, so the update retry after a crash needs no second Claude call.

Single instance: an exclusive byte lock on idea-processor.lock; a second
run exits 0 at once.

The log (idea-processor.log) carries one line per item - id, kind, ms,
ok/err - never the note text and never the TickTick token.
"""

import datetime
import json
import msvcrt
import os
import shutil
import subprocess
import sys
import time

if __package__ in (None, ""):  # run as `python capture\idea_processor.py`
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capture import ticktick  # noqa: E402

# %APPDATA%\GeminiMic - same dir the Windows app uses (config, log, outbox).
APP_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"),
                       "GeminiMic")
STATE_PATH = os.path.join(APP_DIR, "idea-state.json")
LOG_PATH = os.path.join(APP_DIR, "idea-processor.log")
LOCK_PATH = os.path.join(APP_DIR, "idea-processor.lock")

TZ_NAME = "Asia/Tashkent"
MAX_TASKS_PER_RUN = 10
MAX_FAILS = 3          # code-check/CLI failures before "ai-xato" and skip
CLAUDE_TIMEOUT = 120   # s
PRIORITY_MAP = {"high": 5, "medium": 3, "low": 1, "none": 0}
KINDS = ("idea", "task", "noise")

# The structured contract with the model (also passed to the CLI as
# --json-schema). Title rule "<short name> — <one-line takeaway>" lives in the
# prompt; here it is enforced as 1..70 chars.
SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": list(KINDS)},
        "title": {"type": "string", "minLength": 1, "maxLength": 70},
        "description": {"type": "string"},
        "priority": {"type": "string", "enum": ["high", "medium", "low", "none"]},
        "due": {"type": ["string", "null"]},
        "reminder_minutes_before": {"type": ["integer", "null"],
                                    "minimum": 0, "maximum": 1440},
    },
    "required": ["kind", "title", "description", "priority", "due",
                 "reminder_minutes_before"],
    "additionalProperties": False,
}
SCHEMA_JSON = json.dumps(SCHEMA, ensure_ascii=False)


class AiError(Exception):
    """The claude CLI could not be run / answered no usable JSON."""


def now_local():
    """Aware datetime in Asia/Tashkent."""
    return datetime.datetime.now(datetime.timezone.utc).astimezone(_tz())


def _tz():
    """Asia/Tashkent. Windows Python has no IANA database unless tzdata is
    installed; Tashkent is a fixed UTC+5 (no DST since 1992), so fall back."""
    try:
        import zoneinfo
        return zoneinfo.ZoneInfo(TZ_NAME)
    except Exception:
        return datetime.timezone(datetime.timedelta(hours=5), TZ_NAME)


def log_line(task_id, kind, ms, code):
    """One line per item; no raw text, no token."""
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("%s %s %s %dms %s\n"
                    % (now_local().strftime("%Y-%m-%dT%H:%M:%S"),
                       task_id, kind, ms, code))
    except OSError:
        pass


# -- state ---------------------------------------------------------------


def new_state():
    return {"project_ids": {}, "done": {}, "fails": {}, "results": {},
            "bot_seen": [], "bot_since": None}


def load_state(path=None):
    path = path or STATE_PATH
    st = new_state()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return st
    if isinstance(data, dict):
        for k in st:
            if k in data:
                st[k] = data[k]
    return st


def save_state(state, path=None):
    """Atomic write (tmp + os.replace); called after EVERY item."""
    path = path or STATE_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


# -- single-instance lock -------------------------------------------------


def acquire_lock(path=None):
    """Exclusive byte lock; returns the held file object or None."""
    path = path or LOCK_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a+b")
    try:
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        f.close()
        return None
    return f


# -- claude CLI -----------------------------------------------------------


def claude_exe():
    return shutil.which("claude.cmd") or shutil.which("claude")


def parse_cli_json(stdout):
    """The -p --output-format json envelope carries the model's structured
    answer BOTH as `structured_output` (object, preferred) and as `result`
    (the same object serialized to a JSON string). Verified against the real
    CLI 2.1.306: probe 2026-11-08 returned
    {"result":"{\"kind\":\"greeting\"}","structured_output":{"kind":"greeting"},...}
    """
    try:
        envelope = json.loads(stdout)
    except ValueError:
        raise AiError("envelope not JSON")
    if not isinstance(envelope, dict):
        raise AiError("envelope not an object")
    so = envelope.get("structured_output")
    if isinstance(so, dict):
        return so
    raw = envelope.get("result")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except ValueError:
            raise AiError("result not JSON")
        if isinstance(parsed, dict):
            return parsed
    raise AiError("no structured result in envelope")


def claude_env():
    """Environment for the CLI: a copy of ours WITHOUT every ANTHROPIC_* and
    CLAUDE* variable except CLAUDE_CODE_OAUTH_TOKEN (same rule as
    weekly-update-scan.ps1). ANTHROPIC_API_KEY would bill the paid API instead
    of the owner's subscription; ANTHROPIC_BASE_URL and friends inherited from
    a desktop host make the headless CLI answer "Not logged in"."""
    env = dict(os.environ)
    for k in list(env):
        u = k.upper()
        if (u.startswith("ANTHROPIC_") or u.startswith("CLAUDE")) \
                and u != "CLAUDE_CODE_OAUTH_TOKEN":
            del env[k]
    return env


def call_claude(prompt):
    """One sonnet call with the schema; returns the model's dict."""
    exe = claude_exe()
    if not exe:
        raise AiError("claude CLI not found")
    CREATE_NO_WINDOW = 0x08000000
    try:
        proc = subprocess.run(
            [exe, "-p", "--model", "sonnet", "--effort", "high",
             "--output-format", "json", "--json-schema", SCHEMA_JSON],
            input=prompt, text=True, encoding="utf-8", capture_output=True,
            timeout=CLAUDE_TIMEOUT, creationflags=CREATE_NO_WINDOW,
            env=claude_env())
    except (OSError, subprocess.TimeoutExpired) as e:
        raise AiError(type(e).__name__) from None
    if proc.returncode != 0:
        raise AiError("cli exit %d" % proc.returncode)
    return parse_cli_json(proc.stdout)


def build_prompt(raw_title, raw_content, now):
    return (
        "Sen o'zbek tilida ishlaydigan yordamchisan. Foydalanuvchi DIQQAT "
        "ETISHMOVCHILIGI (ADHD) bor: u o'z g'oyalari va vazifalarini ovoz bilan "
        "aytadi, keyin ishini davom ettiradi - uni to'xtatib o'qishga vaqti "
        "yo'q.\n\n"
        "Quyida uning XOM eslatmasi (sarlavha + to'liq matn) va hozirgi vaqt "
        "kelgan. Buni tekshirib, JSON qaytar:\n"
        "- kind: \"idea\" (g'oya/keyinroq kerak), \"task\" (aniq ish, bajarilishi "
        "kerak) yoki \"noise\" (bo'sh, /start kabi behuda matn).\n"
        "- title: 70 belgidan oshmaydigan, BIR QARASHDA O'QILADIGAN satr, "
        "shablon: \"<qisqa nom> — <bir satrlik xulosa>\". Foydalanuvchining "
        "so'zlarini saqla, yangi ma'no o'ylab topma.\n"
        "- description: toza yozilgan to'liq matn (o'zbekcha, lekin "
        "foydalanuvchining asl so'zlari va atamalarini saqlab).\n"
        "- priority: high/medium/low/none - faqat matnda urg'u bo'lsa.\n"
        "- due: FAQAT u aniq vaqt yoki sana aytsa (ISO-8601, ofset bilan). "
        "Vaqt aytilmagan bo'lsa null - o'zingiz to'qima.\n"
        "- reminder_minutes_before: due bo'lsa eslatma necha daqiqa oldin "
        "(0..1440), aks holda null.\n\n"
        "Hozirgi vaqt (%s): %s\n\n"
        "XOM eslatma sarlavhasi: %s\nXOM eslatma matni:\n%s"
        % (TZ_NAME, now.strftime("%Y-%m-%d %H:%M (%A)"), raw_title,
           raw_content or "(bo'sh)")
    )


# -- validation + TickTick field building ----------------------------------


def parse_due(value, now):
    """ISO-8601 with offset -> aware datetime, else None."""
    if not isinstance(value, str) or not value.strip():
        return None
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_tz())
    return dt


def validate_ai(res, now):
    """Code check before anything is written. Returns (ok, reason)."""
    if not isinstance(res, dict):
        return False, "shape"
    if res.get("kind") not in KINDS:
        return False, "kind"
    title = res.get("title")
    if not isinstance(title, str) or not (1 <= len(title.strip()) <= 70):
        return False, "title"
    due = res.get("due")
    if due is not None:
        dt = parse_due(due, now)
        if dt is None:
            return False, "due-parse"
        if dt < now - datetime.timedelta(days=1):
            return False, "due-past"
    if res.get("priority") not in PRIORITY_MAP:
        return False, "priority"
    return True, ""


def ticktick_due(dt):
    """TickTick format yyyy-MM-dd'T'HH:mm:ss+0000, in UTC."""
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")


def update_fields(res, raw_content, now):
    """The POST /task/{id} body for a tidy task (title, content, priority,
    then due+reminders). Ideas: priority low unless the model said high;
    a due is written only when the model returned one."""
    kind = res["kind"]
    title = res["title"].strip()
    content = res.get("description", "") + "\n\n---\nAsl matn: " + (raw_content or "")
    if kind == "idea":
        priority = 5 if res.get("priority") == "high" else 1
    else:
        priority = PRIORITY_MAP.get(res.get("priority"), 0)
    fields = {"title": title, "content": content, "priority": priority}
    dt = parse_due(res.get("due"), now)
    if dt is not None:
        fields["dueDate"] = ticktick_due(dt)
        fields["timeZone"] = TZ_NAME
        fields["isAllDay"] = False
        n = res.get("reminder_minutes_before")
        if isinstance(n, int) and 0 <= n <= 1440:
            fields["reminders"] = (["TRIGGER:-PT%dM" % n] if n > 0
                                   else ["TRIGGER:PT0S"])
    return fields


# -- projects --------------------------------------------------------------


_PROJECT_KEYS = {"📥 Kiruvchi": "kiruvchi", "G'oyalar": "goyalar",
                 "✅ Vazifalar": "vazifalar"}


def forget_projects(state):
    """Drop every cached project id; the next resolve_project re-fetches."""
    state["project_ids"] = {}
    save_state(state)


def resolve_project(state, name, save=True):
    """find-or-create by name, id cached in the state file."""
    ids = state.setdefault("project_ids", {})
    key = _PROJECT_KEYS.get(name, name)
    pid = ids.get(key)
    if pid:
        return pid
    pid = ticktick.find_or_create_project(name)
    ids[key] = pid
    if save:
        save_state(state)
    return pid


# -- telegram bot inbox ------------------------------------------------------


def _bot_header_time(header):
    """Line 1 looks like
    '2026-11-03T06:05:31.9298632+05:00 message_id=380 audio=? type=text'
    - the leading timestamp is the message time."""
    parts = (header or "").split()
    return parts[0] if parts else ""


def run_bot_inbox(state, now=None):
    """New IDEA_BOT_INBOX *.txt files -> raw tasks in Kiruvchi. Read-only on
    the folder; state (bot_seen) is saved after EVERY posted file."""
    inbox = os.environ.get("IDEA_BOT_INBOX")
    if not inbox or not os.path.isdir(inbox):
        return
    kiruvchi = resolve_project(state, ticktick.KIRUVCHI)
    names = sorted(n for n in os.listdir(inbox) if n.lower().endswith(".txt"))
    seen = state.setdefault("bot_seen", [])
    if state.get("bot_since") is None:
        # first run: every file already there is a test file - mark it seen
        state["bot_since"] = (now or now_local()).isoformat()
        for n in names:
            if n not in seen:
                seen.append(n)
        save_state(state)
        return
    for n in names:
        if n in seen:
            continue
        try:
            with open(os.path.join(inbox, n), "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except OSError:
            continue
        header_time = _bot_header_time(lines[0] if lines else "")
        text = "\n".join(lines[1:]).strip()
        if not text:
            seen.append(n)
            save_state(state)
            continue
        title = " ".join(text.split())[:60]
        content = text + "\n\n[manba: Telegram %s]" % header_time
        ticktick.create_task(kiruvchi, title, content)
        log_line(n, "bot", 0, "ok")
        seen.append(n)
        save_state(state)  # per item: a crash never reposts this file


# -- the Kiruvchi queue ------------------------------------------------------


def _task_sort_key(t):
    """Oldest first when the API exposes a timestamp; else API order."""
    for k in ("createdTime", "modifiedTime", "startDate"):
        v = t.get(k)
        if isinstance(v, str):
            return (0, v)
    return (1, "")


def retry_moved(state, now=None):
    """Finish tasks a crashed run left half-way, with the STORED answer (no
    new Claude call). 'moving' = the answer was saved but the move may or may
    not have happened: redo the move, tolerating 'already moved'. 'moved' =
    the move is done: update. The update goes straight to the target list
    (no project_tasks pre-filter, which could hide a moved task); 404 means
    the task is gone."""
    now = now or now_local()
    done = state.setdefault("done", {})
    results = state.setdefault("results", {})
    fails = state.setdefault("fails", {})
    for task_id in [i for i, v in done.items() if v in ("moving", "moved")]:
        stored = results.get(task_id)
        if not stored:
            done[task_id] = "done"  # nothing to update with; do not loop
            save_state(state)
            continue
        kind = stored.get("kind", "?")
        target = stored.get("target")
        t0 = time.monotonic()
        move_tolerated = False
        try:
            if done[task_id] == "moving":
                kiruvchi = resolve_project(state, ticktick.KIRUVCHI)
                try:
                    ticktick.move_task(task_id, kiruvchi, target)
                except ticktick.TickTickError as e:
                    if e.status not in (400, 404):
                        raise
                    move_tolerated = True  # most likely already moved
                done[task_id] = "moved"
                save_state(state)
            fields = update_fields(stored["ai"], stored.get("raw_content", ""), now)
            ticktick.update_task(task_id, target, fields)
        except ticktick.TickTickError as e:
            ms = int((time.monotonic() - t0) * 1000)
            if e.status == 404 and done[task_id] == "moved":
                if move_tolerated:
                    # the move never happened and the task is not in the
                    # target: reprocess it from Kiruvchi (bounded by fails)
                    done.pop(task_id, None)
                    results.pop(task_id, None)
                    fails[task_id] = fails.get(task_id, 0) + 1
                    log_line(task_id, kind, ms, "err requeue")
                else:
                    done[task_id] = "done"  # deleted/completed manually
                    log_line(task_id, kind, ms, "err gone")
                save_state(state)
            else:
                log_line(task_id, kind, ms, "err %s" % e.status)
            continue
        done[task_id] = "done"
        save_state(state)
        log_line(task_id, kind, int((time.monotonic() - t0) * 1000), "ok")


def process_tasks(state, now=None):
    """Open Kiruvchi tasks, oldest first, max 10: Claude -> code check ->
    move FIRST -> update. Every step saves the state file."""
    now = now or now_local()
    kiruvchi = resolve_project(state, ticktick.KIRUVCHI)
    goyalar = resolve_project(state, ticktick.GOYALAR)
    vazifalar = resolve_project(state, ticktick.VAZIFALAR)
    targets = {"idea": goyalar, "task": vazifalar}
    done = state.setdefault("done", {})
    fails = state.setdefault("fails", {})
    results = state.setdefault("results", {})
    try:
        try:
            tasks = ticktick.project_tasks(kiruvchi)
        except ticktick.TickTickError as e:
            if e.status != 404:
                raise
            # cached list id is stale (list deleted/re-created): drop the
            # cache, re-resolve ONCE, retry
            forget_projects(state)
            kiruvchi = resolve_project(state, ticktick.KIRUVCHI)
            targets = {"idea": resolve_project(state, ticktick.GOYALAR),
                       "task": resolve_project(state, ticktick.VAZIFALAR)}
            tasks = ticktick.project_tasks(kiruvchi)
    except ticktick.TickTickError as e:
        log_line("kiruvchi", "?", 0, "err %s" % e.status)
        return
    processed = 0
    for t in sorted(tasks, key=_task_sort_key):
        if processed >= MAX_TASKS_PER_RUN:
            break
        task_id = t.get("id")
        if not task_id or task_id in done:
            continue
        if fails.get(task_id, 0) >= MAX_FAILS:
            continue  # already logged "ai-xato" on the 3rd failure
        raw_title = t.get("title") or ""
        raw_content = t.get("content") or ""
        t0 = time.monotonic()

        stored = results.get(task_id)
        if stored:  # a saved answer from an earlier crashed run
            res = stored["ai"]
        else:
            try:
                res = call_claude(build_prompt(raw_title, raw_content, now))
            except AiError as e:
                fails[task_id] = fails.get(task_id, 0) + 1
                save_state(state)
                code = "ai-xato" if fails[task_id] >= MAX_FAILS else "err %s" % e
                log_line(task_id, "?", int((time.monotonic() - t0) * 1000), code)
                continue
        ok, reason = validate_ai(res, now)
        if not ok:
            fails[task_id] = fails.get(task_id, 0) + 1
            save_state(state)
            code = "ai-xato" if fails[task_id] >= MAX_FAILS else "check %s" % reason
            log_line(task_id, "?", int((time.monotonic() - t0) * 1000), code)
            continue
        ms = int((time.monotonic() - t0) * 1000)
        kind = res["kind"]
        try:
            if kind == "noise":
                ticktick.complete_task(kiruvchi, task_id)
                done[task_id] = "done"
                save_state(state)
                log_line(task_id, kind, ms, "ok")
            else:
                target = targets[kind]
                # answer + target saved BEFORE the move: a crash right after
                # the move still finds the stored answer ("moving" is retried)
                results[task_id] = {"ai": res, "kind": kind, "target": target,
                                    "raw_title": raw_title,
                                    "raw_content": raw_content}
                done[task_id] = "moving"
                save_state(state)
                ticktick.move_task(task_id, kiruvchi, target)  # move FIRST
                done[task_id] = "moved"
                save_state(state)
                ticktick.update_task(task_id, target,
                                     update_fields(res, raw_content, now))
                done[task_id] = "done"
                save_state(state)
                log_line(task_id, kind, ms, "ok")
        except ticktick.TickTickError as e:
            log_line(task_id, kind, ms, "err %s" % e.status)
            if e.status == 404:
                forget_projects(state)  # a cached list id may be stale
            # left as-is: "moving"/"moved" tasks are finished by retry_moved next run
        processed += 1


def run_once():
    state = load_state()
    try:
        run_bot_inbox(state)
    except ticktick.TickTickError as e:
        log_line("bot", "?", 0, "err %s" % e.status)
    retry_moved(state)
    process_tasks(state)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--help" in argv:
        print("usage: python capture\\idea_processor.py --once")
        return 0
    lock = acquire_lock()
    if lock is None:
        return 0  # another instance is running
    try:
        run_once()
    finally:
        try:
            lock.close()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
