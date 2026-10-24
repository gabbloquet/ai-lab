package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.boot.test.context.SpringBootTest.WebEnvironment.RANDOM_PORT;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;

@SpringBootTest(webEnvironment = RANDOM_PORT, properties = "lab.variant=intent")
class OriginValidationContractTest {

    private static final String INITIALIZE = """
            {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25",\
            "capabilities":{},"clientInfo":{"name":"contract-test","version":"1"}}}""";

    private final HttpClient http = HttpClient.newHttpClient();

    @LocalServerPort
    private int port;

    @Test
    void rejectsAForeignOrigin() throws Exception {
        HttpResponse<String> response = initialize("https://evil.example");

        assertThat(response.statusCode()).isEqualTo(403);
        assertThat(response.body()).isEqualTo("Invalid Origin header");
    }

    @Test
    void rejectsAnOriginThatOnlyStartsLikeLocalhost() throws Exception {
        assertThat(initialize("http://localhost.evil.example").statusCode()).isEqualTo(403);
    }

    @Test
    void acceptsALocalBrowserOnAnyPort() throws Exception {
        assertThat(initialize("http://localhost:6274").statusCode()).isEqualTo(200);
        assertThat(initialize("http://127.0.0.1:3000").statusCode()).isEqualTo(200);
    }

    @Test
    void acceptsAClientThatSendsNoOrigin() throws Exception {
        assertThat(initialize(null).statusCode()).isEqualTo(200);
    }

    private HttpResponse<String> initialize(String origin) throws Exception {
        HttpRequest.Builder request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + "/mcp"))
                .header("Content-Type", "application/json")
                .header("Accept", "application/json, text/event-stream")
                .POST(HttpRequest.BodyPublishers.ofString(INITIALIZE));
        if (origin != null) {
            request.header("Origin", origin);
        }
        return http.send(request.build(), HttpResponse.BodyHandlers.ofString());
    }
}
