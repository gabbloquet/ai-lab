package io.github.gabbloquet.ailab.evals.ragqa;

// Sens d'une métrique, fixé avant le run (SPEC.md § 8.1).
public enum Direction {
    HIGHER_BETTER, LOWER_BETTER;

    public static Direction of(String value) {
        return switch (value) {
            case "higher_better" -> HIGHER_BETTER;
            case "lower_better" -> LOWER_BETTER;
            default -> throw new IllegalArgumentException("Sens inconnu : " + value);
        };
    }
}
