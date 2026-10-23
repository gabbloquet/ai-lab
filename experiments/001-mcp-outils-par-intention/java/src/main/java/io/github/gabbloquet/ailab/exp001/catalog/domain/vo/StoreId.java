package io.github.gabbloquet.ailab.exp001.catalog.domain.vo;

import java.util.Locale;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.InvalidIdentifierException;

public record StoreId(String value) {

    public StoreId {
        if (value == null) {
            throw new InvalidIdentifierException("Store id is required");
        }
        value = value.strip().toUpperCase(Locale.ROOT);
        if (value.isEmpty()) {
            throw new InvalidIdentifierException("Store id must not be blank");
        }
    }

    @JsonCreator(mode = JsonCreator.Mode.DELEGATING)
    public static StoreId of(String value) {
        return new StoreId(value);
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
