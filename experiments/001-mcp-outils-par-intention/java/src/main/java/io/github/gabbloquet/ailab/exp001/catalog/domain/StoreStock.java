package io.github.gabbloquet.ailab.exp001.catalog.domain;

/**
 * Magasin qui a un produit en stock, avec les unités disponibles à la vente.
 */
public record StoreStock(Store store, int available) {
}
