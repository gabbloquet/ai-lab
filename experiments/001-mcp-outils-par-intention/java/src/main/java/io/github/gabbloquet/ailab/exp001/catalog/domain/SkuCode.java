package io.github.gabbloquet.ailab.exp001.catalog.domain;

import java.util.Locale;
import java.util.Objects;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

/**
 * Identifiant d'un produit, normalisé à la création : espaces retirés, majuscules.
 * Deux SKU qui ne diffèrent que par la casse ou les espaces sont donc égaux.
 */
public record SkuCode(String value) {

    public SkuCode {
        Objects.requireNonNull(value, "Le SKU est obligatoire");
        value = value.strip().toUpperCase(Locale.ROOT);
        if (value.isEmpty()) {
            throw new IllegalArgumentException("Le SKU ne peut pas être vide");
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
