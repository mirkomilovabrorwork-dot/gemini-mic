package com.autosmart.geminimic;

import android.content.Context;
import android.content.SharedPreferences;

final class Prefs {
    static final String API_KEY = "api_key";
    static final String LANGUAGE_MODE = "language_mode";
    static final String LANG_UZ_EN = "uz_en";
    static final String LANG_UZ_EN_RU = "uz_en_ru";
    static final String LANG_UZ_RU = "uz_ru";
    static final String MODEL = "model";
    static final String MODEL_BETTER = "gemini-3.7-flash";
    static final String MODEL_CHEAP = "gemini-2.5-flash-lite";
    static final String NAME = "gemini_mic_prefs";
    // Phone -> PC text relay: POST the transcript to the PC app instead of typing it here.
    static final String PC_MODE = "pc_mode";
    static final String PC_URL = "pc_url";
    static final String PC_CODE = "pc_code";
    static final String PC_URL_DEFAULT = "https://data365.taildef23b.ts.net/mic";

    private Prefs() {
    }

    static SharedPreferences get(Context ctx) {
        return ctx.getSharedPreferences("gemini_mic_prefs", 0);
    }

    static String apiKey(Context ctx) {
        return get(ctx).getString("api_key", "");
    }

    static String model(Context ctx) {
        return get(ctx).getString("model", "gemini-3.7-flash");
    }

    static String languageMode(Context ctx) {
        return get(ctx).getString("language_mode", "uz_en_ru");
    }

    static boolean pcMode(Context ctx) {
        return get(ctx).getBoolean(PC_MODE, false);
    }

    static String pcUrl(Context ctx) {
        return get(ctx).getString(PC_URL, PC_URL_DEFAULT);
    }

    static String pcCode(Context ctx) {
        return get(ctx).getString(PC_CODE, "");
    }

    static String modelLabel(Context ctx) {
        if ("gemini-2.5-flash-lite".equals(model(ctx))) {
            return "Fast cheap";
        } else {
            return "Better mixed";
        }
    }

    static String languageLabel(Context ctx) {
        String mode = languageMode(ctx);
        if ("uz_en".equals(mode)) {
            return "Uzbek + English";
        } else if ("uz_ru".equals(mode)) {
            return "Uzbek + Russian";
        } else {
            return "Uzbek + English + Russian";
        }
    }
}
