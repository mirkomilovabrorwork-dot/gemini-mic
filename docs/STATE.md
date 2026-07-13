# Gemini Mic — STATE

_Trigger words: "gemini", "gemini mic". Source of truth for resume._

## STATUS (resume board) - 2026-07-11
- Docs-only maintenance: corrected `CLAUDE.md` typo `selftest` -> `self-test`.
- Product code unchanged. Next: resume the previously planned product work.

## What this is
System-wide voice keyboard for Android: hold a floating mic → record → Gemini
transcribes (mixed Uzbek/English/Russian) → text is auto-typed into the focused
field via an accessibility service. Pure Android SDK (Java), no third-party deps.
Package `com.autosmart.geminimic` (debug suffix `.debug`).

## Origin
Original Codex-built project source was lost (not on D:/C:/GitHub). Reconstructed
1:1 by decompiling `GeminiMic-Simple-Android-debug.apk` (androguard) into a clean
Java Gradle project. Decompiled reference + spec live in `D:\vibecoding\geminimic-recovered\`.

## KNOWN LIMITATION — deferred by owner 2026-07-13
- **Accented loanwords get normalized to formal Uzbek synonyms** (owner: says
  "kontrolni tekshirish" → model writes "nazoratni tekshirish"). Root cause:
  generative-LLM ASR "cleans up" accented speech toward formal language; when a
  loanword is pronounced with an Uzbek accent the model perceives it as Uzbek
  and swaps it for the dictionary equivalent. A/B on English-voice TTS did NOT
  reproduce it (model kept control/process/result — clean audio isn't
  ambiguous), and a blind "VERBATIM, don't swap synonyms + kontrol≠nazorat
  example" prompt rule did NOT help on the testable clip and even added a
  spurious word. The only real fix path = A/B on the OWNER'S real voice (prompt
  vs prompt, 3.5 vs 3-flash-preview). **Owner declined the 30-sec voice capture
  ("kerak emas") → deferred. Do NOT ship a blind prompt change.** Reopen only
  with his real audio. Harness ready: scratchpad/ab_verbatim.py.

## GOAL (owner's words)
Voice typing that "just works" on BOTH phone and PC: hold a key/mic, speak
mixed Uzbek/English/Russian, the text lands in the focused field — free
(Gemini free tier), no fiddling. Owner shares it with a friend as a zip.

## STATUS (resume board) — 2026-07-12 (v11)
- **Windows now auto-inserts WITHOUT clicking the field first** (owner wanted
  phone-parity). Added UI Automation (desktop cousin of Android accessibility):
  before pasting, if no editable is already focused, walk the FOREGROUND window
  for an editable control and SetFocus it, then the existing Ctrl+V lands there.
  Strictly additive/no-regression: existing focus is respected (not hijacked);
  UIA miss/error → plain paste as before. Bounded walk (depth 18, 1.5s).
  Commit 30bc4d2. New dep `uiautomation` (comtypes); requirements.txt + build.bat
  updated with --collect-all comtypes/uiautomation (build.bat was ALSO missing
  the pre-existing sounddevice/pynput flags → would've built a broken exe → fixed).
- VERIFIED hard (import is behind try/except = silent-off risk): e2e on Notepad
  no-click → focus=True + text landed; and a FROZEN probe exe proved uiautomation
  imports + GetForegroundControl works when packaged (yinkaisheng lib needs no
  runtime typelib codegen). Windows exe rebuilt 33.1 MB (hash-match running),
  zip refreshed (47.4 MB, feature verified in zip source). Lesson: [[playbook_gotchas_windows_ps]].
- **"Ishlamadi" false alarm (2026-07-12): the app simply WASN'T RUNNING** when
  the owner tested (no crash in Event Log — PC likely rebooted; Windows had no
  autostart, so unlike Android there wasn't even a notification). Fixed the
  class: **Startup shortcut added** on the owner's machine
  (%APPDATA%\...\Startup\GeminiMic.lnk → Desktop exe) so it launches on every
  boot. Relaunched, stable 12s+, hash = new build. TODO next zip refresh: add a
  "put a shortcut in shell:startup" line to HOW-TO-USE.txt for the friend.
- **2nd "ishlamadi" (2026-07-12) SOLVED VIA THE NEW LOG — clipboard-paste race
  (reviewer's F4) was the real killer**: log proved the whole chain worked
  (record→Gemini transcript→UIA focused the Electron editable→Ctrl+V sent 4×)
  yet no text appeared — the app restored the OLD clipboard 0.15s after Ctrl+V,
  and Electron windows read the clipboard AFTER that → transcript vanished.
  (Notepad pastes instantly, so the earlier e2e falsely passed.) Fix commit
  03ea17c (win+mac): hold clipboard 1.2s before restore + 0.15s settle after
  SetFocus. Exe rebuilt+running (hash match). AWAITING owner retest.
  Note: dictating while an Electron app (e.g. Claude) is foreground correctly
  pastes INTO that app's input — text lands wherever the front window is.
- **3rd "ishlamadi" (2026-07-12) — REAL bug found by live Chrome experiment:
  first-hit editable selection pasted into the WRONG field** (Chrome: the
  ADDRESS BAR got the marker; Electron: an invisible helper input, name='' in
  the owner's log — chain looked green 7×, text landed where nobody looks).
  Fix commit 4a4fc2d: collect ≤12 visible candidates, score Edit>Document
  (a web page IS a Document — focusing it pastes nowhere), in-content>chrome,
  area tiebreak; junk-filter tiny edits (<900px²)/small fragments (<50k px²,
  "Loading…" case seen live) → only junk = DON'T hijack, plain paste as before.
  Live-verified: Chrome textarea received the marker with new scoring (address
  bar with old). Exe rebuilt+running (hash match).
- **FINAL VERDICT on no-click (owner CLOSED it 2026-07-12: "ishlamasa, mayli,
  kerak emas")**: latest log shows the scoring works, but in ELECTRON apps
  (Claude etc.) UIA sees NO real editable at all ("no editable found") —
  Electron doesn't expose its inputs to Windows accessibility unless forced
  (per-app --force-renderer-accessibility tricks = deep fragile rabbit hole).
  So: no-click WORKS in Chrome/Notepad-class apps, NOT in Electron; falls back
  harmlessly (no hijack, plain paste). Owner accepted click-first as the way.
  DO NOT reopen this without new evidence — the whole 3-round debug ladder
  (clipboard race → wrong-editable → Electron-no-a11y) is documented in
  [[playbook_gotchas_windows_ps]].
- **Owner-approved consolation (Windows)**: when no text field is confirmed, the
  transcript STAYS in the clipboard so a missed paste is one Ctrl+V away
  (previously the restore destroyed it — a 13s dictation was lost).
  **Nag removed (commit 272b6c1)**: the "clipboardga yozildi" balloon fired on
  EVERY Electron dictation (target never confirmable there) and can't tell real
  failure from unconfirmable — so per owner it's gone; recording is signalled by
  the start beep (1000Hz) + red tray "recording…" + done beep (660Hz), clipboard
  keep is silent. Confirmed-target path unchanged. Exe rebuilt + running (hash
  match). Share zip NOT yet refreshed with this build (do with next zip refresh
  + HOW-TO autostart line).
- **Mac still needs a click** (uiautomation is Windows-only; mac parity would need
  the macOS AXUIElement accessibility API — separate future work). Android already
  inserts without a click. So: Android ✅, Windows ✅ (new), Mac ⏳.
- OWNER TODO unchanged: enable billing for reliable paid 3.5 (optional). Open
  review findings F6/F9/F4/F8 from v5 still queued.

## STATUS (resume board) — 2026-07-11 (v10)
- **Desktop no-speech hallucination — real root cause found + fixed** (owner:
  press-without-speaking still fabricated a story on desktop; Android is fine).
  MEASURED his mic (sounddevice, local): true silence rms<80 (already rejected by
  the old gate), but a single keyboard click clips one 0.1s window to full-scale
  and the old WHOLE-CLIP-AVERAGE RMS gate let that lone transient inflate the
  average past threshold → noise reached Gemini → hallucination.
  Fix (commit b431240, windows + mac): replaced the average-RMS gate with
  has_speech() — a mini energy-VAD that counts 0.2s windows clearing rms 250 and
  requires ≥3 (~0.6s sustained). Verified: speech=True, silence=False,
  single-click=False, short-0.7s-word=True. Android untouched (its gate works).
  Both selftests pass; Windows exe rebuilt (hash-match running), Mac CI
  29168390715, zip refreshed (46.1 MB) — gate verified INSIDE zip source.
  Lesson: [[playbook_gotchas_llm]] (avg RMS also fooled by a lone transient).
- Params if tuning needed: VOICE_RMS_THRESHOLD=250, MIN_VOICED_WINDOWS=3,
  VOICE_WINDOW_SEC=0.20 (windows+mac, near line ~54). Raise MIN_VOICED to reject
  more; lower VOICE_RMS if it rejects the owner's real quiet speech.

## STATUS (resume board) — 2026-07-11 (v9)
- **MODEL SWAP: primary is now gemini-3.5-flash** (owner: 3-flash-preview
  mis-transcribes his mixed uz/en — Uzbek↔English swaps). Fallback →
  gemini-3-flash-preview (different model = separate 429 quota). All 3 platforms
  + the owner's saved Windows config.json (a default change alone wouldn't reach
  a saved config). Commit 7ed1125; Android CI 29167414378, Mac 29167414367,
  Windows exe rebuilt (hash-match running). Live sanity: 3.5 keeps clean English.
- **Language-preservation prompt fix now on ALL 3** (was Windows-only in v8):
  softer uz_en hint + CRITICAL "transcription not translation, never romanize
  English" rule. Bundled into this rebuild.
- **Owner key strategy = ONE PAID key, 3.5 primary** (his choice). KEY FACT
  taught: Gemini free vs paid is per-PROJECT/billing, not a per-call switch —
  enabling billing deletes the free tier; 'free-first-then-paid' would need TWO
  keys. He picked single-paid for simplicity (his volume cost ≈ cents/mo).
  Lesson: [[playbook_gotchas_llm]].
- Share zip refreshed (46.1 MB) — 3.5-primary + anti-translate verified INSIDE
  zip source + APK. Desktop apk/exe current.
- **OWNER TODO: to actually get the reliable PAID tier, enable billing on the
  Gemini project for his key (aistudio.google.com → billing). Until then the key
  is free-tier 3.5 (daily-limited).** The app needs NO change for paid — same key.
- STILL VERIFY (owner, his real voice): does 3.5 fix the uz↔en language errors?
  If yes → done. If still wrong → next lever (dedicated language modes / test 3.5
  vs 3-flash A/B on his voice). Open review findings from v5 remain (F6/F9/F4/F8).

## STATUS (resume board) — 2026-07-11 (v8)
- **English-spoken-comes-out-Uzbek fix (Windows, owner report)**: on Windows,
  speaking English sometimes got translated to Uzbek or romanized in Uzbek Latin.
  LIVE A/B (Windows-SAPI English clip, old vs new prompt) showed BOTH prompts
  keep CLEAN English perfect → the real trigger is the owner's ACCENTED English
  that the Uzbek-primed prompt nudges toward Uzbek; TTS can't reproduce it.
  Fix (commit 38ad573, **Windows only so far**): de-primed the uz_en hint ("a
  sentence may be entirely English or Uzbek; never translate or romanize") + a
  CRITICAL "transcription NOT translation, never rewrite English in Uzbek
  spelling" rule. Verified NEUTRAL on clean English; UNVERIFIED for the accented
  case → owner tests his real voice. Windows exe rebuilt + running (hash-match).
  **PENDING: if it helps on his voice → mirror the same 2 prompt edits to
  GeminiClient.java (Android) + mac/gemini_mic_mac.py, rebuild, refresh zip.**
  Lesson: [[playbook_gotchas_llm]] (clean TTS test can't repro accented ASR bug).
- Share zip NOT yet refreshed for this change (Windows-only, pending confirm).

## STATUS (resume board) — 2026-07-09 (v7)
- **Desktop hallucination root-cause fix** (owner: "Android eshitilmadi deb AI'ga
  yubormaydi, Windows hali ham to'qiyapti"): Android's LOCAL amplitude gate
  rejects silence before the API call; the desktop port used a single-PEAK gate
  (500 int16) that noisier PC mics exceed on a quiet room → silence reached
  Gemini → fake transcript. The NO_SPEECH prompt is only a backstop (can't save
  noisy-but-not-silent audio — model returns invented words, not the token).
  Fix (commit 91d3e88, windows + mac): replaced peak gate with an **RMS energy
  gate at 200** — noise(rms~80) rejected, speech(rms~1500) sent. Threshold is a
  single tunable knob if a mic differs. Android unchanged (its gate already
  works per owner). Both selftests pass; RMS separation verified.
- Rebuilt: Windows exe (RMS build, **hash-confirmed = the running Desktop
  GeminiMic.exe**, PID relaunched), Mac .app (CI 29035931250 from 91d3e88).
  GeminiMic-share.zip refreshed (46.1 MB) — mac .app binary + all source carry
  the RMS gate (verified inside zip). Lesson: [[playbook_gotchas_llm]].
- If it STILL fabricates on Windows with THIS build: the mic's noise floor is
  above rms 200 → raise SILENCE_RMS_THRESHOLD (windows/mac line ~54). If it now
  rejects the owner's real quiet speech → lower it. One-number autoresearch loop.

## STATUS (resume board) — 2026-07-09 (v6)
- **Hallucination fix (owner-reported, the worst dictation bug)**: pressing
  without clear speech / noisy audio made Gemini FABRICATE a whole invented
  speech (e.g. a "personal branding" talk never said). Fixed on all 3 platforms
  (commit 305143b): prompt now orders the model to output token NO_SPEECH for
  silent/unintelligible audio and never invent content; code detects the
  sentinel (strip non-letters → match NOSPEECH) + empty → "Ovoz eshitilmadi",
  types nothing. Matcher verified: rejects real speech, catches [NO_SPEECH].
  MITIGATION not a 100% guarantee (generative model can still occasionally
  confabulate) — owner verifies live. Lesson saved: [[playbook_gotchas_llm]].
- Rebuilt all 3 GREEN (Android 29032947054, Mac 29032947304, local exe) and the
  fix VERIFIED INSIDE the shipped zip + APK (read back out). Desktop refreshed:
  APK + exe (running, PID replaced) + GeminiMic-share.zip (46.1 MB).
- Still-open review findings (next batch when owner says): F6 finishReason/
  MAX_TOKENS truncation, F9 arm-notif needs POST_NOTIFICATIONS, F4 desktop
  clipboard image-loss/restore-race, F8 "No audio" toast while busy (Android).

## STATUS (resume board) — 2026-07-08 (v5)
- **Senior-review pass done (owner asked "critical analiz")**: independent
  adversarial review of the whole product graded it C and found real bugs.
  Owner approved fixing the 4 worst → ALL FIXED + re-verified by the same
  reviewer (verdict: SHIP), commit 4193858:
  (F1) Android placeholder heuristic could WIPE user text → deleted, only exact
  placeholder list matches now. (F2) desktop stale 60s watchdog killed the next
  recording → record_gen generation guard. (F3) desktop quick-tap left a 60s
  ghost recording → hotkey_down press/release flag + abort in start_recording.
  (F5) mac default hotkey right Ctrl doesn't exist on MacBooks → default now
  RIGHT CMD (cmd keys added to keymap; right ctrl still selectable). Mac README
  + HOW-TO updated. **Mac hotkey answer for owner: hold RIGHT CMD (⌘).**
- All 3 rebuilt GREEN (Android run 28918771980, Mac 28918771923, local exe) and
  the FIXES VERIFIED INSIDE the shipped zip (read the java/py back out of it).
  Desktop refreshed: GeminiMic-android.apk + GeminiMic-share.zip (46.1 MB).
  Desktop GeminiMic.exe + GeminiMic-windows.exe NOW REPLACED with the fixed
  build (owner closed it → stopped/copied/relaunched, hashes verified match
  windows/dist/GeminiMic.exe, running PID confirmed). All 3 Desktop deliverables
  current.
- **Review findings left OPEN (owner not yet asked / next batch candidates):**
  (F6) finishReason/MAX_TOKENS never checked → long fast speech silently
  truncates mid-sentence (all 3 platforms; cheap fix: maxOutputTokens 4096 +
  check finishReason). (F9) if POST_NOTIFICATIONS denied, post-boot arm
  notification silently never shows. (F4) desktop clipboard: image/file
  clipboard lost after dictation + 0.15s restore race. (F8) dictating while
  a transcription is in flight → misleading "No audio" toast (Android).
  Plus MINORs: raw HTTP error toasts, key in URL query (prefer header),
  Tk settings in a thread, crash handler can't launch from background.
- OWNER TODO: (1) phone: install new APK, test dictation + reboot-arm;
  (2) PC: close running GeminiMic.exe, replace with the new one, test;
  (3) decide: fix F6+F9 next batch? ("ha" = qilaman)
- **Readability fix (all 3 platforms)**: casual dictation often came back with no
  sentence punctuation, so `formatParagraphs` (splits on `.?!`) couldn't break it
  → one run-on block. Prompt now asks Gemini for natural sentence punctuation +
  capitalization. Same edit in GeminiClient.java + windows/gemini_mic.py +
  mac/gemini_mic_mac.py (kept identical).
- **Android reboot survival (one-tap arm)**: Android 14 forbids starting a mic
  foreground service from background / BOOT_COMPLETED. Solution WITHOUT a boot
  receiver: the accessibility service auto-rebinds on boot →
  `onServiceConnected` posts a "Yoqish uchun bosing" notification → tapping it
  opens `ArmActivity` (translucent, no-history) which — being foreground — starts
  the mic service. Notification cancelled on tap / on service start / skipped when
  already running or no key. New file ArmActivity.java + manifest entry. Orphan
  Prefs BUBBLE_X/Y dropped. Independently reviewed: no blockers.
- All THREE built GREEN this session (Android run 28917789116, Mac 28917789123,
  Windows exe via PyInstaller). Fresh APK verified (models ok, ArmActivity present,
  no overlay/boot perms). Docs (README.md, HOW-TO-USE.txt) de-bubbled + HOW-TO
  model line corrected (primary=3-flash-preview) + reboot-arm step added.
- Delivery: Desktop `GeminiMic-android.apk` refreshed; `GeminiMic-share.zip`
  rebuilt with all fresh source + 3 binaries + corrected HOW-TO. **Desktop
  `GeminiMic.exe` NOT swapped** — the running copy was file-locked; owner must
  close it then replace with `windows/dist/GeminiMic.exe` (or from the zip).
- OWNER TODO: (1) test punctuation/breaks on phone; (2) test reboot → tap arm
  notification → volume-down still types; (3) to update his PC exe, close the
  running GeminiMic.exe and replace it.

## STATUS (resume board) — 2026-07-07 (v3)
- **Android bubble REMOVED** (owner: "volume yetadi"). Volume-Down hold-to-talk is
  now the ONLY Android trigger. Dropped the whole floating overlay UI from
  MicOverlayService (recording engine + volume start/stop/cancel bridge + fg
  notification kept intact), the "Ustidan chizish" checklist row + overlay gate
  from MainActivity, orphan `hasActiveTextInput()`, and **SYSTEM_ALERT_WINDOW**
  from the manifest → one fewer setup step for the friend. Feedback now = toast
  ("Recording") + persistent notification (Ready/Transcribing). CI GREEN
  (run 28902251781); fresh APK verified (correct models, overlay perm ABSENT in
  compiled manifest) → copied to Desktop `GeminiMic-android.apk` + `dist/`.
- ⚠️ **share zip is now STALE** for Android: `GeminiMic-share.zip` still bundles
  the old bubble source + old APK + HOW-TO-USE.txt that mentions the bubble.
  REFRESH IT (source tree + new APK + reword HOW-TO) only AFTER owner confirms the
  no-bubble build works on his phone — else it'd be rebuilt twice.

## STATUS (resume board) — 2026-07-07 (v2)
- THREE platforms, all built & current: **Android** (app/, Java), **Windows**
  (windows/gemini_mic.py, tray), **macOS** (mac/gemini_mic_mac.py, rumps menu bar).
  Same Gemini core on all (prompt/clean/paragraph-format, verified identical).
- MODEL (final): primary **gemini-3-flash-preview** (good quality, ~3x cheaper on
  paid: $0.50/$3 vs 3.5-flash $1.50/$9 per 1M), fallback **gemini-3.5-flash**.
  Fallback fires on HTTP 404/429/500/503 AND on network/read-TIMEOUT (read
  timeout 30s). Both live-verified to transcribe accurately. Note `gemini-3.0-flash`
  does NOT exist (404); real ids = `gemini-3-flash-preview`, `gemini-3.5-flash`.
- v2 features this session:
  · Android: **Volume-Down hold-to-talk** (short press = normal volume; hold =
    record from key-DOWN so speech start isn't missed; via accessibility
    onKeyEvent + MicOverlayService volumeStart/Stop/Cancel bridge). Floating
    bubble still works. MainActivity fully **redesigned** (card UI, light/dark,
    permission checklist, one Start/Stop button; model picker removed).
  · Windows: single-instance mutex, startup beep/balloon (Win11 hides tray under ^),
    beep on record start/done, tray-tooltip guards, Settings modernized + model
    picker removed. Owner's live config = 3-flash-preview.
  · macOS: rumps menu bar (Cmd+V paste, right-Ctrl hold), model picker gone.
- BILLING (verified, official pricing): free tier = no billing, both flash models
  free but rate-limited PER DAY per model (owner's 3.5 daily quota got exhausted by
  my testing → resets daily). Paid = charged immediately, but CHEAP for dictation
  (~$1–5/mo; 3-flash-preview cheapest of the good ones). Paid also = data not used
  for training. App needs NO change for paid — same key, billing on Google's side.
- Delivery: fresh binaries on Desktop — `GeminiMic-android.apk`, `GeminiMic.exe`
  (installed+running), and `GeminiMic-share.zip` (46 MB: all source + all 3
  ready binaries + HOW-TO-USE.txt) for the friend who will continue developing.
- macOS CI: **build on `macos-14` (arm64)** — GitHub retired macos-13 Intel (it
  queues forever). So the `.app` is Apple-Silicon-only (Intel Macs build from
  source). `mac/GeminiMic.spec` is force-committed (a `*.spec` gitignore hid it).
- IN FLIGHT at /clear: a CI run (Android build.yml + Mac build-mac.yml) for the
  3-flash-preview swap was still building — on resume, `gh run list` the latest,
  download `debug-apk` + `GeminiMic-mac` if newer, and refresh the share zip.
- Blockers: none. OWNER TODO: test each platform (hold trigger → speak → text);
  decide free vs paid key (paid = fast/reliable, ~a few $/mo).

## Status — 2026-06-30
- ✅ Clean rebuild complete: 7 classes (MainActivity, MicOverlayService,
  VoiceInputAccessibilityService, GeminiClient, Prefs, GeminiMicApp, CrashActivity)
  + manifest + resources, faithful to the APK.
- ✅ GitHub Actions build **GREEN** → debug APK artifact.
  Repo: https://github.com/mirkomilovabrorwork-dot/gemini-mic (public)
- ✅ On-device: confirmed working (voice → typed text).
- ✅ Feature: transcript formatted into paragraphs — blank line ~every 2
  sentences, a long sentence (>=14 words) stands alone
  (`GeminiClient.formatParagraphs`, applied after `cleanTranscript`).
- ✅ Stable signing: committed `app/debug.keystore` (well-known debug key,
  password "android") so updates install in place without uninstall.
  Latest good run: 28479603726. APK pulled to `dist/app-debug.apk`.
- ✅ Windows edition (`windows/`): Python tray push-to-talk app — hold Right Ctrl
  → record → Gemini → paste into focused field. Same prompt/clean/format logic
  (verified 1:1 via `python gemini_mic.py --selftest`). Packaged to a standalone
  `windows/dist/GeminiMic.exe` (~33 MB) via PyInstaller. Source committed;
  exe/venv gitignored. Build locally: `windows/build.bat`.
- ⏳ NEXT: user runs GeminiMic.exe, sets API key in Settings, tests hold-to-talk
  end-to-end on real mic; then next feature.

## Windows build (local)
- `windows/.venv` has deps; rebuild exe:
  `.venv\Scripts\python -m PyInstaller --onefile --noconsole --name GeminiMic --icon icon.ico --collect-all sounddevice --hidden-import pystray._win32 --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 --noconfirm gemini_mic.py`
- Default hotkey `right ctrl` (changeable in Settings). Config: `%APPDATA%\GeminiMic\config.json`.

## Build / verify
- No local JDK/SDK. Build is cloud-only via GitHub Actions (`.github/workflows/build.yml`):
  `gradle assembleDebug` on Gradle 8.7 + AGP 8.5.2 + Java 17. Push to `main` → APK artifact.
- To get a fresh APK: `gh run download <runId> -n debug-apk -D dist`.

## Notes / gotchas hit
- AAPT rejects raw-hex flag values in `accessibility_service_config.xml` → use named flags.
- `javac` rejects UTF-8 BOM → keep `.java` files BOM-free.
