package io.github.gabbloquet.ailab.exp001;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.bind.BindException;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.boot.context.properties.source.MapConfigurationPropertySource;

import io.github.gabbloquet.ailab.exp001.LabProperties.Variant;

class LabPropertiesTest {

    private static LabProperties bind(Map<String, String> properties) {
        return new Binder(new MapConfigurationPropertySource(properties)).bindOrCreate("lab", LabProperties.class);
    }

    @Test
    void bindsTheVariantGivenAtLaunch() {
        assertThat(bind(Map.of("lab.variant", "intent")).variant()).isEqualTo(Variant.INTENT);
        assertThat(bind(Map.of("lab.variant", "rest")).variant()).isEqualTo(Variant.REST);
    }

    @Test
    void refusesToStartWithoutAVariant() {
        assertThatThrownBy(() -> bind(Map.of()))
                .isInstanceOf(BindException.class)
                .rootCause()
                .hasMessageContaining("--lab.variant=intent");
    }

    @Test
    void refusesAnUnknownVariant() {
        assertThatThrownBy(() -> bind(Map.of("lab.variant", "graphql")))
                .isInstanceOf(BindException.class);
    }
}
