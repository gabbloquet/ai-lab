package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.stream.IntStream;

import org.junit.jupiter.api.Test;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.InvalidIdentifierException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.InvalidSearchQueryException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.ProductNotFoundException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.StoreNotFoundException;

class IntentErrorMessagesTest {

    private static final StoreNotFoundException UNKNOWN_STORE = new StoreNotFoundException(new StoreId("S99"));

    private static IntentErrorMessages withStores(int count) {
        List<Store> stores = IntStream.rangeClosed(1, count)
                .mapToObj(i -> new Store(new StoreId("S%02d".formatted(i)), "Magasin " + i, "Ville " + i))
                .toList();
        return new IntentErrorMessages(new Catalog(List.of(), stores, List.of()));
    }

    @Test
    void pointsToTheSearchToolForAnUnknownProduct() {
        assertThat(withStores(5).messageFor(new ProductNotFoundException(new SkuCode("P-00000"))))
                .isEqualTo("Product not found: P-00000. Use search_catalog to find the SKU of a product.");
    }

    @Test
    void listsEveryKnownStoreWhenThereAreFew() {
        assertThat(withStores(5).messageFor(UNKNOWN_STORE))
                .isEqualTo("Store not found: S99. Known stores: S01, S02, S03, S04, S05.");
    }

    @Test
    void listsTenStoresWithoutMentioningOthersAtTheLimit() {
        assertThat(withStores(10).messageFor(UNKNOWN_STORE))
                .isEqualTo("Store not found: S99. Known stores: S01, S02, S03, S04, S05, S06, S07, S08, S09, S10.");
    }

    @Test
    void capsTheListAndCountsTheOthersBeyondTen() {
        assertThat(withStores(12).messageFor(UNKNOWN_STORE))
                .isEqualTo("Store not found: S99. Known stores: S01, S02, S03, S04, S05, S06, S07, S08, S09, S10"
                        + " and 2 more.");
    }

    @Test
    void passesAnInvalidSearchQueryMessageAsIs() {
        assertThat(withStores(5).messageFor(new InvalidSearchQueryException("Search query must not be blank")))
                .isEqualTo("Search query must not be blank");
    }

    @Test
    void passesAnInvalidIdentifierMessageAsIs() {
        assertThat(withStores(5).messageFor(new InvalidIdentifierException("SKU must not be blank")))
                .isEqualTo("SKU must not be blank");
    }
}
