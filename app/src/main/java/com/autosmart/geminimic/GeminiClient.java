package com.autosmart.geminimic;

import android.content.Context;
import android.util.Base64;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

final class GeminiClient {

    private static final String FALLBACK_MODEL = "gemini-3-flash-preview";

    private GeminiClient() {
    }

    static String cleanTranscript(String p8) {
        if (p8 != null) {
            String s = p8.trim()
                    .replace("```", "").trim()
                    .replace("**", "").trim()
                    .replaceAll("(?m)^\\s*\\[\\d{1,2}:\\d{2}(?::\\d{2})?\\]\\s*", "")
                    .replaceAll("\\[\\d{1,2}:\\d{2}(?::\\d{2})?\\]\\s*", "")
                    .replaceAll("(?m)^\\s*\\d+[.)]\\s+", "")
                    .trim();
            String lower = s.toLowerCase();
            String[] prefixes = new String[6];
            prefixes[0] = "transcript:";
            prefixes[1] = "transcription:";
            prefixes[2] = "text:";
            prefixes[3] = "the transcript is:";
            prefixes[4] = "here is the transcript:";
            prefixes[5] = "boshqa ovoz:";
            for (int i = 0; i < prefixes.length; i++) {
                String prefix = prefixes[i];
                if (lower.startsWith(prefix)) {
                    s = s.substring(prefix.length()).trim();
                    lower = s.toLowerCase();
                }
            }
            if (((s.startsWith("\"")) && (s.endsWith("\"")))
                    || ((s.startsWith("'")) && (s.endsWith("'")))) {
                s = s.substring(1, s.length() - 1).trim();
            }
            return s;
        } else {
            return "";
        }
    }

    private static String extractText(String body) throws Exception {
        JSONArray candidates = new JSONObject(body).optJSONArray("candidates");
        if (candidates == null || candidates.length() == 0) {
            throw new IllegalStateException("No transcript returned");
        }
        JSONArray parts = candidates.getJSONObject(0)
                .getJSONObject("content")
                .getJSONArray("parts");
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < parts.length(); i++) {
            sb.append(parts.getJSONObject(i).optString("text", ""));
        }
        return sb.toString();
    }

    private static String languageInstruction(Context ctx) {
        String mode = Prefs.languageMode(ctx);
        if ("uz_en".equals(mode)) {
            return "The speaker mixes Uzbek and English, but a sentence may also be entirely English or entirely Uzbek. Transcribe each word in the exact language it was spoken in — never translate or romanize.";
        } else if ("uz_ru".equals(mode)) {
            return "The speaker usually mixes Uzbek and Russian. Preserve both languages exactly as spoken.";
        } else {
            return "The speaker may mix Uzbek, English, and Russian in the same sentence. Preserve each language exactly as spoken.";
        }
    }

    private static String transcriptionPrompt(Context ctx) {
        return "Transcribe this audio for direct typing. "
                + languageInstruction(ctx)
                + "\n\nRules:\n"
                + "- Transcribe ONLY speech that is actually audible in THIS audio clip. If the audio is silent, only background noise or music, or has no intelligible speech, output EXACTLY the token NO_SPEECH and nothing else.\n"
                + "- NEVER invent, guess, or fill in a greeting, a speech, a sample text, or an essay that is not clearly spoken in the audio. It is better to output NO_SPEECH than to output words that were not said.\n"
                + "- Write only the words that were actually spoken. Do not invent, replace, translate, or paraphrase words.\n"
                + "- CRITICAL: This is transcription, NOT translation. NEVER translate speech from one language to another. If the speaker talks in English, write the English words in normal English spelling; NEVER rewrite English using Uzbek/Latin phonetic spelling and NEVER replace an English word with its Uzbek meaning. A whole sentence may be entirely English or entirely Russian — keep it in that language. Write every word in the exact language and script it was actually spoken in.\n"
                + "- Do not add timestamps, numbers, bullets, speaker labels, headings, explanations, quotes, or markdown.\n"
                + "- Add natural punctuation and capitalization so the text is easy to read: start each sentence with a capital letter and end it with a period, question mark, or exclamation mark.\n"
                + "- Do not summarize, rewrite, or turn speech into a task list.\n"
                + "- Uzbek words must be written in natural Uzbek Latin.\n"
                + "- Keep English words exactly in English/Latin when they were spoken.\n"
                + "- Keep Russian words exactly in Cyrillic when they were spoken.\n"
                + "- Do not convert English or Russian words into Uzbek. Do not convert Uzbek words into English or Russian.\n"
                + "- Preserve mixed-language word order as spoken.\n"
                + "- Remove only filler sounds like umm, aa, eee and obvious repeated stutters when they do not change the meaning.\n"
                + "- If a word is impossible to identify, write [noaniq].\n"
                + "- Return only the final plain transcript text.";
    }

    private static String readAll(InputStream in) throws Exception {
        if (in == null) {
            return "";
        }
        StringBuilder sb = new StringBuilder();
        BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
        try {
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
        } finally {
            reader.close();
        }
        return sb.toString();
    }

    private static boolean isRetryable(IllegalStateException e) {
        String msg = e.getMessage();
        return msg != null && (msg.startsWith("Gemini error 404")
                || msg.startsWith("Gemini error 429")
                || msg.startsWith("Gemini error 500")
                || msg.startsWith("Gemini error 503"));
    }

    private static String postGenerateContent(String key, String model, JSONObject body, int readTimeoutMs) throws Exception {
        String urlStr = "https://generativelanguage.googleapis.com/v1beta/models/"
                + model + ":generateContent?key=" + key;
        HttpURLConnection conn = (HttpURLConnection) new URL(urlStr).openConnection();
        try {
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(readTimeoutMs);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            byte[] payload = body.toString().getBytes(StandardCharsets.UTF_8);
            OutputStream out = conn.getOutputStream();
            try {
                out.write(payload);
            } finally {
                out.close();
            }
            int code = conn.getResponseCode();
            InputStream stream;
            if (code >= 200 && code < 300) {
                stream = conn.getInputStream();
            } else {
                stream = conn.getErrorStream();
            }
            String responseBody = readAll(stream);
            if (code < 200 || code >= 300) {
                throw new IllegalStateException("Gemini error " + code + ": " + responseBody);
            }
            conn.disconnect();
            return responseBody;
        } catch (Throwable t) {
            conn.disconnect();
            throw t;
        }
    }

    static String testConnection(Context ctx) throws Exception {
        String key = Prefs.apiKey(ctx);
        if (key.isEmpty()) {
            throw new IllegalStateException("Missing Gemini API key");
        }
        JSONObject request = new JSONObject();
        JSONArray contents = new JSONArray();
        JSONObject content = new JSONObject();
        JSONArray parts = new JSONArray();
        parts.put(new JSONObject().put("text", "Reply with exactly OK."));
        content.put("parts", parts);
        contents.put(content);
        request.put("contents", contents);
        request.put("generationConfig", new JSONObject()
                .put("temperature", 0)
                .put("maxOutputTokens", 8));
        String model = Prefs.model(ctx);
        String raw;
        try {
            raw = postGenerateContent(key, model, request, 30000);
        } catch (IllegalStateException e) {
            if (isRetryable(e) && !FALLBACK_MODEL.equals(model)) {
                raw = postGenerateContent(key, FALLBACK_MODEL, request, 30000);
            } else {
                throw e;
            }
        } catch (java.io.IOException e) {
            if (!FALLBACK_MODEL.equals(model)) {
                raw = postGenerateContent(key, FALLBACK_MODEL, request, 30000);
            } else {
                throw e;
            }
        }
        String result = extractText(raw).trim();
        if (result.isEmpty()) {
            throw new IllegalStateException("Gemini returned empty response");
        }
        return result;
    }

    static String transcribe(Context ctx, File audioFile) throws Exception {
        String key = Prefs.apiKey(ctx);
        if (key.isEmpty()) {
            throw new IllegalStateException("Missing Gemini API key");
        }
        byte[] bytes = Files.readAllBytes(audioFile.toPath());
        if (bytes.length == 0) {
            throw new IllegalStateException("No audio recorded");
        }
        if (bytes.length > 20971520) {
            throw new IllegalStateException("Audio is too long");
        }
        JSONObject request = new JSONObject();
        JSONArray contents = new JSONArray();
        JSONObject content = new JSONObject();
        JSONArray parts = new JSONArray();
        parts.put(new JSONObject().put("text", transcriptionPrompt(ctx)));
        parts.put(new JSONObject().put("inline_data",
                new JSONObject()
                        .put("mime_type", "audio/aac")
                        .put("data", Base64.encodeToString(bytes, Base64.NO_WRAP))));
        content.put("parts", parts);
        contents.put(content);
        request.put("contents", contents);
        request.put("generationConfig", new JSONObject()
                .put("temperature", 0)
                .put("maxOutputTokens", 1024)
                .put("thinkingConfig", new JSONObject().put("thinkingBudget", 0)));
        String model = Prefs.model(ctx);
        String raw;
        try {
            raw = postGenerateContent(key, model, request, 30000);
        } catch (IllegalStateException e) {
            if (isRetryable(e) && !FALLBACK_MODEL.equals(model)) {
                raw = postGenerateContent(key, FALLBACK_MODEL, request, 30000);
            } else {
                throw e;
            }
        } catch (java.io.IOException e) {
            if (!FALLBACK_MODEL.equals(model)) {
                raw = postGenerateContent(key, FALLBACK_MODEL, request, 30000);
            } else {
                throw e;
            }
        }
        String cleaned = cleanTranscript(extractText(raw));
        if (isNoSpeech(cleaned)) {
            throw new IllegalStateException("Ovoz eshitilmadi");
        }
        String transcript = formatParagraphs(cleaned);
        if (transcript.isEmpty()) {
            throw new IllegalStateException("Ovoz eshitilmadi");
        }
        return transcript;
    }

    // The model is told to emit the token NO_SPEECH when the audio has no
    // intelligible speech (instead of hallucinating a fake transcript). Match
    // it after stripping punctuation/markup so wrappers like [NO_SPEECH]. count.
    private static boolean isNoSpeech(String text) {
        if (text == null) return true;
        return text.replaceAll("[^A-Za-z]", "").equalsIgnoreCase("NOSPEECH");
    }

    // Groups the transcript into short paragraphs for readability:
    // a blank line after about every 2 sentences, and a long sentence stands alone.
    static String formatParagraphs(String raw) {
        if (raw == null) {
            return "";
        }
        String flat = raw.trim().replaceAll("\\s+", " ");
        if (flat.isEmpty()) {
            return "";
        }
        // Split on whitespace that follows a sentence terminator. A "3.5" has no
        // following space, so decimals are not split.
        String[] sentences = flat.split("(?<=[.!?…])\\s+");
        if (sentences.length <= 1) {
            return flat;
        }
        StringBuilder out = new StringBuilder();
        int inGroup = 0;
        for (int i = 0; i < sentences.length; i++) {
            String s = sentences[i].trim();
            if (s.isEmpty()) {
                continue;
            }
            boolean big = s.split("\\s+").length >= 14;
            if (inGroup > 0 && (big || inGroup >= 2)) {
                out.append("\n\n");
                inGroup = 0;
            }
            if (inGroup > 0) {
                out.append(' ');
            }
            out.append(s);
            inGroup++;
            if (big && i < sentences.length - 1) {
                out.append("\n\n");
                inGroup = 0;
            }
        }
        return out.toString().trim();
    }
}
