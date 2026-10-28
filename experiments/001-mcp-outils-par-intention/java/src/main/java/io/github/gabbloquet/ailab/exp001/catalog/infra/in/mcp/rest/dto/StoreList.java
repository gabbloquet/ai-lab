package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto;

import static java.util.Comparator.comparing;

import java.util.List;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;

public record StoreList(List<StoreEntry> stores) {

    public record StoreEntry(String storeId, String name, String city) { }

    public static StoreList of(List<Store> stores) {
        return new StoreList(stores.stream()
                .sorted(comparing(store -> store.storeId().value()))
                .map(store -> new StoreEntry(store.storeId().value(), store.name(), store.city()))
                .toList());
    }
}
