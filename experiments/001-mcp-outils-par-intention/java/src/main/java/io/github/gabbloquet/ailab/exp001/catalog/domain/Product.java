package io.github.gabbloquet.ailab.exp001.catalog.domain;

import java.math.BigDecimal;

public record Product(SkuCode sku, String name, String brand, String department, String type, BigDecimal price) {
}
