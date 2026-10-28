package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;

public record StockLevel(String sku, String storeId, int available) {

    public static StockLevel of(Product product, Store store, int available) {
        return new StockLevel(product.sku().value(), store.storeId().value(), available);
    }
}
