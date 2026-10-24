package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import static java.util.Comparator.comparing;

import java.util.List;
import java.util.stream.Collectors;

import io.github.gabbloquet.ailab.exp001.catalog.domain.error.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;
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
            case InvalidSearchQueryException _ ->
                    "Search query must not be blank. Provide at least one word of a product name, brand or type."
                            + " To narrow the results to a department, use category.";
            case InvalidIdentifierException _ -> exception.getMessage();
        };
    }

    private String knownStores() {
        List<Store> stores = catalog.stores().stream().sorted(comparing(store -> store.storeId().value())).toList();
        String listed = stores.stream()
                .limit(MAX_LISTED_STORES)
                .map(store -> store.storeId().value() + " (" + store.city() + ")")
                .collect(Collectors.joining(", "));
        int others = stores.size() - MAX_LISTED_STORES;
        return others > 0 ? listed + " and " + others + " more" : listed;
    }

    private String knownDepartments() {
        List<String> departments = catalog.departments();
        String listed = departments.stream().limit(MAX_LISTED_DEPARTMENTS).collect(Collectors.joining(", "));
        int others = departments.size() - MAX_LISTED_DEPARTMENTS;
        return others > 0 ? listed + " and " + others + " more" : listed;
    }
}
