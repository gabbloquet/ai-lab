package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.util.List;

import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto.StoresWithStock;
import org.junit.jupiter.api.Test;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreStock;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto.StoresWithStock.StoreAvailability;

class StoresWithStockTest {

    private final Product headphones = new Product(
            new SkuCode("P-15695"), "Veldric Casque K8", "Veldric", "Audio", "Casque", new BigDecimal("100.00"));

    @Test
    void namesTheProductAndEachStoreWithItsAvailableUnits() {
        var lyon = new StoreStock(new Store(new StoreId("S01"), "Magasin Lyon", "Lyon"), 8);
        var bordeaux = new StoreStock(new Store(new StoreId("S04"), "Magasin Bordeaux", "Bordeaux"), 11);

        assertThat(StoresWithStock.of(headphones, List.of(lyon, bordeaux))).isEqualTo(new StoresWithStock(
                "P-15695", "Veldric Casque K8", List.of(
                        new StoreAvailability("S01", "Magasin Lyon", "Lyon", 8),
                        new StoreAvailability("S04", "Magasin Bordeaux", "Bordeaux", 11))));
    }

    @Test
    void keepsTheOrderGivenByTheCatalog() {
        var bordeaux = new StoreStock(new Store(new StoreId("S04"), "Magasin Bordeaux", "Bordeaux"), 11);
        var lyon = new StoreStock(new Store(new StoreId("S01"), "Magasin Lyon", "Lyon"), 8);

        assertThat(StoresWithStock.of(headphones, List.of(bordeaux, lyon)).stores())
                .extracting(StoreAvailability::storeId).containsExactly("S04", "S01");
    }

    @Test
    void hasNoStoreWhenTheProductIsOutOfStockEverywhere() {
        assertThat(StoresWithStock.of(headphones, List.of()).stores()).isEmpty();
    }
}
