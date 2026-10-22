package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp;

import io.github.gabbloquet.ailab.exp001.catalog.domain.SkuCode;

public class ProductNotFoundException extends ToolException {

    public ProductNotFoundException(SkuCode sku) {
        super("Product not found: " + sku + ". Use search_catalog to find the SKU of a product.");
    }
}
