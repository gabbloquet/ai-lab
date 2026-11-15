# 002 — Plan de la suite

> **Mis à jour le 2026-11-12.** Ce plan n'est pas un protocole. Chaque étape écrit le sien dans le [README](README.md) avant ses résultats.

## Où on en est

- Les étapes 1 à 6 sont jugées. Le run consolidé tourne sur `rag-qa/v4` et la spec `rag-qa/v1`.
- **Chantier 1 fait (2026-11-12)** : la spec [`rag-qa/v2`](../../evals/spec/rag-qa/v2/SPEC.md) est écrite, en brouillon jusqu'au premier rapport qui la citera. Elle comprend le `SPEC.md`, les schémas des items et des exécutions, 84 vecteurs de conformance, et les scorers Python (`ailab_evals.rag_qa_v2`, avec sa métrique DeepEval) et Java (`ragqa`), qui passent tous les vecteurs. Elle couvre aussi ce que demandent les étapes 7 et 8 : coût, latence, appels de recherche, verdict à deux critères, Holm et items exclus.
- **Chantier 2 fait (2026-11-12)** : le golden set [`rag-qa/v5`](../../domains/droit-consommation/golden/rag-qa/README.md) est écrit, avec 366 items. Son `dev` passe à 120 items (`comparison` 9, `set` 7, `false_premise` 20, `multi_article` 18), et son `test` est celui de la v4, complété des champs v2. Le lanceur accepte `--spec v2`, et le run `dev` de contrôle (chantier 3) peut partir. Il rejoue les configurations gelées des étapes 1 à 5, et y ajoute celle de l'étape 6 (`abstain_low_rerank`), calculée sans appel au générateur à partir de `top_k_20` et des notes Cohere.
- **Chantier 3 fait (2026-11-12)** : le [run `dev` de contrôle](results/2026-11-12-controle-dev-v5.md) reproduit les configurations gelées des étapes 1 à 6 sur la v5, notée par la spec v2. Les leviers gardent le sens qu'ils avaient sur la v4, et les modes récents sont les plus durs (`set` sous 0,40). La spec v2 et la v5 sont publiées. L'étape 7 peut commencer.
- **Chantier 4, étape 7, gelée (2026-11-13)** : le run `dev` des quatre candidats est fait ([rapport](results/2026-11-12-etape-7-dev.md)). Les quatre font moins inventer que Mistral Small. La règle du protocole retient **Mistral Large 4** comme générateur de l'étape 8. Le verdict viendra du run consolidé 2.
- **Chantier 5, étape 8 : protocole écrit (2026-11-14)**. RAG agentique avec Mistral Large 4 : deux outils MCP (recherche de 5 passages, lecture d'un article), 6 appels au plus, serveur Python en stdio, 2 cycles `dev` sur le prompt et les descriptions des outils. Le serveur s'écrit ensemble.
- **Chantier 5, étape 8, gelée (2026-11-15)** : le serveur MCP, le client agentique et deux cycles `dev` sont faits ([rapport](results/2026-11-15-etape-8-dev.md)). Le cycle 2 est gelé. Sur le `dev`, +2,8 points de `correct` (non concluant) et un coût 2,4 fois plus élevé. Il reste le chantier 6, le run consolidé 2, dont le protocole s'écrit ensemble.
- D'après la pré-étude des erreurs (README, 2026-11-10, `dev` v4) :
  - la récupération est saturée : à 20 passages, elle ne rate plus que 3 items ;
  - les erreurs qui restent viennent de la génération, surtout des listes incomplètes en `set` ;
  - les réponses inventées dépendent du modèle : 9 sur 28 avec Mistral Small, 0 avec Gemini Flash-Lite ;
  - le `dev` v4 est trop petit pour régler un levier sur `multi_article` ou `comparison`.

## Décisions du propriétaire (2026-11-10)

- Pas de levier taillé pour corriger les défauts d'un modèle. Le générateur est lui-même un levier : c'est l'étape 7.
- Le RAG agentique devient l'étape 8 de la 002.
- Toute la 002 se rejoue sur `rag-qa/v5`, notée par la spec `rag-qa/v2`.
- L'étape 7 attend la v5.

## Décisions du propriétaire (2026-11-12)

- La v5 étend la v4 : seul le `dev` grandit, et le `test` v5 est celui de la v4. Le corpus ne permet pas un `test` neuf.
- Pas de multi-hop dans la v5. L'étape 8 est jugée sur les modes existants, et c'est une limite écrite.
- Les items v4 `comparison` et `false_premise` reçoivent les champs v2 (`anchor`, `false_value`), qui sont relus.
- Le code de campagne de la 002 est adapté à la spec v2 par Claude, en TDD, avec un résumé des choix à la fin.

## Décisions du propriétaire pour l'étape 7 (2026-11-12)

- Quatre candidats, un par axe. Identifiants, disponibilité et tarifs ont été vérifiés le 2026-11-12 sur docs.mistral.ai et aistudio.google.com.
  - Plus gros, même famille : `mistral-large-4-0`, à 0,70 / 2,10 $ par million de tokens.
  - Modèle de pointe : `gemini-4-carbon`, à 2 / 10 $ jusqu'au 30/11, puis 4 / 20 $.
  - Open-weight d'une autre famille : `gemma-4-31b-it`, Apache 2.0, sur le seul palier gratuit.
  - Raisonnement sur un modèle testé : `mistral-small-2603` avec `reasoning_effort="high"`.
- Large 4 et Carbon ne peuvent pas désactiver leur réflexion. Ils tournent au niveau `low`, le plus proche de la baseline, et c'est une limite écrite.
- Baseline : `mistral-small-2603`, sans réflexion (63 tokens de sortie en médiane au run de contrôle), avec `top_k_20`.
- `temperature` n'est plus envoyée aux modèles Gemini, qui l'ignorent (note du README, « Limites »).

## Feuille de route

| # | Chantier | Qui écrit | Sortie |
|---|---|---|---|
| 1 | **Spec `rag-qa/v2`** | ensemble | `SPEC.md`, JSON Schema, vecteurs de conformance, scorers Java et Python qui passent tous les vecteurs |
| 2 | **Golden set `rag-qa/v5`** | Claude (délégué, TDD, résumé des choix) | items conformes au schéma v2, splits `dev` et `test` |
| 3 | **Run `dev` de contrôle v5** | Claude | configurations gelées 1 à 6 rejouées sur le `dev` v5, sans rien régler |
| 4 | **Étape 7 : le générateur** | ensemble (protocole) | verdict par modèle |
| 5 | **Étape 8 : RAG agentique** | ensemble (MCP) | verdict à modèle constant |
| 6 | **Run consolidé 2** sur le `test` v5 | ensemble (protocole) | tableau final des deltas, clôture de la 002 |

**1. Spec v2.** Elle passe en premier, parce qu'elle fixe le format des items de la v5. Elle doit corriger trois limites de la v1 :
- noter les listes (`set`) sans faux négatifs par mots-clés (exemple : `rq-267`) ;
- vérifier le rattachement des valeurs en `comparison` ;
- vérifier le rejet de la prémisse en `false_premise`, ce qui demande un champ `false_value` dans les items.

**2. Golden set v5.** Il faut assez d'items `dev` par mode pour itérer, au moins une vingtaine par mode nouveau (nombre à fixer d'après le MDE) : `multi_article`, `comparison`, `set`, `false_premise`. Il faut aussi des questions multi-hop, pour l'étape 8. Le corpus `data/v1` reste le même, sauf décision contraire.

**3. Run `dev` de contrôle.** Il vérifie que le code de campagne reproduit les configurations gelées, et donne une première mesure de la difficulté de la v5. Ses scores ne servent à rien régler.

**4. Étape 7.** Configuration `top_k_20` gelée, prompts gelés, k = 3. On teste un modèle par axe :
- plus gros dans la même famille ;
- modèle de pointe ;
- open-weight hébergeable ;
- raisonnement activé sur un modèle déjà testé.

Deux critères : `correct` et le taux de réponses inventées. Le coût se compare en dollars par question, avec la latence, jamais en tokens d'un fournisseur à l'autre. Les identifiants, la disponibilité et les tarifs se vérifient à la source avant d'écrire le protocole.

**5. Étape 8.** La recherche devient un outil MCP, conforme à `docs/mcp-bonnes-pratiques.md`, que le modèle appelle autant de fois qu'il veut. Elle est jugée contre `top_k_20`, à modèle constant. Le modèle doit être bon en appel d'outils, et l'étape 7 sert à le choisir. Elle a droit au même nombre de cycles `dev` que la baseline, qui en a reçu 2. Mesures : `correct`, dollars par question, latence, nombre d'appels.

**6. Run consolidé 2.** Il rejoue toutes les configurations gelées des étapes 1 à 8 sur le `test` v5. Il produit le tableau final et la conclusion de la 002, générateur compris.

## Décisions ouvertes

- **Combien de regards sur le `test` v5 ?** Soit les étapes 7 et 8 ont chacune leur run final, puis le run consolidé 2 rejoue tout. Soit elles s'arrêtent à leur gel sur le `dev`, et leur seul run `test` est le run consolidé 2. Recommandation : la seconde, pour ne regarder qu'une fois le `test` v5.
- **Générateurs du run consolidé 2** : les trois actuels seulement, ou aussi ceux de l'étape 7 ? C'est une question de coût.
- **Taille de la v5 par mode**, à fixer d'après le MDE visé.

## Écartés, et pourquoi

| Leviers | Raison |
|---|---|
| Découpage, enrichissement des passages, recherche hybride, HyDE, multi-query, MMR, paramètres ANN | ils visent le rappel, déjà saturé : au plus 3,7 points à gagner sur le `dev` v4 |
| Renvois entre articles | aucun échec du `dev` v4 n'est rattrapable par un renvoi |
| Modèle d'embedding | dernier levier de récupération non couvert, même plafond : en réserve, à revoir si la v5 montre des échecs de récupération |
| Consignes ou filtres contre les réponses inventées d'un modèle | écartés par la décision ci-dessus ; une vérification d'ancrage ne revient que si le meilleur modèle de l'étape 7 invente encore |
| Cache sémantique | ne change rien à la qualité ; piste de coût, hors de la question de la 002 |
