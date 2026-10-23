package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;

import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto.Availability;
import org.junit.jupiter.api.Test;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;

class AvailabilityTest {

    private final Product mouse = new Product(
            new SkuCode("P-38893"), "Junaro Souris T4", "Junaro", "Informatique", "Souris", new BigDecimal("24.90"));
    private final Store bordeaux = new Store(new StoreId("S04"), "Magasin Bordeaux", "Bordeaux");

    @Test
    void namesTheProductAndTheStore() {
        assertThat(Availability.of(mouse, bordeaux, 2))
                .isEqualTo(new Availability("P-38893", "Junaro Souris T4", "S04", "Magasin Bordeaux", 2, true));
    }

    @Test
    void isOutOfStockWhenNothingIsAvailable() {
        assertThat(Availability.of(mouse, bordeaux, 0).inStock()).isFalse();
    }
}
