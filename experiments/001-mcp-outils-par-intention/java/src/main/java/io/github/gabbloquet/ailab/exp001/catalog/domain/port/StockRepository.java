package io.github.gabbloquet.ailab.exp001.catalog.domain.port;

import java.util.Optional;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StockLine;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;

public interface StockRepository {

    Optional<StockLine> find(SkuCode sku, StoreId storeId);
}
