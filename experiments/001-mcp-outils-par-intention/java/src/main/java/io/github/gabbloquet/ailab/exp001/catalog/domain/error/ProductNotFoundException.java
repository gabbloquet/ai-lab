package io.github.gabbloquet.ailab.exp001.catalog.domain.error;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;

public final class ProductNotFoundException extends CatalogException {

    private final SkuCode sku;

    public ProductNotFoundException(SkuCode sku) {
        super("Unknown product: " + sku);
        this.sku = sku;
    }

    public SkuCode sku() {
        return sku;
    }
}
