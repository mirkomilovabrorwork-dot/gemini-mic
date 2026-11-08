package com.autosmart.geminimic;

import android.app.job.JobInfo;
import android.app.job.JobScheduler;
import android.content.ComponentName;
import android.content.Context;
import android.os.PowerManager;

import java.io.File;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.locks.ReentrantLock;

/**
 * The ONE implementation of "process idea audio" (owner 2026-11-08): used by the
 * live take and the service drain in MicOverlayService and by IdeaDrainJobService.
 * A process-wide lock keeps two drain passes from running at once and IN_FLIGHT
 * keeps two workers off the same file.
 */
final class IdeaDrain {

    static final int JOB_ID = 4101;
    static final long JOB_BUDGET_MS = 8 * 60 * 1000;  // JobScheduler stops a job at ~10 min
    private static final long IDEA_HANDOFF_MARGIN_MS = 60000;  // store + TickTick post (+ pairing refresh)

    static final int OUT_SAVED = 0;
    static final int OUT_QUEUED = 1;
    static final int OUT_SILENT = 2;
    static final int OUT_FAILED = 3;

    static final Set<String> IN_FLIGHT = Collections.synchronizedSet(new HashSet<>());
    private static final ReentrantLock LOCK = new ReentrantLock();
    private static volatile boolean scheduleMissed;  // schedule() was asked while a pass ran

    private IdeaDrain() {
    }

    static final class Outcome {
        final int kind;
        final String text;

        Outcome(int kind, String text) {
            this.kind = kind;
            this.text = text;
        }
    }

    static File audioDir(Context ctx) {
        return new File(ctx.getFilesDir(), IdeaAudioQueue.DIR_NAME);
    }

    /** Service-level limit for an idea take: the chain's computed worst case + hand-over margin. */
    static long ideaTimeoutMs(Context ctx, long audioSeconds) {
        return TranscribeChain.worstCaseMs(TranscribeChain.models(Prefs.model(ctx)).length, audioSeconds)
                + IDEA_HANDOFF_MARGIN_MS;
    }

    /** Idea audio files + queued idea texts that are still waiting. */
    static int pending(Context ctx) {
        return IdeaAudioQueue.count(audioDir(ctx)) + TickTickPoster.queuedCount(ctx);
    }

    static boolean isDraining() {
        return LOCK.isLocked();
    }

    /**
     * Worker thread. Transcribe one queued idea and hand the text over; the audio
     * file is deleted ONLY after the text is on TickTick or in the text queue.
     */
    static Outcome processItem(Context ctx, IdeaAudioQueue.Item item) {
        try {
            if (item.audio.length() == 0) {  // nothing to transcribe, retrying cannot help
                IdeaAudioQueue.remove(item);
                return new Outcome(OUT_SILENT, null);
            }
            String text = GeminiClient.transcribeChain(ctx, item.audio, item.seconds());
            // Past transcription: post + remove run as one step, no interrupt may land between them.
            return Uninterruptible.call(() -> {
                TickTickPoster.Result result = TickTickPoster.deliver(ctx, text, item.atMs);
                IdeaAudioQueue.remove(item);
                return new Outcome(result == TickTickPoster.Result.SAVED ? OUT_SAVED : OUT_QUEUED, text);
            });
        } catch (TranscribeChain.NoSpeech e) {
            IdeaAudioQueue.remove(item);  // every model heard silence: the take was silence
            return new Outcome(OUT_SILENT, null);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();  // service/job stopped: not the audio's fault
            return new Outcome(OUT_FAILED, null);
        } catch (Exception e) {
            IdeaAudioQueue.markFailed(item, System.currentTimeMillis());  // audio stays queued
            return new Outcome(OUT_FAILED, null);
        }
    }

    /**
     * Worker thread: oldest first, one item at a time, stop at the first failure or
     * when endAtMs has passed; then the text queue. Returns false when another pass
     * already holds the lock (nothing was done). No vibration here.
     */
    static boolean drainOnce(Context ctx, boolean force, long endAtMs) {
        if (!LOCK.tryLock()) return false;
        PowerManager.WakeLock wl = null;
        try {
            try {
                PowerManager pm = (PowerManager) ctx.getSystemService(Context.POWER_SERVICE);
                wl = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "GeminiMic:drain");
                wl.setReferenceCounted(false);
            } catch (Exception ignored) {
                wl = null;
            }
            for (IdeaAudioQueue.Item item : IdeaAudioQueue.list(audioDir(ctx))) {
                if (Thread.currentThread().isInterrupted()) return true;
                if (System.currentTimeMillis() > endAtMs) return true;  // job time is short: next run continues
                if (IN_FLIGHT.contains(item.name())) continue;
                if (!IdeaAudioQueue.due(item, System.currentTimeMillis(), force)) continue;
                if (!IN_FLIGHT.add(item.name())) continue;
                Outcome outcome;
                try {
                    try { if (wl != null) wl.acquire(ideaTimeoutMs(ctx, item.seconds())); } catch (Exception ignored) {}
                    outcome = processItem(ctx, item);
                } finally {
                    IN_FLIGHT.remove(item.name());
                }
                if (outcome.kind == OUT_FAILED) break;  // still offline / model down: keep order
            }
            if (!Thread.currentThread().isInterrupted()) {
                TickTickPoster.retryQueue(ctx);  // text queue after the audio items
            }
            return true;
        } finally {
            if (wl != null) {
                try { if (wl.isHeld()) wl.release(); } catch (Exception ignored) {}
            }
            LOCK.unlock();
            // an item was added while this pass ran and its schedule() was skipped
            if (scheduleMissed) schedule(ctx);
        }
    }

    /**
     * (Re)schedule the persisted drain job. Same id = replaced, except while a pass
     * is running (replacing would stop it; that pass re-checks pending() itself).
     */
    static void schedule(Context ctx) {
        try {
            if (isDraining()) {
                scheduleMissed = true;  // the running pass schedules when it ends
                return;
            }
            scheduleMissed = false;
            JobScheduler js = (JobScheduler) ctx.getSystemService(Context.JOB_SCHEDULER_SERVICE);
            if (js == null) return;
            js.schedule(new JobInfo.Builder(JOB_ID, new ComponentName(ctx, IdeaDrainJobService.class))
                    .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
                    .setPersisted(true)  // survives reboot (RECEIVE_BOOT_COMPLETED)
                    .setBackoffCriteria(30000, JobInfo.BACKOFF_POLICY_EXPONENTIAL)
                    .build());
        } catch (Exception ignored) {
            // the service drain still runs; nothing else to do
        }
    }
}
