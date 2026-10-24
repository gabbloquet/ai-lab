package io.github.gabbloquet.ailab.exp001.catalog.domain;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.gabbloquet.ailab.exp001.catalog.domain.error.InvalidIdentifierException;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import org.junit.jupiter.api.Test;

class SkuCodeTest {

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
        assertThatThrownBy(() -> new SkuCode("   ")).isInstanceOf(InvalidIdentifierException.class);
    }

    @Test
    void rejectsANullCode() {
        assertThatThrownBy(() -> new SkuCode(null)).isInstanceOf(InvalidIdentifierException.class);
    }

    @Test
    void rejectsACodeWithoutThePrefix() {
        assertThatThrownBy(() -> new SkuCode("80284"))
                .isInstanceOf(InvalidIdentifierException.class)
                .hasMessage("Invalid SKU: 80284. A SKU is P- followed by 5 digits.");
    }

    @Test
    void rejectsACodeWithoutTheDash() {
        assertThatThrownBy(() -> new SkuCode("P80284"))
                .isInstanceOf(InvalidIdentifierException.class)
                .hasMessage("Invalid SKU: P80284. A SKU is P- followed by 5 digits.");
    }

    @Test
    void rejectsACodeWithTheWrongNumberOfDigits() {
        assertThatThrownBy(() -> new SkuCode("P-1234"))
                .isInstanceOf(InvalidIdentifierException.class)
                .hasMessage("Invalid SKU: P-1234. A SKU is P- followed by 5 digits.");
    }

    @Test
    void showsTheCodeAsTypedWithoutSurroundingSpacesInTheMessage() {
        assertThatThrownBy(() -> new SkuCode(" p80284 "))
                .isInstanceOf(InvalidIdentifierException.class)
                .hasMessage("Invalid SKU: p80284. A SKU is P- followed by 5 digits.");
    }
}
