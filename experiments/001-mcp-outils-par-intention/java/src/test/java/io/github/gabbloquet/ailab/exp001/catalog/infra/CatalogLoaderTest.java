package io.github.gabbloquet.ailab.exp001.catalog.infra;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.domain.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.domain.StoreId;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;


class CatalogLoaderTest {

    private final Catalog catalog = CatalogLoader.load(JsonMapper.builder().build(), "magasin/v1");

    @Test
    void loadsTheWholeDataset() {
        assertThat(catalog.products()).hasSize(50);
        assertThat(catalog.stores()).hasSize(5);
        assertThat(catalog.stockLines()).hasSize(250);
    }

    @Test
    void loadsPricesExactly() {
        // 101.99 n'a pas de représentation exacte en double : un chargeur qui passerait par un double échouerait ici.
        assertThat(catalog.product(new SkuCode("P-13905"))).hasValueSatisfying(product ->
                assertThat(product.price()).isEqualByComparingTo(new BigDecimal("101.99")));
    }

    @Test
    void loadsIdentifiersAsValueObjects() {
        // Scénario « fully_reserved » du générateur : stock physique présent mais entièrement réservé.
        assertThat(catalog.stock(new SkuCode("P-38893"), new StoreId("S04"))).hasValueSatisfying(line -> {
            assertThat(line.onHand()).isEqualTo(3);
            assertThat(line.available()).isZero();
        });
    }

}