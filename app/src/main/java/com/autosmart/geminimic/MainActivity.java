package com.autosmart.geminimic;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Space;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {

    private int bgColor;
    private int cardColor;
    private int inkColor;
    private int mutedColor;
    private int accentColor;
    private int successColor;
    private int dangerColor;

    private EditText apiKeyInput;
    private TextView apiKeySavedLabel;
    private TextView nextStep;

    private LinearLayout micRow;
    private LinearLayout accessRow;

    private TextView langUzEnRuLabel;
    private TextView langUzEnLabel;
    private TextView langUzRuLabel;

    private Button primaryButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        computePalette();
        setContentView(buildView());
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshStatusSafely();
    }

    private void computePalette() {
        boolean night = (getResources().getConfiguration().uiMode
                & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES;
        if (night) {
            bgColor = Color.rgb(15, 23, 42);
            cardColor = Color.rgb(30, 41, 59);
            inkColor = Color.rgb(241, 245, 249);
            mutedColor = Color.rgb(148, 163, 184);
            successColor = Color.rgb(74, 222, 128);
            dangerColor = Color.rgb(248, 113, 113);
        } else {
            bgColor = Color.rgb(248, 250, 252);
            cardColor = Color.rgb(255, 255, 255);
            inkColor = Color.rgb(17, 24, 39);
            mutedColor = Color.rgb(75, 85, 99);
            successColor = Color.rgb(22, 163, 74);
            dangerColor = Color.rgb(220, 38, 38);
        }
        accentColor = Color.rgb(37, 99, 235);
    }

    private ScrollView buildView() {
        int pad = dp(20);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(pad, pad, pad, pad);
        layout.setBackgroundColor(bgColor);

        TextView titleView = new TextView(this);
        titleView.setText("Gemini Mic");
        titleView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 26f);
        titleView.setTypeface(titleView.getTypeface(), android.graphics.Typeface.BOLD);
        titleView.setTextColor(inkColor);
        layout.addView(titleView, fullWidth());

        TextView subtitleView = new TextView(this);
        subtitleView.setText("Ovoz-pastga tugmasini bosib turib gapiring.");
        subtitleView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f);
        subtitleView.setTextColor(mutedColor);
        subtitleView.setPadding(0, dp(2), 0, 0);
        layout.addView(subtitleView, fullWidth());

        layout.addView(space(20));

        layout.addView(buildApiKeyCard(), fullWidth());
        layout.addView(space(16));

        layout.addView(buildChecklistCard(), fullWidth());
        layout.addView(space(16));

        layout.addView(buildLanguageCard(), fullWidth());
        layout.addView(space(16));

        primaryButton = primaryButton("Mikrofonni yoqish");
        primaryButton.setOnClickListener(v -> togglePrimaryAction());
        layout.addView(primaryButton, fullWidth());
        layout.addView(space(16));

        layout.addView(buildHowToCard(), fullWidth());

        nextStep = new TextView(this);
        nextStep.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13f);
        nextStep.setTextColor(mutedColor);
        nextStep.setPadding(0, dp(14), 0, 0);
        layout.addView(nextStep, fullWidth());

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(bgColor);
        scroll.addView(layout);
        return scroll;
    }

    private LinearLayout buildApiKeyCard() {
        LinearLayout card = card();

        card.addView(cardTitle("API kalit"));

        apiKeyInput = new EditText(this);
        apiKeyInput.setHint("Gemini API key");
        apiKeyInput.setSingleLine(true);
        apiKeyInput.setInputType(129);
        apiKeyInput.setTextColor(inkColor);
        apiKeyInput.setHintTextColor(mutedColor);
        apiKeyInput.setText(Prefs.apiKey(this));
        card.addView(apiKeyInput, fullWidth());

        card.addView(space(10));

        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);

        Button saveKeyBtn = secondaryButton("Saqlash");
        saveKeyBtn.setOnClickListener(v -> {
            Prefs.get(this).edit().putString(Prefs.API_KEY,
                    apiKeyInput.getText().toString().trim()).apply();
            toast("Saqlandi");
            refreshStatusSafely();
        });
        LinearLayout.LayoutParams saveParams = new LinearLayout.LayoutParams(-2, -2);
        row.addView(saveKeyBtn, saveParams);

        apiKeySavedLabel = new TextView(this);
        apiKeySavedLabel.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13f);
        apiKeySavedLabel.setTextColor(successColor);
        apiKeySavedLabel.setPadding(dp(12), 0, 0, 0);
        row.addView(apiKeySavedLabel, new LinearLayout.LayoutParams(-2, -2));

        card.addView(row, fullWidth());
        return card;
    }

    private LinearLayout buildChecklistCard() {
        LinearLayout card = card();
        card.addView(cardTitle("Sozlash"));

        micRow = checklistRow("Mikrofon");
        card.addView(micRow, fullWidth());

        accessRow = checklistRow("Avto-kiritish");
        card.addView(accessRow, fullWidth());

        return card;
    }

    private LinearLayout checklistRow(String label) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(0, dp(8), 0, dp(8));

        TextView labelView = new TextView(this);
        labelView.setText(label);
        labelView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f);
        labelView.setTextColor(inkColor);
        row.addView(labelView, new LinearLayout.LayoutParams(0, -2, 1f));

        return row;
    }

    private void setRowState(LinearLayout row, boolean granted, Runnable onGrant) {
        while (row.getChildCount() > 1) {
            row.removeViewAt(1);
        }
        if (granted) {
            TextView check = new TextView(this);
            check.setText("✓");
            check.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18f);
            check.setTextColor(successColor);
            row.addView(check);
        } else {
            TextView chip = new TextView(this);
            chip.setText("Ruxsat ber");
            chip.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13f);
            chip.setTextColor(accentColor);
            chip.setPadding(dp(12), dp(6), dp(12), dp(6));
            GradientDrawable bg = new GradientDrawable();
            bg.setCornerRadius(dp(20));
            bg.setStroke(dp(1), accentColor);
            chip.setBackground(bg);
            chip.setOnClickListener(v -> onGrant.run());
            row.addView(chip);
        }
    }

    private LinearLayout buildLanguageCard() {
        LinearLayout card = card();
        card.addView(cardTitle("Til"));

        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.VERTICAL);

        langUzEnRuLabel = languageRow("Uzbek + English + Russian", Prefs.LANG_UZ_EN_RU);
        row.addView(langUzEnRuLabel, fullWidth());

        langUzEnLabel = languageRow("Uzbek + English", Prefs.LANG_UZ_EN);
        row.addView(langUzEnLabel, fullWidth());

        langUzRuLabel = languageRow("Uzbek + Russian", Prefs.LANG_UZ_RU);
        row.addView(langUzRuLabel, fullWidth());

        card.addView(row, fullWidth());
        return card;
    }

    private TextView languageRow(String label, String mode) {
        TextView tv = new TextView(this);
        tv.setText(label);
        tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f);
        tv.setTextColor(inkColor);
        tv.setPadding(0, dp(10), 0, dp(10));
        tv.setTag(mode);
        tv.setOnClickListener(v -> setLanguageMode(mode));
        return tv;
    }

    private void updateLanguageTicks() {
        String active = Prefs.languageMode(this);
        for (TextView tv : new TextView[]{langUzEnRuLabel, langUzEnLabel, langUzRuLabel}) {
            String mode = (String) tv.getTag();
            String base = tv.getText().toString().replace(" ✓", "");
            if (mode.equals(active)) {
                tv.setText(base + " ✓");
                tv.setTextColor(accentColor);
            } else {
                tv.setText(base);
                tv.setTextColor(inkColor);
            }
        }
    }

    private LinearLayout buildHowToCard() {
        LinearLayout card = card();
        card.addView(cardTitle("Qanday ishlatish"));

        TextView body = new TextView(this);
        body.setText("1. Ovoz-pastga tugmasini bosib turib gapiring, qo'yib yuborsangiz yoziladi.\n"
                + "   Qisqa bossangiz — oddiy ovoz pasayadi.\n"
                + "2. Matn to'g'ridan-to'g'ri faol maydonga yoziladi.");
        body.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13f);
        body.setTextColor(mutedColor);
        body.setLineSpacing(dp(2), 1.0f);
        card.addView(body, fullWidth());
        return card;
    }

    private LinearLayout card() {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        int p = dp(16);
        card.setPadding(p, p, p, p);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(cardColor);
        bg.setCornerRadius(dp(16));
        card.setBackground(bg);
        return card;
    }

    private TextView cardTitle(String text) {
        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16f);
        tv.setTypeface(tv.getTypeface(), android.graphics.Typeface.BOLD);
        tv.setTextColor(inkColor);
        tv.setPadding(0, 0, 0, dp(10));
        return tv;
    }

    private Button primaryButton(String text) {
        Button btn = new Button(this);
        btn.setText(text);
        btn.setAllCaps(false);
        btn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16f);
        btn.setTextColor(Color.WHITE);
        btn.setMinHeight(dp(48));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(accentColor);
        bg.setCornerRadius(dp(16));
        btn.setBackground(bg);
        return btn;
    }

    private Button secondaryButton(String text) {
        Button btn = new Button(this);
        btn.setText(text);
        btn.setAllCaps(false);
        btn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f);
        btn.setTextColor(accentColor);
        btn.setMinHeight(dp(44));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.TRANSPARENT);
        bg.setCornerRadius(dp(14));
        bg.setStroke(dp(1), accentColor);
        btn.setBackground(bg);
        btn.setPadding(dp(16), 0, dp(16), 0);
        return btn;
    }

    private Space space(int dpVal) {
        Space s = new Space(this);
        s.setLayoutParams(new LinearLayout.LayoutParams(1, dp(dpVal)));
        return s;
    }

    private ViewGroup.LayoutParams fullWidth() {
        return new LinearLayout.LayoutParams(-1, -2);
    }

    private int dp(int dp) {
        return Math.round(dp * getResources().getDisplayMetrics().density);
    }

    private void toast(String msg) {
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show();
    }

    private void refreshStatusSafely() {
        try {
            boolean hasKey = !Prefs.apiKey(this).isEmpty();
            boolean hasMic = hasAudioPermission();
            boolean hasAccess = isAccessibilityEnabled(this);

            apiKeySavedLabel.setText(hasKey ? "✓ saqlangan" : "");

            setRowState(micRow, hasMic, this::requestAudioPermissions);
            setRowState(accessRow, hasAccess, () -> openSettings(
                    "android.settings.ACCESSIBILITY_SETTINGS", "Could not open Accessibility settings"));

            updateLanguageTicks();

            boolean running = MicOverlayService.isRunning();
            primaryButton.setText(running ? "To'xtatish" : "Mikrofonni yoqish");

            nextStep.setText(nextStepText(hasKey, hasMic, hasAccess, running));
        } catch (Exception e) {
            nextStep.setText("Status check failed: " + e.getMessage());
        }
    }

    private String nextStepText(boolean hasKey, boolean hasMic,
                                 boolean hasAccess, boolean running) {
        if (!hasKey) return "Keyingi qadam: API kalitni kiriting va Saqlash bosing.";
        if (!hasMic) return "Keyingi qadam: mikrofonga ruxsat bering.";
        if (!hasAccess) return "Keyingi qadam: avto-kiritishni yoqing.";
        if (running) return "Tayyor: mikrofon ishlamoqda.";
        return "Tayyor: Mikrofonni yoqish tugmasini bosing.";
    }

    private boolean hasAudioPermission() {
        return checkSelfPermission("android.permission.RECORD_AUDIO") == 0;
    }

    private boolean isAccessibilityEnabled(android.content.Context ctx) {
        String enabled = android.provider.Settings.Secure.getString(
                ctx.getContentResolver(), "enabled_accessibility_services");
        if (enabled == null) return false;
        return enabled.toLowerCase().contains(
                new ComponentName(ctx, VoiceInputAccessibilityService.class)
                        .flattenToString().toLowerCase());
    }

    private void requestAudioPermissions() {
        if (Build.VERSION.SDK_INT >= 33) {
            requestPermissions(new String[]{
                    "android.permission.RECORD_AUDIO",
                    "android.permission.POST_NOTIFICATIONS"
            }, 10);
        } else {
            requestPermissions(new String[]{"android.permission.RECORD_AUDIO"}, 10);
        }
    }

    private void openSettings(String action, String errorMsg) {
        safeStartActivity(new Intent(action), errorMsg);
    }

    private void safeStartActivity(Intent intent, String errorMsg) {
        try {
            startActivity(intent);
        } catch (Exception e) {
            toast(errorMsg);
        }
    }

    private void setLanguageMode(String mode) {
        Prefs.get(this).edit().putString(Prefs.LANGUAGE_MODE, mode).apply();
        toast("Til: " + Prefs.languageLabel(this));
        refreshStatusSafely();
    }

    private void togglePrimaryAction() {
        if (MicOverlayService.isRunning()) {
            stopService(new Intent(this, MicOverlayService.class));
        } else {
            startMicService();
        }
        refreshStatusSafely();
    }

    private void startMicService() {
        if (Prefs.apiKey(this).isEmpty()) {
            toast("Avval Gemini API kalitni kiriting");
            return;
        }
        if (!hasAudioPermission()) {
            requestAudioPermissions();
            return;
        }
        if (!isAccessibilityEnabled(this)) {
            toast("Avval avto-kiritishni yoqing");
            openSettings("android.settings.ACCESSIBILITY_SETTINGS",
                    "Could not open Accessibility settings");
            return;
        }
        startForegroundService(new Intent(this, MicOverlayService.class));
        toast("Mikrofon yoqildi");
    }
}
