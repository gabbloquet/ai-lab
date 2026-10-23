package io.github.gabbloquet.ailab.exp001;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("lab")
public record LabProperties(Variant variant) {

    public enum Variant { INTENT, REST }

    public LabProperties {
        if (variant == null) {
            throw new IllegalArgumentException(
                    "Aucune variante d'outils : lancer le serveur avec --lab.variant=intent ou --lab.variant=rest");
        }
    }
}
