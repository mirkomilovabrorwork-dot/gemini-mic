package com.autosmart.geminimic;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.media.MediaRecorder;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.provider.Settings;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.ImageButton;
import android.widget.Toast;

import java.io.File;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

public class MicOverlayService extends Service {

    private static MicOverlayService instance;

    private static final long AMPLITUDE_SAMPLE_MS = 150;
    private static final String CHANNEL_ID = "gemini_mic";
    private static final int COLLAPSED_SIZE_DP = 18;
    private static final int EXPANDED_SIZE_DP = 60;
    private static final long HOLD_TO_RECORD_MS = 300;
    private static final long IDLE_COLLAPSE_MS = 3000;
    private static final long MAX_RECORDING_MS = 60000;
    private static final long MIN_RECORDING_MS = 650;
    private static final int NOTIFICATION_ID = 41;
    private static final int SILENCE_PEAK_THRESHOLD = 600;
    private static final long TRANSCRIBE_TIMEOUT_MS = 75000;

    final Handler main;
    final ExecutorService worker;
    boolean collapsed;

    FrameLayout bubble;
    ImageButton micButton;
    WindowManager.LayoutParams params;
    WindowManager windowManager;

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
    private final Runnable collapseWhenIdle;
    private final Runnable sampleAmplitude;

    public MicOverlayService() {
        this.main = new Handler(Looper.getMainLooper());
        this.worker = Executors.newCachedThreadPool();
        this.collapsed = true;
        this.autoStopRecording = () -> {
            if (recording && !busy) {
                toast("Auto-stopping at 60 seconds");
                stopAndTranscribe();
            }
        };
        this.collapseWhenIdle = () -> {
            if (!recording && !busy) {
                setCollapsed(true);
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
        startMicForeground("Ready");
        windowManager = (WindowManager) getSystemService("window");
        if (Settings.canDrawOverlays(this)) {
            showBubble();
        } else {
            toast("Allow floating button first");
            stopSelf();
        }
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
        main.removeCallbacks(collapseWhenIdle);
        clearTranscriptionTimeout();
        if (currentTranscription != null) {
            currentTranscription.cancel(true);
            currentTranscription = null;
        }
        stopRecordingQuietly();
        if (bubble != null) {
            windowManager.removeView(bubble);
            bubble = null;
        }
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
        scheduleCollapseWhenIdle();
    }

    private void showBubble() {
        collapsed = true;
        int sizePx = dp(18);
        bubble = new FrameLayout(this);
        bubble.setBackground(bubbleBackground(-14326805));

        micButton = new ImageButton(this);
        micButton.setImageResource(R.drawable.ic_mic_24);
        micButton.setBackgroundColor(0);
        micButton.setColorFilter(-1);
        micButton.setFocusable(false);
        micButton.setLongClickable(false);
        micButton.setContentDescription("Gemini Mic");
        micButton.setVisibility(View.INVISIBLE);
        bubble.addView(micButton, new FrameLayout.LayoutParams(-1, -1, Gravity.CENTER));

        params = new WindowManager.LayoutParams(
                sizePx, sizePx,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT);
        params.gravity = Gravity.TOP | Gravity.START;
        params.alpha = Float.intBitsToFloat(1048911544);
        params.x = Prefs.get(this).getInt("bubble_x",
                getResources().getDisplayMetrics().widthPixels - dp(30));
        params.y = Prefs.get(this).getInt("bubble_y", dp(220));
        clampBubblePosition();

        BubbleTouchListener listener = new BubbleTouchListener();
        bubble.setOnTouchListener(listener);
        micButton.setOnTouchListener(listener);
        windowManager.addView(bubble, params);
    }

    private GradientDrawable bubbleBackground(int color) {
        GradientDrawable d = new GradientDrawable();
        d.setShape(GradientDrawable.OVAL);
        d.setColor(color);
        d.setStroke(dp(2), -1);
        return d;
    }

    private int bubbleSizePx() {
        return dp(collapsed ? 18 : 60);
    }

    void setCollapsed(boolean collapse) {
        if (collapse && (recording || busy)) return;
        this.collapsed = collapse;
        if (params == null || bubble == null || windowManager == null) return;

        int screenW = getResources().getDisplayMetrics().widthPixels;
        int sizePx = bubbleSizePx();

        boolean onRight = (params.x + (Math.max(params.width, 1) / 2)) >= (screenW / 2);

        params.width = sizePx;
        params.height = sizePx;
        params.alpha = collapsed ? Float.intBitsToFloat(1048911544) : Float.intBitsToFloat(1065353216);

        int margin = dp(collapsed ? 3 : 8);
        params.x = onRight ? (screenW - sizePx - margin) : margin;
        clampBubblePosition();

        micButton.setVisibility(collapsed ? View.INVISIBLE : View.VISIBLE);

        int color;
        if (recording) {
            color = -2349530;
        } else if (busy) {
            color = -16411031;
        } else {
            color = -14326805;
        }
        setBubbleColor(color);
        windowManager.updateViewLayout(bubble, params);
    }

    private void clampBubblePosition() {
        int w = getResources().getDisplayMetrics().widthPixels;
        int h = getResources().getDisplayMetrics().heightPixels;
        int sz = bubbleSizePx();
        params.x = Math.max(0, Math.min(params.x, w - sz));
        params.y = Math.max(dp(24), Math.min(params.y, h - sz - dp(48)));
    }

    private void snapToNearestEdge() {
        int w = getResources().getDisplayMetrics().widthPixels;
        int h = getResources().getDisplayMetrics().heightPixels;
        int sz = bubbleSizePx();
        params.x = (params.x + sz / 2 >= w / 2) ? (w - sz - dp(8)) : dp(8);
        params.y = Math.max(dp(24), Math.min(params.y, h - sz - dp(48)));
        windowManager.updateViewLayout(bubble, params);
    }

    private void saveBubblePosition() {
        Prefs.get(this).edit().putInt("bubble_x", params.x).putInt("bubble_y", params.y).apply();
    }

    void scheduleCollapseWhenIdle() {
        main.removeCallbacks(collapseWhenIdle);
        if (!recording && !busy) {
            main.postDelayed(collapseWhenIdle, IDLE_COLLAPSE_MS);
        }
    }

    private void setBubbleColor(int color) {
        if (bubble != null) {
            bubble.setBackground(bubbleBackground(color));
        }
    }

    boolean startRecording() {
        if (busy || recording) return false;
        if (checkSelfPermission("android.permission.RECORD_AUDIO") != 0) {
            toast("Allow microphone first");
            return false;
        }
        try {
            main.removeCallbacks(collapseWhenIdle);
            setCollapsed(false);
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
            setBubbleColor(-2349530);
            toast("Recording");
            return true;
        } catch (Exception e) {
            stopRecordingQuietly();
            toast("Could not start mic");
            scheduleCollapseWhenIdle();
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
            scheduleCollapseWhenIdle();
            return;
        }
        if (duration < MIN_RECORDING_MS) {
            audioFile.delete();
            toast("Hold longer");
            scheduleCollapseWhenIdle();
            return;
        }
        if (peakAmplitude < SILENCE_PEAK_THRESHOLD) {
            audioFile.delete();
            toast("Ovoz eshitilmadi");
            scheduleCollapseWhenIdle();
            return;
        }
        busy = true;
        setCollapsed(false);
        setBubbleColor(-16411031);
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
        setBubbleColor(-14326805);
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
        setBubbleColor(-14326805);
        updateNotification("Ready");
        busy = false;
        scheduleCollapseWhenIdle();
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

    int dp(int dp) {
        return Math.round(dp * getResources().getDisplayMetrics().density);
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

    // Inner class: touch listener for bubble and mic button
    private class BubbleTouchListener implements View.OnTouchListener {
        private boolean dragging;
        private boolean holdRecording;
        private boolean pointerDown;
        private int startX;
        private int startY;
        private float touchX;
        private float touchY;

        private final Runnable beginHoldRecording = () -> {
            if (pointerDown && !dragging && !holdRecording && !busy && !recording) {
                if (VoiceInputAccessibilityService.hasActiveTextInput()) {
                    holdRecording = startRecording();
                } else {
                    toast("Avval matn kiritiladigan joyni bosing");
                }
            }
        };

        @Override
        public boolean onTouch(View v, MotionEvent event) {
            switch (event.getAction()) {
                case MotionEvent.ACTION_DOWN:
                    if (collapsed) {
                        setCollapsed(false);
                        scheduleCollapseWhenIdle();
                    } else {
                        main.removeCallbacks(collapseWhenIdle);
                        startX = params.x;
                        startY = params.y;
                        touchX = event.getRawX();
                        touchY = event.getRawY();
                        pointerDown = true;
                        dragging = false;
                        holdRecording = false;
                        main.postDelayed(beginHoldRecording, HOLD_TO_RECORD_MS);
                    }
                    return true;

                case MotionEvent.ACTION_UP:
                case MotionEvent.ACTION_CANCEL:
                    pointerDown = false;
                    main.removeCallbacks(beginHoldRecording);
                    if (holdRecording && recording) {
                        holdRecording = false;
                        stopAndTranscribe();
                    } else if (!dragging) {
                        scheduleCollapseWhenIdle();
                    } else {
                        snapToNearestEdge();
                        saveBubblePosition();
                        scheduleCollapseWhenIdle();
                    }
                    return true;

                case MotionEvent.ACTION_MOVE:
                    if (pointerDown) {
                        int dx = Math.round(event.getRawX() - touchX);
                        int dy = Math.round(event.getRawY() - touchY);
                        if (!holdRecording && (Math.abs(dx) > dp(10) || Math.abs(dy) > dp(10))) {
                            dragging = true;
                            main.removeCallbacks(beginHoldRecording);
                        }
                        if (dragging) {
                            params.x = startX + dx;
                            params.y = startY + dy;
                            windowManager.updateViewLayout(bubble, params);
                        }
                    }
                    return true;

                default:
                    return false;
            }
        }
    }
}
