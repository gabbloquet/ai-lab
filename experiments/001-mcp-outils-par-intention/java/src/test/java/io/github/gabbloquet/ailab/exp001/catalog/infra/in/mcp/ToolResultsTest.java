package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;

import org.junit.jupiter.api.Test;

import io.modelcontextprotocol.spec.McpSchema.CallToolResult;
import io.modelcontextprotocol.spec.McpSchema.TextContent;
import tools.jackson.databind.json.JsonMapper;

class ToolResultsTest {

    private final ToolResults toolResults = new ToolResults(JsonMapper.builder().build());

    record Sample(String sku, int available) {
    }

    private static List<String> texts(CallToolResult result) {
        return result.content().stream().map(content -> ((TextContent) content).text()).toList();
    }

    @Test
    void returnsTheResponseAsJsonInASingleTextBlock() {
        CallToolResult result = toolResults.run(() -> new Sample("P-15695", 3));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("{\"sku\":\"P-15695\",\"available\":3}");
    }

    @Test
    void returnsAnExpectedErrorWithItsMessageOnlyOnce() {
        CallToolResult result = toolResults.run(() -> {
            throw new ToolException("Product not found: P-00000. Use search_catalog to find the SKU of a product.");
        });

        assertThat(result.isError()).isTrue();
        assertThat(texts(result))
                .containsExactly("Product not found: P-00000. Use search_catalog to find the SKU of a product.");
    }

    @Test
    void treatsInvalidArgumentsAsExpectedErrors() {
        CallToolResult result = toolResults.run(() -> {
            throw new IllegalArgumentException("SKU must not be blank");
        });

        assertThat(result.isError()).isTrue();
        assertThat(texts(result)).containsExactly("SKU must not be blank");
    }

    @Test
    void hidesTheDetailsOfAnUnexpectedError() {
        CallToolResult result = toolResults.run(() -> {
            throw new IllegalStateException("connection to db-prod-07 refused");
        });

        assertThat(result.isError()).isTrue();
        assertThat(texts(result)).singleElement().asString()
                .doesNotContain("db-prod-07")
                .contains("Internal error");
    }
}
