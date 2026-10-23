package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.dto;

import java.math.BigDecimal;
import java.util.List;

import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Alternative;

public record InStockAlternatives(List<AlternativeOffer> alternatives) {

    private static final String EURO = "EUR";

    public record AlternativeOffer(String sku, String name, String brand, BigDecimal price, String currency, int available) {
    }

    public static InStockAlternatives of(List<Alternative> alternatives) {
        return new InStockAlternatives(alternatives.stream()
                .map(alternative -> new AlternativeOffer(
                        alternative.product().sku().value(),
                        alternative.product().name(),
                        alternative.product().brand(),
                        alternative.product().price(),
                        EURO,
                        alternative.available()))
                .toList());
    }
}
