package io.github.gabbloquet.ailab.exp001;

import java.util.Locale;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@ConfigurationPropertiesScan
@SpringBootApplication
public class McpServersApplication {

    // Le SDK MCP valide les arguments avec des messages dans la langue de la JVM : le modèle doit
    // les lire en anglais sur toute machine. Un bloc static couvre main et @SpringBootTest.
    static {
        Locale.setDefault(Locale.ENGLISH);
    }

    public static void main(String[] args) {
        SpringApplication.run(McpServersApplication.class, args);
    }
}
