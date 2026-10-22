package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import java.math.BigDecimal;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Product;

/**
 * Fiche produit renvoyée au modèle par {@code get_product_details}.
 * C'est le contrat de l'outil : il ne suit pas le domaine automatiquement, chaque champ est un choix.
 */
public record ProductDetails(
        String sku,
        String name,
        String brand,
        String department,
        String type,
        BigDecimal price,
        String currency) {

    private static final String EURO = "EUR";

    public static ProductDetails from(Product product) {
        return new ProductDetails(
                product.sku().value(),
                product.name(),
                product.brand(),
                product.department(),
                product.type(),
                product.price(),
                EURO);
    }
}
