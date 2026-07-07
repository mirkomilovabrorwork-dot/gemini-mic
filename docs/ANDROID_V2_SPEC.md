# Android v2 — volume-key trigger + modern redesign + remove "cheap"

Two changes to the existing Android app (keep all working behaviour otherwise:
recording→Gemini→auto-type via accessibility, model 3.5-flash + fallback, paragraph
formatting, floating bubble). Both must land together (blast-radius aware).

## A. Volume-DOWN hold-to-record (the "hotkey")
Goal (owner's exact words): a SHORT press of Volume-Down still lowers the volume
normally; HOLDING Volume-Down starts recording IMMEDIATELY (no missed start —
recording must begin on key-DOWN, not after a hold-timer); releasing stops +
transcribes.

Implementation:
1. `res/xml/accessibility_service_config.xml`: add `android:canRequestFilterKeyEvents="true"`
   and add the `flagRequestFilterKeyEvents` bit (0x20) to `accessibilityFlags`
   (current is `flagReportViewIds|flagRetrieveInteractiveWindows` → add
   `|flagRequestFilterKeyEvents`).
2. `MicOverlayService`: expose a static bridge (like VoiceInputAccessibilityService.instance):
   - `static boolean isRunning()` → instance != null
   - `static void volumeStart()` → post to main: start recording NOW, unconditionally
     (bypass the bubble's hasActiveTextInput gate — the user deliberately held the key).
     Reuse the existing startRecording() path (sets red bubble, MediaRecorder, etc.).
   - `static void volumeStop()` → post to main: stopAndTranscribe()
   - `static void volumeCancel()` → post to main: stop + DISCARD the audio (delete temp,
     no transcription), reset to idle. (Add a cancel that mirrors stopRecordingQuietly + delete file.)
   Keep a static `instance` set in onCreate/onDestroy.
3. `VoiceInputAccessibilityService`: override `onKeyEvent(KeyEvent)`:
   - Only act on `KeyEvent.KEYCODE_VOLUME_DOWN`; for anything else return `super`/false.
   - If `!MicOverlayService.isRunning()` → return false (app not active → let the system
     handle volume normally; NEVER hijack volume when the mic service is off).
   - ACTION_DOWN:
       - if `event.getRepeatCount() == 0`: record `volDownAt = SystemClock.uptimeMillis()`;
         `MicOverlayService.volumeStart()` (start recording immediately).
       - return true (consume every down, incl. repeats, so volume doesn't change while held).
   - ACTION_UP:
       - `held = uptimeMillis() - volDownAt`
       - if `held < 250` (a tap): `MicOverlayService.volumeCancel()` AND perform one real
         volume-down: `((AudioManager)getSystemService(AUDIO_SERVICE)).adjustSuggestedStreamVolume(
         AudioManager.ADJUST_LOWER, AudioManager.USE_DEFAULT_STREAM_TYPE, AudioManager.FLAG_SHOW_UI)`.
       - else (a hold): `MicOverlayService.volumeStop()` (transcribe).
       - return true.
   - Guard against a missing DOWN (e.g. app started mid-press): if ACTION_UP arrives with
     no recorded volDownAt, return false.
   Notes: starting a MediaRecorder on a tap then cancelling is acceptable overhead (owner
   prioritised zero missed-start over tap efficiency). Volume-UP is never touched.
4. Blast radius: the bubble's own hold-to-record must still work (don't break the touch
   listener). Volume trigger and bubble are independent paths into the same
   start/stop methods; guard with the existing `busy`/`recording` flags so they can't
   double-fire.
5. Update the in-app guide text to mention: "Ovoz-pastga tugmasini bosib turib gapiring
   (qo'ysangiz yoziladi). Qisqa bossangiz — oddiy ovoz pasayadi."

## B. Modern redesign of MainActivity (programmatic UI, no XML)
Direction: clean, glance-clear, "understand in one go", light + dark aware, ONE accent
(brand blue #2563EB), one primary action. Keep it programmatic (match current approach).

- **Remove entirely**: the "Quality / cost" section, the "Better mixed language" and
  "Fast cheap" buttons, and any model-selection UI. The app always uses 3.5-flash +
  fallback (no user model choice). (Prefs.model default stays gemini-3.5-flash.)
- **Light/dark**: detect via `getResources().getConfiguration().uiMode & UI_MODE_NIGHT_MASK`.
  Define two palettes (bg, card, ink, muted, accent, success-green, danger-red) and pick.
- **Layout** (single scroll, card-based, generous spacing ~16–20dp, rounded 16dp cards via
  GradientDrawable):
  1. Header: "Gemini Mic" (bold ~26sp) + one-line subtitle.
  2. **API key card**: masked EditText + "Saqlash" primary-styled button. Show a small
     green ✓ "saqlangan" when a key exists.
  3. **Setup checklist card** — a live status list, each row = icon + label + state:
     · Mikrofon (ruxsat) · Ustidan chizish (floating) · Avto-kiritish (accessibility).
     Each row: green ✓ when granted, or a tappable "Ruxsat ber" chip when not. Compute
     state in onResume (reuse hasAudioPermission / canDrawOverlays / isAccessibilityEnabled).
  4. **Language card**: 3 choices (Uz+En+Ru / Uz+En / Uz+Ru) as a simple segmented/radio
     row; tick the active one. (reuse setLanguageMode.)
  5. **Primary action**: one big accent button — "Mikrofonni yoqish" (startMicService) when
     ready; turns into "To'xtatish" when the service is running. (Track running via
     MicOverlayService.isRunning().)
  6. **How-to card** (collapsed/short): 3–4 lines — volume-hold trigger + floating mic +
     colors (blue=ready, red=recording, green=working).
  - Buttons: rounded (GradientDrawable), accent bg + white text for primary; subtle
    outline for secondary; min height ~48dp; setAllCaps(false); 15–16sp.
  - Status/next-step text stays but restyled (muted, small) — keep refreshStatusSafely logic.
- Keep ALL existing method logic (permissions, startMicService, testGemini optional — you
  may drop the separate "Test Gemini" button since the checklist + Save cover it; if you
  drop it, also remove now-unused methods to avoid orphans). Keep `Prefs`, service intents,
  string keys unchanged.

## Verify
- Builds green on CI (assembleDebug). No orphaned methods/imports.
- Manifest/accessibility config still valid (AAPT: named flags only).
- Bubble hold-to-record still works; volume-hold records; short volume tap lowers volume.
