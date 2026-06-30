package com.autosmart.geminimic;

import android.accessibilityservice.AccessibilityService;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.widget.Toast;

public class VoiceInputAccessibilityService extends AccessibilityService {

    private static final String[] PLACEHOLDER_TEXTS;
    private static VoiceInputAccessibilityService instance;

    private AccessibilityNodeInfo lastEditable;
    private final Handler main;

    static {
        PLACEHOLDER_TEXTS = new String[]{
                "broadcast", "card name", "message", "type a message",
                "write a message", "add a comment", "comment", "search",
                "title", "description", "name", "subject", "text message", "enter message"
        };
    }

    public VoiceInputAccessibilityService() {
        this.main = new Handler(Looper.getMainLooper());
    }

    @Override
    protected void onServiceConnected() {
        instance = this;
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        AccessibilityNodeInfo src = event.getSource();
        if (src != null) {
            AccessibilityNodeInfo editable = findEditable(src, true);
            if (editable == null && isUsableEditable(src)) {
                editable = src;
            }
            rememberEditable(editable);
        }
    }

    @Override
    public void onInterrupt() {
    }

    @Override
    public void onDestroy() {
        if (instance == this) {
            instance = null;
        }
        lastEditable = null;
        super.onDestroy();
    }

    static boolean typeText(String text) {
        VoiceInputAccessibilityService svc = instance;
        if (svc != null && text != null && !text.trim().isEmpty()) {
            svc.main.post(() -> svc.insertText(text.trim()));
            return true;
        }
        return false;
    }

    static boolean hasActiveTextInput() {
        VoiceInputAccessibilityService svc = instance;
        if (svc == null) return false;
        AccessibilityNodeInfo root = svc.getRootInActiveWindow();
        if (root == null) return false;
        if (svc.isUsableEditable(root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT))) {
            return true;
        }
        return svc.findEditable(root, true) != null;
    }

    private void insertText(String text) {
        AccessibilityNodeInfo target = findTarget(getRootInActiveWindow());
        if (target != null) {
            rememberEditable(target);
            boolean ok = setText(target, text);
            if (!ok) ok = pasteText(target, text);
            if (!ok) Toast.makeText(this, "This app blocked auto input", Toast.LENGTH_SHORT).show();
        } else {
            Toast.makeText(this, "Avval matn kiritiladigan joyni bosing", Toast.LENGTH_SHORT).show();
        }
    }

    private AccessibilityNodeInfo findTarget(AccessibilityNodeInfo root) {
        if (root != null) {
            AccessibilityNodeInfo focused = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT);
            if (isUsableEditable(focused)) return focused;
            AccessibilityNodeInfo editable = findEditable(root, true);
            if (editable != null) return editable;
        }
        if (lastEditable != null && lastEditable.refresh() && isUsableEditable(lastEditable)) {
            return lastEditable;
        }
        if (root != null) {
            return findEditable(root, false);
        }
        return null;
    }

    private AccessibilityNodeInfo findEditable(AccessibilityNodeInfo node, boolean mustBeFocused) {
        if (node == null) return null;
        if (isUsableEditable(node) && (!mustBeFocused || node.isFocused())) {
            return node;
        }
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo result = findEditable(node.getChild(i), mustBeFocused);
            if (result != null) return result;
        }
        return null;
    }

    private boolean isUsableEditable(AccessibilityNodeInfo node) {
        return node != null && node.isEditable() && node.isEnabled();
    }

    private void rememberEditable(AccessibilityNodeInfo node) {
        if (isUsableEditable(node)) {
            lastEditable = AccessibilityNodeInfo.obtain(node);
        }
    }

    private boolean setText(AccessibilityNodeInfo node, String newText) {
        String current = currentText(node);
        int selStart = node.getTextSelectionStart();
        int selEnd = node.getTextSelectionEnd();
        String space = shouldAddSpace(current, selStart, selEnd, newText) ? " " : "";

        int cursorPos = current.length();
        if (selStart >= 0) cursorPos = Math.min(selStart, cursorPos);

        String combined;
        if (selStart < 0 || selEnd < 0 || selStart > current.length() || selEnd > current.length()) {
            combined = current + space + newText;
        } else {
            combined = current.substring(0, Math.min(selStart, selEnd))
                    + space + newText
                    + current.substring(Math.max(selStart, selEnd));
        }

        Bundle args = new Bundle();
        args.putCharSequence("ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE", combined);
        boolean ok = node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args);
        if (ok) {
            int newCursor = cursorPos + space.length() + newText.length();
            Bundle selArgs = new Bundle();
            selArgs.putInt("ACTION_ARGUMENT_SELECTION_START_INT", newCursor);
            selArgs.putInt("ACTION_ARGUMENT_SELECTION_END_INT", newCursor);
            node.performAction(AccessibilityNodeInfo.ACTION_SET_SELECTION, selArgs);
        }
        return ok;
    }

    private boolean pasteText(AccessibilityNodeInfo node, String newText) {
        if (node == null) return false;
        String space = shouldAddSpace(currentText(node),
                node.getTextSelectionStart(), node.getTextSelectionEnd(), newText) ? " " : "";
        ClipboardManager cm = (ClipboardManager) getSystemService("clipboard");
        if (cm == null) return false;
        cm.setPrimaryClip(ClipData.newPlainText("Gemini Mic", space + newText));
        node.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
        return node.performAction(AccessibilityNodeInfo.ACTION_PASTE);
    }

    private String currentText(AccessibilityNodeInfo node) {
        if (node != null && node.getText() != null) {
            String text = node.getText().toString();
            if (!text.trim().isEmpty()) {
                if (!sameText(text, node.getHintText())
                        && !sameText(text, node.getContentDescription())) {
                    if (!shouldTreatAsPlaceholder(node, text)) {
                        return text;
                    }
                }
            }
        }
        return "";
    }

    private boolean shouldTreatAsPlaceholder(AccessibilityNodeInfo node, String text) {
        String normalized = normalize(text);
        for (String ph : PLACEHOLDER_TEXTS) {
            if (normalized.equals(ph)) return true;
        }
        int selStart = node.getTextSelectionStart();
        int selEnd = node.getTextSelectionEnd();
        if (selStart >= 0 && selEnd >= 0) {
            if (selStart == 0 && selEnd == 0 && looksLikeShortFieldLabel(text)) {
                return true;
            }
            return false;
        }
        return true;
    }

    private boolean looksLikeShortFieldLabel(String text) {
        String t = text != null ? text.trim() : "";
        if (t.isEmpty() || t.length() > 36) return false;
        if (t.contains(".") || t.contains(",") || t.contains("?") || t.contains("!")) return false;
        if (t.split("\\s+").length > 4) return false;
        return Character.isUpperCase(t.charAt(0));
    }

    private boolean shouldAddSpace(String current, int selStart, int selEnd, String newText) {
        if (current.isEmpty() || newText.isEmpty()) return false;
        int pos = current.length();
        if (selStart >= 0) pos = Math.min(selStart, pos);
        if (pos == 0) return false;
        char before = current.charAt(pos - 1);
        char first = newText.charAt(0);
        return !Character.isWhitespace(before) && !isPunctuation(first);
    }

    private boolean isPunctuation(char c) {
        return ".,!?;:)]}".indexOf(c) >= 0;
    }

    private boolean sameText(String a, CharSequence b) {
        return a != null && b != null && normalize(a).equals(normalize(b.toString()));
    }

    private String normalize(String s) {
        return s != null ? s.trim().replaceAll("\\s+", " ").toLowerCase() : "";
    }
}
