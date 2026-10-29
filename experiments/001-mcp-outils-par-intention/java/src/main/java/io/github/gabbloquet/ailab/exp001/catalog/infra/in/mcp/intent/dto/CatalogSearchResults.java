package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonInclude;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;

public record CatalogSearchResults(int total, List<ProductDetails> products, @JsonInclude(JsonInclude.Include.NON_NULL) String hint) {

    private static final int MAX_PRODUCTS = 10;

    public static CatalogSearchResults of(List<Product> matches) {
        String hint = matches.isEmpty() ?
                "No product matches every word of the query. The query searches product names, brands"
                        + " and types; use category to restrict to a department."
                : null;
        return new CatalogSearchResults(
                matches.size(),
                matches.stream().limit(MAX_PRODUCTS).map(ProductDetails::from).toList(),
                hint
        );
    }
}
