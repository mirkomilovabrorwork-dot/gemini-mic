package com.autosmart.geminimic;

import java.util.concurrent.Callable;

/**
 * Runs the hand-over step (post to TickTick, then delete the audio) with the
 * thread's interrupt flag cleared, and puts the flag back afterwards. A timeout,
 * a job stop or a service shutdown must never land between "the post returned
 * 2xx" and "the audio was removed" (that would post the idea twice). Pure Java.
 */
final class Uninterruptible {

    private Uninterruptible() {
    }

    static <T> T call(Callable<T> step) throws Exception {
        boolean was = Thread.interrupted();  // reads and clears the flag
        try {
            return step.call();
        } finally {
            if (was) Thread.currentThread().interrupt();
        }
    }
}
