# 006 — Run final sur le split `test` (2026-11-09)

**Question :** sur le Code de la consommation, une consigne qui demande de vérifier qu'un extrait donne exactement la valeur demandée, pour la situation de la question, fait-elle baisser les réponses inventées aux questions sans réponse, sans faire augmenter les abstentions à tort, à générateur constant ?

**Réponse :** cela dépend du générateur. **Mistral Small : B meilleure.** La consigne fait passer ses réponses inventées de 0,26 à 0,17 (−9,2 points [−15,7 ; −2,6]) sans aucune abstention à tort de plus. **Ministral 14B : non concluant**, avec une baisse de −5,2 points [−13,5 ; +3,0]. **Gemini Flash-Lite : B moins bonne.** Il n'inventait déjà presque pas (0,03), et la consigne double ses abstentions à tort (0,09 → 0,17, +8,7 points [+3,2 ; +14,1]). Une même phrase de prompt aide le modèle qui invente et nuit à celui qui s'abstient déjà.

## Provenance

| Élément | Valeur |
|---|---|
| Commit de gel des variantes | « Geler la 006 avant le run final sur le test » (`28bc317`), dépôt propre (`--final`), commit enregistré dans chaque `summary.json` (`run.commit`) |
| Golden set | `domains/droit-consommation/golden/rag-qa/v3`, `items.jsonl` sha256 `71ec6cf9247ce52dd7c60fe742a357ad4a2cf26a4df6025437477926fec297d8`, 190 items `test` |
| Items écartés | Les 12 items `test` que l'audit de la v1 trouve répondus par le code (`golden/rag-qa/audit/v1-unanswerable.jsonl`, sha256 `456fa478e889ab57528b69b1483881b8b065e9bbd8ac0f8c4a95cc121235dcd4`) : ils n'ont pas tourné. Restent 178 items valides : 51 sans réponse, 127 avec réponse |
| Données | `domains/droit-consommation/data/v1/articles.jsonl` sha256 `ed9bb9ffd05103792132a35f1fab91c0c3dc07a719c7764ab7269eb85851d9d2` |
| Spec de notation | `evals/spec/rag-qa/v1`, avec la règle de verdict à deux critères du README (écart fixé avant le premier run) |
| Lockfile | `uv.lock` sha256 `bb2bb559a490bf8e7da0c59f81ed38f71698a2ad142cedd146df1ce6d9025c76` |
| Baseline (A) | RAG à 20 passages de la 004 : `mistral-embed`, cosinus exact, top-k = 20, prompts du gel de la 002 |
| Variante (B) | A, avec la phrase d'ancrage `exp006_rag.campaign.STRICT_GROUNDING` : celle de A, plus « Avant de répondre, vérifie qu'un extrait donne exactement la valeur demandée, pour la situation de la question. Un extrait sur un cas voisin (autre acteur, autre procédure, autre contrat) ne suffit pas : mets alors `abstained` à vrai. » |
| Code | `python/src/exp006_rag/campaign.py` sha256 `6a3f600a8f8da52622e5963416154fb27dd30bae1d1ffecd0968ac635b0530ea` ; `rag/python/src/ailab_rag/prompting.py` sha256 `925890b82fa134fcc00100e1e50b003bb196ef62cbcb8934e72c468c82ff562c` |
| Boucle | Pydantic AI 2.65.0, sortie imposée par l'outil de sortie, `temperature = 0`, 4 exécutions à la fois |
| Plan | 178 items × 2 variantes × k = 3, soit 1 068 exécutions par générateur |
| Runs | `runs/final-test-<générateur>`, les trois en parallèle, le 2026-11-09 de 18:17 à 18:26 (heure de Paris), avec Langfuse (traces incomplètes, voir Limites) |
| Calcul | `ailab_rag.campaign.abstention_comparison` (verdict `ailab_evals.paired.joint_verdict`) et `summarize`, dans le `summary.json` de chaque run |

Générateurs : `mistral:mistral-small-2603`, `mistral:ministral-14b-2512`, `google:gemini-3.5-flash-lite`, identifiants vérifiés le 2026-11-09, `temperature = 0`.

## Verdict par générateur

Règle fixée avant le run : B est meilleure si la borne haute de l'IC à 95 % du delta des réponses inventées est sous 0 **et** si la borne haute du delta des abstentions à tort est sous +0,03 ; moins bonne si les réponses inventées augmentent, ou si la borne basse des abstentions à tort dépasse +0,03 ; compromis si les réponses inventées baissent mais que la garde ne tient pas ; non concluant sinon.

| Générateur | Réponses inventées A → B (51 items) | Delta [IC 95 %] | Abstentions à tort A → B (127 items) | Delta [IC 95 %] | Verdict |
|---|---|---|---|---|---|
| `mistral-small-2603` | 0,261 → 0,170 | **−0,092** [−0,157 ; −0,026] | 0,008 → 0,005 | −0,003 [−0,008 ; +0,003] | **B meilleure** |
| `ministral-14b-2512` | 0,255 → 0,203 | **−0,052** [−0,135 ; +0,030] | 0,029 → 0,026 | −0,003 [−0,012 ; +0,006] | **non concluant** |
| `gemini-3.5-flash-lite` | 0,026 → 0,020 | −0,007 [−0,020 ; +0,007] | 0,087 → 0,173 | **+0,087** [+0,032 ; +0,141] | **B moins bonne** |

Aucune erreur d'exécution sur les 3 204 exécutions.

**Lecture du seuil de 10 points.** Pour Mistral Small, la baisse est réelle et vaut 9,2 points, mais l'intervalle va de 2,6 à 15,7 points : elle peut être plus petite que l'écart qui compte. Pour Gemini Flash-Lite, le critère principal ne pouvait rien montrer (plancher à 0,03, prévu au protocole) ; c'est la garde qui tranche.

**A reproduit la 005.** Sur les 138 items valides du `test` de la v1, A répond juste à 0,894 (0,891 pour le même A dans la 005) avec Mistral Small, 0,867 (0,870) avec Ministral 14B, 0,872 (0,877) avec Gemini Flash-Lite.

## Métriques secondaires

Elles ne portent pas le verdict. Sur les 178 items valides, `correct` mélange 29 % de questions sans réponse : il donne plus de poids à l'abstention qu'un usage réel (voir le README du golden set).

| Métrique | Mistral Small A | B | Ministral 14B A | B | Gemini Flash-Lite A | B |
|---|---|---|---|---|---|---|
| `correct`, 178 items valides | 0,863 | 0,882 | 0,841 | 0,863 | 0,899 | 0,854 |
| Delta `correct` [IC 95 %] | | +0,019 [−0,003 ; +0,041] | | +0,022 [−0,011 ; +0,056] | | −0,045 [−0,080 ; −0,010] |
| `correct`, 138 items valides de la v1 | 0,894 | 0,889 | 0,867 | 0,877 | 0,872 | 0,812 |
| `correct`, items avec réponse | 0,913 | 0,903 | 0,879 | 0,890 | 0,869 | 0,803 |
| Tokens par exécution | 3 947 | 3 996 | 3 959 | 4 012 | 4 093 | 4 144 |
| Temps de génération, médiane | 0,80 s | 0,79 s | 1,49 s | 1,44 s | 0,83 s | 0,82 s |

**`correct` par mode, A → B :**

| Mode | Mistral Small | Ministral 14B | Gemini Flash-Lite |
|---|---|---|---|
| `direct` | 0,97 → 0,97 | 0,88 → 0,87 | 0,90 → 0,80 |
| `reference` | 1,00 → 1,00 | 1,00 → 1,00 | 0,91 → 0,95 |
| `paraphrase` | 0,93 → 0,91 | 0,82 → 0,88 | 0,91 → 0,80 |
| `multi_article` | 0,64 → 0,61 | 0,71 → 0,71 | 0,59 → 0,45 |
| `lost_context` | 1,00 → 1,00 | 1,00 → 1,00 | 1,00 → 1,00 |
| `unanswerable` (valides) | 0,74 → 0,83 | 0,75 → 0,80 | 0,97 → 0,98 |

## Lecture

- **La consigne marche pour le modèle qui invente le plus.** Mistral Small invente moins sur 9 des 51 questions sans réponse, et davantage sur aucune ; il ne perd aucune réponse juste ailleurs. Au `dev`, le même B ne faisait rien (−1,2 point sur 28 questions) : le `test`, deux fois plus large, montre un effet que le `dev` était trop petit pour voir.
- **Elle ne tranche pas pour Ministral 14B** (−5,2 points, intervalle large), qui invente autant que Mistral Small au départ.
- **Elle nuit au modèle prudent.** Gemini Flash-Lite n'invente presque jamais avec 20 passages (0,03) ; la consigne le rend plus prudent encore, et il s'abstient à tort deux fois plus souvent, surtout sur les questions directes, en paraphrase et à plusieurs articles (−10 à −14 points de `correct`).
- **Une consigne d'abstention se règle par modèle.** Le même texte déplace chaque générateur dans la direction où il penche déjà : vers moins d'invention pour un modèle qui répond trop, vers plus d'abstentions pour un modèle qui s'abstient déjà.
- **Coût nul** : une phrase de plus, environ 50 tokens d'entrée, aucun effet sur le temps de génération.

## Écarts par rapport au `dev`

Au run 0 du `dev` (Mistral Small), la même version de B donnait −1,2 point de réponses inventées [−8,6 ; +6,3] et +3,0 points d'abstentions à tort [−1,8 ; +7,8], sur 28 et 44 items. Sur le `test`, −9,2 points et −0,3 point, sur 51 et 127 items. Les deux intervalles du critère principal se recouvrent ; l'écart reste dans la dispersion attendue entre deux échantillons de cette taille. Le `dev` n'a pas permis de prévoir l'effet sur Gemini Flash-Lite : l'itération ne tournait qu'avec Mistral Small.

## Dispersion

| Générateur | s_d des réponses inventées (51 items) | Items où B invente moins / plus |
|---|---|---|
| `mistral-small-2603` | 0,232 | 9 / 0 |
| `ministral-14b-2512` | 0,293 | 4 / 1 |
| `gemini-3.5-flash-lite` | 0,047 | 1 / 0 |

Avec s_d ≈ 0,23 à 0,29, le MDE sur 51 items est de 9 à 12 points : la baisse de Ministral 14B (−5,2) est sous ce que l'expérience pouvait détecter.

## Limites

- **Traces Langfuse incomplètes** (`run.langfuse_flushed: false` pour les trois runs) : les `executions.jsonl` et `summary.json` font foi.
- **Itération avec un seul générateur.** B a été mise au point avec Mistral Small ; l'effet sur Gemini Flash-Lite n'a été vu qu'au run final.
- **B moins travaillée que A pour le nombre de cycles utiles** : 1 cycle utilisé sur 2, gelée sur la version du run 0, choisie entre deux versions au `dev`.
- **Questions sans réponse relues par des relecteurs IA**, arbitrées par le propriétaire sur des propositions réunies en une page : il peut rester des questions auxquelles le code répond.
- **Le `test` de la v3 a été lu pendant sa construction** (audit, relecture) ; la consigne de B ne s'appuie que sur le `dev`.
- **Les limites de la 002 s'appliquent** : un seul corpus, questions rédigées par un LLM.
