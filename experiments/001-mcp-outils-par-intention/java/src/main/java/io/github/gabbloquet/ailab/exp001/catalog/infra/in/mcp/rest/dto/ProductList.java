package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonInclude;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;

public record ProductList(int total, List<ProductResource> products, @JsonInclude(JsonInclude.Include.NON_NULL) String hint) {

    private static final int MAX_PRODUCTS = 10;

    public static ProductList of(List<Product> products) {
        // Une liste vide ne vient que d'une requête : sans requête, le rayon a au moins un produit.
        String hint = products.isEmpty() ?
                "No product matches every word of the query. The query searches product names, brands"
                        + " and types; use category to restrict to a department."
                : null;
        return new ProductList(
                products.size(),
                products.stream().limit(MAX_PRODUCTS).map(ProductResource::from).toList(),
                hint
        );
    }
}
