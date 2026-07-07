# Gemini Mic — macOS edition spec

A menu-bar app: **hold a hotkey → record mic → Gemini transcribes → paste into the
focused field.** Behaviour + Gemini logic identical to the Windows/Android apps.
Language: **Python (rumps menu-bar)**, packaged to a **`.app`** on a macOS
GitHub Actions runner (we have no Mac to build/test locally — cloud build only).

## Reuse the proven core VERBATIM
Copy these from `windows/gemini_mic.py` UNCHANGED (same strings/logic, they are
already verified):
- `DEFAULT_CONFIG`, `MODEL_CHOICES`, `FALLBACK_MODEL`, `FALLBACK_STATUSES`
- `language_instruction`, `transcription_prompt`, `_TRANSCRIPT_RULES`
- `clean_transcript`, `format_paragraphs`
- `_call_gemini` (sets `.status` on HTTP error), `gemini_transcribe` (primary
  model → on GeminiError.status in FALLBACK_STATUSES retry once with FALLBACK_MODEL)
- config load/save — but path = `~/Library/Application Support/GeminiMic/config.json`
Primary model `gemini-3.5-flash`, fallback `gemini-2.5-flash`.

## macOS shell (new)
- **Menu-bar app via `rumps`.** Title shows state with an emoji:
  idle `🎙️` · recording `🔴` · transcribing `⏳`.
- Menu items:
  - a disabled status line (e.g. "Tayyor" / "Yozilmoqda…" / "Yozyapti…")
  - **"API key kiritish…"** → `rumps.Window` (default text = current key) to paste + Save
  - **"Til"** submenu: Uzbek+English+Russian / Uzbek+English / Uzbek+Russian (radio-style; tick the active one)
  - **"Hotkey: o'ng Ctrl"** disabled info line (changing it = edit config.json; document it)
  - **Quit** (rumps default)
- On launch, if no API key → open the API-key window automatically + a
  `rumps.notification("Gemini Mic", "Sozlash", "API key kiriting…")`.

## Hotkey + recording
- **Push-to-talk** via `pynput.keyboard.Listener`: default key `Key.ctrl_r`
  (right Ctrl). Key-down → start; key-up → stop+transcribe. Ignore auto-repeat.
  Run start/stop OFF the listener thread (threads) so a slow mic init can't
  block key delivery.
- Record with `sounddevice` InputStream 16000 Hz mono int16 → stdlib `wave` → WAV bytes.
- Guards (same as other platforms): min 0.65 s ("Hold longer" → menu status, no popup),
  auto-stop 60 s, silence peak < 500 ("Ovoz eshitilmadi" → menu status). Send WAV as
  `audio/wav` in `gemini_transcribe`.
- Audio feedback: a short system sound on record-start and on done, e.g.
  `subprocess.Popen(["afplay", "/System/Library/Sounds/Pop.aiff"])` (start) and
  `.../Tink.aiff` (done) — never block the UI (Popen, don't wait).

## Paste into the focused field
- Set clipboard with `pyperclip.copy(text)` (pbcopy under the hood), then send
  **Cmd+V** via pynput: `press(Key.cmd); press('v'); release('v'); release(Key.cmd)`;
  sleep ~0.15; restore the previous clipboard. (Reliable for Uzbek Latin + Cyrillic.)

## Files to create under `mac/`
1. `gemini_mic_mac.py` — the full app (core copied verbatim + rumps/pynput/sounddevice shell).
2. `requirements.txt` — rumps, pynput, sounddevice, numpy, requests, pyperclip.
3. `GeminiMic.spec` — PyInstaller spec that builds a windowed `.app` with a proper
   Info.plist. The BUNDLE(info_plist=...) MUST include:
   - `NSMicrophoneUsageDescription` = "Gemini Mic ovozingizni matnga aylantirish uchun mikrofondan foydalanadi." (WITHOUT this, macOS silently denies the mic and recording fails)
   - `LSUIElement` = True (menu-bar only, no Dock icon)
   - `CFBundleName` = "Gemini Mic", bundle id `com.autosmart.geminimic`
   Use `--windowed`, name "Gemini Mic". No console.
4. `--selftest` flag: run clean_transcript/format_paragraphs on 2 samples and exit
   BEFORE importing rumps/sounddevice/pynput (so parity is checkable on any OS).
5. `README.md` — plain, short.

## What it CANNOT remove (be honest in the guide)
macOS forces the user to grant, in System Settings → Privacy & Security:
**Microphone**, **Accessibility**, and **Input Monitoring** for "Gemini Mic".
And first launch of an unsigned app: right-click the .app → **Open** (Gatekeeper).
The 1-page guide must show these 4 steps with where to click.

## Success criteria
1. `python gemini_mic_mac.py --selftest` prints identical clean/format output to the Windows selftest.
2. On the macOS runner, PyInstaller builds `dist/Gemini Mic.app` with the mic-usage Info.plist key present.
3. The .app is zipped (ditto) and uploaded as an artifact.
4. (Owner's friend, first run) grants the 3 permissions + right-click-Open, then hold-to-talk types text.
