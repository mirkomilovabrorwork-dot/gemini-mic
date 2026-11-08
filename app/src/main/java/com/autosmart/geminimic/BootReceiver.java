package com.autosmart.geminimic;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * After a phone reboot nothing else starts MicOverlayService, so queued idea audio
 * would wait until the owner opens the app (impossible with a broken screen).
 * Android 14 and older allow this start; Android 15+ forbids microphone-type
 * foreground services from BOOT_COMPLETED - the start then fails and is swallowed
 * (the accessibility service retries on connect, then the arm notification remains).
 */
public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || !Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) return;
        IdeaDrain.schedule(context);  // works on every Android version, no mic service needed
        if (MicOverlayService.isRunning() || Prefs.apiKey(context).isEmpty()) return;
        try {
            context.startForegroundService(new Intent(context, MicOverlayService.class));
        } catch (Exception ignored) {
            // background-start restriction: nothing else to do here
        }
    }
}
