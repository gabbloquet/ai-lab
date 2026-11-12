package io.github.gabbloquet.ailab.evals.ragqa;

// pᵢ(A) et pᵢ(B) d'un item, avec son split (SPEC.md § 8.1).
public record PairedScore(String itemId, String split, double pA, double pB) {
}
