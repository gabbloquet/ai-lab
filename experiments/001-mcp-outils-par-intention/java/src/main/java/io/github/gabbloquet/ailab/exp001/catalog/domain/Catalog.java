package io.github.gabbloquet.ailab.exp001.catalog.domain;

import io.github.gabbloquet.ailab.exp001.catalog.domain.error.DepartmentNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.InvalidSearchQueryException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.ProductNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.StoreNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.port.ProductRepository;
import io.github.gabbloquet.ailab.exp001.catalog.domain.port.StockRepository;
import io.github.gabbloquet.ailab.exp001.catalog.domain.port.StoreRepository;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.*;

import static java.util.Comparator.comparing;

import java.math.BigDecimal;
import java.text.Normalizer;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Optional;

public class Catalog {

    static final BigDecimal PRICE_TOLERANCE = new BigDecimal("0.20");
    static final int MAX_ALTERNATIVES = 3;

    private final ProductRepository products;
    private final StoreRepository stores;
    private final StockRepository stock;

    public Catalog(ProductRepository products, StoreRepository stores, StockRepository stock) {
        this.products = products;
        this.stores = stores;
        this.stock = stock;
    }

    public List<Store> stores() {
        return stores.findAll();
    }

    public Optional<Product> product(SkuCode sku) {
        return products.findBySku(sku);
    }

    public Optional<Store> store(StoreId storeId) {
        return stores.findById(storeId);
    }

    public Product requireProduct(SkuCode sku) {
        return product(sku).orElseThrow(() -> new ProductNotFoundException(sku));
    }

    public Store requireStore(StoreId storeId) {
        return store(storeId).orElseThrow(() -> new StoreNotFoundException(storeId));
    }

    public List<String> departments() {
        return products.findAll().stream().map(Product::department).distinct().sorted().toList();
    }

    public Optional<StockLine> stock(SkuCode sku, StoreId storeId) {
        return stock.find(sku, storeId);
    }

    public List<StoreStock> storesWithStock(SkuCode sku) {
        return stores.findAll().stream()
                .sorted(comparing(store -> store.storeId().value()))
                .map(store -> new StoreStock(store, available(sku, store.storeId())))
                .filter(stock -> stock.available() > 0)
                .toList();
    }

    public List<Product> similar(SkuCode sku) {
        return products.findBySku(sku).map(this::similarTo).orElse(List.of());
    }

    private List<Product> similarTo(Product reference) {
        BigDecimal low = reference.price().multiply(BigDecimal.ONE.subtract(PRICE_TOLERANCE));
        BigDecimal high = reference.price().multiply(BigDecimal.ONE.add(PRICE_TOLERANCE));
        return products.findAll().stream()
                .filter(candidate -> candidate.type().equals(reference.type()))
                .filter(candidate -> !candidate.sku().equals(reference.sku()))
                .filter(candidate -> candidate.price().compareTo(low) >= 0 && candidate.price().compareTo(high) <= 0)
                .sorted(comparing((Product candidate) -> candidate.price().subtract(reference.price()).abs())
                        .thenComparing(candidate -> candidate.sku().value()))
                .toList();
    }

    public List<Alternative> alternatives(SkuCode sku, StoreId storeId) {
        return similar(sku).stream()
                .map(candidate -> new Alternative(candidate, available(candidate.sku(), storeId)))
                .filter(alternative -> alternative.available() > 0)
                .limit(MAX_ALTERNATIVES)
                .toList();
    }

    public List<Product> browse(String department) {
        boolean filterOnDepartment = department != null && !department.isBlank();
        if (filterOnDepartment && departments().stream().noneMatch(known -> fold(known).equals(fold(department)))) {
            throw new DepartmentNotFoundException(department);
        }
        return products.findAll().stream()
                .filter(product -> !filterOnDepartment || fold(product.department()).equals(fold(department)))
                .sorted(comparing(Product::name).thenComparing(product -> product.sku().value()))
                .toList();
    }

    public List<Product> search(String query, String department) {
        if (query == null || query.isBlank()) {
            throw new InvalidSearchQueryException("Search query must not be blank");
        }
        List<String> words = Arrays.asList(fold(query).split("\\s+"));
        return browse(department).stream()
                .filter(product -> {
                    String text = fold(product.name() + " " + product.brand() + " " + product.type());
                    return words.stream().allMatch(text::contains);
                })
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
