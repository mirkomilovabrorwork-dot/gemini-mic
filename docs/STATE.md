# Gemini Mic — STATE

_Trigger words: "gemini", "gemini mic". Source of truth for resume._

## What this is
System-wide voice keyboard for Android: hold a floating mic → record → Gemini
transcribes (mixed Uzbek/English/Russian) → text is auto-typed into the focused
field via an accessibility service. Pure Android SDK (Java), no third-party deps.
Package `com.autosmart.geminimic` (debug suffix `.debug`).

## Origin
Original Codex-built project source was lost (not on D:/C:/GitHub). Reconstructed
1:1 by decompiling `GeminiMic-Simple-Android-debug.apk` (androguard) into a clean
Java Gradle project. Decompiled reference + spec live in `D:\vibecoding\geminimic-recovered\`.

## GOAL (owner's words)
Voice typing that "just works" on BOTH phone and PC: hold a key/mic, speak
mixed Uzbek/English/Russian, the text lands in the focused field — free
(Gemini free tier), no fiddling. Owner shares it with a friend as a zip.

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
