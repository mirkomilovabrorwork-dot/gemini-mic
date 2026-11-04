# Accuracy test - 10 sentences (owner reads each as one Ctrl dictation)

Ground truth for the A/B (names list + thinking vs AI fix pass), 2026-11-04.
Built from words the model got wrong in his real 11-04 dictations
(Gemini Mic, usage, commander, ba'zida) plus words that must NOT be injected.
Read naturally, one sentence per Ctrl press, in order. Clips land in
%APPDATA%\GeminiMic\clips; copy them right after (only the last 20 are kept).

1. Gemini Mic uchun alohida sessiya och va mikrofonni tekshirib ber.
2. Ba'zida kontrol tugmasini bosganimda signal chiqmayapti, shuni tuzat.
3. Opus ishi Opusga, Sonnet ishi Sonnetga, GLM esa tekshiruvchi bo'lsin.
4. Sen system Jarvis'san, ya'ni commandersan, hamma loyihani sen boshqarasan.
5. Brauzerdan usage sahifasiga o'tib, limitni ko'rib chiq.
6. Bugun ertalab bozorga borib, non va sut olib keldim.
7. Deadline ertaga, shuning uchun deploy qilishdan oldin test qil.
8. Transkriptni Said Umarga Telegram orqali tashlab yubor.
9. Thinking budget ni pasaytir, effort ni to'g'ri tanla.
10. Uyga kelganimda bolalar bilan bir oz o'ynadim, keyin dam oldim.

Sentences 6 and 10 contain none of the listed terms: any listed term appearing
there = an injection (the failure that killed the vocabulary hint on 10-14).
