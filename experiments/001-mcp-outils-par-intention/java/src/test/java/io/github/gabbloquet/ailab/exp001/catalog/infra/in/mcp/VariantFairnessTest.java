package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp;

import static org.assertj.core.api.Assertions.assertThat;

import java.lang.reflect.Method;
import java.lang.reflect.Parameter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

import org.junit.jupiter.api.Test;
import org.springframework.ai.mcp.annotation.McpTool;
import org.springframework.ai.mcp.annotation.McpToolParam;

import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.intent.IntentTools;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.ProductTools;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.StockTools;
import io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp.rest.StoreTools;

// Protège le protocole de la 001 (guide de rédaction des descriptions), pas le code :
// une itération sur une seule variante ne doit pas casser l'équité sans que la build le signale.
class VariantFairnessTest {

    private static final List<Class<?>> INTENT = List.of(IntentTools.class);
    private static final List<Class<?>> REST = List.of(ProductTools.class, StockTools.class, StoreTools.class);

    private static Stream<Method> tools(List<Class<?>> variant) {
        return variant.stream()
                .flatMap(type -> Stream.of(type.getDeclaredMethods()))
                .filter(method -> method.isAnnotationPresent(McpTool.class));
    }

    private static int descriptionLength(List<Class<?>> variant) {
        return tools(variant).mapToInt(method -> method.getAnnotation(McpTool.class).description().length()).sum();
    }

    private static Map<String, String> parameterDescriptions(List<Class<?>> variant) {
        Map<String, String> descriptions = new HashMap<>();
        tools(variant).flatMap(method -> Stream.of(method.getParameters())).forEach((Parameter parameter) -> {
            String description = parameter.getAnnotation(McpToolParam.class).description();
            String previous = descriptions.putIfAbsent(parameter.getName(), description);
            assertThat(previous).as("description of " + parameter.getName()).isIn(null, description);
        });
        return descriptions;
    }

    @Test
    void describesASharedParameterWithTheSameWordsInBothVariants() {
        Map<String, String> intent = parameterDescriptions(INTENT);
        Map<String, String> rest = parameterDescriptions(REST);

        rest.keySet().stream().filter(intent::containsKey).forEach(name ->
                assertThat(rest.get(name)).as(name).isEqualTo(intent.get(name)));
        assertThat(rest.keySet()).containsExactlyInAnyOrderElementsOf(intent.keySet());
    }

    @Test
    void keepsTheToolDescriptionsOfBothVariantsWithinTwentyPercentInLength() {
        int intent = descriptionLength(INTENT);
        int rest = descriptionLength(REST);

        assertThat(Math.abs(rest - intent)).as("A: %d characters, B: %d characters", rest, intent)
                .isLessThanOrEqualTo(intent / 5);
    }
}
