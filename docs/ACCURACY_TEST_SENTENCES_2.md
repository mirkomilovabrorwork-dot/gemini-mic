# Accuracy test 2 - mixed Uzbek/English + noise (owner reads each as one Ctrl dictation)

Ground truth for test 2, 2026-11-05. Set 1 only had English names that are on
the vocabulary list. This set has free English words that are NOT on the list, plus
Uzbek words the model turned into English in his real 11-05 dictations
("pul va sifat" -> "full response" / "pull request", clips 001117 and 001419).
Read it in the usual noisy room, with people talking as normal; that also tests
"only my voice". Read one sentence per Ctrl press, in order. The clips land in
%APPDATA%\GeminiMic\clips.

1. Pul va sifat jihatdan qaysi biri yaxshi, shuni solishtir.
2. Pull request ochib, code review qilib, keyin merge qil.
3. Full response kelmayapti, faqat yarmi chiqyapti.
4. Bu ishni ertaga qilamiz, bugun issue'larni yopib chiq.
5. Serverdagi log faylini ochib, error qayerdaligini top.
6. Frontend tayyor, backend'da hali API ulanmagan.
7. Pulni karta orqali to'ladim, chekini screenshot qilib yubor.
8. Meeting'ni soat uchga ko'chir, hamma online qatnashsin.
9. Bozor narxi oshibdi, endi byudjetni qayta hisoblash kerak.
10. Branch'ni main'ga push qilma, avval menga ko'rsat.

Traps: sentences 1, 7 and 9 have the Uzbek words pul, pulni and bozor, and those must
stay Uzbek. Sentences 2 and 3 have the real English "pull request" and "full response",
and those must stay English. Any words from the background voices that show up in the
text = an only-my-voice failure.
