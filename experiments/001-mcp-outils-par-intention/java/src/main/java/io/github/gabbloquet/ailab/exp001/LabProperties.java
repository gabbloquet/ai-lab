package io.github.gabbloquet.ailab.exp001;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Variante d'outils exposée par ce serveur, choisie au lancement : {@code --lab.variant=intent|rest}.
 * Sans variante, le serveur démarrerait sans aucun outil et fausserait un run sans le signaler :
 * on préfère qu'il refuse de démarrer.
 */
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
