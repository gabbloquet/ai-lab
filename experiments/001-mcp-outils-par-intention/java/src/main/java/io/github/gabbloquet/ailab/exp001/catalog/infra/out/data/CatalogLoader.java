package io.github.gabbloquet.ailab.exp001.catalog.infra.out.data;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.List;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.Product;
import io.github.gabbloquet.ailab.exp001.catalog.domain.vo.StockLine;
import io.github.gabbloquet.ailab.exp001.catalog.domain.Store;
import io.github.gabbloquet.ailab.exp001.catalog.infra.out.memory.InMemoryProductRepository;
import io.github.gabbloquet.ailab.exp001.catalog.infra.out.memory.InMemoryStockRepository;
import io.github.gabbloquet.ailab.exp001.catalog.infra.out.memory.InMemoryStoreRepository;
import tools.jackson.databind.json.JsonMapper;

public final class CatalogLoader {

    private CatalogLoader() {
    }

    public static Catalog load(JsonMapper jsonMapper, String basePath) {
        return new Catalog(
                new InMemoryProductRepository(readProducts(jsonMapper, basePath)),
                new InMemoryStoreRepository(readStores(jsonMapper, basePath)),
                new InMemoryStockRepository(readStockLines(jsonMapper, basePath)));
    }

    public static List<Product> readProducts(JsonMapper jsonMapper, String basePath) {
        return readJsonLines(jsonMapper, basePath + "/products.jsonl", Product.class);
    }

    public static List<Store> readStores(JsonMapper jsonMapper, String basePath) {
        return readJsonLines(jsonMapper, basePath + "/stores.jsonl", Store.class);
    }

    public static List<StockLine> readStockLines(JsonMapper jsonMapper, String basePath) {
        return readJsonLines(jsonMapper, basePath + "/stock.jsonl", StockLine.class);
    }

    private static <T> List<T> readJsonLines(JsonMapper jsonMapper, String path, Class<T> type) {
        InputStream in = CatalogLoader.class.getClassLoader().getResourceAsStream(path);
        if (in == null) {
            throw new IllegalStateException("Ressource introuvable dans le classpath : " + path);
        }
        try (var reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            return reader.lines()
                    .filter(line -> !line.isBlank())
                    .map(line -> jsonMapper.readValue(line, type))
                    .toList();
        } catch (IOException e) {
            throw new UncheckedIOException("Lecture impossible : " + path, e);
        }
    }
}
