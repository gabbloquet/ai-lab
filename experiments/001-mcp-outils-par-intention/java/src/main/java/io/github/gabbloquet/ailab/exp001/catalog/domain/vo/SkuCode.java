package io.github.gabbloquet.ailab.exp001.catalog.domain.vo;

import java.util.Locale;
import java.util.regex.Pattern;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import io.github.gabbloquet.ailab.exp001.catalog.domain.error.InvalidIdentifierException;

public record SkuCode(String value) {

    private static final Pattern FORMAT = Pattern.compile("P-\\d{5}");

    public SkuCode {
        if (value == null) {
            throw new InvalidIdentifierException("SKU is required");
        }
        String typed = value.strip();
        if (typed.isEmpty()) {
            throw new InvalidIdentifierException("SKU must not be blank");
        }
        value = typed.toUpperCase(Locale.ROOT);
        if (!FORMAT.matcher(value).matches()) {
            throw new InvalidIdentifierException("Invalid SKU: " + typed + ". A SKU is P- followed by 5 digits.");
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
