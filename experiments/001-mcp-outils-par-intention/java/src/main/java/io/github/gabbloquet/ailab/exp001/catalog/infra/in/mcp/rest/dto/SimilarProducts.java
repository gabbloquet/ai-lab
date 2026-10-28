package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto;

import java.util.List;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;

public record SimilarProducts(int total, List<ProductResource> products) {

    private static final int MAX_PRODUCTS = 10;

    public static SimilarProducts of(List<Product> similar) {
        return new SimilarProducts(
                similar.size(),
                similar.stream().limit(MAX_PRODUCTS).map(ProductResource::from).toList());
    }
}
