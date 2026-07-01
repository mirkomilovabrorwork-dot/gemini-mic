# Gemini Mic — Windows

A system-tray push-to-talk voice-to-text app. Hold a hotkey, speak, release —
Gemini transcribes the audio and pastes the result into whatever text field is
focused. Transcription logic (prompt, cleanup, paragraph formatting) matches
the Android Gemini Mic app 1:1.

## Run from source

```
pip install -r requirements.txt
python gemini_mic.py
```

On first run (or if no API key is saved yet) the Settings window opens
automatically — paste your Gemini API key, pick a model and language mode,
and click Save.

## Default hotkey

**Right Ctrl**, push-to-talk:
- Press and hold → recording starts (icon turns red).
- Release → recording stops, audio is sent to Gemini (icon turns green while
  transcribing), and the transcript is pasted into the focused field via
  clipboard + Ctrl+V (your previous clipboard contents are restored
  afterwards).

Change the hotkey any time from **tray icon → Settings…** (e.g. `f9`,
`left alt`, a single letter/digit key).

## Tray icon

- Blue = idle / ready
- Red = recording
- Green = transcribing

Tray menu: **Settings…**, **Start with Windows** (adds/removes a registry
Run-key entry so the app launches at login), **Quit**.

## Settings

Stored at `%APPDATA%\GeminiMic\config.json`:

```json
{ "api_key": "", "model": "gemini-2.5-flash", "language_mode": "uz_en_ru", "hotkey": "right ctrl" }
```

- **Model**: Better mixed (`gemini-2.5-flash`) or Fast cheap
  (`gemini-2.5-flash-lite`).
- **Language mode**: Uzbek+English, Uzbek+Russian, or Uzbek+English+Russian —
  controls the language instruction sent to Gemini.

## Recording guards

- Minimum hold: 0.65s (shorter → tooltip "Hold longer", nothing sent).
- Auto-stop at 60s if you hold the hotkey that long.
- Silence check: if the loudest sample in the clip is below amplitude 500
  (out of ±32767 for 16-bit audio), it's treated as silence → tooltip "Ovoz
  eshitilmadi", nothing sent to Gemini.

## Self-test (no mic / no API key needed)

Checks that `clean_transcript` and `format_paragraphs` behave like the
Android `GeminiClient.java` versions:

```
python gemini_mic.py --selftest
```

## Building the .exe

```
build.bat
```

This creates a `venv`, installs `requirements.txt` + PyInstaller, generates
`icon.ico`, and runs:

```
pyinstaller --onefile --noconsole --name GeminiMic --icon icon.ico gemini_mic.py
```

Output: `dist\GeminiMic.exe`. Double-click to run; use the tray menu's
**Start with Windows** to launch it automatically at login.
