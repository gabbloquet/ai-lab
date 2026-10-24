package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.util.List;
import java.util.stream.IntStream;

import org.junit.jupiter.api.Test;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto.CatalogSearchResults;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto.ProductDetails;

class CatalogSearchResultsTest {

    private static List<Product> products(int count) {
        return IntStream.rangeClosed(1, count)
                .mapToObj(i -> new Product(new SkuCode("P-%05d".formatted(i)), "Produit " + i, "Marque", "Audio",
                        "Casque", new BigDecimal("10.00")))
                .toList();
    }

    @Test
    void givesEveryMatchWhenThereAreFew() {
        var matches = products(3);

        assertThat(CatalogSearchResults.of(matches))
                .isEqualTo(new CatalogSearchResults(3, matches.stream().map(ProductDetails::from).toList()));
    }

    @Test
    void givesTenMatchesAtTheLimit() {
        var results = CatalogSearchResults.of(products(10));

        assertThat(results.total()).isEqualTo(10);
        assertThat(results.products()).hasSize(10);
    }

    @Test
    void capsTheProductsAtTenButCountsEveryMatch() {
        var results = CatalogSearchResults.of(products(12));

        assertThat(results.total()).isEqualTo(12);
        assertThat(results.products()).extracting(ProductDetails::sku)
                .containsExactly("P-00001", "P-00002", "P-00003", "P-00004", "P-00005",
                        "P-00006", "P-00007", "P-00008", "P-00009", "P-00010");
    }

    @Test
    void isEmptyWhenNothingMatches() {
        assertThat(CatalogSearchResults.of(List.of())).isEqualTo(new CatalogSearchResults(0, List.of()));
    }
}
