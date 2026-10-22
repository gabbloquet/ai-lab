package io.github.gabbloquet.ailab.exp001.catalog.domain;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class SkuCodeTest {

    // Spec tool-selection v1, § 5 : identifiants comparés sans tenir compte de la casse ni des espaces autour.
    @Test
    void normalizesCaseAndSurroundingSpaces() {
        assertThat(new SkuCode(" p-00001 ").value()).isEqualTo("P-00001");
    }

    @Test
    void codesDifferingOnlyByCaseAreEqual() {
        assertThat(new SkuCode("p-00001")).isEqualTo(new SkuCode("P-00001"));
    }

    @Test
    void rejectsABlankCode() {
        assertThatThrownBy(() -> new SkuCode("   ")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void rejectsANullCode() {
        assertThatThrownBy(() -> new SkuCode(null)).isInstanceOf(NullPointerException.class);
    }
}
