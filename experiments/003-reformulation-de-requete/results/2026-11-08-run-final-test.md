# 003 — Run final sur le split `test` (2026-11-08)

**Question :** sur le Code de la consommation, reformuler la question dans la langue du code avant la recherche augmente-t-il le taux de réponses justes (`correct`) d'un RAG naïf, à générateur constant ?

**Réponse :** non. Pour les trois générateurs, le delta vaut −0,7 à −0,9 point et l'intervalle à 95 % contient 0 : **verdict non concluant**. Les trois bornes hautes (+4,1 à +4,9 points) restent sous les 5 points fixés comme plus petit écart qui compte : **un gain utile est exclu** sur cet échantillon. La reformulation change le top-5 de 108 questions sur 150. Elle aide la paraphrase et la référence, nuit autant au contexte perdu et aux questions directes, et le bilan est nul.

## Provenance

| Élément | Valeur |
|---|---|
| Commit de gel des variantes | « Geler la 003 avant le run final sur le test » (`13e7cab`). Run lancé sur `8e2e2c9` (correctif de l'incident du premier lancement, voir Limites), dépôt propre (`--final`), commit enregistré dans chaque `summary.json` (`run.commit`) |
| Golden set | `domains/droit-consommation/golden/rag-qa/v1`, `items.jsonl` sha256 `1df25172a69b336e203896ab60a6bfbff8d2d0e18cc90f86e299a8a34ea5b5c3`, 150 items `test`, les mêmes que la 002 |
| Données | `domains/droit-consommation/data/v1/articles.jsonl` sha256 `ed9bb9ffd05103792132a35f1fab91c0c3dc07a719c7764ab7269eb85851d9d2` (Code de la consommation, LEGI, état au 13/07/2025) |
| Spec de notation | `evals/spec/rag-qa/v1` |
| Lockfile | `uv.lock` sha256 `99f6d13ee7cfde412c01898dc6e3e42702ef9160ab31f45fe760d59ce0c3145f` |
| Baseline (A) | Le RAG naïf gelé de la 002 : un passage par article, `mistral-embed`, cosinus exact, top-k = 5, prompts du gel de la 002 |
| Variante (B) | Question reformulée par `google:gemini-3.8-flash` (prompt `REFORMULATE_KEEP`, `rag/python/src/ailab_rag/rewriting.py` sha256 `7f65485e8361f3cd3ff49b056feb094f85ef645cd3e6ff85fd09c008194e107f`, température 0) ; recherche avec la question et avec la reformulation, 50 passages chacune, fusion RRF (k = 60), top-5 ; le générateur reçoit la question d'origine |
| Campagne | `python/src/exp003_rag/campaign.py` sha256 `eff05d6fc360f38c585eb8dd5e9d96fffd7ad2113f02b86d6f4026acce47f141` |
| Boucle | Pydantic AI 2.65.0, sortie imposée par l'outil de sortie, aucune nouvelle tentative sur une sortie invalide, `temperature = 0` |
| Plan | 150 items `test` × 2 variantes × k = 3, soit 900 exécutions par générateur ; une seule reformulation par question, calculée avant la campagne et partagée par les trois générateurs |
| Runs | `runs/final-test-mistral-small-2603`, `runs/final-test-ministral-14b-2512`, `runs/final-test-gemini-3.5-flash-lite`, le 2026-11-08 entre 12:11 et 12:32 (heure de Paris). Traces dans Langfuse, sessions du même nom ; une grande partie des envois a été perdue (voir Limites) |
| Calcul | `ailab_rag.campaign.summarize` sur les `executions.jsonl`, résumés recalculés hors ligne (voir Limites) ; verdict de `ailab_evals.paired.aggregate` |

Générateurs : `mistral:mistral-small-2603`, `mistral:ministral-14b-2512`, `google:gemini-3.5-flash-lite`, identifiants vérifiés le 2026-11-07 pour la 002. Réécrivain : `google:gemini-3.8-flash`, qui a répondu pour les 150 questions.

## Verdict par générateur

La règle a été fixée avant le run : B est meilleure si la borne basse de l'IC à 95 % du delta apparié de `correct` est au-dessus de 0, pire si la borne haute est en dessous, non concluant sinon.

| Générateur | `correct` A | `correct` B | Delta B − A | IC 95 % | Verdict |
|---|---|---|---|---|---|
| `mistral-small-2603` | 0,791 | 0,782 | **−0,009** | [−0,059 ; +0,042] | **non concluant** |
| `ministral-14b-2512` | 0,767 | 0,760 | **−0,007** | [−0,062 ; +0,049] | **non concluant** |
| `gemini-3.5-flash-lite` | 0,791 | 0,782 | **−0,009** | [−0,059 ; +0,041] | **non concluant** |

Aucune erreur d'exécution ni sortie illisible sur les 2 700 exécutions. Les trois bornes hautes sont sous +0,05 : un gain de 5 points ou plus est exclu à 95 % pour chacun des trois générateurs.

**A reproduit la 002.** A est le RAG naïf de la 002, sur le même `test` : 0,791 contre 0,791 (Mistral Small), 0,767 contre 0,762 (Ministral 14B), 0,791 contre 0,787 (Gemini Flash-Lite). Les écarts, au plus 0,5 point, viennent de l'indéterminisme résiduel des API à température 0.

## Métriques secondaires

Elles ne portent pas le verdict. Les tokens se comparent entre variantes d'un même générateur, jamais d'un fournisseur à l'autre.

| Métrique | Mistral Small A | B | Ministral 14B A | B | Gemini Flash-Lite A | B |
|---|---|---|---|---|---|---|
| `correct`, items avec réponse | 0,822 | 0,814 | 0,811 | 0,777 | 0,761 | 0,759 |
| `retrieval_miss` | 0,150 | 0,160 | 0,165 | 0,176 | 0,207 | 0,205 |
| `generation_miss` | 0,029 | 0,026 | 0,024 | 0,047 | 0,031 | 0,037 |
| `hallucination` (items sans réponse) | 0,377 | 0,391 | 0,478 | 0,333 | 0,043 | 0,087 |
| `false_abstention` | 0,045 | 0,026 | 0,052 | 0,068 | 0,194 | 0,160 |
| Citations, précision / rappel | 0,71 / 0,77 | 0,68 / 0,76 | 0,73 / 0,79 | 0,69 / 0,76 | 0,83 / 0,74 | 0,82 / 0,74 |
| Tokens du générateur par exécution | 1 282 | 1 316 | 1 292 | 1 325 | 1 339 | 1 374 |

**Récupération**, identique pour les trois générateurs (items avec réponse) :

| | Rang 1 | Top-3 | Top-5 |
|---|---|---|---|
| A, RAG naïf | 0,43 | 0,72 | 0,81 |
| B, reformulation + RRF | 0,48 | 0,72 | 0,80 |

B remonte l'article attendu au rang 1 plus souvent (+5 points), mais le rappel au top-5, le seul qui compte pour un contexte de 5 passages, ne bouge pas. La reformulation change le top-5 de **108 items sur 150**. Sur les items avec réponse, B retrouve tous les articles attendus pour 6 items que A ratait, et en perd 7 que A trouvait.

**`correct` par mode, A → B :**

| Mode | Rappel top-5, A → B | Mistral Small | Ministral 14B | Gemini Flash-Lite |
|---|---|---|---|---|
| `direct` (30) | 0,87 → 0,80 | 0,90 → 0,84 | 0,87 → 0,77 | 0,83 → 0,82 |
| `reference` (22) | 0,77 → 0,82 | 0,86 → 0,91 | 0,83 → 0,94 | 0,77 → 0,82 |
| `paraphrase` (30) | 0,87 → 0,90 | 0,84 → 0,91 | 0,89 → 0,87 | 0,82 → 0,82 |
| `multi_article` (22) | 0,57 → 0,61 | 0,50 → 0,53 | 0,45 → 0,45 | 0,38 → 0,45 |
| `lost_context` (23) | 0,91 → 0,83 | 0,96 → 0,83 | 0,96 → 0,83 | 0,94 → 0,83 |
| `unanswerable` (23) | — | 0,62 → 0,61 | 0,52 → 0,67 | 0,96 → 0,91 |

Chaque mode compte 22 à 30 items : un écart de 5 points y représente un ou deux items.

## Lecture

- **La reformulation déplace les réussites sans en ajouter.** Elle gagne sur la paraphrase et la référence, ce que la pré-étude laissait attendre, et perd autant sur le contexte perdu (−12 à −13 points pour les trois générateurs) et les questions directes.
- **Pourquoi elle perd.** Sur les 7 items dont B perd l'article attendu, les reformulations sont fidèles mais longues : elles ajoutent un vocabulaire juridique générique (« droit de rétractation », « obligation précontractuelle d'information », « procédure de traitement du surendettement ») qui attire des articles voisins. La fusion avec la question d'origine (cycle 2) limite la perte sans la supprimer.
- **Le générateur ne change rien au bilan.** Les trois générateurs voient la même récupération et finissent au même delta, à 0,2 point près. Le levier agit sur la récupération, et la récupération ne gagne rien au top-5.
- **La pré-étude surestimait le gain.** Sur le `dev`, B gagnait +4 points au top-5 (reformulation seule) et +2 points de `correct` (cycle 2). Sur le `test`, le top-5 recule d'un point et `correct` de moins d'un point. C'est l'optimisme attendu d'une sélection du meilleur levier parmi huit configurations, sur 44 items.
- **Coût.** Un appel à Gemini 3.8 Flash par question, et environ 35 tokens de plus par exécution côté générateur, pour aucun gain.

## Écarts par rapport au `dev`

Au cycle 2 du `dev` (Mistral Small), B gagnait +0,02 [−0,08 ; +0,12], avec un gain sur les questions à plusieurs articles (0,50 → 0,71). Sur le `test`, ce gain se réduit à 0,50 → 0,53. Le `dev` compte 50 items, dont 8 à plusieurs articles : l'écart reste dans la dispersion attendue.

## Dispersion

| Générateur | s_d | Couples item × variante instables sur 3 répétitions | Items où B > A / B < A |
|---|---|---|---|
| `mistral-small-2603` | 0,314 | 12 / 300 | 10 / 11 |
| `ministral-14b-2512` | 0,342 | 4 / 300 | 10 / 10 |
| `gemini-3.5-flash-lite` | 0,309 | 8 / 300 | 10 / 11 |

La puissance prévue au protocole (MDE ≈ 9,6 points, avec s_d = 0,417 au `dev`) était pessimiste : sur le `test`, s_d ≈ 0,32 et la demi-largeur des intervalles est d'environ 5 points. C'est ce qui permet d'exclure un gain de 5 points.

## Limites

- **Arrêt pendant l'envoi à Langfuse.** Les trois processus ont écrit leurs 900 exécutions, puis sont restés bloqués à l'envoi des traces : le serveur Langfuse auto-hébergé ne répondait plus (dépassements de délai, redémarrage de son conteneur web). Celui de Mistral Small a été coupé par la fin de la session de travail, ceux de Ministral 14B et de Gemini Flash-Lite ont été arrêtés à la main. Aucun n'a écrit son `summary.json` : les trois ont été recalculés hors ligne à partir des `executions.jsonl`, avec la même fonction `summarize` et sans aucun appel d'API, et le champ `run.summary_recomputed` le signale. Les `executions.jsonl` font foi ; une grande partie des traces et des scores manque dans Langfuse.
- **Lancement en deux temps.** Ministral 14B et Gemini Flash-Lite devaient démarrer après Mistral Small, dans la même commande ; coupés avec elle avant d'avoir commencé, ils ont été lancés ensuite, sur le même commit et sans rien changer. Chaque générateur a fait un seul run sur le `test`.
- **Incident au premier lancement** (avant ce run) : les reformulations du `test` ont échoué au démarrage (boucles asyncio concurrentes sur un même client Gemini). Aucune exécution n'avait été enregistrée ; le correctif `8e2e2c9` ne change ni les variantes ni les reformulations.
- **Coût de la reformulation non mesuré.** Le protocole prévoyait les tokens et la latence de Gemini 3.8 Flash ; le cache des reformulations ne garde que leur texte. Le coût se résume ici à un appel par question.
- **Deux fournisseurs dans B** pour les générateurs Mistral.
- **Les limites de la 002 s'appliquent** : un seul corpus, questions rédigées par un LLM, golden set relu avec l'aide d'un LLM.
