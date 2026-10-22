package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.domain.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.ProductNotFoundException;
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
}
