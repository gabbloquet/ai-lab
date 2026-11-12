package io.github.gabbloquet.ailab.evals.ragqa;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

import org.junit.jupiter.api.Named;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

// Rejoue les vecteurs de conformance de la spec rag-qa v2 (SPEC.md § 9) : le scorer Java est conforme
// s'il reproduit exactement les entiers, les booléens, les chaînes et les null, et les réels à 1e-9 près.
class RagQaConformanceTest {

    private static final double TOLERANCE = 1e-9;
    private static final JsonMapper JSON = JsonMapper.builder().build();

    static Stream<Named<JsonNode>> execution() {
        return vectors("execution");
    }

    static Stream<Named<JsonNode>> aggregate() {
        return vectors("aggregate");
    }

    static Stream<Named<JsonNode>> variant() {
        return vectors("variant");
    }

    static Stream<Named<JsonNode>> comparison() {
        return vectors("comparison");
    }

    static Stream<Named<JsonNode>> joint() {
        return vectors("joint");
    }

    static Stream<Named<JsonNode>> family() {
        return vectors("family");
    }

    @ParameterizedTest
    @MethodSource("execution")
    void scoresEachExecutionLikeTheSpec(JsonNode vector) {
        Map<String, Object> result = RagQaScorer.scoreExecution(vector.get("item"), vector.get("execution"));

        assertConforms(result, vector.get("expected"), id(vector));
    }

    @ParameterizedTest
    @MethodSource("aggregate")
    void comparesEachPairedSeriesLikeTheSpec(JsonNode vector) {
        Map<String, Object> result = PairedStatistics.compare(pairs(vector.get("items")), Direction.HIGHER_BETTER);
        result.remove("p_value");

        assertConforms(result, vector.get("expected"), id(vector));
    }

    @ParameterizedTest
    @MethodSource("variant")
    void aggregatesEachVariantLikeTheSpec(JsonNode vector) {
        Map<String, Object> result = RagQaScorer.variantAggregates(vector.get("items"), vector.get("executions"),
                vector.get("split").stringValue(), strings(vector.get("excluded")));

        assertConforms(result, vector.get("expected"), id(vector));
    }

    @ParameterizedTest
    @MethodSource("comparison")
    void comparesEachMetricLikeTheSpec(JsonNode vector) {
        Map<String, Object> result = RagQaScorer.compare(vector.get("items"), vector.get("executions"),
                vector.get("baseline").stringValue(), vector.get("variant").stringValue(),
                vector.get("metric").stringValue(), Direction.of(vector.get("direction").stringValue()),
                vector.get("split").stringValue(), strings(vector.get("excluded")));

        assertConforms(result, vector.get("expected"), id(vector));
    }

    @ParameterizedTest
    @MethodSource("joint")
    void judgesEachJointVerdictLikeTheSpec(JsonNode vector) {
        Map<String, Object> result = RagQaScorer.jointComparison(vector.get("items"), vector.get("executions"),
                vector.get("baseline").stringValue(), vector.get("variant").stringValue(),
                criterion(vector.get("main")), criterion(vector.get("guard")), vector.get("margin").doubleValue(),
                vector.get("split").stringValue(), strings(vector.get("excluded")));

        assertConforms(result, vector.get("expected"), id(vector));
    }

    @ParameterizedTest
    @MethodSource("family")
    void correctsEachFamilyLikeTheSpec(JsonNode vector) {
        List<PairedStatistics.FamilyMember> members = new ArrayList<>();
        for (JsonNode comparison : vector.get("comparisons")) {
            members.add(new PairedStatistics.FamilyMember(comparison.get("name").stringValue(),
                    Direction.of(comparison.get("direction").stringValue()), pairs(comparison.get("items"))));
        }

        List<Map<String, Object>> result = PairedStatistics.holmFamily(members, vector.get("alpha").doubleValue());

        assertConforms(result, vector.get("expected"), id(vector));
    }

    @Test
    void normalizesTheExamplesOfTheSpec() {
        assertThat(Text.normalize("Délai de 1 500 €.")).isEqualTo("delai de 1500€.");
        assertThat(Text.normalize("10 % du prix")).isEqualTo("10% du prix");
        assertThat(Text.normalize("L’Œuvre")).isEqualTo("l'oeuvre");
    }

    @Test
    void splitsWordsLikeTheExampleOfTheSpec() {
        assertThat(Text.words("d'evaluer et controler l'activite"))
                .containsExactly("d", "evaluer", "et", "controler", "l", "activite");
    }

    private static RagQaScorer.Criterion criterion(JsonNode node) {
        return new RagQaScorer.Criterion(node.get("metric").stringValue(),
                Direction.of(node.get("direction").stringValue()));
    }

    private static List<PairedScore> pairs(JsonNode entries) {
        List<PairedScore> pairs = new ArrayList<>();
        for (JsonNode entry : entries) {
            pairs.add(new PairedScore(entry.get("item_id").stringValue(), entry.get("split").stringValue(),
                    entry.get("p_a").doubleValue(), entry.get("p_b").doubleValue()));
        }
        return pairs;
    }

    private static List<String> strings(JsonNode array) {
        List<String> values = new ArrayList<>();
        array.forEach(node -> values.add(node.stringValue()));
        return values;
    }

    private static String id(JsonNode vector) {
        return vector.get("id").stringValue();
    }

    // Compare récursivement : mêmes clés, mêmes types, réels à TOLERANCE près.
    private static void assertConforms(Object actual, JsonNode expected, String where) {
        if (expected.isNull()) {
            assertThat(actual).as(where).isNull();
        } else if (expected.isObject()) {
            assertThat(actual).as(where).isInstanceOf(Map.class);
            Map<?, ?> map = (Map<?, ?>) actual;
            List<Object> keys = new ArrayList<>(map.keySet());
            assertThat(keys).as(where).containsExactlyInAnyOrderElementsOf(new ArrayList<>(expected.propertyNames()));
            for (String name : expected.propertyNames()) {
                assertConforms(map.get(name), expected.get(name), where + "." + name);
            }
        } else if (expected.isArray()) {
            assertThat(actual).as(where).isInstanceOf(List.class);
            List<?> list = (List<?>) actual;
            assertThat(list).as(where).hasSize(expected.size());
            for (int i = 0; i < expected.size(); i++) {
                assertConforms(list.get(i), expected.get(i), where + "[" + i + "]");
            }
        } else if (expected.isBoolean()) {
            assertThat(actual).as(where).isEqualTo(expected.booleanValue());
        } else if (expected.isString()) {
            assertThat(actual).as(where).isEqualTo(expected.stringValue());
        } else if (expected.isIntegralNumber()) {
            assertThat(actual).as(where).isEqualTo(expected.intValue());
        } else {
            assertThat(actual).as(where).isInstanceOf(Double.class);
            assertThat((Double) actual).as(where).isCloseTo(expected.doubleValue(), within(TOLERANCE));
        }
    }

    private static Stream<Named<JsonNode>> vectors(String kind) {
        var stream = RagQaConformanceTest.class.getResourceAsStream("/rag-qa/v2/conformance.jsonl");
        try (var reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            return reader.lines()
                    .filter(line -> !line.isBlank())
                    .map(JSON::readTree)
                    .filter(vector -> vector.get("kind").stringValue().equals(kind))
                    .map(vector -> Named.of(vector.get("id").stringValue(), vector))
                    .toList()
                    .stream();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
