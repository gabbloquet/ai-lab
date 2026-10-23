package io.github.gabbloquet.ailab.exp001.catalog.domain.error;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;

public final class StoreNotFoundException extends CatalogException {

    private final StoreId storeId;

    public StoreNotFoundException(StoreId storeId) {
        super("Unknown store: " + storeId);
        this.storeId = storeId;
    }

    public StoreId storeId() {
        return storeId;
    }
}
