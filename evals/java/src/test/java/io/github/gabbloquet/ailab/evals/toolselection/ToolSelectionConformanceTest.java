package io.github.gabbloquet.ailab.evals.toolselection;

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
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

// Rejoue les vecteurs de conformance de la spec tool-selection v1 (SPEC.md § 8) : le scorer Java est
// conforme s'il reproduit exactement les entiers, les booléens et les verdicts, et les réels à 1e-9 près.
class ToolSelectionConformanceTest {

    private static final double TOLERANCE = 1e-9;
    private static final JsonMapper JSON = JsonMapper.builder().build();

    static Stream<Named<JsonNode>> executions() {
        return vectors("execution");
    }

    static Stream<Named<JsonNode>> aggregates() {
        return vectors("aggregate");
    }

    @ParameterizedTest
    @MethodSource("executions")
    void scoresEachExecutionLikeTheSpec(JsonNode vector) {
        JsonNode execution = vector.get("execution");
        JsonNode expectation = vector.get("item").get("expected").get(execution.get("variant").stringValue());
        JsonNode error = execution.get("error");

        ExecutionScore score = ToolSelectionScorer.score(
                expectation, execution.get("calls"), error.isNull() ? null : error.stringValue());

        assertConforms(score.asMap(), vector);
    }

    @ParameterizedTest
    @MethodSource("aggregates")
    void aggregatesEachSeriesLikeTheSpec(JsonNode vector) {
        List<PairedScore> scores = new ArrayList<>();
        for (JsonNode entry : vector.get("items")) {
            scores.add(new PairedScore(entry.get("item_id").stringValue(), entry.get("split").stringValue(),
                    entry.get("p_a").doubleValue(), entry.get("p_b").doubleValue()));
        }

        assertConforms(Aggregation.of(scores).asMap(), vector);
    }

    private static void assertConforms(Map<String, Object> actual, JsonNode vector) {
        String id = vector.get("id").stringValue();
        JsonNode expected = vector.get("expected");
        assertThat(actual.keySet()).as(id).containsExactlyInAnyOrderElementsOf(expected.propertyNames());
        for (String name : expected.propertyNames()) {
            JsonNode want = expected.get(name);
            Object got = actual.get(name);
            if (want.isNull()) {
                assertThat(got).as(id + " " + name).isNull();
            } else if (want.isBoolean()) {
                assertThat(got).as(id + " " + name).isEqualTo(want.booleanValue());
            } else if (want.isString()) {
                assertThat(got).as(id + " " + name).isEqualTo(want.stringValue());
            } else if (want.isIntegralNumber()) {
                assertThat(got).as(id + " " + name).isEqualTo(want.intValue());
            } else {
                assertThat((Double) got).as(id + " " + name).isCloseTo(want.doubleValue(), within(TOLERANCE));
            }
        }
    }

    private static Stream<Named<JsonNode>> vectors(String kind) {
        var stream = ToolSelectionConformanceTest.class.getResourceAsStream("/tool-selection/v1/conformance.jsonl");
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
