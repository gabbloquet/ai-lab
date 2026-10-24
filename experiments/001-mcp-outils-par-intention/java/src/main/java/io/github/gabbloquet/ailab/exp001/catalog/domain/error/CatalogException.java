package io.github.gabbloquet.ailab.exp001.catalog.domain.error;

public abstract sealed class CatalogException extends RuntimeException
        permits InvalidIdentifierException, ProductNotFoundException, StoreNotFoundException, InvalidSearchQueryException, DepartmentNotFoundException {

    protected CatalogException(String message) {
        super(message);
    }
}
