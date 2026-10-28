package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.util.List;

import org.junit.jupiter.api.Test;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.DepartmentNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.InvalidIdentifierException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.ProductNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.StoreNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;

class RestErrorMessagesTest {

    private final RestErrorMessages messages = new RestErrorMessages(new Catalog(
            List.of(product("P-00001", "Maison"), product("P-00002", "Audio")),
            List.of(new Store(new StoreId("S02"), "Magasin 2", "Nantes"),
                    new Store(new StoreId("S01"), "Magasin 1", "Lyon")),
            List.of()));

    private static Product product(String sku, String department) {
        return new Product(new SkuCode(sku), "Produit " + sku, "Marque", department, "Type", new BigDecimal("10.00"));
    }

    @Test
    void pointsToTheListingToolForAnUnknownProduct() {
        assertThat(messages.messageFor(new ProductNotFoundException(new SkuCode("P-00000"))))
                .isEqualTo("Product not found: P-00000. Use list_products to find the SKU of a product.");
    }

    @Test
    void listsTheKnownStoresWithTheirCityLikeTheIntentVariant() {
        assertThat(messages.messageFor(new StoreNotFoundException(new StoreId("S99"))))
                .isEqualTo("Store not found: S99. Known stores: S01 (Lyon), S02 (Nantes).");
    }

    @Test
    void namesItACategoryAndListsTheKnownOnes() {
        assertThat(messages.messageFor(new DepartmentNotFoundException("Hifi")))
                .isEqualTo("Category not found: Hifi. Known categories: Audio, Maison.");
    }

    @Test
    void passesAnInvalidIdentifierMessageAsIs() {
        assertThat(messages.messageFor(new InvalidIdentifierException("SKU must not be blank")))
                .isEqualTo("SKU must not be blank");
    }
}
