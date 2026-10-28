# Bonnes pratiques MCP

Référentiel des serveurs MCP du laboratoire. Il distingue ce que **la spec impose** (MUST, SHOULD) de ce que **des praticiens recommandent** sans l'avoir mesuré. Les recommandations sont des hypothèses : certaines expériences du laboratoire les mettent à l'épreuve, comme la [001](../experiments/001-mcp-outils-par-intention/README.md) pour le découpage des outils.

Sources vérifiées le 2026-10-28. Révision de référence : `2025-11-25`, la dernière supportée par la pile Java (SDK MCP Java 2.1.0). Les changements de `2026-07-28` sont signalés à part.

## 1. Concevoir les outils pour le modèle (recommandations)

- **Partir des tâches de l'agent, pas des endpoints d'une API.** `search_contacts` plutôt que `list_contacts`, `schedule_event` plutôt que trois appels à enchaîner ([Anthropic](https://www.anthropic.com/engineering/writing-tools-for-agents), [Philipp Schmid](https://www.philschmid.de/mcp-best-practices)).
- **Peu d'outils, un rôle par serveur.** De 5 à 15 outils par serveur, un serveur par domaine ; supprimer les outils inutilisés (Philipp Schmid).
- **Des arguments plats.** Des types simples, des enums, des valeurs par défaut ; pas d'objets imbriqués, sur lesquels le modèle invente des clés (Philipp Schmid).
- **Des descriptions écrites comme pour un nouvel arrivant.** Quand utiliser l'outil, le format attendu, ce que contient la réponse ; des noms de paramètres sans ambiguïté, `user_id` plutôt que `user` (Anthropic).
- **Des noms qui ne collisionnent pas entre serveurs**, par exemple `{service}_{action}_{resource}` (Philipp Schmid). La spec fixe le jeu de caractères : 1 à 128 caractères parmi `A-Za-z0-9_-.`, sensibles à la casse, uniques dans le serveur (SHOULD).
- **Des réponses sobres.** Des noms lisibles plutôt que des identifiants techniques, de la pagination (`limit` par défaut entre 20 et 50, `has_more`, `total_count`), et, quand une réponse est tronquée, l'indication de comment affiner (Anthropic, Philipp Schmid).

## 2. Réponses et erreurs (spec)

- **Deux mécanismes d'erreur.** Une erreur **protocole** (JSON-RPC) signale un problème de requête : outil inconnu, requête mal formée. Une erreur **d'exécution** (`isError: true` dans le résultat) signale une validation métier ou une API en échec ; le client SHOULD la transmettre au modèle pour qu'il se corrige.
- **Une erreur dit quoi corriger**, avec le format attendu (Anthropic). Jamais de trace ni de détail interne.
- **Un `structuredContent` s'accompagne de son JSON dans un bloc texte** (SHOULD, compatibilité). Si un `outputSchema` est publié, le résultat MUST s'y conformer.
- **Un outil sans paramètre** déclare `{"type": "object", "additionalProperties": false}` (recommandé par la spec).

## 3. Sécuriser le serveur (spec)

**Outils.** Le serveur MUST valider toutes les entrées, contrôler les accès, limiter le débit des appels et assainir les sorties. Les annotations (`readOnlyHint`, `destructiveHint`…) sont **non fiables** pour le client, sauf serveur de confiance : elles informent, elles ne protègent pas.

**Transport Streamable HTTP.**
- MUST valider l'en-tête `Origin` sur toutes les connexions ; une origine présente et invalide reçoit un 403. C'est la défense contre le DNS rebinding.
- En local, SHOULD écouter sur `127.0.0.1` uniquement, pas sur `0.0.0.0`.
- SHOULD authentifier toutes les connexions.
- Un identifiant de session SHOULD être unique et cryptographiquement sûr. Une session MUST NOT servir à authentifier.

**Serveur local.** Préférer `stdio` ; en HTTP, exiger un token ou passer par un socket local à accès restreint.

## 4. Authentification (spec)

L'autorisation est optionnelle. Dès qu'un serveur HTTP la met en place, il est un **resource server OAuth 2.1** : il valide des tokens, il n'en émet pas.

**Serveur MCP.**
- MUST publier un document Protected Resource Metadata ([RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728)) qui nomme au moins un serveur d'autorisation, et le signaler par `WWW-Authenticate: Bearer resource_metadata="…"` sur un 401 ou par l'URI `.well-known/oauth-protected-resource`. SHOULD ajouter `scope="…"` au challenge.
- MUST valider chaque token, à chaque requête, et n'accepter que ceux émis **pour lui** (audience, [RFC 8707](https://www.rfc-editor.org/rfc/rfc8707.html)).
- MUST NOT transmettre le token reçu à une API en aval (*token passthrough*) : pour appeler une autre API, il obtient son propre token.
- Codes HTTP : 401 pour un token absent, invalide ou expiré ; 403 avec `error="insufficient_scope"` et les scopes requis pour une permission insuffisante ; 400 pour une requête d'autorisation mal formée.
- Scopes minimaux : un scope de base en lecture, des scopes supplémentaires demandés au moment où une opération les exige (*step-up*). Pas de `*`, pas de catalogue complet dans `scopes_supported`.

**Client MCP.**
- MUST utiliser PKCE (`S256`) et refuser un serveur d'autorisation qui ne l'annonce pas.
- MUST envoyer le paramètre `resource` (URI canonique du serveur MCP) dans les requêtes d'autorisation et de token.
- MUST passer le token dans l'en-tête `Authorization: Bearer`, jamais dans l'URL.
- Enregistrement, par ordre de préférence : pré-enregistrement, Client ID Metadata Documents, puis Dynamic Client Registration en dernier recours.

**Transport `stdio`.** Pas d'OAuth : les identifiants viennent de l'environnement (SHOULD NOT suivre la spec d'autorisation).

## 5. Évaluer les outils (recommandation)

Le processus d'Anthropic : des tâches réalistes en plusieurs étapes, chacune avec un résultat vérifiable ; une mesure de la précision, du nombre d'appels, des tokens et des erreurs ; la lecture des transcripts (des erreurs de paramètre répétées signalent une description à reformuler) ; une confirmation sur un jeu de test mis de côté. C'est la méthode du laboratoire : split `dev` pour itérer, split `test` pour le verdict.

## 6. Révision `2026-07-28`

Non supportée par le SDK MCP Java 2.1.0, supportée par le SDK MCP Python 2.3.0 (voir les limites de la [001](../experiments/001-mcp-outils-par-intention/README.md#limites)).

- **Plus de sessions ni de handshake `initialize`.** Chaque requête porte sa version de protocole et les capacités du client dans `_meta`. Un état entre appels passe par des identifiants créés par le serveur et transmis comme arguments d'outil.
- **`server/discover`** devient obligatoire (MUST) pour annoncer versions, capacités et identité.
- **`tools/list`** SHOULD renvoyer les outils dans un ordre déterministe, pour le cache du client et le cache de prompt du modèle.
- **Dépréciés** : Roots, Sampling, Logging (journaliser sur `stderr` ou via OpenTelemetry), et Dynamic Client Registration au profit des Client ID Metadata Documents.

## Sources

- [Spec MCP 2025-11-25 : Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [Spec MCP 2025-11-25 : Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [Spec MCP 2025-11-25 : Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)
- [Spec MCP 2025-11-25 : Security Best Practices](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices)
- [Spec MCP 2026-07-28 : Key Changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [Anthropic, *Writing effective tools for agents*](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Philipp Schmid, *MCP best practices*](https://www.philschmid.de/mcp-best-practices)
