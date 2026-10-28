package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StockLine;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.ToolResults;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto.StockLevel;
import io.modelcontextprotocol.spec.McpSchema.CallToolResult;
import org.springframework.ai.mcp.annotation.McpTool;
import org.springframework.ai.mcp.annotation.McpToolParam;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "lab.variant", havingValue = "rest")
public class StockTools {

    private final Catalog catalog;
    private final ToolResults toolResults;

    public StockTools(Catalog catalog, ToolResults toolResults) {
        this.catalog = catalog;
        this.toolResults = toolResults;
    }

    @McpTool(name = "get_stock",
            description = "Returns the stock of a product in a store: the number of units that can be sold (stock minus reserved units).",
            annotations = @McpTool.McpAnnotations(readOnlyHint = true, idempotentHint = true, destructiveHint = false, openWorldHint = false))
    public CallToolResult getStock(
            @McpToolParam(description = "SKU of the product: P- followed by 5 digits.", required = true) String sku,
            @McpToolParam(description = "ID of the store: S followed by 2 digits.", required = true) String storeId) {
        return toolResults.run(() -> {
            Product product = catalog.requireProduct(new SkuCode(sku));
            Store store = catalog.requireStore(new StoreId(storeId));
            int available = catalog.stock(product.sku(), store.storeId()).map(StockLine::available).orElse(0);
            return StockLevel.of(product, store, available);
        });
    }
}
