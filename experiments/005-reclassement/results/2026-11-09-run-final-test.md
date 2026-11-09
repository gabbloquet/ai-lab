# 005 — Run final sur le split `test` (2026-11-09)

**Question :** sur le Code de la consommation, reclasser les 50 premiers passages denses avec Cohere `rerank-v5.0-pro` et n'en envoyer que 5 donne-t-il au moins autant de réponses justes (`correct`) qu'envoyer les 20 premiers passages denses, à générateur constant ?

**Réponse :** les deux variantes font jeu égal, sans qu'on puisse conclure dans un sens ou dans l'autre. Pour les trois générateurs, B est à −0,4 à −2,0 points de A, et l'intervalle contient 0 : **verdict non concluant**. La non-infériorité à −3 points n'est établie pour aucun (bornes basses de −5,6 à −6,5 points), comme le protocole le laissait prévoir ; une perte de plus de 3 points n'est pas établie non plus. Ce que B change sûrement, c'est le coût : **2,6 fois moins de tokens**, mais **0,3 à 0,4 s de plus par question** en médiane, l'appel à Cohere (0,46 s) coûtant plus que ce que la génération gagne à lire 5 passages au lieu de 20.

## Provenance

| Élément | Valeur |
|---|---|
| Commit de gel des variantes | « Geler la 005 avant le run final sur le test » (`0102fde`), dépôt propre (`--final`), commit relevé au démarrage et enregistré dans chaque `summary.json` (`run.commit`) |
| Golden set | `domains/droit-consommation/golden/rag-qa/v1`, `items.jsonl` sha256 `1df25172a69b336e203896ab60a6bfbff8d2d0e18cc90f86e299a8a34ea5b5c3`, 150 items `test`, les mêmes que les 002 à 004 |
| Données | `domains/droit-consommation/data/v1/articles.jsonl` sha256 `ed9bb9ffd05103792132a35f1fab91c0c3dc07a719c7764ab7269eb85851d9d2` (Code de la consommation, LEGI, état au 13/07/2025) |
| Spec de notation | `evals/spec/rag-qa/v1` |
| Lockfile | `uv.lock` sha256 `f4fc41d161d1b6e708df7ffc09939f5f58023e6053daf52d664bad6ad5b453df` |
| Baseline (A) | Le B gelé de la 004 : RAG naïf de la 002 avec top-k = 20 |
| Variante (B) | 50 premiers passages denses reclassés par Cohere `rerank-v5.0-pro` (API `POST /v2/rerank`, clé d'essai, version servie le 2026-11-09), 5 envoyés ; `rag/python/src/ailab_rag/reranking.py` sha256 `5bcea9b2fb93ed027b5c3fe1b55789b606a8979db939a5ad7d3ec6914ce5e0d4` |
| Prompts | `rag/python/src/ailab_rag/prompting.py` sha256 `e84ea88df6323ce435e4a4ec477b575eb734fde2b43fe71b5177539951881daf`, ceux du gel de la 002 |
| Campagne | `python/src/exp005_rag/campaign.py` sha256 `3c22bb294af3ca5424b9821081ff43d5c3bac301c2211eac0d062b6e10d0e2f7` |
| Boucle | Pydantic AI 2.65.0, sortie imposée par l'outil de sortie, aucune nouvelle tentative sur une sortie invalide, `temperature = 0`, 4 exécutions à la fois |
| Plan | 150 items `test` × 2 variantes × k = 3, soit 900 exécutions par générateur ; un classement Cohere par question, calculé avant la campagne de Mistral Small et lu dans le cache par les deux autres générateurs |
| Runs | `runs/final-test-mistral-small-2603` (le 2026-11-09 de 11:43 à 12:02, reclassement compris, avec Langfuse), `runs/final-test-ministral-14b-2512` et `runs/final-test-gemini-3.5-flash-lite` (de 12:19 à 12:25, en parallèle, **sans Langfuse**, voir Limites) |
| Calcul | `ailab_rag.campaign.summarize` (`summary.json` de chaque run) ; verdict de `ailab_evals.paired.aggregate` |

Générateurs : `mistral:mistral-small-2603`, `mistral:ministral-14b-2512`, `google:gemini-3.5-flash-lite`, identifiants vérifiés le 2026-11-09 (API Mistral `/v1/models`, API Google `v1beta/models`), `temperature = 0`.

## Verdict par générateur

La règle a été fixée avant le run : B est meilleure si la borne basse de l'IC à 95 % du delta apparié de `correct` est au-dessus de 0, moins bonne si la borne haute est en dessous, non concluant sinon. Lecture de non-infériorité, fixée avant le run : B ne fait pas moins bien de plus de 3 points si la borne basse est au-dessus de −0,03.

| Générateur | `correct` A | `correct` B | Delta B − A | IC 95 % | Verdict | Non-infériorité à −3 points |
|---|---|---|---|---|---|---|
| `mistral-small-2603` | 0,847 | 0,833 | **−0,013** | [−0,056 ; +0,029] | **non concluant** | non établie |
| `ministral-14b-2512` | 0,840 | 0,836 | **−0,004** | [−0,056 ; +0,047] | **non concluant** | non établie |
| `gemini-3.5-flash-lite` | 0,878 | 0,858 | **−0,020** | [−0,065 ; +0,025] | **non concluant** | non établie |

Aucune erreur d'exécution ni sortie illisible sur les 2 700 exécutions.

**Ce que les intervalles permettent de dire.** Pour aucun générateur, B ne fait moins bien que A de plus de 3 points de façon établie (bornes hautes au-dessus de −3 points), mais la non-infériorité ne l'est pas non plus : l'expérience ne tranche pas, à ±5 points près environ. Pour Gemini Flash-Lite, la borne haute (+2,5 points) est sous les 3 points qui comptent : un gain utile de B est exclu.

**A reproduit la 004.** A est le B de la 004 sur le même `test` : 0,847 (0,838 dans la 004) pour Mistral Small, 0,840 (0,840) pour Ministral 14B, 0,878 (0,864) pour Gemini Flash-Lite. Les écarts, au plus 1,4 point, viennent de l'indéterminisme résiduel des API à température 0.

## Temps de réponse et coût

Médiane (90e centile), en secondes. Génération : durée de l'appel au générateur, par exécution. Reclassement : durée de chacun des 150 appels à Cohere, attente imposée par la clé d'essai exclue (0,46 s en moyenne). La recherche dense, commune aux deux variantes, n'est pas comptée.

| Générateur | Génération A (20 passages) | Génération B (5 passages) | Reclassement B | **Total A** | **Total B (approx.)** | Tokens A | Tokens B |
|---|---|---|---|---|---|---|---|
| `mistral-small-2603` | 0,84 (1,37) | 0,78 (1,22) | 0,46 (0,52) | **0,84** | **≈ 1,24** | 3 962 | 1 531 |
| `ministral-14b-2512` | 1,50 (2,42) | 1,31 (2,02) | 0,46 (0,52) | **1,50** | **≈ 1,77** | 3 972 | 1 540 |
| `gemini-3.5-flash-lite` | 0,77 (0,93) | 0,73 (0,89) | 0,46 (0,52) | **0,77** | **≈ 1,19** | 4 106 | 1 594 |

- **Lire 20 passages au lieu de 5 coûte peu de temps de génération** : 0,04 à 0,19 s de plus en médiane, alors que le prompt est 2,6 fois plus long.
- **L'appel à Cohere coûte plus que ce gain** : B est plus lent de 0,3 à 0,4 s par question en médiane, soit +18 % (Ministral 14B) à +55 % (Gemini Flash-Lite).
- **Le gain de B est en tokens d'entrée** : environ 2 450 de moins par question, au prix d'un appel à Cohere dont le tarif payant n'est pas publié (vérifié le 2026-11-08).
- Le total de B additionne deux médianes mesurées séparément : c'est un ordre de grandeur, pas la médiane exacte de la somme. Les temps dépendent de la charge des API au moment du run ; A et B tournaient en même temps, dans la même campagne.

## Métriques secondaires

Elles ne portent pas le verdict.

| Métrique | Mistral Small A | B | Ministral 14B A | B | Gemini Flash-Lite A | B |
|---|---|---|---|---|---|---|
| `correct`, items avec réponse | 0,908 | 0,887 | 0,882 | 0,877 | 0,874 | 0,850 |
| `retrieval_miss` | 0,055 | 0,071 | 0,063 | 0,076 | 0,087 | 0,102 |
| `generation_miss` | 0,037 | 0,042 | 0,055 | 0,047 | 0,039 | 0,047 |
| `hallucination` (items sans réponse) | 0,493 | 0,464 | 0,391 | 0,391 | 0,101 | 0,101 |
| `false_abstention` | 0,008 | 0,021 | 0,018 | 0,026 | 0,089 | 0,121 |
| Citations, précision / rappel | 0,78 / 0,89 | 0,79 / 0,89 | 0,77 / 0,88 | 0,76 / 0,85 | 0,87 / 0,86 | 0,87 / 0,83 |

**Récupération**, identique pour les trois générateurs (items avec réponse) : rang 1, 0,43 (A, dense) contre 0,67 (B, reclassé) ; top-5, 0,81 contre 0,91. Mais A envoie 20 passages : tous les articles attendus sont dans le contexte de B et pas dans celui de A pour 2 items, et l'inverse pour 4.

**Delta par type d'item :**

| Générateur | Items avec réponse (127) | Items sans réponse (23) |
|---|---|---|
| `mistral-small-2603` | −0,021 | +0,029 |
| `ministral-14b-2512` | −0,005 | 0,000 |
| `gemini-3.5-flash-lite` | −0,024 | 0,000 |

**`correct` par mode, A → B :**

| Mode | Mistral Small | Ministral 14B | Gemini Flash-Lite |
|---|---|---|---|
| `direct` (30) | 0,94 → 0,89 | 0,87 → 0,87 | 0,88 → 0,87 |
| `reference` (22) | 1,00 → 1,00 | 1,00 → 0,95 | 0,94 → 0,95 |
| `paraphrase` (30) | 0,94 → 0,93 | 0,86 → 0,90 | 0,92 → 0,86 |
| `multi_article` (22) | 0,62 → 0,61 | 0,70 → 0,65 | 0,61 → 0,56 |
| `lost_context` (23) | 1,00 → 0,99 | 1,00 → 1,00 | 1,00 → 1,00 |
| `unanswerable` (23) | 0,51 → 0,54 | 0,61 → 0,61 | 0,90 → 0,90 |

## Lecture

- **Le reclassement remplace la profondeur, à peu près.** Avec 5 passages bien classés, les générateurs répondent presque aussi juste qu'avec 20 passages bruts (à 0,4 à 2 points près). La récupération l'annonçait : 0,91 de rappel au top-5 reclassé contre 0,92 au top-20 dense au `dev`.
- **L'hypothèse sur les réponses inventées n'est pas confirmée.** Envoyer 5 passages au lieu de 20 ne fait pas moins inventer sur les questions sans réponse : 0,49 → 0,46 pour Mistral Small, aucun changement pour les deux autres. Moins d'articles voisins ne veut pas dire moins de tentation : le reclassement garde justement les voisins qui ressemblent le plus à une réponse (constat du run 0, sur rq-146).
- **Le choix entre A et B est un choix de coût, pas de qualité.** A est plus rapide (pas d'appel en plus) ; B consomme 2,6 fois moins de tokens d'entrée et ajoute un fournisseur. À ce volume de tokens (4 000 par question), la latence penche pour A ; avec des passages plus longs ou un contexte limité, B prendrait l'avantage.
- **Le levier qui reste est l'abstention.** Ni 20 passages (004) ni 5 passages reclassés (005) ne font moins inventer Mistral Small (près d'une réponse sur deux aux questions sans réponse) ni Ministral 14B (0,39).

## Écarts par rapport au `dev`

Au run 0 du `dev` (Mistral Small), B perdait 4,7 points [−11,3 ; +2,0], surtout par des réponses inventées sur 2 des 6 items sans réponse (0,28 → 0,50). Sur le `test`, qui en compte 23, les réponses inventées baissent légèrement (0,49 → 0,46) et l'écart se réduit à −1,3 point. Le `dev` n'avait pas assez d'items sans réponse pour juger ce point, comme dans la 004.

## Dispersion

| Générateur | s_d | Couples item × variante instables sur 3 répétitions | Items où B > A / B < A |
|---|---|---|---|
| `mistral-small-2603` | 0,264 | 12 / 300 | 9 / 10 |
| `ministral-14b-2512` | 0,321 | 3 / 300 | 8 / 9 |
| `gemini-3.5-flash-lite` | 0,282 | 9 / 300 | 6 / 12 |

Avec s_d ≈ 0,29, le MDE sur 150 items est d'environ 6,7 points, et la demi-largeur des intervalles d'environ 4,7 points. Établir une non-infériorité à −3 points aurait demandé un delta observé d'au moins +1,7 point environ.

## Limites

- **Ministral 14B et Gemini Flash-Lite sans Langfuse.** Lancés après Mistral Small avec Langfuse, ils ont échoué deux fois à leur vérification de départ, avant toute exécution : la machine virtuelle de Docker n'avait que 2,35 Go de mémoire pour une pile Langfuse qui en occupe environ 2 à vide, et ses conteneurs redémarraient sous la charge. Ils ont été relancés sans Langfuse, sur le même commit, à la décision du propriétaire. Journaux des lancements ratés : `runs/incident-2026-11-09/`. Les `executions.jsonl` et `summary.json` font foi ; les traces de Mistral Small sont elles-mêmes incomplètes (`run.langfuse_flushed: false`).
- **Docker redémarré avant le run.** Au redémarrage, deux conteneurs d'un autre projet occupaient les ports de Langfuse (5432, 9000) ; ils ont été arrêtés, et la pile Langfuse recréée en gardant ses volumes.
- **B moins travaillée que A** : A a reçu deux cycles dans la 002, B aucun (gel au run 0 du `dev`).
- **Le modèle de reclassement a été choisi sur le `dev`** parmi trois candidats.
- **Clé d'essai Cohere** : conditions d'usage commercial non vérifiées ; le modèle servi peut changer côté Cohere, mais les notes de l'expérience sont figées dans le cache.
- **Temps de réponse** : mesurés depuis un seul poste, avec 4 exécutions à la fois et deux générateurs en parallèle pour Ministral 14B et Gemini Flash-Lite ; ils dépendent de la charge des API ce jour-là. Le run 0 du `dev` n'a pas de temps de génération (mesure ajoutée avant le gel).
- **Les limites de la 002 s'appliquent** : un seul corpus, questions rédigées par un LLM, golden set relu avec l'aide d'un LLM.
