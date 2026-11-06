import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recording_clearance import NotCleared, require_clearance

tmp = Path(tempfile.mkdtemp())
audio = tmp / "a.bin"
audio.write_bytes(b"audio-bytes-1")
sha = hashlib.sha256(b"audio-bytes-1").hexdigest()


def reg(name, **over):
    e = {"sha256": sha, "kind": "internal", "cleared_by": "Said", "date": "2026-11-06", "note": "t"}
    e.update(over)
    e = {k: v for k, v in e.items() if v is not None}
    p = tmp / name
    p.write_text(json.dumps({"version": 1, "entries": [e]}), encoding="utf-8")
    return p


bad = tmp / "corrupt.json"
bad.write_text("{not json", encoding="utf-8")
empty = tmp / "empty.json"
empty.write_text('{"version": 1, "entries": []}', encoding="utf-8")
changed = tmp / "changed.bin"
changed.write_bytes(b"audio-bytes-2")

refuse = [
    ("uncleared file refused", audio, empty),
    ("changed after clearance refused", changed, reg("r1.json")),
    ("cleared_by Gemini refused", audio, reg("r2.json", cleared_by="Gemini")),
    ("cleared_by gemini-3-flash refused", audio, reg("r3.json", cleared_by="gemini-3-flash")),
    ("empty cleared_by refused", audio, reg("r4.json", cleared_by="  ")),
    ("missing registry refused", audio, tmp / "nope.json"),
    ("corrupt registry refused", audio, bad),
    ("bad kind refused", audio, reg("r5.json", kind="client")),
    ("missing file refused", tmp / "gone.bin", reg("r6.json")),
    ("missing date refused", audio, reg("r7.json", date=None)),
]
ok = [
    ("listed file passes", audio, reg("p1.json")),
    ("Aisha passes", audio, reg("p2.json", cleared_by="Aisha")),
]

failed = 0
for name, f, r in refuse:
    try:
        require_clearance(f, r)
        print(f"FAIL {name}: was cleared")
        failed += 1
    except NotCleared as e:
        print(f"ok   {name}: {e}")
for name, f, r in ok:
    try:
        assert require_clearance(f, r) == sha
        print(f"ok   {name}")
    except (NotCleared, AssertionError) as e:
        print(f"FAIL {name}: {e}")
        failed += 1
print(f"{len(refuse) + len(ok) - failed}/{len(refuse) + len(ok)} passed")
sys.exit(1 if failed else 0)
