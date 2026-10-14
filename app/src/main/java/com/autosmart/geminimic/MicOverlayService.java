package com.autosmart.geminimic;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.media.MediaRecorder;
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

public class MicOverlayService extends Service {

    private static MicOverlayService instance;

    private static final long AMPLITUDE_SAMPLE_MS = 150;
    private static final String CHANNEL_ID = "gemini_mic";
    private static final long MAX_RECORDING_MS = 60000;
    private static final long MIN_RECORDING_MS = 650;
    private static final int NOTIFICATION_ID = 41;
    private static final int SILENCE_PEAK_THRESHOLD = 600;
    private static final long TRANSCRIBE_TIMEOUT_MS = 75000;

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
    PowerManager.WakeLock wakeLock;

    public MicOverlayService() {
        this.main = new Handler(Looper.getMainLooper());
        this.worker = Executors.newCachedThreadPool();
        this.autoStopRecording = () -> {
            if (recording && !busy) {
                toast("Auto-stopping at 60 seconds");
                stopAndTranscribe();
            }
        };
        this.sampleAmplitude = new AmplitudeRunnable();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        // Once the mic service is up, the post-boot "tap to arm" nudge is done.
        NotificationManager nm = (NotificationManager) getSystemService(NotificationManager.class);
        if (nm != null) {
            nm.cancel(VoiceInputAccessibilityService.ARM_NOTIFICATION_ID);
        }
        startMicForeground("Ready");
        restartPcPoller();
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
        stopRecordingQuietly();
        worker.shutdownNow();
        super.onDestroy();
    }

    static boolean isRunning() {
        return instance != null;
    }

    static void volumeStart() {
        MicOverlayService svc = instance;
        if (svc != null) {
            svc.main.post(svc::startRecording);
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
        if (on && pcPoller != null && pcPoller.url.equals(url) && pcPoller.code.equals(code)) {
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

    /** PC said "start": record, then tell the PC whether the mic is live. */
    private void pcStart(PcPoller poller, long seq) {
        if (poller != pcPoller) return;
        boolean ok = startRecording();  // refuses when already recording or busy
        if (ok) {
            pcRecording = true;
            try {
                PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
                wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "GeminiMic:pcRecording");
                wakeLock.acquire(MAX_RECORDING_MS + 5000);
            } catch (Exception ignored) {
                wakeLock = null;
            }
        }
        final String state = ok ? "recording" : "error";
        worker.submit(() -> postAck(poller.url, poller.code, state, seq));
    }

    private void pcStop() {
        // only a PC-started recording: a volume-key recording is never the PC's to end
        if (recording && pcRecording && !busy) stopAndTranscribe();
    }

    private void pcCancel() {
        if (recording && pcRecording) cancelRecording();
    }

    private void cancelRecording() {
        File audioFile = currentFile;
        try {
            if (recorder != null) recorder.stop();
        } catch (Exception ignored) {
        }
        stopRecordingQuietly();
        if (audioFile != null) {
            audioFile.delete();
        }
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
            recorder.setAudioSamplingRate(44100);
            recorder.setAudioEncodingBitRate(96000);
            recorder.setOutputFile(currentFile.getAbsolutePath());
            recorder.prepare();
            recorder.start();
            recording = true;
            recordingStartedAt = System.currentTimeMillis();
            peakAmplitude = 0;
            main.postDelayed(autoStopRecording, MAX_RECORDING_MS);
            main.postDelayed(sampleAmplitude, AMPLITUDE_SAMPLE_MS);
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
        long duration = System.currentTimeMillis() - recordingStartedAt;
        try {
            recorder.stop();
        } catch (Exception ignored) {
        }
        stopRecordingQuietly();
        if (audioFile == null || !audioFile.exists()) {
            toast("No audio");
            return;
        }
        if (duration < MIN_RECORDING_MS) {
            audioFile.delete();
            toast("Hold longer");
            return;
        }
        if (peakAmplitude < SILENCE_PEAK_THRESHOLD) {
            audioFile.delete();
            toast("Ovoz eshitilmadi");
            return;
        }
        busy = true;
        updateNotification("Transcribing");
        final int jobId = ++transcriptionJobId;
        currentTranscriptionTimeout = () -> finishTranscriptionTimeout(jobId);
        main.postDelayed(currentTranscriptionTimeout, TRANSCRIBE_TIMEOUT_MS);
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

    private void stopRecordingQuietly() {
        recording = false;
        pcRecording = false;
        if (wakeLock != null) {
            try { if (wakeLock.isHeld()) wakeLock.release(); } catch (Exception ignored) {}
            wakeLock = null;
        }
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
            worker.submit(() -> {
                int code = sendToPc(pcUrl, pcCode, text);
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

    /** POST {"token","state","seq"} to <pcUrl>/ack; the PC beeps START on "recording". */
    private static void postAck(String pcUrl, String code, String state, long seq) {
        HttpURLConnection conn = null;
        try {
            JSONObject body = new JSONObject().put("token", code).put("state", state).put("seq", seq);
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
     * Outbound long-poll to the PC: GET <pcUrl>/cmd and run start/stop/cancel on
     * the main thread. Never holds a wake lock; backs off 2,4,8..30 s on errors.
     */
    private class PcPoller extends Thread {
        final String url;
        final String code;
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
                            + URLEncoder.encode(code, "UTF-8") + "&wait=20").openConnection();
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
                        String cmd = reply.optString("cmd", "none");
                        long seq = reply.optLong("seq", 0);
                        backoff = 0;
                        status("PC bilan ulangan");
                        if (!running) break;
                        if ("start".equals(cmd)) {
                            main.post(() -> pcStart(this, seq));
                        } else if ("stop".equals(cmd)) {
                            main.post(MicOverlayService.this::pcStop);
                        } else if ("cancel".equals(cmd)) {
                            main.post(MicOverlayService.this::pcCancel);
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
            currentTranscription.cancel(true);
            currentTranscription = null;
        }
        toast("Gemini timeout. Qayta urinib ko'ring");
        finishTranscriptionJob();
    }

    private void finishTranscriptionJob() {
        clearTranscriptionTimeout();
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
