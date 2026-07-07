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

## STATUS (resume board) — 2026-07-07
- MODEL (final): primary **gemini-3.5-flash**, fallback **gemini-3-flash-preview**
  on retryable errors (HTTP 404/429/500/503). Both are Gemini-3 flash, both
  FREE-tier, and DIFFERENT models → separate rate limits, so a 429 on the
  primary is absorbed instantly (429 returns immediately, no long wait).
  Live-verified with real TTS audio: BOTH transcribe the test phrase exactly
  (3.5 does NOT hallucinate). `gemini-3.0-flash` / `-preview` do NOT exist (404);
  `gemini-3-flash-preview` and `gemini-3.5-flash` are the real ids on the key.
  Fallback mechanism: Android GeminiClient.postGenerateContent(model)+isRetryable;
  Windows/Mac `_call_gemini` sets `.status`, `gemini_transcribe` retries once.
- BILLING (verified on official pricing page): free tier works WITHOUT billing —
  both flash models free but rate-limited (~15 RPM). Enabling billing = paid
  immediately, NO free allowance (3.5-flash ~$1.50/$9 per 1M tok). → owner should
  use a NO-BILLING key. Free-tier caveat: Google may use the content for training.
- Windows: hardened (tolerant hotkey parse, beep on start/done, guard msgs →
  tray tooltip, single-instance mutex + startup beep/balloon since Win11 hides
  tray icons under ^). Fresh Desktop\GeminiMic.exe running; live config = 3.5.
- Android: CI green (run 28894991469), fresh APK on Desktop + dist/. Stable
  keystore → installs in place (no uninstall).
- macOS: rumps menu-bar app in `mac/`; cloud-built via `.github/workflows/build-mac.yml`
  (macos-13 Intel → runs on all Macs). Artifact `GeminiMic-mac` (zip of the .app).
  NOT yet delivered to the owner/friend or first-run-tested on a real Mac.
- NEXT: (1) owner tests Windows + Android end-to-end; (2) grab the macOS build
  artifact from the latest build-mac run + write the 1-page permission guide;
  (3) refresh `Desktop\GeminiMic-share.zip` (currently OLD binaries) before the
  friend hand-off.
- Blockers: none. OWNER TODO: install the new APK on the phone; test Windows
  (hold Right Ctrl → beep → speak → release → text); use a NO-BILLING key.

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
