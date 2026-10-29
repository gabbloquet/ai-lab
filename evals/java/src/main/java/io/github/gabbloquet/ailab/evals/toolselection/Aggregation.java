package io.github.gabbloquet.ailab.evals.toolselection;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.statistics.distribution.TDistribution;

// Différence appariée B − A sur les items test seulement, IC de Student à 95 % (SPEC.md § 7).
public record Aggregation(int n, double delta, double ciLow, double ciHigh, Verdict verdict) {

    public enum Verdict {
        B_BETTER("b_better"), B_WORSE("b_worse"), INCONCLUSIVE("inconclusive");

        private final String value;

        Verdict(String value) {
            this.value = value;
        }

        public String value() {
            return value;
        }
    }

    public static Aggregation of(List<PairedScore> scores) {
        double[] differences = scores.stream()
                .filter(score -> score.split().equals("test"))
                .mapToDouble(score -> score.pB() - score.pA())
                .toArray();
        int n = differences.length;
        if (n < 2) {
            throw new IllegalArgumentException("Il faut au moins deux items test pour un intervalle de confiance.");
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
        double halfWidth = TDistribution.of(n - 1).inverseCumulativeProbability(0.975) * deviation / Math.sqrt(n);
        double low = delta - halfWidth;
        double high = delta + halfWidth;
        Verdict verdict = low > 0 ? Verdict.B_BETTER : high < 0 ? Verdict.B_WORSE : Verdict.INCONCLUSIVE;
        return new Aggregation(n, delta, low, high, verdict);
    }

    // Noms de la spec, pour comparer aux vecteurs et écrire les rapports.
    public Map<String, Object> asMap() {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("n", n);
        map.put("delta", delta);
        map.put("ci_low", ciLow);
        map.put("ci_high", ciHigh);
        map.put("verdict", verdict.value());
        return map;
    }
}
