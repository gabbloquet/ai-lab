package io.github.gabbloquet.ailab.exp001;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@ConfigurationPropertiesScan
@SpringBootApplication
public class McpServersApplication {

    public static void main(String[] args) {
        SpringApplication.run(McpServersApplication.class, args);
    }
}
