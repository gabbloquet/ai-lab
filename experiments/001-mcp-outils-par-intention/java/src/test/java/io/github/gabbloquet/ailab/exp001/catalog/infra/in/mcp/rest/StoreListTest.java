package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;

import org.junit.jupiter.api.Test;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto.StoreList;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto.StoreList.StoreEntry;

class StoreListTest {

    @Test
    void listsEveryStoreWithItsNameAndCityInIdOrder() {
        var stores = List.of(
                new Store(new StoreId("S03"), "Magasin Lille", "Lille"),
                new Store(new StoreId("S01"), "Magasin Lyon", "Lyon"));

        assertThat(StoreList.of(stores).stores()).containsExactly(
                new StoreEntry("S01", "Magasin Lyon", "Lyon"),
                new StoreEntry("S03", "Magasin Lille", "Lille"));
    }
}
