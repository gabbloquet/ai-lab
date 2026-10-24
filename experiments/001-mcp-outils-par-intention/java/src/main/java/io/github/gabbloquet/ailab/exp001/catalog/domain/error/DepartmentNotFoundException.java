package io.github.gabbloquet.ailab.exp001.catalog.domain.error;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;

public final class DepartmentNotFoundException extends CatalogException {

    private final String department;

    public DepartmentNotFoundException(String department) {
        super("Unknown department: " + department);
        this.department = department;
    }

    public String department() {
        return department;
    }

}
