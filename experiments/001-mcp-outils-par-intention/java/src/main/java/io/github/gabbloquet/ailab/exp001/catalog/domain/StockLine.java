package io.github.gabbloquet.ailab.exp001.catalog.domain;

public record StockLine(SkuCode sku, StoreId storeId, int onHand, int reserved) {

    public int available() {
        return onHand - reserved;
    }
}
