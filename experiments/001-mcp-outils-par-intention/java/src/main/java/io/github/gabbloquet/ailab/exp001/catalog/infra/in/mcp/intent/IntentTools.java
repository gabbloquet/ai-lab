package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import io.github.gabbloquet.ailab.exp001.catalog.domain.*;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.*;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.ToolResults;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto.Availability;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto.CatalogSearchResults;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto.InStockAlternatives;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto.ProductDetails;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto.StoresWithStock;
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
        return toolResults.run(() -> ProductDetails.from(catalog.requireProduct(new SkuCode(sku))));
    }

    @McpTool(name = "check_availability",
            description = "Returns how many units of a product can be sold in a store (stock minus reserved units),"
                    + " and whether it is in stock.",
            annotations = @McpTool.McpAnnotations(readOnlyHint = true, idempotentHint = true, destructiveHint = false, openWorldHint = false))
    public CallToolResult checkAvailability(
            @McpToolParam(description = "SKU of the product: P- followed by 5 digits.", required = true) String sku,
            @McpToolParam(description = "ID of the store: S followed by 2 digits.", required = true) String storeId) {
        return toolResults.run(() -> {
            Product product = catalog.requireProduct(new SkuCode(sku));
            Store store = catalog.requireStore(new StoreId(storeId));
            int available = catalog.stock(product.sku(), store.storeId()).map(StockLine::available).orElse(0);
            return Availability.of(product, store, available);
        });
    }

    @McpTool(name = "find_stores_with_stock",
            description = "Returns the stores where a product can be sold, with the number of units available in each store. The list is empty when the product is out of stock everywhere.",
            annotations = @McpTool.McpAnnotations(readOnlyHint = true, idempotentHint = true, destructiveHint = false, openWorldHint = false))
    public CallToolResult findStoresWithStock(
            @McpToolParam(description = "SKU of the product: P- followed by 5 digits.", required = true) String sku) {
        return toolResults.run(() -> {
            Product product = catalog.requireProduct(new SkuCode(sku));
            return StoresWithStock.of(product, catalog.storesWithStock(product.sku()));
        });
    }

    @McpTool(name = "find_in_stock_alternative",
            description = "Returns up to 3 products of the same type, priced within 20% of the requested product, that can be sold in the store, closest price first. The list is empty when there is no such product.",
            annotations = @McpTool.McpAnnotations(readOnlyHint = true, idempotentHint = true, destructiveHint = false, openWorldHint = false))
    public CallToolResult findInStockAlternative(
            @McpToolParam(description = "SKU of the product: P- followed by 5 digits.", required = true) String sku,
            @McpToolParam(description = "ID of the store: S followed by 2 digits.", required = true) String storeId) {
        return toolResults.run(() -> {
            Product product = catalog.requireProduct(new SkuCode(sku));
            Store store = catalog.requireStore(new StoreId(storeId));
            return InStockAlternatives.of(catalog.alternatives(product.sku(), store.storeId()));
        });
    }

    @McpTool(name = "search_catalog",
            description = "Searches products whose name, brand or type contain every word of the query, ignoring case and accents. Returns at most 10 products, sorted by name, and the total number of matches."
                    + " If total is greater than the number of products returned, refine the query or use a category.",
            annotations = @McpTool.McpAnnotations(readOnlyHint = true, idempotentHint = true, destructiveHint = false, openWorldHint = false))
    public CallToolResult searchCatalog(
            @McpToolParam(description = "Words to look for in the product name, brand or type.", required = true) String query,
            @McpToolParam(description = "Department to search in: Audio, Informatique, Maison or Sport.", required = false) String category) {
        return toolResults.run(() -> CatalogSearchResults.of(catalog.search(query, category)));
    }
}
