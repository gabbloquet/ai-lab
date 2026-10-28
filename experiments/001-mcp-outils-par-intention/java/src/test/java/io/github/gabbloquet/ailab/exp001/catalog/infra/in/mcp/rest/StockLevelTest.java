package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;

import org.junit.jupiter.api.Test;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto.StockLevel;

class StockLevelTest {

    private final Product headphones = new Product(
            new SkuCode("P-15695"), "Veldric Casque K8", "Veldric", "Audio", "Casque", new BigDecimal("100.00"));
    private final Store lyon = new Store(new StoreId("S01"), "Magasin Lyon", "Lyon");

    @Test
    void identifiesTheProductAndTheStoreByTheirIds() {
        assertThat(StockLevel.of(headphones, lyon, 3)).isEqualTo(new StockLevel("P-15695", "S01", 3));
    }
}
