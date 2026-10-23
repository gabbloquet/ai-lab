package io.github.gabbloquet.ailab.exp001.catalog.domain.vo;

import java.util.Locale;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.InvalidIdentifierException;

public record SkuCode(String value) {

    public SkuCode {
        if (value == null) {
            throw new InvalidIdentifierException("SKU is required");
        }
        value = value.strip().toUpperCase(Locale.ROOT);
        if (value.isEmpty()) {
            throw new InvalidIdentifierException("SKU must not be blank");
        }
    }

    @JsonCreator(mode = JsonCreator.Mode.DELEGATING)
    public static SkuCode of(String value) {
        return new SkuCode(value);
    }

    @JsonValue
    @Override
    public String value() {
        return value;
    }

    @Override
    public String toString() {
        return value;
    }
}
