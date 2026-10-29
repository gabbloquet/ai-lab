package io.github.gabbloquet.ailab.evals.toolselection;

import java.text.Normalizer;
import java.util.HashSet;

import com.ibm.icu.lang.UCharacter;

import tools.jackson.databind.JsonNode;

// Égalité de deux valeurs JSON (SPEC.md § 5).
public final class ValueEquality {

    private ValueEquality() {
    }

    public static boolean equal(JsonNode a, JsonNode b) {
        if (a.isBoolean() || b.isBoolean()) {
            return a.isBoolean() && b.isBoolean() && a.booleanValue() == b.booleanValue();
        }
        if (a.isNull() || b.isNull()) {
            return a.isNull() && b.isNull();
        }
        if (a.isString() && b.isString()) {
            return normalized(a.stringValue()).equals(normalized(b.stringValue()));
        }
        if (a.isNumber() && b.isNumber()) {
            return a.decimalValue().compareTo(b.decimalValue()) == 0;
        }
        if (a.isArray() && b.isArray()) {
            if (a.size() != b.size()) {
                return false;
            }
            for (int i = 0; i < a.size(); i++) {
                if (!equal(a.get(i), b.get(i))) {
                    return false;
                }
            }
            return true;
        }
        if (a.isObject() && b.isObject()) {
            if (!new HashSet<>(a.propertyNames()).equals(new HashSet<>(b.propertyNames()))) {
                return false;
            }
            return a.propertyNames().stream().allMatch(name -> equal(a.get(name), b.get(name)));
        }
        return false;
    }

    // NFC, puis espaces retirés aux deux bouts, puis casefold Unicode complet, comme en Python.
    static String normalized(String text) {
        return UCharacter.foldCase(strip(Normalizer.normalize(text, Normalizer.Form.NFC)), true);
    }

    // String.strip() ignore l'espace insécable ; str.strip() de Python le retire (vecteur cv-026).
    private static String strip(String text) {
        int start = 0;
        int end = text.length();
        while (start < end && isPythonSpace(text.codePointAt(start))) {
            start += Character.charCount(text.codePointAt(start));
        }
        while (end > start && isPythonSpace(text.codePointBefore(end))) {
            end -= Character.charCount(text.codePointBefore(end));
        }
        return text.substring(start, end);
    }

    private static boolean isPythonSpace(int codePoint) {
        return Character.isWhitespace(codePoint) || Character.isSpaceChar(codePoint) || codePoint == 0x85;
    }
}
