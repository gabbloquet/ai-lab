package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.boot.test.context.SpringBootTest.WebEnvironment.RANDOM_PORT;

import java.time.Duration;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;

import io.modelcontextprotocol.client.McpClient;
import io.modelcontextprotocol.client.McpSyncClient;
import io.modelcontextprotocol.client.transport.HttpClientStreamableHttpTransport;
import io.modelcontextprotocol.spec.McpSchema.CallToolRequest;
import io.modelcontextprotocol.spec.McpSchema.CallToolResult;
import io.modelcontextprotocol.spec.McpSchema.TextContent;
import io.modelcontextprotocol.spec.McpSchema.Tool;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest(webEnvironment = RANDOM_PORT, properties = "lab.variant=intent")
class IntentToolsContractTest {

    @LocalServerPort
    private int port;

    private McpSyncClient client;

    @BeforeEach
    void connect() {
        var transport = HttpClientStreamableHttpTransport.builder("http://127.0.0.1:" + port)
                .endpoint("/mcp")
                .build();
        client = McpClient.sync(transport).requestTimeout(Duration.ofSeconds(10)).build();
        client.initialize();
    }

    @AfterEach
    void disconnect() {
        client.closeGracefully();
    }

    @Test
    void exposesOnlyTheIntentTools() {
        assertThat(client.listTools().tools()).extracting(Tool::name)
                .containsExactlyInAnyOrder("get_product_details", "check_availability", "find_stores_with_stock",
                        "find_in_stock_alternative", "search_catalog");
    }

    @Test
    @SuppressWarnings("unchecked")
    void asksForAQueryAndAnOptionalCategoryToSearch() {
        Map<String, Object> schema = tool("search_catalog").inputSchema();
        Map<String, Object> properties = (Map<String, Object>) schema.get("properties");

        assertThat(properties).containsOnlyKeys("query", "category");
        assertThat((List<String>) schema.get("required")).containsExactly("query");
    }

    @Test
    void searchesEveryWordIgnoringCaseAndAccents() {
        CallToolResult result = call("search_catalog", Map.of("query", "CAFETIERE pellisse"));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"total":2,"products":[\
                {"sku":"P-14165","name":"Pellisse Cafetière F5","brand":"Pellisse","department":"Maison",\
                "type":"Cafetière","price":157.0,"currency":"EUR"},\
                {"sku":"P-13905","name":"Pellisse Cafetière G9","brand":"Pellisse","department":"Maison",\
                "type":"Cafetière","price":101.99,"currency":"EUR"}]}""");
    }

    @Test
    void filtersTheSearchOnACategory() {
        CallToolResult result = call("search_catalog", Map.of("query", "veldric", "category", "audio"));

        assertThat(texts(result)).containsExactly("""
                {"total":2,"products":[\
                {"sku":"P-15695","name":"Veldric Casque K8","brand":"Veldric","department":"Audio",\
                "type":"Casque","price":100.0,"currency":"EUR"},\
                {"sku":"P-23396","name":"Veldric Écouteurs R7","brand":"Veldric","department":"Audio",\
                "type":"Écouteurs","price":76.5,"currency":"EUR"}]}""");
    }

    @Test
    void explainsAnEmptySearchInsteadOfAnsweringWithNothing() {
        CallToolResult result = call("search_catalog", Map.of("query", "audio"));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"total":0,"products":[],\
                "hint":"No product matches every word of the query. The query searches product names, brands\
                 and types; use category to restrict to a department."}""");
    }

    record SearchSummary(int total, List<Map<String, Object>> products) {
    }

    @Test
    void returnsTenProductsAtMostButCountsEveryMatch() {
        CallToolResult result = call("search_catalog", Map.of("query", "e"));

        SearchSummary summary = JsonMapper.builder().build().readValue(texts(result).getFirst(), SearchSummary.class);
        assertThat(summary.total()).isEqualTo(49);
        assertThat(summary.products()).hasSize(10);
    }

    @Test
    void tellsTheModelToRefineTheSearchWhenResultsAreCapped() {
        assertThat(tool("search_catalog").description())
                .contains("If total is greater than the number of products returned, refine the query or use a category.");
    }

    @Test
    void reportsABlankSearchQuery() {
        CallToolResult result = call("search_catalog", Map.of("query", "  "));

        assertThat(result.isError()).isTrue();
        assertThat(texts(result)).containsExactly(
                "Search query must not be blank. Provide at least one word of a product name, brand or type."
                        + " To narrow the results to a department, use category.");
    }

    @Test
    void reportsAnUnknownCategoryWithTheKnownOnes() {
        CallToolResult result = call("search_catalog", Map.of("query", "casque", "category", "Hifi"));

        assertThat(result.isError()).isTrue();
        assertThat(texts(result))
                .containsExactly("Category not found: Hifi. Known categories: Audio, Informatique, Maison, Sport.");
    }

    @Test
    @SuppressWarnings("unchecked")
    void asksForTheSkuAsAPlainString() {
        Map<String, Object> schema = tool("get_product_details").inputSchema();
        Map<String, Object> properties = (Map<String, Object>) schema.get("properties");

        assertThat(properties).containsOnlyKeys("sku");
        assertThat((Map<String, Object>) properties.get("sku")).containsEntry("type", "string");
        assertThat((List<String>) schema.get("required")).containsExactly("sku");
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

    @Test
    void returnsTheProductDetailsAsJsonInASingleTextBlock() {
        CallToolResult result = call("get_product_details", Map.of("sku", "p-13905"));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"sku":"P-13905","name":"Pellisse Cafetière G9","brand":"Pellisse","department":"Maison",\
                "type":"Cafetière","price":101.99,"currency":"EUR"}""");
    }

    @Test
    void reportsAnUnknownProductOnceWithWhatToDoNext() {
        CallToolResult result = call("get_product_details", Map.of("sku", "P-00000"));

        assertThat(result.isError()).isTrue();
        assertThat(texts(result))
                .containsExactly("Product not found: P-00000. Use search_catalog to find the SKU of a product.");
    }

    @Test
    void reportsABlankSkuAsAnInvalidArgument() {
        CallToolResult result = call("get_product_details", Map.of("sku", "   "));

        assertThat(result.isError()).isTrue();
        assertThat(texts(result)).containsExactly("SKU must not be blank");
    }

    @Test
    void reportsAMalformedSkuWithTheExpectedFormat() {
        CallToolResult result = call("get_product_details", Map.of("sku", "80284"));

        assertThat(result.isError()).isTrue();
        assertThat(texts(result)).containsExactly("Invalid SKU: 80284. A SKU is P- followed by 5 digits.");
    }

    @Test
    void givesTheQuantityAvailableForSaleNetOfReservations() {
        CallToolResult result = call("check_availability", Map.of("sku", "P-38893", "storeId", "s04"));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"sku":"P-38893","name":"Zorvane Souris E8","storeId":"S04","storeName":"Magasin Bordeaux",\
                "available":0,"inStock":false}""");
    }

    @Test
    void reportsAnUnknownStoreWithTheKnownOnes() {
        CallToolResult result = call("check_availability", Map.of("sku", "P-38893", "storeId", "S99"));

        assertThat(result.isError()).isTrue();
        assertThat(texts(result)).containsExactly(
                "Store not found: S99. Known stores: S01 (Lyon), S02 (Nantes), S03 (Lille), S04 (Bordeaux),"
                        + " S05 (Strasbourg).");
    }

    @Test
    void listsTheStoresThatCanSellAProductWithTheirAvailableUnits() {
        CallToolResult result = call("find_stores_with_stock", Map.of("sku", "P-15695"));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"sku":"P-15695","name":"Veldric Casque K8","stores":[\
                {"storeId":"S01","name":"Magasin Lyon","city":"Lyon","available":8},\
                {"storeId":"S04","name":"Magasin Bordeaux","city":"Bordeaux","available":11},\
                {"storeId":"S05","name":"Magasin Strasbourg","city":"Strasbourg","available":7}]}""");
    }

    @Test
    void answersWithNoStoreWhenTheProductIsOutOfStockEverywhere() {
        CallToolResult result = call("find_stores_with_stock", Map.of("sku", "P-13478"));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"sku":"P-13478","name":"Tisanor Écran B6","stores":[]}""");
    }

    @Test
    void offersAlternativesAtBothBoundsOfThePriceBand() {
        CallToolResult result = call("find_in_stock_alternative", Map.of("sku", "P-15695", "storeId", "S02"));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"alternatives":[\
                {"sku":"P-26361","name":"Zorvane Casque P2","brand":"Zorvane","price":80.0,"currency":"EUR","available":4},\
                {"sku":"P-44671","name":"Ostrane Casque N4","brand":"Ostrane","price":120.0,"currency":"EUR","available":4}]}""");
    }

    @Test
    void offersNoAlternativeWhenNoneIsAvailableInTheStore() {
        CallToolResult result = call("find_in_stock_alternative", Map.of("sku", "P-22280", "storeId", "S03"));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"alternatives":[]}""");
    }

    @Test
    void reportsAnUnknownStoreWhenLookingForAlternatives() {
        CallToolResult result = call("find_in_stock_alternative", Map.of("sku", "P-15695", "storeId", "S99"));

        assertThat(result.isError()).isTrue();
        assertThat(texts(result)).containsExactly(
                "Store not found: S99. Known stores: S01 (Lyon), S02 (Nantes), S03 (Lille), S04 (Bordeaux),"
                        + " S05 (Strasbourg).");
    }

    @Test
    void reportsAnUnknownProductWhenLookingForStores() {
        CallToolResult result = call("find_stores_with_stock", Map.of("sku", "P-00000"));

        assertThat(result.isError()).isTrue();
        assertThat(texts(result))
                .containsExactly("Product not found: P-00000. Use search_catalog to find the SKU of a product.");
    }

    private Tool tool(String name) {
        return client.listTools().tools().stream()
                .filter(tool -> tool.name().equals(name))
                .findFirst()
                .orElseThrow();
    }

    private CallToolResult call(String tool, Map<String, Object> arguments) {
        return client.callTool(new CallToolRequest(tool, arguments));
    }

    private static List<String> texts(CallToolResult result) {
        return result.content().stream().map(content -> ((TextContent) content).text()).toList();
    }
}
