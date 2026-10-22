package io.github.gabbloquet.ailab.exp001.catalog.domain;

import static java.util.stream.Collectors.toUnmodifiableMap;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;

public class Catalog {

    private record StockKey(SkuCode sku, StoreId storeId) {
    }

    private final List<Product> products;
    private final List<Store> stores;
    private final List<StockLine> stockLines;
    private final Map<SkuCode, Product> productsBySku;
    private final Map<StockKey, StockLine> stockByKey;

    /**
     * Un SKU en double, ou deux lignes de stock pour le même couple produit × magasin,
     * font échouer la construction : un catalogue incohérent ne doit pas démarrer.
     */
    public Catalog(List<Product> products, List<Store> stores, List<StockLine> stockLines) {
        this.products = List.copyOf(products);
        this.stores = List.copyOf(stores);
        this.stockLines = List.copyOf(stockLines);
        this.productsBySku = this.products.stream()
                .collect(toUnmodifiableMap(Product::sku, Function.identity()));
        this.stockByKey = this.stockLines.stream()
                .collect(toUnmodifiableMap(line -> new StockKey(line.sku(), line.storeId()), Function.identity()));
    }

    public List<Product> products() {
        return products;
    }

    public List<Store> stores() {
        return stores;
    }

    public List<StockLine> stockLines() {
        return stockLines;
    }

    public Optional<Product> product(SkuCode sku) {
        return Optional.ofNullable(productsBySku.get(sku));
    }

    public Optional<StockLine> stock(SkuCode sku, StoreId storeId) {
        return Optional.ofNullable(stockByKey.get(new StockKey(sku, storeId)));
    }
}
