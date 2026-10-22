package io.github.gabbloquet.ailab.exp001.catalog.domain;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class StoreIdTest {

    @Test
    void normalizesCaseAndSurroundingSpaces() {
        assertThat(new StoreId(" s01 ").value()).isEqualTo("S01");
    }

    @Test
    void idsDifferingOnlyByCaseAreEqual() {
        assertThat(new StoreId("s01")).isEqualTo(new StoreId("S01"));
    }

    @Test
    void rejectsABlankId() {
        assertThatThrownBy(() -> new StoreId("   ")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void rejectsANullId() {
        assertThatThrownBy(() -> new StoreId(null)).isInstanceOf(NullPointerException.class);
    }
}
