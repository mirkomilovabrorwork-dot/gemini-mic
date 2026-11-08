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

    static void markFailed(Item item, long now) {
        item.fails++;
        item.lastTry = now;
        writeSidecar(item);
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
                + ",\"fails\":" + item.fails + ",\"lastTry\":" + item.lastTry + "}";
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
        try {
            String s = new String(Files.readAllBytes(json.toPath()), StandardCharsets.UTF_8);
            atMs = num(s, "atMs", atMs);
            ms = num(s, "ms", 0);
            fails = (int) num(s, "fails", 0);
            lastTry = num(s, "lastTry", 0);
        } catch (IOException ignored) {
            // no sidecar: file time, duration estimated from the size below
        }
        if (ms <= 0) ms = Math.max(1000, audio.length() * 8000L / 48000L);  // 48 kbps estimate
        return new Item(audio, json, atMs, ms, fails, lastTry);
    }

    private static long num(String s, String key, long dflt) {
        Matcher m = Pattern.compile("\"" + key + "\"\\s*:\\s*(-?\\d+)").matcher(s);
        return m.find() ? Long.parseLong(m.group(1)) : dflt;
    }
}
