package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;

import org.junit.jupiter.api.Test;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto.ProductResource;

class ProductResourceTest {

    private final Product headphones = new Product(
            new SkuCode("P-15695"), "Veldric Casque K8", "Veldric", "Audio", "Casque", new BigDecimal("100.00"));

    @Test
    void exposesTheSkuAsPlainText() {
        assertThat(ProductResource.from(headphones).sku()).isEqualTo("P-15695");
    }

    @Test
    void givesThePriceWithItsCurrency() {
        ProductResource resource = ProductResource.from(headphones);

        assertThat(resource.price()).isEqualByComparingTo(new BigDecimal("100.00"));
        assertThat(resource.currency()).isEqualTo("EUR");
    }

    @Test
    void keepsTheReadableDescriptionOfTheProduct() {
        ProductResource resource = ProductResource.from(headphones);

        assertThat(resource.name()).isEqualTo("Veldric Casque K8");
        assertThat(resource.brand()).isEqualTo("Veldric");
        assertThat(resource.department()).isEqualTo("Audio");
        assertThat(resource.type()).isEqualTo("Casque");
    }
}
