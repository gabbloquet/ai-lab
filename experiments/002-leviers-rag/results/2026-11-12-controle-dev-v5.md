# 002 — Run `dev` de contrôle sur le golden set v5 (2026-11-12)

> **Split `dev` seulement.** Ce run ne porte aucun verdict et ne sert à régler aucune configuration (plan de la 002, chantier 3). Les verdicts du tableau sont ceux du calcul, donnés à titre indicatif, comme pour tout résultat `dev`.

**Question :** le code de campagne, passé à la spec `rag-qa/v2`, reproduit-il les configurations gelées des étapes 1 à 6, et quelle est la difficulté du golden set v5 pour elles ?

**Réponse.** La reproduction est exacte : chaque configuration redonne les contextes des runs finaux de ses étapes. Sur le `dev` v5, les leviers vont dans le même sens que dans le run consolidé sur la v4 :
- le RAG bat nettement le modèle seul ;
- 20 passages battent 5 avec Ministral 14B et Gemini Flash-Lite, mais pas après correction de Holm avec Mistral Small ;
- ni la reformulation ni le reclassement n'apportent de gain net ;
- les étapes 5 et 6 ne font pas moins inventer, et la consigne de l'étape 5 fait trop s'abstenir Gemini.

Les modes récents, notés par les règles v2, sont les plus durs : `set` reste sous 0,40 et `comparison` entre 0,56 et 0,78 avec 20 passages.

## Provenance

| Élément | Valeur |
|---|---|
| Commit | `aacc6e5` (« 002 : ajouter l'étape 6 au run de contrôle sur la v5 »), enregistré dans chaque `summary.json` (`run.commit`) |
| Golden set | `domains/droit-consommation/golden/rag-qa/v5`, `items.jsonl` sha256 `9677d85172341b31ec5f71e030bda87ebe17a531126df63c5b0c22fca1426d53` ; 118 items `dev` valides, 2 écartés par l'audit (`audit/v1-unanswerable.jsonl`) |
| Données | `domains/droit-consommation/data/v1` |
| Spec de notation | `evals/spec/rag-qa/v2` : `SPEC.md` sha256 `332b854924a7fc025b7deb33d876e4d800cc3554c899f471cb8b7f5c83a334e6`, `conformance.jsonl` sha256 `e704977d831a6c80e9bf91f9f2e58e1c110953a4bba56713c721394cbced426d` |
| Scorer | `ailab_evals.rag_qa_v2` (Python), conforme aux 84 vecteurs. Le scorer Java (`ragqa`), conforme aux mêmes vecteurs, n'a pas servi à ce run |
| Lockfile | `uv.lock` sha256 `462061c320a663572e9a439074fa7534770e83795a96da7a4ca615147f9aba76` |
| Lancement | `uv run --env-file .env python -m exp002_leviers.campaign --split dev --spec v2 --model <générateur>`, le 2026-11-12, de 12 h 35 à 13 h 19. Sorties : `runs/2026-11-12-<générateur>-dev/` (`executions.jsonl`, `step6-executions.jsonl`, `summary.json`) |

**Générateurs** : `mistral:mistral-small-2603`, `mistral:ministral-14b-2512`, `google:gemini-3.5-flash-lite`, avec `temperature = 0` et k = 3.

**Configurations** : celles du run consolidé (`closed_book`, `naive_rag`, `query_rewrite`, `top_k_20`, `rerank_cohere`, `abstain_strict`), plus celle de l'étape 6 (`abstain_low_rerank`). Celle-ci est calculée sans appel au générateur, à partir des exécutions `top_k_20` et des notes `cohere:rerank-v5.0-pro` en cache, avec un seuil de 0,20.

**Reformulation** : `google:gemini-3.8-flash`.

**Contrôle de reproduction** (avant tout appel payant, sur les caches seuls) : les contextes sont identiques pour 150 items sur 150 (`query_rewrite`, `rerank_cohere`) et 190 sur 190 (`top_k_20`). La seule référence non unanime vient d'un run d'étape précédent. Elle est connue : sur `naive_rag/rq-001`, un des 27 contextes de référence intervertit deux articles.

**Mesures hors spec, et ce qu'elles couvrent.**
- **`latency_s`** : la durée de bout en bout de chaque exécution, recherche comprise. Les embeddings, reformulations et notes Cohere venant des caches, la recherche est plus rapide qu'en production. Les mesures ont été prises sur la même machine, pendant la même heure.
- **`cost_usd`** n'est pas calculé (`null`) : le barème des prix se vérifie à la source dans le protocole de l'étape 7.

## Comparaisons de `correct` (§ 8.1 et § 8.3 de la spec v2)

Famille de Holm : les six comparaisons de chaque générateur, avec α = 0,05.

| Comparaison | Mistral Small | Ministral 14B | Gemini Flash-Lite |
|---|---|---|---|
| `naive_rag` − `closed_book` | 0,393 → 0,706, +0,314 [+0,216 ; +0,411], **meilleure** | 0,305 → 0,715, +0,410 [+0,307 ; +0,512], **meilleure** | 0,418 → 0,701, +0,282 [+0,190 ; +0,375], **meilleure** |
| `query_rewrite` − `naive_rag` | +0,017 [−0,033 ; +0,067], non concluant | +0,028 [−0,016 ; +0,073], non concluant | +0,028 [−0,028 ; +0,084], non concluant |
| `top_k_20` − `naive_rag` | +0,079 [+0,017 ; +0,141], non concluant après Holm (p_holm = 0,064) | +0,119 [+0,046 ; +0,191], **meilleure** | +0,124 [+0,054 ; +0,195], **meilleure** |
| `rerank_cohere` − `top_k_20` | −0,023 [−0,066 ; +0,021], non concluant | +0,003 [−0,053 ; +0,059], non concluant | −0,008 [−0,064 ; +0,047], non concluant |
| `rerank_cohere` − `naive_rag` | +0,056 [−0,011 ; +0,124], non concluant | +0,121 [+0,052 ; +0,191], **meilleure** | +0,116 [+0,043 ; +0,188], **meilleure** |
| `abstain_strict` − `top_k_20` | −0,020 [−0,057 ; +0,018], non concluant | −0,023 [−0,062 ; +0,017], non concluant | −0,141 [−0,207 ; −0,075], **moins bonne** |

## Étapes 5 et 6 : verdict à deux critères (§ 8.2)

Le critère principal est `hallucination`, sur les 28 questions sans réponse, en `lower_better`. La garde est `false_abstention`, sur les 90 questions avec réponse, en `lower_better`, avec une marge de 0,03.

| Générateur | Étape 5 (`abstain_strict`) : inventées / garde | Verdict | Étape 6 (`abstain_low_rerank`) : inventées / garde | Verdict |
|---|---|---|---|---|
| Mistral Small | −0,048 [−0,106 ; +0,010] / +0,052 [+0,013 ; +0,091] | non concluant | −0,060 [−0,139 ; +0,020] / 0,000 | non concluant |
| Ministral 14B | −0,012 [−0,120 ; +0,096] / +0,011 [−0,008 ; +0,031] | non concluant | −0,036 [−0,109 ; +0,038] / 0,000 | non concluant |
| Gemini Flash-Lite | 0,000 / +0,219 [+0,130 ; +0,307] | **moins bonne** (garde franchie) | 0,000 / 0,000 | non concluant |

Le seuil de l'étape 6 écarte 10 des 28 questions sans réponse et aucune des 90 questions avec réponse. Le même schéma se voyait au `test` v4 (16 sur 51, et 1 sur 183).

## Agrégats par configuration (§ 7)

| `correct` / inventées / abstentions à tort | Mistral Small | Ministral 14B | Gemini Flash-Lite |
|---|---|---|---|
| `closed_book` | 0,393 / 0,202 / 0,126 | 0,305 / 0,286 / 0,178 | 0,418 / 0,107 / 0,317 |
| `naive_rag` | 0,706 / 0,250 / 0,115 | 0,715 / 0,179 / 0,104 | 0,701 / 0,036 / 0,284 |
| `query_rewrite` | 0,723 / 0,262 / 0,081 | 0,743 / 0,155 / 0,074 | 0,729 / 0,048 / 0,267 |
| `top_k_20` | 0,785 / 0,238 / 0,052 | 0,833 / 0,190 / 0,004 | 0,825 / 0,000 / 0,144 |
| `rerank_cohere` | 0,763 / 0,226 / 0,048 | 0,836 / 0,226 / 0,004 | 0,816 / 0,000 / 0,163 |
| `abstain_strict` | 0,766 / 0,190 / 0,104 | 0,811 / 0,179 / 0,015 | 0,684 / 0,000 / 0,363 |
| `abstain_low_rerank` | 0,799 / 0,179 / 0,052 | 0,842 / 0,155 / 0,004 | 0,825 / 0,000 / 0,144 |

Aucune erreur d'exécution, sauf avec Gemini : 0,6 % en `closed_book` et en `naive_rag`.

**`top_k_20`, en détail.**

| | Mistral Small | Ministral 14B | Gemini Flash-Lite |
|---|---|---|---|
| `failure` : `correct` / `retrieval_miss` / `generation_miss` | 0,793 / 0,044 / 0,163 | 0,841 / 0,044 / 0,115 | 0,770 / 0,070 / 0,159 |
| `premise` : `corrected` / `adopted` / `missed` (`unresolved` : 0) | 0,750 / 0,033 / 0,217 | 0,950 / 0,050 / 0 | 0,867 / 0,050 / 0,083 |
| Tokens par exécution | 3 984 | 3 996 | 4 120 |
| Latence médiane / 95ᵉ centile (s) | 0,88 / 1,43 | 1,31 / 2,19 | 0,79 / 1,29 |

**`correct` par mode, avec `top_k_20`** (n `dev` : `comparison` 9, `set` 7, `false_premise` 20, `multi_article` 18, `direct` 11, `paraphrase` 10, `reference` 8, `lost_context` 7, `unanswerable` 28) :

| Mode | Mistral Small | Ministral 14B | Gemini Flash-Lite |
|---|---|---|---|
| `set` | 0,33 | 0,29 | 0,38 |
| `comparison` | 0,59 | 0,78 | 0,56 |
| `false_premise` | 0,75 | 0,95 | 0,70 |
| `multi_article` | 0,91 | 0,81 | 0,87 |
| `paraphrase` | 0,77 | 0,83 | 0,60 |
| `unanswerable` | 0,76 | 0,81 | 1,00 |
| `direct`, `reference`, `lost_context` | 0,86 à 1,00 | 0,91 à 1,00 | 1,00 |

## Lecture

- **Le code de campagne v2 reproduit les configurations gelées.** Le contrôle de reproduction est exact. Les comparaisons gardent leur sens de la v4. Un test du dépôt vérifie aussi que l'analyse v2 redonne exactement les chiffres de l'analyse v1 sur des items sans champs v2.
- **La récupération reste saturée.** Avec 20 passages, 4 à 7 % des exécutions manquent un article attendu. Les échecs viennent surtout de la génération (12 à 16 %), comme dans la pré-étude du `dev` v4.
- **Les modes récents sont durs.** En `set`, chaque élément de la liste doit figurer dans la réponse. En `comparison`, chaque valeur doit maintenant être rattachée à son cas (spec v2, § 5.3).
- **Le rejet de la prémisse est mesuré, et l'hésitation n'apparaît pas.** Aucune réponse ne donne les deux valeurs sans trancher (`unresolved` à 0), comme à l'étalonnage de la spec. Les échecs `false_premise` sont surtout des réponses sans la vraie valeur (`missed`, jusqu'à 22 % avec Mistral Small), plus que des prémisses reprises (`adopted`, 3 à 5 %).
- **Les réponses inventées dépendent du modèle**, et aucun levier de récupération ni d'abstention ne les fait baisser nettement. Avec 20 passages, Gemini n'en invente aucune, contre 24 % pour Mistral Small. C'est la question de l'étape 7.

## Limites

- **Un `dev` petit**, et des IC larges : 28 questions sans réponse, et 7 à 20 items par mode récent. Les scores par mode sont indicatifs.
- **Le `test` v5 est celui de la v4** : il a déjà été lu deux fois en agrégat (run consolidé, étape 6).
- **Latence mesurée avec les caches**, sur une seule machine. Elle ne se compare qu'entre runs mesurés de la même façon (spec v2, § 7).
- **Coût non calculé** : le barème des prix vient avec l'étape 7.
- **Limites du golden set v5** (son README, section « v5 ») : un corpus épuisé pour `comparison` et `set`, des doutes de relecture gardés, et des pluriels non retrouvés par les ancres.
