package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp;

import static java.util.Comparator.comparing;

import java.util.List;
import java.util.stream.Collectors;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;

// Partagé par les deux variantes : une même erreur doit lister les mêmes valeurs en A et en B.
public final class KnownValues {

    private static final int MAX_LISTED_STORES = 10;
    private static final int MAX_LISTED_DEPARTMENTS = 5;

    private KnownValues() {
    }

    public static String stores(Catalog catalog) {
        List<Store> stores = catalog.stores().stream().sorted(comparing(store -> store.storeId().value())).toList();
        String listed = stores.stream()
                .limit(MAX_LISTED_STORES)
                .map(store -> store.storeId().value() + " (" + store.city() + ")")
                .collect(Collectors.joining(", "));
        int others = stores.size() - MAX_LISTED_STORES;
        return others > 0 ? listed + " and " + others + " more" : listed;
    }

    public static String departments(Catalog catalog) {
        List<String> departments = catalog.departments();
        String listed = departments.stream().limit(MAX_LISTED_DEPARTMENTS).collect(Collectors.joining(", "));
        int others = departments.size() - MAX_LISTED_DEPARTMENTS;
        return others > 0 ? listed + " and " + others + " more" : listed;
    }
}
