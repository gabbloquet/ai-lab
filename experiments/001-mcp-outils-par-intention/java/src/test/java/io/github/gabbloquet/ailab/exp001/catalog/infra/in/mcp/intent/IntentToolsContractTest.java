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

/**
 * Contrat public de la variante intent, vu par un vrai client MCP en Streamable HTTP :
 * ce que voit le modèle (outils, schéma, annotations) et ce qu'il reçoit (réponses, erreurs).
 * Sert aussi de garde-fou au SDK MCP 2.1.0 imposé au-dessus de la 2.0.0 tirée par Spring AI.
 */
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
                .containsExactlyInAnyOrder("get_product_details");
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
    void declaresTheToolAsReadOnlyOnAClosedDomain() {
        var annotations = tool("get_product_details").annotations();

        assertThat(annotations.readOnlyHint()).isTrue();
        assertThat(annotations.destructiveHint()).isFalse();
        assertThat(annotations.idempotentHint()).isTrue();
        assertThat(annotations.openWorldHint()).isFalse();
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
