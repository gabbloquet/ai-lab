package io.github.gabbloquet.ailab.exp001.catalog.infra.out.memory;

import static java.util.stream.Collectors.toUnmodifiableMap;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;

import io.github.gabbloquet.ailab.exp001.catalog.domain.port.StockRepository;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StockLine;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;

public final class InMemoryStockRepository implements StockRepository {

    private record StockKey(SkuCode sku, StoreId storeId) {
    }

    private final Map<StockKey, StockLine> stockByKey;

    public InMemoryStockRepository(List<StockLine> stockLines) {
        this.stockByKey = stockLines.stream()
                .collect(toUnmodifiableMap(line -> new StockKey(line.sku(), line.storeId()), Function.identity()));
    }

    @Override
    public Optional<StockLine> find(SkuCode sku, StoreId storeId) {
        return Optional.ofNullable(stockByKey.get(new StockKey(sku, storeId)));
    }
}
