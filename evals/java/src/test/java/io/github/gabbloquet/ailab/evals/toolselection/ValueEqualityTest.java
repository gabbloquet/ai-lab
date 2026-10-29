package io.github.gabbloquet.ailab.evals.toolselection;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import tools.jackson.databind.json.JsonMapper;

// Même table que le test Python : les deux scorers doivent juger égales les mêmes valeurs (SPEC.md § 5).
class ValueEqualityTest {

    private static final JsonMapper JSON = JsonMapper.builder().build();

    @ParameterizedTest(name = "{0} = {1} ? {2}")
    @CsvSource(delimiter = '|', textBlock = """
            true                 | 1                        | false
            1                    | true                     | false
            false                | 0                        | false
            true                 | true                     | true
            null                 | null                     | true
            null                 | ""                       | false
            2                    | 2.0                      | true
            "2"                  | 2                        | false
            [1, "A"]             | [1.0, " a "]             | true
            [1, 2]               | [2, 1]                   | false
            {"k": "\\u00c9"}     | {"k": "e\\u0301"}        | true
            {"k": "\\u00c9"}     | {"k": "e"}               | false
            {"k": 1}             | {"k": 1, "x": 2}         | false
            "Straße"             | "STRASSE"                | true
            "\\u00a0P-15695\\t"  | "p-15695"                | true
            """)
    void comparesValuesWithTheRulesOfTheSpec(String a, String b, boolean equal) {
        assertThat(ValueEquality.equal(JSON.readTree(a), JSON.readTree(b))).isEqualTo(equal);
    }
}
