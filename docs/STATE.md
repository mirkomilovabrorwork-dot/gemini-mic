STATUS: 11-06 15:25 picked up on the new account from the 2 old sessions; nothing built. Live app healthy: MICUSB1 + gemini-3-flash-preview, 15 takes since 11-05 15:07, stop-to-text median 5 s, max 9 s
NEXT: men - no work queued; wait for the owner's order (choices: English words main/issue, 'mic too far' warning, 3.8 retry)
SIZDAN: 0
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

## 2026-11-04 21:00 - owner's 4 asks (only my voice / beep / context correction / max accuracy)
- Beep: default render = Headphones (WH-1000XM5) (pycaw). PlaySound after 25 s idle takes 0.2-0.45 s
  longer than warm (scratchpad probe, silent tone) = the BT link sleeps; the bare 80 ms tone was cut.
  Fix 6c96c56: BEEP_LEAD_SEC 0.5 of silence in beep(). Taps < ~0.3 s stay silent by design (59 of 348
  takes in the log were < 0.5 s). lab-only: owner's ears. Undo: BEEP_LEAD_SEC = 0.
- Only-my-voice: 20 clips of 20:29-20:45 copied to scratchpad. Speech/room SNR 13-23 dB, no clipping.
  3.1-pro-preview heard faint other voices in 8/18, NONE of them appeared in the pasted text (one
  doubtful: 202935). The x6 software gain scales his voice and others equally -> lowering it blocks
  nothing. No change made.
- Accuracy (scratchpad/ab_context.py, results.json, side.txt; 15 clips x 5 variants, one run each):
  same clip + same settings gives different words run to run (203939 live "Gemini 2", rerun "Gemini
  Make") -> single runs are noise; ground truth needed (only the speaker knows). Errors seen = his
  names/English words (Gemini Mic, usage, commander) + a few Uzbek words (bazada/ba'zida).
  Prev-dictation context: once spread a wrong name 3x ("Gemini Live" for Gemini Mic) - risky.
  Text-only fix pass with his names list: fixed Gemini Mic in 2 clips, 11 untouched, 1 doubtful, +3-5 s
  (one 30 s timeout). Thinking 2048: fixed "usage", +~1 s, mixed elsewhere. 3 blockReason misses/75.
  Research (sourced, sonnet researcher): Live API transcript is a side channel, no documented
  context correction; Wispr/Superwhisper use screen/app context + learned dictionary, no published
  gains; GER papers gain mostly on weak ASR, over-correction is the known failure.
  Offered owner: A = bigger personal names list + thinking (no extra step) vs B = AI fix pass after
  the text (+3-5 s); both measured on 10 read sentences x3 runs before shipping.
- 22:15 owner chose "A + Live". New candidate found: gemini-3.5-transcribe (Google's dedicated STT model,
  Interactions API, custom_vocabulary up to 1000 terms, language_codes; the batch twin of the Live
  transcribe model). On the 15 past clips (1 run, scratchpad tr_side.txt): with vocab it got Gemini Mic
  (3 clips), Gemini Live, Opus/Sonnet/GLM, usage right where the app missed; still wrong: Jarvis
  ("jaruissan"), "Gemini Unlimited", one "Nimaga"->"Nega" swap (breaks the verbatim bar), no paragraphs.
  Without language_codes 1/15 clip came back in Cyrillic; uz-UZ+en-US fixed it (1 clip, probe_latin.py).
  Limit: 10 requests/min on this key -> any ship needs a fallback to the current model on 429.
  Harness for the 10 read sentences ready: scratchpad ab10.py (C0 app / A names+think / T / TS smart,
  3 runs, WER + injection on sentences 6/10). Live (websocket) not built yet. Owner has not read yet.
- 23:00 owner read the 10 sentences (clips 230009..230145, copied to scratchpad read10/). Scored by
  scratchpad score_all.py (letter error rate, word splits ignored; 3 runs, Live 1 run):
  gemini-3-flash-preview + 10-name list 3.5% @2.1 s (max 2.7) | 3.8-flash + names + think 3.8% @2.9 |
  3.8 plain 4.6% | 3-flash plain 4.7% | 3.7 + names + think (A) 4.8% (max 9.6 s) | APP NOW (3.7, 5 terms)
  5.9% @3.1 | transcribe smart 5.9% | Live (transcribe-live, streamed) 7.2% @0.5 s after release |
  transcribe 8.4% (rewrote sentence 3 "Opus ishlayapti" 3/3 = meaning change) | ElevenLabs scribe_v2 9.4%.
  Injections 0 everywhere, no Cyrillic.
  Refusals (blockReason, scratchpad block38/block_any/fallback_ab): 3-flash-preview 0/38 clips + 0/12 on
  the hard ones; 3.7 11/12 on the hard ones (log 24/339 overall); 3.8+think 5/38.
- 23:02 owner saw English "Key terms phonetically... Let's double-check" in a 45 s paste. Cause: 3.7
  blockReason=OTHER on clip 230239 (4/4 replays) -> fallback gemini-3.5-flash wrote its working notes
  into the text (gemini_mic.py:869-872 fallback path). Replays of 3.5: 0/4 notes but 2/4 "00:0100:46"
  timestamp junk. 3-flash-preview transcribed it clean 3/3.
- Sentence 9 lost "tanla" in EVERY model: clip 230133 last 0.2 s RMS 5336 vs clip mean 3217 = he was
  still speaking when Ctrl went up; recording stops at release (no tail). Fix candidate: ~0.4 s tail.
- 23:27 owner said ha (boshla). BUILT: model gemini-3-flash-preview + 10-name vocab (DEFAULT_CONFIG + live config.json; backup scratchpad config_before.json), FALLBACK 3.5 -> 3.8-flash, RELEASE_TAIL_SEC 0.4 (_stop_after_tail; re-press inside tail continues the take), 402 toast in Uzbek. gate + 40 tests pass, app restarted 23:26:58. LIVE CHECK BLOCKED: Google prepaid credits depleted (402 on every call since 23:18; my A/B runs ~600 calls helped drain it). Unsent clips saved 231817..232130 - transcribe after top-up. Android/Mac defaults NOT changed.
- 23:28 owner put a FREE-tier key (new project). First call on it: gemini-3-flash-preview + 10 names, 3 s, his 103-char question verbatim, last word kept (tail live). Free-tier per-model limits are shown only in AI Studio (official rate-limits page); RPD resets midnight Pacific = 13:00 Tashkent. His load: max 136 dictations/day (11-04), usually 5-50. Free tier = Google may use the audio for training. Google's own 'speak into any app' dictation (Gemini desktop) is macOS-only today; gemini.google/desktop says 'more coming to Windows over time' (checked 23:30).
- 23:40 owner thought Google's dictation reached Windows - re-checked: official Windows help (support.google.com/gemini/answer/18263854) lists no dictation/voice; Speak to Window is only on the Mac help page (hold fn, 'rolling out over time'); Android Police 10-07: Windows has only the Dictate button into Gemini's own box. One report: Speak to Window English-only. Verdict: stay on Gemini Mic. Running: ab_ctx.py (owner idea 'think, fix misheard words by context') on 3-flash + names, 2 runs.
- 23:47 owner saw 'Model band' - CAUSE = my ab_ctx.py test on his free key ate the per-minute quota (429 on his dictations 23:45, 23:47). Killed 23:49, no result kept. Lesson: never A/B on the key the owner dictates with. 23:50 owner: use his OpenRouter key (Meet app's, limited to Gemini 3.7) - asked Business OS (SendMessage msg 7174d618) to lift the model limit via Mac Mini. App calls Google directly: OpenRouter needs a code path (spec + boshla).
- 11-05 00:00 owner: "Hozir qur" + "qilinmay qolmasligi shart avval free key u ishlamasa srazi openrouter key bn qiladi". Meet STT key (server /opt/data365/app.env OPENROUTER_API_KEY, sk-or-v1-3ca...) pulled over ssh, stored as openrouter_api_key in live config.json. Probe (scratchpad or_probe.py): google/gemini-3-flash-preview 200 2.9 s correct, 3.8 and 3.7 also 200 = NO model limit. BUILDING: any Google error -> OpenRouter google/<model> at once; Google 3.8 fallback only without an OpenRouter key.
- 00:06 LIVE: his real dictation 000636: Google free key 429 -> OpenRouter google/gemini-3-flash-preview -> pasted in 4 s ('Xo''p, endi ishlayaptimi?'). Free key's 3-flash daily quota is hit (429 since 23:55). 00:09 context test via OpenRouter (scratchpad ab_ctx_or.py, 40 calls, $0.024): plain 4.7% letter errors -> context hint + reasoning 1024 3.7% (0 injections, 3.1 s median, max 5.2 s); Google path plain 3.5%. OpenRouter path now uses the hint. Replay 000856 OK in 5.1 s but began with '...' (watch). 41 tests pass, app restarted 00:09.
- 00:20 'pul va sifat' -> 'full response'/'pull request' (his clips 001117, 001419). Owner thought the context hint did it: NO - plain prompt (= Google path) gives the same 6/6 (scratchpad pul_probe.py, $0.014). Cause: uz_en prompt + English names push 'pul' to English. Lab line 'Uzbek word first when it fits' (pul_probe2.py): 6/12 right vs 0/12 - noisy, not built. Set 1 had only list names; free English words untested -> docs/ACCURACY_TEST_SENTENCES_2.md (mixed + read in noise, also tests only-my-voice).
- 00:29 ONLY-MY-VOICE BUILT + LIVE (owner 00:20: 'faqat meni ovozimni eshitadigan qilish bu shart ... 30-40 sm, maks 50 sm ... Do fast'). near_voice_gate: windows >10 dB under the take's own speech level (95th pct) muted, hold 0.4 s, attack 0.1 s; raw clip still saved, model gets the gated audio; log line 'near gate: muted N%'. Lab (scratchpad near_gate_lab*.py, ~$0.08 OpenRouter): far voice mixed at -16 dB (~2 m) leaked into the text 4/4 pairs plain -> 0/4; 15 dB / 0.25 s hold still leaked. Clean 10 reads 3.1% -> 3.1-3.6% (run noise); his 6 real 11-05 clips same text. LIMIT: a person talking AT THE SAME TIME as him, or right next to him, is not removed - test 2 in his noisy room is the real check. 44 tests OK.
- 00:40 owner: 'hozir yonimda ichki yo'q, ertaga ish vaqtida sinaymiz. Ertaga soat 2 PMlarda eslatvor' -> test 2 moved to 11-05 14:00 at the office; scheduled task gemini-mic-test2-reminder (14:00, messages this session; may pause on an approval - default mode). Clip 003900 (1st sentence) taken before he stopped - ignore. Scorer ready: scratchpad score_test2.py <start yyyyMMdd-HHmmss> (live vs raw vs gate vs gate+UZ-first, extra-word leak). OpenRouter spend 00:40: today $0.29 (incl. ~$0.16 my lab tests), week $0.85, 23 backup calls today.
- 00:47 TEST 2 DONE (owner read the 10 mixed sentences, podcast loud on his phone ~2 m away; clips 004454..004634 in scratchpad test2/, score_test2.py, $0.016). Podcast words in text: raw (no gate) 2/10 (#10 'O'zi, coder, Angliyada o'sha', #8 'o'sha yerda' for 'online') -> gate 0/10. Letter error raw 8.9% -> gate 5.9%. 'pul va sifat' right. Still wrong: 'Pulni'->'To'lov', 'main''ga'->'menga', 'issue''larni'->other words. Uzbek-first prompt line 6.4% vs 5.9% -> DISCARDED. First word present in 10/10 (pre-roll 0.6 s). 14:00 reminder deleted (owner did the podcast test instead).
- 00:55 owner: 'Shu tugagandagi tik etishni o'chirib qo'yaver' (end tick = 660 Hz pasted cue; he waited for it). Removed all 3 done beeps (local + 2 phone paste paths); start beep stays. Back-to-back takes already worked (24 in log). Owner: 'endi telefon orqali emas, mikrofon orqali ishlayapmiz faqat' - phone_trigger already False, no phone use 11-04/05. 44 tests OK, app restarted.
- Model + 10-name list + 0.4 s tail: built 23:27 above.

## OWNER TODOs

## OPEN THREADS
- speaker separation for Uzbek meetings (Jarvis order 11-06) | test running on a real 21-min Meet recording; research on how foreign recorders do it running | score, Gemini debate, report to Jarvis | men
- OpenRouter backup | works: 7 of 12 pasted takes 11-05..06, no '...' | watch cost (week $2.51, key shared with Meet) | men
- beep 0.5 s lead (6c96c56) | lab-only, live app has it; he has not confirmed or complained | tells me only if the beep is missing | siz
- accuracy | 3-flash live; main'ga, issue'larni still wrong (test 2) | his order: work on English words; 3.8 retry = config model gemini-3.8-flash | men
- quiet speech | rumble cut live 83793f7; mic close since 11-05 12:42 | field proof on his real soft voice still absent; watch | men
- only-my-voice | MICUSB1 close to him, leaks 0/8; XM5 0/6 but more own-word errors | 'mic too far' warning = offer, his call | siz
- stray gemini_mic.py | empty untracked file in repo root | delete on his word | siz

Tugadi — /clear xavfsiz

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
