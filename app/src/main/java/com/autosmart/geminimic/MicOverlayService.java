package com.autosmart.geminimic;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.net.ConnectivityManager;
import android.net.Network;
import android.media.AudioManager;
import android.media.MediaRecorder;
import android.media.session.PlaybackState;
import android.media.VolumeProvider;
import android.media.session.MediaSession;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicBoolean;

public class MicOverlayService extends Service {

    private static MicOverlayService instance;

    private static final long AMPLITUDE_SAMPLE_MS = 150;
    private static final String CHANNEL_ID = "gemini_mic";
    private static final long MAX_RECORDING_MS = 10 * 60 * 1000;  // owner: 5 min takes must never be cut
    private static final long MIN_RECORDING_MS = 650;
    private static final int NOTIFICATION_ID = 41;
    private static final int SILENCE_PEAK_THRESHOLD = 600;
    // Typing / PC-relay takes: 75 s as before, plus the longer read timeout per audio second.
    private static final long LEGACY_TRANSCRIBE_TIMEOUT_MS = 75000;
    private static final long IDEA_HANDOFF_MARGIN_MS = 60000;  // store + TickTick post (+ pairing refresh)
    // Volume-key idea capture (owner 2026-11-08)
    private static final long QUEUE_RETRY_MS = 5 * 60 * 1000;
    private static final long MEDIA_TAP_MS = 350;        // media path: no repeat in time = tap
    private static final long MEDIA_HOLD_GAP_MS = 700;   // media path: silence after repeats = release

    final Handler main;
    final ExecutorService worker;

    boolean recording;
    boolean busy;
    MediaRecorder recorder;
    File currentFile;
    long recordingStartedAt;
    int peakAmplitude;

    Future<?> currentTranscription;
    Runnable currentTranscriptionTimeout;
    int transcriptionJobId;

    private final Runnable autoStopRecording;
    private final Runnable sampleAmplitude;

    // PC hotkey -> phone recording (main-thread state)
    PcPoller pcPoller;
    String pcStatus;            // suffix on the notification, null = no PC poll
    String notificationText = "Ready";
    boolean pcRecording;        // the current recording was started by the PC
    long pcSeq;                 // seq of the PC state the phone last applied (acks carry it)
    PowerManager.WakeLock wakeLock;  // PC take: recording + transcription + POST

    // Volume-Down hold = idea -> TickTick (owner 2026-11-08). The screen is
    // broken: feedback is vibration only, nothing may need typing on the phone.
    boolean volumeRecording;    // the current recording was started by a volume key
    boolean ideaJob;            // the running transcription job is an idea take (audio is queued on disk)
    boolean mediaTake;          // the current take was started via the MediaSession path
    MediaSession mediaSession;  // captures volume keys while the screen is off

    private final Runnable startBuzz;
    private final Runnable mediaTapCancel;
    private final Runnable mediaHoldStop;
    private Runnable queueRetry;  // not final: the lambda re-posts itself

    // Idea-audio drain (owner 2026-11-08): one worker pass at a time, oldest first
    private final AtomicBoolean draining = new AtomicBoolean(false);
    private volatile boolean forceAgain;
    private ConnectivityManager.NetworkCallback netCallback;


    public MicOverlayService() {
        this.main = new Handler(Looper.getMainLooper());
        this.worker = Executors.newCachedThreadPool();
        this.autoStopRecording = () -> {
            if (recording && !busy) {
                toast("Auto-stopping at 10 minutes");
                stopAndTranscribe();
            }
        };
        this.sampleAmplitude = new AmplitudeRunnable();
        // Delayed past the tap window so a short volume tap never vibrates,
        // and only for volume-key takes (a PC/floating take stays silent).
        this.startBuzz = () -> {
            if (recording && volumeRecording) {
                TickTickPoster.buzzStart(MicOverlayService.this);
            }
        };
        this.mediaTapCancel = () -> {
            if (recording && mediaTake) {
                cancelRecording();
                AudioManager am = (AudioManager) getSystemService(AUDIO_SERVICE);
                if (am != null) {
                    am.adjustSuggestedStreamVolume(AudioManager.ADJUST_LOWER,
                            AudioManager.USE_DEFAULT_STREAM_TYPE, AudioManager.FLAG_SHOW_UI);
                }
            }
        };
        this.mediaHoldStop = () -> {
            if (recording && mediaTake) stopAndTranscribe();
        };
        this.queueRetry = () -> {
            drain(false);
            main.postDelayed(this.queueRetry, QUEUE_RETRY_MS);
        };
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        try {
            startMicForeground("Ready");
        } catch (Exception e) {
            // a microphone foreground service refused from the background (Android 14+/15):
            // stop quietly instead of crashing; the arm notification stays for a tap
            stopSelf();
            return;
        }
        instance = this;
        // Once the mic service is up, the post-boot "tap to arm" nudge is done.
        NotificationManager nm = (NotificationManager) getSystemService(NotificationManager.class);
        if (nm != null) {
            nm.cancel(VoiceInputAccessibilityService.ARM_NOTIFICATION_ID);
        }
        restartPcPoller();
        setupMediaSession();
        // Pair with TickTick via the PC relay on start if we have no token yet.
        worker.execute(() -> {
            if (Prefs.ticktickToken(MicOverlayService.this).isEmpty()) {
                TickTickPoster.fetchPairing(MicOverlayService.this);
            }
        });
        main.postDelayed(queueRetry, QUEUE_RETRY_MS);  // offline queues: every 5 min
        registerNetworkCallback();  // internet back -> drain at once
        IdeaDrain.schedule(this);   // persisted job: drains without this service too
        drain(false);               // and on service start
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        if (instance == this) {
            instance = null;
        }
        clearTranscriptionTimeout();
        if (currentTranscription != null) {
            currentTranscription.cancel(true);
            currentTranscription = null;
        }
        stopPcPoller();
        releaseMediaSession();
        unregisterNetworkCallback();
        main.removeCallbacks(startBuzz);
        main.removeCallbacks(mediaTapCancel);
        main.removeCallbacks(mediaHoldStop);
        main.removeCallbacks(queueRetry);
        stopRecordingQuietly();
        releaseWakeLock();
        worker.shutdownNow();
        super.onDestroy();
    }

    static boolean isRunning() {
        return instance != null;
    }

    static void volumeStart() {
        MicOverlayService svc = instance;
        if (svc != null) {
            svc.main.post(() -> {
                if (svc.startRecording()) {
                    svc.volumeRecording = true;
                    svc.mediaTake = false;  // the accessibility path owns this take
                    svc.acquireVolumeWakeLock();
                }
            });
        }
    }

    static void volumeStop() {
        MicOverlayService svc = instance;
        if (svc != null) {
            svc.main.post(svc::stopAndTranscribe);
        }
    }

    static void volumeCancel() {
        MicOverlayService svc = instance;
        if (svc != null) {
            svc.main.post(svc::cancelRecording);
        }
    }

    /** Called after the PC prefs are saved: (re)start or stop the PC poller. */
    static void refreshPcMode() {
        MicOverlayService svc = instance;
        if (svc != null) {
            svc.main.post(svc::restartPcPoller);
        }
    }

    private void restartPcPoller() {
        String code = Prefs.pcCode(this);
        String url = Prefs.pcUrl(this);
        boolean on = Prefs.pcMode(this) && !code.isEmpty();
        // onPause saves the prefs too: an unchanged setup must not drop a live poll
        // (a command the PC handed to a torn-down connection would be lost).
        if (on && pcPoller != null && pcPoller.isAlive()
                && pcPoller.url.equals(url) && pcPoller.code.equals(code)) {
            return;
        }
        stopPcPoller();
        if (on) {
            pcPoller = new PcPoller(url, code);
            pcPoller.start();
        } else {
            setPcStatus(null);
        }
    }

    private void stopPcPoller() {
        if (pcPoller != null) {
            pcPoller.shutdown();
            pcPoller = null;
        }
    }

    private void setPcStatus(String status) {
        if (status == null ? pcStatus == null : status.equals(pcStatus)) return;
        pcStatus = status;
        updateNotification(notificationText);
    }

    /**
     * A NEW PC desired state (seq changed): "recording" -> start; "idle" -> stop
     * (discard -> cancel). Every end of a PC take is acked "stopped".
     */
    private void pcApply(PcPoller poller, String state, long seq, boolean discard) {
        if (poller != pcPoller) return;
        if ("recording".equals(state)) {
            pcStart(poller, seq);
            return;
        }
        pcSeq = seq;
        // only a PC-started recording: a volume-key recording is never the PC's to end
        if (recording && pcRecording) {
            if (discard) cancelRecording(); else stopAndTranscribe();  // both ack "stopped"
        } else {
            worker.submit(() -> postAck(poller.url, poller.code, "stopped", seq, "idle"));
        }
    }

    /** PC said "start": record, then tell the PC whether the mic is live. */
    private void pcStart(PcPoller poller, long seq) {
        boolean ok;
        if (recording && pcRecording) {
            ok = true;  // already recording for the PC: confirm again
        } else {
            ok = startRecording();  // refuses when already recording or busy
            if (ok) {
                pcRecording = true;
                try {
                    PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
                    wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "GeminiMic:pcRecording");
                    wakeLock.setReferenceCounted(false);  // a later acquire() just extends it
                    wakeLock.acquire(MAX_RECORDING_MS + 5000);
                } catch (Exception ignored) {
                    wakeLock = null;
                }
            }
        }
        if (ok) pcSeq = seq;
        final String state = ok ? "recording" : "error";
        worker.submit(() -> postAck(poller.url, poller.code, state, seq, null));
    }

    /** A PC take ended on the phone without text (or with text to follow on "stop"). */
    private void pcAckStopped(boolean wasPc, String reason) {
        if (!wasPc) return;
        if (!"stop".equals(reason)) releaseWakeLock();  // no transcription follows
        final PcPoller poller = pcPoller;
        if (poller == null) return;
        final long seq = pcSeq;
        worker.submit(() -> postAck(poller.url, poller.code, "stopped", seq, reason));
    }

    private void releaseWakeLock() {
        release(wakeLock);
        wakeLock = null;
    }

    /** CPU stays up through a volume-key take (recording + transcription + POST). */
    private void acquireVolumeWakeLock() {
        try {
            PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
            wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "GeminiMic:volumeRecording");
            wakeLock.setReferenceCounted(false);
            wakeLock.acquire(MAX_RECORDING_MS + 5000);
        } catch (Exception ignored) {
            wakeLock = null;
        }
    }

    /**
     * Screen-off capture: while the screen is OFF the accessibility service gets
     * no volume keys - the system routes them to an ACTIVE MediaSession's remote
     * VolumeProvider. Honest limits (must be measured on the real phone):
     * - the provider gives per-press/repeat callbacks but NO key-up event, so a
     *   "hold" is detected from OS key repeats + a timeout after the last one
     *   ({@link #MEDIA_HOLD_GAP_MS}); a "tap" = no repeat within {@link #MEDIA_TAP_MS};
     * - if another app is actively playing, that session may win the keys.
     * When the screen is ON the accessibility path consumes the keys first;
     * the mediaTake/!recording guards keep the two paths from double-starting.
     */
    private void setupMediaSession() {
        try {
            mediaSession = new MediaSession(this, "GeminiMic");
            mediaSession.setPlaybackState(new PlaybackState.Builder()
                    .setState(PlaybackState.STATE_PLAYING, 0, 1.0f)
                    .build());
            mediaSession.setPlaybackToRemote(new VolumeProvider(
                    VolumeProvider.VOLUME_CONTROL_ABSOLUTE, 100, 50) {
                @Override
                public void onAdjustVolume(int direction) {
                    // binder thread -> hop to main (all recording state is main-only)
                    main.post(() -> mediaVolumeAdjust(direction));
                }
            });
            mediaSession.setActive(true);
        } catch (Exception e) {
            releaseMediaSession();  // screen-off capture stays off; accessibility path unaffected
        }
    }

    private void releaseMediaSession() {
        if (mediaSession != null) {
            try {
                mediaSession.setActive(false);
                mediaSession.release();
            } catch (Exception ignored) {
            }
            mediaSession = null;
        }
    }

    /** Volume-down arrived through the MediaSession (screen off). Main thread. */
    private void mediaVolumeAdjust(int direction) {
        if (direction >= 0) return;  // volume-up is not ours
        if (busy) return;            // a transcription is running: ignore
        if (!recording) {
            if (startRecording()) {
                volumeRecording = true;
                mediaTake = true;
                acquireVolumeWakeLock();
                main.postDelayed(mediaTapCancel, MEDIA_TAP_MS);
            }
        } else if (mediaTake) {
            // another OS key repeat = still held; a stop is armed for the
            // silence that follows the LAST repeat (no key-up exists here)
            main.removeCallbacks(mediaTapCancel);
            main.postDelayed(mediaHoldStop, MEDIA_HOLD_GAP_MS);
        }
    }

    private static void release(PowerManager.WakeLock wl) {
        if (wl == null) return;
        try { if (wl.isHeld()) wl.release(); } catch (Exception ignored) {}
    }

    private void cancelRecording() {
        File audioFile = currentFile;
        boolean wasPc = pcRecording;
        try {
            if (recorder != null) recorder.stop();
        } catch (Exception ignored) {
        }
        stopRecordingQuietly();
        if (audioFile != null) {
            audioFile.delete();
        }
        pcAckStopped(wasPc, "cancel");
        releaseWakeLock();  // a volume-key take cancelled as a tap: nothing follows
    }

    boolean startRecording() {
        if (busy || recording) return false;
        if (checkSelfPermission("android.permission.RECORD_AUDIO") != 0) {
            toast("Allow microphone first");
            return false;
        }
        try {
            currentFile = new File(getCacheDir(),
                    "speech-" + System.currentTimeMillis() + ".aac");
            recorder = new MediaRecorder();
            recorder.setAudioSource(MediaRecorder.AudioSource.MIC);
            recorder.setOutputFormat(MediaRecorder.OutputFormat.AAC_ADTS);
            recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC);
            recorder.setAudioChannels(1);           // mono, 16 kHz, 48 kbps: 5 min ~ 1.8 MB, same accuracy
            recorder.setAudioSamplingRate(16000);
            recorder.setAudioEncodingBitRate(48000);
            recorder.setOutputFile(currentFile.getAbsolutePath());
            recorder.prepare();
            recorder.start();
            recording = true;
            recordingStartedAt = System.currentTimeMillis();
            peakAmplitude = 0;
            main.postDelayed(autoStopRecording, MAX_RECORDING_MS);
            main.postDelayed(sampleAmplitude, AMPLITUDE_SAMPLE_MS);
            main.postDelayed(startBuzz, MEDIA_TAP_MS);  // past the tap window: taps stay silent
            toast("Recording");
            return true;
        } catch (Exception e) {
            stopRecordingQuietly();
            toast("Could not start mic");
            return false;
        }
    }

    void stopAndTranscribe() {
        File audioFile = currentFile;
        long startedAt = recordingStartedAt;
        long duration = System.currentTimeMillis() - recordingStartedAt;
        boolean wasPc = pcRecording;
        // Frozen at stop time: a take STARTED by a volume key is an idea (audio queued
        // on disk, then TickTick) unless the old typing behaviour is forced on.
        final boolean ideaTake = volumeRecording && !Prefs.volumeTypesText(this);
        try {
            recorder.stop();
        } catch (Exception ignored) {
        }
        stopRecordingQuietly();
        if (audioFile == null || !audioFile.exists()) {
            pcAckStopped(wasPc, "nofile");
            if (!wasPc) releaseWakeLock();  // volume take: nothing follows
            toast("No audio");
            return;
        }
        if (duration < MIN_RECORDING_MS) {
            audioFile.delete();
            pcAckStopped(wasPc, "short");
            if (!wasPc) releaseWakeLock();
            toast("Hold longer");
            return;
        }
        if (peakAmplitude < SILENCE_PEAK_THRESHOLD) {
            audioFile.delete();
            pcAckStopped(wasPc, "silent");
            if (!wasPc) releaseWakeLock();
            toast("Ovoz eshitilmadi");
            return;
        }
        final long seconds = Math.max(1, (duration + 999) / 1000);
        final long timeoutMs = ideaTake
                ? IdeaDrain.ideaTimeoutMs(this, seconds)
                : LEGACY_TRANSCRIBE_TIMEOUT_MS + 2 * 300 * seconds;
        if (wakeLock != null) {
            // keep the CPU up through transcription + the POST
            try { wakeLock.acquire(timeoutMs + 5000); } catch (Exception ignored) {}
        }
        pcAckStopped(wasPc, "stop");  // text follows through the relay POST
        busy = true;
        ideaJob = ideaTake;
        updateNotification("Transcribing");
        final int jobId = ++transcriptionJobId;
        currentTranscriptionTimeout = () -> finishTranscriptionTimeout(jobId);
        main.postDelayed(currentTranscriptionTimeout, timeoutMs);
        if (ideaTake) {
            // Write-ahead: the audio goes to disk BEFORE any network call.
            final IdeaAudioQueue.Item item = IdeaAudioQueue.store(IdeaDrain.audioDir(this), audioFile, startedAt, duration);
            IdeaDrain.IN_FLIGHT.add(item.name());  // the drain must not touch a live take
            IdeaDrain.schedule(this);  // safety net: the job drains it even if this service dies
            try {
                currentTranscription = worker.submit(() -> {
                    IdeaDrain.Outcome outcome;
                    try {
                        outcome = IdeaDrain.processItem(MicOverlayService.this, item);
                    } finally {
                        IdeaDrain.IN_FLIGHT.remove(item.name());
                    }
                    main.post(() -> finishIdeaTake(jobId, outcome));
                });
            } catch (RuntimeException e) {
                IdeaDrain.IN_FLIGHT.remove(item.name());  // service is going down: the file stays queued
                throw e;
            }
            return;
        }
        currentTranscription = worker.submit(() -> {
            try {
                String text = GeminiClient.transcribe(MicOverlayService.this, audioFile);
                main.post(() -> finishTranscriptionSuccess(jobId, text));
            } catch (Exception e) {
                main.post(() -> finishTranscriptionError(jobId, e));
            } finally {
                audioFile.delete();
            }
        });
    }

    /** Main thread: vibrate the result of a live idea take (vibration is the only feedback). */
    private void finishIdeaTake(int jobId, IdeaDrain.Outcome outcome) {
        if (isActiveTranscription(jobId)) {  // after a timeout the "queued" buzz was already given
            if (outcome.text != null) copyToClipboard(outcome.text);  // cheap safety net
            if (outcome.kind == IdeaDrain.OUT_SAVED) {
                TickTickPoster.buzzSaved(this);
            } else if (outcome.kind == IdeaDrain.OUT_SILENT) {
                TickTickPoster.buzzStart(this);  // one short 60 ms: nothing was said
            } else {
                TickTickPoster.buzzQueued(this);  // text queued, or audio queued
            }
            finishTranscriptionJob();
        }
        drain(false);
    }

    /** Start a drain pass of the idea-audio queue (+ the text queue). force = ignore retry spacing. */
    void drain(boolean force) {
        if (!draining.compareAndSet(false, true)) {
            if (force) forceAgain = true;  // network came back while a pass runs: go again
            return;
        }
        try {
            worker.execute(() -> {
                boolean f = force;
                try {
                    do {
                        forceAgain = false;
                        IdeaDrain.drainOnce(MicOverlayService.this, f, Long.MAX_VALUE);
                        f = true;
                    } while (forceAgain && !Thread.currentThread().isInterrupted());
                } finally {
                    draining.set(false);
                }
            });
        } catch (RuntimeException e) {
            draining.set(false);  // worker already shut down
        }
    }

    private void registerNetworkCallback() {
        try {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
            if (cm == null) return;
            netCallback = new ConnectivityManager.NetworkCallback() {
                @Override
                public void onAvailable(Network network) {
                    drain(true);
                }
            };
            cm.registerDefaultNetworkCallback(netCallback);
        } catch (Exception e) {
            netCallback = null;  // the 5-minute pass still runs
        }
    }

    private void unregisterNetworkCallback() {
        if (netCallback == null) return;
        try {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
            if (cm != null) cm.unregisterNetworkCallback(netCallback);
        } catch (Exception ignored) {
        }
        netCallback = null;
    }

    private void stopRecordingQuietly() {
        recording = false;
        pcRecording = false;  // the wake lock outlives the recording (see finishTranscriptionJob)
        volumeRecording = false;
        mediaTake = false;
        main.removeCallbacks(startBuzz);
        main.removeCallbacks(mediaTapCancel);
        main.removeCallbacks(mediaHoldStop);
        main.removeCallbacks(autoStopRecording);
        main.removeCallbacks(sampleAmplitude);
        if (recorder != null) {
            try { recorder.release(); } catch (Exception ignored) {}
            recorder = null;
        }
        currentFile = null;
    }

    private void finishTranscriptionSuccess(int jobId, String text) {
        if (!isActiveTranscription(jobId)) return;
        copyToClipboard(text);  // cheap safety net in both modes
        final String pcCode = Prefs.pcCode(this);
        if (Prefs.pcMode(this) && !pcCode.isEmpty()) {
            // Owner is at the PC: send the text there; type on the phone only
            // if the PC did not take it, so a dead PC never loses a dictation.
            final String pcUrl = Prefs.pcUrl(this);
            final PowerManager.WakeLock wl = wakeLock;  // held until the POST is done
            wakeLock = null;
            worker.submit(() -> {
                int code = sendToPc(pcUrl, pcCode, text);
                release(wl);
                main.post(() -> {
                    if (code == 200) {
                        toast("PC ga yozildi ✓");
                        return;
                    }
                    toast(code == 403 ? "PC kodi noto'g'ri" : "PC javob bermadi");
                    typeOnPhone(text);
                });
            });
        } else {
            typeOnPhone(text);
        }
        finishTranscriptionJob();
    }

    private void typeOnPhone(String text) {
        if (!VoiceInputAccessibilityService.typeText(text)) {
            toast("Enable auto input first");
        }
    }

    private void copyToClipboard(String text) {
        try {
            ClipboardManager cm = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
            if (cm != null) cm.setPrimaryClip(ClipData.newPlainText("Gemini Mic", text));
        } catch (Exception ignored) {}
    }

    /** POST {"token","text"} to the PC relay; returns the HTTP code, or -1 on a network error. */
    private static int sendToPc(String url, String code, String text) {
        HttpURLConnection conn = null;
        try {
            JSONObject body = new JSONObject().put("token", code).put("text", text);
            conn = (HttpURLConnection) new URL(url).openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(10000);
            conn.setReadTimeout(10000);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            byte[] payload = body.toString().getBytes(StandardCharsets.UTF_8);
            OutputStream out = conn.getOutputStream();
            try {
                out.write(payload);
            } finally {
                out.close();
            }
            return conn.getResponseCode();
        } catch (Exception e) {
            return -1;
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    /** pc_url without trailing slashes (".../mic"); /cmd and /ack hang off it. */
    private static String pcBase(String pcUrl) {
        String u = pcUrl.trim();
        while (u.endsWith("/")) u = u.substring(0, u.length() - 1);
        return u;
    }

    /**
     * POST {"token","state","seq"[,"reason"]} to <pcUrl>/ack; the PC beeps START
     * on "recording" and un-sticks its tray / takes over on "stopped".
     */
    private static void postAck(String pcUrl, String code, String state, long seq, String reason) {
        HttpURLConnection conn = null;
        try {
            JSONObject body = new JSONObject().put("token", code).put("state", state).put("seq", seq);
            if (reason != null) body.put("reason", reason);
            conn = (HttpURLConnection) new URL(pcBase(pcUrl) + "/ack").openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(10000);
            conn.setReadTimeout(10000);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            OutputStream out = conn.getOutputStream();
            try {
                out.write(body.toString().getBytes(StandardCharsets.UTF_8));
            } finally {
                out.close();
            }
            conn.getResponseCode();
        } catch (Exception ignored) {
            // no ack -> the PC falls back to its own mic after 2 s
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    /**
     * Outbound long-poll to the PC: GET <pcUrl>/cmd?have=<seq> returns the PC's
     * DESIRED state; a new seq is applied on the main thread (pcApply). Never
     * holds a wake lock; backs off 2,4,8..30 s on errors.
     */
    private class PcPoller extends Thread {
        final String url;
        final String code;
        private long handledSeq = -1;  // -1: the first poll returns the state at once
        private volatile boolean running = true;
        private volatile HttpURLConnection conn;

        PcPoller(String url, String code) {
            super("GeminiMic-PcPoller");
            setDaemon(true);
            this.url = url;
            this.code = code;
        }

        void shutdown() {
            running = false;
            interrupt();
            HttpURLConnection c = conn;
            if (c != null) c.disconnect();  // unblocks a pending long-poll read
        }

        private void status(String s) {
            main.post(() -> {
                if (pcPoller == this) setPcStatus(s);
            });
        }

        @Override
        public void run() {
            int backoff = 0;
            while (running) {
                int http = -1;
                try {
                    HttpURLConnection c = (HttpURLConnection) new URL(pcBase(url) + "/cmd?token="
                            + URLEncoder.encode(code, "UTF-8") + "&wait=20&have=" + handledSeq)
                            .openConnection();
                    conn = c;
                    c.setConnectTimeout(10000);
                    c.setReadTimeout(35000);
                    http = c.getResponseCode();
                    if (http == 200) {
                        InputStream in = c.getInputStream();
                        ByteArrayOutputStream buf = new ByteArrayOutputStream();
                        byte[] chunk = new byte[1024];
                        int n;
                        while ((n = in.read(chunk)) > 0) buf.write(chunk, 0, n);
                        in.close();
                        JSONObject reply = new JSONObject(buf.toString("UTF-8"));
                        String state = reply.optString("state", "idle");
                        long seq = reply.optLong("seq", 0);
                        boolean discard = reply.optBoolean("discard", false);
                        backoff = 0;
                        status("PC bilan ulangan");
                        if (!running) break;
                        if (seq != handledSeq) {
                            handledSeq = seq;
                            main.post(() -> pcApply(this, state, seq, discard));
                        }
                        continue;
                    }
                } catch (Exception ignored) {
                } finally {
                    HttpURLConnection c = conn;
                    conn = null;
                    if (c != null) c.disconnect();
                }
                if (!running) break;
                long sleepSec;
                if (http == 403) {
                    status("PC kodi noto'g'ri");
                    sleepSec = 60;
                } else {
                    status("PC kutilmoqda");
                    backoff = backoff == 0 ? 2 : Math.min(backoff * 2, 30);
                    sleepSec = backoff;
                }
                try {
                    Thread.sleep(sleepSec * 1000);
                } catch (InterruptedException e) {
                    break;
                }
            }
        }
    }

    private void finishTranscriptionError(int jobId, Exception e) {
        if (!isActiveTranscription(jobId)) return;
        toast(e.getMessage() != null ? e.getMessage() : "Transcription failed");
        finishTranscriptionJob();
    }

    private void finishTranscriptionTimeout(int jobId) {
        if (!isActiveTranscription(jobId)) return;
        if (currentTranscription != null) {
            // an idea item is never interrupted: post + remove must finish (chain calls have hard deadlines)
            currentTranscription.cancel(!ideaJob);
            currentTranscription = null;
        }
        if (ideaJob) {
            // the audio is already on disk: the drain retries it, nothing is lost
            toast("Gemini sekin. Ovoz navbatda");
            TickTickPoster.buzzQueued(this);
            finishTranscriptionJob();
            drain(false);
            return;
        }
        toast("Gemini timeout. Qayta urinib ko'ring");
        finishTranscriptionJob();
    }

    private void finishTranscriptionJob() {
        clearTranscriptionTimeout();
        releaseWakeLock();
        ideaJob = false;
        currentTranscription = null;
        updateNotification("Ready");
        busy = false;
    }

    private boolean isActiveTranscription(int jobId) {
        return busy && transcriptionJobId == jobId;
    }

    private void clearTranscriptionTimeout() {
        if (currentTranscriptionTimeout != null) {
            main.removeCallbacks(currentTranscriptionTimeout);
            currentTranscriptionTimeout = null;
        }
    }

    private Notification notification(String text) {
        NotificationManager nm = (NotificationManager) getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel(
                CHANNEL_ID, "Gemini Mic", NotificationManager.IMPORTANCE_LOW));
        return new Notification.Builder(this, CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_mic_24)
                .setContentTitle("Gemini Mic")
                .setContentText(text)
                .setOngoing(true)
                .build();
    }

    private void updateNotification(String text) {
        notificationText = text;
        ((NotificationManager) getSystemService(NotificationManager.class))
                .notify(NOTIFICATION_ID, notification(
                        pcStatus == null ? text : text + " · " + pcStatus));
    }

    private void startMicForeground(String text) {
        Notification n = notification(text);
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(NOTIFICATION_ID, n, 128);
        } else {
            startForeground(NOTIFICATION_ID, n);
        }
    }

    void toast(String msg) {
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show();
    }

    // Inner class: amplitude sampler Runnable
    private class AmplitudeRunnable implements Runnable {
        @Override
        public void run() {
            if (recording && recorder != null) {
                try {
                    peakAmplitude = Math.max(peakAmplitude, recorder.getMaxAmplitude());
                } catch (Exception ignored) {
                }
                main.postDelayed(this, AMPLITUDE_SAMPLE_MS);
            }
        }
    }
}
