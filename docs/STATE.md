STATUS: 11-08 20:15 net-loss retry, model-answer guard, idle-only restart - app restarted
NEXT: siz - use it; tell me if any take goes missing (retry + guard are lab-only)
SIZDAN: 2 | delete script: run it, type yes
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

## 2026-11-08 22:00 - USB-C EarPods
- config input_device now "EarPods|MICUSB1|USB MIC|Microphone Array|WH-1000XM5" (owner: plugged mic/headset wins, else laptop). 1 live take 22:00: text exact, rms 799 at max gain 6x (laptop ~2000) - quiet but clean.
- Output default set to WH-1000XM5 via IPolicyConfig (scratchpad setdef.ps1); EarPods capture endpoint is 100% with 0..0 dB range - no system gain exists. Quiet-speech errors: re-run ungated 4 clips -> no consistent gain; level is not the cause (Gemini level-invariant), source SNR is.
- My 2-mic parallel MME test script garbled audio (Gemini hallucinated) - don't reuse; test via the app itself.

## 2026-11-08 20:15 - lost takes, chime, net outage, restart cut (5583d18 and earlier)
- Mic: any live mic ranked above the current one wins (396f0d1). TickTick chime muted 89% -> gate guard 0.7 (4f1ddf1).
- Slow/stuck call: read timeout 15+0.2*s; blue clipboard badge when no paste target (2929791, 472ea34).
- Net outage 20:01-20:03 lost 2 takes -> retry every 20 s for 15 min, text to clipboard (5583d18).
- 2.8 s near-silent take came back as a model answer -> drop > 30 chars/s + 30 (5583d18).
- MY MISTAKE: blind restarts at 19:58/19:59 cut 2 takes. RULE: restart ONLY via windows/restart_when_idle.ps1 (reads state.txt).
- 19:47 take (clipboard) re-transcribed from clips/20261108-194610.wav and given to owner.
- lab-only: retry-later and the answer guard not yet exercised live.

## 2026-11-08 19:00 - "tezlat", lost 144 s take, mic choice
- Cause: 144 s take lost 18:32 - 4.6 MB WAV upload > 15 s connect timeout (write timeout) on every step;
  both 2.5-flash fallbacks dead (Google 404 "no longer available", OpenRouter guardrail 404).
- Fix: audio sent as MP3 48 kbps (lameenc, 5x smaller); A/B 5 clips same text, 63 s take 14.2 -> 4.8 s;
  upload timeout scales with length; fallback = gemini-3.8-flash (OR 200 checked); with an OpenRouter key
  Google (free, 429 most of the time) is only the last resort. Live: lost 145 s clip -> 13.7 s, 6 s clip -> 3.3 s.
- Mic: XM5 dropped 18:10; owner in a quiet room -> order now Microphone Array|MICUSB1|WH-1000XM5 (full-band beats BT 16 kHz).
- Thinking (reasoning 1024) kept: it is the context-correction step (4.7 -> 3.7% letter errors), ~1 s.

## 2026-11-08 18:00 - owner's 4 asks (beep, long speech split, slow, clipboard) + "har doim ishlashi shart"
- Causes (log 11-05..11-08): AUTO_STOP_SEC=60 rolled long takes into pieces (16 rollovers); Google free key 429 on 157/209 calls,
  each take waited for it (median 1 s, max 31 s); 2 takes lost today when Google AND OpenRouter failed (no 3rd step).
- Built by GLM (2 handoffs in _handoff/2026-11-08-*), reviewed by me: AUTO_STOP 300 s, read timeout scales with length,
  max tokens 8192; Google skipped 10 min after a 429; chain Google -> OR same model -> OR 2.5-flash -> Google 2.5-flash.
  Start beep removed (owner chose on-screen badge): red "Yozilyapti" / green "Matnga aylanmoqda" pill top-center, no focus.
  Tests 61 pass. Live: replay 174814 -> 6.0 s (429 path) then 2.8 s (Google skipped). Badge screenshot shows it. App restarted 17:51.
- Lab-only: a real 5-min take; OR 2.5-flash step live. Context step cost: ~$0.003/take on OpenRouter (reasoning 1024 = most of it),
  OR total this week $3.31 shared with Meet; it bought 4.7% -> 3.7% letter errors for +1 s, kept.
- Clipboard checked: field confirmed -> old clipboard restored; 13/214 had no confirmed field (Electron) -> text stays in clipboard.
- Phone for "only my voice": owner chose not now (distance, not the phone, removes other voices; MICUSB1 close = 0/8 leaks).

## 2026-11-07 21:06 - owner: "gemini micni headphonega otkaz" + "ovozi 100foiz"
- xm5_trial.py on: input_device WH-1000XM5 first, XM5 mic level 100%; app restarted, log 21:06:09 'mic stream opened on Headset (WH-1000XM5)'. Back: python windows/xm5_trial.py off. No take after the switch yet.

## 2026-11-07 - blind review of clearance gate + delete script (Gemini 3.8 flash via agy, read-only)
- Gate (recording_clearance.py): no finding - fail-closed on missing/bad registry, empty list, by sha256 not name. Test 12/12.
- delete_vendor_copies.py fixed: (1) real host refuses when stdin is not a terminal (piped "yes" = the 11-06 incident path);
  (2) only HTTP 200 ids are deleted (500/timeout used to be queued). Verified: piped run -> exit 2 before key/network;
  local stub: 500 id kept, 200 id deleted. Real host never called.
- Script is git-excluded (.git/info/exclude); backup copy (not git, sha256 same): C:/Users/mirko/AppData/Roaming/GeminiMic/backup/delete_vendor_copies.2026-11-07.py

## 2026-11-06 23:20 - clearance gate built; ElevenLabs copies deleted by accident
- tools/recording_clearance.py + docs/recording_clearance.json + must-fail test in gate; diar/compare.py now calls it. Ad hoc scripts can still skip it; agent can write a human name; a hook is System's job.
- INCIDENT: doer's test passed the real host and "yes" to tools/delete_vendor_copies.py with the real key. All 4 ids now 404 (abror x2, Abduazim, Azimjon), control id 200. Order was "delete nothing"; Abduazim and Azimjon were the owner's choice. Irreversible; local outputs intact. Script fixed, stub tests pass; real delete path never run on purpose.

## 2026-11-06 22:50 - speaker test result (full: shared notes speaker-separation-results-2026-11-06.md)
- One 21-min 3-person Meet recording, truth = Meet's lit tile from video (813 of 1283 s readable, 20/24 frames agreed). Error with gaps counted: Gemini told 3 = 22.4, Scribe auto 26.9, Gemini+Scribe 31-35. Short turns wrong 33-60%. No method kept all 3 people.
- Recommendation: stay on Gemini, pass the speaker count; future Meet: trial per-person audio bot (Recall $0.65/hour). Gemini debate rejected the stitch, 1 round.
- Gemini times drift, median 6.5 s, max 56 s. Word error not measured. ElevenLabs key has about 440 credits left. Local audio copies deleted; Mac originals untouched.

## 2026-11-06 - how foreign recorders separate speakers (Jarvis order; full note in shared notes, how-foreign-recorders-separate-speakers-2026-11-06.md)
- Leaders take the speaker from the call: own audio per person (Recall, $0.65/hour, preview-only official Meet route), lit Meet tile (Vexa code read), mic vs system (Granola). Audio guessing is only the fallback.
- Room and phone: no magic anywhere, generic labels then human rename. One device shared by several people cannot be split by any of them. No Uzbek accuracy figure exists.
- For us: old Meet recordings = read the lit tile from the video ($0, days, estimate); phone/room = audio only + attendee names; bot only for future Meet calls. MeetGeek publishes no method.
- AS recordings have one mixed track (L=R on 5 files). Lit-tile truth is being measured on abror-57450491; it cannot grade itself, a human sample is needed for its own error.
- Vendor facts for Otter, Read.ai, Fathom, Fireflies, tl;dv, MeetGeek, Krisp are search snippets only.

## 2026-11-06 15:25 - takeover from the old account's 2 sessions (read tails + summaries; no code touched)
- Session 4f66a58e (only my voice + accurate text) ended 11-05 01:27 asking 3.8-flash ha/yo'q. CLOSED, not by the owner: commander
  picked 3.8 at 13:10, then back to 3-flash at 15:07 (Google failed 6/6). No answer is owed.
- Its "two missing transcripts" (owner 01:16 "ASAP") WERE delivered in chat 01:17 (clips 01:11, 01:12; doubtful name "Pilos AI" flagged).
- Session 7ab10fa6 (quiet speech, other voices, XM5) ended 11-05 15:07 waiting for new takes -> they now exist, measured below.
- Log since restart 11-05 15:06:50 (%APPDATA%\GeminiMic\log.txt): 15 takes -> 12 pasted, stop-to-text median 5 s, max 9 s (51 s take).
  Google 5, OpenRouter 7 + 1 empty: free key 429 from 17:24 to 20:05 on 11-05, Google direct again 11-06 14:33. Leading '...': 0.
  3 takes without text, all <= 2.4 s near room floor: 172417 + 172418 (gate rejected, loudest 531-551 < threshold ~600), 200415 (model
  said no speech). Replay without gate gave long sentences that cannot fit 2 s = invented, so NO proof of lost speech (~$0.002).
- OpenRouter key: this week $2.51, today $0.01, no limit set. It is the Meet app's key, so the total is shared with Meet.
- Mic stream self-healed twice (11-05 17:40, 11-06 15:11, reopened on MICUSB1), no take lost. Not checked: the owner's own view since 11-05 15:07.
- Stray empty untracked gemini_mic.py in repo root (0 bytes, 11-05 00:52): left in place, safe to delete on his word.

## 2026-11-05 15:07 - back to the desk mic and 3-flash (commander decision, "Men tanladim")
- xm5_trial.py off -> input_device MICUSB1 first again; config "model" -> gemini-3-flash-preview (3.8 failed 6/6 on Google).
- App restarted 15:06:50 on MICUSB1. Replay of real take 125227 with OpenRouter OFF (no fallback possible): 2.9 s and 2.3 s, text right.
- RETRY 3.8 LATER (one line): config "model": "gemini-3.8-flash" + restart.

## 2026-11-05 15:05 - XM5 trial result (6 takes 14:59-15:01, talker 1-2 m)
- Foreign words in pasted text: XM5 0/6 (colleague faint in 2/6, e.g. 150034 0-2 s "Men buni qanday qilib...", not in text);
  MICUSB1 after the 12:42 move 0/8 (faint 7/8). His "boshqa VKP" = his own "boshqa gap" mis-heard, not a leak.
- Own-word errors on XM5 (16 kHz hands-free): 'Atrofdagilar gapiryapti, qalay bo'lyapti' -> 'Hamma gapirib, ishlayapti,
  qayerda bilasiz'; 'gap' -> 'VKP'; ~9/75 words (reference = 3-flash diarization, scratchpad diar_xm5.json, not ground truth).
- SLOW is not the XM5: Google gemini-3.8-flash failed 6/6 (503 after 5-26 s or ReadTimeout 30 s), OpenRouter then 3-5 s;
  takes run one after another, so waits stack (145915: stop 14:59:15 -> text 15:00:11 = 56 s).
- BEEP late: PlaySound on the XM5 in hands-free mode took 0.86-0.90 s (0.5 s silence lead + ~0.3 s output) vs 0.30 s with
  no lead. The lead was for A2DP sleep (6c96c56); an always-open headset mic keeps the link awake, so it only adds delay.
- First take 145904 went to 'Quick settings' (he was clicking Bluetooth): kept in clipboard, not pasted.

## 2026-11-05 13:26 - XM5 mic trial prepared (owner: "5-10 sm dan gapirsam ham tashqi shovqin ... XM5 ni o'zida mikrofon bor-ku")
- windows/xm5_trial.py: `on` = XM5 first in input_device (falls back to MICUSB1 when the headset is off), XM5 capture
  level -> 100 % + unmute, app restarted; `off` = config restored from config.json.before_xm5, restarted.
  Round trip tested live 13:24-13:25: app back on MICUSB1, config byte-identical. XM5 itself lab-only: it is paired but
  Unplugged (not connected to the PC), so its level and peak could not be read now.
- input_device picks the app's mic (windows_default_mic only forces the Windows default) -> the switch edits input_device.
- RAW_GAIN: no change. Gain is linear and per clip (min(6x, 28000/peak)): it lifts his voice and the room equally, so it
  cannot let room voices back in relative terms; a louder XM5 just gets a lower gain. XM5 peak shows per take in the log.
- Not on by default: an open headset mic forces BT hands-free, music on the XM5 drops to phone quality.
- History to weigh: XM5 on PC gave digital zeros 08-03/10-14 until re-paired; raw->shared fallback exists for that.

## 2026-11-05 13:10 - switched to gemini-3.8-flash (commander decision, "Men tanladim" - not the owner's words)
- Basis: test-2 lab 3-flash 6.8% vs 3.8-flash 5.1% letter errors, same speed/cost. Telegram question closed by the commander.
- Changed ONLY live %APPDATA%\GeminiMic\config.json "model" (backup scratchpad config_before_38.json); DEFAULT_CONFIG untouched.
  App restarted 13:09:29. Replay of real clip 125227 through gemini_transcribe: text right, but 10.3 s - Google 3.8 gave 503,
  OpenRouter google/gemini-3.8-flash answered. Risk known: 3.8 refused hard clips before (blockReason; 3.8+think 5/38).
- UNDO (one line): in config.json set "model": "gemini-3-flash-preview" + restart the app.

## 2026-11-05 13:05 - other people's words in the text: cause = mic distance, fixed by moving it
- Owner 12:43 (via system relay): "gaplarimiz orasiga boshqa odamlarning gapi ham tushib qolyapti".
- Measured on his last 20 takes (scratchpad leak/, diar.py = 3-flash diarization vs pasted text, $0.14):
  12:34-12:41, mic 40-50 cm: his 95th pct 730-1400, a colleague talking alone only -2.8..+9.8 dB under him ->
  the 10 dB near gate cannot separate them (muted 0-8%); colleague words in the PASTED text 2-3/12
  ("Besh portli ekan-da." before he spoke; "Aytyapti to'g'ri emas deb..." overlapping him).
  ~12:42 he moved the mic closer: his level 4300-7900, his/floor 23-33 dB, colleague 16 dB under; gate muted
  14-31%; pasted = main-speaker text 8/8 (colleagues still faintly audible in 7/8, none in text).
- Decision: NO code change. Rejected: stricter gate (cuts his soft word ends at distance), "main speaker only"
  prompt line (omission/injection risk seen before), level gating cannot remove overlapping speech.
- Gemini review (agy 3.8-flash-high): AGREE-WITH-CHANGES - keep mic <= ~25 cm; suggests a "mic too far" warning
  when a take's 95th pct < ~2500 (separates 20/20 takes here). NOT built: offer only (false-alarm risk on soft takes).
- The far mic was also the quiet-speech cause (his/floor 9-15 dB then vs 23-33 dB now).

## 2026-11-05 02:03 - quiet speech fixed at the source (rumble cut)
- Owner 01:50: "sekin gapirsam xato yozyapti, baland gapirsam to'g'ri yozyapti" + "o'zing qaror qilib, to'g'risini qilaver".
- CAUSE (measured, scratchpad levels.py): his 01:07-01:34 takes sit ~7 dB over the room floor (good 11-04 23:00
  reads ~25 dB); the floor (rms ~500 at 6x) is mostly rumble under 150 Hz (117 dB vs 103 dB at 150-500 Hz).
  Not the beep lead, not the gain (already 6x max, peaks 3-12k), not the near gate (muted 0% on most quiet takes).
- Lab (scratchpad quiet_lab.py, OpenRouter ~$0.6): his 10 reads turned down + real 01:xx room tone, 3 runs.
  Quiet itself reproduced: -18 dB 4.1% -> 9.2-10.5% letter errors (-12 dB no harm). Shipped cut: -18 dB 9.2 -> 6.1%,
  -21 dB 9.7 -> 7.1%; loud 4.3 -> 3.7% (words 45 -> 53/261 = run noise); podcast set neutral. DISCARDED: peak
  normalise (no clear gain), spectral denoise (worse). 16/20 real quiet takes come out different run to run =
  they are at the edge; mic closer is still the biggest lever.
- BUILT 83793f7: highpass() 120 Hz on the model audio only, before near_voice_gate; saved clip + has_speech unchanged.
  Blind review (judge): SHIP-WITH-FIXES -> power-of-two FFT (odd lengths 5x slower; now 60 s chunk 0.23 s) + comment
  numbers, both fixed. 50 tests + gate OK. App restarted 02:02:47 on MICUSB1 raw. lab-only: his real soft voice.
  Undo: in stop_recording_and_transcribe use `near = near_voice_gate(audio)` again (or git revert 83793f7) + restart.
- Board compressed: 10-23 / 10-14 sections moved verbatim to STATE_ARCHIVE.md.

## 2026-11-05 01:25 - dropped takes fixed; model A/B for English words
- Owner: "birinchisida ishlamadi, keyingisida ishladi ... oxirgi besh-oltitalarni tekshirib ol". Cause:
  has_speech threshold 2.0x room floor (~500 at 6x gain on MICUSB1). His voice since ~00:48 arrives
  ~8x weaker than during test 2 (floor unchanged = mic farther/turned); 4 of 5 rejected takes were
  real speech (OpenRouter transcript), 1 NO_SPEECH. A 45 s real take sat only 1.1-1.3x over floor.
  VOICE_FLOOR_RATIO 2.0 -> 1.3; the model's NO_SPEECH decides borderline. Live after restart: 6/6 kept.
  NOT the near-voice gate (owner's guess): it muted 0% on those takes and rejects existed on 11-04.
  Lost 01:11/01:12 takes recovered via scratchpad recover.py and given to him in chat.
- English words (owner "hal qila olsang, hal qil"): vocab + 20 dev terms -> issue/main unchanged.
  Models on test-2 clips (OpenRouter): 3-flash 6.8% vs 3.8-flash 5.1% letter errors, same speed
  (~3.4 s), same cost ($0.0005/take). 3.8 fixed Pulni, heard "main"; issue'larni still wrong; new
  miss "avval mainga". 3.5-flash / 3.1-pro / 4-argon: 404 = his OpenRouter guardrail/data policy.
  3-flash-preview is the owner's own pick (code comment) -> switch only on his yes.

## OWNER TODOs
- (since 2026-11-08) Naushnik turi. UZ: Qiling: naushnikingiz simlimi yoki Bluetooth - bir so'z yozing | Ko'rasiz: men tugma yo'lini shunga moslayman | undo: keyin o'zgartirsangiz bas
- (since 2026-11-06) Last ElevenLabs copy gSNFitP4zpS49FoeI1Wz (41 s, source unknown). Men tanladim: separate named group in the delete script. UZ: Qiling: python D:\vibecoding\gemini-mic\tools\delete_vendor_copies.py ishga tushiring, yes yozing | Ko'rasiz: o'chdi (404) | undo: yes yozmasangiz hech narsa o'chmaydi
- (since 2026-11-06) OpenRouter logging check. UZ: Qiling: openrouter.ai/settings/preferences oching | Ko'rasiz: prompt logging o'chiq turibdi | undo: faqat ko'rish, hech narsa o'zgarmaydi

## OPEN THREADS
- vendor copies after the speaker test | 4 ElevenLabs copies gone (incident 11-06), last one in the owner's delete script | owner runs the script; OpenRouter setting check | siz
- OpenRouter backup | works: 7 of 12 pasted takes 11-05..06, no '...' | watch cost (week $2.51, key shared with Meet) | men
- beep 0.5 s lead (6c96c56) | lab-only, live app has it; he has not confirmed or complained | tells me only if the beep is missing | siz
- accuracy | 3-flash live; main'ga, issue'larni still wrong (test 2) | his order: work on English words; 3.8 retry = config model gemini-3.8-flash | men
- quiet speech | rumble cut live 83793f7; mic close since 11-05 12:42 | field proof on his real soft voice still absent; watch | men
- idea capture (Right Alt hold + phone Vol-DOWN hold -> TickTick Kiruvchi -> Sonnet sorts to G'oyalar/Vazifalar; 10-min takes, audio queued offline + JobScheduler, 3-model chain) | 11-08 21:50 code DONE uncommitted, 4 blind reviews folded (pytest 100 pass; local Java test ALL PASS; known limit: service destroy/kill mid-post may duplicate one note, never lose); 11-08 22:xx owner: NO Claude login -> brain = GLM glm-5.3 with thinking (his words 'eng kuchli modelini'), Gemini Flash free key as fallback; Antigravity rejected for a background job (desktop tool, minutes per call) | NEXT (fresh row, delegate): swap call_claude in capture/idea_processor.py to GLM API (key from glm-run config, never logged) + Gemini fallback + tests + blind review, then live processor test, register 2-min processor task, PC hotkey live test via restart_when_idle, commit+CI APK (ask owner), phone test | men (+ owner: Authorize)
- voice Jarvis via headset (Vol-UP hold: ask / give Claude a task -> spoken answer) | 11-08 owner chose Gemini Live on his FREE Gemini key, fallback STT+TTS if bad or costly. Pricing checked (aistudio.google.com/docs/pricing 11-08): 3.8 Live free tier free; paid $0.005/min heard + $0.018/min spoken; billed by audio seconds, silence on an open stream billed like speech (forum, Google billing reply) -> push-to-talk only; free tier may use data for training; long-session context cost unverified; + phone voice control (Motorola Edge 30): open apps = easy (launch intent); bus route = Yandex Maps deep link yandexmaps://maps.yandex.ru/?rtext=A~B&rtt=mt (coords; needs geocode); driving other apps' screens via our AccessibilityService = possible but fragile; Google's own Gemini app-agent rolls out S26/Pixel 10 first, Motorola unconfirmed | Men tanladim: start after idea capture is live; next = spec -> owner 'boshla'; fresh session (this one is past its ceiling) | men
- only-my-voice | MICUSB1 close to him, leaks 0/8; XM5 0/6 but more own-word errors | 'mic too far' warning = offer, his call | siz
- stray gemini_mic.py | empty untracked file in repo root | delete on his word | siz


## NEXT STEP (single queue, oldest first)
- Nothing queued for me: wait for the owner's order.
- PARKED phone path: PC-trigger built 10-14 (c9b9ac1, detail in STATE_ARCHIVE.md, spec _handoff/2026-10-14-gemini-mic-pc-trigger.md);
  phone_trigger False in live config, owner 11-05 00:55 "endi telefon orqali emas, mikrofon orqali ishlayapmiz faqat". Screen-off test moot unless he returns to the phone.
- XM5 on PC: the digital-zeros note is out of date, trial 11-05 14:59 captured real audio. App binds MICUSB1 first, XM5 third.
- Open since 10-13, unverified: if calls lose the mic while the app holds it ->
  open the mic only while the hotkey is held.
- Vocabulary list (10 terms, log 11-06) live; "soxta" -> drop thinking budget first;
  clips: last 20 WAVs in %APPDATA%\GeminiMic\clips.
- Share-zip handover DONE (owner declared 2026-08-07); a friend's later result
  = NEW input, not this duty reopening.

## DECISIONS (owner one-tap answers - auto-appended; a decided question is never re-asked)
- 2026-10-14 [Telefon] Telefonda aynan nima bo'ldi? -> **hech qanday xabar yoq**
- 2026-10-14 [APK holati] Telefon ilovasining Sozlamalarida "Matnni PC ga yozish" degan tugma bormi va yoqilganmi? -> **qara telda ovoz pasaytirish tugmani bosmadim komputerda ctrl bosdim, telda komputer ulanishi bor halos**
- 2026-10-14 [Ctrl→telefon] "PC da Ctrl bossam telefon yozsin" rejimini quramizmi? -> **Ha, qur**
- 2026-10-14 [Ekran o'chiq] Ekran o'chiq sinovi: telefonni 5 daqiqa tegmay, keyin PC da Ctrl bossangiz bip keldimi? -> **Hali sinamadim**
- 2026-10-14 [Asosiy ovoz] Hamkasblar ovozi aralashganda modelga "faqat asosiy gapiruvchini yoz" deb aytib sinaymizmi? -> **Keyinroq (tavsiya)**
- 2026-10-14 [Uzun gap] 60 soniyadan uzun gapda matn tartibi buzilishi mumkin. Sizning gaplaringiz 2-4 soniya. Tuzataymi? -> **Keyinroq (tavsiya)**
- 2026-11-04 [Aniqlik] Aniqlik uchun qaysi yo'lni 10 ta gapda sinab ko'raylik? -> **A + Live (Tavsiya)**

- 2026-11-08 [Tip ovozi] "Tip" ovozi Bluetooth naushnikda ba'zan yo'qoladi, 100% kafolat yo'q. Yozilayotganini qanday bilib turasiz? -> **Ekranda belgi (Tavsiya)**
- 2026-11-08 [Telefon] Begona ovozni telefonning o'zi emas, mikrofon og'izga yaqin bo'lgani kamaytiradi. Telefonni sinaymizmi? -> **Hozircha kerak emas (Tavsiya)**
Tugadi — /clear xavfsiz
