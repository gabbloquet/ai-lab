package io.github.gabbloquet.ailab.exp001.catalog.domain;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.util.List;

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
    void unknownStoreGivesNoStockLine() {
        assertThat(catalog.stock(HEADPHONES_SKU, new StoreId("S99"))).isEmpty();
    }
}
