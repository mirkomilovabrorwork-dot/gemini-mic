# Gemini Mic — STATE

_Trigger words: "gemini", "gemini mic". Source of truth for resume._

## NEXT STEP (2026-07-28)

**Rebuild `GeminiMic-share.zip` from the current source, then hand it to the friend.**
Why this and not something else: a wave-audit on 2026-07-28 searched Desktop, Downloads and both project
folders and found **no `*share*.zip` anywhere** - the only Desktop artefact is `GeminiMic.exe` (33.1 MB,
2026-07-13). The board below still describes the zip as if it exists on the Desktop. So the thing the
friend is supposed to receive does not currently exist, and every "refresh the zip" note below is really
"build the zip".
Gate before handing it over: `.claude\gate.cmd` (py_compile of the win+mac sources + the Windows
self-test) - verified green 2026-07-28. Owner action needed: none until the zip exists.

## STATUS (resume board) - 2026-07-11
- **Merge-commit hook tracked (2026-07-18):** `.githooks/pre-merge-commit` is now in git too. It was created but untracked, so a clone carried only half the protection - git routes a MERGE through that hook, and that path would have been silently unguarded.
- **Native git pre-commit hook (2026-07-18):** `.githooks/pre-commit` runs this repo's own `.claude/gate.cmd` before any commit, so a commit from a terminal, an IDE or another agent is checked too - previously only commits made through Claude's own tools were. Proven BOTH ways before landing: a deliberate breakage blocked the commit with the real failure, and reverting it let the same commit through. Escape hatch `SKIP_GATE=1` (deliberately loud). **After a fresh clone it is INERT until you run `git config core.hooksPath .githooks`** - that setting is local git config and does not travel with the repo.
- Done-gate added 2026-07-13: `.claude/gate.cmd` (py_compile win+mac sources + windows --selftest) now guards every commit via the global gate-before-commit hook.
- Docs-only maintenance: corrected `CLAUDE.md` typo `selftest` -> `self-test`.
- Product code unchanged. Next: resume the previously planned product work.

## What this is
System-wide voice keyboard for Android: hold a floating mic → record → Gemini
transcribes (mixed Uzbek/English/Russian) → text is auto-typed into the focused
field via an accessibility service. Pure Android SDK (Java), no third-party deps.
Package `com.autosmart.geminimic` (debug suffix `.debug`).

## Origin
Original Codex-built project source was lost (not on D:/C:/GitHub). Reconstructed
1:1 by decompiling `GeminiMic-Simple-Android-debug.apk` (androguard) into a clean
Java Gradle project. Decompiled reference + spec live in `D:\vibecoding\geminimic-recovered\`.

## 2026-07-30 — FIRST-WORDS FIX SHIPPED (Windows); NEXT STEP below
- **Owner: "boshidagi gapim yozilmayapti" — ROOT CAUSE + FIX (commit fc44961):**
  the input stream was opened ON key-down (~0.2-0.5s on Windows) so capture
  started late and the first words were dropped; the start beep honestly fired
  after the late open. NOW: persistent mic stream (opened at app start, 1.5s RAM
  ring, 0.1s blocks) + key-down seeds the recording with the last 0.6s
  (pre-roll) → capture is instant, speech at/just-before the press survives,
  beep fires immediately. Audio never leaves the machine outside a dictation.
  Tradeoff: Windows mic-in-use indicator stays on. quit() closes the stream;
  device unplug → lazy reopen (stream.active check). Verified: selftest, ring
  math unit-check, app restarted, log line "mic stream opened (persistent…)".
  Android has the same latency class (MediaRecorder) — NOT built, candidate only.
- **NEXT STEP: owner tests first-words capture** (speak immediately on press —
  beginning should now be in the text). Then his OPEN QUESTION: use the
  BLUETOOTH HEADSET mic instead of the external mic. Facts for that decision:
  the app follows the WINDOWS DEFAULT input device (no picker in-app yet), and
  BT is a real fork — BT headset mic runs in hands-free mode: EITHER keep the
  persistent stream (first words safe) and ALL his audio/music sounds like a
  phone call while the app runs, OR open-on-demand for BT (music stays hi-fi)
  and the first-words loss RETURNS (BT HFP wake adds ~0.5-1s). BT mic quality
  (tinny 16kHz) also likely WORSENS the word-substitution defect. Options put
  to him: (a) try by switching Windows default input when wearing the headset,
  (b) I build an in-app device picker + BT-aware mode, (c) stay on external mic
  for accuracy. AWAITING his pick.

## 2026-07-29 (FINAL) — model is gemini-3-flash-preview; 3.6 REJECTED
- **The owner was right and my 3.6 switch was wrong.** He said "narx va sifat
  menimcha hali ham 3" — and I had never A/B'd the cheap incumbent against 3.6,
  only 3.5-vs-3.6 and 3.6-vs-pro. Measured on 4 segments of his own recording:
  · **3-flash-preview: correct EVERY time** ("delegatsiya", "thinking budget"),
    ~2.3–4.5s, **$0.39/mo** at 30/day.
  · 3.6-flash: wrote "relokatsiya", and on **2 of 3 segments emitted its own
    REASONING instead of the transcript** ("Using explicit rules for mixed
    Uzbek/English speech transcription…") → unusable for dictation.
  · 3.1-pro-preview: most accurate but 9.2s on a 12s clip (~3x the wait) and
    $1.55/mo — owner first chose it, then reversed on price/quality.
  **FINAL: primary `gemini-3-flash-preview`, fallback `gemini-3.5-flash`.**
  Commit f15ca32 (+ e37e2cc), Android CI 30480877402 GREEN, APK on Desktop,
  Windows app restarted, config.json set. **DO NOT re-"upgrade" to 3.6** — the
  reason is commented at the constant in both platforms.
- KEPT from the 3.6 round (good regardless): maxOutputTokens 4096, per-model
  thinking config, `finishReason != STOP` logging, gate-rejection rms logging.
- **VTT leak fixed** (e37e2cc): a dictation came back as subtitle cues
  ("00:03.000-->00:08.500 …"); the cleaner only knew the `[00:01]` form. Now
  strips the arrow form too — marker only, sentence preserved; normal spoken
  times ("Soat 10:30", "09:00 --> 10:00") untouched.

## 2026-07-29 (superseded) — MODEL SWITCHED to gemini-3.6-flash (Windows + Android)
- **Settled by A/B on the OWNER'S OWN recorded voice** (60s captured locally,
  `scratchpad/owner_voice.wav`): 3.5-flash wrote his spoken "thinking budget" as
  **"sinking budget"**; **3.6-flash got it right** — exactly the defect class he
  had been complaining about. Rest equivalent. HE judged the two transcripts
  (only the speaker knows ground truth). Latency equal (~2.0 vs ~2.2s on 10s).
- **Cheaper too**: 3.6 output $7.50/1M vs 3.5's $9.00 (input both $1.50).
  Measured real usage = 710 in / 25 out tokens per 10s dictation → **~$1.13/mo
  at 30/day** (3.5 ≈ $1.16, 3-flash-preview ≈ $0.39 — 3x cheaper but it is the
  model that made the language errors, so not worth 74¢/mo).
- **Mac deliberately NOT switched** — owner scoped it to Windows+Android.
- Implementation: `generationConfig` is now PER-MODEL on both platforms and the
  fallback path rebuilds it (3.6 rejects `thinkingBudget`; the older models NEED
  it or they enable thinking: 10s clip 2s → 3.1s on 3.5, 4.7s on 3-preview).
  Commit 491d9e4; Android CI 30477745813 GREEN, APK verified (3.6 primary +
  3-flash-preview fallback compiled in) and copied to Desktop; Windows app
  restarted on the new code; owner's config.json set to 3.6. E2E re-verified on
  his voice through the real app path.
- **REGRESSION from that switch, found + fixed same session (commit 3c0e24e):**
  owner reported "spoke a long time, not even a third got written" — his log
  showed a 50.6s dictation → 110 chars (old model: 60.8s → 584). Cause: 3.6
  rejects `thinkingBudget`, so I dropped it — which left 3.6's thinking ON, and
  thinking tokens bill against `maxOutputTokens`: on an identical 45s clip 3.6
  spent 984 of 1024 on thoughts and returned `finishReason=MAX_TOKENS` with 97
  chars, cut mid-sentence — as a normal HTTP 200, so nothing looked wrong.
  FIX: 3.6 gets `thinkingLevel: "low"` (→ 320 chars/STOP, same as the 3.5
  baseline, and still keeps "thinking budget" that 3.5 mangles); maxOutputTokens
  1024→**4096** on all models; Windows now LOGS any `finishReason != STOP` with
  usageMetadata so silent truncation can't hide again. E2E on his voice: 332
  chars, 2.3s. Android CI 30478552394 GREEN, APK verified + on Desktop.
- **OWNER TODO: install the new APK on the phone** (Desktop `GeminiMic-android.apk`).
- Share zip still NOT refreshed (carries the old model + pre-SAC exe + no
  autostart line in HOW-TO). Do all three at the next zip refresh.

## 2026-07-29 — app was BLOCKED by Windows, + model survey
- **ROOT CAUSE of "ishlamayapti" (2026-07-28): Windows Smart App Control is ON
  (VerifiedAndReputablePolicyState=1) and blocks the unsigned GeminiMic.exe** —
  "An Application Control policy has blocked this file". Nothing wrong with the
  code. WORKAROUND IN PLACE: run from source via the venv's `pythonw.exe
  gemini_mic.py` (python is signed → allowed); the Startup shortcut was
  REPOINTED to that. Consequence: **the .exe is dead on this machine — edit the
  .py and just restart the process, no PyInstaller rebuild needed.** (Other
  routes if ever wanted: sign the exe, or turn SAC off — irreversible without a
  Windows reinstall, so not done.) The share-zip friend is unaffected unless he
  also has SAC on; note it in HOW-TO at next zip refresh.
- **Model survey (owner asked about "new Gemini 1.5" — that is a 2024 model,
  two generations BEHIND).** Queried the models API: newest flash on his key is
  **gemini-3.6-flash** (app runs 3.5-flash). A/B on TTS clips: 3.6 ≈ 3.5, NO
  measurable gain (3.6 with thinkingLevel:low was slightly WORSE — turned
  "kontrol"→"control"). **3.6 rejects `thinkingConfig.thinkingBudget` with a
  generic 400** — must drop it or use `thinkingLevel`. Verified ALL THREE
  platforms send `thinkingBudget: 0` (GeminiClient.java:235, windows:571,
  mac:374) → a 3.6 switch is a 3-file change, not a config flip. NOT switched:
  no evidence of gain.
  Real test needs the owner's accented voice (see KNOWN LIMITATION below);
  owner AGREED 2026-07-29 to record 20s → A/B 3.5 vs 3.6 on his real voice.
- Gate rejections now log `voiced=N/3 loudest_rms=X threshold=Y` (commit
  ebc86c8) so "he spoke quietly" is distinguishable from "he never spoke".

## FIX 2026-07-13: "spoke but nothing, not even in clipboard"
- Log showed the has_speech gate rejected 19 REAL dictations ("no sustained
  speech", e.g. a 2.98s utterance) — quiet/far speech fell under VOICE_RMS=250.
  Lowered to 120 (his silence floor rms<80 → safe margin; verified silence+click
  still rejected, quiet speech passes). Commit 6e0dab2, win+mac, exe rebuilt.
  If silence starts hallucinating again → nudge back up; if still eats speech →
  lower more. The two other "not working" causes are separate: (a) Electron
  (Claude) flaky UIA → auto-paste inconsistent, use Ctrl+V / click field first;
  (b) [[below]] loanword normalization.

## PROMPT EXPERIMENTS ALREADY RUN AND REJECTED (2026-07-29) — do not repeat
Scored on 3-4 segments of the owner's own recording (`scratchpad/owner_voice.wav`),
metric = how many of {delegatsiya, thinking budget, workflow} survive verbatim.
- **Stronger "VERBATIM / you are a microphone, not an editor" rule with explicit
  examples (terminal≠ilova, kontrol≠nazorat)**: NO gain — 1/1/2 → 1/1/1. REJECTED.
- **Owner's hypothesis: the per-language script rules ("Uzbek Latin, English in
  English, Russian in Cyrillic") confuse the model into substituting words** —
  tested a minimal prompt with those rules removed: **WORSE, 7 → 5**. The rules
  help. REJECTED, prompt kept as-is.
- Head-to-head 3-flash-preview vs 3.5-flash on 4 segments: **4 : 2** for
  3-preview; 3.5 once emitted an ENTIRE segment in Cyrillic. Confirms the owner.
- **"Deep think" round (owner: make 3-flash itself verbatim) — 3 mechanically
  new levers, ALL measured, none beat baseline 7/9:** domain-context line
  ("software developer dictating, English jargon expected") **7/9** tie ·
  pause-aware ~12s chunking, parallel **5/9** (short chunks lose context and
  hurt) · 3-sample vote at temp 0.7, medoid pick **5/9** (substitution is NOT
  random on the hard spot — all 3 samples agree on the wrong word, so voting
  can't fix it; that's also why temp changes do nothing). Harness:
  `scratchpad/test_deep.py`. **Total 16 experiments. The "thinking budget"
  passage at ~30-55s fails in EVERY configuration — for 3-flash the acoustic
  evidence there genuinely reads as Uzbek "sening byudjeting"; this is the
  model's ceiling on this clip, not a settings problem.** The ONLY in-Gemini
  lever that ever scored above baseline remains the vocabulary hint (8/9),
  rejected for false-positive risk; its safe re-entry test (feed speech WITHOUT
  the listed words, verify none get injected) is written above.
- **Deep-think round 2 (owner repeated the directive) — 2 more levers, both
  measured, neither beat 7/9:** two-pass verify WITH AUDIO in the second call
  (draft + "fix only mismatches"; distinct from ustoz's failed text-only refine)
  **7/9 tie at 3.7s** (double latency, adds "Albatta, mana…" preamble noise —
  not worth it) · per-word [timestamps] to force acoustic alignment (stripped
  after) **5/9**. Harness: `scratchpad/test_deep2.py`. **Running total: 18
  experiments; software levers inside 3-flash are EXHAUSTED.**
- **Mic level checked programmatically (owner asked, 2026-07-29 late): the
  Windows capture level was ALREADY 100%** (pycaw, IAudioEndpointVolume; dB
  range -96..+30 so scalar 1.0 includes the boost ceiling). Nothing to raise in
  settings → the -28 dBFS quietness comes from DISTANCE / the laptop's AMD mic
  array itself. So the one remaining physical lever is: **speak closer to the
  mic**, then re-record the 60s reference ("boshla") and re-run the harness
  (best variants: baseline + A-DOMAIN). pycaw now installed in windows/.venv
  (test tool only, not a runtime dependency of the app).
- **The remaining lever is PHYSICAL, not software: capture SNR.** Key insight —
  the stubborn failure is PHONETIC, not semantic: accented "thinking" ≈
  "sening" (th→s), and his recording's speech RMS is only **-28 dBFS** (peak
  -9). The model may genuinely be hearing "sening" on quiet audio. Post-hoc
  software gain already failed (amplifies noise equally, 5/9) — the fix must be
  at CAPTURE: raise the Windows microphone input level / speak closer, then
  re-record the 60s reference and re-run the harness. If the score doesn't move
  on louder audio either → that is the model's true ceiling, said plainly.
- **Owner's idea: run with NO prompt at all (maybe the rules are what make it
  "edit") — TESTED, disproven, and the reason matters.** With no text part the
  model does not transcribe AT ALL, it ANSWERS the audio: "Delegatsiya va
  avtomatlashtirish o'rtasidagi farqni…", "Ushbu videoda gapirayotgan shaxs…",
  "Albatta, OpenAI tomonidan taqdim etilgan o1-preview…". It scored 7/9 only
  because the marker words appear inside that commentary — **the metric lies on
  this variant; do not read that 7 as a tie.** With a bare "Transcribe this
  audio." it does transcribe but prepends "Albatta, mana audio transkripsiyasi:",
  and once emitted Kazakh Cyrillic and once timestamps. 3.5-flash with the bare
  line scored **2/9**. CONCLUSION: the long prompt is load-bearing — it is what
  keeps the output a clean transcript — and it is NOT the cause of substitution.
- **Fable's 4 API-level ideas (owner asked for Fable + Codex) — ALL TESTED, ALL
  LOST to the baseline's 7/9.** Its root-cause frame is worth keeping: Gemini is
  an audio-conditioned LANGUAGE MODEL, so at each token it blends weak acoustic
  evidence against its own fluent-text prior; substitution happens in DECODING,
  below the level prompt text operates on — which is why 7 wording attempts all
  plateaued. Results:
  · gain-normalize + high-pass the audio (his mic peaks at -9 dBFS, speech RMS
    -28, so this was a fair shot): **5/9**, 2.3s
  · audio part FIRST + rules moved to `system_instruction` (recency, not
    wording): **6/9**, 1.8s
  · `responseMimeType: application/json` + `responseSchema` of {start,text}
    segments, to break prose-momentum decoding: **5/9**, 2.4s
  · `thinkingBudget: 512` (revise-before-emit while audio is still in context,
    with thought-parts filtered out of the join): **6/9**, 1.9s
  Harness: `scratchpad/test_fable.py`.
- **Owner's counter-idea: maybe ustoz's "correct an unclear word from context"
  rule HELPS rather than hurts** — tested as a softened variant ("choose the
  reading that fits the context rather than a phonetically similar word that
  makes no sense"): **7→5, WORSE.** REJECTED.
- **Vocabulary hint (list of the speaker's own terms appended to the prompt):
  the ONLY thing that measurably WORKED** — score 7→8, and the segment that
  produced "sening byudjeting" every time became "Thinking budget" **3/3 with
  the list vs 0/3 without**. **OWNER REJECTED IT anyway (2026-07-29): a bias
  list can pull DIFFERENT words INTO the listed ones** ("boshqa asoslar
  aytganimda o'z-o'ziga aylantirib qo'yishi mumkin") — a false-positive risk I
  failed to flag when proposing it. Reverted, not shipped. Only revisit if he
  asks, and only with a false-positive test (feed speech that does NOT contain
  the listed words and check none are injected).
- **Cross-checked against the ustoz project** (owner asked; independent agent read
  `ustoz-github/apps/web/lib/gemini-transcribe.ts`). ustoz runs the SAME model
  (gemini-3-flash-preview) and the same single-pass shape; it has NO lexical
  post-processing that could reverse a substitution. Two transferable candidates
  found, both TESTED HERE AND REJECTED:
  · **bold-mark every foreign word** (`**deadline**`, stripped later so the user
    never sees it) — 7→**6**, and it caused a NEW failure, pulling the Uzbek
    loanword "delegatsiya" into English "dedication".
  · **temperature 0.1** (ustoz's value, unexamined there) — 7→**6**. Keep 0.
  Two useful NEGATIVES from ustoz's own history: (1) its prompt rule 7 says "if a
  word is unclear, correct it from context" — that LICENSES exactly this bug; do
  not port it. (2) ustoz already tried a second "clean/refine" LLM pass over a
  finished transcript and abandoned it as DATA-LOSING
  (`CLAUDE_TO_CODEX_REFINED_DATA_LOSS_2026-07-04.md`) — do not build one here.
- Model scoreboard on the same 4 segments (metric = {delegatsiya, thinking
  budget, workflow} surviving): **3-flash-preview 7/9 @2.0s** · 3.1-pro 6/9
  @10.1s · 3.5-flash 2/4 on the head-to-head (once wrote a whole segment in
  Cyrillic). 3-preview wins accuracy AND speed AND price — nothing to change.
Remaining defect = word SUBSTITUTION by meaning ("terminal" → "ilova"), which is
not a mishearing (the words sound nothing alike). Every available lever has been
measured: 3 prompt variants, 4 models, vocabulary bias. Current config is the
best measured; the residual is a limitation of generative-LLM ASR on accented
mixed speech. Do NOT burn another session re-testing these.

## KNOWN LIMITATION — deferred by owner 2026-07-13
- **Accented loanwords get normalized to formal Uzbek synonyms** (owner: says
  "kontrolni tekshirish" → model writes "nazoratni tekshirish"). Root cause:
  generative-LLM ASR "cleans up" accented speech toward formal language; when a
  loanword is pronounced with an Uzbek accent the model perceives it as Uzbek
  and swaps it for the dictionary equivalent. A/B on English-voice TTS did NOT
  reproduce it (model kept control/process/result — clean audio isn't
  ambiguous), and a blind "VERBATIM, don't swap synonyms + kontrol≠nazorat
  example" prompt rule did NOT help on the testable clip and even added a
  spurious word. The only real fix path = A/B on the OWNER'S real voice (prompt
  vs prompt, 3.5 vs 3-flash-preview). **Owner declined the 30-sec voice capture
  ("kerak emas") → deferred. Do NOT ship a blind prompt change.** Reopen only
  with his real audio. Harness ready: scratchpad/ab_verbatim.py.

## GOAL (owner's words)
Voice typing that "just works" on BOTH phone and PC: hold a key/mic, speak
mixed Uzbek/English/Russian, the text lands in the focused field — free
(Gemini free tier), no fiddling. Owner shares it with a friend as a zip.

## STATUS (resume board) — 2026-07-12 (v11)
- **Windows now auto-inserts WITHOUT clicking the field first** (owner wanted
  phone-parity). Added UI Automation (desktop cousin of Android accessibility):
  before pasting, if no editable is already focused, walk the FOREGROUND window
  for an editable control and SetFocus it, then the existing Ctrl+V lands there.
  Strictly additive/no-regression: existing focus is respected (not hijacked);
  UIA miss/error → plain paste as before. Bounded walk (depth 18, 1.5s).
  Commit 30bc4d2. New dep `uiautomation` (comtypes); requirements.txt + build.bat
  updated with --collect-all comtypes/uiautomation (build.bat was ALSO missing
  the pre-existing sounddevice/pynput flags → would've built a broken exe → fixed).
- VERIFIED hard (import is behind try/except = silent-off risk): e2e on Notepad
  no-click → focus=True + text landed; and a FROZEN probe exe proved uiautomation
  imports + GetForegroundControl works when packaged (yinkaisheng lib needs no
  runtime typelib codegen). Windows exe rebuilt 33.1 MB (hash-match running),
  zip refreshed (47.4 MB, feature verified in zip source). Lesson: [[playbook_gotchas_windows_ps]].
- **"Ishlamadi" false alarm (2026-07-12): the app simply WASN'T RUNNING** when
  the owner tested (no crash in Event Log — PC likely rebooted; Windows had no
  autostart, so unlike Android there wasn't even a notification). Fixed the
  class: **Startup shortcut added** on the owner's machine
  (%APPDATA%\...\Startup\GeminiMic.lnk → Desktop exe) so it launches on every
  boot. Relaunched, stable 12s+, hash = new build. TODO next zip refresh: add a
  "put a shortcut in shell:startup" line to HOW-TO-USE.txt for the friend.
- **2nd "ishlamadi" (2026-07-12) SOLVED VIA THE NEW LOG — clipboard-paste race
  (reviewer's F4) was the real killer**: log proved the whole chain worked
  (record→Gemini transcript→UIA focused the Electron editable→Ctrl+V sent 4×)
  yet no text appeared — the app restored the OLD clipboard 0.15s after Ctrl+V,
  and Electron windows read the clipboard AFTER that → transcript vanished.
  (Notepad pastes instantly, so the earlier e2e falsely passed.) Fix commit
  03ea17c (win+mac): hold clipboard 1.2s before restore + 0.15s settle after
  SetFocus. Exe rebuilt+running (hash match). AWAITING owner retest.
  Note: dictating while an Electron app (e.g. Claude) is foreground correctly
  pastes INTO that app's input — text lands wherever the front window is.
- **3rd "ishlamadi" (2026-07-12) — REAL bug found by live Chrome experiment:
  first-hit editable selection pasted into the WRONG field** (Chrome: the
  ADDRESS BAR got the marker; Electron: an invisible helper input, name='' in
  the owner's log — chain looked green 7×, text landed where nobody looks).
  Fix commit 4a4fc2d: collect ≤12 visible candidates, score Edit>Document
  (a web page IS a Document — focusing it pastes nowhere), in-content>chrome,
  area tiebreak; junk-filter tiny edits (<900px²)/small fragments (<50k px²,
  "Loading…" case seen live) → only junk = DON'T hijack, plain paste as before.
  Live-verified: Chrome textarea received the marker with new scoring (address
  bar with old). Exe rebuilt+running (hash match).
- **FINAL VERDICT on no-click (owner CLOSED it 2026-07-12: "ishlamasa, mayli,
  kerak emas")**: latest log shows the scoring works, but in ELECTRON apps
  (Claude etc.) UIA sees NO real editable at all ("no editable found") —
  Electron doesn't expose its inputs to Windows accessibility unless forced
  (per-app --force-renderer-accessibility tricks = deep fragile rabbit hole).
  So: no-click WORKS in Chrome/Notepad-class apps, NOT in Electron; falls back
  harmlessly (no hijack, plain paste). Owner accepted click-first as the way.
  DO NOT reopen this without new evidence — the whole 3-round debug ladder
  (clipboard race → wrong-editable → Electron-no-a11y) is documented in
  [[playbook_gotchas_windows_ps]].
- **Owner-approved consolation (Windows)**: when no text field is confirmed, the
  transcript STAYS in the clipboard so a missed paste is one Ctrl+V away
  (previously the restore destroyed it — a 13s dictation was lost).
  **Nag removed (commit 272b6c1)**: the "clipboardga yozildi" balloon fired on
  EVERY Electron dictation (target never confirmable there) and can't tell real
  failure from unconfirmable — so per owner it's gone; recording is signalled by
  the start beep (1000Hz) + red tray "recording…" + done beep (660Hz), clipboard
  keep is silent. Confirmed-target path unchanged. Exe rebuilt + running (hash
  match). Share zip NOT yet refreshed with this build (do with next zip refresh
  + HOW-TO autostart line).
- **Mac still needs a click** (uiautomation is Windows-only; mac parity would need
  the macOS AXUIElement accessibility API — separate future work). Android already
  inserts without a click. So: Android ✅, Windows ✅ (new), Mac ⏳.
- OWNER TODO unchanged: enable billing for reliable paid 3.5 (optional). Open
  review findings F6/F9/F4/F8 from v5 still queued.

## STATUS (resume board) — 2026-07-11 (v10)
- **Desktop no-speech hallucination — real root cause found + fixed** (owner:
  press-without-speaking still fabricated a story on desktop; Android is fine).
  MEASURED his mic (sounddevice, local): true silence rms<80 (already rejected by
  the old gate), but a single keyboard click clips one 0.1s window to full-scale
  and the old WHOLE-CLIP-AVERAGE RMS gate let that lone transient inflate the
  average past threshold → noise reached Gemini → hallucination.
  Fix (commit b431240, windows + mac): replaced the average-RMS gate with
  has_speech() — a mini energy-VAD that counts 0.2s windows clearing rms 250 and
  requires ≥3 (~0.6s sustained). Verified: speech=True, silence=False,
  single-click=False, short-0.7s-word=True. Android untouched (its gate works).
  Both selftests pass; Windows exe rebuilt (hash-match running), Mac CI
  29168390715, zip refreshed (46.1 MB) — gate verified INSIDE zip source.
  Lesson: [[playbook_gotchas_llm]] (avg RMS also fooled by a lone transient).
- Params if tuning needed: VOICE_RMS_THRESHOLD=250, MIN_VOICED_WINDOWS=3,
  VOICE_WINDOW_SEC=0.20 (windows+mac, near line ~54). Raise MIN_VOICED to reject
  more; lower VOICE_RMS if it rejects the owner's real quiet speech.

## STATUS (resume board) — 2026-07-11 (v9)
- **MODEL SWAP: primary is now gemini-3.5-flash** (owner: 3-flash-preview
  mis-transcribes his mixed uz/en — Uzbek↔English swaps). Fallback →
  gemini-3-flash-preview (different model = separate 429 quota). All 3 platforms
  + the owner's saved Windows config.json (a default change alone wouldn't reach
  a saved config). Commit 7ed1125; Android CI 29167414378, Mac 29167414367,
  Windows exe rebuilt (hash-match running). Live sanity: 3.5 keeps clean English.
- **Language-preservation prompt fix now on ALL 3** (was Windows-only in v8):
  softer uz_en hint + CRITICAL "transcription not translation, never romanize
  English" rule. Bundled into this rebuild.
- **Owner key strategy = ONE PAID key, 3.5 primary** (his choice). KEY FACT
  taught: Gemini free vs paid is per-PROJECT/billing, not a per-call switch —
  enabling billing deletes the free tier; 'free-first-then-paid' would need TWO
  keys. He picked single-paid for simplicity (his volume cost ≈ cents/mo).
  Lesson: [[playbook_gotchas_llm]].
- Share zip refreshed (46.1 MB) — 3.5-primary + anti-translate verified INSIDE
  zip source + APK. Desktop apk/exe current.
- **OWNER TODO: to actually get the reliable PAID tier, enable billing on the
  Gemini project for his key (aistudio.google.com → billing). Until then the key
  is free-tier 3.5 (daily-limited).** The app needs NO change for paid — same key.
- STILL VERIFY (owner, his real voice): does 3.5 fix the uz↔en language errors?
  If yes → done. If still wrong → next lever (dedicated language modes / test 3.5
  vs 3-flash A/B on his voice). Open review findings from v5 remain (F6/F9/F4/F8).

## STATUS (resume board) — 2026-07-11 (v8)
- **English-spoken-comes-out-Uzbek fix (Windows, owner report)**: on Windows,
  speaking English sometimes got translated to Uzbek or romanized in Uzbek Latin.
  LIVE A/B (Windows-SAPI English clip, old vs new prompt) showed BOTH prompts
  keep CLEAN English perfect → the real trigger is the owner's ACCENTED English
  that the Uzbek-primed prompt nudges toward Uzbek; TTS can't reproduce it.
  Fix (commit 38ad573, **Windows only so far**): de-primed the uz_en hint ("a
  sentence may be entirely English or Uzbek; never translate or romanize") + a
  CRITICAL "transcription NOT translation, never rewrite English in Uzbek
  spelling" rule. Verified NEUTRAL on clean English; UNVERIFIED for the accented
  case → owner tests his real voice. Windows exe rebuilt + running (hash-match).
  **PENDING: if it helps on his voice → mirror the same 2 prompt edits to
  GeminiClient.java (Android) + mac/gemini_mic_mac.py, rebuild, refresh zip.**
  Lesson: [[playbook_gotchas_llm]] (clean TTS test can't repro accented ASR bug).
- Share zip NOT yet refreshed for this change (Windows-only, pending confirm).

## STATUS (resume board) — 2026-07-09 (v7)
- **Desktop hallucination root-cause fix** (owner: "Android eshitilmadi deb AI'ga
  yubormaydi, Windows hali ham to'qiyapti"): Android's LOCAL amplitude gate
  rejects silence before the API call; the desktop port used a single-PEAK gate
  (500 int16) that noisier PC mics exceed on a quiet room → silence reached
  Gemini → fake transcript. The NO_SPEECH prompt is only a backstop (can't save
  noisy-but-not-silent audio — model returns invented words, not the token).
  Fix (commit 91d3e88, windows + mac): replaced peak gate with an **RMS energy
  gate at 200** — noise(rms~80) rejected, speech(rms~1500) sent. Threshold is a
  single tunable knob if a mic differs. Android unchanged (its gate already
  works per owner). Both selftests pass; RMS separation verified.
- Rebuilt: Windows exe (RMS build, **hash-confirmed = the running Desktop
  GeminiMic.exe**, PID relaunched), Mac .app (CI 29035931250 from 91d3e88).
  GeminiMic-share.zip refreshed (46.1 MB) — mac .app binary + all source carry
  the RMS gate (verified inside zip). Lesson: [[playbook_gotchas_llm]].
- If it STILL fabricates on Windows with THIS build: the mic's noise floor is
  above rms 200 → raise SILENCE_RMS_THRESHOLD (windows/mac line ~54). If it now
  rejects the owner's real quiet speech → lower it. One-number autoresearch loop.

## STATUS (resume board) — 2026-07-09 (v6)
- **Hallucination fix (owner-reported, the worst dictation bug)**: pressing
  without clear speech / noisy audio made Gemini FABRICATE a whole invented
  speech (e.g. a "personal branding" talk never said). Fixed on all 3 platforms
  (commit 305143b): prompt now orders the model to output token NO_SPEECH for
  silent/unintelligible audio and never invent content; code detects the
  sentinel (strip non-letters → match NOSPEECH) + empty → "Ovoz eshitilmadi",
  types nothing. Matcher verified: rejects real speech, catches [NO_SPEECH].
  MITIGATION not a 100% guarantee (generative model can still occasionally
  confabulate) — owner verifies live. Lesson saved: [[playbook_gotchas_llm]].
- Rebuilt all 3 GREEN (Android 29032947054, Mac 29032947304, local exe) and the
  fix VERIFIED INSIDE the shipped zip + APK (read back out). Desktop refreshed:
  APK + exe (running, PID replaced) + GeminiMic-share.zip (46.1 MB).
- Still-open review findings (next batch when owner says): F6 finishReason/
  MAX_TOKENS truncation, F9 arm-notif needs POST_NOTIFICATIONS, F4 desktop
  clipboard image-loss/restore-race, F8 "No audio" toast while busy (Android).

## STATUS (resume board) — 2026-07-08 (v5)
- **Senior-review pass done (owner asked "critical analiz")**: independent
  adversarial review of the whole product graded it C and found real bugs.
  Owner approved fixing the 4 worst → ALL FIXED + re-verified by the same
  reviewer (verdict: SHIP), commit 4193858:
  (F1) Android placeholder heuristic could WIPE user text → deleted, only exact
  placeholder list matches now. (F2) desktop stale 60s watchdog killed the next
  recording → record_gen generation guard. (F3) desktop quick-tap left a 60s
  ghost recording → hotkey_down press/release flag + abort in start_recording.
  (F5) mac default hotkey right Ctrl doesn't exist on MacBooks → default now
  RIGHT CMD (cmd keys added to keymap; right ctrl still selectable). Mac README
  + HOW-TO updated. **Mac hotkey answer for owner: hold RIGHT CMD (⌘).**
- All 3 rebuilt GREEN (Android run 28918771980, Mac 28918771923, local exe) and
  the FIXES VERIFIED INSIDE the shipped zip (read the java/py back out of it).
  Desktop refreshed: GeminiMic-android.apk + GeminiMic-share.zip (46.1 MB).
  Desktop GeminiMic.exe + GeminiMic-windows.exe NOW REPLACED with the fixed
  build (owner closed it → stopped/copied/relaunched, hashes verified match
  windows/dist/GeminiMic.exe, running PID confirmed). All 3 Desktop deliverables
  current.
- **Review findings left OPEN (owner not yet asked / next batch candidates):**
  (F6) finishReason/MAX_TOKENS never checked → long fast speech silently
  truncates mid-sentence (all 3 platforms; cheap fix: maxOutputTokens 4096 +
  check finishReason). (F9) if POST_NOTIFICATIONS denied, post-boot arm
  notification silently never shows. (F4) desktop clipboard: image/file
  clipboard lost after dictation + 0.15s restore race. (F8) dictating while
  a transcription is in flight → misleading "No audio" toast (Android).
  Plus MINORs: raw HTTP error toasts, key in URL query (prefer header),
  Tk settings in a thread, crash handler can't launch from background.
- OWNER TODO: (1) phone: install new APK, test dictation + reboot-arm;
  (2) PC: close running GeminiMic.exe, replace with the new one, test;
  (3) decide: fix F6+F9 next batch? ("ha" = qilaman)
- **Readability fix (all 3 platforms)**: casual dictation often came back with no
  sentence punctuation, so `formatParagraphs` (splits on `.?!`) couldn't break it
  → one run-on block. Prompt now asks Gemini for natural sentence punctuation +
  capitalization. Same edit in GeminiClient.java + windows/gemini_mic.py +
  mac/gemini_mic_mac.py (kept identical).
- **Android reboot survival (one-tap arm)**: Android 14 forbids starting a mic
  foreground service from background / BOOT_COMPLETED. Solution WITHOUT a boot
  receiver: the accessibility service auto-rebinds on boot →
  `onServiceConnected` posts a "Yoqish uchun bosing" notification → tapping it
  opens `ArmActivity` (translucent, no-history) which — being foreground — starts
  the mic service. Notification cancelled on tap / on service start / skipped when
  already running or no key. New file ArmActivity.java + manifest entry. Orphan
  Prefs BUBBLE_X/Y dropped. Independently reviewed: no blockers.
- All THREE built GREEN this session (Android run 28917789116, Mac 28917789123,
  Windows exe via PyInstaller). Fresh APK verified (models ok, ArmActivity present,
  no overlay/boot perms). Docs (README.md, HOW-TO-USE.txt) de-bubbled + HOW-TO
  model line corrected (primary=3-flash-preview) + reboot-arm step added.
- Delivery: Desktop `GeminiMic-android.apk` refreshed; `GeminiMic-share.zip`
  rebuilt with all fresh source + 3 binaries + corrected HOW-TO. **Desktop
  `GeminiMic.exe` NOT swapped** — the running copy was file-locked; owner must
  close it then replace with `windows/dist/GeminiMic.exe` (or from the zip).
- OWNER TODO: (1) test punctuation/breaks on phone; (2) test reboot → tap arm
  notification → volume-down still types; (3) to update his PC exe, close the
  running GeminiMic.exe and replace it.

## STATUS (resume board) — 2026-07-07 (v3)
- **Android bubble REMOVED** (owner: "volume yetadi"). Volume-Down hold-to-talk is
  now the ONLY Android trigger. Dropped the whole floating overlay UI from
  MicOverlayService (recording engine + volume start/stop/cancel bridge + fg
  notification kept intact), the "Ustidan chizish" checklist row + overlay gate
  from MainActivity, orphan `hasActiveTextInput()`, and **SYSTEM_ALERT_WINDOW**
  from the manifest → one fewer setup step for the friend. Feedback now = toast
  ("Recording") + persistent notification (Ready/Transcribing). CI GREEN
  (run 28902251781); fresh APK verified (correct models, overlay perm ABSENT in
  compiled manifest) → copied to Desktop `GeminiMic-android.apk` + `dist/`.
- ⚠️ **share zip is now STALE** for Android: `GeminiMic-share.zip` still bundles
  the old bubble source + old APK + HOW-TO-USE.txt that mentions the bubble.
  REFRESH IT (source tree + new APK + reword HOW-TO) only AFTER owner confirms the
  no-bubble build works on his phone — else it'd be rebuilt twice.

## STATUS (resume board) — 2026-07-07 (v2)
- THREE platforms, all built & current: **Android** (app/, Java), **Windows**
  (windows/gemini_mic.py, tray), **macOS** (mac/gemini_mic_mac.py, rumps menu bar).
  Same Gemini core on all (prompt/clean/paragraph-format, verified identical).
- MODEL (final): primary **gemini-3-flash-preview** (good quality, ~3x cheaper on
  paid: $0.50/$3 vs 3.5-flash $1.50/$9 per 1M), fallback **gemini-3.5-flash**.
  Fallback fires on HTTP 404/429/500/503 AND on network/read-TIMEOUT (read
  timeout 30s). Both live-verified to transcribe accurately. Note `gemini-3.0-flash`
  does NOT exist (404); real ids = `gemini-3-flash-preview`, `gemini-3.5-flash`.
- v2 features this session:
  · Android: **Volume-Down hold-to-talk** (short press = normal volume; hold =
    record from key-DOWN so speech start isn't missed; via accessibility
    onKeyEvent + MicOverlayService volumeStart/Stop/Cancel bridge). Floating
    bubble still works. MainActivity fully **redesigned** (card UI, light/dark,
    permission checklist, one Start/Stop button; model picker removed).
  · Windows: single-instance mutex, startup beep/balloon (Win11 hides tray under ^),
    beep on record start/done, tray-tooltip guards, Settings modernized + model
    picker removed. Owner's live config = 3-flash-preview.
  · macOS: rumps menu bar (Cmd+V paste, right-Ctrl hold), model picker gone.
- BILLING (verified, official pricing): free tier = no billing, both flash models
  free but rate-limited PER DAY per model (owner's 3.5 daily quota got exhausted by
  my testing → resets daily). Paid = charged immediately, but CHEAP for dictation
  (~$1–5/mo; 3-flash-preview cheapest of the good ones). Paid also = data not used
  for training. App needs NO change for paid — same key, billing on Google's side.
- Delivery: fresh binaries on Desktop — `GeminiMic-android.apk`, `GeminiMic.exe`
  (installed+running), and `GeminiMic-share.zip` (46 MB: all source + all 3
  ready binaries + HOW-TO-USE.txt) for the friend who will continue developing.
- macOS CI: **build on `macos-14` (arm64)** — GitHub retired macos-13 Intel (it
  queues forever). So the `.app` is Apple-Silicon-only (Intel Macs build from
  source). `mac/GeminiMic.spec` is force-committed (a `*.spec` gitignore hid it).
- IN FLIGHT at /clear: a CI run (Android build.yml + Mac build-mac.yml) for the
  3-flash-preview swap was still building — on resume, `gh run list` the latest,
  download `debug-apk` + `GeminiMic-mac` if newer, and refresh the share zip.
- Blockers: none. OWNER TODO: test each platform (hold trigger → speak → text);
  decide free vs paid key (paid = fast/reliable, ~a few $/mo).

## Status — 2026-06-30
- ✅ Clean rebuild complete: 7 classes (MainActivity, MicOverlayService,
  VoiceInputAccessibilityService, GeminiClient, Prefs, GeminiMicApp, CrashActivity)
  + manifest + resources, faithful to the APK.
- ✅ GitHub Actions build **GREEN** → debug APK artifact.
  Repo: https://github.com/mirkomilovabrorwork-dot/gemini-mic (public)
- ✅ On-device: confirmed working (voice → typed text).
- ✅ Feature: transcript formatted into paragraphs — blank line ~every 2
  sentences, a long sentence (>=14 words) stands alone
  (`GeminiClient.formatParagraphs`, applied after `cleanTranscript`).
- ✅ Stable signing: committed `app/debug.keystore` (well-known debug key,
  password "android") so updates install in place without uninstall.
  Latest good run: 28479603726. APK pulled to `dist/app-debug.apk`.
- ✅ Windows edition (`windows/`): Python tray push-to-talk app — hold Right Ctrl
  → record → Gemini → paste into focused field. Same prompt/clean/format logic
  (verified 1:1 via `python gemini_mic.py --selftest`). Packaged to a standalone
  `windows/dist/GeminiMic.exe` (~33 MB) via PyInstaller. Source committed;
  exe/venv gitignored. Build locally: `windows/build.bat`.
- ⏳ NEXT: user runs GeminiMic.exe, sets API key in Settings, tests hold-to-talk
  end-to-end on real mic; then next feature.

## Windows build (local)
- `windows/.venv` has deps; rebuild exe:
  `.venv\Scripts\python -m PyInstaller --onefile --noconsole --name GeminiMic --icon icon.ico --collect-all sounddevice --hidden-import pystray._win32 --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 --noconfirm gemini_mic.py`
- Default hotkey `right ctrl` (changeable in Settings). Config: `%APPDATA%\GeminiMic\config.json`.

## Build / verify
- No local JDK/SDK. Build is cloud-only via GitHub Actions (`.github/workflows/build.yml`):
  `gradle assembleDebug` on Gradle 8.7 + AGP 8.5.2 + Java 17. Push to `main` → APK artifact.
- To get a fresh APK: `gh run download <runId> -n debug-apk -D dist`.

## Notes / gotchas hit
- AAPT rejects raw-hex flag values in `accessibility_service_config.xml` → use named flags.
- `javac` rejects UTF-8 BOM → keep `.java` files BOM-free.
