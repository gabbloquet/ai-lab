package io.github.gabbloquet.ailab.exp001.catalog.infra.out.memory;

import static java.util.stream.Collectors.toUnmodifiableMap;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;

import io.github.gabbloquet.ailab.exp001.catalog.domain.port.ProductRepository;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;

public final class InMemoryProductRepository implements ProductRepository {

    private final List<Product> products;
    private final Map<SkuCode, Product> productsBySku;

    public InMemoryProductRepository(List<Product> products) {
        this.products = List.copyOf(products);
        this.productsBySku = this.products.stream().collect(toUnmodifiableMap(Product::sku, Function.identity()));
    }

    @Override
    public Optional<Product> findBySku(SkuCode sku) {
        return Optional.ofNullable(productsBySku.get(sku));
    }

    @Override
    public List<Product> findAll() {
        return products;
    }
}
