package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto;

import java.math.BigDecimal;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;

public record ProductResource(
        String sku,
        String name,
        String brand,
        String department,
        String type,
        BigDecimal price,
        String currency) {

    private static final String EURO = "EUR";

    public static ProductResource from(Product product) {
        return new ProductResource(
                product.sku().value(),
                product.name(),
                product.brand(),
                product.department(),
                product.type(),
                product.price(),
                EURO);
    }
}
