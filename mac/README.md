# Gemini Mic — macOS

Menu-bar app: hold a hotkey, gapiring, tugmani qo'yib yuborganda matn
avtomatik joylashtiriladi (Gemini orqali).

## Ishlatish
1. Menyu-bar ikonkasi (🎙️) ustiga bosing → **API key kiritish…** → Gemini API
   key ni kiriting → Save.
2. Yozish kerak bo'lgan joyga bosing (masalan, Notes, Messages, brauzer).
3. **O'ng Cmd (⌘)** tugmasini bosib turib gapiring, qo'yib yuboring — matn
   avtomatik joylashtiriladi. (MacBook klaviaturasida o'ng Ctrl yo'q, shuning
   uchun standart tugma — o'ng Cmd.)
4. Ikonka holati: 🎙️ tayyor · 🔴 yozilmoqda · ⏳ Gemini javob kutilmoqda.
5. Menyudagi **"Til"** bo'limidan tilni tanlang (O'zbek+Ingliz+Rus / +Ingliz
   / +Rus).

Hotkey o'zgartirish uchun: `~/Library/Application Support/GeminiMic/config.json`
faylida `"hotkey"` qiymatini tahrirlang (masalan `"f9"`), keyin ilovani qayta
ishga tushiring.

## Birinchi ishga tushirishda macOS talab qiladigan ruxsatlar
macOS bu ilovani cheklab qo'yadi — quyidagi 4 qadamni bajarish shart:

1. **Gatekeeper ("noma'lum dasturchi"):** Finder'da `Gemini Mic.app`ni
   **o'ng tugma bilan bosing → Open** (oddiy double-click ishlamaydi birinchi
   marta).
2. **System Settings → Privacy & Security → Microphone:** "Gemini Mic"ni
   yoqing (mikrofonsiz yozib bo'lmaydi).
3. **System Settings → Privacy & Security → Accessibility:** "Gemini Mic"ni
   yoqing (Cmd+V ni avtomatik yuborish uchun kerak).
4. **System Settings → Privacy & Security → Input Monitoring:** "Gemini
   Mic"ni yoqing (hotkey'ni global tinglash uchun kerak).

Ruxsat berilgach, ilovani qayta ishga tushiring.

## Ishlab chiqish (local)
```
pip install -r requirements.txt
python gemini_mic_mac.py             # ilovani ishga tushirish
python gemini_mic_mac.py --selftest  # Gemini matn-tozalash mantig'ini tekshirish (Mac kutubxonalarisiz ishlaydi)
```

## Build (.app)
Faqat macOS runner'da (masalan GitHub Actions macOS runner):
```
pip install -r requirements.txt pyinstaller
pyinstaller GeminiMic.spec
ditto -c -k --sequesterRsrc --keepParent "dist/Gemini Mic.app" "Gemini Mic.zip"
```
