# 002 — Run final sur le split `test` (2026-11-07)

**Question :** sur le Code de la consommation, de combien un RAG naïf (B) augmente-t-il le taux de réponses justes par rapport au même modèle sans récupération (A) ?

**Réponse :** de **37 à 44 points de `correct`** selon le modèle, avec des intervalles à 95 % tous au-dessus de 27 points. Pour les trois modèles, **B est meilleure**. Le RAG naïf échoue surtout à la récupération : quand B se trompe sur une question qui a une réponse, l'article attendu manquait au contexte dans 15 à 21 % des cas, contre 2 à 3 % où il était là et la réponse était fausse.

## Provenance

| Élément | Valeur |
|---|---|
| Commit de gel des variantes | « Geler la 002 avant le run final sur le test » (`8d082ad`). Run lancé sur `f05f78b3bdd9d0443ecd3992aa8fe9984161c221` (changement de modèles, voir Limites), dépôt propre (`--final`), commit enregistré dans chaque `summary.json` (`run.commit`) |
| Golden set | `domains/droit-consommation/golden/rag-qa/v1`, `items.jsonl` sha256 `1df25172a69b336e203896ab60a6bfbff8d2d0e18cc90f86e299a8a34ea5b5c3`, 150 items `test` |
| Données | `domains/droit-consommation/data/v1/articles.jsonl` sha256 `ed9bb9ffd05103792132a35f1fab91c0c3dc07a719c7764ab7269eb85851d9d2` (Code de la consommation, LEGI, état au 13/07/2025) |
| Spec de notation | `evals/spec/rag-qa/v1` |
| Lockfile | `uv.lock` sha256 `bffb65f130fc6f75dc11313213d3e4e3d3ddc7556293a136ceb7727dad63beb1` |
| Prompts | `python/src/exp002_rag/prompting.py` sha256 `af87a27b1782c6467998cf2dd44819cf289a07d23c6cb73f00d6aaf949c2f9c1` : prompt système avec la consigne d'abstention du cycle 1 ; A pose la question seule ; B ajoute la phrase d'ancrage du cycle 2 et les extraits |
| RAG naïf | un passage par article (2 155 passages), `mistral-embed`, similarité cosinus exacte, top-k = 5 |
| Boucle | Pydantic AI 2.65.0, sortie imposée par l'outil de sortie, aucune nouvelle tentative sur une sortie invalide, `temperature = 0` |
| Plan | 150 items `test` × 2 variantes × k = 3, soit 900 exécutions par modèle |
| Runs | `runs/final-test-mistral-small-2603`, `runs/final-test-ministral-14b-2512`, `runs/final-test-gemini-3.5-flash-lite`, lancés le 2026-11-07 entre 15:10 et 15:20 (heure de Paris). Traces et scores dans Langfuse, sessions du même nom ; une partie des envois a été perdue (voir Limites) |
| Calcul | `exp002_rag.campaign.summarize` (`summary.json` de chaque run) ; verdict de `ailab_evals.paired.aggregate` |

| Modèle | Identifiant vérifié le 2026-11-07 | Réglages envoyés |
|---|---|---|
| Mistral Small | `mistral:mistral-small-2603` (API Mistral, `/v1/models`) | `temperature = 0` |
| Ministral 14B | `mistral:ministral-14b-2512` (API Mistral, `/v1/models`) | `temperature = 0` |
| Gemini Flash-Lite | `google:gemini-3.5-flash-lite` (API Google, `v1beta/models`) | `temperature = 0` |

## Verdict par modèle

La règle a été fixée avant le run : B est meilleure si la borne basse de l'IC à 95 % du delta apparié de `correct` est au-dessus de 0.

| Modèle | `correct` A | `correct` B | Delta B − A | IC 95 % | Verdict |
|---|---|---|---|---|---|
| `mistral-small-2603` | 0,418 | 0,791 | **+0,373** | [+0,276 ; +0,470] | **B meilleure** |
| `ministral-14b-2512` | 0,320 | 0,762 | **+0,442** | [+0,354 ; +0,531] | **B meilleure** |
| `gemini-3.5-flash-lite` | 0,420 | 0,787 | **+0,367** | [+0,273 ; +0,460] | **B meilleure** |

Les trois intervalles excluent largement le plus petit écart qui compte (10 points). Aucune erreur d'exécution ni sortie illisible sur les 2 700 exécutions.

## Métriques secondaires

Elles ne portent pas le verdict. Les tokens se comparent entre variantes d'un même modèle, jamais d'un fournisseur à l'autre.

| Métrique | Mistral Small A | B | Ministral 14B A | B | Gemini Flash-Lite A | B |
|---|---|---|---|---|---|---|
| `correct`, items avec réponse | 0,367 | 0,824 | 0,257 | 0,798 | 0,346 | 0,756 |
| `hallucination` (items sans réponse) | 0,304 | 0,391 | 0,333 | 0,435 | 0,174 | 0,043 |
| `false_abstention` | 0,113 | 0,052 | 0,139 | 0,055 | 0,276 | 0,194 |
| Citations, précision / rappel | 0,19 / 0,17 | 0,72 / 0,77 | 0,20 / 0,18 | 0,72 / 0,79 | 0,29 / 0,21 | 0,82 / 0,73 |
| Tokens par exécution | 354 | 1 282 | 372 | 1 291 | 378 | 1 338 |

**Diagnostic de B** (items avec réponse) :

| Modèle | `correct` | `retrieval_miss` | `generation_miss` |
|---|---|---|---|
| `mistral-small-2603` | 0,82 | 0,15 | 0,03 |
| `ministral-14b-2512` | 0,80 | 0,18 | 0,02 |
| `gemini-3.5-flash-lite` | 0,76 | 0,21 | 0,03 |

La récupération est la même pour les trois modèles : l'article attendu est au rang 1 dans 43 % des cas, dans le top-3 dans 72 %, dans le top-5 dans 81 %.

**`correct` par mode, A → B :**

| Mode | Mistral Small | Ministral 14B | Gemini Flash-Lite |
|---|---|---|---|
| `direct` (30) | 0,31 → 0,90 | 0,20 → 0,87 | 0,39 → 0,82 |
| `reference` (22) | 0,48 → 0,85 | 0,32 → 0,82 | 0,48 → 0,77 |
| `paraphrase` (30) | 0,36 → 0,86 | 0,27 → 0,88 | 0,30 → 0,81 |
| `multi_article` (22) | 0,18 → 0,52 | 0,06 → 0,41 | 0,14 → 0,36 |
| `lost_context` (23) | 0,52 → 0,96 | 0,45 → 0,96 | 0,42 → 0,96 |
| `unanswerable` (23) | 0,70 → 0,61 | 0,67 → 0,57 | 0,83 → 0,96 |

## Lecture

- **Le RAG naïf apporte beaucoup, à tous les modèles testés.** Sans récupération, les modèles répondent juste de mémoire à 26 à 37 % des questions qui ont une réponse ; avec, à 76 à 82 %.
- **Plus le modèle sait peu, plus il gagne** : Ministral 14B, qui sait le moins (0,257 sans contexte), gagne le plus (+44 points).
- **La récupération est le premier levier de la série.** Elle explique 15 à 21 % d'échecs, la génération 2 à 3 %. L'article attendu n'est en tête que dans 43 % des cas.
- **Le mode « plusieurs articles » reste faible** (0,36 à 0,52) : il faut retrouver deux articles dans un top-5.
- **Les questions sans réponse divisent les modèles.** Avec le contexte, les modèles Mistral inventent un peu plus qu'à vide (0,30 → 0,39 et 0,33 → 0,44) : des extraits voisins leur donnent de quoi répondre à tort. Gemini Flash-Lite s'abstient au contraire presque toujours (0,04 d'hallucination), au prix de plus de fausses abstentions.

## Écarts par rapport au `dev`

Sur le `dev`, Gemini Flash-Lite gagnait moins (+0,22 au run 0) parce qu'il répondait mieux à vide (0,48). Sur le `test`, son score à vide est de 0,42 et son gain de +0,37. Le `dev` compte 50 items : la différence reste dans la dispersion attendue entre deux échantillons de cette taille.

## Dispersion

| Modèle | s_d | Couples item × variante instables sur 3 répétitions |
|---|---|---|
| `mistral-small-2603` | 0,601 | 18 / 300 |
| `ministral-14b-2512` | 0,548 | 12 / 300 |
| `gemini-3.5-flash-lite` | 0,579 | 30 / 300 |

Avec s_d ≈ 0,58, le MDE sur 150 items est d'environ 13 points, au-dessus des 10 points visés. Sans conséquence ici : les écarts mesurés sont trois fois plus grands.
