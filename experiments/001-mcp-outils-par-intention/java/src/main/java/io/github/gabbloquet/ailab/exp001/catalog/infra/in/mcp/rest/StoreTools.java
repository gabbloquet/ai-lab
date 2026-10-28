package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.ToolResults;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto.StoreList;
import io.modelcontextprotocol.spec.McpSchema.CallToolResult;
import org.springframework.ai.mcp.annotation.McpTool;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "lab.variant", havingValue = "rest")
public class StoreTools {

    private final Catalog catalog;
    private final ToolResults toolResults;

    public StoreTools(Catalog catalog, ToolResults toolResults) {
        this.catalog = catalog;
        this.toolResults = toolResults;
    }

    @McpTool(name = "list_stores",
            description = "Returns every store with its ID, name and city.",
            annotations = @McpTool.McpAnnotations(readOnlyHint = true, idempotentHint = true, destructiveHint = false, openWorldHint = false))
    public CallToolResult listStores() {
        return toolResults.run(() -> StoreList.of(catalog.stores()));
    }
}
