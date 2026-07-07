"""Gemini Mic — Windows tray voice-to-text app.

Hold a hotkey -> record mic -> Gemini transcribes -> paste into the focused
field. Ports the Android app's Gemini prompt / cleanTranscript /
formatParagraphs logic 1:1 (see GeminiClient.java).

Run:      python gemini_mic.py
Self-test: python gemini_mic.py --selftest
"""

import base64
import ctypes
import json
import os
import re
import sys
import tempfile
import threading
import time
import wave
from io import BytesIO

# ---------------------------------------------------------------------------
# Paths / config
# ---------------------------------------------------------------------------

APP_NAME = "GeminiMic"
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "GeminiMic")
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

# Primary is gemini-3.5-flash; when it errors (busy/quota/not available) retry
# once with a DIFFERENT model (separate quota) so a 429 rarely reaches the user.
FALLBACK_MODEL = "gemini-3-flash-preview"
FALLBACK_STATUSES = (404, 429, 500, 503)

LANGUAGE_CHOICES = [
    ("Uzbek + English", "uz_en"),
    ("Uzbek + Russian", "uz_ru"),
    ("Uzbek + English + Russian", "uz_en_ru"),
]

# Recording guards (match Android)
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
# Self-test entry point (no other deps needed)
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
# Heavier imports (only needed for the actual tray app, not --selftest)
# ---------------------------------------------------------------------------

import numpy as np
import requests
import sounddevice as sd
import pyperclip
from PIL import Image, ImageDraw
import pystray
from pynput import keyboard
from pynput.keyboard import Key, Controller as KeyboardController

import winsound

import tkinter as tk
from tkinter import ttk, messagebox


def beep(freq, duration):
    """Short non-blocking tone for audio feedback (recording start / done)."""
    def _b():
        try:
            winsound.Beep(freq, duration)
        except Exception:
            pass
    threading.Thread(target=_b, daemon=True).start()


# ---------------------------------------------------------------------------
# Icon generation (blue/red/green circle + mic glyph)
# ---------------------------------------------------------------------------

COLOR_IDLE = (37, 99, 235)  # #2563EB blue
COLOR_RECORDING = (220, 38, 38)  # red
COLOR_TRANSCRIBING = (22, 163, 74)  # green


def make_icon_image(color, size=64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = 2
    draw.ellipse([pad, pad, size - pad, size - pad], fill=color)

    # simple mic glyph in white
    cx = size / 2
    body_w = size * 0.22
    body_h = size * 0.30
    body_top = size * 0.22
    body_bottom = body_top + body_h
    draw.rounded_rectangle(
        [cx - body_w / 2, body_top, cx + body_w / 2, body_bottom],
        radius=body_w / 2,
        fill="white",
    )
    # stand arc
    arc_r = size * 0.18
    draw.arc(
        [cx - arc_r, body_top - size * 0.02, cx + arc_r, body_bottom + size * 0.06],
        start=20,
        end=160,
        fill="white",
        width=max(2, int(size * 0.045)),
    )
    # base stem
    stem_top = body_bottom + size * 0.06
    stem_bottom = stem_top + size * 0.10
    draw.line([cx, stem_top, cx, stem_bottom], fill="white", width=max(2, int(size * 0.045)))
    # base foot
    foot_w = size * 0.18
    draw.line(
        [cx - foot_w / 2, stem_bottom, cx + foot_w / 2, stem_bottom],
        fill="white",
        width=max(2, int(size * 0.045)),
    )
    return img


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
# Windows "Start with Windows" toggle (Run registry key)
# ---------------------------------------------------------------------------

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _startup_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    else:
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        script = os.path.abspath(__file__)
        return f'"{pythonw}" "{script}"'


def is_startup_enabled():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except (ImportError, FileNotFoundError, OSError):
        return False


def set_startup_enabled(enabled):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _startup_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
    except (ImportError, OSError):
        pass


# ---------------------------------------------------------------------------
# Settings window (Tkinter)
# ---------------------------------------------------------------------------

class SettingsWindow:
    """Runs a Tkinter settings dialog on its own thread with its own mainloop,
    since the tray icon runs on the main thread via pystray."""

    _lock = threading.Lock()
    _open = False

    def __init__(self, app):
        self.app = app

    def open(self):
        with SettingsWindow._lock:
            if SettingsWindow._open:
                return
            SettingsWindow._open = True
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        try:
            self._build_and_show()
        finally:
            with SettingsWindow._lock:
                SettingsWindow._open = False

    def _build_and_show(self):
        cfg = self.app.get_config()

        root = tk.Tk()
        root.title("Gemini Mic — Settings")
        root.resizable(False, False)
        try:
            root.attributes("-topmost", True)
        except tk.TclError:
            pass

        pad = {"padx": 10, "pady": 6}

        frm = ttk.Frame(root)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Gemini API key:").grid(row=0, column=0, sticky="w", **pad)
        api_key_var = tk.StringVar(value=cfg.get("api_key", ""))
        api_key_entry = ttk.Entry(frm, textvariable=api_key_var, show="*", width=40)
        api_key_entry.grid(row=0, column=1, sticky="we", **pad)

        show_var = tk.BooleanVar(value=False)

        def toggle_show():
            api_key_entry.config(show="" if show_var.get() else "*")

        ttk.Checkbutton(frm, text="Show", variable=show_var, command=toggle_show).grid(
            row=0, column=2, sticky="w", **pad
        )

        ttk.Label(frm, text="Model:").grid(row=1, column=0, sticky="nw", **pad)
        model_var = tk.StringVar(value=cfg.get("model", DEFAULT_CONFIG["model"]))
        model_frame = ttk.Frame(frm)
        model_frame.grid(row=1, column=1, columnspan=2, sticky="w", **pad)
        for label, value in MODEL_CHOICES:
            ttk.Radiobutton(model_frame, text=label, variable=model_var, value=value).pack(
                anchor="w"
            )

        ttk.Label(frm, text="Language:").grid(row=2, column=0, sticky="nw", **pad)
        lang_var = tk.StringVar(value=cfg.get("language_mode", DEFAULT_CONFIG["language_mode"]))
        lang_frame = ttk.Frame(frm)
        lang_frame.grid(row=2, column=1, columnspan=2, sticky="w", **pad)
        for label, value in LANGUAGE_CHOICES:
            ttk.Radiobutton(lang_frame, text=label, variable=lang_var, value=value).pack(
                anchor="w"
            )

        ttk.Label(frm, text="Push-to-talk hotkey:").grid(row=3, column=0, sticky="w", **pad)
        hotkey_var = tk.StringVar(value=cfg.get("hotkey", DEFAULT_CONFIG["hotkey"]))
        ttk.Entry(frm, textvariable=hotkey_var, width=20).grid(
            row=3, column=1, sticky="w", **pad
        )
        ttk.Label(frm, text="(e.g. 'right ctrl', 'f9')", foreground="#666").grid(
            row=3, column=2, sticky="w", **pad
        )

        status_var = tk.StringVar(value="")
        status_label = ttk.Label(frm, textvariable=status_var, foreground="#0a0")
        status_label.grid(row=4, column=0, columnspan=3, sticky="w", padx=10)

        def on_save():
            new_cfg = {
                "api_key": api_key_var.get().strip(),
                "model": model_var.get(),
                "language_mode": lang_var.get(),
                "hotkey": hotkey_var.get().strip() or DEFAULT_CONFIG["hotkey"],
            }
            try:
                save_config(new_cfg)
            except OSError as e:
                messagebox.showerror("Gemini Mic", f"Could not save settings:\n{e}")
                return
            self.app.apply_config(new_cfg)
            status_var.set("Saved.")
            root.after(700, root.destroy)

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=5, column=0, columnspan=3, sticky="e", padx=10, pady=(10, 10))
        ttk.Button(btn_frame, text="Save", command=on_save).pack(side="right")
        ttk.Button(btn_frame, text="Cancel", command=root.destroy).pack(side="right", padx=(0, 6))

        root.update_idletasks()
        w = root.winfo_reqwidth()
        h = root.winfo_reqheight()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

        root.mainloop()


# ---------------------------------------------------------------------------
# Hotkey parsing (pynput)
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
# Main application
# ---------------------------------------------------------------------------

class GeminiMicApp:
    def __init__(self):
        self.cfg = load_config()
        self.lock = threading.Lock()
        self.recording = False
        self.frames = []
        self.stream = None
        self.record_start = 0.0
        self.hotkey_target = parse_hotkey(self.cfg.get("hotkey", DEFAULT_CONFIG["hotkey"]))
        self.kb_controller = KeyboardController()
        self.icon = None
        self.settings_window = SettingsWindow(self)
        self._listener = None

    # -- config -----------------------------------------------------------

    def get_config(self):
        with self.lock:
            return dict(self.cfg)

    def apply_config(self, new_cfg):
        with self.lock:
            self.cfg = dict(new_cfg)
            self.hotkey_target = parse_hotkey(self.cfg.get("hotkey", DEFAULT_CONFIG["hotkey"]))

    # -- tray icon ----------------------------------------------------------

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Settings…", lambda: self.settings_window.open()),
            pystray.MenuItem(
                "Start with Windows",
                lambda: set_startup_enabled(not is_startup_enabled()),
                checked=lambda item: is_startup_enabled(),
            ),
            pystray.MenuItem("Quit", self.quit),
        )

    def set_state(self, state):
        """state: 'idle' | 'recording' | 'transcribing'"""
        if self.icon is None:
            return
        color = {
            "idle": COLOR_IDLE,
            "recording": COLOR_RECORDING,
            "transcribing": COLOR_TRANSCRIBING,
        }.get(state, COLOR_IDLE)
        title = {
            "idle": "Gemini Mic — ready",
            "recording": "Gemini Mic — recording…",
            "transcribing": "Gemini Mic — transcribing…",
        }.get(state, "Gemini Mic")
        self.icon.icon = make_icon_image(color)
        self.icon.title = title

    def notify(self, message, title="Gemini Mic"):
        try:
            if self.icon is not None:
                self.icon.notify(message, title)
        except Exception:
            pass

    def _tooltip(self, text):
        """Quiet status via the tray tooltip — no popup balloon."""
        if self.icon is not None:
            self.icon.title = text

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

        beep(1000, 80)  # audio cue: recording started (confirms the hotkey works)

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
            self._tooltip("Gemini Mic — hold longer")
            return

        wav_bytes, audio = frames_to_wav_bytes(frames)

        if audio.size == 0 or int(np.max(np.abs(audio))) < SILENCE_PEAK_THRESHOLD:
            self.set_state("idle")
            self._tooltip("Gemini Mic — ovoz eshitilmadi")
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
                beep(660, 90)  # audio cue: transcript pasted (done)
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
            kb.press(Key.ctrl)
            kb.press("v")
            kb.release("v")
            kb.release(Key.ctrl)
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

    # -- lifecycle ----------------------------------------------------------

    def quit(self, *_args):
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
        if self.icon is not None:
            self.icon.stop()

    def run(self):
        if not self.cfg.get("api_key"):
            self.settings_window.open()

        self.start_hotkey_listener()

        self.icon = pystray.Icon(
            APP_NAME,
            make_icon_image(COLOR_IDLE),
            "Gemini Mic — ready",
            menu=self._build_menu(),
        )

        def on_ready(icon):
            icon.visible = True
            beep(880, 120)
            self.notify(
                "Ishga tushdi. Yozish joyiga bosing, o'ng Ctrl ni bosib turib gapiring. "
                "Ikonka soat yonidagi ^ ichida bo'lishi mumkin."
            )

        self.icon.run(setup=on_ready)


def _already_running():
    """Single-instance guard via a named Windows mutex."""
    try:
        ctypes.windll.kernel32.CreateMutexW(None, False, "GeminiMic_SingleInstance")
        return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return False


def main():
    try:
        # DPI awareness for crisp tray icon rendering, best-effort.
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    if _already_running():
        ctypes.windll.user32.MessageBoxW(
            None,
            "Gemini Mic allaqachon ishlayapti.\n\n"
            "Soat yonidagi ^ belgisini bosing — ko'k mikrofon ikonkasi o'sha yerda.\n"
            "Ishlatish: yozish joyiga bosing, o'ng Ctrl ni bosib turib gapiring.",
            "Gemini Mic",
            0x40,  # MB_ICONINFORMATION
        )
        return

    app = GeminiMicApp()
    app.run()


if __name__ == "__main__":
    main()
