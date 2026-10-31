package io.github.gabbloquet.ailab.exp001.catalog.domain.port;

import java.util.List;
import java.util.Optional;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;

public interface ProductRepository {

    Optional<Product> findBySku(SkuCode sku);

    List<Product> findAll();
}
