package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.util.List;

import org.junit.jupiter.api.Test;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Alternative;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto.InStockAlternatives;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto.InStockAlternatives.AlternativeOffer;

class InStockAlternativesTest {

    private static Alternative alternative(String sku, String name, String brand, String price, int available) {
        return new Alternative(
                new Product(new SkuCode(sku), name, brand, "Audio", "Casque", new BigDecimal(price)), available);
    }

    @Test
    void offersEachAlternativeWithItsPriceInEurosAndItsAvailableUnits() {
        var cheaper = alternative("P-26361", "Zorvane Casque P2", "Zorvane", "80.00", 4);

        assertThat(InStockAlternatives.of(List.of(cheaper)).alternatives()).containsExactly(
                new AlternativeOffer("P-26361", "Zorvane Casque P2", "Zorvane", new BigDecimal("80.00"), "EUR", 4));
    }

    @Test
    void keepsTheOrderGivenByTheCatalog() {
        var closest = alternative("P-44671", "Ostrane Casque N4", "Ostrane", "105.00", 1);
        var further = alternative("P-26361", "Zorvane Casque P2", "Zorvane", "80.00", 4);

        assertThat(InStockAlternatives.of(List.of(closest, further)).alternatives())
                .extracting(AlternativeOffer::sku).containsExactly("P-44671", "P-26361");
    }

    @Test
    void hasNoOfferWhenThereIsNoAlternative() {
        assertThat(InStockAlternatives.of(List.of()).alternatives()).isEmpty();
    }
}
