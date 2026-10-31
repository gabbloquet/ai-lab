package io.github.gabbloquet.ailab.exp001.catalog.infra.out.data;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

class CatalogLoaderTest {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final String DATA = "magasin/v1";

    private final Catalog catalog = CatalogLoader.load(JSON, DATA);

    @Test
    void loadsTheWholeDataset() {
        assertThat(CatalogLoader.readProducts(JSON, DATA)).hasSize(50);
        assertThat(CatalogLoader.readStores(JSON, DATA)).hasSize(5);
        assertThat(CatalogLoader.readStockLines(JSON, DATA)).hasSize(250);
    }

    @Test
    void loadsPricesExactly() {
        assertThat(catalog.product(new SkuCode("P-13905"))).hasValueSatisfying(product ->
                assertThat(product.price()).isEqualByComparingTo(new BigDecimal("101.99")));
    }

    @Test
    void loadsIdentifiersAsValueObjects() {
        assertThat(catalog.stock(new SkuCode("P-38893"), new StoreId("S04"))).hasValueSatisfying(line -> {
            assertThat(line.onHand()).isEqualTo(3);
            assertThat(line.available()).isZero();
        });
    }

}