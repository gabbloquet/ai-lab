package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.stream.IntStream;

import org.junit.jupiter.api.Test;

import io.github.gabbloquet.ailab.exp001.catalog.domain.StoreId;

class StoreNotFoundExceptionTest {

    private static final StoreId UNKNOWN = new StoreId("S99");

    /** S01, S02, … : autant d'identifiants que demandé, déjà triés comme les renvoie le catalogue. */
    private static List<StoreId> stores(int count) {
        return IntStream.rangeClosed(1, count).mapToObj(i -> new StoreId("S%02d".formatted(i))).toList();
    }

    @Test
    void listsEveryKnownStoreWhenThereAreFew() {
        assertThat(new StoreNotFoundException(UNKNOWN, stores(5)))
                .hasMessage("Store not found: S99. Known stores: S01, S02, S03, S04, S05.");
    }

    @Test
    void listsTenStoresWithoutMentioningOthersAtTheLimit() {
        assertThat(new StoreNotFoundException(UNKNOWN, stores(10)))
                .hasMessage("Store not found: S99. Known stores: S01, S02, S03, S04, S05, S06, S07, S08, S09, S10.");
    }

    @Test
    void capsTheListAndCountsTheOthersBeyondTen() {
        assertThat(new StoreNotFoundException(UNKNOWN, stores(12)))
                .hasMessage("Store not found: S99. Known stores: S01, S02, S03, S04, S05, S06, S07, S08, S09, S10"
                        + " and 2 more.");
    }

    @Test
    void isAnExpectedToolErrorSentAsIsToTheModel() {
        assertThat(new StoreNotFoundException(UNKNOWN, stores(1))).isInstanceOf(ToolException.class);
    }
}
