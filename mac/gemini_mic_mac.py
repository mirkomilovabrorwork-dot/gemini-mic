"""Gemini Mic — macOS menu-bar voice-to-text app.

Hold a hotkey -> record mic -> Gemini transcribes -> paste into the focused
field. Gemini core logic is copied verbatim from windows/gemini_mic.py
(same strings/logic; only the config path differs).

Run:      python gemini_mic_mac.py
Self-test: python gemini_mic_mac.py --selftest
"""

import base64
import json
import os
import re
import subprocess
import sys
import threading
import time
import wave
from io import BytesIO

# ---------------------------------------------------------------------------
# Paths / config
# ---------------------------------------------------------------------------

APP_NAME = "GeminiMic"
CONFIG_DIR = os.path.join(
    os.path.expanduser("~"), "Library", "Application Support", "GeminiMic"
)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "api_key": "",
    "model": "gemini-3.5-flash",
    "language_mode": "uz_en_ru",
    "hotkey": "right ctrl",
}

MODEL_CHOICES = [
    ("Better mixed (gemini-3.5-flash)", "gemini-3.5-flash"),
    ("Fast cheap (gemini-2.5-flash-lite)", "gemini-2.5-flash-lite"),
]

# Primary is gemini-3.5-flash; on error (busy/quota/not available) retry once
# with a DIFFERENT model (separate quota) so a 429 rarely reaches the user.
FALLBACK_MODEL = "gemini-3-flash-preview"
FALLBACK_STATUSES = (404, 429, 500, 503)

LANGUAGE_CHOICES = [
    ("Uzbek + English", "uz_en"),
    ("Uzbek + Russian", "uz_ru"),
    ("Uzbek + English + Russian", "uz_en_ru"),
]

# Recording guards (match Android/Windows)
SAMPLE_RATE = 16000
MIN_DURATION_SEC = 0.65
AUTO_STOP_SEC = 60
SILENCE_PEAK_THRESHOLD = 500  # abs int16 sample amplitude
MAX_AUDIO_BYTES = 20 * 1024 * 1024

GEMINI_CONNECT_TIMEOUT = 15
GEMINI_READ_TIMEOUT = 45


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG})
    except (FileNotFoundError, ValueError, OSError):
        pass
    return cfg


def save_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, CONFIG_PATH)


# ---------------------------------------------------------------------------
# Gemini prompt (verbatim port of GeminiClient.java)
# ---------------------------------------------------------------------------

_TRANSCRIPT_RULES = (
    "- Write only the words that were actually spoken. Do not invent, replace, translate, or paraphrase words.\n"
    "- Do not add timestamps, numbers, bullets, speaker labels, headings, explanations, quotes, markdown, or formatting.\n"
    "- Do not summarize, rewrite, or turn speech into a task list.\n"
    "- Uzbek words must be written in natural Uzbek Latin.\n"
    "- Keep English words exactly in English/Latin when they were spoken.\n"
    "- Keep Russian words exactly in Cyrillic when they were spoken.\n"
    "- Do not convert English or Russian words into Uzbek. Do not convert Uzbek words into English or Russian.\n"
    "- Preserve mixed-language word order as spoken.\n"
    "- Remove only filler sounds like umm, aa, eee and obvious repeated stutters when they do not change the meaning.\n"
    "- If a word is impossible to identify, write [noaniq].\n"
    "- Return only the final plain transcript text."
)


def language_instruction(language_mode):
    if language_mode == "uz_en":
        return "The speaker usually mixes Uzbek and English. Preserve both languages exactly as spoken."
    elif language_mode == "uz_ru":
        return "The speaker usually mixes Uzbek and Russian. Preserve both languages exactly as spoken."
    else:
        return "The speaker may mix Uzbek, English, and Russian in the same sentence. Preserve each language exactly as spoken."


def transcription_prompt(language_mode):
    return (
        "Transcribe this audio for direct typing. "
        + language_instruction(language_mode)
        + "\n\nRules:\n"
        + _TRANSCRIPT_RULES
    )


# ---------------------------------------------------------------------------
# cleanTranscript — verbatim port of GeminiClient.cleanTranscript
# ---------------------------------------------------------------------------

_TIMESTAMP_LINE_START_RE = re.compile(r"^\s*\[\d{1,2}:\d{2}(?::\d{2})?\]\s*", re.MULTILINE)
_TIMESTAMP_INLINE_RE = re.compile(r"\[\d{1,2}:\d{2}(?::\d{2})?\]\s*")
_LIST_MARKER_RE = re.compile(r"^\s*\d+[.)]\s+", re.MULTILINE)

_PREFIXES = [
    "transcript:",
    "transcription:",
    "text:",
    "the transcript is:",
    "here is the transcript:",
    "boshqa ovoz:",
]


def clean_transcript(text):
    if text is None:
        return ""
    s = text.strip()
    s = s.replace("```", "").strip()
    s = s.replace("**", "").strip()
    s = _TIMESTAMP_LINE_START_RE.sub("", s)
    s = _TIMESTAMP_INLINE_RE.sub("", s)
    s = _LIST_MARKER_RE.sub("", s)
    s = s.strip()

    lower = s.lower()
    for prefix in _PREFIXES:
        if lower.startswith(prefix):
            s = s[len(prefix):].strip()
            lower = s.lower()

    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()

    return s


# ---------------------------------------------------------------------------
# formatParagraphs — verbatim port of GeminiClient.formatParagraphs
# ---------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"\s+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+")


def format_paragraphs(raw):
    if raw is None:
        return ""
    flat = _WHITESPACE_RE.sub(" ", raw.strip())
    if not flat:
        return ""

    sentences = _SENTENCE_SPLIT_RE.split(flat)
    if len(sentences) <= 1:
        return flat

    out = []
    in_group = 0
    n = len(sentences)
    for i, raw_s in enumerate(sentences):
        s = raw_s.strip()
        if not s:
            continue
        big = len(s.split()) >= 14
        if in_group > 0 and (big or in_group >= 2):
            out.append("\n\n")
            in_group = 0
        if in_group > 0:
            out.append(" ")
        out.append(s)
        in_group += 1
        if big and i < n - 1:
            out.append("\n\n")
            in_group = 0

    return "".join(out).strip()


# ---------------------------------------------------------------------------
# Self-test entry point (no other deps needed) — MUST run before any
# rumps/sounddevice/pynput import so parity is checkable on any OS.
# ---------------------------------------------------------------------------

def _run_selftest():
    samples = [
        '```Transcript: "Salom, bugun men ofisga bordim va u yerda juda ko\'p ishlar bor edi."```',
        "[00:01] 1. Hello world. This is a test sentence with more than fourteen words in it to check the long sentence rule works well. Short one. Another short one here too. Va yana bitta.",
        "  **the transcript is:** Bu juda oddiy gap.   Va yana bittasi bor.  ",
        "boshqa ovoz: 'Mening ismim Aziz.'",
    ]
    for i, sample in enumerate(samples, 1):
        cleaned = clean_transcript(sample)
        formatted = format_paragraphs(cleaned)
        print(f"--- sample {i} ---")
        print("input   :", repr(sample))
        print("cleaned :", repr(cleaned))
        print("formatted:")
        print(formatted)
        print()


if __name__ == "__main__" and "--selftest" in sys.argv:
    _run_selftest()
    sys.exit(0)


# ---------------------------------------------------------------------------
# Heavier imports (only needed for the actual menu-bar app, not --selftest)
# ---------------------------------------------------------------------------

import numpy as np
import requests
import sounddevice as sd
import pyperclip
import rumps
from pynput import keyboard
from pynput.keyboard import Key, Controller as KeyboardController


def play_sound(path):
    """Short non-blocking system sound for audio feedback (record start / done)."""
    try:
        subprocess.Popen(
            ["afplay", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


SOUND_START = "/System/Library/Sounds/Pop.aiff"
SOUND_DONE = "/System/Library/Sounds/Tink.aiff"


# ---------------------------------------------------------------------------
# WAV helper
# ---------------------------------------------------------------------------

def frames_to_wav_bytes(frames, sample_rate=SAMPLE_RATE):
    """frames: list of numpy int16 arrays (mono). Returns WAV bytes."""
    if frames:
        audio = np.concatenate(frames)
    else:
        audio = np.array([], dtype=np.int16)
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())
    return buf.getvalue(), audio


# ---------------------------------------------------------------------------
# Gemini transcription call
# ---------------------------------------------------------------------------

class GeminiError(Exception):
    pass


def _call_gemini(api_key, model, body):
    """POST to the Gemini generateContent endpoint for `model` and return the
    joined text of the first candidate's parts."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    try:
        resp = requests.post(
            url,
            json=body,
            timeout=(GEMINI_CONNECT_TIMEOUT, GEMINI_READ_TIMEOUT),
        )
    except requests.RequestException as e:
        raise GeminiError(f"Network error: {e}")

    if resp.status_code < 200 or resp.status_code >= 300:
        err = GeminiError(f"Gemini error {resp.status_code}: {resp.text}")
        err.status = resp.status_code
        raise err

    try:
        data = resp.json()
    except ValueError:
        raise GeminiError("Gemini returned invalid JSON")

    candidates = data.get("candidates") or []
    if not candidates:
        raise GeminiError("No transcript returned")

    try:
        parts = candidates[0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        raise GeminiError("No transcript returned")

    return "".join(p.get("text", "") for p in parts)


def gemini_transcribe(api_key, model, language_mode, wav_bytes):
    if not api_key:
        raise GeminiError("Missing Gemini API key")
    if len(wav_bytes) == 0:
        raise GeminiError("No audio recorded")
    if len(wav_bytes) > MAX_AUDIO_BYTES:
        raise GeminiError("Audio is too long")

    body = {
        "contents": [
            {
                "parts": [
                    {"text": transcription_prompt(language_mode)},
                    {
                        "inline_data": {
                            "mime_type": "audio/wav",
                            "data": base64.b64encode(wav_bytes).decode("ascii"),
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 1024,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    try:
        text = _call_gemini(api_key, model, body)
    except GeminiError as e:
        if getattr(e, "status", None) in FALLBACK_STATUSES and model != FALLBACK_MODEL:
            text = _call_gemini(api_key, FALLBACK_MODEL, body)
        else:
            raise

    transcript = format_paragraphs(clean_transcript(text))
    if not transcript:
        raise GeminiError("Empty transcript")
    return transcript


# ---------------------------------------------------------------------------
# Hotkey parsing (pynput) — right Ctrl by default; edit config.json to change.
# ---------------------------------------------------------------------------

_NAMED_KEYS = {
    "right ctrl": Key.ctrl_r,
    "left ctrl": Key.ctrl_l,
    "ctrl": Key.ctrl_l,
    "right alt": Key.alt_r,
    "left alt": Key.alt_l,
    "alt": Key.alt_l,
    "right shift": Key.shift_r,
    "left shift": Key.shift_l,
    "shift": Key.shift_l,
    "caps lock": Key.caps_lock,
    "tab": Key.tab,
    "space": Key.space,
    "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
    "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
    "f9": Key.f9, "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
}


_HOTKEY_ALIASES = {
    "control": "ctrl",
    "ctrl left": "left ctrl", "ctrl right": "right ctrl",
    "left control": "left ctrl", "right control": "right ctrl",
    "control left": "left ctrl", "control right": "right ctrl",
    "alt left": "left alt", "alt right": "right alt",
    "shift left": "left shift", "shift right": "right shift",
    "lctrl": "left ctrl", "rctrl": "right ctrl",
    "lshift": "left shift", "rshift": "right shift",
    "lalt": "left alt", "ralt": "right alt",
}


def parse_hotkey(hotkey_str):
    """Returns a pynput Key or a single-character string to match against
    KeyCode.char (lowercased). Tolerant of word order / spelling variants."""
    s = " ".join((hotkey_str or "").strip().lower().replace("_", " ").split())
    s = _HOTKEY_ALIASES.get(s, s)
    if s in _NAMED_KEYS:
        return _NAMED_KEYS[s]
    if len(s) == 1:
        return s
    # fall back to default
    return Key.ctrl_r


def key_matches(pressed_key, target):
    if isinstance(target, str):
        char = getattr(pressed_key, "char", None)
        return char is not None and char.lower() == target
    return pressed_key == target


# ---------------------------------------------------------------------------
# Main application (rumps menu-bar app)
# ---------------------------------------------------------------------------

STATUS_READY = "Tayyor"
STATUS_RECORDING = "Yozilmoqda…"
STATUS_TRANSCRIBING = "Yozyapti…"

TITLE_IDLE = "🎙️"
TITLE_RECORDING = "🔴"
TITLE_TRANSCRIBING = "⏳"


class GeminiMicApp(rumps.App):
    def __init__(self):
        super().__init__(APP_NAME, title=TITLE_IDLE, quit_button=None)

        self.cfg = load_config()
        self.lock = threading.Lock()
        self.recording = False
        self.frames = []
        self.stream = None
        self.record_start = 0.0
        self.hotkey_target = parse_hotkey(self.cfg.get("hotkey", DEFAULT_CONFIG["hotkey"]))
        self.kb_controller = KeyboardController()
        self._listener = None

        self.status_item = rumps.MenuItem(STATUS_READY)
        self.status_item.set_callback(None)

        self.api_key_item = rumps.MenuItem("API key kiritish…", callback=self.on_api_key)

        self.lang_items = {}
        lang_menu = []
        for label, value in LANGUAGE_CHOICES:
            item = rumps.MenuItem(label, callback=self.on_language_select)
            self.lang_items[value] = item
            lang_menu.append(item)
        self._refresh_language_ticks()

        self.hotkey_info_item = rumps.MenuItem(
            f"Hotkey: {self.cfg.get('hotkey', DEFAULT_CONFIG['hotkey'])}"
        )
        self.hotkey_info_item.set_callback(None)

        self.menu = [
            self.status_item,
            None,
            self.api_key_item,
            {"Til": lang_menu},
            self.hotkey_info_item,
            None,
            rumps.MenuItem("Quit", callback=self.on_quit),
        ]

    # -- config -----------------------------------------------------------

    def get_config(self):
        with self.lock:
            return dict(self.cfg)

    def apply_config(self, new_cfg):
        with self.lock:
            self.cfg = dict(new_cfg)
            self.hotkey_target = parse_hotkey(self.cfg.get("hotkey", DEFAULT_CONFIG["hotkey"]))

    def _refresh_language_ticks(self):
        current = self.cfg.get("language_mode", DEFAULT_CONFIG["language_mode"])
        for value, item in self.lang_items.items():
            item.state = 1 if value == current else 0

    # -- menu callbacks -------------------------------------------------

    def on_api_key(self, _sender):
        cfg = self.get_config()
        window = rumps.Window(
            message="Gemini API key ni kiriting:",
            title="Gemini Mic — API key",
            default_text=cfg.get("api_key", ""),
            ok="Save",
            cancel="Cancel",
            dimensions=(320, 24),
        )
        response = window.run()
        if response.clicked:
            new_key = response.text.strip()
            cfg = self.get_config()
            cfg["api_key"] = new_key
            save_config(cfg)
            self.apply_config(cfg)
            rumps.notification("Gemini Mic", "Sozlash", "API key saqlandi.")

    def on_language_select(self, sender):
        value = None
        for v, item in self.lang_items.items():
            if item is sender:
                value = v
                break
        if value is None:
            return
        cfg = self.get_config()
        cfg["language_mode"] = value
        save_config(cfg)
        self.apply_config(cfg)
        self._refresh_language_ticks()

    def on_quit(self, _sender):
        with self.lock:
            self.recording = False
            stream = self.stream
            self.stream = None
        try:
            if stream is not None:
                stream.stop()
                stream.close()
        except Exception:
            pass
        if self._listener is not None:
            self._listener.stop()
        rumps.quit_application()

    # -- state / status ---------------------------------------------------

    def set_state(self, state):
        """state: 'idle' | 'recording' | 'transcribing'"""
        title, status = {
            "idle": (TITLE_IDLE, STATUS_READY),
            "recording": (TITLE_RECORDING, STATUS_RECORDING),
            "transcribing": (TITLE_TRANSCRIBING, STATUS_TRANSCRIBING),
        }.get(state, (TITLE_IDLE, STATUS_READY))
        self.title = title
        self.status_item.title = status

    def _set_status_text(self, text):
        """Quiet status via the menu line — no popup."""
        self.status_item.title = text

    def notify(self, message, title="Gemini Mic"):
        try:
            rumps.notification(title, "", message)
        except Exception:
            pass

    # -- recording ----------------------------------------------------------

    def _audio_callback(self, indata, frames_count, time_info, status):
        if self.recording:
            self.frames.append(indata[:, 0].copy())

    def start_recording(self):
        with self.lock:
            if self.recording:
                return
            self.recording = True
            self.frames = []
            self.record_start = time.monotonic()
        self.set_state("recording")
        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                callback=self._audio_callback,
            )
            stream.start()
        except Exception as e:
            with self.lock:
                self.recording = False
            self.set_state("idle")
            self.notify(f"Microphone error: {e}")
            return

        with self.lock:
            if not self.recording:
                # released before the mic finished opening — discard this stream
                stray = stream
            else:
                self.stream = stream
                stray = None
        if stray is not None:
            try:
                stray.stop()
                stray.close()
            except Exception:
                pass
            return

        play_sound(SOUND_START)  # audio cue: recording started (confirms the hotkey works)

        # auto-stop watchdog
        def watchdog():
            time.sleep(AUTO_STOP_SEC)
            if self.recording:
                self.stop_recording_and_transcribe()

        threading.Thread(target=watchdog, daemon=True).start()

    def stop_recording_and_transcribe(self):
        with self.lock:
            if not self.recording:
                return
            self.recording = False
            duration = time.monotonic() - self.record_start
            frames = self.frames
            self.frames = []
            stream = self.stream
            self.stream = None

        try:
            if stream is not None:
                stream.stop()
                stream.close()
        except Exception:
            pass

        if duration < MIN_DURATION_SEC:
            self.set_state("idle")
            self._set_status_text("Ushlab turing (juda qisqa)")
            return

        wav_bytes, audio = frames_to_wav_bytes(frames)

        if audio.size == 0 or int(np.max(np.abs(audio))) < SILENCE_PEAK_THRESHOLD:
            self.set_state("idle")
            self._set_status_text("Ovoz eshitilmadi")
            return

        self.set_state("transcribing")

        def worker():
            try:
                cfg = self.get_config()
                transcript = gemini_transcribe(
                    cfg.get("api_key", ""),
                    cfg.get("model", DEFAULT_CONFIG["model"]),
                    cfg.get("language_mode", DEFAULT_CONFIG["language_mode"]),
                    wav_bytes,
                )
                self.paste_text(transcript)
                play_sound(SOUND_DONE)  # audio cue: transcript pasted (done)
            except GeminiError as e:
                self.notify(str(e))
            except Exception as e:
                self.notify(f"Unexpected error: {e}")
            finally:
                self.set_state("idle")

        threading.Thread(target=worker, daemon=True).start()

    # -- paste ----------------------------------------------------------

    def paste_text(self, text):
        try:
            saved_clipboard = pyperclip.paste()
        except Exception:
            saved_clipboard = None

        try:
            pyperclip.copy(text)
        except Exception as e:
            self.notify(f"Clipboard error: {e}")
            return

        try:
            kb = self.kb_controller
            kb.press(Key.cmd)
            kb.press("v")
            kb.release("v")
            kb.release(Key.cmd)
        except Exception as e:
            self.notify(f"Paste error: {e}")

        time.sleep(0.15)

        if saved_clipboard is not None:
            try:
                pyperclip.copy(saved_clipboard)
            except Exception:
                pass

    # -- hotkey listener ----------------------------------------------------

    def _on_press(self, key):
        if key_matches(key, self.hotkey_target):
            # Dispatch off the pynput listener thread so a slow mic init
            # can't block key-event delivery (incl. the matching release).
            if not self.recording:
                threading.Thread(target=self.start_recording, daemon=True).start()
            # ignore auto-repeat while already recording

    def _on_release(self, key):
        if key_matches(key, self.hotkey_target):
            if self.recording:
                threading.Thread(target=self.stop_recording_and_transcribe, daemon=True).start()

    def start_hotkey_listener(self):
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def maybe_prompt_first_run(self):
        """If no API key yet, open the key window shortly AFTER the run loop
        starts — a rumps.Window before app.run() is unreliable."""
        if not self.cfg.get("api_key"):
            self._firstrun_timer = rumps.Timer(self._first_run, 1)
            self._firstrun_timer.start()

    def _first_run(self, timer):
        timer.stop()
        if not self.cfg.get("api_key"):
            self.notify("API key kiriting…", "Sozlash")
            self.on_api_key(None)


def main():
    app = GeminiMicApp()
    app.start_hotkey_listener()
    app.maybe_prompt_first_run()
    app.run()


if __name__ == "__main__":
    main()
