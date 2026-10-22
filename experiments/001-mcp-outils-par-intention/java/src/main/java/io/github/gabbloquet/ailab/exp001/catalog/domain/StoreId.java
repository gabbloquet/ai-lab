package io.github.gabbloquet.ailab.exp001.catalog.domain;

import java.util.Locale;
import java.util.Objects;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

/**
 * Identifiant d'un magasin, normalisé à la création : espaces retirés, majuscules.
 */
public record StoreId(String value) {

    public StoreId {
        Objects.requireNonNull(value, "L'identifiant du magasin est obligatoire");
        value = value.strip().toUpperCase(Locale.ROOT);
        if (value.isEmpty()) {
            throw new IllegalArgumentException("L'identifiant du magasin ne peut pas être vide");
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
