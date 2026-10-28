package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest;

import io.github.gabbloquet.ailab.exp001.catalog.domain.error.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.KnownValues;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.ToolErrorMessages;

@Component
@ConditionalOnProperty(name = "lab.variant", havingValue = "rest")
public class RestErrorMessages implements ToolErrorMessages {

    private final Catalog catalog;

    public RestErrorMessages(Catalog catalog) {
        this.catalog = catalog;
    }

    @Override
    public String messageFor(CatalogException exception) {
        return switch (exception) {
            case ProductNotFoundException e ->
                    "Product not found: " + e.sku() + ". Use list_products to find the SKU of a product.";
            case StoreNotFoundException e ->
                    "Store not found: " + e.storeId() + ". Known stores: " + KnownValues.stores(catalog) + ".";
            case DepartmentNotFoundException e ->
                    "Category not found: " + e.department() + ". Known categories: "
                            + KnownValues.departments(catalog) + ".";
            // Inatteignable en A : sans requête, list_products parcourt le rayon au lieu de chercher.
            case InvalidSearchQueryException _ -> exception.getMessage();
            case InvalidIdentifierException _ -> exception.getMessage();
        };
    }
}
