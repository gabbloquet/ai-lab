# Pistes d'expériences

Ce fichier réunit les leviers qui n'ont pas encore été jugés, avec ce qui les justifie ou les écarte. Une piste n'est pas une décision : elle devient une expérience quand on lui donne une question, une baseline gelée et un protocole écrit avant les résultats (`experiments/_template/README.md`).

Chaque ligne cite sa preuve. Quand une condition dépend d'une mesure, la mesure est datée et renvoie au rapport qui la porte.

Le tableau « Écartés » de [`PLAN.md`](../experiments/002-leviers-rag/PLAN.md) garde la trace des décisions prises pendant la 002. Pour la suite, c'est ce fichier qui fait foi.

Dernière mise à jour : 2026-11-17, après le tri des pistes de récupération sur le `dev` v5.

## Série RAG (domaine `droit-consommation`)

### Ce que montre la v5

Run consolidé 2, `test` v5, spec `rag-qa/v2` ([rapport](../experiments/002-leviers-rag/results/2026-11-15-run-consolide-2-test.md), blocs B et C, et `runs/consolidated2-test/summary.json`).

| Configuration | `correct` | `all_evidence` | `retrieval_miss` | Réponses inventées |
|---|---|---|---|---|
| `top_k_20`, Mistral Large 4 | 0,870 | 0,880 | 9,5 % | 1,3 % |
| `agentic_rag`, Mistral Large 4 | 0,899 | 0,905 | 6,2 % | 2,6 % |
| `top_k_20`, Gemini 4 Carbon | 0,886 | 0,880 | 10,6 % | 0 % |
| `agentic_rag`, Gemini 4 Carbon | 0,953 | 0,976 | 1,5 % | 0 % |

- **`all_evidence`** (spec v2, § 6) : part des items avec réponse dont tous les articles attendus sont dans le contexte. À 20 passages, la récupération est la même pour tous les générateurs (en cache) : 0,880, soit 22 items incomplets sur 183.
- **`retrieval_miss`** : exécutions sur un item avec réponse, à la réponse fausse, dont le contexte manquait d'au moins un article attendu. À 20 passages, de 7,7 % (Ministral 14B) à 10,7 % (Gemini Flash-Lite) sur les sept générateurs. C'est une borne haute des échecs dus à la récupération : quand la réponse demande plusieurs articles, celui qui manque n'était pas forcément indispensable.
- **Comparaison avec le `dev`.**
  - Sur les `retrieval_miss`, avec les mêmes générateurs, l'écart tient : 4,4 à 7,0 % au contrôle `dev` v5 ([rapport](../experiments/002-leviers-rag/results/2026-11-12-controle-dev-v5.md)).
  - Sur les items complets, il n'est pas net : 0,921 sur le `dev` v4 (5 items incomplets sur 63, pré-étude du README de la 002), contre 0,880 sur le `test` v5 (22 sur 183). Le chiffre de 93 % souvent cité est un rappel d'articles (0,929), une autre mesure.

### Deux règles pour les pistes de récupération

1. **Ne pas juger sur le `test` v5 un levier choisi d'après le `test` v5.** Les pistes ci-dessous sont motivées par des chiffres du `test` v5, déjà lu trois fois en agrégat. Un levier retenu parce que ce `test` montre de la marge, puis jugé sur lui, ajouterait un quatrième regard, avec sélection. Le protocole doit dire, avant toute mesure, sur quels items le verdict sera rendu. Deux options sont possibles. La première est un nouveau `test`, fait d'items jamais lus. Le README du golden set dit que le corpus ne permet pas un `test` neuf : au 2026-11-12, il ne restait que 31 à 44 articles candidats en `set`, et le corpus est épuisé pour les modes à valeurs. Ce qu'il reste pour les autres modes n'est pas vérifié. Un `test` limité aux modes encore possibles n'aurait pas la composition du `test` v5 : ses chiffres ne se compareraient pas à ceux de la 002. La seconde est d'accepter ce quatrième regard, en écrivant le biais de sélection dans les limites. **À trancher par le propriétaire.**
2. **Juger la récupération sur `all_evidence`, pas sur `correct`.** Un levier qui rattraperait tous les `retrieval_miss` gagnerait au plus 6,0 à 8,4 points de `correct` selon le générateur (`retrieval_miss` × 183/234). Or le MDE de `correct` est de 5,7 à 6,4 points (README de la 002, « Taille et MDE »). Un levier qui en rattrape la moitié resterait non concluant sur `correct`. Le critère principal est donc `all_evidence`, apparié, en récupération seule : sans générateur, et sans coût de génération. `correct` sert de garde.

### Tri sur le `dev` v5, en récupération seule (2026-11-17)

Mesuré par la [pré-étude après la clôture](../experiments/002-leviers-rag/README.md#pré-étude-après-la-clôture--trier-les-pistes-de-récupération-2026-11-17-dev-seulement) (`prestudy/search_v5_dev.py`) : 90 items `dev` avec réponse, depuis les caches, sans appel. À 20 passages, 9 items sont incomplets (`all_evidence` = 0,900).

| Piste | Résultat sur le `dev` v5 | Suite |
|---|---|---|
| **Plus de 20 passages** | 30 passages : +1 item ; 50 passages : +2 items, sans perte (0,922). | **Retombe** : 2 items au mieux, sous ce qu'une étape pourrait détecter. |
| **Reclassement Cohere de 50 candidats vers 20 passages** | 0,900, avec 2 items gagnés et 2 perdus. Le gain du `dev` v4 (3 gagnés, 0 perdu) ne tient pas. Il ne réordonne que les mêmes 50 candidats, donc ne peut pas dépasser 0,922. | **Retombe.** |
| **Modèle d'embedding** | Non mesuré : il faut ré-encoder les 2 150 articles. Il produit un autre classement, donc il peut compléter les 9 items incomplets à 20 passages (4 `multi_article`, 3 `paraphrase`, 1 `comparison`, 1 `false_premise`). Parmi eux, 7 manquent encore à 50 passages avec mistral-embed : aucun réordonnancement des candidats actuels ne les atteint. | **Survit, avec un plafond de 9 items** (10 points d'`all_evidence` sur le `dev`). |
| **Multi-query, HyDE** | Non mesurés : ils font un appel au générateur par question. Ils changent la requête, donc ils ont la même cible de 9 items. Le RAG agentique de Carbon, qui reformule ses recherches, ne laisse que 2 items jamais complets (0,959). La reformulation de l'étape 2 n'a pas été concluante sur le `test` v5 : ni gain ni perte de 5 points avec les deux Mistral, et un gain non exclu avec Gemini Flash-Lite ([−2,3 ; +5,2]). | **Survivent, avec le même plafond.** Ils recoupent ce que fait déjà l'agentique : changer la requête. |

**Conclusion du tri.** À requête inchangée, la récupération de ce corpus a presque tout donné. Ce qui reste à gagner tient à la façon de chercher, c'est-à-dire aux requêtes. La ligne « RAG agentique selon le générateur » ci-dessous en devient la piste principale.

### Candidates à une étape

| Piste | Pourquoi | Points à trancher |
|---|---|---|
| **RAG agentique selon le générateur** | Le gain dépend du générateur. Avec Large 4 : +2,8 points, non concluant, perte de 3 points exclue mais pas un gain ([−0,5 ; +6,2]). Avec Carbon : +6,7 points, concluant (comparaison secondaire C', déclarée d'avance). 43 % des appels de Carbon vont à `get_article`, qui cherche un article par son numéro, contre 6 % pour Large 4. | La question porte sur la façon de chercher, pas seulement sur l'outil. Coût de Carbon agentique : 0,025 $ et 21 s par question au tarif du run, environ 0,05 $ après le doublement du tarif au 1ᵉʳ décembre (limites du rapport). |

### En attente : la condition n'est pas remplie

| Piste | Condition | État au 2026-11-17 |
|---|---|---|
| **Vérification d'ancrage** contre les réponses inventées | `PLAN.md` : « une vérification d'ancrage ne revient que si le meilleur modèle de l'étape 7 invente encore » | Large 4 invente sur 1,3 % des questions sans réponse, Carbon sur 0 % (`test` v5). Condition non remplie. |
| **Renvois entre articles** | Écartée sur le `dev` v4 : aucun échec n'était rattrapable par un renvoi (`PLAN.md`). | À rouvrir si Carbon suit des renvois avec `get_article`. Non vérifiable avec les runs existants : ils comptent les appels mais n'en gardent pas les arguments. Carbon appelle `get_article` 1,1 à 1,3 fois par question avec réponse sur le `dev`, alors que 8 questions sur 118 seulement citent un numéro d'article. Pour trancher, il faut relancer en journalisant les arguments. |
| **Questions multi-hop** | Il faut des questions qu'on ne peut pas résoudre sans enchaîner deux articles. Le Code de la consommation seul n'en fournit pas : le second saut se contourne (README du golden set, section « v4 »). | Demande un corpus de plusieurs codes reliés par des renvois. C'est le cas où l'agentique a le plus à gagner, non mesuré par la v5. |
| **Plus d'items `comparison` et `set`** | Le `dev` v5 n'en a que 9 et 7 : le réglage d'un levier sur ces modes reste fragile. | Le corpus est épuisé pour ces modes (README du golden set, section « v5 »). Même dépendance que le multi-hop : un corpus plus large. |

### Écartées, et pourquoi

| Piste | Raison | Source |
|---|---|---|
| Recherche hybride BM25 + dense | Mesurée sur le `dev` v4 : tous les articles @20 = 0,841 contre 0,921 pour la dense, 0 item gagné et 5 perdus. Elle échoue surtout en paraphrase. À ne rouvrir que si la mesure du `dev` v5 la contredit. | Pré-étude du README de la 002 |
| Enrichissement des passages (en-tête indexé) | Mesuré sur le `dev` v4 : 0,921, comme la dense, avec 3 items gagnés et 3 perdus. | Pré-étude du README de la 002 |
| Découpage des articles | Un passage est déjà un article entier, coupé seulement au-delà de 12 000 caractères (`rag/python/src/ailab_rag/corpus.py`). Découper davantage visait le rappel sur le `dev` v4. | `PLAN.md` de la 002 |
| Paramètres ANN, mesure de similarité | La recherche est exacte, et les vecteurs normalisés donnent le même classement quelle que soit la mesure. Il n'y a rien à régler. | Pré-étude du README de la 002 |
| MMR | Il vise la diversité du contexte. Rien n'indique de passages redondants, mais ce n'a pas été mesuré. | `PLAN.md` de la 002 |
| Consignes ou filtres contre les réponses inventées d'un modèle | Le générateur est le levier : on compare des modèles plutôt que de corriger les défauts de l'un. | Décision du propriétaire, `PLAN.md` de la 002 |

## Hors qualité : coût et infrastructure

| Piste | Intérêt | Note |
|---|---|---|
| **Cache sémantique** | Baisse du coût et de la latence, sans effet attendu sur la qualité. | Hors de la question de la 002. Une expérience coût devra mesurer aussi la qualité, pour vérifier l'absence d'effet. |
| **Relance des erreurs d'embedding dans le serveur MCP** | Une erreur passagère de l'API d'embedding coûte aujourd'hui un appel sur les 6 du plafond. | Relancer côté serveur, sans compter la relance dans le plafond. Touche au code MCP : à écrire ensemble. |
| **Limite de débit dans le temps** sur le serveur MCP | Écart connu de la 002 : seul le plafond de 6 appels par session borne le débit. | Voir `docs/mcp-bonnes-pratiques.md` et les limites du rapport de l'étape 8. |
| **Test de `server/discover`** | MUST de la révision `2026-07-28`, assuré par le SDK mais non vérifié par un test du dépôt. | Même source. |
