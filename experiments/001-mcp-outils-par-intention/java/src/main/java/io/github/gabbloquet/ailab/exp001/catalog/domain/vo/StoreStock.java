package io.github.gabbloquet.ailab.exp001.catalog.domain.vo;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;

public record StoreStock(Store store, int available) {
}
