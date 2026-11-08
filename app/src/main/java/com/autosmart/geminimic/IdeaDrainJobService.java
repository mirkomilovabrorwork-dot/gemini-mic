package com.autosmart.geminimic;

import android.app.job.JobParameters;
import android.app.job.JobService;

/**
 * Drains the idea queues without MicOverlayService (after a reboot the mic
 * foreground service may be refused, and the owner cannot open the app). Same
 * code and lock as the service drain: {@link IdeaDrain#drainOnce}. No vibration.
 */
public class IdeaDrainJobService extends JobService {

    private volatile Thread worker;
    private volatile boolean stopped;

    @Override
    public boolean onStartJob(JobParameters params) {
        stopped = false;
        Thread t = new Thread(() -> {
            boolean ran = false;
            try {
                ran = IdeaDrain.drainOnce(this, false,
                        System.currentTimeMillis() + IdeaDrain.JOB_BUDGET_MS);
            } catch (RuntimeException ignored) {
            }
            // items left (failed, spaced, out of time) or another pass held the lock -> run again with backoff
            boolean more = !ran || IdeaDrain.pending(this) > 0;
            worker = null;
            if (!stopped) jobFinished(params, more);  // after onStopJob the system already rescheduled
        }, "GeminiMic-IdeaDrainJob");
        t.setDaemon(true);
        worker = t;
        t.start();
        return true;  // work continues on the thread
    }

    @Override
    public boolean onStopJob(JobParameters params) {
        stopped = true;
        Thread t = worker;
        if (t != null) t.interrupt();  // system limit or constraints lost
        return true;  // reschedule
    }
}
