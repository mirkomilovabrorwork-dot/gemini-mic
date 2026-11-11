package com.autosmart.geminimic;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/** Plain-main local test (no Android SDK, no JUnit). Run: see the handoff CHECKS. */
public class TranscribeChainTest {

    static int failures = 0;

    static void check(String name, boolean ok) {
        System.out.println((ok ? "PASS " : "FAIL ") + name);
        if (!ok) failures++;
    }

    interface Script {
        String answer(String model, int n) throws Exception;
    }

    static class Stub implements TranscribeChain.Poster {
        final List<String> calls = new ArrayList<>();
        final List<Integer> timeouts = new ArrayList<>();
        final Script script;
        final AtomicBoolean aborted = new AtomicBoolean(false);

        Stub(Script s) {
            script = s;
        }

        public String post(String model, int readTimeoutMs) throws Exception {
            calls.add(model);
            timeouts.add(readTimeoutMs);
            return script.answer(model, calls.size());
        }

        public void abort() {
            aborted.set(true);
        }
    }

    static final TranscribeChain.Sleeper NO_SLEEP = ms -> { };
    static final String[] M = {"m1", "m2", "m3"};

    static Throwable run(Stub s, long sec, String[] out) {
        try {
            out[0] = TranscribeChain.run(M, sec, s, NO_SLEEP);
            return null;
        } catch (Throwable t) {
            return t;
        }
    }

    public static void main(String[] args) throws Exception {
        String[] out = new String[1];

        // 429 on model 1 (both tries) -> model 2 answers
        Stub s = new Stub((m, n) -> {
            if (m.equals("m1")) throw new TranscribeChain.HttpException(429, "busy");
            return "salom dunyo";
        });
        Throwable t = run(s, 10, out);
        check("429 on m1 -> m2 answers", t == null && "salom dunyo".equals(out[0])
                && s.calls.equals(List.of("m1", "m1", "m2")));

        // IOException everywhere -> Retryable after 6 tries
        s = new Stub((m, n) -> { throw new IOException("offline"); });
        t = run(s, 10, out);
        check("IOException on all -> Retryable (6 tries)",
                t instanceof TranscribeChain.Retryable && s.calls.size() == 6);

        // 401 -> Fatal at once
        s = new Stub((m, n) -> { throw new TranscribeChain.HttpException(401, "key"); });
        t = run(s, 10, out);
        check("401 -> Fatal at once", t instanceof TranscribeChain.Fatal && s.calls.size() == 1);

        // 400 on m1 only (model rejects config) -> m2 used
        s = new Stub((m, n) -> {
            if (m.equals("m1")) throw new TranscribeChain.HttpException(400, "bad config");
            return "ok matn";
        });
        t = run(s, 10, out);
        check("400 on m1 -> skip to m2 (no retry of m1)", t == null
                && s.calls.equals(List.of("m1", "m2")));

        // 400 everywhere -> Fatal
        s = new Stub((m, n) -> { throw new TranscribeChain.HttpException(400, "bad"); });
        t = run(s, 10, out);
        check("400 on all -> Fatal", t instanceof TranscribeChain.Fatal && s.calls.size() == 3);

        // model-answer guard trips on m1 -> m2 used (10 s audio: limit 330 chars)
        final String monologue = "x".repeat(400);
        s = new Stub((m, n) -> m.equals("m1") ? monologue : "qisqa matn");
        t = run(s, 10, out);
        check("guard trips on m1 -> m2", t == null && "qisqa matn".equals(out[0])
                && s.calls.equals(List.of("m1", "m2")));

        // blocked answer then ok on retry of same model
        s = new Stub((m, n) -> {
            if (n == 1) throw new TranscribeChain.BadAnswer("blocked");
            return "ikkinchi urinish";
        });
        t = run(s, 10, out);
        check("blocked once -> same model retried", t == null && s.calls.equals(List.of("m1", "m1")));

        // empty text twice on m1 -> m2
        s = new Stub((m, n) -> m.equals("m1") ? "  " : "matn bor");
        t = run(s, 10, out);
        check("empty text -> m1 x2 then m2", t == null
                && s.calls.equals(List.of("m1", "m1", "m2")));

        // NO_SPEECH on all -> NoSpeech
        s = new Stub((m, n) -> TranscribeChain.NO_SPEECH);
        t = run(s, 10, out);
        check("NO_SPEECH on all -> NoSpeech", t instanceof TranscribeChain.NoSpeech
                && s.calls.size() == 3);

        // NO_SPEECH on m1, network error on rest -> Retryable (not silence)
        s = new Stub((m, n) -> {
            if (m.equals("m1")) return TranscribeChain.NO_SPEECH;
            throw new IOException("x");
        });
        t = run(s, 10, out);
        check("NO_SPEECH + errors -> Retryable", t instanceof TranscribeChain.Retryable);

        // read timeout for 300 s audio = 120 s
        s = new Stub((m, n) -> "matn");
        run(s, 300, out);
        check("read timeout 300 s audio = 120000 ms", s.timeouts.get(0) == 120000);

        // models(): duplicates skipped, primary first
        check("models order", String.join(",", TranscribeChain.models("gemini-3.5-flash"))
                .equals("gemini-3.5-flash,gemini-3.7-flash,gemini-3.8-flash"));
        check("models default", String.join(",", TranscribeChain.models("gemini-3.7-flash"))
                .equals("gemini-3.7-flash,gemini-3.5-flash,gemini-3.8-flash"));

        // stalled call (never returns) is abandoned at its deadline, abort() called, next try used
        final Object forever = new Object();
        Stub stall = new Stub((m, n) -> {
            if (n == 1) {
                synchronized (forever) {
                    forever.wait();  // simulates a stalled upload
                }
            }
            return "ikkinchi urinishda";
        });
        long t0 = System.currentTimeMillis();
        String r = TranscribeChain.run(M, 10, stall, NO_SLEEP, 300);
        long took = System.currentTimeMillis() - t0;
        check("stalled call abandoned at deadline, abort() called, retry answers",
                "ikkinchi urinishda".equals(r) && stall.aborted.get() && stall.calls.size() == 2
                        && took >= 250 && took < 3000);

        // everything stalls -> Retryable, finishes in ~6 deadlines, not forever
        Stub allStall = new Stub((m, n) -> {
            synchronized (forever) {
                forever.wait();
            }
            return "";
        });
        t0 = System.currentTimeMillis();
        try {
            TranscribeChain.run(M, 10, allStall, NO_SLEEP, 100);
            check("all stalled -> Retryable", false);
        } catch (TranscribeChain.Retryable e) {
            took = System.currentTimeMillis() - t0;
            check("all stalled -> Retryable within bound", allStall.calls.size() == 6 && took < 5000);
        }

        // worst-case numbers
        System.out.println("worst case 3 models, 300 s take: " + TranscribeChain.worstCaseMs(3, 300) / 1000.0 + " s");
        System.out.println("worst case 3 models, 600 s take: " + TranscribeChain.worstCaseMs(3, 600) / 1000.0 + " s");
        check("worst case formula 300 s", TranscribeChain.worstCaseMs(3, 300) == 6 * 195000L + 16000L);

        queueTests();
        handoffTests();

        System.out.println(failures == 0 ? "ALL PASS" : ("FAILURES: " + failures));
        System.exit(failures == 0 ? 0 : 1);
    }

    static void queueTests() throws Exception {
        File root = Files.createTempDirectory("idea-audio-test").toFile();
        File dir = new File(root, IdeaAudioQueue.DIR_NAME);
        long base = 1_700_000_000_000L;

        File a = new File(root, "speech-a.aac");
        File b = new File(root, "speech-b.aac");
        Files.write(a.toPath(), new byte[]{1, 2, 3});
        Files.write(b.toPath(), new byte[]{4, 5, 6});
        // store the NEWER take first to prove ordering is by take start, not insertion
        IdeaAudioQueue.Item later = IdeaAudioQueue.store(dir, b, base + 60_000, 5000);
        IdeaAudioQueue.Item earlier = IdeaAudioQueue.store(dir, a, base, 7000);

        check("queue: file moved into idea-audio", !a.exists() && !b.exists()
                && earlier.audio.exists() && later.audio.exists());
        List<IdeaAudioQueue.Item> l = IdeaAudioQueue.list(dir);
        check("queue: oldest first by take start", l.size() == 2
                && l.get(0).atMs == base && l.get(1).atMs == base + 60_000);
        check("queue: sidecar keeps start time and duration", l.get(0).ms == 7000
                && l.get(0).seconds() == 7);
        check("queue: count", IdeaAudioQueue.count(dir) == 2);

        // failure keeps the file, persists the count
        long now = base + 10_000_000L;
        IdeaAudioQueue.markFailed(l.get(0), now, "boom");
        IdeaAudioQueue.Item re = IdeaAudioQueue.list(dir).get(0);
        check("queue: failure keeps file, fails persisted", re.audio.exists() && re.fails == 1
                && re.lastTry == now);
        check("queue: not due within 60 s of a failure, due after",
                !IdeaAudioQueue.due(re, now + 30_000, false)
                        && IdeaAudioQueue.due(re, now + 61_000, false));
        check("queue: force (network back) ignores spacing", IdeaAudioQueue.due(re, now + 1, true));

        // 3 failures -> 15 min spacing
        IdeaAudioQueue.markFailed(re, now, "boom");
        IdeaAudioQueue.markFailed(re, now, "boom");
        IdeaAudioQueue.Item three = IdeaAudioQueue.list(dir).get(0);
        check("queue: after 3 fails spaced to 15 min", three.fails == 3
                && !IdeaAudioQueue.due(three, now + 14 * 60_000, false)
                && IdeaAudioQueue.due(three, now + 15 * 60_000, false)
                && IdeaAudioQueue.due(three, now + 1, true));

        // deleted only on remove (after handoff)
        IdeaAudioQueue.remove(three);
        check("queue: remove deletes audio + sidecar", !three.audio.exists()
                && !three.json.exists() && IdeaAudioQueue.count(dir) == 1);

        // same-second collision gets its own name
        File c = new File(root, "speech-c.aac");
        File d = new File(root, "speech-d.aac");
        Files.write(c.toPath(), new byte[]{9});
        Files.write(d.toPath(), new byte[]{8});
        IdeaAudioQueue.Item c1 = IdeaAudioQueue.store(dir, c, base + 5, 1000);
        IdeaAudioQueue.Item d1 = IdeaAudioQueue.store(dir, d, base + 6, 1000);
        check("queue: same-second takes both kept", !c1.name().equals(d1.name())
                && IdeaAudioQueue.count(dir) == 3);
    }

    // finding 1: an interrupt must not land between the post and the remove
    static void handoffTests() throws Exception {
        final List<String> steps = new ArrayList<>();
        Thread.currentThread().interrupt();  // e.g. a timeout / job stop arrives now
        String r = Uninterruptible.call(() -> {
            steps.add("post");
            boolean flagDuringStep = Thread.currentThread().isInterrupted();
            Thread.sleep(20);  // interruptible call inside the step: must NOT throw
            steps.add("remove");
            return flagDuringStep ? "flag-seen" : "clean";
        });
        boolean flagAfter = Thread.interrupted();  // read + clear for the rest of the test
        check("handoff: post+remove both ran under a pending interrupt",
                steps.equals(List.of("post", "remove")) && "clean".equals(r));
        check("handoff: interrupt flag restored afterwards", flagAfter);
        String r2 = Uninterruptible.call(() -> "x");
        check("handoff: no interrupt -> flag stays clear", "x".equals(r2) && !Thread.currentThread().isInterrupted());

        // failure reason: key stripped, capped, sidecar round-trip; network vs item classification
        String red = IdeaAudioQueue.sanitizeReason("HTTP 400 https://x/y:generateContent?key=AIzaSECRET&a=1", null);
        check("reason: nothing after key= survives", !red.contains("AIza") && !red.contains("key="));
        check("reason: null -> fallback class name", "IOException".equals(IdeaAudioQueue.sanitizeReason(null, "IOException")));
        check("reason: capped at 200", IdeaAudioQueue.sanitizeReason("x".repeat(500), null).length() == 200);
        check("class: UnknownHost wrapped in Retryable stops the pass", IdeaAudioQueue.isNetworkOrKey(
                new TranscribeChain.Retryable("t", new java.net.UnknownHostException("h"))));
        check("class: timeout/connect stop the pass", IdeaAudioQueue.isNetworkOrKey(new java.net.SocketTimeoutException())
                && IdeaAudioQueue.isNetworkOrKey(new java.net.ConnectException()));
        check("class: missing key stops the pass", IdeaAudioQueue.isNetworkOrKey(new TranscribeChain.Fatal("Missing Gemini API key")));
        check("class: bad answer / HTTP 400 is an item failure", !IdeaAudioQueue.isNetworkOrKey(new TranscribeChain.BadAnswer("blocked"))
                && !IdeaAudioQueue.isNetworkOrKey(new TranscribeChain.Retryable("t", new TranscribeChain.HttpException(400, "bad"))));
        File d = Files.createTempDirectory("qerr").toFile();
        File a = new File(d, "in.aac");
        Files.write(a.toPath(), new byte[]{1, 2, 3});
        IdeaAudioQueue.Item it = IdeaAudioQueue.store(d, a, 1000L, 2000L);
        IdeaAudioQueue.markFailed(it, 5L, "Gemini error 400 key=ZZZ");
        check("reason: persisted in sidecar and read back", "Gemini error 400".equals(IdeaAudioQueue.list(d).get(0).lastError));
    }
}
