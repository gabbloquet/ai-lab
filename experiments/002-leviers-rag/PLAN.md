# 002 — Plan de la suite

> **Mis à jour le 2026-11-10.** Ce plan n'est pas un protocole. Chaque étape écrit le sien dans le [README](README.md) avant ses résultats.

## Où on en est

- Les étapes 1 à 6 sont jugées. Le run consolidé tourne sur `rag-qa/v4` et la spec `rag-qa/v1`.
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
