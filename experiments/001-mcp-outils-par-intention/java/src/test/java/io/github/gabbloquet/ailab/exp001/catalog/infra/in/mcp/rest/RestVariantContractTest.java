package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

import io.modelcontextprotocol.spec.McpSchema.Tool;

class RestVariantContractTest extends RestContractTestBase {

    // Le modèle lit les outils dans cet ordre : il est figé. Spring AI publie bean par bean (ProductTools,
    // StockTools, StoreTools), puis par nom de méthode Java dans chaque bean.
    @Test
    void exposesOnlyTheRestToolsInAFixedOrder() {
        assertThat(client.listTools().tools()).extracting(Tool::name)
                .containsExactly("get_product", "get_similar", "list_products", "get_stock", "list_stores");
    }

    @Test
    void declaresEveryToolAsReadOnlyOnAClosedDomain() {
        assertThat(client.listTools().tools()).allSatisfy(tool -> {
            assertThat(tool.annotations().readOnlyHint()).as(tool.name()).isTrue();
            assertThat(tool.annotations().destructiveHint()).as(tool.name()).isFalse();
            assertThat(tool.annotations().idempotentHint()).as(tool.name()).isTrue();
            assertThat(tool.annotations().openWorldHint()).as(tool.name()).isFalse();
        });
    }
}
