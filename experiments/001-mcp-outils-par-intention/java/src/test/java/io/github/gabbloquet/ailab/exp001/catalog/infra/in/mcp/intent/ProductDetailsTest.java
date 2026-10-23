package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;

import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto.ProductDetails;
import org.junit.jupiter.api.Test;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;

class ProductDetailsTest {

    private final Product headphones = new Product(
            new SkuCode("P-15695"), "Veldric Casque K8", "Veldric", "Audio", "Casque", new BigDecimal("100.00"));

    @Test
    void exposesTheSkuAsPlainText() {
        assertThat(ProductDetails.from(headphones).sku()).isEqualTo("P-15695");
    }

    @Test
    void givesThePriceWithItsCurrency() {
        ProductDetails details = ProductDetails.from(headphones);

        assertThat(details.price()).isEqualByComparingTo(new BigDecimal("100.00"));
        assertThat(details.currency()).isEqualTo("EUR");
    }

    @Test
    void keepsTheReadableDescriptionOfTheProduct() {
        ProductDetails details = ProductDetails.from(headphones);

        assertThat(details.name()).isEqualTo("Veldric Casque K8");
        assertThat(details.brand()).isEqualTo("Veldric");
        assertThat(details.department()).isEqualTo("Audio");
        assertThat(details.type()).isEqualTo("Casque");
    }
}
