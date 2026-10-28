package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.util.List;
import java.util.stream.IntStream;

import org.junit.jupiter.api.Test;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto.ProductResource;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto.SimilarProducts;

class SimilarProductsTest {

    private static List<Product> products(int count) {
        return IntStream.rangeClosed(1, count)
                .mapToObj(i -> new Product(new SkuCode("P-%05d".formatted(i)), "Produit " + i, "Marque", "Audio",
                        "Casque", new BigDecimal("10.00")))
                .toList();
    }

    @Test
    void givesEverySimilarProductWhenThereAreFew() {
        var similar = products(3);

        assertThat(SimilarProducts.of(similar))
                .isEqualTo(new SimilarProducts(3, similar.stream().map(ProductResource::from).toList()));
    }

    @Test
    void capsTheProductsAtTenButCountsEverySimilarOne() {
        var result = SimilarProducts.of(products(12));

        assertThat(result.total()).isEqualTo(12);
        assertThat(result.products()).extracting(ProductResource::sku)
                .containsExactly("P-00001", "P-00002", "P-00003", "P-00004", "P-00005",
                        "P-00006", "P-00007", "P-00008", "P-00009", "P-00010");
    }

    @Test
    void isEmptyWhenThereIsNoSimilarProduct() {
        var result = SimilarProducts.of(List.of());

        assertThat(result.total()).isZero();
        assertThat(result.products()).isEmpty();
    }
}
