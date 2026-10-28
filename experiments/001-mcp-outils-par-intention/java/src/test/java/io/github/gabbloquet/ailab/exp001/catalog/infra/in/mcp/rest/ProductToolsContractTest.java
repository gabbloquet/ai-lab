package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

import io.modelcontextprotocol.spec.McpSchema.CallToolResult;

class ProductToolsContractTest extends RestContractTestBase {

    @Test
    @SuppressWarnings("unchecked")
    void asksForTheSkuAsAPlainString() {
        for (String name : List.of("get_product", "get_similar")) {
            Map<String, Object> schema = tool(name).inputSchema();
            Map<String, Object> properties = (Map<String, Object>) schema.get("properties");

            assertThat(properties).as(name).containsOnlyKeys("sku");
            assertThat((Map<String, Object>) properties.get("sku")).as(name).containsEntry("type", "string");
            assertThat((List<String>) schema.get("required")).as(name).containsExactly("sku");
        }
    }

    @Test
    void returnsTheProductAsJsonInASingleTextBlock() {
        CallToolResult result = call("get_product", Map.of("sku", "p-10851"));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"sku":"P-10851","name":"Brivaux Clavier E6","brand":"Brivaux","department":"Informatique",\
                "type":"Clavier","price":158.0,"currency":"EUR"}""");
    }

    @Test
    void reportsAnUnknownProductOnceWithWhatToDoNext() {
        CallToolResult result = call("get_product", Map.of("sku", "P-00000"));

        assertThat(result.isError()).isTrue();
        assertThat(texts(result))
                .containsExactly("Product not found: P-00000. Use list_products to find the SKU of a product.");
    }

    @Test
    void reportsAMalformedSkuWithTheExpectedFormat() {
        CallToolResult result = call("get_product", Map.of("sku", "80284"));

        assertThat(result.isError()).isTrue();
        assertThat(texts(result)).containsExactly("Invalid SKU: 80284. A SKU is P- followed by 5 digits.");
    }

    @Test
    void listsTheSimilarProductsWhateverTheirStock() {
        CallToolResult result = call("get_similar", Map.of("sku", "P-10851"));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"total":4,"products":[\
                {"sku":"P-46421","name":"Tisanor Clavier X1","brand":"Tisanor","department":"Informatique",\
                "type":"Clavier","price":157.9,"currency":"EUR"},\
                {"sku":"P-65392","name":"Ostrane Clavier S1","brand":"Ostrane","department":"Informatique",\
                "type":"Clavier","price":148.5,"currency":"EUR"},\
                {"sku":"P-30926","name":"Ostrane Clavier V2","brand":"Ostrane","department":"Informatique",\
                "type":"Clavier","price":173.8,"currency":"EUR"},\
                {"sku":"P-54597","name":"Ostrane Clavier M2","brand":"Ostrane","department":"Informatique",\
                "type":"Clavier","price":131.5,"currency":"EUR"}]}""");
    }

    @Test
    void answersWithNoSimilarProductForATypeWithASingleProduct() {
        CallToolResult result = call("get_similar", Map.of("sku", "P-93810"));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"total":0,"products":[]}""");
    }

    @Test
    void reportsAnUnknownProductWhenLookingForSimilarOnes() {
        CallToolResult result = call("get_similar", Map.of("sku", "P-00000"));

        assertThat(result.isError()).isTrue();
        assertThat(texts(result))
                .containsExactly("Product not found: P-00000. Use list_products to find the SKU of a product.");
    }

    @Test
    @SuppressWarnings("unchecked")
    void takesAnOptionalQueryAndAnOptionalCategoryToList() {
        Map<String, Object> schema = tool("list_products").inputSchema();

        assertThat((Map<String, Object>) schema.get("properties")).containsOnlyKeys("query", "category");
        assertThat((List<String>) schema.getOrDefault("required", List.of())).isEmpty();
    }

    @Test
    void listsACategoryWithoutQuerySortedByName() {
        CallToolResult result = call("list_products", Map.of("category", "sport"));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"total":6,"products":[\
                {"sku":"P-42098","name":"Brivaux Montre connectée V2","brand":"Brivaux","department":"Sport",\
                "type":"Montre connectée","price":95.0,"currency":"EUR"},\
                {"sku":"P-13278","name":"Junaro Montre connectée B2","brand":"Junaro","department":"Sport",\
                "type":"Montre connectée","price":396.9,"currency":"EUR"},\
                {"sku":"P-93810","name":"Ostrane Vélo d'appartement P3","brand":"Ostrane","department":"Sport",\
                "type":"Vélo d'appartement","price":718.9,"currency":"EUR"},\
                {"sku":"P-46048","name":"Tisanor Montre connectée H7","brand":"Tisanor","department":"Sport",\
                "type":"Montre connectée","price":351.5,"currency":"EUR"},\
                {"sku":"P-24592","name":"Veldric Montre connectée K4","brand":"Veldric","department":"Sport",\
                "type":"Montre connectée","price":182.9,"currency":"EUR"},\
                {"sku":"P-39256","name":"Zorvane Montre connectée T9","brand":"Zorvane","department":"Sport",\
                "type":"Montre connectée","price":140.0,"currency":"EUR"}]}""");
    }

    @Test
    void listsTenProductsOfTheWholeCatalogButCountsThemAll() {
        CallToolResult result = call("list_products", Map.of());

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).singleElement().asString()
                .startsWith("{\"total\":50,\"products\":[")
                .satisfies(text -> assertThat(text.split("\"sku\"", -1)).hasSize(11));
    }

    @Test
    void searchesEveryWordOfTheQueryInACategory() {
        CallToolResult result = call("list_products", Map.of("query", "montre VELDRIC", "category", "Sport"));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"total":1,"products":[\
                {"sku":"P-24592","name":"Veldric Montre connectée K4","brand":"Veldric","department":"Sport",\
                "type":"Montre connectée","price":182.9,"currency":"EUR"}]}""");
    }

    @Test
    void explainsAnEmptyListInsteadOfAnsweringWithNothing() {
        CallToolResult result = call("list_products", Map.of("query", "audio"));

        assertThat(result.isError()).isNotEqualTo(Boolean.TRUE);
        assertThat(texts(result)).containsExactly("""
                {"total":0,"products":[],"hint":"No product matches every word of the query. The query searches\
                 product names, brands and types; use category to restrict to a department."}""");
    }

    @Test
    void reportsAnUnknownCategoryWithTheKnownOnes() {
        CallToolResult result = call("list_products", Map.of("category", "Hifi"));

        assertThat(result.isError()).isTrue();
        assertThat(texts(result)).containsExactly(
                "Category not found: Hifi. Known categories: Audio, Informatique, Maison, Sport.");
    }
}
