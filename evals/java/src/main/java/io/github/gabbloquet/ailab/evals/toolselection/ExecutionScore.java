package io.github.gabbloquet.ailab.evals.toolselection;

import java.util.LinkedHashMap;
import java.util.Map;

// Métriques d'une exécution (SPEC.md § 6). precision est null quand M + E = 0.
public record ExecutionScore(
        double toolRecall,
        double argsRecall,
        Double precision,
        int extraCalls,
        int nCalls,
        boolean success,
        boolean strictSuccess) {

    // Noms de la spec, pour comparer aux vecteurs et écrire les rapports.
    public Map<String, Object> asMap() {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("tool_recall", toolRecall);
        map.put("args_recall", argsRecall);
        map.put("precision", precision);
        map.put("extra_calls", extraCalls);
        map.put("n_calls", nCalls);
        map.put("success", success);
        map.put("strict_success", strictSuccess);
        return map;
    }
}
