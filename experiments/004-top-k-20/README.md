# 004 — Envoyer 20 passages au lieu de 5 ?

> **Statut :** gelée le 2026-11-08, run final en cours
> **Domaines :** [`droit-consommation`](../../domains/droit-consommation/README.md)
> **Spec de notation :** [`rag-qa/v1`](../../evals/spec/rag-qa/v1/SPEC.md) (publiée)

Troisième expérience de la série « notre RAG répond mal, quels sont les plus gros leviers ? ». La [002](../002-rag-naif-vs-modele-seul/README.md) a établi le RAG naïf : sur le `test`, 15 à 21 % de ses échecs viennent d'un article attendu absent du contexte. La [003](../003-reformulation-de-requete/README.md) a montré qu'une reformulation de la question remonte l'article attendu au rang 1 plus souvent, sans en mettre plus dans le top-5 : elle n'a rien fait gagner. La 004 agit sur la taille du contexte elle-même.

Les sections Question, Hypothèse, Protocole, Discipline d'itération et Mesures sont écrites avant le premier run.

## Pré-étude : à quelle profondeur sont les articles manqués ? (2026-11-08, `dev` seulement)

Récupération seule du RAG naïf, sans faire répondre de modèle, sur les 44 items `dev` qui ont une réponse. Rappel : part des articles attendus présents dans les k premiers passages. Le `test` n'a pas été mesuré.

| Passages | Rappel | Tous les articles attendus |
|---|---|---|
| 3 | 0,68 | 0,64 |
| **5 (baseline)** | **0,73** | **0,70** |
| 8 | 0,73 | 0,70 |
| 10 | 0,81 | 0,77 |
| 15 | 0,88 | 0,86 |
| **20** | **0,92** | **0,91** |

| Mode (items) | Top-5 | Top-10 | Top-20 |
|---|---|---|---|
| `direct` (11) | 0,91 | 0,91 | 1,00 |
| `reference` (8) | 0,75 | 0,88 | 1,00 |
| `paraphrase` (10) | 0,50 | 0,60 | 0,70 |
| `multi_article` (8) | 0,62 | 0,69 | 0,94 |
| `lost_context` (7) | 0,86 | 1,00 | 1,00 |

- **Les articles manqués sont proches** : la plupart sont classés entre la 9e et la 20e place. Le trou de la baseline est un problème de classement plus que d'article introuvable.
- **La courbe monte régulièrement** de 5 à 20 passages : k = 20 n'est pas un pic bruité choisi parmi plusieurs valeurs.
- **44 items** : 2 points, c'est un item.

**Levier retenu** (décision du 2026-11-08) : top-k = 20. C'est la version la moins chère de ce gain (aucun appel en plus), et le point de comparaison d'un futur reclassement (*reranking*), qui devra faire aussi bien avec 5 passages.

## Question

Sur le Code de la consommation, **envoyer au générateur les 20 passages les plus proches au lieu de 5** augmente-t-il le taux de réponses justes (`correct`, spec `rag-qa/v1`) d'un RAG naïf, à générateur constant ?

## Hypothèse

- **H1 :** le RAG à 20 passages (B) répond juste plus souvent que le RAG naïf à 5 passages (A), surtout sur les questions à plusieurs articles et en référence.
- **H0 :** pas de différence mesurable entre A et B.
- **Plus petit écart qui compte en pratique : 3 points de `correct`.** Le levier n'ajoute aucun appel, seulement des tokens d'entrée : un gain plus petit que pour la 003 vaut déjà son coût.

**Attentes secondaires**, qui ne portent pas le verdict : moins de `retrieval_miss` en B ; plus d'`hallucination` possible sur les items sans réponse (plus d'articles voisins à mal utiliser), surtout pour les générateurs Mistral, déjà à 0,38-0,48 avec 5 passages ; plus de `generation_miss` si le modèle se perd dans un contexte plus long.

## Protocole

| Élément | Valeur |
|---|---|
| Baseline (A) | Le **RAG naïf de la 002**, gelé : un passage par article, texte seul indexé, `mistral-embed`, cosinus exact, top-k = 5, prompts du gel de la 002 |
| Variante (B) | A avec **top-k = 20** |
| Ce qui change entre A et B | Le nombre de passages envoyés au générateur, et lui seul |
| Ce qui est fixé | Le générateur, les prompts, le format de sortie, la température (0), l'index, la requête de recherche (la question seule), les données (`data/v1`) |
| Générateurs | Un verdict par modèle : `mistral:mistral-small-2603`, `mistral:ministral-14b-2512` et `google:gemini-3.5-flash-lite`, ceux des 002 et 003. Identifiants vérifiés le 2026-11-08 (API Mistral `/v1/models`, API Google `v1beta/models`) |
| Golden set | `domains/droit-consommation/golden/rag-qa/v1` (publié) : n_dev = 50, n_test = 150. Le même `test` que les 002 et 003 |
| Répétitions | k = 3 |
| Implémentation | `python/`, sur les briques partagées `ailab_rag` |

**Trois générateurs.** Dans la 003, le levier ne touchait que la récupération, identique pour tous, et les trois deltas se sont confondus. Ici, l'effet passe par la génération : chaque modèle exploite un contexte quatre fois plus long à sa manière, et les verdicts peuvent différer.

**Coût.** Environ 15 passages de plus par question, soit de l'ordre de 3 000 tokens d'entrée (estimation tirée des 1 280 tokens par exécution de A, non vérifiée).

**Taille de l'échantillon.** Au run final de la 003, sur ce même `test` et avec ce même A, s_d valait 0,31 à 0,34. Avec s_d = 0,33, le MDE sur 150 items vaut (1,976 + 0,844) × 0,33 / √150 ≈ **7,6 points**, au-dessus des 3 points qui comptent. **L'expérience manque de puissance pour un gain de 3 points** : un résultat non concluant ne prouvera pas l'absence d'effet, et exclure un gain utile demanderait une borne haute sous +3 points. Écrit avant le premier run.

**Lancer un run** (depuis `python/`) :

```sh
uv run --env-file ../../../.env python -m exp004_rag.campaign \
    --split dev --model mistral:mistral-small-2603 --k 3 --run-dir ../runs/<nom>
```

Le run final ajoute `--split test --final --langfuse` ; il refuse de partir si l'arbre git n'est pas propre. Le `summary.json` est écrit avant l'envoi des traces à Langfuse, qui est abandonné après 120 s (`run.langfuse_flushed` le signale).

## Discipline d'itération

1. **Même effort pour chaque variante.** A est le RAG naïf gelé de la 002, qui y a reçu deux cycles de mise au point (consigne d'abstention, phrase d'ancrage). B a droit au même nombre de cycles sur le `dev`. A ne change pas.
2. **Gel avant le run final**, puis **un seul run sur le `test`**. Un run raté pour une raison technique se relance en entier, et l'incident est noté dans les Limites.

**Budget d'itération :** A, 2 cycles reçus dans la 002, gelé ; B, N = 2 cycles sur le `dev`, avec Mistral Small. Ces cycles sont réservés à l'adaptation du prompt de génération au contexte long (par exemple si les réponses inventées augmentent) ; la valeur k = 20 est fixée par la pré-étude et ne change pas.

**Journal d'itération**, sur le `dev` uniquement (Mistral Small, k = 3) :

| # | Date | Variante | Modification | Motif | `correct` dev |
|---|---|---|---|---|---|
| 0 | 2026-11-08 | A et B | aucune : mesure de départ (commit `8164964`) | vérifier la chaîne, estimer s_d | A 0,767 · **B 0,867** ; delta +0,10 [−0,002 ; +0,20]. `retrieval_miss` 0,18 → 0,03 ; `generation_miss` 0,04 → 0,08 ; `false_abstention` 0,15 → 0,02 ; `hallucination` 0,33 → 0,28 ; plusieurs articles 0,54 → 0,88 ; tokens 1 280 → 4 233. Items B > A : 7, B < A : 3 (abstentions isolées sur une répétition). s_d = 0,358 |

**Commit de gel :** le commit « Geler la 004 avant le run final sur le test » (2026-11-08). Son hash est enregistré dans le `summary.json` de chaque run (`run.commit`).

**Configuration gelée :** A, le RAG naïf de la 002, inchangé ; B, le même avec top-k = 20. Le prompt de génération est celui du gel de la 002 pour les deux variantes (`ailab_rag.prompting`, identique à `exp002_rag/prompting.py` du commit `8d082ad` à l'import près). **Budget utilisé : 0 cycle sur 2 pour B.** Les cycles étaient réservés à une hausse des réponses inventées, qui ne s'est pas produite au run 0 (0,33 → 0,28) ; corriger les quelques abstentions à tort aurait ajusté B sur 3 items du `dev`.
**Run final sur le `test` :** à venir

## Mesures

- **Métrique principale, qui porte le verdict :** `correct`, spec `rag-qa/v1` (§ 5).
- **Métriques secondaires, publiées sans porter le verdict :** répartition de `failure` (dont `retrieval_miss` et `generation_miss`), `evidence_recall@k` (k ∈ {1, 3, 5, 10}), `correct` par mode, `hallucination`, `false_abstention`, précision et rappel des citations, tokens du générateur par exécution.
- **Règle de verdict :** celle de la spec (§ 8).

## Résultats

À venir.

## Verdict

À venir.

## Limites

Déjà connues avant le run :
- **B moins travaillée que A** : A a reçu deux cycles de mise au point dans la 002, B aucun (gel au run 0, voir Configuration gelée). L'écart, s'il joue, joue contre B.
- **Profondeur choisie sur le `dev`**, parmi six valeurs mesurées : le gain de rappel de la pré-étude peut être en partie optimiste, même si la courbe est régulière.
- **Puissance insuffisante pour 3 points** (voir Taille de l'échantillon).
- **Les limites de la 002 s'appliquent** : un seul corpus, questions rédigées par un LLM, golden set relu avec l'aide d'un LLM.
