# Idea / task capture ("bir tugma -> TickTick") - SPEC v1

Owner approval: 2026-11-08 "Xo'p, aytganlarimni qilib boshlayver". Research + why: side-session note
idea-capture-plan-2026-11-08.md (shared notes of session local_c7878262).

## Owner's need (his words, summarised)
Ideas and tasks come constantly; he will not stop working for fear of forgetting them. He presses ONE button, speaks,
and goes on. The AI (Claude Sonnet, high effort, on his subscription - his choice) decides idea vs task, writes a short
main line he reads at a glance, the full text in the description, and reminds him at the right time. Main place: TickTick.

## Shape (one queue, nothing lost)
All sources write the RAW text into ONE TickTick list "📥 Kiruvchi" first (so a failed AI step never loses a note and
the note is already visible). The processor then rewrites each raw task IN PLACE (title, content, priority, due,
reminder) and MOVES it to "💡 G'oyalar" or "✅ Vazifalar". Noise ("hi", "/start", empty) is completed, not deleted.

Sources:
1. PC: new hold-hotkey `idea_hotkey` (default "ctrl+alt", hold both; release either = stop) in windows/gemini_mic.py.
   Guard (review 11-08: he is a video editor, Ctrl+Alt+<key> are app shortcuts; AltGr = LCtrl+RAlt): recording
   starts only after Ctrl+Alt are held ALONE for 0.35 s; any other key pressed while held = discard silently.
   Same recording + transcription path as Right Ctrl; at the end, instead of paste_text: post raw to Kiruvchi
   (title = first 60 chars, content = full transcript + "\n\n[manba: PC <time>]"). Badge shows "Saqlandi" (green, 1.5 s).
   On TickTick failure: append to %APPDATA%\GeminiMic\idea-outbox.jsonl and retry every 60 s; never paste the text.
   Right Ctrl behaviour must stay exactly as today.
2. Phone (Android, app/): Volume-DOWN HOLD = idea capture (owner 11-08: phone typing not needed). Tap still = normal
   volume down. After transcription: POST raw to Kiruvchi directly (phone has internet even when PC is off);
   on failure keep in a local queue file and retry (on next capture + every 5 min while the service lives).
   Short vibration on start and on saved (screen is broken - he cannot read it); 3 long pulses when the post
   failed and the note is queued (token expired / no internet). Volume tap: keep the existing proven path
   (consume, then adjustSuggestedStreamVolume on a tap < 250 ms). TickTick token: copied into the app
   once via the existing PC relay pairing or a settings field (doer picks the simplest that needs no typing on the
   broken screen; report which).
   Screen OFF / locked: try to make the hold work; AccessibilityService likely gets no volume keys with screen off
   (research: they go to an active MediaSession). If not doable cleanly, v1 = works with screen on/lock screen, and
   the report says so. Must be measured on HIS phone, not assumed.
3. Telegram task bot (@ coach token, Jarvis-TaskBot, system-owned ~/.claude - DO NOT EDIT): it already saves text/voice
   transcripts to C:\Users\mirko\.claude\channels\coach\voice-inbox\*.txt. Processor READS new files (state file of
   seen names, flushed to disk after EACH successful post) and posts each as raw to Kiruvchi. First run: mark
   all files older than the processor's install time as seen (the 5 existing ones are tests). Read-only on that folder.

Processor: gemini-mic/capture/idea_processor.py (new), run by Windows scheduled task every 2 min (hidden, like the
other Jarvis tasks; NOT registered by the doer - commander registers after review).
- Lists: find-or-create "📥 Kiruvchi", "💡 G'oyalar", "✅ Vazifalar" by name (cache ids in state file). The PC app
  uses the same capture/ticktick.py helper to resolve the Kiruvchi projectId. Phone gets token + kiruvchi_id from
  the PC relay: NEW `GET /ticktick` on the existing relay server, same relay-token auth as /cmd, returns
  {"access_token", "kiruvchi_id"}; the phone stores both at pairing and refreshes them on 401.
- Single instance: named mutex / lock file at start; a second run exits at once. Task Scheduler: do not start a new instance.
- For each open task in Kiruvchi (oldest first, max 10 per run): POST the raw text and now (Asia/Tashkent) to the
  AI chain GLM glm-5.3 (api.z.ai, key from C:\Users\mirko\.claude\.secrets\glm.key) -> OpenRouter
  google/gemini-3-flash-preview -> Google gemini-3-flash-preview (keys from %APPDATA%\GeminiMic\config.json;
  requests, timeouts 10/60 s, first provider whose answer parses as a JSON dict wins).
  Schema: {kind: idea|task|noise, title (<= 70 chars: "<short name> — <one-line takeaway>"), description (cleaned
  full text, Uzbek, his words kept), priority: high|medium|low|none, due: ISO datetime or null (only when he named a
  time/date), reminder_minutes_before: int or null}.
- Code check before writing: kind valid, title 1..70 chars, due parses and is not in the past by > 1 day; otherwise
  leave the task in Kiruvchi untouched and log (retry next run, after 3 failures add tag "ai-xato" and skip).
- Write (order matters - review 11-08): FIRST move to the target list and record "moved" in the state file, THEN
  update title, content = description + "\n\n---\nAsl matn: " + raw, priority (5/3/1/0), dueDate+timeZone
  "Asia/Tashkent"+reminders ["TRIGGER:-PT<n>M"] when due, then move to the target list. Idempotent: state file maps
  task id -> done, so a crash mid-run never duplicates.
- Ideas: priority low unless he said urgent; no due unless he named one. Tasks: priority by urgency words + due.
- Log: %APPDATA%\GeminiMic\idea-processor.log (one line per item: id, kind, ms, ok/err). No raw text in the log.

TickTick client: gemini-mic/capture/ticktick.py (new, small, requests-based): token from
D:\vibecoding\_secrets\ticktick-token.json (never printed/logged), base https://api.ticktick.com/open/v1. Needs
scope "tasks:read tasks:write": the auth step in D:\vibecoding\_tools\ticktick\ticktick-tasks.mjs requests both
(commander change) and the owner clicks Allow once.

## Out of v1 (later, ask first)
Morning triage (top 3 into "Bugun"), Sunday idea review, Telegram reminders, Devor break-screen list.

## Done = measured
- PC: 3 real holds of Ctrl+Alt -> 3 tasks appear in Kiruvchi within 10 s of release, then tidy in G'oyalar/Vazifalar
  within 3 min; Right Ctrl still pastes. A "ertaga soat 15:00 da X" note gets due 15:00 + reminder.
- TickTick down (bad token) -> nothing lost: outbox holds it, delivered after token fixed.
- Bot: a text sent to the task bot shows up tidy in TickTick within 3 min.
- Phone: Volume-Down hold on his phone -> task in Kiruvchi; screen-off result reported as measured.
- Tests: unit tests for schema check, idempotence, outbox retry, hotkey parsing; existing gemini-mic tests still pass.
