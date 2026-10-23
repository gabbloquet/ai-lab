package io.github.gabbloquet.ailab.exp001.catalog.domain;

/**
 * Produit proposé à la place d'un autre, avec les unités disponibles à la vente dans le magasin demandé.
 */
public record Alternative(Product product, int available) {
}
