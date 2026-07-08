# Gemini Mic

A system-wide voice keyboard for Android that uses the Gemini API to transcribe voice (mixed Uzbek / English / Russian) and auto-type it into any focused text field. Hold the Volume-Down key, speak, release.

## Build

Built on GitHub Actions. No local toolchain required. Push to trigger CI.

## Permissions required

- INTERNET — Gemini API calls
- RECORD_AUDIO — microphone
- FOREGROUND_SERVICE / FOREGROUND_SERVICE_MICROPHONE — persistent mic service
- POST_NOTIFICATIONS — foreground + "tap to arm" notifications

## Usage

1. Open the app and paste your Gemini API key, then tap Save.
2. Tap "Allow microphone" and grant the permission.
3. Tap "Enable auto input" and enable the Gemini Mic accessibility service.
4. Tap "Mikrofonni yoqish" to start the service.
5. In any app, focus a text field, then HOLD the Volume-Down key and speak; release to transcribe and auto-type. (A short press still lowers the volume normally.)
6. After a phone reboot, tap the "Gemini Mic — Yoqish uchun bosing" notification once to re-arm.
