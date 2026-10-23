package io.github.gabbloquet.ailab.exp001.catalog;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Objects;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.SkuCode;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StockLine;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StoreId;
import io.github.gabbloquet.ailab.exp001.catalog.infra.out.data.CatalogLoader;
import tools.jackson.databind.json.JsonMapper;

class OracleConformanceTest {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Catalog CATALOG = CatalogLoader.load(JSON, "magasin/v1");

    record AvailabilityExpectation(String sku, String storeId, int available, List<String> alternatives) {
    }

    record StoresWithStockExpectation(String sku, List<String> storeIds) {
    }

    static List<AvailabilityExpectation> availability() {
        return read("magasin/oracle/v1/availability.jsonl", AvailabilityExpectation.class);
    }

    static List<StoresWithStockExpectation> storesWithStock() {
        return read("magasin/oracle/v1/stores_with_stock.jsonl", StoresWithStockExpectation.class);
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("availability")
    void matchesTheOracleOnAvailabilityAndAlternatives(AvailabilityExpectation expected) {
        var sku = new SkuCode(expected.sku());
        var storeId = new StoreId(expected.storeId());

        assertThat(CATALOG.stock(sku, storeId).map(StockLine::available).orElse(0)).isEqualTo(expected.available());
        assertThat(CATALOG.alternatives(sku, storeId))
                .extracting(alternative -> alternative.product().sku().value())
                .containsExactlyElementsOf(expected.alternatives());
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("storesWithStock")
    void matchesTheOracleOnStoresWithStock(StoresWithStockExpectation expected) {
        assertThat(CATALOG.storesWithStock(new SkuCode(expected.sku())))
                .extracting(stock -> stock.store().storeId().value())
                .containsExactlyElementsOf(expected.storeIds());
    }

    private static <T> List<T> read(String path, Class<T> type) {
        var in = Objects.requireNonNull(
                OracleConformanceTest.class.getClassLoader().getResourceAsStream(path), "Attentes introuvables : " + path);
        try (var reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            return reader.lines().filter(line -> !line.isBlank()).map(line -> JSON.readValue(line, type)).toList();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
