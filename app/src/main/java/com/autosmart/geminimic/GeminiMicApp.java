package com.autosmart.geminimic;

import android.app.Application;
import android.content.Intent;

import java.io.PrintWriter;
import java.io.StringWriter;

public class GeminiMicApp extends Application {
    static final String LAST_CRASH = "last_crash";

    @Override
    public void onCreate() {
        super.onCreate();
        Thread.setDefaultUncaughtExceptionHandler((thread, throwable) -> {
            Prefs.get(this).edit().putString("last_crash", stackTrace(throwable)).apply();
            Intent intent = new Intent(this, CrashActivity.class);
            intent.addFlags(268468224);
            startActivity(intent);
            System.exit(2);
        });
    }

    private String stackTrace(Throwable t) {
        StringWriter sw = new StringWriter();
        t.printStackTrace(new PrintWriter(sw));
        return sw.toString();
    }
}
