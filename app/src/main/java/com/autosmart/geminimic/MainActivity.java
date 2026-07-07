package com.autosmart.geminimic;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.util.TypedValue;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Space;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {

    private EditText apiKeyInput;
    private TextView nextStep;
    private TextView status;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(buildView());
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshStatusSafely();
    }

    private ScrollView buildView() {
        int pad = dp(20);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(pad, pad, pad, pad);
        layout.setBackgroundColor(Color.rgb(248, 250, 252));

        TextView titleView = new TextView(this);
        titleView.setText("Gemini Mic");
        titleView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 29f);
        titleView.setTextColor(Color.rgb(17, 24, 39));
        titleView.setGravity(android.view.Gravity.START);
        layout.addView(titleView, fullWidth());

        TextView subtitleView = new TextView(this);
        subtitleView.setText("One floating mic. Drag to the side. Auto input.");
        subtitleView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f);
        subtitleView.setTextColor(Color.rgb(75, 85, 99));
        layout.addView(subtitleView, fullWidth());

        layout.addView(space(16));

        apiKeyInput = new EditText(this);
        apiKeyInput.setHint("Gemini API key");
        apiKeyInput.setSingleLine(true);
        apiKeyInput.setInputType(129);
        apiKeyInput.setText(Prefs.apiKey(this));
        layout.addView(apiKeyInput, fullWidth());

        Button saveKeyBtn = button("Save API key");
        saveKeyBtn.setOnClickListener(v -> {
            Prefs.get(this).edit().putString("api_key",
                    apiKeyInput.getText().toString().trim()).apply();
            toast("Saved");
            refreshStatusSafely();
        });
        layout.addView(saveKeyBtn, fullWidth());

        layout.addView(sectionTitle("Quality / cost"), fullWidth());

        Button betterBtn = button("Better mixed language");
        betterBtn.setOnClickListener(v -> {
            Prefs.get(this).edit().putString("model", "gemini-3.5-flash").apply();
            toast("Mode: Better mixed");
            refreshStatusSafely();
        });
        layout.addView(betterBtn, fullWidth());

        Button cheapBtn = button("Fast cheap");
        cheapBtn.setOnClickListener(v -> {
            Prefs.get(this).edit().putString("model", "gemini-2.5-flash-lite").apply();
            toast("Mode: Fast cheap");
            refreshStatusSafely();
        });
        layout.addView(cheapBtn, fullWidth());

        layout.addView(sectionTitle("Language hint"), fullWidth());

        Button uzEnRuBtn = button("Uzbek + English + Russian");
        uzEnRuBtn.setOnClickListener(v -> setLanguageMode("uz_en_ru"));
        layout.addView(uzEnRuBtn, fullWidth());

        Button uzEnBtn = button("Uzbek + English");
        uzEnBtn.setOnClickListener(v -> setLanguageMode("uz_en"));
        layout.addView(uzEnBtn, fullWidth());

        Button uzRuBtn = button("Uzbek + Russian");
        uzRuBtn.setOnClickListener(v -> setLanguageMode("uz_ru"));
        layout.addView(uzRuBtn, fullWidth());

        Button micPermBtn = button("Allow microphone");
        micPermBtn.setOnClickListener(v -> requestAudioPermissions());
        layout.addView(micPermBtn, fullWidth());

        Button testBtn = button("Test Gemini");
        testBtn.setOnClickListener(v -> testGemini());
        layout.addView(testBtn, fullWidth());

        Button overlayBtn = button("Allow floating mic");
        overlayBtn.setOnClickListener(v -> openOverlaySettings());
        layout.addView(overlayBtn, fullWidth());

        Button accessibilityBtn = button("Enable auto input");
        accessibilityBtn.setOnClickListener(v ->
                openSettings("android.settings.ACCESSIBILITY_SETTINGS",
                        "Could not open Accessibility settings"));
        layout.addView(accessibilityBtn, fullWidth());

        Button startBtn = button("Start microphone bubble");
        startBtn.setOnClickListener(v -> startMicService());
        layout.addView(startBtn, fullWidth());

        Button stopBtn = button("Stop microphone bubble");
        stopBtn.setOnClickListener(v ->
                stopService(new Intent(this, MicOverlayService.class)));
        layout.addView(stopBtn, fullWidth());

        nextStep = new TextView(this);
        nextStep.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16f);
        nextStep.setTextColor(Color.rgb(37, 99, 235));
        nextStep.setPadding(0, dp(16), 0, dp(4));
        layout.addView(nextStep, fullWidth());

        status = new TextView(this);
        status.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f);
        status.setTextColor(Color.rgb(75, 85, 99));
        layout.addView(status, fullWidth());

        TextView guideHeader = new TextView(this);
        guideHeader.setText("Qisqa guide");
        guideHeader.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18f);
        guideHeader.setTextColor(Color.rgb(17, 24, 39));
        guideHeader.setPadding(0, dp(18), 0, dp(6));
        layout.addView(guideHeader, fullWidth());

        TextView guideBody = new TextView(this);
        guideBody.setText("1. Setup tugagach Start microphone bubble bosing.\n"
                + "2. Sifat uchun Better mixed, tejamkorlik uchun Fast cheap tanlang.\n"
                + "3. Ko'p ishlatadigan til aralashmasini tanlang.\n"
                + "4. Telegram/Trello/Notes ichida yoziladigan joyni bosing.\n"
                + "5. Chetdagi kichkina blue dotni bosing, mic kattalashadi.\n"
                + "6. Katta blue micni bosib turing va gapiring.\n"
                + "7. Qo'yib yuborsangiz recording to'xtaydi va Gemini yozadi.\n"
                + "8. Green - kuting, Blue - tayyor, Red - recording.\n\n"
                + "Oddiy tap record qilmaydi. Ovoz eshitilmasa API'ga yubormaydi. "
                + "Input topilmasa: Avval matn kiritiladigan joyni bosing.");
        guideBody.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f);
        guideBody.setTextColor(Color.rgb(75, 85, 99));
        guideBody.setLineSpacing(dp(2), 1.0f);
        layout.addView(guideBody, fullWidth());

        ScrollView scroll = new ScrollView(this);
        scroll.addView(layout);
        return scroll;
    }

    private Button button(String text) {
        Button btn = new Button(this);
        btn.setText(text);
        btn.setAllCaps(false);
        btn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f);
        return btn;
    }

    private TextView sectionTitle(String text) {
        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16f);
        tv.setTextColor(Color.rgb(17, 24, 39));
        tv.setPadding(0, dp(12), 0, dp(4));
        return tv;
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
            boolean hasOverlay = Settings.canDrawOverlays(this);
            boolean hasAccess = isAccessibilityEnabled(this);

            nextStep.setText(nextStepText(hasKey, hasMic, hasOverlay, hasAccess));

            String keyStatus = hasKey ? "saved" : "missing";
            String micStatus = hasMic ? "allowed" : "needed";
            String overlayStatus = hasOverlay ? "allowed" : "needed";
            String accessStatus = hasAccess ? "enabled" : "needed";

            status.setText("API key: " + keyStatus
                    + "\nMode: " + Prefs.modelLabel(this)
                    + "\nLanguage: " + Prefs.languageLabel(this)
                    + "\nMicrophone: " + micStatus
                    + "\nFloating mic: " + overlayStatus
                    + "\nAuto input: " + accessStatus);
        } catch (Exception e) {
            nextStep.setText("Ready: app opened. Complete permissions, then start bubble.");
            status.setText("Status check failed: " + e.getMessage());
        }
    }

    private String nextStepText(boolean hasKey, boolean hasMic, boolean hasOverlay, boolean hasAccess) {
        if (!hasKey) return "Next: paste Gemini API key and Save.";
        if (!hasMic) return "Next: Allow microphone.";
        if (!hasOverlay) return "Next: Allow floating mic.";
        if (!hasAccess) return "Next: Enable auto input.";
        return "Ready: tap Start microphone bubble.";
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

    private void openOverlaySettings() {
        Intent intent = new Intent("android.settings.action.MANAGE_OVERLAY_PERMISSION");
        intent.setData(android.net.Uri.parse("package:" + getPackageName()));
        safeStartActivity(intent, "Could not open floating mic settings");
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
        Prefs.get(this).edit().putString("language_mode", mode).apply();
        toast("Language: " + Prefs.languageLabel(this));
        refreshStatusSafely();
    }

    private void startMicService() {
        if (Prefs.apiKey(this).isEmpty()) {
            toast("Add Gemini API key first");
            return;
        }
        if (!hasAudioPermission()) {
            requestAudioPermissions();
            return;
        }
        if (!Settings.canDrawOverlays(this)) {
            toast("Allow floating mic first");
            openOverlaySettings();
            return;
        }
        if (!isAccessibilityEnabled(this)) {
            toast("Enable auto input first");
            openSettings("android.settings.ACCESSIBILITY_SETTINGS",
                    "Could not open Accessibility settings");
            return;
        }
        startForegroundService(new Intent(this, MicOverlayService.class));
        toast("Mic bubble started");
    }

    private void testGemini() {
        Prefs.get(this).edit().putString("api_key",
                apiKeyInput.getText().toString().trim()).apply();
        status.setText("Testing Gemini...");
        new Thread(() -> {
            try {
                String result = GeminiClient.testConnection(this);
                runOnUiThread(() -> {
                    toast("Gemini OK: " + result);
                    status.setText("Gemini OK: " + result);
                    refreshStatusSafely();
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    toast("Gemini failed");
                    status.setText("Gemini failed: " + e.getMessage());
                });
            }
        }).start();
    }
}
