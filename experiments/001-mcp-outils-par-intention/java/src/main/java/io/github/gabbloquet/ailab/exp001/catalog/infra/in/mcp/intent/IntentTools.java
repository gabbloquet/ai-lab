package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.domain.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.domain.StockLine;
import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;
import io.github.gabbloquet.ailab.exp001.catalog.domain.StoreId;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.ProductNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.StoreNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.ToolResults;
import io.modelcontextprotocol.spec.McpSchema.CallToolResult;
import org.springframework.ai.mcp.annotation.McpTool;
import org.springframework.ai.mcp.annotation.McpToolParam;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "lab.variant", havingValue = "intent")
public class IntentTools {

    private final Catalog catalog;
    private final ToolResults toolResults;

    public IntentTools(Catalog catalog, ToolResults toolResults) {
        this.catalog = catalog;
        this.toolResults = toolResults;
    }

    @McpTool(name = "get_product_details",
            description = "Returns the details of a product from its SKU: name, brand, department, type and price in euros.",
            annotations = @McpTool.McpAnnotations(readOnlyHint = true, idempotentHint = true, destructiveHint = false, openWorldHint = false))
    public CallToolResult getProductDetails(@McpToolParam(description = "SKU of the product: P- followed by 5 digits.", required = true) String sku) {
        return toolResults.run(() -> {
            SkuCode skuCode = new SkuCode(sku);
            return catalog.product(skuCode)
                    .map(ProductDetails::from)
                    .orElseThrow(() -> new ProductNotFoundException(skuCode));
        });
    }


    @McpTool(name = "check_availability",
            description = "Returns how many units of a product can be sold in a store (stock minus reserved units),"
                    + " and whether it is in stock.",
            annotations = @McpTool.McpAnnotations(readOnlyHint = true, idempotentHint = true, destructiveHint = false, openWorldHint = false))
    public CallToolResult checkAvailability(
            @McpToolParam(description = "SKU of the product: P- followed by 5 digits.", required = true) String sku,
            @McpToolParam(description = "ID of the store: S followed by 2 digits.", required = true) String storeId) {
        return toolResults.run(() -> {
            SkuCode skuCode = new SkuCode(sku);
            StoreId id = new StoreId(storeId);
            Product product = catalog.product(skuCode).orElseThrow(() -> new ProductNotFoundException(skuCode));
            Store store = catalog.store(id).orElseThrow(() -> new StoreNotFoundException(id, catalog.storeIds()));
            int available = catalog.stock(skuCode, id).map(StockLine::available).orElse(0);
            return Availability.of(product, store, available);
        });
    }
}
