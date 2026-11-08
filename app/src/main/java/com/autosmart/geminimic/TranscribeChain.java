package com.autosmart.geminimic;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * Model chain for an idea take (owner 2026-11-08: "if the model is busy, switch
 * to a backup model or retry until it works"). Pure Java (no Android imports) so
 * it compiles and is tested on the PC: the HTTP call and the JSON reading are
 * injected through {@link Poster}.
 *
 * Every call has a HARD deadline (PC lesson: a 144 s take died because its
 * upload stalled; HttpURLConnection has no write timeout and cancelling a
 * Future does not unblock a socket write). At the deadline the chain calls
 * {@link Poster#abort()} from another thread (the real poster disconnects the
 * connection) and treats the call as a retryable failure.
 */
final class TranscribeChain {

    static final String[] DEFAULT_ORDER = {"gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.8-flash"};
    /** Poster returns this instead of text when the model said NO_SPEECH. */
    static final String NO_SPEECH = "\u0000NO_SPEECH";
    static final int TRIES_PER_MODEL = 2;
    static final int CONNECT_MS = 15000;
    static final int SAME_MODEL_BACKOFF_MS = 2000;
    static final int NEXT_MODEL_BACKOFF_MS = 5000;

    private TranscribeChain() {
    }

    /** One model call. Returns the cleaned text, or {@link #NO_SPEECH}. */
    interface Poster {
        String post(String model, int readTimeoutMs) throws Exception;

        /** Called from another thread at the deadline: unblock a stalled call. */
        default void abort() {
        }
    }

    interface Sleeper {
        void sleep(long ms) throws InterruptedException;
    }

    /** Non-2xx answer from the API. */
    static final class HttpException extends Exception {
        final int code;

        HttpException(int code, String message) {
            super(message);
            this.code = code;
        }
    }

    /** 200 answer that is unusable (blocked / no candidates). */
    static final class BadAnswer extends Exception {
        BadAnswer(String message) {
            super(message);
        }
    }

    /** Try again later: the audio must be kept. */
    static final class Retryable extends Exception {
        Retryable(String message, Throwable cause) {
            super(message, cause);
        }
    }

    /** Retrying cannot help (bad key): the chain stopped, the audio must be kept. */
    static final class Fatal extends Exception {
        Fatal(String message) {
            super(message);
        }
    }

    /** Every model heard silence: the take was silence, drop it. */
    static final class NoSpeech extends Exception {
        NoSpeech() {
            super("Ovoz eshitilmadi");
        }
    }

    /** Configured model first, then the backups; duplicates skipped. */
    static String[] models(String primary) {
        List<String> out = new ArrayList<>();
        if (primary != null && !primary.trim().isEmpty()) out.add(primary.trim());
        for (String m : DEFAULT_ORDER) {
            if (!out.contains(m)) out.add(m);
        }
        return out.toArray(new String[0]);
    }

    static int readTimeoutMs(long audioSeconds) {
        return (int) (30000 + 300 * Math.max(0, audioSeconds));
    }

    /** Hard per-call deadline (upload + wait + download): 45 s + 0.5 s per audio second. */
    static long callDeadlineMs(long audioSeconds) {
        return 45000 + 500 * Math.max(0, audioSeconds);
    }

    /** The PC's guard: more text than anyone can speak (30 chars/s + 30) is a model monologue. */
    static boolean tooLong(String text, long audioSeconds) {
        return text.length() > 30L * Math.max(1, audioSeconds) + 30;
    }

    /** Worst case of {@link #run}: every try runs to its hard deadline, plus all backoffs. */
    static long worstCaseMs(int modelCount, long audioSeconds) {
        long tries = (long) modelCount * TRIES_PER_MODEL;
        long backoff = (long) modelCount * (TRIES_PER_MODEL - 1) * SAME_MODEL_BACKOFF_MS
                + (long) (modelCount - 1) * NEXT_MODEL_BACKOFF_MS;
        return tries * callDeadlineMs(audioSeconds) + backoff;
    }

    static String run(String[] models, long audioSeconds, Poster poster) throws Exception {
        return run(models, audioSeconds, poster, Thread::sleep, callDeadlineMs(audioSeconds));
    }

    static String run(String[] models, long audioSeconds, Poster poster, Sleeper sleeper)
            throws Exception {
        return run(models, audioSeconds, poster, sleeper, callDeadlineMs(audioSeconds));
    }

    static String run(String[] models, long audioSeconds, Poster poster, Sleeper sleeper,
                      long deadlineMs) throws Exception {
        ExecutorService calls = Executors.newCachedThreadPool(r -> {
            Thread t = new Thread(r, "GeminiMic-call");
            t.setDaemon(true);
            return t;
        });
        try {
            return runChain(models, audioSeconds, poster, sleeper, deadlineMs, calls);
        } finally {
            calls.shutdownNow();
        }
    }

    private static String call(Poster poster, String model, int readTimeout, long deadlineMs,
                               ExecutorService calls) throws Exception {
        Future<String> f = calls.submit(() -> poster.post(model, readTimeout));
        try {
            return f.get(deadlineMs, TimeUnit.MILLISECONDS);
        } catch (TimeoutException e) {
            try {
                poster.abort();
            } catch (RuntimeException ignored) {
            }
            f.cancel(true);
            throw new IOException("call deadline " + deadlineMs + " ms");
        } catch (ExecutionException e) {
            Throwable c = e.getCause();
            if (c instanceof Exception) throw (Exception) c;
            throw e;
        } catch (InterruptedException e) {
            try {
                poster.abort();
            } catch (RuntimeException ignored) {
            }
            f.cancel(true);
            throw e;
        }
    }

    private static String runChain(String[] models, long audioSeconds, Poster poster,
                                   Sleeper sleeper, long deadlineMs, ExecutorService calls)
            throws Exception {
        int readTimeout = readTimeoutMs(audioSeconds);
        int silent = 0;
        int rejected = 0;
        Exception last = null;
        boolean first = true;
        for (String model : models) {
            boolean heardSilence = false;
            boolean rejectedModel = false;
            for (int t = 0; t < TRIES_PER_MODEL; t++) {
                if (!first) sleeper.sleep(t > 0 ? SAME_MODEL_BACKOFF_MS : NEXT_MODEL_BACKOFF_MS);
                first = false;
                String text;
                try {
                    text = call(poster, model, readTimeout, deadlineMs, calls);
                } catch (InterruptedException e) {
                    throw e;
                } catch (HttpException e) {
                    last = e;
                    if (e.code == 401 || e.code == 403) {
                        throw new Fatal("Gemini kaliti qabul qilinmadi (" + e.code + ")");
                    }
                    // 400/404 and other 4xx (not 408/429): this model rejects the
                    // request (e.g. a thinking setting it does not know) - retrying
                    // the same model cannot help, the next model may accept it.
                    if (e.code >= 400 && e.code < 500 && e.code != 408 && e.code != 429) {
                        rejectedModel = true;
                        break;
                    }
                    continue;  // 408/429/5xx: busy model, try again / next model
                } catch (Exception e) {
                    last = e;  // IOException, deadline, BadAnswer, parse trouble: retryable
                    continue;
                }
                if (NO_SPEECH.equals(text)) {
                    heardSilence = true;
                    break;
                }
                if (text == null || text.trim().isEmpty()) {
                    last = new BadAnswer("empty text");
                    continue;
                }
                if (tooLong(text, audioSeconds)) {
                    last = new BadAnswer("answer longer than the audio can hold");
                    break;  // a monologue repeats: go to the next model
                }
                return text;
            }
            if (heardSilence) silent++;
            if (rejectedModel) rejected++;
        }
        if (silent == models.length) throw new NoSpeech();
        if (rejected == models.length) {
            throw new Fatal("Hamma model so'rovni rad etdi: "
                    + (last != null ? last.getMessage() : ""));
        }
        throw new Retryable("Transkripsiya bo'lmadi: "
                + (last != null ? last.getMessage() : "no answer"), last);
    }
}
