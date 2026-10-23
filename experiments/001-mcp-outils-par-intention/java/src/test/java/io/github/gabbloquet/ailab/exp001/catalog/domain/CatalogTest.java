package io.github.gabbloquet.ailab.exp001.catalog.domain;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigDecimal;
import java.util.List;

import io.github.gabbloquet.ailab.exp001.catalog.domain.error.ProductNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.StoreNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StockLine;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;
import org.junit.jupiter.api.Test;

class CatalogTest {

    private static final SkuCode HEADPHONES_SKU = new SkuCode("P-00001");
    private static final StoreId LYON = new StoreId("S01");

    private static final Product HEADPHONES =
            new Product(HEADPHONES_SKU, "Casque test", "Marque", "Audio", "Casque", new BigDecimal("100.00"));

    private final Catalog catalog = new Catalog(
            List.of(HEADPHONES),
            List.of(new Store(LYON, "Magasin test", "Lyon")),
            List.of(new StockLine(HEADPHONES_SKU, LYON, 3, 3))
    );

    @Test
    void findsAProductBySku() {
        assertThat(catalog.product(HEADPHONES_SKU)).contains(HEADPHONES);
    }

    @Test
    void requiresAKnownProduct() {
        assertThat(catalog.requireProduct(HEADPHONES_SKU)).isEqualTo(HEADPHONES);
    }

    @Test
    void signalsAnUnknownProductWithItsSku() {
        assertThatThrownBy(() -> catalog.requireProduct(new SkuCode("P-99999")))
                .isInstanceOfSatisfying(ProductNotFoundException.class,
                        e -> assertThat(e.sku()).isEqualTo(new SkuCode("P-99999")));
    }

    @Test
    void requiresAKnownStore() {
        assertThat(catalog.requireStore(LYON).city()).isEqualTo("Lyon");
    }

    @Test
    void signalsAnUnknownStoreWithItsId() {
        assertThatThrownBy(() -> catalog.requireStore(new StoreId("S99")))
                .isInstanceOfSatisfying(StoreNotFoundException.class,
                        e -> assertThat(e.storeId()).isEqualTo(new StoreId("S99")));
    }

    @Test
    void unknownSkuGivesNoProduct() {
        assertThat(catalog.product(new SkuCode("P-99999"))).isEmpty();
    }

    @Test
    void findsAProductFromAnUnnormalizedCode() {
        assertThat(catalog.product(new SkuCode(" p-00001 "))).contains(HEADPHONES);
    }

    @Test
    void findsTheStockLineOfAProductInAStore() {
        assertThat(catalog.stock(HEADPHONES_SKU, LYON)).hasValueSatisfying(line -> {
            assertThat(line.onHand()).isEqualTo(3);
            assertThat(line.reserved()).isEqualTo(3);
        });
    }

    @Test
    void fullyReservedStockIsNotAvailable() {
        assertThat(catalog.stock(HEADPHONES_SKU, LYON))
                .hasValueSatisfying(line -> assertThat(line.available()).isZero());
    }

    @Test
    void findsAStockLineFromUnnormalizedCodes() {
        assertThat(catalog.stock(new SkuCode("p-00001"), new StoreId("s01"))).isPresent();
    }

    @Test
    void findsAStoreById() {
        assertThat(catalog.store(new StoreId(" s01 "))).hasValueSatisfying(store ->
                assertThat(store.city()).isEqualTo("Lyon"));
    }

    @Test
    void listsStoreIdsInOrder() {
        var catalog = new Catalog(
                List.of(),
                List.of(new Store(new StoreId("S03"), "Magasin 3", "Lille"),
                        new Store(new StoreId("S01"), "Magasin 1", "Lyon"),
                        new Store(new StoreId("S02"), "Magasin 2", "Nantes")),
                List.of());

        assertThat(catalog.storeIds()).extracting(StoreId::value).containsExactly("S01", "S02", "S03");
    }

    @Test
    void unknownStoreIdGivesNoStore() {
        assertThat(catalog.store(new StoreId("S99"))).isEmpty();
    }

    @Test
    void unknownStoreGivesNoStockLine() {
        assertThat(catalog.stock(HEADPHONES_SKU, new StoreId("S99"))).isEmpty();
    }
}
