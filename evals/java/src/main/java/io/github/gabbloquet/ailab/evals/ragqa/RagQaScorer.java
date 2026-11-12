package io.github.gabbloquet.ailab.evals.ragqa;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

import tools.jackson.databind.JsonNode;

// Scorer de la spec rag-qa v2 (evals/spec/rag-qa/v2/SPEC.md) : métriques par exécution (§ 6), agrégats
// par variante (§ 7), comparaisons et verdict à deux critères (§ 8). Les résultats portent les noms de
// la spec ; un réel est un Double, un entier un Integer, une absence de valeur null.
public final class RagQaScorer {

    static final int[] KS = {1, 3, 5, 10};
    private static final List<String> FAILURES = List.of("correct", "retrieval_miss", "generation_miss", "error");
    private static final List<String> PREMISES = List.of("corrected", "unresolved", "adopted", "missed");

    public record Criterion(String metric, Direction direction) {
    }

    private RagQaScorer() {
    }

    // --- § 6 : métriques par exécution ----------------------------------------------------------------

    public static Map<String, Object> scoreExecution(JsonNode item, JsonNode execution) {
        boolean answerable = item.get("answerable").booleanValue();
        JsonNode facts = item.get("expected").get("facts");
        Set<String> gold = new HashSet<>();
        item.get("expected").get("articles").forEach(article -> gold.add(article.get("id").stringValue()));
        String answer = execution.get("answer").stringValue();
        String text = Text.normalize(answer);
        boolean abstained = execution.get("abstained").booleanValue();
        boolean failed = !execution.get("error").isNull();
        List<String> context = null;
        if (!execution.get("context").isNull()) {
            Set<String> unique = new LinkedHashSet<>();
            execution.get("context").forEach(id -> unique.add(id.stringValue()));
            context = new ArrayList<>(unique);
        }
        Integer toolCalls = integerOrNull(execution.get("tool_calls"));
        JsonNode falseValue = item.get("false_value");

        List<Boolean> foundEach = new ArrayList<>();
        facts.forEach(fact -> foundEach.add(Text.factFound(fact, text)));
        boolean allFound = !foundEach.contains(false);
        Integer found = answerable ? (int) foundEach.stream().filter(b -> b).count() : null;
        Integer attached = null;
        if (answerable && anchored(facts)) {
            int count = 0;
            for (int i = 0; i < facts.size(); i++) {
                if (attached(facts, i, answer)) {
                    count++;
                }
            }
            attached = count;
        }
        Boolean taken = falseValue == null ? null : Text.falseValueTaken(falseValue, text);

        boolean correct;
        if (failed) {
            correct = false;
        } else if (answerable) {
            correct = !abstained && allFound && (attached == null || attached == facts.size())
                    && !Boolean.TRUE.equals(taken);
        } else {
            correct = abstained;
        }

        String premise = null;
        if (falseValue != null) {
            premise = allFound ? (taken ? "unresolved" : "corrected") : (taken ? "adopted" : "missed");
        }

        boolean scoresContext = context != null && answerable;
        boolean ranked = scoresContext && (toolCalls == null || toolCalls <= 1);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("correct", correct);
        result.put("facts_found", found);
        result.put("facts_attached", attached);
        result.put("premise", premise);
        result.put("false_abstention", failed || !answerable ? null : abstained);
        result.put("hallucination", failed || answerable ? null : !abstained);
        for (int k : KS) {
            if (ranked) {
                Set<String> top = new HashSet<>(context.subList(0, Math.min(k, context.size())));
                Set<String> hit = new HashSet<>(gold);
                hit.retainAll(top);
                result.put("evidence_recall@" + k, (double) hit.size() / gold.size());
                result.put("all_evidence@" + k, top.containsAll(gold));
            } else {
                result.put("evidence_recall@" + k, null);
                result.put("all_evidence@" + k, null);
            }
        }
        result.put("all_evidence", scoresContext ? context.containsAll(gold) : null);
        result.put("context_size", context == null ? null : context.size());
        String failure = null;
        if (scoresContext) {
            if (failed) {
                failure = "error";
            } else if (correct) {
                failure = "correct";
            } else {
                failure = context.containsAll(gold) ? "generation_miss" : "retrieval_miss";
            }
        }
        result.put("failure", failure);
        Double precision = null;
        Double citationRecall = null;
        if (answerable) {
            Set<String> cited = new HashSet<>();
            execution.get("cited").forEach(c -> cited.add(Text.normalizeCitation(c.stringValue())));
            Set<String> expectedNums = new HashSet<>();
            item.get("expected").get("articles")
                    .forEach(a -> expectedNums.add(Text.normalizeCitation(a.get("num").stringValue())));
            Set<String> matched = new HashSet<>(cited);
            matched.retainAll(expectedNums);
            precision = cited.isEmpty() ? null : (double) matched.size() / cited.size();
            citationRecall = (double) matched.size() / expectedNums.size();
        }
        result.put("citation_precision", precision);
        result.put("citation_recall", citationRecall);
        result.put("tool_calls", toolCalls);
        result.put("latency_s", doubleOrNull(execution.get("latency_s")));
        result.put("cost_usd", doubleOrNull(execution.get("cost_usd")));
        return result;
    }

    private static boolean anchored(JsonNode facts) {
        if (facts.isEmpty()) {
            return false;
        }
        for (JsonNode fact : facts) {
            if (!fact.has("anchor")) {
                return false;
            }
        }
        return true;
    }

    // § 5.3 : un segment contient la valeur et son ancre, sans l'ancre d'un autre fait.
    private static boolean attached(JsonNode facts, int index, String answer) {
        for (String segment : Text.segments(answer)) {
            if (!Text.factFound(facts.get(index), segment) || !anyForm(facts.get(index).get("anchor"), segment)) {
                continue;
            }
            boolean other = false;
            for (int j = 0; j < facts.size(); j++) {
                if (j != index && anyForm(facts.get(j).get("anchor"), segment)) {
                    other = true;
                    break;
                }
            }
            if (!other) {
                return true;
            }
        }
        return false;
    }

    private static boolean anyForm(JsonNode forms, String text) {
        for (JsonNode form : forms) {
            if (Text.formFound(form, text)) {
                return true;
            }
        }
        return false;
    }

    private static Integer integerOrNull(JsonNode node) {
        return node == null || node.isNull() ? null : node.intValue();
    }

    private static Double doubleOrNull(JsonNode node) {
        return node == null || node.isNull() ? null : node.doubleValue();
    }

    // --- § 7 : agrégats par variante -------------------------------------------------------------------

    private record Row(JsonNode item, JsonNode execution, Map<String, Object> score) {
    }

    private static Map<String, JsonNode> kept(JsonNode items, String split, Collection<String> excluded) {
        Map<String, JsonNode> kept = new LinkedHashMap<>();
        for (JsonNode item : items) {
            String id = item.get("id").stringValue();
            if (item.get("split").stringValue().equals(split) && !excluded.contains(id)) {
                kept.put(id, item);
            }
        }
        return kept;
    }

    public static Map<String, Object> variantAggregates(JsonNode items, JsonNode executions, String split,
            Collection<String> excluded) {
        Map<String, JsonNode> kept = kept(items, split, excluded);
        List<Row> rows = new ArrayList<>();
        for (JsonNode execution : executions) {
            JsonNode item = kept.get(execution.get("item_id").stringValue());
            if (item != null) {
                rows.add(new Row(item, execution, scoreExecution(item, execution)));
            }
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("n_executions", rows.size());
        result.put("correct", mean(rows, r -> r.score().get("correct")));
        result.put("correct_answerable",
                mean(rows, r -> r.item().get("answerable").booleanValue() ? r.score().get("correct") : null));
        result.put("false_abstention_rate", mean(rows, r -> r.score().get("false_abstention")));
        result.put("hallucination_rate", mean(rows, r -> r.score().get("hallucination")));
        result.put("error_rate", mean(rows, r -> !r.execution().get("error").isNull()));
        for (int k : KS) {
            result.put("evidence_recall@" + k, mean(rows, r -> r.score().get("evidence_recall@" + k)));
            result.put("all_evidence@" + k, mean(rows, r -> r.score().get("all_evidence@" + k)));
        }
        result.put("all_evidence", mean(rows, r -> r.score().get("all_evidence")));
        result.put("context_size", mean(rows, r -> r.score().get("context_size")));
        result.put("failure", distribution(rows, "failure", FAILURES));
        result.put("premise", distribution(rows, "premise", PREMISES));
        Map<String, List<Row>> byMode = new LinkedHashMap<>();
        rows.forEach(r -> byMode.computeIfAbsent(r.item().get("mode").stringValue(), m -> new ArrayList<>()).add(r));
        Map<String, Object> correctByMode = new LinkedHashMap<>();
        byMode.forEach((mode, modeRows) -> correctByMode.put(mode, mean(modeRows, r -> r.score().get("correct"))));
        result.put("correct_by_mode", correctByMode);
        result.put("tokens_mean", strictMean(rows, r -> {
            JsonNode usage = r.execution().get("usage");
            if (usage.get("input_tokens").isNull() || usage.get("output_tokens").isNull()) {
                return null;
            }
            return usage.get("input_tokens").intValue() + usage.get("output_tokens").intValue();
        }));
        result.put("cost_usd_mean", strictMean(rows, r -> r.score().get("cost_usd")));
        List<Double> latencies = new ArrayList<>();
        boolean complete = !rows.isEmpty();
        for (Row r : rows) {
            Object latency = r.score().get("latency_s");
            if (latency == null) {
                complete = false;
            } else {
                latencies.add((Double) latency);
            }
        }
        result.put("latency_s_median", complete ? percentile(latencies, 0.5) : null);
        result.put("latency_s_p95", complete ? percentile(latencies, 0.95) : null);
        result.put("tool_calls_mean", strictMean(rows, r -> r.score().get("tool_calls")));
        return result;
    }

    private interface Extractor {
        Object value(Row row);
    }

    private static double asNumber(Object value) {
        if (value instanceof Boolean b) {
            return b ? 1.0 : 0.0;
        }
        return ((Number) value).doubleValue();
    }

    private static Double mean(List<Row> rows, Extractor extractor) {
        double sum = 0;
        int count = 0;
        for (Row row : rows) {
            Object value = extractor.value(row);
            if (value != null) {
                sum += asNumber(value);
                count++;
            }
        }
        return count == 0 ? null : sum / count;
    }

    // Moyenne seulement si aucune valeur n'est nulle (§ 7, cinq dernières clés).
    private static Double strictMean(List<Row> rows, Extractor extractor) {
        if (rows.isEmpty()) {
            return null;
        }
        double sum = 0;
        for (Row row : rows) {
            Object value = extractor.value(row);
            if (value == null) {
                return null;
            }
            sum += asNumber(value);
        }
        return sum / rows.size();
    }

    private static Map<String, Object> distribution(List<Row> rows, String metric, List<String> keys) {
        List<Object> present = rows.stream().map(r -> r.score().get(metric)).filter(Objects::nonNull).toList();
        if (present.isEmpty()) {
            return null;
        }
        Map<String, Object> shares = new LinkedHashMap<>();
        for (String key : keys) {
            shares.put(key, (double) present.stream().filter(key::equals).count() / present.size());
        }
        return shares;
    }

    // § 7 : interpolation linéaire entre les rangs (méthode 7 de Hyndman et Fan).
    static double percentile(List<Double> values, double q) {
        List<Double> ordered = values.stream().sorted().toList();
        double h = (ordered.size() - 1) * q;
        int low = (int) Math.floor(h);
        int high = Math.min(low + 1, ordered.size() - 1);
        return ordered.get(low) + (h - low) * (ordered.get(high) - ordered.get(low));
    }

    // --- § 8 : comparaison et verdicts ---------------------------------------------------------------

    // § 8.1 étape 1 : moyenne de la métrique sur les exécutions notées de chaque item.
    private static Map<String, Double> perItem(Map<String, JsonNode> kept, JsonNode executions, String variant,
            String metric) {
        Map<String, double[]> sums = new LinkedHashMap<>();
        for (JsonNode execution : executions) {
            JsonNode item = kept.get(execution.get("item_id").stringValue());
            if (item == null || !execution.get("variant").stringValue().equals(variant)) {
                continue;
            }
            Object value = scoreExecution(item, execution).get(metric);
            if (value != null) {
                double[] acc = sums.computeIfAbsent(item.get("id").stringValue(), id -> new double[2]);
                acc[0] += asNumber(value);
                acc[1] += 1;
            }
        }
        Map<String, Double> means = new LinkedHashMap<>();
        sums.forEach((id, acc) -> means.put(id, acc[0] / acc[1]));
        return means;
    }

    public static Map<String, Object> compare(JsonNode items, JsonNode executions, String baseline, String variant,
            String metric, Direction direction, String split, Collection<String> excluded) {
        Map<String, JsonNode> kept = kept(items, split, excluded);
        Map<String, Double> pA = perItem(kept, executions, baseline, metric);
        Map<String, Double> pB = perItem(kept, executions, variant, metric);
        List<PairedScore> pairs = new ArrayList<>();
        for (String id : kept.keySet()) {
            if (pA.containsKey(id) && pB.containsKey(id)) {
                pairs.add(new PairedScore(id, "test", pA.get(id), pB.get(id)));
            }
        }
        return PairedStatistics.compare(pairs, direction);
    }

    // § 8.2 : verdict à deux critères.
    static String jointVerdict(Map<String, Object> main, Map<String, Object> guard, Direction mainDirection,
            Direction guardDirection, double margin) {
        if (main.get("delta") == null || guard.get("delta") == null) {
            return null;
        }
        double mainLow = (Double) main.get("ci_low");
        double mainHigh = (Double) main.get("ci_high");
        double guardLow = (Double) guard.get("ci_low");
        double guardHigh = (Double) guard.get("ci_high");
        boolean holds;
        boolean broken;
        if (guardDirection == Direction.LOWER_BETTER) {
            holds = guardHigh < margin;
            broken = guardLow > margin;
        } else {
            holds = guardLow > -margin;
            broken = guardHigh < -margin;
        }
        if (PairedStatistics.worsens(mainLow, mainHigh, mainDirection) || broken) {
            return "b_worse";
        }
        if (PairedStatistics.improves(mainLow, mainHigh, mainDirection)) {
            return holds ? "b_better" : "tradeoff";
        }
        return "inconclusive";
    }

    public static Map<String, Object> jointComparison(JsonNode items, JsonNode executions, String baseline,
            String variant, Criterion main, Criterion guard, double margin, String split,
            Collection<String> excluded) {
        Map<String, Object> mainResult = compare(items, executions, baseline, variant, main.metric(),
                main.direction(), split, excluded);
        Map<String, Object> guardResult = compare(items, executions, baseline, variant, guard.metric(),
                guard.direction(), split, excluded);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("main", mainResult);
        result.put("guard", guardResult);
        result.put("verdict", jointVerdict(mainResult, guardResult, main.direction(), guard.direction(), margin));
        return result;
    }
}
