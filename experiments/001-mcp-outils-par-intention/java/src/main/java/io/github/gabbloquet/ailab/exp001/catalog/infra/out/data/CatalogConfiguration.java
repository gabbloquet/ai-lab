package io.github.gabbloquet.ailab.exp001.catalog.infra.out.data;

import io.github.gabbloquet.ailab.exp001.catalog.domain.Catalog;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import tools.jackson.databind.json.JsonMapper;


@Configuration
class CatalogConfiguration {

    @Bean
    Catalog catalog(JsonMapper jsonMapper) {
        return CatalogLoader.load(jsonMapper, "magasin/v1");
    }

}
