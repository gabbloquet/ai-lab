package io.github.gabbloquet.ailab.evals.ragqa;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.IntStream;

import org.apache.commons.statistics.distribution.TDistribution;

// Comparaison appariée (SPEC.md § 8.1), p-value et correction de Holm (§ 8.3).
public final class PairedStatistics {

    public record FamilyMember(String name, Direction direction, List<PairedScore> pairs) {
    }

    private PairedStatistics() {
    }

    // § 8.1 étapes 3 à 5 et p-value du § 8.3, sur les items du split test.
    public static Map<String, Object> compare(List<PairedScore> pairs, Direction direction) {
        double[] differences = pairs.stream()
                .filter(pair -> pair.split().equals("test"))
                .mapToDouble(pair -> pair.pB() - pair.pA())
                .toArray();
        int n = differences.length;
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("n", n);
        if (n < 2) {
            result.put("delta", null);
            result.put("ci_low", null);
            result.put("ci_high", null);
            result.put("verdict", null);
            result.put("p_value", null);
            return result;
        }
        double sum = 0;
        for (double difference : differences) {
            sum += difference;
        }
        double delta = sum / n;
        double squares = 0;
        for (double difference : differences) {
            squares += (difference - delta) * (difference - delta);
        }
        double deviation = Math.sqrt(squares / (n - 1));
        TDistribution student = TDistribution.of(n - 1);
        double halfWidth = student.inverseCumulativeProbability(0.975) * deviation / Math.sqrt(n);
        double low = delta - halfWidth;
        double high = delta + halfWidth;
        double pValue;
        if (deviation == 0.0) {
            pValue = delta == 0.0 ? 1.0 : 0.0;
        } else {
            double t = delta / (deviation / Math.sqrt(n));
            pValue = 2 * student.survivalProbability(Math.abs(t));
        }
        result.put("delta", delta);
        result.put("ci_low", low);
        result.put("ci_high", high);
        result.put("verdict", verdict(low, high, direction));
        result.put("p_value", pValue);
        return result;
    }

    static boolean improves(double low, double high, Direction direction) {
        return direction == Direction.HIGHER_BETTER ? low > 0 : high < 0;
    }

    static boolean worsens(double low, double high, Direction direction) {
        return direction == Direction.HIGHER_BETTER ? high < 0 : low > 0;
    }

    private static String verdict(double low, double high, Direction direction) {
        if (improves(low, high, direction)) {
            return "b_better";
        }
        return worsens(low, high, direction) ? "b_worse" : "inconclusive";
    }

    // § 8.3 : p-values, ajustement de Holm et verdict corrigé, dans l'ordre reçu.
    public static List<Map<String, Object>> holmFamily(List<FamilyMember> members, double alpha) {
        List<Map<String, Object>> results = members.stream().map(m -> compare(m.pairs(), m.direction())).toList();
        int m = members.size();
        double[] filled = new double[m];
        for (int i = 0; i < m; i++) {
            Object p = results.get(i).get("p_value");
            filled[i] = p == null ? 1.0 : (Double) p;
        }
        List<Integer> order = IntStream.range(0, m).boxed()
                .sorted(Comparator.comparingDouble(i -> filled[i]))
                .toList();
        Map<Integer, Double> adjusted = new HashMap<>();
        double running = 0.0;
        for (int rank = 0; rank < m; rank++) {
            int i = order.get(rank);
            running = Math.max(running, Math.min(1.0, (m - rank) * filled[i]));
            adjusted.put(i, running);
        }
        List<Map<String, Object>> output = new ArrayList<>();
        for (int i = 0; i < m; i++) {
            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("name", members.get(i).name());
            Object p = results.get(i).get("p_value");
            if (p == null) {
                entry.put("p_value", null);
                entry.put("p_holm", null);
                entry.put("verdict_holm", null);
            } else {
                double pHolm = adjusted.get(i);
                String verdict = "inconclusive";
                if (pHolm < alpha) {
                    boolean positive = (Double) results.get(i).get("delta") > 0;
                    boolean better = positive == (members.get(i).direction() == Direction.HIGHER_BETTER);
                    verdict = better ? "b_better" : "b_worse";
                }
                entry.put("p_value", p);
                entry.put("p_holm", pHolm);
                entry.put("verdict_holm", verdict);
            }
            output.add(entry);
        }
        return output;
    }
}
