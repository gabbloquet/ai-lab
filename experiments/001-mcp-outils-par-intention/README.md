# 001 — Outils MCP : par intention métier ou miroir REST ?

> **Statut :** cadrage
> **Domaines :** [`magasin`](../../domains/magasin/README.md)
> **Spec de notation :** [`tool-selection/v1`](../../evals/spec/tool-selection/v1/SPEC.md) (brouillon)

## Question

Un serveur MCP dont les outils correspondent à des **intentions métier**, comme `find_in_stock_alternative(sku, store_id)`, permet-il à un LLM de faire **plus souvent les bons appels avec les bons arguments** qu'un serveur dont les outils **reproduisent les endpoints d'une API REST** (`get_product`, `get_stock`, `get_similar`…) ?

## Hypothèse

- **H1 :** la variante par intention (B) a un taux de `success` plus élevé que la variante miroir REST (A). Elle demande moins de chaînage, donc il y a moins d'occasions de se tromper.
- **H0 :** pas de différence mesurable entre A et B.
- **Plus petit écart qui compte en pratique : 10 points de `success`.** En dessous, réécrire un serveur MCP existant ne vaut pas l'effort.
- **Attentes secondaires**, qui ne portent pas le verdict : B fait moins d'appels par question. Pour les tokens, aucune prédiction : les schémas de B sont peut-être plus longs, mais B demande moins de tours d'échange.

### Ce que disent les praticiens

L'hypothèse n'est pas nouvelle : des praticiens expérimentés la recommandent déjà.

- [Anthropic, *Writing effective tools for agents*](https://www.anthropic.com/engineering/writing-tools-for-agents) conseille de construire des outils autour du besoin de l'agent plutôt que d'exposer les endpoints d'une API. Son exemple : un `schedule_event` qui trouve un créneau et crée l'événement, plutôt que `list_users`, `list_events` et `create_event`. L'article recommande aussi des réponses riches en information utile (des noms lisibles plutôt que des identifiants techniques), des erreurs qui disent quoi corriger, et un format de réponse choisi par évaluation.
- [Philipp Schmid, *MCP best practices*](https://www.philschmid.de/mcp-best-practices) classe la conversion « un endpoint REST, un outil » parmi les pièges, et recommande de 5 à 15 outils par serveur.
- [Nordic APIs](https://nordicapis.com/8-tips-and-best-practices-for-mcp-server-development/) recommande un serveur par domaine (*bounded context*).

**Ce que la 001 ajoute :** une mesure, et non une recommandation. Même modèle, mêmes questions, deux designs, un intervalle de confiance, trois modèles, et un split `test` jamais vu pendant la mise au point. Anthropic recommande d'ailleurs lui-même de valider ces choix par l'évaluation, avec un jeu de test mis de côté.

## Protocole

| Élément | Valeur |
|---|---|
| Baseline (A) | Serveur MCP **miroir REST** : 5 outils calqués sur des endpoints |
| Variante (B) | Serveur MCP **par intention** : 5 outils, un par besoin métier |
| Ce qui change entre A et B | Le découpage, les noms et les descriptions des outils, et donc le jeu d'outils exposé |
| Ce qui est fixé | Le modèle, le prompt système, la température (0), un maximum de **10 appels d'outils** par exécution, le nombre d'outils (5 de chaque côté), le guide de rédaction des descriptions (voir plus bas), le transport (Streamable HTTP, sur `127.0.0.1`), le format des réponses (JSON sérialisé dans un bloc texte, voir plus bas), les données (`domains/magasin/data/v1`), la boucle d'agent et sa configuration (voir plus bas) |
| Modèles | Un modèle par fournisseur : Gemini, Mistral et Claude. Les identifiants exacts seront fixés et vérifiés avant le gel. Un verdict par modèle. |
| Golden set | `domains/magasin/golden/tool-selection/v1` : 130 items, **n_dev = 30, n_test = 100**, 26 items par intention, soit environ 6 en `dev` et 20 en `test` |
| Répétitions | k = 5 |
| Implémentation | `java/` : les deux serveurs MCP (Spring AI), testés en boîte noire à travers le protocole MCP. `python/` : la boucle d'agent, qui sert de client MCP, et la notation (métrique DeepEval personnalisée, conforme à la spec) |

### Les deux jeux d'outils

Les deux serveurs couvrent les **mêmes cinq besoins** :

| Besoin | B — par intention | A — miroir REST |
|---|---|---|
| Disponibilité d'un produit dans un magasin | `check_availability(sku, store_id)` | `get_stock(sku, store_id)` |
| Alternative en stock | `find_in_stock_alternative(sku, store_id)` | `get_similar(sku)` puis `get_stock(sku, store_id)` |
| Autres magasins qui ont le produit | `find_stores_with_stock(sku)` | `list_stores()` puis `get_stock(sku, store_id)` pour chaque magasin |
| Fiche produit | `get_product_details(sku)` | `get_product(sku)` |
| Recherche dans le catalogue | `search_catalog(query, category?)` | `list_products(query?, category?)` |

Les **deux serveurs renvoient de vraies données** du domaine : en A, le modèle a besoin du résultat de `get_similar` pour savoir sur quels SKU appeler `get_stock`. Leur logique est implémentée en TDD.

### Architecture des serveurs

Les deux variantes sont **deux adaptateurs primaires au-dessus du même cœur** (architecture hexagonale) :

```
java/src/main/java/io/github/gabbloquet/ailab/exp001/catalog/
├── domain/              le cœur : entités, value objects (SkuCode, StoreId), règles métier
└── infra/
    ├── in/mcp/          adaptateurs entrants (primaires) : ce qui pilote le cœur
    │   ├── ToolResults      construction des réponses MCP, commune aux deux variantes
    │   ├── intent/          variante B : outils et DTO de réponse
    │   └── rest/            variante A : outils et DTO de réponse
    └── out/data/        adaptateur sortant (secondaire) : chargement de domains/magasin/data/v1, embarqué dans le jar
```

- Le protocole MCP reste hors du domaine : aucune annotation ni aucun type MCP dans `catalog.domain`.
- **Chaque outil renvoie un DTO dédié**, jamais un objet du domaine. La réponse se conçoit pour le modèle, et une évolution du domaine ne doit pas modifier en silence ce qu'il lit.
- Les paramètres des outils sont des types simples (`String`), convertis en value objects à l'intérieur de l'adaptateur. Le schéma vu par le modèle reste donc `{"sku": {"type": "string"}}`.

**Les réponses sont construites par `ToolResults`, pas par Spring AI.** Par défaut, Spring AI 2.0.1 renvoie le message d'une exception deux fois (son code concatène le message et celui de la cause racine, qui est l'exception elle-même quand elle n'a pas de cause), et transmettrait au modèle le détail d'une erreur interne. `ToolResults` renvoie le JSON en un seul bloc texte, une erreur attendue avec son message une seule fois, et un message générique pour une erreur inattendue, journalisée côté serveur.

**Format des réponses : JSON dans un bloc texte, pour les deux variantes.** Spring AI 2.0.1 propose aussi un mode structuré (`generateOutputSchema = true`), qui publie un `outputSchema`. Mais d'après son code source (`AbstractMcpToolMethodCallback.convertValueToCallToolResult`, lu le 2026-10-22), il renvoie alors le résultat **uniquement** en `structuredContent`, sans le bloc texte que la spec MCP recommande pour la compatibilité. Un hôte qui ne lit que le texte ne verrait rien. Le mode texte est lu par tous les hôtes. Le format de réponse fera l'objet d'une expérience à part.

### Neutraliser l'effet des descriptions

Si les outils de B étaient mieux décrits que ceux de A, l'expérience mesurerait la qualité de rédaction et non le découpage. Pour l'éviter, les deux variantes suivent **le même guide de rédaction** :
- chaque description suit la même structure : ce que fait l'outil, ce qu'il renvoie, et un mot sur chaque paramètre ;
- **aucune formulation n'est reprise des questions du golden set** ;
- la longueur totale des descriptions d'une variante ne s'écarte pas de plus de 20 % de l'autre, en tokens.

Les longueurs mesurées sont publiées dans les Résultats.

### Contexte transmis au modèle

Un prompt système identique pour les deux variantes, versionné dans `python/prompts/system.md`, indique le magasin courant (`context.storeId` de l'item). Le modèle ne reçoit ni identifiant de magasin supplémentaire ni liste de SKU.

### Boucle d'agent

La boucle est la même pour les deux variantes et ne partage aucun code avec les serveurs. Elle se connecte en Streamable HTTP au serveur de la variante, démarré avec `--lab.variant`, pose la question, exécute les appels d'outils et enregistre **tous les appels émis**, y compris ceux qui sont rejetés côté client ou côté serveur, comme l'exige la spec.

Une bibliothèque d'agent fait des choses en coulisse qui influencent la mesure : validation des arguments côté client, nouvelle tentative proposée automatiquement au modèle, comptage des appels. Ces comportements sont donc **des paramètres du protocole**, fixés et documentés :

| Paramètre | Valeur prévue |
|---|---|
| Bibliothèque | Pydantic AI (`pydantic-ai` 2.59.0), sous réserve du test exploratoire ci-dessous |
| Erreur renvoyée par un outil MCP | `tool_error_behavior='failed'` : l'erreur est rendue au modèle comme un résultat en échec, sans demande de correction automatique |
| Arguments invalides (validation côté client) | Budget de correction : à fixer après le test exploratoire |
| Plafond de 10 appels | Via `request_limit` ou un compteur à nous. `tool_calls_limit` ne compte que les appels réussis. |

**Test exploratoire, avant tout run.** On connecte la boucle à un serveur MCP minimal, puis on provoque un argument invalide, un argument halluciné et une erreur serveur. Ce test vérifie deux choses :
- l'historique des messages conserve-t-il chaque appel émis, y compris les appels invalides ?
- que se passe-t-il quand le budget de correction est épuisé ?

Si l'historique ne permet pas de reconstituer tous les appels, on écrit la boucle nous-mêmes, directement avec les SDK des fournisseurs et le SDK MCP Python.

### Taille de l'échantillon

MDE = (t₀,₉₇₅ + t₀,₈₀) × s_d / √n_test, avec n_test = 100 :

| Hypothèse sur s_d | 0,3 | 0,4 | 0,5 |
|---|---|---|---|
| MDE | 8,5 pts | 11,3 pts | 14,1 pts |

Avec s_d ≤ 0,35, le MDE reste sous les 10 points qu'on vise. Si le s_d mesuré sur les runs `dev` dépasse 0,4, on le note dans les Limites **avant** le run `test` : l'expérience ne pourra alors pas détecter un écart de 10 points.

### Lancer un run

À définir avec l'implémentation.

## Discipline d'itération

1. **Même effort pour chaque variante :** 3 cycles d'itération sur le `dev` par variante, avec **un seul modèle** (le moins cher des trois) pour limiter le coût.
2. **Gel avant le run final :** un commit fige les deux serveurs, leurs descriptions, le prompt système, la boucle d'agent avec sa configuration, et les identifiants de modèles.
3. **Un seul run sur le `test`**, sur les trois modèles.

**Budget d'itération :** N = 3 cycles par variante.

**Journal d'itération :**

| # | Date | Variante | Modification | Motif | `success` dev |
|---|---|---|---|---|---|
| | | | | | |

**Commit de gel :** —
**Run final sur le `test` :** —

## Mesures

- **Métrique principale, qui porte le verdict :** `success` (tous les appels requis sont faits avec des arguments acceptables), selon la spec `tool-selection/v1`.
- **Métriques secondaires :** `args_recall`, `tool_recall`, `precision`, `strict_success`, `extra_calls`, `n_calls`, tokens par item (entrée + sortie), longueur des descriptions d'outils (en tokens).
- **Règle de verdict :** celle de la spec. Delta apparié sur le `test`, IC à 95 % ; B est meilleure si la borne basse de l'IC est au-dessus de 0.

## Résultats

Pas encore de résultats.

## Verdict

Pas encore de verdict.

## Limites

- **Version de la spec MCP** (vérifié le 2026-10-21). La pile Java (Spring AI 2.0.1, SDK MCP Java 2.1.0) s'arrête à la révision `2025-11-25`. La révision `2026-07-28` (cœur sans état, `server/discover`, Multi Round-Trip Requests) n'est **pas** supportée par le SDK Java 2.1.0 ([ROADMAP](https://github.com/modelcontextprotocol/java-sdk/blob/main/ROADMAP.md) : prévue en 3.x). Le SDK Python 2.3.0 la supporte ([`MODERN_PROTOCOL_VERSIONS`](https://github.com/modelcontextprotocol/python-sdk/blob/v2.3.0/src/mcp-types/mcp_types/version.py)). Les deux variantes partagent la même pile, donc la comparaison n'est pas biaisée, mais l'expérience ne dit rien de spécifique à la révision `2026-07-28`.
- **Données synthétiques**, un seul domaine, questions en français. Le résultat ne se généralise pas tel quel à d'autres domaines, d'autres langues ou des catalogues plus grands.
- **Cinq outils par variante.** Avec des dizaines d'outils, l'écart pourrait être très différent.
- **Itération sur un seul modèle.** Les variantes sont mises au point avec un seul modèle, ce qui peut avantager ce modèle-là au run final.
- **Non-déterminisme.** Une température de 0 ne garantit pas des sorties identiques chez ces fournisseurs. C'est ce que couvrent les k = 5 répétitions. Si un modèle n'accepte pas la température 0, sa configuration réelle est indiquée ici.
- **Effet des descriptions.** Le guide de rédaction le réduit sans l'éliminer.
- **Format des réponses.** Il est fixé à du JSON en texte. Anthropic indique que le format (JSON, XML, Markdown) change les performances : l'écart entre A et B pourrait être différent avec un autre format.
- **Boucle d'agent.** Les résultats valent pour cette boucle et sa configuration. Un autre client, par exemple Spring AI `ChatClient` ou un IDE, formate autrement les schémas d'outils et gère autrement les erreurs : l'écart absolu entre A et B pourrait changer.
