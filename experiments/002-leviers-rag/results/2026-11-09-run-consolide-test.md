# 002 — Run consolidé sur le split `test` du golden set v4 (2026-11-09)

**Question :** sur le golden set v4, de combien chaque levier gelé fait-il varier `correct` : seul, contre le RAG naïf, et en plus des leviers précédents ?

**Réponse :** deux leviers font gagner des réponses justes, les trois autres non.

- **Le RAG naïf**, contre le modèle seul : +28 à +44 points, avec les trois modèles.
- **20 passages au lieu de 5** : +6,8 points avec Ministral 14B et +10,4 avec Gemini Flash-Lite. C'est non concluant avec Mistral Small (+6,1 points) : l'IC non corrigé exclut 0, mais la correction de Holm le rend non concluant.
- **La reformulation de la question** ne fait rien gagner : −0,3 à +1,3 point.
- **Le reclassement Cohere**, en plus des 20 passages, ne fait rien gagner non plus : −1,0 à −2,1 points, mais avec 2,5 fois moins de tokens. Comparé aux 5 passages denses (lecture nouvelle), il gagne +5,8 points avec Ministral et +8,3 avec Gemini, et reste non concluant avec Mistral Small.
- **La consigne d'abstention** ne fait plus moins inventer Mistral Small : −3,3 points, non concluant, quand l'étape 5 mesurait −9,2. Elle nuit toujours à Gemini, qui s'abstient à tort 15 points de plus et perd 9 points de `correct`.

## Provenance

| Élément | Valeur |
|---|---|
| Commit de gel | « Geler le run consolidé de la 002 avant le run final sur le test » (`f836315`), dépôt propre (`--final`), commit enregistré dans chaque `summary.json` (`run.commit`) |
| Golden set | `domains/droit-consommation/golden/rag-qa/v4`, `items.jsonl` sha256 `3e12a0312384bdd4fd12140ebde41d78fe9d6d9f378d3c9a5c9aa2ac7c3f9f35`, 246 items `test` |
| Items écartés | Les 12 items `test` que l'audit de la v1 trouve répondus par le code (`golden/rag-qa/audit/v1-unanswerable.jsonl`, sha256 `456fa478e889ab57528b69b1483881b8b065e9bbd8ac0f8c4a95cc121235dcd4`) : ils n'ont pas tourné. Restent 234 items valides : 51 sans réponse, 183 avec réponse |
| Données | `domains/droit-consommation/data/v1/articles.jsonl` sha256 `ed9bb9ffd05103792132a35f1fab91c0c3dc07a719c7764ab7269eb85851d9d2` |
| Spec de notation | `evals/spec/rag-qa/v1` (§ 8 pour l'IC) ; correction de Holm et critères de l'étape 5 fixés par le protocole du README avant le run |
| Lockfile | `uv.lock` sha256 `462061c320a663572e9a439074fa7534770e83795a96da7a4ca615147f9aba76` |
| Configurations | Reprises telles quelles des paquets d'étape (`exp003_rag` à `exp006_rag`) par `exp002_leviers.configurations`. `closed_book`, `naive_rag` (5 passages), `query_rewrite` (reformulation `google:gemini-3.8-flash`, fusion RRF), `top_k_20`, `rerank_cohere` (`cohere:rerank-v5.0-pro`, 50 candidats vers 5), `abstain_strict` (20 passages et `STRICT_GROUNDING`) |
| Contrôle de reproduction | Avant le gel et au début de chaque run : 968 contextes sur 968 identiques à ceux des runs finaux des étapes, ordre compris, sur les caches seuls (`exp002_leviers.reproduction`) |
| Code | `python/src/exp002_leviers/` : `configurations.py` sha256 `faa6865b1c512a8c21b0ab55bfd4dc8dec17c7f55439fb717a6fadfa6efffa04`, `campaign.py` `59233ef45501c4f211d6973d100cd73cf0855b2c1f3651e35d654498261151a2`, `analysis.py` `6946f14e559e8fbb493f1bbd39a70a43125e7def34779e30ee7f7794f6d5142e`, `reproduction.py` `261c159b2ab2184df02b5388ec0817562c457cd559800b8a72fede26a13328b7` |
| Boucle | Pydantic AI 2.65.0, sortie imposée par l'outil de sortie, `temperature = 0`, 4 exécutions à la fois |
| Plan | 234 items × 6 configurations × k = 3, soit 4 212 exécutions par générateur |
| Runs | `runs/2026-11-09-<générateur>-test`, le 2026-11-09 de 20:23 à 20:43 (heure de Paris), sans Langfuse |
| Calcul | `exp002_leviers.analysis.analyze`, dans le `summary.json` de chaque run |

Générateurs : `mistral:mistral-small-2603`, `mistral:ministral-14b-2512`, `google:gemini-3.5-flash-lite`, à `temperature = 0`.

Une seule exécution a fini en erreur sur 12 636 : `closed_book` avec Gemini, comptée fausse (spec § 6).

## Verdict par comparaison et par modèle

Règle fixée avant le run. Pour chaque item, on prend la moyenne de `correct` sur ses 3 répétitions. On calcule ensuite le delta apparié B − A, son IC de Student à 95 % (spec § 8) et la p-value bilatérale du test t apparié. Les six p-values d'un modèle sont corrigées par Holm. Une comparaison conclut si sa p-value corrigée est sous 0,05. En gras : delta concluant après Holm.

| Comparaison (lecture) | Mistral Small | Ministral 14B | Gemini Flash-Lite |
|---|---|---|---|
| `naive_rag` − `closed_book` (isolée et cumulative) | 0,427 → 0,766, **+0,339** [+0,268 ; +0,410], p_holm < 0,001 | 0,325 → 0,764, **+0,439** [+0,369 ; +0,508], p_holm < 0,001 | 0,436 → 0,717, **+0,281** [+0,208 ; +0,354], p_holm < 0,001 |
| `query_rewrite` − `naive_rag` (isolée) | −0,003 [−0,038 ; +0,032], p_holm = 1 | +0,013 [−0,027 ; +0,052], p_holm = 1 | +0,009 [−0,032 ; +0,049], p_holm = 0,68 |
| `top_k_20` − `naive_rag` (isolée et cumulative) | 0,766 → 0,828, +0,061 [+0,014 ; +0,108], p_holm = 0,056 | 0,764 → 0,832, **+0,068** [+0,020 ; +0,116], p_holm = 0,027 | 0,717 → 0,821, **+0,104** [+0,062 ; +0,146], p_holm < 0,001 |
| `rerank_cohere` − `top_k_20` (cumulative) | −0,021 [−0,060 ; +0,017], p_holm = 0,84 | −0,010 [−0,050 ; +0,030], p_holm = 1 | −0,021 [−0,061 ; +0,018], p_holm = 0,58 |
| `rerank_cohere` − `naive_rag` (isolée, nouvelle) | +0,040 [−0,004 ; +0,084], p_holm = 0,30 | 0,764 → 0,822, **+0,058** [+0,013 ; +0,104], p_holm = 0,049 | 0,717 → 0,799, **+0,083** [+0,035 ; +0,130], p_holm = 0,002 |
| `abstain_strict` − `top_k_20` (cumulative) | −0,003 [−0,028 ; +0,023], p_holm = 1 | +0,007 [−0,022 ; +0,036], p_holm = 1 | 0,821 → 0,731, **−0,090** [−0,127 ; −0,053], p_holm < 0,001 |

**Holm change un seul verdict.** `top_k_20` − `naive_rag` avec Mistral Small : l'IC non corrigé exclut 0 (verdict de la spec : B meilleure), mais la p-value corrigée vaut 0,056. Les 17 autres verdicts sont les mêmes avec et sans correction. Pour `rerank_cohere` − `naive_rag` avec Ministral, la p-value corrigée (0,049) est tout juste sous le seuil.

### Consigne d'abstention : critères de l'étape 5

C'est la même règle qu'à l'étape 5, sans correction. Le critère principal est le delta apparié des réponses inventées sur les 51 questions sans réponse valides. La garde porte sur les abstentions à tort, sur les 183 questions avec réponse, avec une marge de +0,03.

| Générateur | Réponses inventées A → B | Delta [IC 95 %] | Abstentions à tort A → B | Delta [IC 95 %] | Verdict |
|---|---|---|---|---|---|
| `mistral-small-2603` | 0,222 → 0,190 | −0,033 [−0,093 ; +0,027] | 0,022 → 0,056 | +0,035 [+0,008 ; +0,061] | **non concluant** |
| `ministral-14b-2512` | 0,222 → 0,183 | −0,039 [−0,113 ; +0,035] | 0,024 → 0,024 | +0,000 [−0,013 ; +0,013] | **non concluant** |
| `gemini-3.5-flash-lite` | 0,020 → 0,020 | 0,000 [0,000 ; 0,000] | 0,148 → 0,299 | **+0,151** [+0,098 ; +0,205] | **B moins bonne** |

Pour Mistral Small, la garde ne tient pas : la borne haute (+0,061) dépasse la marge de 0,03. Même une baisse nette des réponses inventées aurait donné un compromis, pas un gain.

## Tableau des deltas de l'expérience

Il confronte le verdict de chaque étape, mesuré à son run final, à celui du run consolidé. Delta de `correct` en points, verdict après Holm pour le run consolidé.

| Levier | Étape (v1 ou v3) | Run consolidé (v4) | Même sens ? |
|---|---|---|---|
| RAG naïf (1) | +37,3 / +44,2 / +36,7 | **+33,9 / +43,9 / +28,1** | oui, les trois |
| Reformulation (2) | −0,9 / −0,7 / −0,9 | −0,3 / +1,3 / +0,9 | oui : rien |
| 20 passages (3) | +4,0 / **+7,3** / **+8,0** | +6,1 / **+6,8** / **+10,4** | oui, Mistral Small toujours non concluant |
| Reclassement, contre 20 passages (4) | −1,3 / −0,4 / −2,0 | −2,1 / −1,0 / −2,1 | oui : rien |
| Reclassement, contre 5 passages (4, nouvelle) | — | +4,0 / **+5,8** / **+8,3** | — |
| Consigne d'abstention (5) : `hallucination` | **−9,2** / −5,2 / −0,7 | −3,3 / −3,9 / 0,0 | non pour Mistral Small |
| Consigne d'abstention (5) : `false_abstention` | −0,3 / −0,3 / **+8,7** | +3,5 / 0,0 / **+15,1** | oui pour Gemini |

Ordre des valeurs dans chaque case : Mistral Small, Ministral 14B, Gemini Flash-Lite. Les deltas d'étape sont ceux des rapports d'étape. Pour l'étape 5, on lit le critère principal et la garde, pas `correct`.

## Métriques secondaires

Elles ne portent pas le verdict. Les valeurs sont calculées sur les 234 items valides, sauf mention contraire.

**`correct` par configuration :**

| Configuration | Mistral Small | Ministral 14B | Gemini Flash-Lite |
|---|---|---|---|
| `closed_book` | 0,427 | 0,325 | 0,436 |
| `naive_rag` | 0,766 | 0,764 | 0,717 |
| `query_rewrite` | 0,764 | 0,776 | 0,725 |
| `top_k_20` | 0,828 | 0,832 | **0,821** |
| `rerank_cohere` | 0,806 | 0,822 | 0,799 |
| `abstain_strict` | 0,825 | **0,839** | 0,731 |

**`correct` sur les 138 items valides du `test` de la v1, comparé aux étapes.** `top_k_20` donne 0,891 avec Mistral Small, 0,879 avec Ministral et 0,870 avec Gemini. Le même A donnait 0,894, 0,867 et 0,872 dans le rapport de l'étape 5. **Sur les 56 items nouveaux de la v4** (14 `comparison`, 12 `set`, 30 `false_premise`), `top_k_20` tombe à 0,685, 0,744 et 0,571 : ces items sont nettement plus durs.

**`correct` par mode** (Mistral Small / Ministral 14B / Gemini Flash-Lite) :

| Mode | `naive_rag` | `top_k_20` | `rerank_cohere` | `abstain_strict` |
|---|---|---|---|---|
| `direct` | 0,90 / 0,87 / 0,83 | 0,94 / 0,87 / 0,89 | 0,89 / 0,87 / 0,87 | 0,97 / 0,87 / 0,80 |
| `paraphrase` | 0,87 / 0,86 / 0,79 | 0,93 / 0,90 / 0,90 | 0,91 / 0,87 / 0,87 | 0,93 / 0,87 / 0,80 |
| `reference` | 0,82 / 0,82 / 0,77 | 1,00 / 1,00 / 0,91 | 1,00 / 0,97 / 0,95 | 1,00 / 1,00 / 0,95 |
| `lost_context` | 0,96 / 0,96 / 0,94 | 1,00 / 1,00 / 1,00 | 0,96 / 1,00 / 1,00 | 1,00 / 1,00 / 1,00 |
| `multi_article` | 0,50 / 0,39 / 0,38 | 0,65 / 0,70 / 0,61 | 0,64 / 0,65 / 0,58 | 0,67 / 0,68 / 0,47 |
| `comparison` | 0,29 / 0,26 / 0,29 | 0,50 / 0,52 / 0,48 | 0,50 / 0,48 / 0,50 | 0,45 / 0,52 / 0,40 |
| `set` | 0,56 / 0,42 / 0,64 | 0,64 / 0,61 / 0,75 | 0,50 / 0,58 / 0,67 | 0,72 / 0,78 / 0,64 |
| `false_premise` | 0,81 / 0,87 / 0,34 | 0,79 / 0,90 / 0,54 | 0,78 / 0,82 / 0,48 | 0,67 / 0,87 / 0,18 |
| `unanswerable` (valides) | 0,79 / 0,86 / 0,98 | 0,78 / 0,78 / 0,98 | 0,79 / 0,85 / 0,96 | 0,81 / 0,82 / 0,98 |

Les modes comptent de 12 à 51 items : un écart de moins de 15 à 20 points entre deux cases n'y est pas mesurable.

**Récupération, coût et temps :**

| Configuration | `evidence_recall@5` | Tokens par exécution (Mistral Small / Ministral / Gemini) | Génération, médiane |
|---|---|---|---|
| `closed_book` | — | 356 / 373 / 472 | 0,80 / 1,03 / 0,79 s |
| `naive_rag` | 0,770 | 1 287 / 1 296 / 1 342 | 0,79 / 0,95 / 0,78 s |
| `query_rewrite` | 0,781 | 1 310 / 1 320 / 1 366 | 0,77 / 0,94 / 0,78 s |
| `top_k_20` | 0,770 (5 premiers des 20) | 3 893 / 3 905 / 4 034 | 0,83 / 1,13 / 0,80 s |
| `rerank_cohere` | **0,888** | 1 526 / 1 537 / 1 587 | 0,77 / 0,98 / 0,77 s |
| `abstain_strict` | 0,770 (5 premiers des 20) | 3 942 / 3 957 / 4 084 | 0,80 / 1,10 / 0,80 s |

Le temps de génération exclut la recherche, et donc l'appel à Cohere et la reformulation, faits d'avance et gardés en cache.

## Lecture

- **Le RAG naïf reste le levier massif.** Son gain est plus faible avec Gemini (+28 points), qui répond déjà juste sans contexte à 88 % des questions sans réponse, mais s'abstient à tort sur 29 % des questions avec réponse quand il ne reçoit que 5 passages.
- **Ce qui paie, c'est d'envoyer plus de bons articles au générateur.** 20 passages et le reclassement en 5 font tous les deux mieux que 5 passages denses. Ils ne diffèrent pas entre eux (−1 à −2 points, non concluant), et le reclassement envoie 2,5 fois moins de tokens. Le reclassement porte le rappel au top-5 de 0,77 à 0,89. 20 passages couvrent davantage, mais avec du bruit.
- **La reformulation ne fait toujours rien.** Son petit gain de rappel au top-5 (+1 point) ne se voit pas dans `correct`.
- **La consigne d'abstention n'a pas tenu son effet sur Mistral Small.** Sur les mêmes 51 questions sans réponse, son A invente moins que dans l'étape 5 (0,222 contre 0,261), et la consigne n'en retire que 3,3 points. Sa garde ne tient pas non plus. L'étape 5 avait un seul run final, et l'intervalle de son delta (−15,7 à −2,6 points) laissait déjà la place à un petit effet. Le nouveau delta est dans cet intervalle, mais n'exclut plus 0.
- **La consigne coûte cher à Gemini sur les nouveaux modes.** En `false_premise`, elle fait tomber son `correct` de 0,54 à 0,18 : face à une prémisse fausse, il s'abstient au lieu de corriger la valeur. Mistral Small y perd aussi 12 points (0,79 → 0,67).
- **La meilleure configuration de l'expérience, par modèle :**
  - **Gemini Flash-Lite** : `top_k_20`.
  - **Mistral Small et Ministral 14B** : `top_k_20` ou `abstain_strict`, à égalité.
  - **Pour économiser des tokens**, `rerank_cohere` à qualité égale, au prix d'un fournisseur de plus.

## Écarts par rapport au protocole et au `dev`

- **Le run `dev` de contrôle** (k = 1, 91 items, commit `f8ca40f`) n'a servi qu'à vérifier que la campagne tournait : aucune erreur. Ses scores n'ont rien réglé.
- **La source de `naive_rag`.** Le protocole cite `exp002_rag`. Le registre prend la fonction de baseline des étapes 2 et 3, qui fait la même recherche, parce que celle de l'étape 1 est privée et construit son propre index. Le contrôle de reproduction confirme les contextes des runs finaux de l'étape 1.
- **Une référence non unanime au contrôle de reproduction.** Pour `rq-001`, à l'étape 1, 1 exécution sur 27 a vu deux articles dans l'ordre inverse. La référence est le contexte de la majorité.

## Dispersion

| Comparaison | s_d (Mistral Small / Ministral / Gemini) | Items où B gagne / perd |
|---|---|---|
| `naive_rag` − `closed_book` | 0,553 / 0,540 / 0,567 | 105/18, 116/11, 100/23 |
| `query_rewrite` − `naive_rag` | 0,273 / 0,306 / 0,315 | 18/18, 17/13, 20/18 |
| `top_k_20` − `naive_rag` | 0,366 / 0,372 / 0,324 | 33/23, 29/13, 38/10 |
| `rerank_cohere` − `top_k_20` | 0,301 / 0,311 / 0,309 | 20/20, 17/16, 17/23 |
| `rerank_cohere` − `naive_rag` | 0,340 / 0,353 / 0,366 | 27/18, 26/11, 35/11 |
| `abstain_strict` − `top_k_20` | 0,198 / 0,224 / 0,288 | 18/13, 9/8, 3/33 |

Avec n = 234, le MDE sans correction vaut (1,970 + 0,843) × s_d / √234, soit 6,0 à 6,8 points pour les leviers de récupération et 5,5 à 5,7 pour le reclassement. C'est un peu au-dessus des valeurs prévues au protocole (5,7 à 6,4 et 4,8 à 5,9). Les écarts de 3 points qui comptent pour 20 passages et pour le reclassement restent sous ce que le run pouvait détecter.

## Limites

- **Un seul run par configuration et par modèle**, à `temperature = 0`. La dispersion vient des items et des 3 répétitions, pas de plusieurs runs.
- **Les configurations n'ont pas été réitérées sur la v4**, comme le veut le protocole. Une consigne ou une profondeur réglée sur la v4 pourrait faire mieux sur les modes nouveaux.
- **Les questions sans réponse sont les mêmes qu'à l'étape 5** (les 51 questions valides de la v3) : la v4 n'en ajoute pas.
- **Les modes nouveaux sont petits** (12 à 30 items `test`) et ne se lisent qu'en secondaire. En `comparison`, la spec v1 ne vérifie pas le rattachement de chaque valeur à son cas. En `false_premise`, elle ne vérifie pas que la prémisse est rejetée. La reprise de la prémisse, que le README du golden set prévoit de compter, n'est pas mesurée, faute de `false_value` dans les items.
- **Sans Langfuse.** Les `executions.jsonl` et `summary.json` font foi.
- **Coût non mesuré sur facture.** L'estimation du protocole était de 8 à 13 $.
- **Les limites des étapes s'appliquent** : un seul corpus, et des questions rédigées par un LLM, relues par des relecteurs IA et arbitrées par le propriétaire.
