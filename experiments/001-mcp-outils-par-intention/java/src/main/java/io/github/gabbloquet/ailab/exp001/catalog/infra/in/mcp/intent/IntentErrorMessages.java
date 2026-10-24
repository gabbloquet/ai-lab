package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import java.util.List;
import java.util.stream.Collectors;

import io.github.gabbloquet.ailab.exp001.catalog.domain.error.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.ToolErrorMessages;

@Component
@ConditionalOnProperty(name = "lab.variant", havingValue = "intent")
public class IntentErrorMessages implements ToolErrorMessages {

    private static final int MAX_LISTED_STORES = 10;
    private static final int MAX_LISTED_DEPARTMENTS = 5;

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
            case DepartmentNotFoundException e ->
                    "Category not found: " + e.department() + ". Known categories: " + knownDepartments() + ".";
            case InvalidIdentifierException _, InvalidSearchQueryException _ -> exception.getMessage();
        };
    }

    private String knownStores() {
        List<StoreId> storeIds = catalog.storeIds();
        String listed = storeIds.stream().limit(MAX_LISTED_STORES).map(StoreId::value).collect(Collectors.joining(", "));
        int others = storeIds.size() - MAX_LISTED_STORES;
        return others > 0 ? listed + " and " + others + " more" : listed;
    }

    private String knownDepartments() {
        List<String> departments = catalog.departments();
        String listed = departments.stream().limit(MAX_LISTED_DEPARTMENTS).collect(Collectors.joining(", "));
        int others = departments.size() - MAX_LISTED_DEPARTMENTS;
        return others > 0 ? listed + " and " + others + " more" : listed;
    }
}
