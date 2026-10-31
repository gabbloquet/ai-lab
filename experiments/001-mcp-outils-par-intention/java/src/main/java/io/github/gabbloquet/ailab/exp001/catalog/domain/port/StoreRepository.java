package io.github.gabbloquet.ailab.exp001.catalog.domain.port;

import java.util.List;
import java.util.Optional;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;

public interface StoreRepository {

    Optional<Store> findById(StoreId storeId);

    List<Store> findAll();
}
