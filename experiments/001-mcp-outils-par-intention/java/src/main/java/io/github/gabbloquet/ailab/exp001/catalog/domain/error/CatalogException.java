package io.github.gabbloquet.ailab.exp001.catalog.domain.error;

public abstract sealed class CatalogException extends RuntimeException
        permits InvalidIdentifierException, ProductNotFoundException, StoreNotFoundException, InvalidSearchQueryException {

    protected CatalogException(String message) {
        super(message);
    }
}
