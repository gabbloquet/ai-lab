package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp;

import io.github.gabbloquet.ailab.exp001.catalog.domain.StoreId;

import java.util.List;
import java.util.stream.Collectors;

public class StoreNotFoundException extends ToolException {

    private static final int MAX_LISTED = 10;

    public StoreNotFoundException(StoreId storeId, List<StoreId> knownStores) {
        super("Store not found: " + storeId + ". Known stores: " + describe(knownStores) + ".");
    }

    private static String describe(List<StoreId> knownStores) {
        String listed = knownStores.stream().limit(MAX_LISTED).map(StoreId::value).collect(Collectors.joining(", "));
        int others = knownStores.size() - MAX_LISTED;
        return others > 0 ? listed + " and " + others + " more" : listed;
    }
}
