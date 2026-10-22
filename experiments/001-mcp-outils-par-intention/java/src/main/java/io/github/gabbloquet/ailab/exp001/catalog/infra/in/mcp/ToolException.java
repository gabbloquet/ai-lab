package io.github.gabbloquet.ailab.exp001.catalog.infra.in.mcp;

/**
 * Erreur attendue d'un outil (produit introuvable, demande impossible). Son message est renvoyé
 * tel quel au modèle : il doit dire ce qui ne va pas et comment corriger l'appel.
 */
public class ToolException extends RuntimeException {

    public ToolException(String message) {
        super(message);
    }
}
