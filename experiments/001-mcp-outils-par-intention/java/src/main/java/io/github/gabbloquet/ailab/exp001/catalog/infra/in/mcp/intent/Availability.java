package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;

/**
 * Disponibilité d'un produit dans un magasin, renvoyée au modèle par {@code check_availability}.
 * {@code available} est déjà net des unités réservées : le modèle n'a pas de calcul à faire.
 */
public record Availability(
        String sku,
        String name,
        String storeId,
        String storeName,
        int available,
        boolean inStock) {

    public static Availability of(Product product, Store store, int available) {
        return new Availability(
                product.sku().value(),
                product.name(),
                store.storeId().value(),
                store.name(),
                available,
                available > 0);
    }
}
