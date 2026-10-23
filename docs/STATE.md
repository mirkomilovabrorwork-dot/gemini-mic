STATUS: 2026-10-23 17:10 'No transcript returned' on long takes = gemini-3.7-flash (served as 3.8-flash) blockReason=OTHER, intermittent -> all platforms now fall back to 3.5-flash on a block (ce8bd89; Windows LIVE 17:09, Android APK via CI). MICUSB1 primary everywhere (f71d2ab).
NEXT: owner - next dictation with the phone app open: log must show `record stop` and NO `relay: state recording` -> proves MICUSB1 beats the phone; unplug MICUSB1 -> Ctrl must go to the phone. Screen-off test still open. DEFERRED (owner 10-14): PhoneHead seq-tagging + primary-speaker A/B
SIZDAN: 1 | ekran o'chiq sinovi: 5 daqiqa tegmang, keyin Ctrl -> bip keldimi?
 Gemini Mic — STATE

_Trigger words: "gemini mic", "gemini-mic". (bare "gemini" dropped 2026-10-20: it is also the model name and hijacked a system session) Source of truth for resume._

## GOAL (owner's words)
Voice typing that "just works" on BOTH phone and PC: hold a key/mic, speak
mixed Uzbek/English/Russian, the text lands in the focused field — free
(Gemini free tier), no fiddling. Owner shares it with a friend as a zip.
Owner's later recorded refinements (his words, not scope invention):
- 2026-07-29 quality bar: "aytgan so'zimni aytganimdek yozish kerak" — verbatim,
  no word substitution (best measured config = 7/9 on his voice; ceiling and
  every rejected lever documented below).
- 2026-07-29 key strategy: ONE key for simplicity ("1 pulli kalit" choice); the
  "free tier" wording above predates that decision.
- 2026-07-30: dictate through the BT headset when practical ("headphones yoza
  olsa yaxshiroq") — works via the pinned driver path; telephone-grade quality
  caveat stands.

## NEXT STEP (single queue, oldest first)
- DONE 15:47: owner installed the APK, dictated on the phone (volume-down
  hold) -> PC pasted. Log: relay: accepted 22/44/21 chars, "paste: Ctrl+V sent".
  His first attempt failed only because he pressed Ctrl on the PC (PC mic path).
- OPEN (owner 15:48): "PC Ctrl bosganimda telefon yozsin" - PC-triggered phone
  recording. Would need: phone keeps an outbound long-poll/WebSocket to the PC
  (Funnel) from its foreground service; PC key -> "start/stop" push -> phone
  records. Owner 15:50: "Ha, qur" (warned: start lag + Doze). DESIGN (mine):
  phone long-polls GET /cmd?wait=20 via the Funnel from its foreground service;
  PC hotkey -> start/stop/cancel; PC plays the START beep only after the phone
  ACKs "recording" (POST /ack) so the first syllable is safe; text returns via
  the v1 POST; no phone within 45 s -> local mic as today. Battery: a Settings
  button to exempt from battery optimisation + wake lock only while recording.
  Funnel long-poll idle limit: UNVERIFIED (Tailscale docs name no limit; 20 s
  waits + reconnect backoff). Spec: _handoff/2026-10-14-gemini-mic-pc-trigger.md.
- XM5 on the PC: still digital zeros on every capture path after the 14:57
  reconnect (Hands-Free link half-open). Not fixable without re-pairing the
  headset in Windows Bluetooth settings (owner declined for now). PC dictation
  is effectively phone-only until then; the app still binds XM5 first.
- Open since 10-13, unverified: if calls lose the mic while the app holds it ->
  open the mic only while the hotkey is held.
- Vocabulary list (5 terms) live; "soxta" -> drop thinking budget first;
  clips: last 20 WAVs in %APPDATA%\GeminiMic\clips.
- Share-zip handover DONE (owner declared 2026-08-07); a friend's later result
  = NEW input, not this duty reopening.

## 2026-10-23 17:10 - "No transcript returned" (owner screenshot) -> FIXED on all platforms
- 17:02 (22 s) and 17:03 (35 s) takes: HTTP 200, no candidates, promptFeedback.blockReason=OTHER,
  modelVersion "gemini-3.8-flash" (the 3.7-flash alias), serviceTier standard (= paid tier; a block is
  not a quota error). Replay: first replay blocked both, a later replay of one passed -> intermittent.
  3.5-flash and 3-flash-preview transcribed both clips correctly. Google docs: OTHER = input blocked for
  a non-safety reason; no documented cause (forum anecdote: non-English words near a filtered term).
- ce8bd89: Windows (log blockReason, status 0 -> FALLBACK_MODEL; test_block_fallback, mutant caught),
  Android (isBlocked -> fallback post), Mac (status 0). Windows restarted 17:09:52 on MICUSB1.
- Residual risk: if BOTH models block the same clip the error still shows (not seen yet).
  If blocks keep appearing (count `blockReason=` in the log), consider 3-flash-preview as primary.

## 2026-10-23 16:30 - owner: "Telegram, hamma yerda tashqi mikrofon asosiy" -> DONE (Windows side live)
- Owner declined the "only my voice" filter for now (16:10: "hozircha kerak emas"); options given:
  Gemini prompt / lower gain / Krisp BVC (pricing unverified) / mic placement.
- MICUSB1 was already the Windows default (console+multimedia+communications) at 16:15; the gap is
  Windows moving the default to a BT headset on connect. f71d2ab: windows_default_mic re-asserted every
  5 s while idle from _prefer_mic_watch via pycaw IPolicyConfig (capture endpoint only - MICUSB1 also has
  a Speakers endpoint, untouched). Bug found live: pycaw GetEndpointDataFlow returns the string
  "eCapture", not the enum -> first build never matched; fixed before commit.
- Live x2: default forced to the AMD array -> app log "windows default mic -> Microphone (MICUSB1)
  (all roles)" within 14-16 s, all 3 roles back. GLM review folded (COM init once; after the recording
  guard). Undo: set windows_default_mic "" in config.json (or Settings) + restart.
- Telegram Desktop (running) keeps its OWN input choice: follows Windows only if set to "Default".

## 2026-10-23 15:10 - owner: "tashqi mikrofon birinchi, u bo'lmasagina telefon" -> DONE (lab + 1 live take)
- MICUSB1 plugged in (WASAPI 15). Config: input_device "MICUSB1|Microphone Array|WH-1000XM5|USB MIC",
  new key phone_unless_mic "MICUSB1" (DEFAULT_CONFIG "" = old behaviour, friend's zip unaffected).
- 0281bce: preferred_mic_live() = stream open on that device AND a block < 1 s ago; _on_press skips
  the phone path when it is true. Unplug -> stream dies -> watch/auto-heal moves to the next mic, and
  preferred_mic_live() is False -> phone again. _prefer_mic_watch already switches BACK to MICUSB1
  within ~5-60 s of it returning.
- GLM review (read-only, tree unchanged): F1 "stream.device None on system default" DISPROVED
  (sounddevice resolves it to index 1 = MICUSB1, probed); F2 test misnamed -> renamed. Known gap:
  a plugged mic that delivers pure silence still wins over the phone ("Ovoz eshitilmadi").
- Live: app restarted 15:04:41 on MICUSB1 raw; 15:06:40 take rms 871 @6x, 3 s, verbatim.

## 2026-10-14 19:15 - "two pythonw copies" EXPLAINED (not a bug, closed)
- PID 20456 (1-5 MB) = `windows\.venv\Scripts\pythonw.exe` = the uv venv LAUNCHER SHIM;
  it spawns the real interpreter `%APPDATA%\uv\python\cpython-3.11.15\pythonw.exe
  gemini_mic.py` (PID 30516, 19-85 MB, parent = the shim) and waits. One app instance;
  the mutex never had a second copy to exit. Nothing to fix; killing either kills both.

## 2026-10-14 19:10 — test log leak FIXED (429dc2f)
- The 19:03:59-19:04:05 "relay: state recording #1 / ack stopped #2 (cancel)" lines in the
  live log were test_phone_session's server threads outliving tearDown (seq #1/#2 match the
  test, the live app was at #0) - NOT an owner take. Fix: `GEMINI_MIC_LOG_PATH` env override
  (LOG_PATH read at import) + each test sets it to %TEMP%\gemini_mic_test.log before import.
  Proved: override -> probe line lands in the temp file; 3 test files rerun -> +0 live lines.

## 2026-10-14 19:05 — 3.7 live; "Model band" x3 = network blip, not the model; log patch
- Log 18:48:43 / 18:49:14 / 18:49:26: `calling model=gemini-3.7-flash` -> `GeminiError("Model band...")`
  in the SAME second = requests.RequestException (connection, not the 15/30 s timeout); the
  silent 3.5-flash fallback failed too. 18:50:18 take OK (4 s, "Slash clear", pasted). Probe
  19:00: text-only POST to 3.7-flash -> HTTP 200 in 4.2 s. Verdict: ~1 min network blip
  (unverified which hop - DNS/Wi-Fi; the real exception was NOT logged).
- 5319e30 (mine, 2 lines): log the exception class+message on a request failure and a
  `gemini: fallback -> model=...` line. 34 tests green (3 files, run directly with
  windows/.venv python; `pytest` is not installed in that venv). App restarted 19:01 via
  watchdog; phone poller reconnected 19:01:44 (phone awake at that moment).
- APK with the 3.7 default on Desktop (18:42, run 38573911813 green) - owner has not said
  whether he re-installed it; the phone's own takes still use whatever model the installed
  build defaults to (prefs never write "model").

## 2026-10-14 18:45 — owner: "gemini micni ham 3.7ga o'tkaz" -> DONE
- Model gemini-3-flash-preview -> gemini-3.7-flash in Windows DEFAULT_CONFIG + live
  config.json (app restarted 18:41), Android Prefs default (MODEL_BETTER + getString
  fallback; the app never writes the "model" key, so the default applies on install),
  Mac default. Hukm given: shubhali - 13:10 A/B on his clips: 3.7-flash tied in word errors
  (19 vs 20) but ~2x slower (4.3 s vs 2.2 s); his call, reversible via Settings/model. Owner's reason (18:50): "3.7 mixed language uchun
  yaxshi natija beryapti" - his wider experience beats our 2-clip A/B; re-measure on the
  next ~10 saved clips (clips dir) before ever arguing it back.
  New APK from CI (run 38573911813) -> Desktop once green. Verify live: next dictation's
  `gemini: calling model=gemini-3.7-flash` + latency.

## 2026-10-14 18:40 — v2 PROVEN LIVE by the owner; ack window widened
- Owner installed the APK (196adcf Android side), 18:11-18:33: 4 PC-hotkey sessions all
  went through the phone - log: `state recording #n -> phone` -> `ack recording` ~2 s
  later (log second resolution), stop -> `ack stopped` -> `accepted N chars` -> paste
  3-4 s after release. Owner: "hammasi ishladi". One `phone: no text within 40s` for a
  take that produced no text (harmless, logged).
- 2 s ack round trip sat ON the 2.0 s fallback edge -> PHONE_ACK_SEC 3.5 (commit after
  9592ca1), app restarted 18:37. Memory: feedback_timeout_anchor (measure, then x1.5-2).
- Owner asked: works with the phone screen off? Answered: designed to (foreground service,
  battery exemption, wake lock during recording) but UNTESTED; Doze may stall the first
  press after a long idle. Duty: 5-min screen-off test.
  UZ: Qiling: telefon ekranini o'chirib 5 daqiqa tegmang, keyin PC da Ctrl bosib bip kuting | Ko'rasiz: bip 2-3 s ichida kelsa ekran o'chiq ham ishlaydi; kelmasa ayting | Nega: Android uxlab qolgan telefonda fon aloqani kechiktirishi mumkin - buni faqat real telefon ko'rsatadi | Vaqt: 6 daqiqa

## 2026-10-14 18:05 — pass 3 + two review one-liners live; waiting on the phone-Ctrl test
- ab1f71b (doer opus): callback stores un-gained blocks; gain_for = min(6, 28000/peak) applied
  once at stop (WAV + clip); NEW-2 (desired state never stays "recording"; stop sent even if
  the tray update raises) and NEW-1 (PhoneHead placeholder keeps head-before-tail at the 60 s
  handover, 40 s cap). 35 tests x4 green.
- Judge re-check: both fixed; FIX-FIRST on a gate regression (gain from the loudest sample -
  a pre-roll key click lowered it and rejected quiet desk-mic speech). My fix 1496c86: the
  gate sees un-gained audio x RAW_GAIN as unclipped floats; proved: speech rms 40 + 12000
  click -> accepted (was rejected), room noise -> rejected. Judge: fixed, but the gate input
  skipped the 1 kHz start-beep notch -> beep leak alone passed. 974852f: notch applied to the
  gate input (judge: SHIP); the empty-clip log guard it announced was NOT in it - landed
  as 9592ca1. App restarted 18:06 on 9592ca1. Known, logged, shippable:
  PhoneHead fills with ANY phone text (a head later than 40 s or a new short take within the
  window can paste out of order).
- Owner 17:42 laptop dictation (pre-fix 6x): rms 8320, verbatim. Model = gemini-3-flash-preview
  (owner asked 17:55; answered from the log + 13:10 A/B).
- Side effect noticed: the unit suite writes "relay: rejected ..." lines into the REAL app
  log (%APPDATA%\GeminiMic\log.txt) - harmless, but confusing when reading the log; worth a
  LOG_PATH override in tests later.

## 2026-10-14 17:25 — laptop raw path works but CLIPS; re-review found 2 more
- Owner 17:19-17:20, laptop array RAW 6x: 4 dictations verbatim near the mic ("ishladi"),
  but clips rms 5366-11895, peak 32768, 0.05-2.49 % samples clipped -> the 6x gain tuned
  for USB MIC PRO saturates the array. Owner: "uzoqdan xato" - told him: far-field is
  physics, only closeness (phone) helps; the clipping is fixable. Pass 3 = callback stores
  un-gained blocks, gain = min(6, 28000/peak) applied once at stop (gate + WAV).
- The raw-zero self-heal (F11) did NOT misfire on the array (kept raw, correct).
- Judge re-review of 196adcf: all 11 fixed; FIX-FIRST on NEW-2 (desired state can stay
  "recording" after a session -> phantom 60 s take on the next poller start; stop sent
  after set_state which can raise) and NEW-1 (60 s handover can paste tail before head).
  Both in pass 3. Then: re-check -> restart -> CI -> APK -> owner.

## 2026-10-14 16:50 — v2 built (c9b9ac1), blind review FIX-FIRST; laptop mic live; raw-zero puzzle
- v2 PC-trigger commit c9b9ac1 (doer opus, 16 tests, e2e sim). CI 38555952314 GREEN (APK not
  delivered - fixes first). Blind judge (opus): FIX-FIRST, 10 findings; proven: F1 local+phone
  record at once after a 60 s rollover / auto-repeat (release stops only the phone -> second
  paste); F2 a lost stop lets the phone record to its 60 s cap and the PC pastes it (oldest
  parked poll wins; no ack for stop); F4 flaky test (15.6 ms monotonic tick). Fix pass = desired-
  state protocol on /cmd (state+seq, phone reconciles, acks "stopped"), fresh-press-only phone
  path, release also stops local, wake lock through the upload, phone_seen=-inf, 150 ms hold.
  Fix doer opus running on `_handoff/2026-10-14-gemini-mic-pc-trigger-fixes.md`.
- Laptop array, owner 16:43 (app on shared path, array first, raw off): 2 dictations verbatim,
  rms 665/986, 3 s. Owner: "norm ishlayapti; shovqin/hamkasblar ovozini bloklash + balandroq".
  Answered: Windows cannot block other people's speech (Voice Clarity = noise only, 12:40);
  level is fine (rms > 500); only closeness helps -> phone mode is the real answer. Cheap lever
  offered (Hukm shubhali): prompt "primary speaker only" - try after v2 lands.
- Raw-zero puzzle: 15:39/15:40 app clips on the array RAW were rms=2; my 2 s sd.rec probe at
  16:38 also gave RAW max=1 vs SHARED max=15. But a callback-stream probe at 16:47 showed raw
  blocks: first callback at 0.56 s, first ~0.2 s zero, then real audio (max 700-1100). So raw
  on the array is NOT always dead; the 15:39 zeros remain unexplained (maybe the stream opened
  while the XM5 fallback was mid-switch). Self-heal commit 7490501 (doer opus) is correct in
  shape but its 0.6 s window is shorter than the 0.56 s first-block latency and would misjudge
  warm-up zeros -> F11 in the fix spec (wait for first block, skip 0.3 s, judge 0.5 s).
  Config now: array first, raw ON (app restarted 16:48:12, raw stream on the array).
- Two pythonw copies again after each watchdog start (second ~5 MB) - still uninvestigated.

## 2026-10-14 15:35 — PHONE MODE BUILT, PC side LIVE, waiting on the phone test
- Commits aca34d3 (doer opus, spec `_handoff/2026-10-14-gemini-mic-phone-relay.md`)
  + 18cfbde (my review fold: token 8 -> 12 hex, lockout 60 s after 5 wrong tokens
  - the automated security review flagged 32-bit entropy on a public endpoint) +
  CI fix (setup-android default pulled the retired 'tools' package: EVERY Android
  build since at least 08:57 today had failed at SDK setup - pinned packages,
  run 38550162134 GREEN). Pushed (standing yes).
- LIVE PROOF (app restarted 15:29:51, "relay: listening on 127.0.0.1:5588"):
  `GET https://data365.taildef23b.ts.net/mic/ping` -> {"ok":true}; POST wrong token
  -> 403 and "relay: rejected token" in the log. Not yet proven: a real phone
  POST pasting into a PC field (needs the phone), Android code on a real device.
- Phone code (relay_token) is in Settings ("Telefon kodi: ...", button "Yangi kod").
  APK: Desktop `GeminiMic-android.apk` (38 KB, CI artifact) + dist/apk-new/.
  Phone setup: install -> Sozlamalar -> "Matnni PC ga yozish" ON -> PC manzil
  (prefilled) -> PC kodi -> "Tekshirish" should toast "PC ulandi" -> dictate.
- Xavf: Funnel = public internet endpoint guarded only by the 12-char code +
  lockout; GET /ping is open (returns no data). If the PC app is closed the phone
  falls back to typing on the phone + clipboard. XM5 on PC stays bound as mic
  (still zeros until the headset is re-paired) - PC-side dictation is effectively
  phone-only until then.
  UZ: Qiling: Desktopdagi GeminiMic-android.apk ni telefonga o'rnating, Sozlamalarda "Matnni PC ga yozish" ni yoqib, PC kodini kiriting, "Tekshirish" bosing, keyin bitta gap ayting | Ko'rasiz: telefonda "PC ga yozildi" chiqadi va matn PC dagi ochiq maydonga tushadi | Nega: bu rejim shu uchun qurildi; faqat sizning telefoningiz buni tasdiqlay oladi | Vaqt: 2 daqiqa

## 2026-10-14 15:10 — XM5 dead on PC -> owner chose PHONE MODE; relay being built
- Owner's 3 XM5 dictations 14:58-15:03 on the raw path: rms=2 (digital zero, 8-11 s).
  Probed with the app STOPPED: XM5 WASAPI raw / shared+convert / MME all rms=0 max=1;
  Headset render endpoint absent from WASAPI enumeration -> the Hands-Free (SCO) link
  to this PC is not carrying audio after the 14:57 reconnect. Phone BT was OFF (owner),
  so not multipoint. PnP toggle of "WH-1000XM5 Hands-Free AG" needs admin (failed).
  Owner 15:08: "Telefon rejimini qur" (declined XM5 power-cycle).
- DESIGN (Men tanladim, reversible): Android app keeps recording/transcribing on the
  phone mic, then POSTs {token,text} over HTTPS to the PC's EXISTING Tailscale Funnel
  `https://data365.taildef23b.ts.net/mic` -> `127.0.0.1:5588` where a listener thread in
  the Windows app enqueues a paste-only job into the existing FIFO -> paste_text. Why
  Funnel and not LAN: office Wi-Fi is the Windows "Public" profile (inbound to pythonw
  blocked without an admin firewall rule) and may isolate clients; the phone is NOT on
  the tailnet (status: only data365 + bunyods-mac-mini); Funnel is already on for
  data365 (`/` -> 127.0.0.1:3000, the Jarvis bridge). Security: 8-hex token generated
  by the Windows app, shown in Settings, typed once on the phone; listener binds
  127.0.0.1 only; GET /ping is tokenless and returns no data. Fallback: if the PC does
  not answer, the phone types the text locally as before + clipboard.
  Spec: `D:/vibecoding/_handoff/2026-10-14-gemini-mic-phone-relay.md` (doer opus).
- INCIDENT 15:06: my `tailscale serve --bg --set-path /mic ...` ran under Git Bash,
  which mangled `/mic` into `/C:/Program Files/Git/mic` (MSYS path conversion), and the
  serve status afterwards printed data365 as "(tailnet only)" - Funnel on data365 MAY
  have been switched off (unverified: every further tailscale call, even `funnel status`,
  was denied by the permission classifier "External Ingress Tunnel"). Jarvis bridge on
  :3000 may be unreachable from the internet until fixed.
  RESOLVED 15:20 by the owner (4 commands): data365 Funnel on, `/` -> 3000 and
  `/mic` -> 5588, both "Available on the internet". Probed: Funnel STRIPS the prefix -
  `/mic/ping` arrives at the backend as `/ping`, `/mic` as `/`.
- Side fact: two pythonw copies of the app run (3192 at 5 MB = the watchdog's second
  start that the mutex should have exited; harmless so far, not investigated).

## 2026-10-14 — OWNER DIRECTIVE: "yo tel yo XM5 mic orqali ideal yechim"
- Desk mic (USB MIC PRO) is OUT of the daily path (owner 14:25 + this). Two
  candidates only: (A) XM5 straight on the PC — zero extra parts, ceiling =
  BT Hands-Free 16 kHz channel + in-headset NR (not fixable from Windows);
  (B) phone-grade capture for PC dictation — our Android app records on the
  phone mic (44.1 kHz, "telda yaxshi"), transcribes, and relays the TEXT to the
  Windows app over LAN which pastes it (no audio bridge like WO Mic). Cost of
  B: a LAN receiver in the Windows app + "send to PC" in the Android app; needs
  same Wi-Fi, phone awake, press on the phone. Decision rule: the pending 30 s
  XM5 "Ha..." test on the raw path (3cfe19d) decides — acceptable -> A is the
  ideal, stop; still mangled -> build B. Log 14:27:36 shows only a 0.12 s
  press (rejected: too short); no real XM5 dictation on the raw path yet.
  Untested idea C (unverified): a USB LE-Audio dongle could give the XM5 a
  wideband LC3 mic on Windows (this PC's MT7921 has no LE Audio endpoint).

## 2026-10-14 14:20 — "birinchi gap xato" ROOT CAUSE = Windows mic-effects gate eats the first syllable
- Owner 14:05: first seconds / first word wrong ("Tashqi" -> "Boshqa", "Ha"
  dropped on XM5). Clip envelopes: DIGITAL ZERO floor (0-1) for 1-2 s, then
  40 -> 446 within 50 ms. Room tone with the app stopped (scratchpad
  gate_probe.py): MME rms 346 / WASAPI default 354 / WASAPI RAW 64 - the
  endpoint's APO chain (Realtek "VocaEffectPack" entries on USB MIC PRO AND
  on the XM5 Hands-Free endpoint) applies ~6x gain and a silence gate.
  Onset A/B (onset_ab.py, two simultaneous WASAPI streams, room speech):
  APO path ramps 0 -> 3,20,41,58,70,93,136... over ~150 ms (first 100 ms =
  50% of steady); RAW path is flat from the first 10 ms (112%). That ramp IS
  the lost first syllable. Not the preroll (clips show 1-2 s of silence
  before speech), not the model.
- FIX SHIPPED 3b1d9e1 (doer opus + my gate edit), LIVE 14:18: mic opens via
  WASAPI eStreamOptionRaw (bypasses every APO), RAW_GAIN 6x in the callback,
  WASAPI candidate first per fragment, config `raw_capture` (default true)
  = off switch. Doer's catch: the raw path has NO silence gate, so room noise
  after gain (~350) beat the fixed has_speech threshold (120) -> an empty
  press would send teammates' chatter to Gemini. Added VOICE_FLOOR_RATIO 2.5:
  voice must clear max(120, 2.5 x the clip's 20th-percentile window rms).
  Checks: synthetic room noise rms350 -> rejected, +0.5 s speech -> accepted,
  the 4 latest real clips -> accepted. Log line now carries floor=.
  Log: "mic stream opened on Microphone (USB MIC PRO) (WASAPI raw, gain 6x,
  ...)". Blind review (fable judge) running on `git diff 2f07a58`.
  OWNER PROOF 14:19: "Ha, endi ishlayapti." - the first word is in. Clip
  floors on the raw path are ~290-460 (room, x6), never 0 -> no gate ramp.
- Gate tuning 68ff195: a real 2.25 s dictation was rejected at ratio 2.5
  (voiced 2/3, floor 458, threshold 1146). Measured room-only raw clip: p20
  290, chatter bursts to 954 (3.3x) in <=2 windows; owner's speech 3-6x his
  floor. VOICE_FLOOR_RATIO -> 2.0; checks: room-burst clip rejected, owner
  clip shape accepted. If he still gets "Ovoz eshitilmadi" on short quiet
  phrases, next knob = MIN_VOICED_WINDOWS 3 -> 2 (but that readmits bursts).
- BLIND REVIEW (fable judge) on the raw-capture diff: 5a FAIL - the clip-own
  20th percentile IS speech on an all-speech clip (short phrase, chain tail)
  -> 15/20 real clips cut to their loudest 1.5 s were rejected. FIX 3cfe19d:
  `room_floor` = 20th percentile of the idle ring blocks BEFORE the pre-roll,
  captured at key press; has_speech takes min(clip p20, room_floor). Checks:
  all-speech 1.5 s shape accepted (was rejected), room-burst and flat-room
  clips rejected, MME-style click rejected. Loudest-cut sweep now 12/20 -
  the 8 misses are OLD low-level MME/XM5 clips (speech rms 150-400, below
  2x a 300 floor); on today's raw path his speech is 1300-2600 vs floor
  ~300-460, so they pass. Judge's other notes: raw_capture=false does not
  roll back the gate change (true; the floor is ~0 on MME so threshold stays
  120); XM5 WASAPI raw untested; beep bleed at 6x unverified (notched).
- Owner 14:25: "telefon mic va headphone qulay, tashqi mic qulay emas" ->
  XM5 is the real daily mic. XM5 reconnected 14:27: app opened it RAW
  ("mic stream opened on Headset (WH-1000XM5) (WASAPI raw, gain 6x...)").
  AWAITING his first XM5 dictation on the raw path (first word + level).
  Zero-code alternative (owner's hands, not needed if the fix lands): Sound
  settings -> USB MIC PRO -> Audio enhancements OFF (HKLM write needs admin,
  so I cannot flip it).

_Older entries (2026-07 .. 2026-10-14 14:05) moved to docs/STATE_ARCHIVE.md._

## DECISIONS (owner one-tap answers - auto-appended; a decided question is never re-asked)
- 2026-10-14 [Telefon] Telefonda aynan nima bo'ldi? -> **hech qanday xabar yoq**
- 2026-10-14 [APK holati] Telefon ilovasining Sozlamalarida "Matnni PC ga yozish" degan tugma bormi va yoqilganmi? -> **qara telda ovoz pasaytirish tugmani bosmadim komputerda ctrl bosdim, telda komputer ulanishi bor halos**
- 2026-10-14 [Ctrl→telefon] "PC da Ctrl bossam telefon yozsin" rejimini quramizmi? -> **Ha, qur**
- 2026-10-14 [Ekran o'chiq] Ekran o'chiq sinovi: telefonni 5 daqiqa tegmay, keyin PC da Ctrl bossangiz bip keldimi? -> **Hali sinamadim**
- 2026-10-14 [Asosiy ovoz] Hamkasblar ovozi aralashganda modelga "faqat asosiy gapiruvchini yoz" deb aytib sinaymizmi? -> **Keyinroq (tavsiya)**
- 2026-10-14 [Uzun gap] 60 soniyadan uzun gapda matn tartibi buzilishi mumkin. Sizning gaplaringiz 2-4 soniya. Tuzataymi? -> **Keyinroq (tavsiya)**
