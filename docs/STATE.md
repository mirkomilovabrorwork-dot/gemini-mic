STATUS: TELEFON REJIMI qurildi (18cfbde), PC tomoni jonli + Funnel orqali tekshirildi; APK Desktopda, telefonda hali sinalmagan
NEXT: siz - APK o'rnatib, kodni kiritib bitta gap; men - logda 'relay: accepted' + PC ga yozilganini tekshiraman
SIZDAN: 1 | Desktopdagi GeminiMic-android.apk ni telefonga o'rnating, PC kodini kiriting, bitta gap ayting
 Gemini Mic — STATE

_Trigger words: "gemini", "gemini mic". Source of truth for resume._

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
- OWNER (since 2026-10-14): install Desktop `GeminiMic-android.apk`, turn on
  "Matnni PC ga yozish", enter the PC code (Settings -> "Telefon kodi"), tap
  "Tekshirish", dictate one sentence. Reply ishladi/yo'q.
  UZ: Qiling: Desktopdagi GeminiMic-android.apk ni o'rnatib, "Matnni PC ga yozish" ni yoqing, PC kodini kiriting, "Tekshirish", bitta gap ayting | Ko'rasiz: telefonda "PC ga yozildi", matn PC maydoniga tushadi | Nega: telefon rejimi faqat sizning telefoningizda tasdiqlanadi | Vaqt: 2 daqiqa
- ME after his answer: log must show `relay: accepted N chars` + paste; if "PC
  javob bermadi" -> check phone internet (office Wi-Fi) vs mobile data first.
- XM5 on the PC: still digital zeros on every capture path after the 14:57
  reconnect (Hands-Free link half-open). Not fixable without re-pairing the
  headset in Windows Bluetooth settings (owner declined for now). PC dictation
  is effectively phone-only until then; the app still binds XM5 first.
- Open since 10-13, unverified: if calls lose the mic while the app holds it ->
  open the mic only while the hotkey is held.
- Vocabulary list (5 terms) live; "soxta" -> drop thinking budget first;
  clips: last 20 WAVs in %APPDATA%\GeminiMic\clips.
- Two pythonw copies run after each watchdog start (second one ~5 MB; mutex
  should exit it) - harmless so far, not investigated.
- Share-zip handover DONE (owner declared 2026-08-07); a friend's later result
  = NEW input, not this duty reopening.

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
