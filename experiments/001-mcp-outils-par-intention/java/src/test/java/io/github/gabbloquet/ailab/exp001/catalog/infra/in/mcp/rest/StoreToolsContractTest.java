package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Map;

import org.junit.jupiter.api.Test;

import io.modelcontextprotocol.spec.McpSchema.CallToolResult;

class StoreToolsContractTest extends RestContractTestBase {

    @Test
    @SuppressWarnings("unchecked")
    void takesNoArgument() {
        Map<String, Object> properties = (Map<String, Object>) tool("list_stores").inputSchema()
                .getOrDefault("properties", Map.of());

        assertThat(properties).isEmpty();
    }

    @Test
    void listsEveryStoreWithItsCityInIdOrder() {
        CallToolResult result = call("list_stores", Map.of());

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"stores":[\
                {"storeId":"S01","name":"Magasin Lyon","city":"Lyon"},\
                {"storeId":"S02","name":"Magasin Nantes","city":"Nantes"},\
                {"storeId":"S03","name":"Magasin Lille","city":"Lille"},\
                {"storeId":"S04","name":"Magasin Bordeaux","city":"Bordeaux"},\
                {"storeId":"S05","name":"Magasin Strasbourg","city":"Strasbourg"}]}""");
    }
}
