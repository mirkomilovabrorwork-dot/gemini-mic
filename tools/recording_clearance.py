import hashlib
import json
import re
import sys
from pathlib import Path

DEFAULT = Path(__file__).resolve().parent.parent / "docs" / "recording_clearance.json"
KINDS = {"internal", "own_dictation", "synthetic"}
MACHINE_WORDS = {"gemini", "gpt", "claude", "glm", "deepseek", "model", "auto", "agent", "jarvis", "llm", "ai"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class NotCleared(Exception):
    pass


def file_sha256(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        raise NotCleared("fayl topilmadi yoki o'qib bo'lmadi")
    return h.hexdigest()


def _machine_name(name):
    return any(w in MACHINE_WORDS for w in re.findall(r"[a-z]+", name.lower()))


def _entry_problem(e):
    if not isinstance(e, dict):
        return "yozuv noto'g'ri"
    if e.get("kind") not in KINDS:
        return "kind ruxsat etilmagan"
    if not (isinstance(e.get("date"), str) and DATE_RE.match(e["date"])):
        return "sana yo'q yoki noto'g'ri"
    by = e.get("cleared_by")
    if not (isinstance(by, str) and by.strip()):
        return "cleared_by bo'sh"
    if _machine_name(by):
        return "cleared_by mashina nomi, odam bo'lishi kerak"
    return None


def require_clearance(path, registry=DEFAULT):
    digest = file_sha256(path)
    try:
        data = json.loads(Path(registry).read_text(encoding="utf-8"))
        entries = data["entries"]
        if not isinstance(entries, list):
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        raise NotCleared("ruxsat ro'yxati yo'q yoki buzuq")
    problem = None
    for e in entries:
        if isinstance(e, dict) and str(e.get("sha256", "")).lower() == digest:
            problem = _entry_problem(e)
            if problem is None:
                return digest
    raise NotCleared(problem or "bu fayl ruxsat ro'yxatida yo'q")


def main(argv):
    if len(argv) != 2:
        print("usage: recording_clearance.py <file>")
        return 2
    try:
        digest = require_clearance(argv[1])
    except NotCleared as e:
        print(f"REFUSED: {e}")
        return 1
    print(f"CLEARED: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
