package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import io.github.gabbloquet.ailab.exp001.catalog.domain.error.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.KnownValues;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.ToolErrorMessages;

@Component
@ConditionalOnProperty(name = "lab.variant", havingValue = "intent")
public class IntentErrorMessages implements ToolErrorMessages {

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
                    "Store not found: " + e.storeId() + ". Known stores: " + KnownValues.stores(catalog) + ".";
            case DepartmentNotFoundException e ->
                    "Category not found: " + e.department() + ". Known categories: "
                            + KnownValues.departments(catalog) + ".";
            case InvalidSearchQueryException _ ->
                    "Search query must not be blank. Provide at least one word of a product name, brand or type."
                            + " To narrow the results to a department, use category.";
            case InvalidIdentifierException _ -> exception.getMessage();
        };
    }
}
