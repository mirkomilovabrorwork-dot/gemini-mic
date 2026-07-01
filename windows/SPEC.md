# Gemini Mic — Windows edition spec

A tray app: **hold a hotkey → record mic → Gemini transcribes → paste into the
focused field.** Behaviour and Gemini logic must match the Android app 1:1.
Language: **Python** (this machine has it), packaged to a **standalone .exe** (PyInstaller).

## UX
- Runs in the system tray (icon = blue mic circle). No main window.
- **Push-to-talk:** hold the hotkey (default `right ctrl`) → recording starts;
  release → stop + transcribe + paste. Tooltip/icon reflect state:
  blue = idle/ready, red = recording, green = transcribing.
- Tray menu: **Settings…**, **Start with Windows** (toggle), **Quit**.
- First run (or empty API key) → open Settings automatically.
- Feedback via tray tooltip + `tray.notify(...)` (short balloon) for errors and
  the guard messages below.

## Config  (`%APPDATA%\GeminiMic\config.json`)
```json
{ "api_key": "", "model": "gemini-2.5-flash", "language_mode": "uz_en_ru", "hotkey": "right ctrl" }
```
- Models: better `gemini-2.5-flash`, cheap `gemini-2.5-flash-lite`.
- Language modes: `uz_en`, `uz_ru`, `uz_en_ru`.
- Settings dialog (Tkinter): API key entry (masked), model radio (Better mixed / Fast cheap),
  language radio (Uzbek+English / Uzbek+Russian / Uzbek+English+Russian), Save button.

## Recording
- `sounddevice` InputStream, **16000 Hz, mono, int16**, buffer to memory.
- On release: build a **WAV** (stdlib `wave`) in a temp file (or bytes).
- Guards (match Android): min duration **0.65 s** (else tooltip "Hold longer"),
  auto-stop at **60 s**, silence check — peak abs sample < **500** → skip
  (tooltip "Ovoz eshitilmadi"). Delete temp audio after.

## Gemini call (MUST match Android GeminiClient exactly)
- Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}`
- Body: `{"contents":[{"parts":[{"text": <prompt>}, {"inline_data": {"mime_type":"audio/wav","data": <base64 no-wrap of the WAV bytes>}}]}], "generationConfig":{"temperature":0,"maxOutputTokens":1024,"thinkingConfig":{"thinkingBudget":0}}}`
- Timeout: connect 15s, read 45s. Non-2xx → raise with `"Gemini error {code}: {body}"`.
- Extract: `candidates[0].content.parts[*].text` joined.
- Max audio 20 MB (else error "Audio is too long").

### Prompt (verbatim)
`transcriptionPrompt` = `"Transcribe this audio for direct typing. " + languageInstruction + "\n\nRules:\n"` then these exact lines:
```
- Write only the words that were actually spoken. Do not invent, replace, translate, or paraphrase words.
- Do not add timestamps, numbers, bullets, speaker labels, headings, explanations, quotes, markdown, or formatting.
- Do not summarize, rewrite, or turn speech into a task list.
- Uzbek words must be written in natural Uzbek Latin.
- Keep English words exactly in English/Latin when they were spoken.
- Keep Russian words exactly in Cyrillic when they were spoken.
- Do not convert English or Russian words into Uzbek. Do not convert Uzbek words into English or Russian.
- Preserve mixed-language word order as spoken.
- Remove only filler sounds like umm, aa, eee and obvious repeated stutters when they do not change the meaning.
- If a word is impossible to identify, write [noaniq].
- Return only the final plain transcript text.
```
`languageInstruction`:
- `uz_en` → "The speaker usually mixes Uzbek and English. Preserve both languages exactly as spoken."
- `uz_ru` → "The speaker usually mixes Uzbek and Russian. Preserve both languages exactly as spoken."
- else   → "The speaker may mix Uzbek, English, and Russian in the same sentence. Preserve each language exactly as spoken."

### cleanTranscript (port of the Android method, verbatim behaviour)
Trim; remove ```` ``` ```` and `**`; strip a leading `[HH:MM(:SS)]` timestamp (line-start and inline); strip a leading `N.`/`N)` list marker per line; strip leading known prefixes (case-insensitive) `transcript:`, `transcription:`, `text:`, `the transcript is:`, `here is the transcript:`, `boshqa ovoz:`; if the whole string is wrapped in matching `"`/`'` quotes, drop them; trim.

### formatParagraphs (port exactly from GeminiClient.formatParagraphs)
Collapse whitespace to single spaces; split into sentences on whitespace **following** a terminator `[.!?…]` (so `3.5` is not split); if ≤1 sentence return as-is; else group: blank line (`\n\n`) after every **2** sentences, and a sentence with **≥14 words** stands alone as its own paragraph. Apply AFTER cleanTranscript.

## Typing into the focused field
- Use **clipboard paste** (reliable for Uzbek Latin + Cyrillic):
  save current clipboard → set clipboard to transcript → send **Ctrl+V** → sleep ~0.15s → restore clipboard.
- Do not simulate per-char typing (drops unicode in some apps).

## Packaging
- `requirements.txt`: sounddevice, numpy, requests, pynput, pystray, pillow, pyperclip.
- Build: `pyinstaller --onefile --noconsole --name "GeminiMic" --icon <ico> gemini_mic.py` (bundle the tray icon).
- Output `windows/dist/GeminiMic.exe` — double-click to run; add to Startup for "Start with Windows".

## Files to create (under `windows/`)
- `gemini_mic.py` (single-file app), `requirements.txt`, `build.bat` (venv + pip + pyinstaller), `README.md`, `icon.ico` (blue mic — can be generated from the Android `ic_mic_launcher` shape or a simple Pillow-drawn circle+mic).

## Success criteria
1. `python gemini_mic.py` launches a tray icon, no crash.
2. Settings dialog saves/loads config.
3. `format_paragraphs` + `clean_transcript` produce identical output to the Java versions on test strings.
4. Hold hotkey records; release transcribes (real Gemini) and pastes text into the focused field.
5. `GeminiMic.exe` built and launches the same way.
