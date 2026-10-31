package io.github.gabbloquet.ailab.exp001.catalog.infra.out.memory;

import static java.util.stream.Collectors.toUnmodifiableMap;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;
import io.github.gabbloquet.ailab.exp001.catalog.domain.port.StoreRepository;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;

public final class InMemoryStoreRepository implements StoreRepository {

    private final List<Store> stores;
    private final Map<StoreId, Store> storesById;

    public InMemoryStoreRepository(List<Store> stores) {
        this.stores = List.copyOf(stores);
        this.storesById = this.stores.stream().collect(toUnmodifiableMap(Store::storeId, Function.identity()));
    }

    @Override
    public Optional<Store> findById(StoreId storeId) {
        return Optional.ofNullable(storesById.get(storeId));
    }

    @Override
    public List<Store> findAll() {
        return stores;
    }
}
