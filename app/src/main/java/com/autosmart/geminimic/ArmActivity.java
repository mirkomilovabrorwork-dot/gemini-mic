package com.autosmart.geminimic;

import android.app.Activity;
import android.app.NotificationManager;
import android.content.Intent;
import android.os.Bundle;
import android.widget.Toast;

// Invisible one-tap "arm" screen. Opened by tapping the post-boot notification.
// Because this Activity is in the foreground when it runs, starting the
// microphone foreground service here is allowed on Android 14+ (a mic service
// cannot be started from the background / directly from a boot receiver).
public class ArmActivity extends Activity {

    private boolean handled;

    @Override
    protected void onResume() {
        super.onResume();
        if (handled) {
            return;
        }
        handled = true;

        NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (nm != null) {
            nm.cancel(VoiceInputAccessibilityService.ARM_NOTIFICATION_ID);
        }

        boolean ready = !Prefs.apiKey(this).isEmpty()
                && checkSelfPermission("android.permission.RECORD_AUDIO") == 0;

        if (MicOverlayService.isRunning()) {
            Toast.makeText(this, "Mikrofon allaqachon yoqilgan", Toast.LENGTH_SHORT).show();
        } else if (ready) {
            startForegroundService(new Intent(this, MicOverlayService.class));
            Toast.makeText(this, "Mikrofon yoqildi", Toast.LENGTH_SHORT).show();
        } else {
            startActivity(new Intent(this, MainActivity.class));
        }
        finish();
    }
}
