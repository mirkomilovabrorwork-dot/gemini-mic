package com.autosmart.geminimic;

import android.app.Activity;
import android.os.Bundle;
import android.util.TypedValue;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

public class CrashActivity extends Activity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        String crashText = Prefs.get(this).getString("last_crash", "No crash details saved.");

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(dp(18), dp(18), dp(18), dp(18));

        TextView title = new TextView(this);
        title.setText("Gemini Mic could not open");
        title.setTextSize(TypedValue.COMPLEX_UNIT_SP, 22f);
        layout.addView(title);

        TextView subtitle = new TextView(this);
        subtitle.setText("Send this crash text back so the APK can be fixed.");
        subtitle.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f);
        subtitle.setPadding(0, dp(8), 0, dp(10));
        layout.addView(subtitle);

        TextView crashView = new TextView(this);
        crashView.setText(crashText);
        crashView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12f);
        layout.addView(crashView);

        Button clearBtn = new Button(this);
        clearBtn.setText("Clear and close");
        clearBtn.setAllCaps(false);
        clearBtn.setOnClickListener(v -> {
            Prefs.get(this).edit().remove("last_crash").apply();
            finish();
        });
        layout.addView(clearBtn);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(layout);
        setContentView(scroll);
    }

    private int dp(int dp) {
        return Math.round(dp * getResources().getDisplayMetrics().density);
    }
}
