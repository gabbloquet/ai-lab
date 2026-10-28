package io.github.gabbloquet.ailab.exp001.catalog.domain;

import io.github.gabbloquet.ailab.exp001.catalog.domain.error.DepartmentNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.InvalidSearchQueryException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.ProductNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.StoreNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.*;

import static java.util.Comparator.comparing;
import static java.util.stream.Collectors.toUnmodifiableMap;

import java.math.BigDecimal;
import java.text.Normalizer;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;

public class Catalog {

    static final BigDecimal PRICE_TOLERANCE = new BigDecimal("0.20");
    static final int MAX_ALTERNATIVES = 3;

    private record StockKey(SkuCode sku, StoreId storeId) {
    }

    private final List<Product> products;
    private final List<Store> stores;
    private final List<StockLine> stockLines;
    private final Map<SkuCode, Product> productsBySku;
    private final Map<StoreId, Store> storesById;
    private final Map<StockKey, StockLine> stockByKey;

    public Catalog(List<Product> products, List<Store> stores, List<StockLine> stockLines) {
        this.products = List.copyOf(products);
        this.stores = List.copyOf(stores);
        this.stockLines = List.copyOf(stockLines);
        this.productsBySku = this.products.stream()
                .collect(toUnmodifiableMap(Product::sku, Function.identity()));
        this.storesById = this.stores.stream()
                .collect(toUnmodifiableMap(Store::storeId, Function.identity()));
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

    public Optional<Store> store(StoreId storeId) {
        return Optional.ofNullable(storesById.get(storeId));
    }

    public Product requireProduct(SkuCode sku) {
        return product(sku).orElseThrow(() -> new ProductNotFoundException(sku));
    }

    public Store requireStore(StoreId storeId) {
        return store(storeId).orElseThrow(() -> new StoreNotFoundException(storeId));
    }

    public List<String> departments() {
        return products.stream().map(Product::department).distinct().sorted().toList();
    }

    public Optional<StockLine> stock(SkuCode sku, StoreId storeId) {
        return Optional.ofNullable(stockByKey.get(new StockKey(sku, storeId)));
    }

    public List<StoreStock> storesWithStock(SkuCode sku) {
        return stores.stream()
                .sorted(comparing(store -> store.storeId().value()))
                .map(store -> new StoreStock(store, available(sku, store.storeId())))
                .filter(stock -> stock.available() > 0)
                .toList();
    }

    public List<Alternative> alternatives(SkuCode sku, StoreId storeId) {
        Product reference = productsBySku.get(sku);
        if (reference == null) {
            return List.of();
        }
        BigDecimal low = reference.price().multiply(BigDecimal.ONE.subtract(PRICE_TOLERANCE));
        BigDecimal high = reference.price().multiply(BigDecimal.ONE.add(PRICE_TOLERANCE));
        return products.stream()
                .filter(candidate -> candidate.type().equals(reference.type()))
                .filter(candidate -> !candidate.sku().equals(sku))
                .filter(candidate -> candidate.price().compareTo(low) >= 0 && candidate.price().compareTo(high) <= 0)
                .map(candidate -> new Alternative(candidate, available(candidate.sku(), storeId)))
                .filter(alternative -> alternative.available() > 0)
                .sorted(comparing((Alternative alternative) -> alternative.product().price().subtract(reference.price()).abs())
                        .thenComparing(alternative -> alternative.product().sku().value()))
                .limit(MAX_ALTERNATIVES)
                .toList();
    }

    public List<Product> browse(String department) {
        boolean filterOnDepartment = department != null && !department.isBlank();
        if (filterOnDepartment && departments().stream().noneMatch(known -> fold(known).equals(fold(department)))) {
            throw new DepartmentNotFoundException(department);
        }
        return products.stream()
                .filter(product -> !filterOnDepartment || fold(product.department()).equals(fold(department)))
                .sorted(comparing(Product::name).thenComparing(product -> product.sku().value()))
                .toList();
    }

    public List<Product> search(String query, String department) {
        if (query == null || query.isBlank()) {
            throw new InvalidSearchQueryException("Search query must not be blank");
        }
        boolean filterOnDepartment = department != null && !department.isBlank();
        if (filterOnDepartment && departments().stream().noneMatch(known -> fold(known).equals(fold(department)))) {
            throw new DepartmentNotFoundException(department);
        }
        List<String> words = Arrays.asList(fold(query).split("\\s+"));
        return products.stream()
                .filter(product -> !filterOnDepartment || fold(product.department()).equals(fold(department)))
                .filter(product -> {
                    String text = fold(product.name() + " " + product.brand() + " " + product.type());
                    return words.stream().allMatch(text::contains);
                })
                .sorted(comparing(Product::name).thenComparing(product -> product.sku().value()))
                .toList();
    }

    private int available(SkuCode sku, StoreId storeId) {
        return stock(sku, storeId).map(StockLine::available).orElse(0);
    }

    private static String fold(String text) {
        return Normalizer.normalize(text, Normalizer.Form.NFD)
                .replaceAll("\\p{M}", "")
                .toLowerCase(Locale.ROOT)
                .strip();
    }
}
