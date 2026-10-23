package io.github.gabbloquet.ailab.exp001.catalog.domain;

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

/**
 * Catalogue en mémoire et règles métier du domaine magasin (domains/magasin/README.md).
 * L'oracle Python (domains/magasin/magasin_rules.py) applique les mêmes règles ; OracleConformanceTest le vérifie.
 */
public class Catalog {

    /** Fourchette de prix d'une alternative : ±20 % autour du prix du produit demandé, bornes incluses. */
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

    public Optional<StockLine> stock(SkuCode sku, StoreId storeId) {
        return Optional.ofNullable(stockByKey.get(new StockKey(sku, storeId)));
    }

    /** Magasins où le produit a des unités disponibles à la vente, triés par identifiant. */
    public List<StoreStock> storesWithStock(SkuCode sku) {
        return stores.stream()
                .sorted(comparing(store -> store.storeId().value()))
                .map(store -> new StoreStock(store, available(sku, store.storeId())))
                .filter(stock -> stock.available() > 0)
                .toList();
    }

    /**
     * Produits du même type, différents du produit demandé, dont le prix est à ±20 % (bornes incluses)
     * et qui ont des unités disponibles dans le magasin. Triés par écart de prix puis par SKU ; 3 au plus.
     * Aucun résultat pour un produit inconnu.
     */
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

    /**
     * Produits dont le nom, la marque ou le type contiennent chacun des mots de la requête, sans tenir compte
     * de la casse ni des accents, éventuellement filtrés sur un rayon. Triés par nom puis par SKU.
     */
    public List<Product> search(String query, String department) {
        if (query == null || query.isBlank()) {
            throw new IllegalArgumentException("Search query must not be blank");
        }
        List<String> words = Arrays.asList(fold(query).split("\\s+"));
        boolean filterOnDepartment = department != null && !department.isBlank();
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

    /** Minuscules, sans accents ni espaces autour : « Cafetière » et « CAFETIERE » deviennent « cafetiere ». */
    private static String fold(String text) {
        return Normalizer.normalize(text, Normalizer.Form.NFD)
                .replaceAll("\\p{M}", "")
                .toLowerCase(Locale.ROOT)
                .strip();
    }
}
