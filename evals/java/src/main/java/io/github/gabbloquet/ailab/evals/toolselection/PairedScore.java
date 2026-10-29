package io.github.gabbloquet.ailab.evals.toolselection;

// pᵢ(A) et pᵢ(B) d'un item : moyenne de success sur ses k répétitions (SPEC.md § 7).
public record PairedScore(String itemId, String split, double pA, double pB) {
}
