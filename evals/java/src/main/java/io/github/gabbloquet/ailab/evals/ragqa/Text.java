package io.github.gabbloquet.ailab.evals.ragqa;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

import com.ibm.icu.lang.UCharacter;

import tools.jackson.databind.JsonNode;

// Texte : normalisation (SPEC.md § 4), formes (§ 5.1, § 5.2), segments (§ 5.3), prémisse (§ 5.4).
// Les indices sont ceux des String Java (UTF-16) ; les comparaisons de caractères se font par point de code.
public final class Text {

    static final int WINDOW = 6;
    static final List<List<String>> MARKERS = List.of(List.of("non"), List.of("pas"), List.of("ni"),
            List.of("plutot", "que"), List.of("au", "lieu", "de"), List.of("contrairement"), List.of("faux"),
            List.of("inexact"), List.of("errone"), List.of("incorrect"));

    private static final Pattern SPACE_BETWEEN_DIGITS = Pattern.compile("(?<=[0-9]) (?=[0-9])");
    private static final Pattern SPACE_BEFORE_SIGN = Pattern.compile("(?<=[0-9]) (?=[%€])");
    private static final Pattern SPACES = Pattern.compile(" +");
    private static final Pattern CLAUSE = Pattern.compile(",? et ");
    private static final List<String> CITATION_PREFIXES = List.of("articles", "article", "art.");

    private Text() {
    }

    // La normalisation N du § 4, étape par étape.
    public static String normalize(String text) {
        String nfc = Normalizer.normalize(text, Normalizer.Form.NFC);
        String apostrophes = nfc.replace('’', '\'').replace('‘', '\'').replace('ʼ', '\'');
        StringBuilder spaced = new StringBuilder();
        apostrophes.codePoints().forEach(cp -> spaced.appendCodePoint(isPythonSpace(cp) ? ' ' : cp));
        String folded = UCharacter.foldCase(spaced.toString(), true);
        StringBuilder unaccented = new StringBuilder();
        Normalizer.normalize(folded, Normalizer.Form.NFD).codePoints()
                .filter(cp -> Character.getType(cp) != Character.NON_SPACING_MARK)
                .forEach(unaccented::appendCodePoint);
        String recomposed = Normalizer.normalize(unaccented, Normalizer.Form.NFC);
        String ligatures = recomposed.replace("œ", "oe").replace("æ", "ae");
        String digits = SPACE_BETWEEN_DIGITS.matcher(ligatures).replaceAll("");
        String signs = SPACE_BEFORE_SIGN.matcher(digits).replaceAll("");
        return SPACES.matcher(signs).replaceAll(" ").strip();
    }

    // str.isspace() de Python : Character.isWhitespace exclut l'espace insécable, isSpaceChar les tabulations.
    static boolean isPythonSpace(int codePoint) {
        return Character.isWhitespace(codePoint) || Character.isSpaceChar(codePoint) || codePoint == 0x85;
    }

    // Catégories Unicode L* et N* (§ 5.1).
    static boolean isLetterOrDigit(int codePoint) {
        return switch (Character.getType(codePoint)) {
            case Character.UPPERCASE_LETTER, Character.LOWERCASE_LETTER, Character.TITLECASE_LETTER,
                    Character.MODIFIER_LETTER, Character.OTHER_LETTER, Character.DECIMAL_DIGIT_NUMBER,
                    Character.LETTER_NUMBER, Character.OTHER_NUMBER -> true;
            default -> false;
        };
    }

    // § 5.2 : les suites maximales de lettres ou chiffres.
    public static List<String> words(String text) {
        List<String> found = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        text.codePoints().forEach(cp -> {
            if (isLetterOrDigit(cp)) {
                current.appendCodePoint(cp);
            } else if (!current.isEmpty()) {
                found.add(current.toString());
                current.setLength(0);
            }
        });
        if (!current.isEmpty()) {
            found.add(current.toString());
        }
        return found;
    }

    // Débuts des occurrences délimitées de N(form) dans un texte déjà normalisé (§ 5.1).
    static List<Integer> occurrences(String form, String text) {
        String needle = normalize(form);
        List<Integer> starts = new ArrayList<>();
        int start = text.indexOf(needle);
        while (start != -1) {
            int end = start + needle.length();
            boolean beforeOk = start == 0 || !isLetterOrDigit(text.codePointBefore(start));
            boolean afterOk = end == text.length() || !isLetterOrDigit(text.codePointAt(end));
            if (beforeOk && afterOk) {
                starts.add(start);
            }
            start = text.indexOf(needle, start + 1);
        }
        return starts;
    }

    // Une forme acceptée, textuelle ou à mots-clés, dans un texte déjà normalisé.
    static boolean formFound(JsonNode form, String text) {
        if (form.isString()) {
            return !occurrences(form.stringValue(), text).isEmpty();
        }
        List<String> sequence = words(text);
        List<String> tokens = new ArrayList<>();
        form.get("tokens").forEach(token -> tokens.add(normalize(token.stringValue())));
        int window = form.get("window").intValue();
        for (int p = 0; p < sequence.size(); p++) {
            if (sequence.get(p).equals(tokens.getFirst()) && matchFrom(sequence, tokens, window, 1, p + 1)) {
                return true;
            }
        }
        return false;
    }

    private static boolean matchFrom(List<String> sequence, List<String> tokens, int window, int tokenIndex,
            int position) {
        if (tokenIndex == tokens.size()) {
            return true;
        }
        int last = Math.min(sequence.size(), position + window + 1);
        for (int p = position; p < last; p++) {
            if (sequence.get(p).equals(tokens.get(tokenIndex))
                    && matchFrom(sequence, tokens, window, tokenIndex + 1, p + 1)) {
                return true;
            }
        }
        return false;
    }

    static boolean factFound(JsonNode fact, String text) {
        for (JsonNode form : fact.get("accepted")) {
            if (formFound(form, text)) {
                return true;
            }
        }
        return false;
    }

    // § 5.3 étapes 1 à 3 : phrases normalisées, non vides.
    static List<String> sentences(String answer) {
        String text = Normalizer.normalize(answer, Normalizer.Form.NFC);
        List<String> parts = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        int index = 0;
        while (index < text.length()) {
            int cp = text.codePointAt(index);
            int next = index + Character.charCount(cp);
            if (cp == ';' || cp == '!' || cp == '?' || cp == '\n' || cp == '\r') {
                parts.add(current.toString());
                current.setLength(0);
            } else if (cp == '.' && (next == text.length() || isPythonSpace(text.codePointAt(next)))) {
                if (abbreviationBefore(text, index)) {
                    current.appendCodePoint(cp);
                } else {
                    parts.add(current.toString());
                    current.setLength(0);
                }
            } else {
                current.appendCodePoint(cp);
            }
            index = next;
        }
        parts.add(current.toString());
        List<String> sentences = new ArrayList<>();
        for (String part : parts) {
            String normalized = normalize(part);
            if (!normalized.isEmpty()) {
                sentences.add(normalized);
            }
        }
        return sentences;
    }

    // Le mot qui précède le point est une seule lettre, ou « art » (après casefold).
    private static boolean abbreviationBefore(String text, int dot) {
        if (dot == 0 || !isLetterOrDigit(text.codePointBefore(dot))) {
            return false;
        }
        List<String> preceding = words(UCharacter.foldCase(text.substring(0, dot), true));
        String last = preceding.getLast();
        boolean singleLetter = last.codePointCount(0, last.length()) == 1 && Character.isLetter(last.codePointAt(0));
        return singleLetter || last.equals("art");
    }

    // § 5.3 : toutes les phrases et toutes les propositions.
    static List<String> segments(String answer) {
        List<String> found = new ArrayList<>();
        for (String sentence : sentences(answer)) {
            found.add(sentence);
            for (String clause : CLAUSE.split(sentence, -1)) {
                if (!clause.isBlank()) {
                    found.add(clause);
                }
            }
        }
        return found;
    }

    // § 5.4 : un marqueur figure parmi les WINDOW mots qui précèdent l'occurrence.
    static boolean marked(String text, int start) {
        List<String> all = words(text.substring(0, start));
        List<String> before = all.subList(Math.max(0, all.size() - WINDOW), all.size());
        for (List<String> marker : MARKERS) {
            for (int i = 0; i + marker.size() <= before.size(); i++) {
                if (before.subList(i, i + marker.size()).equals(marker)) {
                    return true;
                }
            }
        }
        return false;
    }

    // § 5.4 : au moins une occurrence délimitée de la fausse valeur n'est pas marquée.
    static boolean falseValueTaken(JsonNode falseValue, String text) {
        for (JsonNode form : falseValue.get("accepted")) {
            for (int start : occurrences(form.stringValue(), text)) {
                if (!marked(text, start)) {
                    return true;
                }
            }
        }
        return false;
    }

    // La normalisation C du § 6.
    static String normalizeCitation(String citation) {
        String text = normalize(citation);
        for (String prefix : CITATION_PREFIXES) {
            if (text.startsWith(prefix)) {
                text = text.substring(prefix.length());
                break;
            }
        }
        return text.replace(" ", "").replace(".", "").toUpperCase(java.util.Locale.ROOT);
    }
}
