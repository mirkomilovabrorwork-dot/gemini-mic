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
  Latest good run: 28465174788. Built APK pulled to `dist/app-debug.apk`.
- ⏳ NEXT: on-device test — install APK, paste Gemini API key, grant
  mic + overlay + accessibility, start bubble, confirm voice→text works.

## Build / verify
- No local JDK/SDK. Build is cloud-only via GitHub Actions (`.github/workflows/build.yml`):
  `gradle assembleDebug` on Gradle 8.7 + AGP 8.5.2 + Java 17. Push to `main` → APK artifact.
- To get a fresh APK: `gh run download <runId> -n debug-apk -D dist`.

## Notes / gotchas hit
- AAPT rejects raw-hex flag values in `accessibility_service_config.xml` → use named flags.
- `javac` rejects UTF-8 BOM → keep `.java` files BOM-free.
