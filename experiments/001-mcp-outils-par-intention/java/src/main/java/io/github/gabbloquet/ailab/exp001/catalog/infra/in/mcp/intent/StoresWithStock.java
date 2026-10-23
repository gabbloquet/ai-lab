package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.StoreStock;

import java.util.List;

public record StoresWithStock(String sku, String name, List<StoreAvailability> stores) {

    public record StoreAvailability(String storeId, String name, String city, int available) { }

    public static StoresWithStock of(Product product, List<StoreStock> stores) {
        List<StoreAvailability> storeAvailability = stores.stream()
                .map(storeStock -> new StoreAvailability(storeStock.store().storeId().value(), storeStock.store().name(), storeStock.store().city(), storeStock.available()))
                .toList();
        return new StoresWithStock(product.sku().value(), product.name(), storeAvailability);
    }
}
