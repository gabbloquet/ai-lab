package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp;

import java.util.List;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("lab.mcp")
public record McpSecurityProperties(List<String> allowedOrigins) {

    public McpSecurityProperties {
        allowedOrigins = allowedOrigins == null ? List.of() : List.copyOf(allowedOrigins);
    }
}
