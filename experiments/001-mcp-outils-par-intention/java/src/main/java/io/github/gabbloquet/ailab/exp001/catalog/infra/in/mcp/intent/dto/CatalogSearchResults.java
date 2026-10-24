package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto;

import java.util.List;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;

public record CatalogSearchResults(int total, List<ProductDetails> products) {

    private static final int MAX_PRODUCTS = 10;

    public static CatalogSearchResults of(List<Product> matches) {
        return new CatalogSearchResults(
                matches.size(),
                matches.stream().limit(MAX_PRODUCTS).map(ProductDetails::from).toList());
    }
}
