package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp;

import io.github.gabbloquet.ailab.exp001.catalog.domain.error.CatalogException;

@FunctionalInterface
public interface ToolErrorMessages {

    String messageFor(CatalogException exception);
}
