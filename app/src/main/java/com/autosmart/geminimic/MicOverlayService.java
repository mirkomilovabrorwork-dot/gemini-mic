package com.autosmart.geminimic;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.media.MediaRecorder;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.widget.Toast;

import java.io.File;
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
        if (!VoiceInputAccessibilityService.typeText(text)) {
            toast("Enable auto input first");
        }
        finishTranscriptionJob();
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
        ((NotificationManager) getSystemService(NotificationManager.class))
                .notify(NOTIFICATION_ID, notification(text));
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
