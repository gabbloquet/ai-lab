package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

import io.modelcontextprotocol.spec.McpSchema.CallToolResult;

class StockToolsContractTest extends RestContractTestBase {

    @Test
    @SuppressWarnings("unchecked")
    void asksForTheSkuAndTheStoreId() {
        Map<String, Object> schema = tool("get_stock").inputSchema();

        assertThat((Map<String, Object>) schema.get("properties")).containsOnlyKeys("sku", "storeId");
        assertThat((List<String>) schema.get("required")).containsExactlyInAnyOrder("sku", "storeId");
    }

    @Test
    void givesTheQuantityAvailableForSaleNetOfReservations() {
        CallToolResult result = call("get_stock", Map.of("sku", "P-10851", "storeId", "s03"));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"sku":"P-10851","storeId":"S03","available":4}""");
    }

    @Test
    void reportsAnUnknownStoreWithTheKnownOnes() {
        CallToolResult result = call("get_stock", Map.of("sku", "P-10851", "storeId", "S99"));

        assertThat(result.isError()).isTrue();
        assertThat(texts(result)).containsExactly("Store not found: S99. Known stores: S01 (Lyon), S02 (Nantes),"
                + " S03 (Lille), S04 (Bordeaux), S05 (Strasbourg).");
    }

    @Test
    void reportsAnUnknownProductBeforeTheStore() {
        CallToolResult result = call("get_stock", Map.of("sku", "P-00000", "storeId", "S99"));

        assertThat(result.isError()).isTrue();
        assertThat(texts(result))
                .containsExactly("Product not found: P-00000. Use list_products to find the SKU of a product.");
    }
}
