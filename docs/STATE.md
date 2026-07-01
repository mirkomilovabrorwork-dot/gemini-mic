# Gemini Mic — STATE

_Trigger word: "gemini mic". Source of truth for resume._

## What this is
System-wide voice keyboard for Android: hold a floating mic → record → Gemini
transcribes (mixed Uzbek/English/Russian) → text is auto-typed into the focused
field via an accessibility service. Pure Android SDK (Java), no third-party deps.
Package `com.autosmart.geminimic` (debug suffix `.debug`).

## Origin
Original Codex-built project source was lost (not on D:/C:/GitHub). Reconstructed
1:1 by decompiling `GeminiMic-Simple-Android-debug.apk` (androguard) into a clean
Java Gradle project. Decompiled reference + spec live in `D:\vibecoding\geminimic-recovered\`.

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
