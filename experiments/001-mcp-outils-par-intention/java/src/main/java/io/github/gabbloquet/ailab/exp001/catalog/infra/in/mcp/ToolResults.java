package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp;

import java.util.function.Supplier;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import io.modelcontextprotocol.spec.McpSchema.CallToolResult;
import tools.jackson.databind.json.JsonMapper;

@Component
public class ToolResults {

    private static final Logger LOG = LoggerFactory.getLogger(ToolResults.class);

    static final String INTERNAL_ERROR = "Internal error while running the tool. Try again later.";

    private final JsonMapper jsonMapper;

    public ToolResults(JsonMapper jsonMapper) {
        this.jsonMapper = jsonMapper;
    }

    public CallToolResult run(Supplier<?> tool) {
        try {
            return CallToolResult.builder().addTextContent(jsonMapper.writeValueAsString(tool.get())).build();
        } catch (ToolException | IllegalArgumentException e) {
            return error(e.getMessage());
        } catch (RuntimeException e) {
            LOG.error("Erreur inattendue pendant l'exécution d'un outil", e);
            return error(INTERNAL_ERROR);
        }
    }

    private static CallToolResult error(String message) {
        return CallToolResult.builder().isError(true).addTextContent(message).build();
    }
}
