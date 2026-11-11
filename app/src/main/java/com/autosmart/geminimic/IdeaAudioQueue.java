package com.autosmart.geminimic;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Write-ahead audio queue for idea takes (owner 2026-11-08): the recording is
 * moved into idea-audio/yyyyMMdd-HHmmss.aac with a sidecar .json BEFORE
 * transcription and removed only after its text was handed over (posted or in
 * the text queue). Pure Java so the logic is tested on the PC.
 */
final class IdeaAudioQueue {

    static final String DIR_NAME = "idea-audio";
    static final int FAILS_BEFORE_SPACING = 3;
    static final long SPACED_RETRY_MS = 15 * 60 * 1000;
    static final long MIN_GAP_MS = 60 * 1000;  // not again right after a failure (unless forced)

    private IdeaAudioQueue() {
    }

    static final class Item {
        final File audio;
        final File json;   // may be absent on disk (best effort)
        final long atMs;   // take START
        final long ms;     // duration
        int fails;
        long lastTry;
        String lastError = "";

        Item(File audio, File json, long atMs, long ms, int fails, long lastTry) {
            this.audio = audio;
            this.json = json;
            this.atMs = atMs;
            this.ms = ms;
            this.fails = fails;
            this.lastTry = lastTry;
        }

        String name() {
            return audio.getName();
        }

        long seconds() {
            return Math.max(1, (ms + 999) / 1000);
        }
    }

    /** Moves the audio into dir (copy if rename fails) and writes the sidecar. Never null. */
    static Item store(File dir, File audio, long startMs, long durationMs) {
        dir.mkdirs();
        String stamp = new SimpleDateFormat("yyyyMMdd-HHmmss", Locale.ROOT).format(new Date(startMs));
        File dest = new File(dir, stamp + ".aac");
        for (int n = 1; dest.exists(); n++) dest = new File(dir, stamp + "-" + n + ".aac");
        File json = new File(dir, dest.getName().replaceAll("\\.aac$", ".json"));
        Item item = new Item(dest, json, startMs, durationMs, 0, 0);
        writeSidecar(item);
        if (!audio.renameTo(dest)) {
            try {
                Files.copy(audio.toPath(), dest.toPath(), StandardCopyOption.REPLACE_EXISTING);
                audio.delete();
            } catch (IOException e) {
                // disk trouble: keep working on the original file, it is still on disk
                return new Item(audio, json, startMs, durationMs, 0, 0);
            }
        }
        return item;
    }

    /** Oldest first (file names are the take start time). */
    static List<Item> list(File dir) {
        List<Item> out = new ArrayList<>();
        File[] files = dir.listFiles((d, n) -> n.endsWith(".aac"));
        if (files == null) return out;
        Arrays.sort(files);
        for (File f : files) {
            File json = new File(dir, f.getName().replaceAll("\\.aac$", ".json"));
            out.add(readSidecar(f, json));
        }
        return out;
    }

    static int count(File dir) {
        File[] files = dir.listFiles((d, n) -> n.endsWith(".aac"));
        return files == null ? 0 : files.length;
    }

    /** True when the item may be tried now. force (network came back) ignores the spacing. */
    static boolean due(Item item, long now, boolean force) {
        if (force) return true;
        long gap = item.fails >= FAILS_BEFORE_SPACING ? SPACED_RETRY_MS : MIN_GAP_MS;
        return now - item.lastTry >= gap;
    }

    static void markFailed(Item item, long now, String reason) {
        item.fails++;
        item.lastTry = now;
        item.lastError = sanitizeReason(reason, null);
        writeSidecar(item);
    }

    /** Reason for storage/display: no API key (cut at "key="), no quotes/control chars, <= 200 chars. */
    static String sanitizeReason(String reason, String fallback) {
        String r = reason == null || reason.trim().isEmpty() ? fallback : reason;
        if (r == null) return "";
        int k = r.indexOf("key=");
        if (k >= 0) r = r.substring(0, k);
        r = r.replaceAll("[\\p{Cntrl}\"\\\\]", " ").trim();
        return r.length() > 200 ? r.substring(0, 200) : r;
    }

    /** True when the failure is the network / the key (every item would fail): the pass must stop. */
    static boolean isNetworkOrKey(Throwable t) {
        for (int i = 0; t != null && i < 10; i++, t = t.getCause()) {
            if (t instanceof java.net.UnknownHostException || t instanceof java.net.SocketTimeoutException
                    || t instanceof java.net.ConnectException) return true;
            String m = t.getMessage();
            if (m != null && (m.contains("Missing Gemini API key") || m.contains("kaliti qabul qilinmadi"))) return true;
        }
        return false;
    }

    static void remove(Item item) {
        item.audio.delete();
        if (item.json != null) item.json.delete();
    }

    private static void writeSidecar(Item item) {
        if (item.json == null) return;
        String iso = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.ROOT)
                .format(new Date(item.atMs));
        String body = "{\"at\":\"" + iso + "\",\"atMs\":" + item.atMs + ",\"ms\":" + item.ms
                + ",\"fails\":" + item.fails + ",\"lastTry\":" + item.lastTry
                + ",\"lastError\":\"" + (item.lastError == null ? "" : item.lastError) + "\"}";
        try {
            FileOutputStream out = new FileOutputStream(item.json, false);
            try {
                out.write(body.getBytes(StandardCharsets.UTF_8));
            } finally {
                out.close();
            }
        } catch (IOException ignored) {
        }
    }

    private static Item readSidecar(File audio, File json) {
        long atMs = audio.lastModified();
        long ms = 0;
        int fails = 0;
        long lastTry = 0;
        String lastError = "";
        try {
            String s = new String(Files.readAllBytes(json.toPath()), StandardCharsets.UTF_8);
            atMs = num(s, "atMs", atMs);
            ms = num(s, "ms", 0);
            fails = (int) num(s, "fails", 0);
            lastTry = num(s, "lastTry", 0);
            Matcher e = Pattern.compile("\"lastError\"\\s*:\\s*\"([^\"]*)\"").matcher(s);
            if (e.find()) lastError = e.group(1);
        } catch (IOException ignored) {
            // no sidecar: file time, duration estimated from the size below
        }
        if (ms <= 0) ms = Math.max(1000, audio.length() * 8000L / 48000L);  // 48 kbps estimate
        Item item = new Item(audio, json, atMs, ms, fails, lastTry);
        item.lastError = lastError;
        return item;
    }

    private static long num(String s, String key, long dflt) {
        Matcher m = Pattern.compile("\"" + key + "\"\\s*:\\s*(-?\\d+)").matcher(s);
        return m.find() ? Long.parseLong(m.group(1)) : dflt;
    }
}
