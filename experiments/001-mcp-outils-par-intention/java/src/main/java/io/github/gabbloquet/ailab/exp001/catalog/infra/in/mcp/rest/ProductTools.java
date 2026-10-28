package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.ToolResults;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto.ProductList;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto.ProductResource;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto.SimilarProducts;
import io.modelcontextprotocol.spec.McpSchema.CallToolResult;
import org.springframework.ai.mcp.annotation.McpTool;
import org.springframework.ai.mcp.annotation.McpToolParam;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "lab.variant", havingValue = "rest")
public class ProductTools {

    private final Catalog catalog;
    private final ToolResults toolResults;

    public ProductTools(Catalog catalog, ToolResults toolResults) {
        this.catalog = catalog;
        this.toolResults = toolResults;
    }

    @McpTool(name = "get_product",
            description = "Returns a product from its SKU: name, brand, department, type and price in euros.",
            annotations = @McpTool.McpAnnotations(readOnlyHint = true, idempotentHint = true, destructiveHint = false, openWorldHint = false))
    public CallToolResult getProduct(@McpToolParam(description = "SKU of the product: P- followed by 5 digits.", required = true) String sku) {
        return toolResults.run(() -> ProductResource.from(catalog.requireProduct(new SkuCode(sku))));
    }

    @McpTool(name = "get_similar",
            description = "Returns the products of the same type as the requested product, priced within 20% of its price,"
                    + " whatever their stock, closest price first. Returns at most 10 products and the total number of"
                    + " similar products.",
            annotations = @McpTool.McpAnnotations(readOnlyHint = true, idempotentHint = true, destructiveHint = false, openWorldHint = false))
    public CallToolResult getSimilar(@McpToolParam(description = "SKU of the product: P- followed by 5 digits.", required = true) String sku) {
        return toolResults.run(() -> {
            Product product = catalog.requireProduct(new SkuCode(sku));
            return SimilarProducts.of(catalog.similar(product.sku()));
        });
    }

    @McpTool(name = "list_products",
            description = "Lists products sorted by name: every product, or those of a category. With a query, keeps the"
                    + " products whose name, brand or type contain every word of the query, ignoring case and accents."
                    + " Returns at most 10 products and the total number of matches."
                    + " If total is greater than the number of products returned, refine the query or use a category.",
            annotations = @McpTool.McpAnnotations(readOnlyHint = true, idempotentHint = true, destructiveHint = false, openWorldHint = false))
    public CallToolResult listProducts(
            @McpToolParam(description = "Words to look for in the product name, brand or type.", required = false) String query,
            @McpToolParam(description = "Department to search in: Audio, Informatique, Maison or Sport.", required = false) String category) {
        return toolResults.run(() -> ProductList.of(query == null || query.isBlank()
                ? catalog.browse(category)
                : catalog.search(query, category)));
    }
}
