package com.autosmart.geminimic;

import android.content.Context;
import android.os.Build;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.os.VibratorManager;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.FileWriter;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/**
 * Idea capture (owner 2026-11-08): a Volume-Down hold on the phone saves what
 * he says as a raw task in TickTick "📥 Kiruvchi" instead of typing it into a
 * field. The TickTick token + kiruvchi projectId arrive WITHOUT typing from
 * the PC relay: GET &lt;pc&gt;/ticktick?token=&lt;relay token&gt; (same auth
 * style as the /cmd long-poll). Any failed post goes to a local jsonl queue
 * and is retried on the next capture / every 5 min while the service lives.
 * Feedback is vibration only (the phone screen is broken).
 */
final class TickTickPoster {

    static final String QUEUE_FILE = "idea-queue.jsonl";
    private static final String TASK_URL = "https://api.ticktick.com/open/v1/task";
    private static final int TIMEOUT_MS = 15000;
    private static final int RELAY_TIMEOUT_MS = 10000;
    private static final Object QUEUE_LOCK = new Object();  // live take appends while the drain rewrites

    enum Result { SAVED, QUEUED }

    private TickTickPoster() {
    }

    /**
     * Hand over one idea: post (queue on failure). atMs = when the take STARTED
     * (the "[manba: telefon HH:mm]" line). The text queue is flushed by the
     * drain (retryQueue), not here, so audio items keep their order.
     */
    static Result deliver(Context ctx, String text, long atMs) {
        if (postWithRefresh(ctx, text, atMs)) return Result.SAVED;
        enqueue(ctx, text, atMs);
        IdeaDrain.schedule(ctx);  // the job flushes the text queue when the net is back
        return Result.QUEUED;
    }

    /** Retry queued ideas oldest-first; a line is removed only after a 2xx post. */
    static void retryQueue(Context ctx) {
        File queue = queueFile(ctx);
        while (true) {
            String line = null;
            synchronized (QUEUE_LOCK) {
                for (String l : readLines(queue)) {
                    if (textOf(l) != null) { line = l; break; }  // unreadable line: leave it, skip
                }
            }
            if (line == null) return;
            if (!postWithRefresh(ctx, textOf(line), atOf(line))) return;  // still offline: keep order
            synchronized (QUEUE_LOCK) {  // persisted only after the 2xx; re-read: a new idea may have been appended
                List<String> lines = readLines(queue);
                lines.remove(line);
                writeLines(queue, lines);
            }
        }
    }

    static int queuedCount(Context ctx) {
        return readLines(queueFile(ctx)).size();
    }

    /**
     * GET &lt;pc&gt;/ticktick?token=&lt;relay token&gt; -> {"access_token","kiruvchi_id"};
     * store both in Prefs. Returns true when usable values were stored.
     */
    static boolean fetchPairing(Context ctx) {
        String code = Prefs.pcCode(ctx);
        if (code.isEmpty()) return false;
        HttpURLConnection conn = null;
        try {
            conn = (HttpURLConnection) new URL(pcBase(Prefs.pcUrl(ctx)) + "/ticktick?token="
                    + URLEncoder.encode(code, "UTF-8")).openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(RELAY_TIMEOUT_MS);
            conn.setReadTimeout(RELAY_TIMEOUT_MS);
            if (conn.getResponseCode() != 200) return false;
            InputStream in = conn.getInputStream();
            ByteArrayOutputStream buf = new ByteArrayOutputStream();
            byte[] chunk = new byte[1024];
            int n;
            while ((n = in.read(chunk)) > 0) buf.write(chunk, 0, n);
            in.close();
            JSONObject reply = new JSONObject(buf.toString("UTF-8"));
            String token = reply.optString("access_token", "");
            String project = reply.optString("kiruvchi_id", "");
            if (token.isEmpty() || project.isEmpty()) return false;
            Prefs.saveTickTick(ctx, token, project);
            return true;
        } catch (Exception e) {
            return false;
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    /** POST with the stored token; one pairing refresh + retry after a 401. */
    private static boolean postWithRefresh(Context ctx, String text, long atMs) {
        String token = Prefs.ticktickToken(ctx);
        String project = Prefs.ticktickProject(ctx);
        if (token.isEmpty() || project.isEmpty()) {
            if (!fetchPairing(ctx)) return false;
            token = Prefs.ticktickToken(ctx);
            project = Prefs.ticktickProject(ctx);
            if (token.isEmpty() || project.isEmpty()) return false;
        }
        int code = httpPostTask(token, project, text, atMs);
        if (code == 401 && fetchPairing(ctx)) {
            token = Prefs.ticktickToken(ctx);
            project = Prefs.ticktickProject(ctx);
            if (!token.isEmpty() && !project.isEmpty()) {
                code = httpPostTask(token, project, text, atMs);  // retry the post once
            }
        }
        return code >= 200 && code < 300;
    }

    /** POST the task JSON; returns the HTTP code, or -1 on a network error. */
    private static int httpPostTask(String token, String projectId, String text, long atMs) {
        HttpURLConnection conn = null;
        try {
            JSONObject body = new JSONObject()
                    .put("title", title(text))
                    .put("content", text + "\n\n[manba: telefon "
                            + new SimpleDateFormat("HH:mm", Locale.ROOT).format(new Date(atMs)) + "]")
                    .put("projectId", projectId);
            conn = (HttpURLConnection) new URL(TASK_URL).openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(TIMEOUT_MS);
            conn.setReadTimeout(TIMEOUT_MS);
            conn.setDoOutput(true);
            conn.setRequestProperty("Authorization", "Bearer " + token);
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            OutputStream out = conn.getOutputStream();
            try {
                out.write(body.toString().getBytes(StandardCharsets.UTF_8));
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

    private static String title(String text) {
        String flat = text.replaceAll("\\s+", " ").trim();
        return flat.length() <= 60 ? flat : flat.substring(0, 60);
    }

    private static File queueFile(Context ctx) {
        return new File(ctx.getFilesDir(), QUEUE_FILE);
    }

    private static void enqueue(Context ctx, String text, long atMs) {
        synchronized (QUEUE_LOCK) {
            try {
                JSONObject line = new JSONObject()
                        .put("text", text).put("at", atMs);
                FileWriter w = new FileWriter(queueFile(ctx), true);
                try {
                    w.write(line.toString() + "\n");
                } finally {
                    w.close();
                }
            } catch (Exception ignored) {
            }
        }
    }

    /** Take start time of a queued line (older lines carry the enqueue time). */
    private static long atOf(String line) {
        try {
            return new JSONObject(line).optLong("at", System.currentTimeMillis());
        } catch (Exception e) {
            return System.currentTimeMillis();
        }
    }

    private static String textOf(String line) {
        try {
            String text = new JSONObject(line).optString("text", "");
            return text.trim().isEmpty() ? null : text;
        } catch (Exception e) {
            return null;
        }
    }

    private static List<String> readLines(File f) {
        List<String> lines = new ArrayList<>();
        if (!f.exists()) return lines;
        try {
            BufferedReader r = new BufferedReader(
                    new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8));
            try {
                String line;
                while ((line = r.readLine()) != null) {
                    if (!line.trim().isEmpty()) lines.add(line);
                }
            } finally {
                r.close();
            }
        } catch (Exception ignored) {
        }
        return lines;
    }

    private static void writeLines(File f, List<String> lines) {
        try {
            FileOutputStream out = new FileOutputStream(f, false);
            try {
                for (String line : lines) {
                    out.write((line + "\n").getBytes(StandardCharsets.UTF_8));
                }
            } finally {
                out.close();
            }
        } catch (Exception ignored) {
        }
    }

    /** pc_url without trailing slashes; /ticktick hangs off it like /cmd and /ack. */
    private static String pcBase(String pcUrl) {
        String u = pcUrl.trim();
        while (u.endsWith("/")) u = u.substring(0, u.length() - 1);
        return u;
    }

    // Vibration feedback (screen is broken: this is the only channel)

    /** Start of recording: one short 60 ms. */
    static void buzzStart(Context ctx) {
        waveform(ctx, new long[]{0, 60});
    }

    /** Saved (2xx): two short 60 ms. */
    static void buzzSaved(Context ctx) {
        waveform(ctx, new long[]{0, 60, 120, 60});
    }

    /** Queued (post failed): three long 400 ms. */
    static void buzzQueued(Context ctx) {
        waveform(ctx, new long[]{0, 400, 200, 400, 200, 400});
    }

    private static void waveform(Context ctx, long[] pattern) {
        try {
            Vibrator v;
            if (Build.VERSION.SDK_INT >= 31) {
                VibratorManager vm =
                        (VibratorManager) ctx.getSystemService(Context.VIBRATOR_MANAGER_SERVICE);
                v = vm != null ? vm.getDefaultVibrator() : null;
            } else {
                v = (Vibrator) ctx.getSystemService(Context.VIBRATOR_SERVICE);
            }
            if (v != null) v.vibrate(VibrationEffect.createWaveform(pattern, -1));
        } catch (Exception ignored) {
        }
    }
}
