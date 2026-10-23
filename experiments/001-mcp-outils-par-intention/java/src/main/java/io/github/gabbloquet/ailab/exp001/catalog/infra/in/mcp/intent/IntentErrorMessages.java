package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import java.util.List;
import java.util.stream.Collectors;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.CatalogException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.InvalidIdentifierException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.ProductNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.StoreNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.ToolErrorMessages;

@Component
@ConditionalOnProperty(name = "lab.variant", havingValue = "intent")
public class IntentErrorMessages implements ToolErrorMessages {

    private static final int MAX_LISTED_STORES = 10;

    private final Catalog catalog;

    public IntentErrorMessages(Catalog catalog) {
        this.catalog = catalog;
    }

    @Override
    public String messageFor(CatalogException exception) {
        return switch (exception) {
            case ProductNotFoundException e ->
                    "Product not found: " + e.sku() + ". Use search_catalog to find the SKU of a product.";
            case StoreNotFoundException e ->
                    "Store not found: " + e.storeId() + ". Known stores: " + knownStores() + ".";
            case InvalidIdentifierException e -> e.getMessage();
        };
    }

    private String knownStores() {
        List<StoreId> storeIds = catalog.storeIds();
        String listed = storeIds.stream().limit(MAX_LISTED_STORES).map(StoreId::value).collect(Collectors.joining(", "));
        int others = storeIds.size() - MAX_LISTED_STORES;
        return others > 0 ? listed + " and " + others + " more" : listed;
    }
}
