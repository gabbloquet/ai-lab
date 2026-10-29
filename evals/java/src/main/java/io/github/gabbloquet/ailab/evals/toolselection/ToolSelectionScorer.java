package io.github.gabbloquet.ailab.evals.toolselection;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import tools.jackson.databind.JsonNode;

// Note une exécution contre l'attente d'un item (SPEC.md § 4 et § 6).
public final class ToolSelectionScorer {

    private ToolSelectionScorer() {
    }

    // expectation : l'entrée expected[variante] de l'item ; calls : les appels émis, dans l'ordre.
    public static ExecutionScore score(JsonNode expectation, JsonNode calls, String error) {
        List<JsonNode> required = list(expectation.get("required"));
        List<JsonNode> tolerated = list(expectation.get("tolerated"));
        List<JsonNode> untolerated = list(calls).stream()
                .filter(call -> tolerated.stream().noneMatch(pattern -> satisfies(call, pattern)))
                .toList();

        int r = required.size();
        int m = maximumMatching(required, untolerated);
        int n = matchingByName(required, untolerated);
        int extra = untolerated.size() - m;
        boolean success = m == r && error == null;
        return new ExecutionScore(
                (double) n / r,
                (double) m / r,
                m + extra == 0 ? null : (double) m / (m + extra),
                extra,
                calls.size(),
                success,
                success && extra == 0);
    }

    // § 4 : même outil (sensible à la casse), arguments requis présents et acceptables, arguments
    // facultatifs acceptables s'ils sont présents, aucun argument hors du motif.
    static boolean satisfies(JsonNode call, JsonNode pattern) {
        JsonNode args = call.get("args");
        if (!call.get("tool").stringValue().equals(pattern.get("tool").stringValue()) || !args.isObject()) {
            return false;
        }
        JsonNode requiredArgs = pattern.get("args");
        JsonNode optionalArgs = pattern.get("optional");
        for (String name : args.propertyNames()) {
            boolean known = requiredArgs.get(name) != null || (optionalArgs != null && optionalArgs.get(name) != null);
            if (!known) {
                return false;
            }
        }
        for (String name : requiredArgs.propertyNames()) {
            if (args.get(name) == null || !acceptable(args.get(name), requiredArgs.get(name))) {
                return false;
            }
        }
        if (optionalArgs != null) {
            for (String name : optionalArgs.propertyNames()) {
                if (args.get(name) != null && !acceptable(args.get(name), optionalArgs.get(name))) {
                    return false;
                }
            }
        }
        return true;
    }

    private static boolean acceptable(JsonNode value, JsonNode accepted) {
        if (accepted.isObject()) {
            return true; // {"any": true}, garanti par le schéma du golden set
        }
        for (JsonNode candidate : accepted) {
            if (ValueEquality.equal(value, candidate)) {
                return true;
            }
        }
        return false;
    }

    // § 6.2 : couplage maximum motifs ↔ appels par chemins augmentants (algorithme de Kuhn).
    // Un couplage glouton dans l'ordre des appels peut en manquer (vecteur cv-017).
    static int maximumMatching(List<JsonNode> patterns, List<JsonNode> calls) {
        Map<Integer, Integer> owner = new HashMap<>(); // appel -> motif
        int matched = 0;
        for (int pattern = 0; pattern < patterns.size(); pattern++) {
            if (augment(pattern, patterns, calls, owner, new HashSet<>())) {
                matched++;
            }
        }
        return matched;
    }

    private static boolean augment(int pattern, List<JsonNode> patterns, List<JsonNode> calls,
            Map<Integer, Integer> owner, Set<Integer> seen) {
        for (int call = 0; call < calls.size(); call++) {
            if (seen.contains(call) || !satisfies(calls.get(call), patterns.get(pattern))) {
                continue;
            }
            seen.add(call);
            if (!owner.containsKey(call) || augment(owner.get(call), patterns, calls, owner, seen)) {
                owner.put(call, pattern);
                return true;
            }
        }
        return false;
    }

    // § 6.3 : pour chaque outil, le minimum entre motifs requis et appels non tolérés de cet outil.
    private static int matchingByName(List<JsonNode> required, List<JsonNode> calls) {
        Map<String, Integer> patternsByTool = countByTool(required);
        Map<String, Integer> callsByTool = countByTool(calls);
        return patternsByTool.entrySet().stream()
                .mapToInt(entry -> Math.min(entry.getValue(), callsByTool.getOrDefault(entry.getKey(), 0)))
                .sum();
    }

    private static Map<String, Integer> countByTool(List<JsonNode> nodes) {
        Map<String, Integer> counts = new HashMap<>();
        nodes.forEach(node -> counts.merge(node.get("tool").stringValue(), 1, Integer::sum));
        return counts;
    }

    private static List<JsonNode> list(JsonNode array) {
        List<JsonNode> nodes = new ArrayList<>();
        array.forEach(nodes::add);
        return nodes;
    }
}
