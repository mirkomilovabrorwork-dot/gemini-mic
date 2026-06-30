# Gemini Mic

A floating microphone overlay for Android that uses the Gemini API to transcribe voice and auto-type into any focused text field.

## Build

Built on GitHub Actions. No local toolchain required. Push to trigger CI.

## Permissions required

- INTERNET — Gemini API calls
- RECORD_AUDIO — microphone
- SYSTEM_ALERT_WINDOW — floating bubble overlay
- FOREGROUND_SERVICE / FOREGROUND_SERVICE_MICROPHONE — persistent mic service
- POST_NOTIFICATIONS — foreground notification

## Usage

1. Open the app and paste your Gemini API key, then tap Save.
2. Tap "Allow microphone" and grant the permission.
3. Tap "Allow floating mic" and enable overlay for this app.
4. Tap "Enable auto input" and enable the Gemini Mic accessibility service.
5. Tap "Start microphone bubble" — a small blue dot appears at the screen edge.
6. Focus a text field in any app, then tap the bubble to expand it.
7. Hold the expanded mic button and speak; release to transcribe and auto-type.
