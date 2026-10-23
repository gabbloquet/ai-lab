package io.github.gabbloquet.ailab.exp001.catalog.domain;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;

public record Store(StoreId storeId, String name, String city) {
}
