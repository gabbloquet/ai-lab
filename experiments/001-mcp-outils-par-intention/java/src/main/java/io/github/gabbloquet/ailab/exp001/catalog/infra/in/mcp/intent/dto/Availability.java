package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;

public record Availability(
        String sku,
        String name,
        String storeId,
        String storeName,
        int available,
        boolean inStock) {

    public static Availability of(Product product, Store store, int available) {
        return new Availability(
                product.sku().value(),
                product.name(),
                store.storeId().value(),
                store.name(),
                available,
                available > 0);
    }
}
