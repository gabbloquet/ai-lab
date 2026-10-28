package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.util.List;
import java.util.stream.IntStream;

import org.junit.jupiter.api.Test;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto.ProductList;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.dto.ProductResource;

class ProductListTest {

    private static List<Product> products(int count) {
        return IntStream.rangeClosed(1, count)
                .mapToObj(i -> new Product(new SkuCode("P-%05d".formatted(i)), "Produit " + i, "Marque", "Audio",
                        "Casque", new BigDecimal("10.00")))
                .toList();
    }

    @Test
    void givesEveryProductWhenThereAreFew() {
        var products = products(3);

        assertThat(ProductList.of(products))
                .isEqualTo(new ProductList(3, products.stream().map(ProductResource::from).toList(), null));
    }

    @Test
    void capsTheProductsAtTenButCountsEveryOne() {
        var list = ProductList.of(products(12));

        assertThat(list.total()).isEqualTo(12);
        assertThat(list.products()).extracting(ProductResource::sku)
                .containsExactly("P-00001", "P-00002", "P-00003", "P-00004", "P-00005",
                        "P-00006", "P-00007", "P-00008", "P-00009", "P-00010");
    }

    @Test
    void explainsWhatTheQuerySearchesWhenNothingMatches() {
        assertThat(ProductList.of(List.of()).hint())
                .isEqualTo("No product matches every word of the query. The query searches product names, brands"
                        + " and types; use category to restrict to a department.");
    }

    @Test
    void givesNoHintWhenThereAreProducts() {
        assertThat(ProductList.of(products(3)).hint()).isNull();
    }
}
