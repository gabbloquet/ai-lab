package io.github.gabbloquet.ailab.exp001.catalog;

import java.util.List;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StockLine;

public final class Catalogs {

    private Catalogs() {
    }

    public static Catalog inMemory(List<Product> products, List<Store> stores, List<StockLine> stockLines) {
        return new Catalog(products, stores, stockLines);
    }
}
